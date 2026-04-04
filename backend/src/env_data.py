import os, time
import numpy as np
import pandas as pd
import requests
import xarray as xr
from requests.adapters import HTTPAdapter
from scipy.spatial import KDTree
from urllib3.util.retry import Retry
import conf


def _mk_session():
    s = requests.Session()
    r = Retry(total=5, backoff_factor=1.0, status_forcelist=[500,502,503,504])
    s.mount("https://", HTTPAdapter(max_retries=r))
    s.mount("http://", HTTPAdapter(max_retries=r))
    return s

def _griddap(ds, var, constraints):
    return conf.ERDDAP + "/griddap/" + ds + ".nc?" + var + constraints


def grab_etopo():
    if os.path.exists(conf.ETOPO_FILE):
        return xr.open_dataset(conf.ETOPO_FILE)
    s = conf.ETOPO_STRIDE
    url = _griddap(conf.ETOPO_DS, "altitude",
        "[(%s):%d:(%s)][(%s):%d:(%s)]" % (conf.LAT_MIN, s, conf.LAT_MAX, conf.LON_MIN, s, conf.LON_MAX))
    resp = _mk_session().get(url, timeout=300)
    resp.raise_for_status()
    os.makedirs(conf.DATA_DIR, exist_ok=True)
    with open(conf.ETOPO_FILE, "wb") as fh:
        fh.write(resp.content)
    return xr.open_dataset(conf.ETOPO_FILE)


def _calc_slope(ds):
    evar = list(ds.data_vars)[0]
    elev = ds[evar].values
    latk = "latitude" if "latitude" in ds.dims else "lat"
    lonk = "longitude" if "longitude" in ds.dims else "lon"
    lats = ds[latk].values
    lons = ds[lonk].values

    dy = np.abs(np.mean(np.diff(lats))) * 111320
    dx_per = np.abs(np.mean(np.diff(lons))) * 111320 * np.cos(np.radians(lats))
    dx_per = np.maximum(dx_per, 1.0)
    dx_2d = np.broadcast_to(dx_per[:, np.newaxis], elev.shape)

    gy, gx = np.gradient(elev)
    gy = gy / dy
    gx = gx / dx_2d

    s = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
    return xr.DataArray(s, dims=[latk, lonk], coords={latk: lats, lonk: lons})


