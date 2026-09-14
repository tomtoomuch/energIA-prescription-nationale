import pandas as pd
from pathlib import Path
import joblib
from sklearn.preprocessing import OneHotEncoder #transformer les noms des régions en indicateurs numériques
from sklearn.compose import ColumnTransformer #Appliquer cette transformation à la colonne région
from sklearn.pipeline import Pipeline #Enchaîner la préparation et le modèle
from sklearn.linear_model import LinearRegression #Apprendre une formule pour estimer la consommation
from sklearn.metrics import mean_absolute_error



def preparer_donnees(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    dates_originales = df["date_locale"].astype("string").str.strip()
    dates_converties = pd.to_datetime(
        dates_originales,
        format="%Y-%m-%d",
        errors="coerce"
    )
    problemes = dates_converties.isna()
    if problemes.any():
        print("\nNombre de dates problématiques :", problemes.sum())
        print("\nExemples de valeurs originales :")
        print(dates_originales[problemes].head(20).to_string())
        raise ValueError("Vérifie les dates affichées ci-dessus.")

    df["date_locale"] = dates_converties
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
            exemples = texte[inconnues].unique().tolist()
            raise ValueError(
                f"Valeurs non reconnues dans {colonne} : {exemples}"
            )
        df[colonne] = valeurs.astype("Int8")

    # extraire les informations du calendrier
    df["annee"] = df["date_locale"].dt.year
    df["mois"] = df["date_locale"].dt.month
    df["jour_semaine"] = df["date_locale"].dt.dayofweek

    #lundi = 0, ..., samedi = 5, dimanche = 6
    df["weekend"] = (df["jour_semaine"] >= 5).astype("int8")

    #Ajouter les saisons météorologiques
    mois = df["mois"]
    df["saison_hiver"] = mois.isin([12, 1, 2]).astype("int8")
    df["saison_printemps"] = mois.isin([3, 4, 5]).astype("int8")
    df["saison_ete"] = mois.isin([6, 7, 8]).astype("int8")
    df["saison_automne"] = mois.isin([9, 10, 11]).astype("int8")

    #convertir les mesures en nombres
    for colonne in [
        "consommation",
        "temperature_2m",
        "relative_humidity_2m",
        "heure_locale",
    ]:
        texte = (
            df[colonne]
            .astype("string")
            .str.strip()
            .str.replace(",", ".", regex=False)
        )

        df[colonne] = pd.to_numeric(texte, errors="coerce")

    return df

# __file__ contient le chemin du script Python.
dossier_script = Path(__file__).resolve().parent

chemin_csv = dossier_script / "data" / "dataset_final.csv"


df = pd.read_csv(
    chemin_csv,
    sep=None,
    engine="python",
    encoding="utf-8-sig"
)

df.columns = df.columns.str.strip()


df = preparer_donnees(df)

df["minute"] = df["heure"].str.split(":").str[1].astype(int)



colonnes = [
    "libelle_region",
    "mois",
    "jour_semaine",
    "heure_locale",
    "minute",
    "ferie",
    "vacances_scolaires",
]
X = df[colonnes].copy()
y = df["consommation"].copy() #à apprendre

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

#test final.
X_test = X.loc[masque_test].copy()
y_test = y.loc[masque_test].copy()


#transformer les noms des régions en indicateurs numériques
preparation = ColumnTransformer(
    transformers=[
        (
            "region",
            OneHotEncoder(handle_unknown="ignore"),#évite une erreur si une région inconnue apparaît plus tard
            ["libelle_region"],
        )
    ],
    remainder="passthrough",#conserve les autres colonnes, déjà numériques.
)

modele = Pipeline(
    steps=[
        ("preparation", preparation),
        ("regression", LinearRegression()),
    ]
)

modele.fit(X_train, y_train)


# sauvegarder la préparation et le modèle entraîné
dossier_modeles = dossier_script / "modeles"
dossier_modeles.mkdir(parents=True, exist_ok=True)

chemin_modele = dossier_modeles / "modele_consommation.joblib"

joblib.dump(modele, chemin_modele)

print("\nModèle sauvegardé :", chemin_modele)



# prediction
predictions = modele.predict(X_validation)

comparaison = X_validation[["libelle_region"]].copy()
comparaison["consommation_reelle"] = y_validation
comparaison["consommation_predite"] = predictions



# calculer l'erreur moyenne sur toute la validation
mae = mean_absolute_error(y_validation, predictions)



comparaison["erreur_signee"] = (
    comparaison["consommation_predite"]
    - comparaison["consommation_reelle"]
)

# 2. Mesurer la taille de l'écart, sans son signe.
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

print("\nRésultats par région :")
print(resultats_regions.round(2).to_string())


# choisir la journée à prédire
jour = pd.Timestamp("2025-09-01", tz="Europe/Paris")
fin = jour + pd.DateOffset(days=1)

# créer un horaire toutes les 15 minutes
horaires = pd.date_range(
    start=jour,
    end=fin,
    freq="15min",
    inclusive="left",
)

# récupérer les régions utilisées pendant l'apprentissage
regions = sorted(X_train["libelle_region"].unique())

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
if entrees_15min[colonnes].isna().any().any():
    raise ValueError(
        "Calendrier incomplet pour la journée demandée. "
        "Fournir les jours fériés et vacances de cette date pour chaque région."
    )

# prédire directement la consommation à chaque quart d'heure
entrees_15min["consommation_predite"] = modele.predict(
    entrees_15min[colonnes]
)

# conserver les prédictions séparément des observations réelles
resultats_15min = entrees_15min[
    [
        "date_heure",
        "libelle_region",
        "consommation_predite",
    ]
].copy()

resultats_15min["date_creation_utc"] = pd.Timestamp.now(tz="UTC")
resultats_15min["origine"] = "prediction_modele"
resultats_15min["date_fin_entrainement"] = (
    df.loc[masque_train, "date_locale"].max().strftime("%Y-%m-%d")
)
resultats_15min = resultats_15min.sort_values(
    ["date_heure", "libelle_region"]
)

# sauvegarder les prédictions dans un fichier CSV
# Le dataset_final.csv n'est pas modifié.
dossier_predictions = dossier_script / "predictions"
dossier_predictions.mkdir(parents=True, exist_ok=True)

chemin_predictions = (
    dossier_predictions / f"predictions_15min_{jour:%Y-%m-%d}.csv"
)
resultats_15min.to_csv(
    chemin_predictions,
    index=False,
    encoding="utf-8-sig",
)

# afficher quelques horaires pour la première région
print("\nPremières prédictions pour chaque région :")

for region, tableau in resultats_15min.groupby("libelle_region"):
    print("\nRégion :", region)
    print(tableau.head(4).round(2).to_string(index=False))

print("\nNombre de prédictions par région :")
print(resultats_15min.groupby("libelle_region").size())

