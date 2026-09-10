# Tutoriel — microservices de prévision EnergIA

Ce document décrit la reprise de l'exercice sous forme de deux services :

- **training** entraîne et publie le modèle ;
- **prediction** charge le modèle publié et prédit la consommation.

Le CSV entraîne un modèle de régression ; il ne sert pas à entraîner le LLM Ollama.

## 1. Sauvegarder les fichiers

~~~powershell
Copy-Item prediction\main.py prediction\orig_main.py
Copy-Item prediction\requirements.txt prediction\orig_requirements.txt
Copy-Item prediction\dockerfile prediction\orig_dockerfile
Copy-Item prediction\BRIEF.md prediction\orig_BRIEF.md
~~~

## 2. Dépendances

Contenu de \`requirements.txt\` :

~~~txt
pandas
scikit-learn
joblib
fastapi
uvicorn
python-dotenv==1.0.1
~~~

## 3. Code partagé — \`core.py\`

~~~python
import json, os
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
FEATURES = ["temperature", "jour_semaine", "heure", "est_weekend", "saison_automne", "saison_ete", "saison_hiver", "saison_printemps"]

def season_from_month(month):
    if month in (12, 1, 2): return "hiver"
    if month in (3, 4, 5): return "printemps"
    if month in (6, 7, 8): return "ete"
    return "automne"

def build_features(timestamp, temperature):
    season = season_from_month(timestamp.month)
    values = {
        "temperature": temperature, "jour_semaine": timestamp.weekday(),
        "heure": timestamp.hour, "est_weekend": int(timestamp.weekday() >= 5),
    }
    values.update({f"saison_{name}": int(name == season) for name in ("automne", "ete", "hiver", "printemps")})
    return pd.DataFrame([values], columns=FEATURES)

def train_and_publish_model():
    df = pd.read_csv(DATA_PATH, parse_dates=["date_heure"]).sort_values("date_heure")
    df["saison"] = df["mois"].map(season_from_month)
    for season in ("automne", "ete", "hiver", "printemps"):
        df[f"saison_{season}"] = (df["saison"] == season).astype(int)
    split = int(len(df) * .8)
    model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)
    model.fit(df[FEATURES].iloc[:split], df["consommation_mw"].iloc[:split])
    predicted = model.predict(df[FEATURES].iloc[split:])
    actual = df["consommation_mw"].iloc[split:]
    trained_at = datetime.now(timezone.utc)
    metadata = {
        "model_version": "rf-" + trained_at.strftime("%Y%m%dT%H%M%SZ"),
        "trained_at": trained_at.isoformat(),
        "metrics": {"mae_mw": float(mean_absolute_error(actual, predicted)), "mape_percent": float(mean_absolute_percentage_error(actual, predicted) * 100)},
        "features": FEATURES,
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata

def load_published_model():
    if not MODEL_PATH.is_file() or not METADATA_PATH.is_file():
        raise FileNotFoundError("Aucun modèle publié.")
    return joblib.load(MODEL_PATH), json.loads(METADATA_PATH.read_text(encoding="utf-8"))
~~~

## 4. Service d'entraînement — \`training_main.py\`

~~~python
import os
from fastapi import Depends, FastAPI, Header, HTTPException
from core import DATA_PATH, train_and_publish_model

app = FastAPI(title="EnergIA Training")
TOKEN = os.getenv("SECURITY_TOKEN")

def verify(x_api_key: str = Header(alias="x-api-key")):
    if not TOKEN or x_api_key != TOKEN:
        raise HTTPException(401, "Clé API invalide")

@app.get("/health")
def health():
    return {"status": "ok", "data_available": DATA_PATH.is_file()}

@app.post("/train", dependencies=[Depends(verify)])
def train():
    try:
        return {"status": "published", **train_and_publish_model()}
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(422, str(error))
~~~

## 5. Service de prédiction — \`main.py\`

~~~python
import os
from datetime import datetime
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from core import build_features, load_published_model

app = FastAPI(title="EnergIA Prediction")
TOKEN = os.getenv("SECURITY_TOKEN")

class PredictionRequest(BaseModel):
    timestamp: datetime
    temperature: float = Field(ge=-60, le=60)

def verify(x_api_key: str = Header(alias="x-api-key")):
    if not TOKEN or x_api_key != TOKEN:
        raise HTTPException(401, "Clé API invalide")

@app.get("/health")
def health():
    try:
        _, meta = load_published_model()
        return {"status": "ok", "model_version": meta["model_version"]}
    except FileNotFoundError:
        return {"status": "waiting_for_model"}

@app.post("/predictions", dependencies=[Depends(verify)])
def predict(request: PredictionRequest):
    try:
        model, meta = load_published_model()
    except FileNotFoundError as error:
        raise HTTPException(503, str(error))
    value = float(model.predict(build_features(request.timestamp, request.temperature))[0])
    return {"prediction_mw": round(value, 2), "model_version": meta["model_version"]}
~~~

## 6. Docker et volume partagé

Créer \`dockerfile.training\` :

~~~dockerfile
FROM python:3.12-slim
WORKDIR /prediction
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8005
CMD ["uvicorn", "training_main:app", "--host", "0.0.0.0", "--port", "8005"]
~~~

Le Dockerfile de prédiction doit lancer :

~~~dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
~~~

Dans Compose, partager le volume :

~~~yaml
services:
  training:
    build: { context: ./prediction, dockerfile: dockerfile.training }
    volumes: [prediction-models:/models]
  prediction:
    build: { context: ./prediction, dockerfile: dockerfile }
    volumes: [prediction-models:/models:ro]
volumes:
  prediction-models:
~~~

## 7. Tester

~~~powershell
docker compose up --build training prediction
Invoke-RestMethod -Method Post http://localhost:8005/train -Headers @{"x-api-key"=$env:SECURITY_TOKEN}
~~~

Puis envoyer à \`POST /predictions\` :

~~~json
{ "timestamp": "2025-03-05T18:00:00+01:00", "temperature": 7.5 }
~~~

Le résultat contient la consommation estimée et la version du modèle. En production, faire passer ces appels par la gateway et ne jamais exposer \`SECURITY_TOKEN\` au navigateur.
