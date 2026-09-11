import json
from datetime import date, timedelta
from pathlib import Path

import requests


# ---------- Dossiers et fichiers ----------

RACINE_PROJET = Path(__file__).resolve().parent.parent
DOSSIER_DATA = RACINE_PROJET / "data"

ANNEE = 2026

FICHIER_ELECTRICITE = DOSSIER_DATA / "eco2mix-regional.json"
FICHIER_METEO = DOSSIER_DATA / "meteo-regions.json"
FICHIER_CALENDRIER = DOSSIER_DATA / f"calendrier-{ANNEE}.json"
FICHIER_VACANCES = DOSSIER_DATA / "vacances-scolaires-regions.json"


# ---------- URL des API ----------

URL_API_ELECTRICITE = (
    "https://odre.opendatasoft.com/api/records/1.0/search/"
)

URL_API_METEO = "https://archive-api.open-meteo.com/v1/archive"

URL_API_VACANCES = (
    "https://data.education.gouv.fr/api/explore/v2.1/"
    "catalog/datasets/fr-en-calendrier-scolaire/exports/json"
)


# ---------- Points météo des régions ----------

# Code INSEE, région, ville de référence, latitude, longitude
REGIONS = [
    ("11", "Île-de-France", "Paris", 48.8566, 2.3522),
    ("24", "Centre-Val de Loire", "Orléans", 47.9029, 1.9093),
    ("27", "Bourgogne-Franche-Comté", "Dijon", 47.3220, 5.0415),
    ("28", "Normandie", "Rouen", 49.4432, 1.0993),
    ("32", "Hauts-de-France", "Lille", 50.6292, 3.0573),
    ("44", "Grand Est", "Strasbourg", 48.5734, 7.7521),
    ("52", "Pays de la Loire", "Nantes", 47.2184, -1.5536),
    ("53", "Bretagne", "Rennes", 48.1173, -1.6778),
    ("75", "Nouvelle-Aquitaine", "Bordeaux", 44.8378, -0.5792),
    ("76", "Occitanie", "Toulouse", 43.6047, 1.4442),
    ("84", "Auvergne-Rhône-Alpes", "Lyon", 45.7640, 4.8357),
    ("93", "Provence-Alpes-Côte d'Azur", "Marseille", 43.2965, 5.3698),
]


# ---------- Correspondance académies / régions ----------

REGIONS_ACADEMIES = {
    "Île-de-France": ["Paris", "Créteil", "Versailles"],
    "Centre-Val de Loire": ["Orléans-Tours"],
    "Bourgogne-Franche-Comté": ["Besançon", "Dijon"],
    "Normandie": ["Normandie", "Caen", "Rouen"],
    "Hauts-de-France": ["Amiens", "Lille"],
    "Grand Est": ["Nancy-Metz", "Reims", "Strasbourg"],
    "Pays de la Loire": ["Nantes"],
    "Bretagne": ["Rennes"],
    "Nouvelle-Aquitaine": ["Bordeaux", "Limoges", "Poitiers"],
    "Occitanie": ["Montpellier", "Toulouse"],
    "Auvergne-Rhône-Alpes": ["Clermont-Ferrand", "Grenoble", "Lyon"],
    "Provence-Alpes-Côte d'Azur": ["Aix-Marseille", "Nice"],
    "Corse": ["Corse"],
    "Guadeloupe": ["Guadeloupe"],
    "Martinique": ["Martinique"],
    "Guyane": ["Guyane"],
    "La Réunion": ["La Réunion", "Réunion"],
    "Mayotte": ["Mayotte"],
}

ACADEMIE_REGION = {
    academie: region
    for region, academies in REGIONS_ACADEMIES.items()
    for academie in academies
}


# ---------- Enregistrement commun ----------

def enregistrer_json(donnees, chemin_fichier):
    chemin = Path(chemin_fichier)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    with chemin.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, indent=2, ensure_ascii=False)

    print(f"Fichier créé : {chemin.resolve()}")
    return str(chemin)


# ---------- Électricité ----------

def telecharger_electricite(url, chemin_fichier):
    print("\nTéléchargement des données électriques régionales...")

    params = {
        "dataset": "eco2mix-regional-tr",
        "rows": 1000,
        "sort": "-date_heure",
        "q": "NOT #null(consommation)",
    }

    reponse = requests.get(url, params=params, timeout=60)
    reponse.raise_for_status()
    donnees = reponse.json()

    if not isinstance(donnees, dict) or not donnees.get("records"):
        raise ValueError("Aucune mesure électrique reçue.")

    print(f"Nombre de mesures : {len(donnees['records'])}")

    # Conserver la réponse complète : records, fields, etc.
    return enregistrer_json(donnees, chemin_fichier)


