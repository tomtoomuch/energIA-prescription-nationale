Contexte du projet
Travail attendu
Charger et explorer la donnée

import pandas as pd

​

# Chargement du fichier

df = pd.read_csv("tp1pedagogiqueconso.csv", parse_dates=["date_heure"])

​

# Découverte du jeu de données

print("Dimensions :", df.shape)

print("\nAperçu :")

print(df.head())

​

print("\nInformations :")

print(df.info())

​

print("\nStatistiques :")

print(df.describe())

​

print("\nValeurs manquantes :")

print(df.isna().sum())

Combien de lignes/colonnes ? Quelle période couverte ? Y a-t-il des valeurs manquantes ?

    Pourquoi explorer avant de modéliser ? Cette étape s'appelle l'analyse exploratoire de données (EDA, Exploratory Data Analysis). Un modèle entraîné sur une donnée mal comprise (valeurs manquantes ignorées, aberrations non détectées, colonnes mal typées) produit des résultats faux sans le signaler. L'EDA sert à vérifier la qualité de la donnée et à formuler des hypothèses (ex. "je pense que la conso dépend de la température") avant de les tester avec un modèle.

Visualiser pour comprendre la saisonnalité

df.set_index("date_heure")["consommation_mw"].plot(figsize=(12, 4), title="Consommation dans le temps")

plt.show()

 

df.groupby("jour_semaine")["consommation_mw"].mean().plot(kind="bar", title="Moyenne par jour de semaine")

plt.show()

 

df.groupby("heure")["consommation_mw"].mean().plot(kind="bar", title="Moyenne par heure")

plt.show()

 

df.plot.scatter(x="temperature", y="consommation_mw", alpha=0.3, title="Consommation vs temperature")

plt.show()

Quels effets retrouvez-vous dans ces graphiques (froid, heures de pointe, week-end) ?

    Corrélation ne veut pas dire causalité. Voir que la consommation baisse quand la température monte ne prouve pas mathématiquement un lien de cause à effet, même si ici on sait que c'est le cas (effet chauffage). En data science, on reste toujours prudent : une corrélation visuelle est une piste à vérifier, pas une certitude.

Matrice de corrélation

Une matrice de corrélation donne une vue d'ensemble des liens entre toutes les variables numériques

colonnes_numeriques = ["temperature", "jour_semaine", "heure", "est_weekend", "mois", "consommation_mw"]

matrice_corr = df[colonnes_numeriques].corr()

 

plt.figure(figsize=(8, 6))

sns.heatmap(matrice_corr, annot=True, cmap="coolwarm", center=0)

plt.title("Matrice de correlation")

plt.show()

Quelle variable est la plus corrélée à consommation_mw ? Le signe (positif/négatif) correspond-il à ce que vous attendiez ?

    Les limites d'une matrice de corrélation Le coefficient de corrélation classique (Pearson) ne mesure que les relations linéaires. Une variable comme heure peut avoir un vrai effet sur la consommation (pics le matin et le soir) sans que cela ressorte comme une forte corrélation linéaire, car la relation est cyclique, pas une simple droite croissante ou décroissante. Une matrice de corrélation est donc un bon point de départ pour repérer les signaux évidents (ex. température), mais elle ne dispense pas d'inspecter aussi les graphiques par catégorie pour les effets plus complexes.

Modalités pédagogiques
Construire les features

Les modèles de machine learning ne comprennent que des nombres. Une variable comme le mois (1 à 12) pose un problème si elle est utilisée telle quelle : pour un modèle, l'écart entre 1 (janvier) et 12 (décembre) est énorme, alors qu'en réalité ce sont deux mois d'hiver, donc "proches" en termes de consommation.

Une solution simple : regrouper les mois en saisons, puis transformer cette catégorie en plusieurs colonnes de 0/1 (une technique appelée one-hot encoding).

def mois_vers_saison(mois):

    if mois in [12, 1, 2]:

        return "hiver"

    elif mois in [3, 4, 5]:

        return "printemps"

    elif mois in [6, 7, 8]:

        return "ete"

    else:

        return "automne"

 

df["saison"] = df["mois"].apply(mois_vers_saison)

df_saison = pd.get_dummies(df["saison"], prefix="saison")

