import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DOSSIER = Path(__file__).resolve().parent
MODELE = joblib.load(DOSSIER / "modeles" / "modele_consommation.joblib")
INFORMATIONS = json.loads(
    (DOSSIER / "modeles" / "modele_consommation.json").read_text(
        encoding="utf-8"
    )
)

app = FastAPI(title="Prédiction EnergIA")


class EntreePrediction(BaseModel):
    libelle_region: str
    mois: int = Field(ge=1, le=12)
    jour_semaine: int = Field(ge=0, le=6)
    heure_locale: int = Field(ge=0, le=23)
    minute: int
    ferie: int = Field(ge=0, le=1)
    vacances_scolaires: int = Field(ge=0, le=1)


@app.get("/health")
def health():
    return {"status": "ok", "regions": len(INFORMATIONS["regions"])}


@app.post("/predict")
def predict(entree: EntreePrediction):
    if entree.libelle_region not in INFORMATIONS["regions"]:
        raise HTTPException(422, "Région inconnue")

    if entree.minute not in (0, 15, 30, 45):
        raise HTTPException(422, "Minute attendue : 00, 15, 30 ou 45")

    valeurs = entree.model_dump()
    tableau = pd.DataFrame(
        [valeurs],
        columns=INFORMATIONS["colonnes"],
    )
    estimation = float(MODELE.predict(tableau)[0])

    return {
        "consommation_predite": estimation,
        "origine": "estimation_modele_sklearn",
        "precision_15min_evaluee": INFORMATIONS["precision_15min_evaluee"],
    }