# ---------- Météo ----------

def telecharger_meteo(url, chemin_fichier):
    print("\nTéléchargement de la météo historique...")

    # 1. Lire les consommations déjà téléchargées.
    with FICHIER_ELECTRICITE.open("r", encoding="utf-8") as fichier:
        electricite = json.load(fichier)

    records = electricite.get("records", [])

    if not records:
        raise ValueError("Le fichier électrique ne contient aucune mesure.")

    # 2. Convertir les dates en UTC.
    from datetime import datetime, timezone

    dates = [
        datetime.fromisoformat(
            record["fields"]["date_heure"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        for record in records
    ]

    date_debut = min(dates).date().isoformat()
    date_fin = max(dates).date().isoformat()

    print(f"Période demandée : {date_debut} au {date_fin}")

    # 3. Demander la météo des mêmes dates pour les 12 villes.
    params = {
        "latitude": ",".join(str(region[3]) for region in REGIONS),
        "longitude": ",".join(str(region[4]) for region in REGIONS),
        "start_date": date_debut,
        "end_date": date_fin,
        "hourly": "temperature_2m,relative_humidity_2m",
        "timezone": "UTC",
    }

    reponse = requests.get(url, params=params, timeout=60)
    reponse.raise_for_status()
    resultats = reponse.json()

    if not isinstance(resultats, list) or len(resultats) != len(REGIONS):
        raise ValueError("Réponse météo inattendue ou incomplète.")

    # 4. Conserver le même format que votre ancien fichier météo.
    donnees = {"regions": []}

    for region, meteo in zip(REGIONS, resultats):
        code, nom, ville, latitude, longitude = region

        donnees["regions"].append({
            "code_insee_region": code,
            "libelle_region": nom,
            "ville_reference": ville,
            "latitude_demandee": latitude,
            "longitude_demandee": longitude,
            "meteo": meteo,
        })

    return enregistrer_json(donnees, chemin_fichier)


# ---------- Jours fériés et week-ends ----------

def telecharger_calendrier(annee, chemin_fichier):
    print(f"\nTéléchargement du calendrier {annee}...")

    url = (
        "https://calendrier.api.gouv.fr/jours-feries/"
        f"metropole/{annee}.json"
    )

    reponse = requests.get(url, timeout=60)
    reponse.raise_for_status()
    jours_feries = reponse.json()

    calendrier = []
    jour = date(annee, 1, 1)

    while jour.year == annee:
        date_texte = jour.isoformat()

        calendrier.append({
            "date": date_texte,
            "jour_semaine": jour.weekday(),  # Lundi = 0, dimanche = 6
            "weekend": jour.weekday() >= 5,
            "ferie": date_texte in jours_feries,
            "nom_ferie": jours_feries.get(date_texte),
        })

        jour += timedelta(days=1)

    print(f"Nombre de jours : {len(calendrier)}")
    return enregistrer_json(calendrier, chemin_fichier)


# ---------- Vacances scolaires ----------

def telecharger_vacances(url, chemin_fichier):
    print("\nTéléchargement des vacances scolaires...")

    reponse = requests.get(url, timeout=60)
    reponse.raise_for_status()
    donnees = reponse.json()

    if not isinstance(donnees, list) or not donnees:
        raise ValueError("Le calendrier scolaire est vide ou inattendu.")

    lieux_non_associes = set()

    for ligne in donnees:
        academie = ligne.get("location") or ""
        region = ACADEMIE_REGION.get(academie)

        ligne["libelle_region"] = region

        if region is None:
            lieux_non_associes.add(academie)

    print(f"Nombre de périodes : {len(donnees)}")

    if lieux_non_associes:
        print(
            "Lieux sans région associée :",
            ", ".join(sorted(lieux_non_associes)),
        )

    return enregistrer_json(donnees, chemin_fichier)


# ---------- Exécution ----------

if __name__ == "__main__":
    DOSSIER_DATA.mkdir(parents=True, exist_ok=True)
    print(f"Dossier de sortie : {DOSSIER_DATA}")

    telecharger_electricite(URL_API_ELECTRICITE, FICHIER_ELECTRICITE)
    telecharger_meteo(URL_API_METEO, FICHIER_METEO)
    telecharger_calendrier(ANNEE, FICHIER_CALENDRIER)
    telecharger_vacances(URL_API_VACANCES, FICHIER_VACANCES)

    print("\nLes quatre fichiers JSON ont été enregistrés.")