df = pd.concat([df, df_saison], axis=1)

 

features = ["temperature", "jour_semaine", "heure", "est_weekend"] + list(df_saison.columns)

X = df[features]

y = df["consommation_mw"]

    Le one-hot encoding pd.getdummies transforme une colonne catégorielle (ex. "hiver", "été"...) en plusieurs colonnes binaires (saisonhiver = 1 ou 0, saison_ete = 1 ou 0, etc.). Chaque saison devient ainsi une information indépendante pour le modèle

Split train/test et entraînement

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

 

model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)

model.fit(X_train, y_train)

Pourquoi shuffle=False sur une série temporelle ? Que se passerait-il si on mélangeait les données avant de séparer train et test ?
Comparer à un modèle plus simple

Avant de se satisfaire du RandomForest, comparez-le à un modèle beaucoup plus simple : la régression linéaire.

model_lineaire = LinearRegression()

model_lineaire.fit(X_train, y_train)

pred_lineaire = model_lineaire.predict(X_test)

 

mae_lineaire = mean_absolute_error(y_test, pred_lineaire)

print(f"MAE regression lineaire : {mae_lineaire:.0f} MW")

Le RandomForest fait-il vraiment mieux que la régression linéaire ? Si l'écart est faible, qu'est-ce que cela vous dit sur la complexité réellement nécessaire pour ce problème ?

    Pourquoi comparer à un modèle simple : Un modèle plus complexe n'est pas automatiquement meilleur qu'un modèle simple: il est surtout plus flexible pour capturer des relations non linéaires. S'il n'apporte qu'un gain marginal, le modèle simple peut être préférable en pratique

Évaluer

y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)

mape = mean_absolute_percentage_error(y_test, y_pred)

print(f"MAE : {mae:.0f} MW - MAPE : {mape*100:.1f}%")

    La MAE (Mean Absolute Error) est l'écart moyen, en MW, entre la prédiction et la vraie valeur. La MAPE (Mean Absolute Percentage Error) exprime ce même écart en pourcentage de la vraie valeur. Aucune des deux n'est "meilleure" dans l'absolu : la MAE parle en MW concrets, la MAPE relativise l'erreur.

Importance des features et analyse des résidus

importances = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)

importances.plot(kind="bar", title="Importance des features")

plt.show()

 

residus = y_test.values - y_pred

 

plt.figure(figsize=(12, 4))

plt.plot(residus)

plt.axhline(0, color="red", linestyle="--")

plt.title("Residus (erreur) dans le temps")

plt.show()

 

df_test = df.iloc[X_test.index].copy()

df_test["erreur_abs"] = abs(residus)

df_test.groupby("heure")["erreur_abs"].mean().plot(kind="bar", title="Erreur moyenne par heure")

plt.show()

Ce classement correspond-il à ce que vous attendiez, et à ce qu'indiquait la matrice de corrélation ? Si une variable ressort ici comme importante sans être fortement corrélée linéairement à la consommation, quelle explication proposez-vous ?

    Un score global (MAE) cache des disparités : le modèle peut très bien prédire certaines heures et se tromper largement sur d'autres. L'analyse des résidus permet de le vérifier.

Y a-t-il des heures ou des périodes où le modèle se trompe systématiquement plus ? Une piste d'explication ?

    Deux modèles avec la même MAE globale peuvent avoir des comportements très différents : l'un se trompe un peu partout de façon régulière, l'autre est excellent la plupart du temps mais se trompe fortement sur des cas précis (ex. les heures de pointe, justement les moments où une bonne prédiction compte le plus pour EnergIA). L'analyse des résidus permet de détecter ce genre de faiblesse invisible dans un score unique.

Comparer à une baseline naïve

baseline_pred = df["consommation_mw"].shift(24).iloc[X_test.index]

mae_baseline = mean_absolute_error(y_test, baseline_pred.bfill())

print(f"MAE baseline (J-1) : {mae_baseline:.0f} MW")

Votre modèle fait-il mieux qu'une prédiction naïve ("même valeur qu'hier à la même heure") ? Si non, pourquoi selon vous ?

    Si un modèle plus complexe ne fait pas mieux qu'une règle aussi simple, il n'apporte aucune valeur malgré sa sophistication apparente.
