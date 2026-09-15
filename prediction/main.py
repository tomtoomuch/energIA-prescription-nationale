from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import pandas as pd

from prediction.etl.dataframe import creer_dataframe

app = FastAPI(title="API de Prédiction - Modèle régressif")

# Charger le modèle de régression pré-entraîné au démarrage
model = joblib.load("./modeles/modele_consommation.joblib")

# Définir le format des données d'entrée
class PredictionInput(BaseModel):
    feature_1: float
    feature_2: float
    feature_3: float

@app.post("/predict")
def predict(data: PredictionInput):
    # Convertir les données reçues en DataFrame pour le modèle
    input_df = pd.DataFrame([data.model_dump()])
    
    # Faire la prédiction (retourne un tableau, ex: [24.5])
    prediction = model.predict(input_df)
    
    # Retourner le résultat sous forme de float
    return {"prediction": float(prediction[0])}