import json
import re
import unicodedata
from pathlib import Path

import joblib
import pandas as pd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


# ---------- Configuration ----------

DOSSIER_SCRIPT = Path(__file__).resolve().parent

CHEMIN_CSV = DOSSIER_SCRIPT / "data" / "dataset_final.csv"
DOSSIER_MODELES = DOSSIER_SCRIPT / "modeles"
DOSSIER_PREDICTIONS = DOSSIER_SCRIPT / "predictions"
DOSSIER_GRAPHIQUES = DOSSIER_SCRIPT / "graphiques"

JOUR_PREDICTION = "2025-09-01"

COLONNES = [
    "libelle_region",
    "mois",
    "jour_semaine",
    "heure_locale",
    "minute",
    "ferie",
    "vacances_scolaires",
]


# ---------- Préparation des données ----------

def preparer_donnees(df):
    df = df.copy()
    df.columns = df.columns.str.strip()

    colonnes_requises = [
        "libelle_region",
        "date_heure",
        "date_locale",
        "consommation",
        "temperature_2m",
        "relative_humidity_2m",
        "ferie",
        "vacances_scolaires",
    ]

    absentes = [
        colonne
        for colonne in colonnes_requises
        if colonne not in df.columns
    ]

    if absentes:
        raise ValueError(f"Colonnes absentes : {absentes}")

    if df.empty:
        raise ValueError("Le dataset est vide.")

    df["libelle_region"] = (
        df["libelle_region"].astype("string").str.strip()
    )
    df["libelle_region"] = df["libelle_region"].replace("", pd.NA)

    dates_originales = (
        df["date_locale"].astype("string").str.strip()
    )

    dates_converties = pd.to_datetime(
        dates_originales,
        format="%Y-%m-%d",
        errors="coerce",
    )

    if dates_converties.isna().any():
        raise ValueError("Des dates locales sont absentes ou invalides.")

    df["date_locale"] = dates_converties

    df["date_heure"] = pd.to_datetime(
        df["date_heure"],
        utc=True,
        errors="coerce",
    )

    if df["date_heure"].isna().any():
        raise ValueError("Des horodatages sont absents ou invalides.")

    # Date française pour le calendrier et les heures.
    dates_locales = df["date_heure"].dt.tz_convert("Europe/Paris")

    dates_attendues = (
        dates_locales.dt.tz_localize(None).dt.normalize()
    )

    if not dates_attendues.eq(df["date_locale"]).all():
        raise ValueError(
            "date_locale ne correspond pas à date_heure "
            "dans le fuseau Europe/Paris."
        )

    correspondance = {
        "VRAI": 1,
        "FAUX": 0,
        "TRUE": 1,
        "FALSE": 0,
        "1": 1,
        "0": 0,
    }

    for colonne in ["ferie", "vacances_scolaires"]:
        texte = (
            df[colonne]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        valeurs = texte.map(correspondance)
        inconnues = texte.notna() & valeurs.isna()

        if inconnues.any():
            raise ValueError(
                f"Valeurs non reconnues dans {colonne} : "
                f"{texte[inconnues].unique().tolist()}"
            )

        df[colonne] = valeurs.astype("Int8")

    # extraire les informations du calendrier
    df["annee"] = dates_locales.dt.year
    df["mois"] = dates_locales.dt.month
    df["jour_semaine"] = dates_locales.dt.dayofweek
    df["heure_locale"] = dates_locales.dt.hour
    df["minute"] = dates_locales.dt.minute

    # lundi = 0, ..., samedi = 5, dimanche = 6
    df["weekend"] = (df["jour_semaine"] >= 5).astype("int8")

    # Ajouter les saisons météorologiques
    mois = df["mois"]

    df["saison_hiver"] = mois.isin([12, 1, 2]).astype("int8")
    df["saison_printemps"] = mois.isin([3, 4, 5]).astype("int8")
    df["saison_ete"] = mois.isin([6, 7, 8]).astype("int8")
    df["saison_automne"] = mois.isin([9, 10, 11]).astype("int8")

    # convertir les mesures en nombres
    for colonne in [
        "consommation",
        "temperature_2m",
        "relative_humidity_2m",
    ]:
        texte = (
            df[colonne]
            .astype("string")
            .str.strip()
            .str.replace(",", ".", regex=False)
        )

        df[colonne] = pd.to_numeric(texte, errors="coerce")

    # Vérifier les informations nécessaires au modèle.
    manquantes = df[COLONNES + ["consommation"]].isna().sum()

    if manquantes.any():
        raise ValueError(
            "Valeurs manquantes à corriger :\n"
            + manquantes[manquantes > 0].to_string()
        )

    numeriques = [
        colonne
        for colonne in COLONNES
        if colonne != "libelle_region"
    ] + ["consommation"]

    if df[numeriques].isin([float("inf"), float("-inf")]).any().any():
        raise ValueError("Des valeurs numériques sont infinies.")

    # Retirer seulement les doublons équivalents pour le modèle.
    cles = ["libelle_region", "date_heure"]
    doublons = df.duplicated(cles, keep=False)

    if doublons.any():
        champs = numeriques + [
            "temperature_2m",
            "relative_humidity_2m",
        ]

        variations = (
            df.loc[doublons]
            .groupby(cles)[champs]
            .nunique(dropna=False)
        )

        if (variations > 1).any().any():
            raise ValueError(
                "Des observations au même instant "
                "contiennent des valeurs contradictoires."
            )

        nombre = int(df.duplicated(cles).sum())
        df = df.drop_duplicates(cles).copy()

        print("Doublons équivalents retirés en mémoire :", nombre)

    return df.sort_values(cles).reset_index(drop=True)


# ---------- Noms des dossiers ----------

def nom_region_fichier(region):
    texte = unicodedata.normalize("NFKD", region)
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = re.sub(r"[^a-zA-Z0-9]+", "_", texte)

    return texte.strip("_").lower()


# ---------- Matrices de corrélation ----------

def tracer_correlation(donnees, region, mois, dossier_sortie):
    colonnes_correlation = [
        "consommation",
        "temperature_2m",
        "relative_humidity_2m",
        "jour_semaine",
        "heure_locale",
        "minute",
        "weekend",
        "ferie",
        "vacances_scolaires",
    ]

    valeurs = donnees[colonnes_correlation].astype(float)
    valeurs = valeurs.replace(
        [float("inf"), float("-inf")],
        float("nan"),
    )

    # Une variable constante n'a pas de corrélation définie.
    variables = [
        colonne
        for colonne in valeurs.columns
        if valeurs[colonne].nunique() > 1
    ]

    if len(variables) < 2:
        print("Corrélation impossible :", region, mois)
        return

    correlation = valeurs[variables].corr(
        method="pearson",
        min_periods=3,
    )

    fig, ax = plt.subplots(figsize=(12, 9))

    image = ax.imshow(
        correlation,
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
    )

    positions = range(len(correlation.columns))

    ax.set_xticks(positions)
    ax.set_yticks(positions)

    ax.set_xticklabels(
        correlation.columns,
        rotation=45,
        ha="right",
    )
    ax.set_yticklabels(correlation.index)

    for ligne in range(len(correlation)):
        for colonne in range(len(correlation)):
            valeur = correlation.iloc[ligne, colonne]
            texte = "ND" if pd.isna(valeur) else f"{valeur:.2f}"

            couleur = (
                "white"
                if pd.notna(valeur) and abs(valeur) > 0.6
                else "black"
            )

            ax.text(
                colonne,
                ligne,
                texte,
                ha="center",
                va="center",
                color=couleur,
                fontsize=9,
            )

    ax.set_title(
        f"Corrélation des observations — {region}\n{mois}"
    )

    fig.colorbar(image, ax=ax, label="Corrélation de Pearson")
    fig.tight_layout()

    dossier_region = dossier_sortie / nom_region_fichier(region)
    dossier_region.mkdir(parents=True, exist_ok=True)

    fig.savefig(
        dossier_region / f"correlation_{mois}.png",
        dpi=150,
    )

    plt.close(fig)


# ---------- Courbes réelle / prédite ----------

def tracer_comparaison(
    donnees,
    region,
    mois,
    type_periode,
    dossier_sortie,
):
    donnees = donnees.sort_values("date_heure").copy()

    mae_mois = mean_absolute_error(
        donnees["consommation"],
        donnees["consommation_predite"],
    )

    dates_locales = (
        donnees["date_heure"].dt.tz_convert("Europe/Paris")
    )

    fig, ax = plt.subplots(figsize=(15, 5))

    ax.plot(
        dates_locales,
        donnees["consommation"],
        label="Consommation réelle",
        color="steelblue",
        linewidth=1,
    )

    ax.plot(
        dates_locales,
        donnees["consommation_predite"],
        label="Consommation prédite",
        color="darkorange",
        linewidth=1,
        linestyle="--",
    )

    ax.set_title(
        f"{region} — {mois}\n"
        f"{type_periode} — MAE : {mae_mois:.2f}"
    )

    ax.set_xlabel("Date locale")
    ax.set_ylabel("Consommation — unité du dataset")

    ax.xaxis.set_major_locator(
        mdates.DayLocator(interval=4, tz=dates_locales.dt.tz)
    )
    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%d/%m",
            tz=dates_locales.dt.tz,
        )
    )

    ax.grid(alpha=0.3)
    ax.legend()

    fig.autofmt_xdate()
    fig.tight_layout()

    dossier_region = dossier_sortie / nom_region_fichier(region)
    dossier_region.mkdir(parents=True, exist_ok=True)

    fig.savefig(
        dossier_region / f"reel_predit_{mois}.png",
        dpi=150,
    )

    plt.close(fig)


