import os
import numpy as np
import pandas as pd
import xarray as xr
from scipy.spatial import KDTree
import conf
from src.env_data import (
    grab_etopo,
    _calc_slope,
    _mk_session,
    _grab_sst_month,
    _lon360,
    _load_wind,
    _ll2xyz,
)
from src.feat_eng import add_feats

_bathy_cache = None


def _ensure_bathy():
    global _bathy_cache
    if _bathy_cache is not None:
        return _bathy_cache
    ds = grab_etopo()
    sg = _calc_slope(ds)
    evar = list(ds.data_vars)[0]
    latk = "latitude" if "latitude" in ds.dims else "lat"
    lonk = "longitude" if "longitude" in ds.dims else "lon"
    lg, lo = np.meshgrid(ds[latk].values, ds[lonk].values, indexing="ij")
    mask = ds[evar].values >= 0
    x, y, z = _ll2xyz(lg[mask], lo[mask])
    tree = KDTree(np.column_stack([x, y, z]))
    _bathy_cache = {"ds": ds, "sg": sg, "tree": tree, "evar": evar, "latk": latk, "lonk": lonk}
    return _bathy_cache


def _shore_km(tree, lat, lon):
    qx, qy, qz = _ll2xyz(np.array([lat]), np.array([lon]))
    chord, _ = tree.query(np.column_stack([qx, qy, qz]))
    return float(6371.0 * 2 * np.arcsin(np.clip(chord[0] / 2, 0, 1)))


def build_feature_matrix(lat, lon, month, _day):
    warnings = []
    c = _ensure_bathy()
    ds, sg, tree = c["ds"], c["sg"], c["tree"]
    evar, latk, lonk = c["evar"], c["latk"], c["lonk"]
    sel = {latk: lat, lonk: lon}
    elev = float(ds[evar].sel(**sel, method="nearest").values)
    if elev >= 0:
        warnings.append("point_on_land")
    depth = -elev if elev < 0 else 0.0
    slope = float(sg.sel(**sel, method="nearest").values)
    dist_shore = _shore_km(tree, lat, lon)

    os.makedirs(conf.SST_DIR, exist_ok=True)
    sess = _mk_session()
    sst_ds = _grab_sst_month(conf.API_REF_YEAR, month, sess)
    if sst_ds is None:
        raise RuntimeError(
            "SST unavailable for year=%d month=%d (network or ERDDAP); run pipeline to cache"
            % (conf.API_REF_YEAR, month)
        )
    var = "sst" if "sst" in sst_ds.data_vars else list(sst_ds.data_vars)[0]
    arr = sst_ds[var].squeeze(drop=True)
    latd = "latitude" if "latitude" in arr.dims else "lat"
    lond = "longitude" if "longitude" in arr.dims else "lon"
    arr = arr.sortby(latd).sortby(lond)
    arr = arr.interpolate_na(dim=latd, method="nearest")
    arr = arr.interpolate_na(dim=lond, method="nearest")
    try:
        sst_v = float(arr.sel(**{latd: lat, lond: _lon360(lon)}, method="nearest").values)
    except Exception:
        sst_v = np.nan
    if np.isnan(sst_v):
        sst_v = -1.8

    if not os.path.exists(conf.WIND_FILE):
        raise RuntimeError("missing wind file %s; run pipeline once" % conf.WIND_FILE)
    wds = _load_wind()
    snap = None
    wind_v = np.nan
    try:
        snap = (
            wds["wind_speed"]
            .sel(time="%d-%02d-01" % (conf.API_REF_YEAR, month), method="nearest")
            .squeeze(drop=True)
            .sortby("lat")
            .sortby("lon")
        )
        wind_v = float(snap.sel(lat=lat, lon=_lon360(lon), method="nearest").values)
    except Exception:
        pass
    wds.close()
    if np.isnan(wind_v):
        if snap is not None:
            wind_v = float(np.nanmedian(snap.values))
        if np.isnan(wind_v):
            wind_v = 7.0

    ms = np.sin(2 * np.pi * month / 12)
    mc = np.cos(2 * np.pi * month / 12)

    df = pd.DataFrame(
        [
            {
                "decimalLatitude": lat,
                "decimalLongitude": lon,
                "depth": depth,
                "slope": slope,
                "sst": sst_v,
                "wind_speed_10m": wind_v,
                "distance_to_shore_km": dist_shore,
                "month_sin": ms,
                "month_cos": mc,
            }
        ]
    )
    df = add_feats(df)
    X = df[conf.ALL_FEATS].values.astype(np.float64)
    return X, warnings
