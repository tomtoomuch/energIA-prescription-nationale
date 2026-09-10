# Consigne initiale — prédiction de consommation

## Charger et explorer la donnée

```python
import pandas as pd

df = pd.read_csv("tp1pedagogiqueconso.csv", parse_dates=["date_heure"])
print("Dimensions :", df.shape)
print(df.head())
print(df.info())
print(df.describe())
print(df.isna().sum())
```

Identifier le nombre de lignes et de colonnes, la période couverte et les valeurs manquantes. L'analyse exploratoire sert à comprendre la qualité des données et à formuler des hypothèses avant d'entraîner un modèle.

## Visualiser la saisonnalité

```python
df.set_index("date_heure")["consommation_mw"].plot(figsize=(12, 4))
df.groupby("jour_semaine")["consommation_mw"].mean().plot(kind="bar")
df.groupby("heure")["consommation_mw"].mean().plot(kind="bar")
df.plot.scatter(x="temperature", y="consommation_mw", alpha=0.3)
```

Rechercher les effets du froid, des heures de pointe et du week-end. Une corrélation visuelle reste une piste, et non une preuve de causalité.

## Matrice de corrélation

```python
colonnes_numeriques = [
    "temperature", "jour_semaine", "heure", "est_weekend", "mois", "consommation_mw"
]
matrice_corr = df[colonnes_numeriques].corr()
sns.heatmap(matrice_corr, annot=True, cmap="coolwarm", center=0)
```

Le coefficient de Pearson ne décrit que les relations linéaires : l'heure peut avoir un effet cyclique important sans forte corrélation linéaire.

## Construire les features

Transformer le mois en saison, puis encoder les saisons sous forme de variables binaires :

```python
def mois_vers_saison(mois):
    if mois in [12, 1, 2]:
        return "hiver"
    elif mois in [3, 4, 5]:
        return "printemps"
    elif mois in [6, 7, 8]:
        return "ete"
    return "automne"

df["saison"] = df["mois"].apply(mois_vers_saison)
df_saison = pd.get_dummies(df["saison"], prefix="saison")
df = pd.concat([df, df_saison], axis=1)
features = ["temperature", "jour_semaine", "heure", "est_weekend"] + list(df_saison.columns)
X = df[features]
y = df["consommation_mw"]
```

## Entraîner, comparer et évaluer

```python
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)
model.fit(X_train, y_train)

model_lineaire = LinearRegression()
model_lineaire.fit(X_train, y_train)
pred_lineaire = model_lineaire.predict(X_test)
mae_lineaire = mean_absolute_error(y_test, pred_lineaire)

y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
mape = mean_absolute_percentage_error(y_test, y_pred)
```

Ne pas mélanger une série temporelle avant le split, afin d'éviter une fuite d'information. Comparer la forêt aléatoire à la régression linéaire, puis à la baseline naïve :

```python
baseline_pred = df["consommation_mw"].shift(24).iloc[X_test.index]
mae_baseline = mean_absolute_error(y_test, baseline_pred.bfill())
```

## Interpréter le modèle

```python
importances = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
residus = y_test.values - y_pred
df_test = df.iloc[X_test.index].copy()
df_test["erreur_abs"] = abs(residus)
df_test.groupby("heure")["erreur_abs"].mean().plot(kind="bar")
```

Comparer l'importance des variables aux corrélations et rechercher les périodes où l'erreur est systématiquement plus forte. Une MAE globale peut masquer de mauvais résultats pendant les pointes de consommation.
