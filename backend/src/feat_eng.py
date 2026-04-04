import numpy as np
import pandas as pd
import conf

def add_feats(df):
    df = df.copy()
    for f in conf.env_feats:
        df[f + "_squared"] = df[f] ** 2
    df["abs_latitude"] = df["decimalLatitude"].abs()
    df["sst_x_distance_to_shore_km"] = df["sst"] * df["distance_to_shore_km"]
    df["sst_x_depth"] = df["sst"] * df["depth"]
    df["depth_x_wind_speed_10m"] = df["depth"] * df["wind_speed_10m"]
    df["sst_x_month_cos"] = df["sst"] * df["month_cos"]
    return df
