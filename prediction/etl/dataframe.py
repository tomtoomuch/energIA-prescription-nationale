import json
from pathlib import Path

import pandas as pd


RACINE_PROJET = Path(__file__).resolve().parent.parent
DOSSIER_DATA = RACINE_PROJET / "data"


def lire_json(nom_fichier):
    chemin = DOSSIER_DATA / nom_fichier

    with chemin.open("r", encoding="utf-8") as fichier:
        return json.load(fichier)


def charger_electricite():
    donnees = lire_json("eco2mix-regional.json")

    lignes = [
        record["fields"]
        for record in donnees["records"]
    ]

    df = pd.DataFrame(lignes)

    df["code_insee_region"] = (
        df["code_insee_region"].astype(str).str.zfill(2)
    )

    df["date_heure"] = pd.to_datetime(
        df["date_heure"],
        utc=True,
    )

    # La météo est horaire : 14:15 et 14:30 seront associés à 14:00.
    df["heure_utc"] = df["date_heure"].dt.floor("h")

    # Le calendrier utilise la date française.
    df["date_locale"] = (
        df["date_heure"]
        .dt.tz_convert("Europe/Paris")
        .dt.strftime("%Y-%m-%d")
    )

    return df

def charger_meteo():
    donnees = lire_json("meteo-regions.json")
    tableaux = []

    for region in donnees["regions"]:
        meteo = region["meteo"]

        if meteo.get("utc_offset_seconds") != 0:
            raise ValueError(
                "La météo doit être téléchargée avec timezone=UTC."
            )

        df_region = pd.DataFrame(meteo["hourly"])

        df_region["heure_utc"] = pd.to_datetime(
            df_region["time"],
            utc=True,
        )

        df_region["code_insee_region"] = str(
            region["code_insee_region"]
        ).zfill(2)

        df_region["ville_reference"] = region["ville_reference"]

        tableaux.append(
            df_region[[
                "code_insee_region",
                "heure_utc",
                "ville_reference",
                "temperature_2m",
                "relative_humidity_2m",
            ]]
        )

    return pd.concat(tableaux, ignore_index=True)

def charger_calendrier():
    donnees = lire_json("calendrier-2026.json")

    df = pd.DataFrame(donnees)

    return df.rename(columns={
        "date": "date_locale",
    })


def ajouter_vacances(df):
    vacances = pd.DataFrame(
        lire_json("vacances-scolaires-regions.json")
    )

    # Garder les lignes associées à une région.
    vacances = vacances[
        vacances["libelle_region"].notna()
    ].copy()

    # Écarter les périodes réservées aux enseignants.
    vacances = vacances[
        vacances["population"].fillna("") != "Enseignants"
    ].copy()

    for colonne in ["start_date", "end_date"]:
        vacances[colonne] = (
            pd.to_datetime(vacances[colonne], utc=True)
            .dt.tz_convert("Europe/Paris")
            .dt.strftime("%Y-%m-%d")
        )

    # Un seul calcul par région et par jour.
    jours = df[
        ["libelle_region", "date_locale"]
    ].drop_duplicates()

    resultats = []

    for region, jour in jours.itertuples(index=False, name=None):
        periodes = vacances[
            vacances["libelle_region"] == region
        ]

        annee = int(jour[:4])

        if jour[5:] < "09-01":
            annee -= 1

        annee_scolaire = f"{annee}-{annee + 1}"

        calendrier_disponible = (
            periodes["annee_scolaire"] == annee_scolaire
        ).any()

        actives = periodes[
            (periodes["start_date"] <= jour)
            & (jour < periodes["end_date"])
        ]

        resultats.append({
            "libelle_region": region,
            "date_locale": jour,
            "vacances_au_moins_une_zone": (
                not actives.empty
                if calendrier_disponible
                else pd.NA
            ),
            "zones_en_vacances": ", ".join(
                sorted(actives["zones"].dropna().unique())
            ),
        })

    df_vacances = pd.DataFrame(resultats)

    return df.merge(
        df_vacances,
        on=["libelle_region", "date_locale"],
        how="left",
        validate="many_to_one",
    )

# ----Dataframe-------

def creer_dataframe():
    df_electricite = charger_electricite()
    df_meteo = charger_meteo()
    df_calendrier = charger_calendrier()

    # Même région ET même heure.
    df = df_electricite.merge(
        df_meteo,
        on=["code_insee_region", "heure_utc"],
        how="left",
        validate="many_to_one",
    )

    # Même date française.
    df = df.merge(
        df_calendrier,
        on="date_locale",
        how="left",
        validate="many_to_one",
    )

    df = ajouter_vacances(df)

    return df.sort_values(
        ["date_heure", "code_insee_region"]
    ).reset_index(drop=True)


if __name__ == "__main__":
    df = creer_dataframe()

    colonnes = [
        "libelle_region",
        "date_heure",
        "consommation",
        "temperature_2m",
        "relative_humidity_2m",
        "weekend",
        "ferie",
        "vacances_au_moins_une_zone",
    ]

    print(df[colonnes].head(10).to_string(index=False))

    print("\nDimensions :", df.shape)

    print("\nValeurs manquantes :")
    print(df[colonnes].isna().sum())

    # Facultatif : sauvegarder le tableau fusionné.
    df.to_csv(
        DOSSIER_DATA / "dataset_final.csv",
        index=False,
        encoding="utf-8-sig",
    )