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

import conf
import geocoder_util
from src.predict_point import build_feature_matrix

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
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DECISION_THRESHOLD = 0.5
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


class PredictResponse(BaseModel):
    latitude: float
    longitude: float
    location_name: str = Field(..., description="IHO sea/ocean or Nominatim place name")
    month: int
    day: int
    reference_year_used: int
    seal_probability: float
    seal_present: bool
    species_top5: list[SpeciesEntry]
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
    Returns P(seal) and top-5 species from Stage 2 (conditional on seal).
    """
    try:
        X, warns = build_feature_matrix(
            request.latitude,
            request.longitude,
            request.month,
            request.day,
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
    order = np.argsort(p_sp)[::-1][: conf.TOP_K]
    top = []
    for i in order:
        pc = float(p_sp[i])
        sci = str(classes[i])
        top.append(
            SpeciesEntry(
                species=sci,
                common_name=conf.species_common_name(sci),
                probability=round(pc, 6),
                probability_joint=round(p_seal * pc, 6),
            )
        )

    return PredictResponse(
        latitude=request.latitude,
        longitude=request.longitude,
        location_name=location_name,
        month=request.month,
        day=request.day,
        reference_year_used=conf.API_REF_YEAR,
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
