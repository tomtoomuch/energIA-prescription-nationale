"""API interne de prédiction de consommation électrique."""

from datetime import datetime, timezone
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

try:  # exécution par uvicorn dans le conteneur
    from core import build_features, load_published_model
except ModuleNotFoundError:  # import comme package lors des tests
    from prediction.core import build_features, load_published_model


app = FastAPI(title="EnergIA Prediction", version="1.0.0")
SECURITY_TOKEN = os.getenv("SECURITY_TOKEN")


class PredictionRequest(BaseModel):
    timestamp: datetime
    temperature: float = Field(ge=-60, le=60)


def verify_api_key(x_api_key: str = Header(alias="x-api-key")) -> None:
    if not SECURITY_TOKEN or x_api_key != SECURITY_TOKEN:
        raise HTTPException(status_code=401, detail="Clé API invalide")


@app.get("/health")
def health() -> dict:
    try:
        _, metadata = load_published_model()
        return {"status": "ok", "service": "prediction", "model_version": metadata["model_version"]}
    except FileNotFoundError:
        return {"status": "waiting_for_model", "service": "prediction"}


@app.get("/model", dependencies=[Depends(verify_api_key)])
def model_metadata() -> dict:
    try:
        _, metadata = load_published_model()
        return metadata
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/predictions", dependencies=[Depends(verify_api_key)])
def predict(request: PredictionRequest) -> dict:
    try:
        model, metadata = load_published_model()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    prediction_mw = float(model.predict(build_features(request.timestamp, request.temperature))[0])
    return {
        "prediction_mw": round(prediction_mw, 2),
        "timestamp": request.timestamp.astimezone(timezone.utc).isoformat() if request.timestamp.tzinfo else request.timestamp.isoformat(),
        "temperature": request.temperature,
        "model_version": metadata["model_version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
