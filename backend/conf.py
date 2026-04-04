import os

basedir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(basedir, "data")
MODELS_DIR = os.path.join(basedir, "models")
RESULTS_DIR = os.path.join(basedir, "results")

TAXON = "Phocidae"
N_RECORDS = 50000
PAGE_SZ = 5000
MIN_DATE = "1982-01-01"
ABSENCE_RATIO = 1.0
MAX_SHORE_KM = 500.0

LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0

ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap"

ETOPO_DS = "etopo180"
ETOPO_STRIDE = 8
ETOPO_FILE = os.path.join(DATA_DIR, "etopo_global.nc")

SST_DS = "ncdcOisst21Agg"
SST_STRIDE = 4
SST_DIR = os.path.join(DATA_DIR, "sst_cache")

UWND_URL = "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/surface/uwnd.mon.mean.nc"
VWND_URL = "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/surface/vwnd.mon.mean.nc"
WIND_FILE = os.path.join(DATA_DIR, "ncep_wind_speed.nc")

env_feats = ["depth", "slope", "sst", "wind_speed_10m", "distance_to_shore_km"]
season_feats = ["month_sin", "month_cos"]
extra_feats = ["abs_latitude"]
interaction_feats = [
    "sst_x_distance_to_shore_km",
    "sst_x_depth",
    "depth_x_wind_speed_10m",
    "sst_x_month_cos",
]
base_feats = env_feats + season_feats + extra_feats
sq_feats = [x + "_squared" for x in env_feats]
ALL_FEATS = base_feats + sq_feats + interaction_feats

MIN_SPECIES_COUNT = 30
TOP_K = 5

TEST_SZ = 0.2
SEED = 16111719
MODEL_PKL = os.path.join(MODELS_DIR, "seal_sdm_model.pkl")
SCALER_PKL = os.path.join(MODELS_DIR, "seal_scaler.pkl")
SPECIES_MODEL_PKL = os.path.join(MODELS_DIR, "species_model.pkl")
SPECIES_SCALER_PKL = os.path.join(MODELS_DIR, "species_scaler.pkl")
SPECIES_CLASSES_PKL = os.path.join(MODELS_DIR, "species_classes.pkl")

BATHY_CSV = os.path.join(DATA_DIR, "bathymetry.csv")
OCC_CSV = os.path.join(DATA_DIR, "occurrences.csv")
COMBINED_CSV = os.path.join(DATA_DIR, "combined.csv")
RAW_CSV = os.path.join(DATA_DIR, "features_raw.csv")
FINAL_CSV = os.path.join(DATA_DIR, "final_dataset.csv")

EQ_TXT = os.path.join(RESULTS_DIR, "equation.txt")
RESULTS_TXT = os.path.join(RESULTS_DIR, "results.txt")
ROC_S1_PNG = os.path.join(RESULTS_DIR, "roc_stage1.png")
ROC_S2_PNG = os.path.join(RESULTS_DIR, "roc_stage2.png")
CONFUSION_PNG = os.path.join(RESULTS_DIR, "confusion_species.png")
FEAT_IMP_PNG = os.path.join(RESULTS_DIR, "feature_importance.png")