# ---------- Exécution ----------

def main():
    if not CHEMIN_CSV.exists():
        raise FileNotFoundError(
            f"Dataset introuvable : {CHEMIN_CSV}"
        )

    df = pd.read_csv(
        CHEMIN_CSV,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
    )

    df = preparer_donnees(df)

    if set(df["annee"].unique()) != {2025}:
        raise ValueError(
            "Ce découpage attend les données de 2025. "
            "Adapter les dates si le dataset change d'année."
        )

    X = df[COLONNES].copy()
    y = df["consommation"].copy()  # à apprendre

    # Séparer les données selon les dates.
    masque_train = df["date_locale"] < "2025-09-01"

    masque_validation = (
        (df["date_locale"] >= "2025-09-01")
        & (df["date_locale"] < "2025-11-01")
    )

    masque_test = df["date_locale"] >= "2025-11-01"

    X_train = X.loc[masque_train].copy()
    y_train = y.loc[masque_train].copy()

    X_validation = X.loc[masque_validation].copy()
    y_validation = y.loc[masque_validation].copy()

    # test final
    X_test = X.loc[masque_test].copy()
    y_test = y.loc[masque_test].copy()

    for nom, partie in [
        ("Entraînement", X_train),
        ("Validation", X_validation),
        ("Test", X_test),
    ]:
        if partie.empty:
            raise ValueError(f"Partition vide : {nom}")

        print(nom, ":", partie.shape)

    regions = sorted(X_train["libelle_region"].unique())

    inconnues = set(df["libelle_region"]) - set(regions)

    if inconnues:
        raise ValueError(
            f"Régions absentes de l'entraînement : {inconnues}"
        )

    # transformer les noms des régions en indicateurs numériques
    preparation = ColumnTransformer(
        transformers=[
            (
                "region",
                OneHotEncoder(handle_unknown="ignore"),
                ["libelle_region"],
            )
        ],
        remainder="passthrough",
    )

    modele = Pipeline(
        steps=[
            ("preparation", preparation),
            ("regression", LinearRegression()),
        ]
    )

    # préparer les données des graphiques
    donnees_graphiques = df.copy()

    donnees_graphiques["mois_graphique"] = (
        donnees_graphiques["date_heure"]
        .dt.tz_convert("Europe/Paris")
        .dt.strftime("%Y-%m")
    )

    # Matrices descriptives avant l'entraînement.
    # Ne pas utiliser les mois de test pour régler le modèle.
    print("\nCréation des matrices de corrélation...")

    for (region, mois), groupe in donnees_graphiques.groupby(
        ["libelle_region", "mois_graphique"]
    ):
        tracer_correlation(
            groupe,
            region,
            mois,
            DOSSIER_GRAPHIQUES / "correlations",
        )

    # entraîner le modèle
    modele.fit(X_train, y_train)

    print("\nApprentissage terminé.")

    # sauvegarder la préparation et le modèle entraîné
    DOSSIER_MODELES.mkdir(parents=True, exist_ok=True)

    chemin_modele = (
        DOSSIER_MODELES / "modele_consommation.joblib"
    )

    joblib.dump(modele, chemin_modele)

    print("\nModèle sauvegardé :", chemin_modele)

    # prediction sur la validation
    predictions = modele.predict(X_validation)

    comparaison = df.loc[
        masque_validation,
        ["date_heure", "libelle_region"],
    ].copy()

    comparaison["consommation_reelle"] = y_validation
    comparaison["consommation_predite"] = predictions

    # calculer l'erreur moyenne sur toute la validation
    mae = mean_absolute_error(y_validation, predictions)

    comparaison["erreur_signee"] = (
        comparaison["consommation_predite"]
        - comparaison["consommation_reelle"]
    )

    # Mesurer la taille de l'écart, sans son signe.
    comparaison["erreur_absolue"] = (
        comparaison["erreur_signee"].abs()
    )

    # Regrouper les observations et calculer les mesures par région.
    resultats_regions = (
        comparaison
        .groupby("libelle_region")
        .agg(
            nombre_predictions=("erreur_absolue", "count"),
            consommation_moyenne=("consommation_reelle", "mean"),
            mae=("erreur_absolue", "mean"),
            erreur_signee_moyenne=("erreur_signee", "mean"),
        )
        .sort_values("mae", ascending=False)
    )

    print("\nMAE de validation :", round(mae, 2))
    print("\nRésultats par région :")
    print(resultats_regions.round(2).to_string())

    dossier_evaluation = DOSSIER_GRAPHIQUES / "evaluation"
    dossier_evaluation.mkdir(parents=True, exist_ok=True)

    resultats_regions.to_csv(
        dossier_evaluation / "erreurs_par_region.csv",
        encoding="utf-8-sig",
    )

    # comparer le réel et le prédit pour tous les mois demandés
    comparaison_graphique = donnees_graphiques.copy()

    comparaison_graphique["consommation_predite"] = (
        modele.predict(X)
    )

    print("\nCréation des courbes réelle/prédite...")

    for (region, mois), groupe in comparaison_graphique.groupby(
        ["libelle_region", "mois_graphique"]
    ):
        if mois < "2025-09":
            type_periode = "Entraînement : données déjà vues"
        elif mois < "2025-11":
            type_periode = "Validation"
        else:
            type_periode = "Test"

        tracer_comparaison(
            groupe,
            region,
            mois,
            type_periode,
            DOSSIER_GRAPHIQUES / "reel_predit",
        )

    # choisir la journée à prédire
    jour = pd.Timestamp(
        JOUR_PREDICTION,
        tz="Europe/Paris",
    )

    fin = jour + pd.DateOffset(days=1)

    if jour.tz_localize(None) <= df.loc[
        masque_train, "date_locale"
    ].max():
        raise ValueError(
            "Choisir une journée après la fin de l'entraînement."
        )

    # créer un horaire toutes les 15 minutes
    horaires = pd.date_range(
        start=jour,
        end=fin,
        freq="15min",
        inclusive="left",
    )

    # créer une ligne pour chaque horaire et chaque région
    entrees_15min = pd.MultiIndex.from_product(
        [horaires, regions],
        names=["date_heure", "libelle_region"],
    ).to_frame(index=False)

    # extraire les informations du calendrier
    dates = entrees_15min["date_heure"]

    entrees_15min["date_locale"] = (
        dates.dt.tz_localize(None).dt.normalize()
    )
    entrees_15min["mois"] = dates.dt.month
    entrees_15min["jour_semaine"] = dates.dt.dayofweek
    entrees_15min["heure_locale"] = dates.dt.hour
    entrees_15min["minute"] = dates.dt.minute

    # récupérer les jours fériés et vacances par région et par date
    calendrier = df[
        [
            "date_locale",
            "libelle_region",
            "ferie",
            "vacances_scolaires",
        ]
    ].drop_duplicates()

    entrees_15min = entrees_15min.merge(
        calendrier,
        on=["date_locale", "libelle_region"],
        how="left",
        validate="many_to_one",
    )

    # vérifier que les informations nécessaires sont présentes
    if entrees_15min[COLONNES].isna().any().any():
        raise ValueError(
            "Calendrier incomplet pour la journée demandée. "
            "Fournir les jours fériés et vacances correspondants."
        )

    # prédire directement la consommation à chaque quart d'heure
    entrees_15min["consommation_predite"] = modele.predict(
        entrees_15min[COLONNES]
    )

    # conserver les prédictions séparément des observations réelles
    resultats_15min = entrees_15min[
        [
            "date_heure",
            "libelle_region",
            "consommation_predite",
        ]
    ].copy()

    resultats_15min["date_creation_utc"] = pd.Timestamp.now(
        tz="UTC"
    )
    resultats_15min["origine"] = "prediction_modele"
    resultats_15min["date_fin_entrainement"] = (
        df.loc[masque_train, "date_locale"]
        .max()
        .strftime("%Y-%m-%d")
    )

    resultats_15min = resultats_15min.sort_values(
        ["libelle_region", "date_heure"]
    )

    # sauvegarder les prédictions dans un fichier CSV
    # Le dataset_final.csv n'est pas modifié.
    DOSSIER_PREDICTIONS.mkdir(parents=True, exist_ok=True)

    chemin_predictions = (
        DOSSIER_PREDICTIONS
        / f"predictions_15min_{jour:%Y-%m-%d}.csv"
    )

    resultats_15min.to_csv(
        chemin_predictions,
        index=False,
        encoding="utf-8-sig",
    )

    # conserver les informations utiles sur le modèle
    informations = {
        "algorithme": "LinearRegression",
        "colonnes": COLONNES,
        "regions": regions,
        "date_fin_entrainement": (
            df.loc[masque_train, "date_locale"]
            .max()
            .strftime("%Y-%m-%d")
        ),
        "mae_validation": float(mae),
        "pas_predictions_minutes": 15,
        "precision_15min_evaluee": False,
    }

    chemin_modele.with_suffix(".json").write_text(
        json.dumps(informations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # afficher quelques horaires pour chaque région

    # afficher quelques horaires pour la première région
    print("\nPremières prédictions pour chaque région :")

    for region, tableau in resultats_15min.groupby("libelle_region"):
        print("\nRégion :", region)

        apercu = tableau.head(4).copy()
        apercu["consommation_predite"] = (
            apercu["consommation_predite"].round(2)
        )

        print(apercu.to_string(index=False))


    print("\nPremières prédictions pour chaque région :")

    for region, tableau in resultats_15min.groupby(
        "libelle_region"
    ):
        print("\nRégion :", region)

        apercu = tableau.head(4).copy()
        apercu["consommation_predite"] = (
            apercu["consommation_predite"].round(2)
        )

        print(apercu.to_string(index=False))

    print("\nNombre de prédictions par région :")
    print(resultats_15min.groupby("libelle_region").size())

    print("\nPrédictions sauvegardées :", chemin_predictions)
    print("Graphiques enregistrés dans :", DOSSIER_GRAPHIQUES)

    print(
        "\nLes comparaisons utilisent les observations disponibles. "
        "La précision aux minutes 15 et 45 n'est pas évaluée."
    )


if __name__ == "__main__":
    main()