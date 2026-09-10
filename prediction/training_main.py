"""API interne qui entraîne et publie le modèle de consommation."""

import os

from fastapi import Depends, FastAPI, Header, HTTPException

try:  # exécution par uvicorn dans le conteneur
    from core import DATA_PATH, train_and_publish_model
except ModuleNotFoundError:  # import comme package lors des tests
    from prediction.core import DATA_PATH, train_and_publish_model


app = FastAPI(title="EnergIA Training", version="1.0.0")
SECURITY_TOKEN = os.getenv("SECURITY_TOKEN")


def verify_api_key(x_api_key: str = Header(alias="x-api-key")) -> None:
    if not SECURITY_TOKEN or x_api_key != SECURITY_TOKEN:
        raise HTTPException(status_code=401, detail="Clé API invalide")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "training", "data_available": DATA_PATH.is_file()}


@app.post("/train", dependencies=[Depends(verify_api_key)])
def train() -> dict:
    try:
        metadata = train_and_publish_model()
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"status": "published", **metadata}
