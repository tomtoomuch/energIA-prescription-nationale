import json
from pathlib import Path

import pandas as pd

RACINE_PROJET = Path(__file__).resolve().parent.parent
DOSSIER_DATA = RACINE_PROJET / "data"


# ---------- Lecture ----------
def lire_json(nom_fichier):
    with (DOSSIER_DATA / nom_fichier).open(
        "r", encoding="utf-8"
    ) as fichier:
        return json.load(fichier)

# ---------- Toutes les mesures électriques ----------

def charger_electricite():
    donnees = lire_json("eco2mix-regional.json")

    # Conserver tous les enregistrements et tous leurs champs.
    df = pd.DataFrame([
        record["fields"]
        for record in donnees["records"]
    ])

    df["code_insee_region"] = (
        df["code_insee_region"].astype("string").str.zfill(2)
    )

    df["date_heure"] = pd.to_datetime(
        df["date_heure"], utc=True
    )

    # Clé horaire pour la météo.
    df["heure_utc"] = df["date_heure"].dt.floor("h")

    # Date française pour les jours fériés et les vacances.
    dates_locales = df["date_heure"].dt.tz_convert("Europe/Paris")

    df["date_locale"] = dates_locales.dt.strftime("%Y-%m-%d")
    df["annee"] = dates_locales.dt.year
    df["mois"] = dates_locales.dt.month
    df["jour_semaine"] = dates_locales.dt.dayofweek
    df["heure_locale"] = dates_locales.dt.hour
    df["weekend"] = df["jour_semaine"] >= 5

    return df


# ---------- Météo de toutes les régions ----------

def charger_meteo():
    donnees = lire_json("meteo-regions.json")
    tableaux = []

    for region in donnees["regions"]:
        meteo = region["meteo"]

        if meteo.get("utc_offset_seconds") != 0:
            raise ValueError(
                "Le fichier météo doit utiliser timezone=UTC."
            )

        tableau = pd.DataFrame(meteo["hourly"])

        tableau["heure_utc"] = pd.to_datetime(
            tableau.pop("time"), utc=True
        )

        tableau["code_insee_region"] = str(
            region["code_insee_region"]
        ).zfill(2)

        tableau["ville_reference"] = region["ville_reference"]

        tableaux.append(tableau)

    return pd.concat(tableaux, ignore_index=True)


# ---------- Calendriers des années présentes ----------

def charger_calendrier(annees):
    tableaux = []

    for annee in sorted(annees):
        nom = f"calendrier-{annee}.json"

        if not (DOSSIER_DATA / nom).exists():
            print(f"Calendrier absent : {nom}")
            continue

        tableau = pd.DataFrame(lire_json(nom))

        tableau = tableau.rename(columns={
            "date": "date_locale",
        })

        # Le week-end est déjà calculé depuis la date électrique.
        tableaux.append(
            tableau[["date_locale", "ferie", "nom_ferie"]]
        )

    if not tableaux:
        return pd.DataFrame(
            columns=["date_locale", "ferie", "nom_ferie"]
        )

    return pd.concat(tableaux, ignore_index=True)


# ---------- Vacances par région et par jour ----------

def ajouter_vacances(df):
    vacances = pd.DataFrame(
        lire_json("vacances-scolaires-regions.json")
    )

    vacances = vacances[
        vacances["libelle_region"].notna()
        & vacances["population"].fillna("").ne("Enseignants")
    ].copy()

    for colonne in ["start_date", "end_date"]:
        vacances[colonne] = (
            pd.to_datetime(vacances[colonne], utc=True)
            .dt.tz_convert("Europe/Paris")
            .dt.strftime("%Y-%m-%d")
        )

    # Éviter de refaire le calcul pour chaque demi-heure.
    jours = df[
        ["libelle_region", "date_locale"]
    ].drop_duplicates()

    periodes_par_region = {
        region: tableau
        for region, tableau in vacances.groupby("libelle_region")
    }

    resultats = []

    for region, jour in jours.itertuples(index=False, name=None):
        periodes = periodes_par_region.get(region)
        indicateur = pd.NA

        if periodes is not None:
            annee = int(jour[:4])

            if jour[5:] < "09-01":
                annee -= 1

            annee_scolaire = f"{annee}-{annee + 1}"

            calendrier_disponible = (
                periodes["annee_scolaire"]
                .eq(annee_scolaire)
                .any()
            )

            en_vacances = (
                (periodes["start_date"] <= jour)
                & (jour < periodes["end_date"])
            ).any()

            if en_vacances:
                indicateur = True
            elif calendrier_disponible:
                indicateur = False

        resultats.append({
            "libelle_region": region,
            "date_locale": jour,
            "vacances_scolaires": indicateur,
        })

    tableau = pd.DataFrame(resultats)
    tableau["vacances_scolaires"] = (
        tableau["vacances_scolaires"].astype("boolean")
    )

    return df.merge(
        tableau,
        on=["libelle_region", "date_locale"],
        how="left",
        validate="many_to_one",
    )


# ---------- Fusion ----------

def creer_dataframe():
    df = charger_electricite()
    nombre_mesures = len(df)

    meteo = charger_meteo()
    calendrier = charger_calendrier(df["annee"].unique())

    # Garder chaque mesure électrique, même sans météo correspondante.
    df = df.merge(
        meteo,
        on=["code_insee_region", "heure_utc"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_meteo"),
    )

    df = df.merge(
        calendrier,
        on="date_locale",
        how="left",
        validate="many_to_one",
        suffixes=("", "_calendrier"),
    )

    df = ajouter_vacances(df)

    df = df.sort_values(
        ["date_heure", "code_insee_region"]
    ).reset_index(drop=True)

    print(f"\nMesures électriques lues : {nombre_mesures}")
    print(f"Lignes après fusion : {len(df)}")

    return df


# ---------- Exécution ----------

if __name__ == "__main__":
    df = creer_dataframe()

    print("\nPériode couverte en dates françaises :")
    print(df["date_locale"].min(), "→", df["date_locale"].max())

    print("\nNombre de mesures par région et par mois :")
    couverture = pd.crosstab(
        df["libelle_region"],
        [df["annee"], df["mois"]],
    )
    print(couverture.to_string())

    colonnes = [
          "libelle_region",
        "annee",
        "mois",
        "jour_semaine",
        "heure_locale",
        "weekend",
        "ferie",
        "vacances_scolaires",
    ]

    print("\nAperçu :")


    print("\nValeurs manquantes :")
    print(df[colonnes].isna().sum())

    fichier_sortie = DOSSIER_DATA / "dataset_final.csv"

    df.to_csv(
        fichier_sortie,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"\nDataset enregistré : {fichier_sortie}")

