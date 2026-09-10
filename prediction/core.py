"""Fonctions partagées par les APIs d'entraînement et de prédiction."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = Path(os.getenv("TRAINING_DATA_PATH", BASE_DIR / "data" / "tp1-pedagogique-conso.csv"))
MODEL_DIR = Path(os.getenv("MODEL_DIR", BASE_DIR / "models"))
MODEL_PATH = MODEL_DIR / "consumption_model.joblib"
METADATA_PATH = MODEL_DIR / "consumption_model.metadata.json"
FEATURES = [
    "temperature",
    "jour_semaine",
    "heure",
    "est_weekend",
    "saison_automne",
    "saison_ete",
    "saison_hiver",
    "saison_printemps",
]


def season_from_month(month: int) -> str:
    if month in (12, 1, 2):
        return "hiver"
    if month in (3, 4, 5):
        return "printemps"
    if month in (6, 7, 8):
        return "ete"
    return "automne"


def build_features(timestamp: datetime, temperature: float) -> pd.DataFrame:
    """Construit exactement les variables utilisées par le modèle publié."""
    season = season_from_month(timestamp.month)
    values: dict[str, float | int] = {
        "temperature": temperature,
        "jour_semaine": timestamp.weekday(),
        "heure": timestamp.hour,
        "est_weekend": int(timestamp.weekday() >= 5),
    }
    values.update({f"saison_{name}": int(name == season) for name in ("automne", "ete", "hiver", "printemps")})
    return pd.DataFrame([values], columns=FEATURES)


def _prepare_training_data() -> tuple[pd.DataFrame, pd.Series]:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Jeu de données introuvable : {DATA_PATH}")

    dataframe = pd.read_csv(DATA_PATH, parse_dates=["date_heure"])
    required = {"date_heure", "temperature", "jour_semaine", "heure", "est_weekend", "mois", "consommation_mw"}
    missing = required.difference(dataframe.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {', '.join(sorted(missing))}")
    if dataframe[list(required)].isna().any().any():
        raise ValueError("Le jeu de données contient des valeurs manquantes.")

    dataframe = dataframe.sort_values("date_heure").copy()
    dataframe["saison"] = dataframe["mois"].map(season_from_month)
    for season in ("automne", "ete", "hiver", "printemps"):
        dataframe[f"saison_{season}"] = (dataframe["saison"] == season).astype(int)
    return dataframe[FEATURES], dataframe["consommation_mw"]


def train_and_publish_model() -> dict:
    """Entraîne sans fuite temporelle puis publie l'artefact et sa traçabilité."""
    features, target = _prepare_training_data()
    split_index = int(len(features) * 0.8)
    if split_index == 0 or split_index == len(features):
        raise ValueError("Le jeu de données ne permet pas de séparer apprentissage et test.")

    x_train, x_test = features.iloc[:split_index], features.iloc[split_index:]
    y_train, y_test = target.iloc[:split_index], target.iloc[split_index:]
    model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)

    trained_at = datetime.now(timezone.utc)
    version = f"rf-{trained_at.strftime('%Y%m%dT%H%M%SZ')}"
    metadata = {
        "model_version": version,
        "algorithm": "RandomForestRegressor",
        "trained_at": trained_at.isoformat(),
        "training_rows": len(x_train),
        "test_rows": len(x_test),
        "metrics": {
            "mae_mw": round(float(mean_absolute_error(y_test, predictions)), 3),
            "mape_percent": round(float(mean_absolute_percentage_error(y_test, predictions) * 100), 3),
        },
        "features": FEATURES,
        "training_data": str(DATA_PATH),
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def load_published_model() -> tuple[RandomForestRegressor, dict]:
    if not MODEL_PATH.is_file() or not METADATA_PATH.is_file():
        raise FileNotFoundError("Aucun modèle publié. Appelez d'abord POST /train sur le service training.")
    model = joblib.load(MODEL_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return model, metadata
