"""
Hybrid reverse geocoding for marine and coastal coordinates.

1) Point-in-polygon against IHO World Seas (GeoPandas + marineregions.org shapefile).
2) If no marine polygon matches (land, gaps, or near-shore), fall back to Nominatim (geopy).

Download the IHO shapefile (required for ocean names):
  https://www.marineregions.org/download_file.php?id=World_Seas_IHO_v3.zip
  (MarineRegions.org -> Products -> IHO Sea Areas, or search "IHO Sea Areas" on the site.)

  Unzip and point IHO_SEAS_SHAPEFILE to the .shp path, e.g.:
    export IHO_SEAS_SHAPEFILE=/path/to/World_Seas_IHO_v3.shp

  Alternatively call set_iho_shapefile("/path/to/World_Seas_IHO_v3.shp") once at startup.

Nominatim usage policy: set a unique user_agent; do not hammer the service (rate limits apply).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default relative path if you place the unzipped shapefile under backend/data/iho/
_DEFAULT_RELATIVE_SHP = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "iho",
    "World_Seas_IHO_v3.shp",
)


def _pick_name_column(gdf) -> Optional[str]:
    """Pick the best attribute column for the marine region label."""
    candidates = (
        "NAME",
        "name",
        "Name",
        "MarineRegio",
        "marregion",
        "MARREGION",
        "LABEL",
        "label",
        "geoname",
    )
    for c in candidates:
        if c in gdf.columns:
            return c
    for c in gdf.columns:
        if c != "geometry" and gdf[c].dtype == object:
            return c
    return None


class HybridReverseGeocoder:
    """
    Loads IHO polygons once; reuses them for every lookup.
    Nominatim client is created once with a fixed user_agent.
    """

    def __init__(
        self,
        iho_shapefile_path: Optional[str],
        *,
        user_agent: str = "seal-sdm-geocoder/1.0 (https://github.com; research use)",
    ):
        self._gdf = None
        self._name_col: Optional[str] = None
        self._nominatim = None
        self._user_agent = user_agent

        if iho_shapefile_path and os.path.isfile(iho_shapefile_path):
            import geopandas as gpd

            self._gdf = gpd.read_file(iho_shapefile_path)
            if self._gdf.crs is None:
                self._gdf.set_crs(4326, inplace=True)
            else:
                self._gdf = self._gdf.to_crs(epsg=4326)
            self._name_col = _pick_name_column(self._gdf)
            if self._name_col is None:
                logger.warning("IHO shapefile has no obvious name column; ocean names disabled.")
                self._gdf = None
        else:
            if iho_shapefile_path:
                logger.warning(
                    "IHO shapefile not found at %s; only Nominatim fallback will run.",
                    iho_shapefile_path,
                )

        from geopy.geocoders import Nominatim

        self._nominatim = Nominatim(user_agent=user_agent, timeout=12)

    def marine_region_name(self, lat: float, lon: float) -> Optional[str]:
        """
        Return the IHO sea/ocean name if (lon, lat) lies inside a polygon, else None.
        """
        if self._gdf is None or self._name_col is None:
            return None

        import geopandas as gpd
        from shapely.geometry import Point

        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return None

        pt = Point(lon, lat)
        gpt = gpd.GeoDataFrame({"geometry": [pt]}, crs="EPSG:4326")
        # within = point inside polygon; covers most IHO uses
        hit = gpd.sjoin(gpt, self._gdf, how="left", predicate="within")
        if hit.index_right.isna().all():
            # try intersects for edge cases (boundary)
            hit = gpd.sjoin(gpt, self._gdf, how="left", predicate="intersects")
        if hit.index_right.isna().all():
            return None

        row = self._gdf.loc[hit["index_right"].iloc[0]]
        val = row[self._name_col]
        if val is None or (isinstance(val, float) and str(val) == "nan"):
            return None
        s = str(val).strip()
        return s if s else None

    def nominatim_place_string(self, lat: float, lon: float) -> Optional[str]:
        """
        Reverse-geocode with Nominatim and compress to a short place description.
        """
        from geopy.exc import GeocoderServiceError, GeocoderTimedOut

        try:
            loc = self._nominatim.reverse((lat, lon), exactly_one=True, language="en")
        except (GeocoderTimedOut, GeocoderServiceError, OSError) as e:
            logger.debug("Nominatim error: %s", e)
            return None
        except Exception as e:
            logger.debug("Unexpected geocoder error: %s", e)
            return None

        if loc is None:
            return None

        raw: dict[str, Any] = getattr(loc, "raw", {}) or {}
        addr = raw.get("address") or {}

        # Prefer human-scale labels over full postal dumps
        ordered_keys = (
            "amenity",
            "tourism",
            "leisure",
            "neighbourhood",
            "suburb",
            "quarter",
            "city_district",
            "town",
            "village",
            "hamlet",
            "city",
            "municipality",
            "county",
            "state",
            "region",
            "country",
        )
        parts: list[str] = []
        seen: set[str] = set()
        for key in ordered_keys:
            v = addr.get(key)
            if v and str(v).strip():
                t = str(v).strip()
                if t.lower() not in seen:
                    parts.append(t)
                    seen.add(t.lower())
            if len(parts) >= 4:
                break

        if parts:
            return ", ".join(parts)

        name = raw.get("display_name") or getattr(loc, "address", None) or str(loc)
        if isinstance(name, str) and len(name) > 120:
            return name[:117] + "..."
        return str(name) if name else None

    def resolve(self, lat: float, lon: float) -> str:
        """Full hybrid pipeline."""
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return "Unknown Location"

        marine = self.marine_region_name(lat, lon)
        if marine:
            return marine

        landish = self.nominatim_place_string(lat, lon)
        if landish:
            return landish

        return "Unknown Location"


_resolver: Optional[HybridReverseGeocoder] = None


def set_iho_shapefile(path: str) -> None:
    """Force the global resolver to use this shapefile path (re-instantiates loader)."""
    global _resolver
    _resolver = HybridReverseGeocoder(path)


def _get_resolver() -> HybridReverseGeocoder:
    global _resolver
    if _resolver is None:
        path = os.environ.get("IHO_SEAS_SHAPEFILE", _DEFAULT_RELATIVE_SHP)
        _resolver = HybridReverseGeocoder(path)
    return _resolver


def get_location_name(lat: float, lon: float) -> str:
    """
    Return a short human-readable place name: IHO sea/ocean if applicable,
    otherwise a compact Nominatim-derived string, or 'Unknown Location'.
    """
    try:
        return _get_resolver().resolve(float(lat), float(lon))
    except Exception as e:
        logger.exception("get_location_name failed: %s", e)
        return "Unknown Location"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("--- geocoder_util self-test ---")
    print(
        "If ocean test prints 'Unknown Location', set IHO_SEAS_SHAPEFILE or place\n"
        "  World_Seas_IHO_v3.shp under backend/data/iho/\n"
        "  Download: https://www.marineregions.org/download_file.php?id=World_Seas_IHO_v3.zip\n"
    )

    tests = [
        ("mid-Pacific (deep ocean)", 0.0, -160.0),
        ("La Jolla Shores (coastal)", 32.8595, -117.2568),
        ("North Atlantic patch", 45.0, -40.0),
    ]

    for label, la, lo in tests:
        name = get_location_name(la, lo)
        print("%s  (%.4f, %.4f) -> %r" % (label, la, lo, name))
