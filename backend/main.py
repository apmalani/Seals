import os
import sys
from contextlib import asynccontextmanager

_BACKEND = os.path.dirname(os.path.abspath(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

import conf
import geocoder_util
from src.predict_point import LandPointError, build_feature_matrix

_models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    for key, path in [
        ("s1", conf.MODEL_PKL),
        ("sc1", conf.SCALER_PKL),
        ("s2", conf.SPECIES_MODEL_PKL),
        ("sc2", conf.SPECIES_SCALER_PKL),
        ("cls", conf.SPECIES_CLASSES_PKL),
    ]:
        if not os.path.isfile(path):
            raise RuntimeError("missing model file %s (train pipeline first)" % path)
        _models[key] = joblib.load(path)
    iho = conf.resolve_iho_shapefile()
    if iho:
        geocoder_util.set_iho_shapefile(iho)
    yield
    _models.clear()


app = FastAPI(
    title="Seal Presence Prediction API",
    description="OBIS-trained SDM: environmental backfill + two-stage logistic regression.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DECISION_THRESHOLD = 0.5
# Minimum P(species | seal) to include in the ranked list (drops sub-1% tails / 0.0% UI noise).
MIN_SPECIES_DISPLAY_PROB = 0.01
MODEL_VERSION = "sdm-two-stage-1.0"


class PredictRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, example=-64.5)
    longitude: float = Field(..., ge=-180, le=180, example=-62.5)
    month: int = Field(..., ge=1, le=12, description="Calendar month (1-12)")
    day: int = Field(conf.API_REF_DAY, ge=1, le=31, description="Day of month; SST/wind use monthly fields")


class SpeciesEntry(BaseModel):
    species: str = Field(..., description="Scientific name (model class label)")
    common_name: str
    probability: float = Field(..., description="P(species | seal), Stage 2")
    probability_joint: float = Field(..., description="P(seal) * P(species | seal)")


class PredictionCovariates(BaseModel):
    """Environmental and engineered inputs used for the SDM (same order as training)."""

    latitude: float
    longitude: float
    month: int
    day: int
    reference_year: int = Field(..., description="Calendar year used for SST / wind layers")
    bathy_elevation_m: float = Field(
        ...,
        description="ETOPO elevation (m): negative = ocean floor below sea level, positive = land",
    )
    ocean_depth_m: float = Field(
        ...,
        description="Positive depth below sea surface (m); 0 on land",
    )
    seafloor_slope: float
    distance_to_shore_km: float = Field(
        ...,
        description="Great-circle distance to nearest ETOPO ocean cell (km)",
    )
    sea_surface_temperature_c: Optional[float] = Field(
        None,
        description="Monthly SST (°C) at nearest grid; omitted for land points",
    )
    wind_speed_10m: Optional[float] = Field(
        None,
        description="NCEP-derived 10 m wind speed at nearest month/grid; omitted for land",
    )
    month_sin: float
    month_cos: float
    abs_latitude: float
    note: Optional[str] = None


class PredictResponse(BaseModel):
    latitude: float
    longitude: float
    location_name: str = Field(..., description="IHO sea/ocean or Nominatim place name")
    month: int
    day: int
    reference_year_used: int
    covariates: PredictionCovariates
    seal_probability: float
    seal_present: bool
    species_top5: list[SpeciesEntry] = Field(
        ...,
        description="Up to TOP_K species with P(species|seal) >= 1%, descending",
    )
    species_probabilities_conditional: bool = True
    warnings: list[str]
    model_version: str


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Seal Prediction API is running."}


@app.post("/api/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(request: PredictRequest):
    """
    Backfill bathy/SST/wind for lat/lon and month (year fixed in config for SST/wind).
    Returns covariates, P(seal), and up to TOP_K Stage-2 species (conditional on seal),
    each with P(species|seal) at least 1%, in descending order.

    Ocean-only: if ETOPO indicates land (elevation >= 0), returns **422** with
    `location_name` and `covariates` but does not run inference.
    """
    try:
        X, warns, covariates = build_feature_matrix(
            request.latitude,
            request.longitude,
            request.month,
            request.day,
        )
    except LandPointError as exc:
        try:
            location_name = geocoder_util.get_location_name(
                request.latitude, request.longitude
            )
        except Exception:
            location_name = "Unknown Location"
        raise HTTPException(
            status_code=422,
            detail={
                "error": "point_on_land",
                "message": "Prediction is only defined for ocean points (ETOPO bathymetry shows land).",
                "location_name": location_name,
                "covariates": exc.covariates,
            },
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="feature build failed: %s" % exc)

    try:
        location_name = geocoder_util.get_location_name(
            request.latitude, request.longitude
        )
    except Exception:
        location_name = "Unknown Location"

    sc1 = _models["sc1"]
    s1 = _models["s1"]
    sc2 = _models["sc2"]
    s2 = _models["s2"]
    classes = list(_models["cls"])

    Xs1 = sc1.transform(X)
    p_seal = float(s1.predict_proba(Xs1)[0, 1])

    Xs2 = sc2.transform(X)
    p_sp = s2.predict_proba(Xs2)[0]
    order = np.argsort(p_sp)[::-1]
    top = []
    for i in order:
        pc = float(p_sp[i])
        if pc < MIN_SPECIES_DISPLAY_PROB:
            continue
        if len(top) >= conf.TOP_K:
            break
        sci = str(classes[i])
        top.append(
            SpeciesEntry(
                species=sci,
                common_name=conf.species_common_name(sci),
                probability=round(pc, 6),
                probability_joint=round(p_seal * pc, 6),
            )
        )

    cov_model = PredictionCovariates(**covariates)

    return PredictResponse(
        latitude=request.latitude,
        longitude=request.longitude,
        location_name=location_name,
        month=request.month,
        day=request.day,
        reference_year_used=conf.API_REF_YEAR,
        covariates=cov_model,
        seal_probability=round(p_seal, 6),
        seal_present=p_seal >= DECISION_THRESHOLD,
        species_top5=top,
        species_probabilities_conditional=True,
        warnings=warns,
        model_version=MODEL_VERSION,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
