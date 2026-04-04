from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import random


app = FastAPI(
    title="Seal Presence Prediction API",
    description="Predicts the probability of seal presence at a given location.",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default dev port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class PredictRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, example=57.4)
    longitude: float = Field(..., ge=-180, le=180, example=-153.2)
    water_temp: float | None = Field(None, description="Sea surface temperature in °C", example=8.3)


class PredictResponse(BaseModel):
    latitude: float
    longitude: float
    water_temp: float | None
    seal_probability: float = Field(..., description="Predicted probability of seal presence (0–1)")
    seal_present: bool = Field(..., description="True if probability exceeds decision threshold")
    model_version: str



# TODO: Replace this function with your teammate's trained LogisticRegression
#       model once it's ready. Suggested interface:
#
#   import joblib
#   model = joblib.load("seal_lr_model.pkl")
#
#   def run_model(latitude, longitude, water_temp):
#       features = [[latitude, longitude, water_temp or 0.0]]
#       probability = model.predict_proba(features)[0][1]
#       return round(float(probability), 4)

DECISION_THRESHOLD = 0.50   # classify as "present" if probability >= this value

def placeholder_model(latitude: float, longitude: float, water_temp: float | None) -> float:
    """
    Dummy stand-in for the Logistic Regression model.

    Returns a fake but plausible probability so the frontend and API
    contract can be developed in parallel before the real model is ready.
    """
    # Seed with rounded coords so the same location always returns the
    # same value during a single session — makes frontend testing easier.
    random.seed(round(latitude, 1) + round(longitude, 1))
    base_prob = random.uniform(0.55, 0.95)   # hardcoded "optimistic" range

    # Tiny water-temp nudge so the field has *some* visible effect
    if water_temp is not None:
        base_prob += (water_temp - 10) * 0.005

    return round(min(max(base_prob, 0.0), 1.0), 4)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def health_check():
    """Quick liveness probe."""
    return {"status": "ok", "message": "Seal Prediction API is running."}


@app.post("/api/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(request: PredictRequest):
    """
    Accept location (and optional water temperature) and return the
    predicted probability of seal presence.
    """
    try:
        probability = placeholder_model(
            latitude=request.latitude,
            longitude=request.longitude,
            water_temp=request.water_temp,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model inference failed: {exc}")

    return PredictResponse(
        latitude=request.latitude,
        longitude=request.longitude,
        water_temp=request.water_temp,
        seal_probability=probability,
        seal_present=probability >= DECISION_THRESHOLD,
        model_version="placeholder-0.1.0",   # bump this when the real model lands
    )


# ---------------------------------------------------------------------------
# Entry-point (for `python main.py` during local dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)