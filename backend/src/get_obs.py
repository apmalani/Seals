import os
import numpy as np
import pandas as pd
from pyobis import occurrences
from scipy.spatial import KDTree
import conf


def pull_from_obis():
    frames = []
    offset = 0
    while sum(len(f) for f in frames) < conf.N_RECORDS:
        q = occurrences.search(scientificname=conf.TAXON, size=conf.PAGE_SZ, offset=offset)
        q.execute()
        d = q.data
        if isinstance(d, pd.DataFrame): batch = d
        elif isinstance(d, list): batch = pd.DataFrame(d)
        elif isinstance(d, dict) and "results" in d: batch = pd.DataFrame(d["results"])
        else: batch = pd.DataFrame(d) if d is not None else pd.DataFrame()
        if batch.empty: break
        frames.append(batch)
        offset += conf.PAGE_SZ

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    for c in ["decimalLatitude","decimalLongitude","eventDate"]:
        if c not in df.columns: raise ValueError("missing " + c)

    df = df.dropna(subset=["decimalLatitude","decimalLongitude","eventDate"])
    df["eventDate"] = pd.to_datetime(df["eventDate"], errors="coerce", utc=True)
    df = df.dropna(subset=["eventDate"])
    df = df[df["eventDate"] >= pd.Timestamp(conf.MIN_DATE, tz="UTC")]
    keep = ["decimalLatitude","decimalLongitude","eventDate"]
    if "species" in df.columns:
        keep.append("species")
    df = df[keep].copy()
    df["decimalLatitude"] = df["decimalLatitude"].astype(float)
    df["decimalLongitude"] = df["decimalLongitude"].astype(float)
    if "species" not in df.columns:
        df["species"] = "unknown_phocidae"
    df["species"] = df["species"].fillna("unknown_phocidae").str.strip()
    df["target"] = 1
    return df.reset_index(drop=True)


def _open_etopo():
    import xarray as xr
    if not os.path.exists(conf.ETOPO_FILE):
        from src.env_data import grab_etopo
        grab_etopo()
    return xr.open_dataset(conf.ETOPO_FILE)

def _land_tree(etopo):
    latk = "latitude" if "latitude" in etopo.dims else "lat"
    lonk = "longitude" if "longitude" in etopo.dims else "lon"
    evar = list(etopo.data_vars)[0]
    lg, lo = np.meshgrid(etopo[latk].values, etopo[lonk].values, indexing="ij")
    mask = etopo[evar].values >= 0
    la_r, lo_r = np.radians(lg[mask]), np.radians(lo[mask])
    xyz = np.column_stack([np.cos(la_r)*np.cos(lo_r), np.cos(la_r)*np.sin(lo_r), np.sin(la_r)])
    return KDTree(xyz)

def _shore_km(tree, lats, lons):
    la_r, lo_r = np.radians(lats), np.radians(lons)
    xyz = np.column_stack([np.cos(la_r)*np.cos(lo_r), np.cos(la_r)*np.sin(lo_r), np.sin(la_r)])
    chord, _ = tree.query(xyz)
    return 6371.0 * 2 * np.arcsin(np.clip(chord/2, 0, 1))

def generate_fakes(occ_df, ratio=1.0):
    n = int(len(occ_df) * ratio)
    etopo = _open_etopo()
    latk = "latitude" if "latitude" in etopo.dims else "lat"
    lonk = "longitude" if "longitude" in etopo.dims else "lon"
    evar = list(etopo.data_vars)[0]
    tree = _land_tree(etopo)

    dates = occ_df["eventDate"].values
    rng = np.random.default_rng(conf.SEED)

    good_la, good_lo, good_dt = [], [], []
    for attempt in range(30):
        if len(good_la) >= n: break
        lats = rng.uniform(conf.LAT_MIN, conf.LAT_MAX, size=n*5)
        lons = rng.uniform(conf.LON_MIN, conf.LON_MAX, size=n*5)

        elevs = np.array([float(etopo[evar].sel(**{latk:la, lonk:lo}, method="nearest").values) for la,lo in zip(lats,lons)])
        ocean = elevs <= 0
        ol, oo = lats[ocean], lons[ocean]
        dists = _shore_km(tree, ol, oo)
        near = dists <= conf.MAX_SHORE_KM

        for la, lo in zip(ol[near], oo[near]):
            if len(good_la) >= n: break
            good_la.append(la)
            good_lo.append(lo)
            good_dt.append(rng.choice(dates))
        print("  absences: attempt %d, got %d/%d" % (attempt+1, len(good_la), n))

    etopo.close()
    df = pd.DataFrame({"decimalLatitude": good_la[:n], "decimalLongitude": good_lo[:n],
                        "eventDate": good_dt[:n], "target": 0, "species": ""})
    df["eventDate"] = pd.to_datetime(df["eventDate"], utc=True)
    return df.reset_index(drop=True)


def build_it():
    os.makedirs(conf.DATA_DIR, exist_ok=True)
    occ = pull_from_obis()
    occ.to_csv(conf.OCC_CSV, index=False)
    print("got %d occurrences" % len(occ))

    fake = generate_fakes(occ, ratio=conf.ABSENCE_RATIO)
    combined = pd.concat([occ, fake], ignore_index=True)
    combined = combined.sample(frac=1, random_state=conf.SEED).reset_index(drop=True)
    combined.to_csv(conf.COMBINED_CSV, index=False)
    print("combined: %d rows (%d pos, %d neg)" % (len(combined), (combined["target"]==1).sum(), (combined["target"]==0).sum()))
    return combined