def _ll2xyz(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.cos(la)*np.cos(lo), np.cos(la)*np.sin(lo), np.sin(la)

def _get_shore_dist(ds, df):
    evar = list(ds.data_vars)[0]
    latk = "latitude" if "latitude" in ds.dims else "lat"
    lonk = "longitude" if "longitude" in ds.dims else "lon"
    lg, lo = np.meshgrid(ds[latk].values, ds[lonk].values, indexing="ij")
    mask = ds[evar].values >= 0
    x, y, z = _ll2xyz(lg[mask], lo[mask])
    tree = KDTree(np.column_stack([x,y,z]))
    qx, qy, qz = _ll2xyz(df["decimalLatitude"].values, df["decimalLongitude"].values)
    chord, _ = tree.query(np.column_stack([qx,qy,qz]))
    return 6371.0 * 2 * np.arcsin(np.clip(chord/2, 0, 1))


def _process_bathy(df):
    if os.path.exists(conf.BATHY_CSV):
        cached = pd.read_csv(conf.BATHY_CSV)
        if len(cached) == len(df):
            df = df.copy()
            for c in ["depth","slope","distance_to_shore_km"]:
                df[c] = cached[c].values
            print("  bathy from cache (%d rows)" % len(df))
            return df

    ds = grab_etopo()
    evar = list(ds.data_vars)[0]
    latk = "latitude" if "latitude" in ds.dims else "lat"
    lonk = "longitude" if "longitude" in ds.dims else "lon"
    sg = _calc_slope(ds)

    depths, slopes = [], []
    for _, row in df.iterrows():
        sel = {latk: row["decimalLatitude"], lonk: row["decimalLongitude"]}
        d = float(ds[evar].sel(**sel, method="nearest").values)
        s = float(sg.sel(**sel, method="nearest").values)
        depths.append(-d if d < 0 else 0.0)
        slopes.append(s)

    df = df.copy()
    df["depth"] = depths
    df["slope"] = slopes
    df["distance_to_shore_km"] = _get_shore_dist(ds, df)
    ds.close()

    pd.DataFrame({k: df[k] for k in ["depth","slope","distance_to_shore_km"]}).to_csv(conf.BATHY_CSV, index=False)
    print("  bathy done, depth [%.0f, %.0f]" % (df["depth"].min(), df["depth"].max()))
    return df


def _lon360(lon):
    return lon % 360

def _sst_path(yr, mo):
    return os.path.join(conf.SST_DIR, "sst_%d_%02d.nc" % (yr, mo))

def _grab_sst_month(yr, mo, sess):
    path = _sst_path(yr, mo)
    if os.path.exists(path):
        ds = xr.open_dataset(path); ds.load(); ds.close()
        return ds
    s = conf.SST_STRIDE
    url = _griddap(conf.SST_DS, "sst",
        "[(%d-%02d-15T12:00:00Z)][(0.0)][(-89.875):%d:(89.875)][(0.125):%d:(359.875)]" % (yr, mo, s, s))
    tmp = path + ".tmp"
    try:
        r = sess.get(url, timeout=180); r.raise_for_status()
        with open(tmp, "wb") as fh: fh.write(r.content)
        os.rename(tmp, path)
        ds = xr.open_dataset(path); ds.load(); ds.close()
        return ds
    except Exception:
        return None
    finally:
        if os.path.exists(tmp): os.remove(tmp)


def _process_sst(df):
    os.makedirs(conf.SST_DIR, exist_ok=True)
    df = df.copy()
    df["_ym"] = df["eventDate"].dt.to_period("M")
    months = sorted(df["_ym"].unique())
    print("  sst: %d months to load" % len(months))

    sess = _mk_session()
    lookup = {}
    for i, ym in enumerate(months):
        yr, mo = ym.year, ym.month
        ds = _grab_sst_month(yr, mo, sess)
        if ds is not None:
            var = "sst" if "sst" in ds.data_vars else list(ds.data_vars)[0]
            arr = ds[var].squeeze(drop=True)
            latd = "latitude" if "latitude" in arr.dims else "lat"
            lond = "longitude" if "longitude" in arr.dims else "lon"
            arr = arr.sortby(latd).sortby(lond)
            arr = arr.interpolate_na(dim=latd, method="nearest")
            arr = arr.interpolate_na(dim=lond, method="nearest")
            lookup[(yr, mo)] = arr
        time.sleep(0.02)

    print("  sst: got %d/%d grids" % (len(lookup), len(months)))

    if not lookup:
        df["sst"] = np.nan
        df.drop(columns=["_ym"], inplace=True)
        return df

    samp = next(iter(lookup.values()))
    latv = "latitude" if "latitude" in samp.dims else "lat"
    lonv = "longitude" if "longitude" in samp.dims else "lon"

    vals = []
    for _, row in df.iterrows():
        k = (row["_ym"].year, row["_ym"].month)
        if k in lookup:
            v = float(lookup[k].sel(**{latv: row["decimalLatitude"], lonv: _lon360(row["decimalLongitude"])}, method="nearest").values)
            vals.append(v)
        else:
            vals.append(np.nan)

    df["sst"] = vals
    nans = df["sst"].isna().sum()
    df["sst"] = df["sst"].fillna(-1.8)
    print("  sst done, filled %d NaN, range [%.1f, %.1f]" % (nans, df["sst"].min(), df["sst"].max()))
    df.drop(columns=["_ym"], inplace=True)
    return df


def _load_wind():
    if os.path.exists(conf.WIND_FILE):
        return xr.open_dataset(conf.WIND_FILE)

    print("  downloading NCEP wind (this takes a minute)...")
    uds = xr.open_dataset(conf.UWND_URL)
    vds = xr.open_dataset(conf.VWND_URL)
    yrs = sorted(set(pd.to_datetime(uds.time.values).year))

    chunks = []
    for yr in yrs:
        sl = slice("%d-01-01" % yr, "%d-12-31" % yr)
        u = uds["uwnd"].sel(time=sl).values
        v = vds["vwnd"].sel(time=sl).values
        chunks.append(np.sqrt(u**2 + v**2))

    wspd = np.concatenate(chunks, axis=0)
    ds = xr.Dataset({"wind_speed": (("time","lat","lon"), wspd)},
        coords={"time": uds.time.values, "lat": uds.lat.values, "lon": uds.lon.values})
    uds.close(); vds.close()

    os.makedirs(conf.DATA_DIR, exist_ok=True)
    ds.to_netcdf(conf.WIND_FILE)
    print("  wind cached (%d MB)" % int(os.path.getsize(conf.WIND_FILE)/1e6))
    return ds


def _process_wind(df):
    ds = _load_wind()
    df = df.copy()
    df["_ym"] = df["eventDate"].dt.to_period("M")
    months = sorted(df["_ym"].unique())

    warr = ds["wind_speed"]
    wlookup = {}
    for ym in months:
        try:
            snap = warr.sel(time="%d-%02d-01" % (ym.year, ym.month), method="nearest").squeeze(drop=True)
            wlookup[(ym.year, ym.month)] = snap.sortby("lat").sortby("lon")
        except Exception:
            pass

    vals = []
    for _, row in df.iterrows():
        k = (row["_ym"].year, row["_ym"].month)
        if k in wlookup:
            v = float(wlookup[k].sel(lat=row["decimalLatitude"], lon=_lon360(row["decimalLongitude"]), method="nearest").values)
            vals.append(v)
        else:
            vals.append(np.nan)

    df["wind_speed_10m"] = vals
    df.drop(columns=["_ym"], inplace=True)
    ds.close()

    nans = df["wind_speed_10m"].isna().sum()
    if nans > 0:
        med = df["wind_speed_10m"].median()
        df["wind_speed_10m"] = df["wind_speed_10m"].fillna(med)
    print("  wind done, range [%.1f, %.1f] m/s" % (df["wind_speed_10m"].min(), df["wind_speed_10m"].max()))
    return df


def _tack_on_timeofyear(df):
    df = df.copy()
    mo = df["eventDate"].dt.month
    df["month_sin"] = np.sin(2 * np.pi * mo / 12)
    df["month_cos"] = np.cos(2 * np.pi * mo / 12)
    return df


def run_backfill(df):
    print("backfilling %d rows..." % len(df))
    os.makedirs(conf.DATA_DIR, exist_ok=True)
    df = _process_bathy(df)
    df = _process_sst(df)
    df = _process_wind(df)
    df = _tack_on_timeofyear(df)

    before = len(df)
    drop_cols = conf.env_feats + conf.season_feats
    df = df.dropna(subset=drop_cols).reset_index(drop=True)

    df.to_csv(conf.RAW_CSV, index=False)
    return df
