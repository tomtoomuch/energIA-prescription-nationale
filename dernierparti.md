# Pipeline EnergIA : prédiction, gateway et lancement

Ce document explique comment les données de prédiction sont préparées, comment les graphiques arrivent sur la page publique et ce que lance `index.py` à la racine du projet.

## Vue d’ensemble

```text
Sources publiques
    ↓
prediction/etl/extraction.py → JSON dans prediction/data/
    ↓
prediction/etl/dataframe.py → dataset_final.csv
    ↓
prediction/ConsomationML.py → modèle sklearn, évaluation,
                              prédictions et graphiques
    ↓
prediction-api       gateway → graphiques.html
                            → ms-python
                            → ms-python-2
                            → mcp-server → Ollama / Gemma 4
```

`ms-python` réalise la simulation ponctuelle du moteur prescriptif. `ms-python-2` réalise les simulations temporelles des phases 1 à 3 avec ses données de référence. La prédiction sklearn est une autre branche du projet : ses estimations ne sont pas automatiquement utilisées comme consommation de référence par `ms-python-2`.

## Préparer les données de prédiction

`prediction/etl/extraction.py` télécharge les données électriques, météo et calendaires de 2025. Il crée les fichiers JSON dans `prediction/data/`.

`prediction/etl/dataframe.py` lit ces JSON, prépare les dates et fusionne les sources. Son résultat est `prediction/data/dataset_final.csv`, qui contient les **observations**.

`prediction/ConsomationML.py` lit ce CSV, entraîne une pipeline scikit-learn avec `LinearRegression`, puis crée :

- `prediction/modeles/modele_consommation.joblib` : modèle entraîné ;
- `prediction/modeles/modele_consommation.json` : informations sur le modèle ;
- `prediction/graphiques/correlations/` : matrices par région et mois ;
- `prediction/graphiques/reel_predit/` : comparaison réelle/prédite par région et mois ;
- `prediction/graphiques/evaluation/erreurs_par_region.csv` : évaluation de validation par région ;
- `prediction/predictions/` : estimations sauvegardées à 15 minutes.

Les courbes réelles utilisent les mesures historiques disponibles à **30 minutes**. Les valeurs à 15 et 45 minutes sont des estimations du modèle ; leur précision n’a pas été évaluée. Le CSV d’évaluation est regroupé par région sur la validation : ses chiffres ne correspondent pas au mois choisi dans la page.

## Ce que fait `index.py`

Depuis la racine du projet, lancer :

```powershell
python index.py
```

Le fichier effectue quatre étapes :

1. Il télécharge les JSON si un fichier source nécessaire manque.
2. Il reconstruit `dataset_final.csv` s’il manque.
3. Il entraîne le modèle si le `.joblib`, le JSON d’informations ou le graphique de contrôle manque.
4. Il vérifie Docker Compose, construit les images locales et démarre les six services avec `docker compose up -d --build`.

Après le démarrage, il vérifie que les six conteneurs tournent, contacte le gateway, teste les connexions vers `ms-python` et `ms-python-2`, puis vérifie que `/api/graphiques` trouve des régions. Il ouvre ensuite la page d’accueil dans le navigateur.

Avec les données, le modèle et les graphiques déjà présents, les trois premières étapes sont ignorées. Les images Docker sont tout de même reconstruites lors de `python index.py`.

Pour forcer seulement l’entraînement :

```powershell
python index.py --retrain
```

Pour retélécharger les sources, reconstruire le dataset et réentraîner :

```powershell
python index.py --rebuild-data
```

Pour ne pas ouvrir le navigateur :

```powershell
python index.py --no-browser
```

Utiliser le Python de l’environnement virtuel du projet. Docker Desktop doit être démarré avant `python index.py`. Les conteneurs continuent à fonctionner après la fin du programme, car Docker utilise l’option `-d`.

## Comment le gateway affiche les graphiques

Dans `docker-compose.yml`, le dossier local est monté dans le conteneur du gateway en lecture seule :

```yaml
volumes:
  - ./prediction/graphiques:/app/prediction-graphiques:ro
```

Dans `gateway/index.js`, `/api/graphiques` cherche les images disponibles pour chaque région et mois de 2025. La route `/graphiques/...` sert les fichiers PNG et le CSV d’évaluation.

`gateway/public/graphiques.html` contient les sélecteurs région et mois. `gateway/public/graphiques.js` appelle `/api/graphiques`, remplit les sélecteurs et affiche les deux images correspondantes.

Adresses utiles, avec le port `3000` par défaut :

```text
http://localhost:3000/
http://localhost:3000/graphiques.html
http://localhost:3000/api/graphiques
```

Si `GATEWAY_PORT` a une autre valeur dans `.env`, remplacer `3000` par ce port.

## Rôle des autres services

| Service Docker | Rôle |
|---|---|
| `gateway` | Page publique et accès aux autres services |
| `ms-python` | Parc, régions, réseau et simulation ponctuelle |
| `ms-python-2` | Consommation de référence et simulations temporelles |
| `prediction-api` | Chargement du modèle sklearn pour servir une prédiction |
| `llm` | Ollama avec Gemma 4 |
| `mcp-server` | Outils et assistant reliant Gemma 4 aux données EnergIA |

Le navigateur utilise le gateway. Gemma 4 passe par `mcp-server` pour les outils MCP existants. Les questions sur la consommation de référence et les simulations de phase 3 concernent `ms-python-2`.

## Vérifier le démarrage

```powershell
docker compose ps
docker compose logs --tail=50 gateway prediction-api mcp-server
```

`docker compose ps` montre l’état réel des conteneurs. Si `index.py` annonce un échec, lire les dernières lignes des logs du service indiqué.

La route `/api/graphiques` doit retourner une liste de régions. Une liste vide indique généralement que le gateway ne voit pas les fichiers montés dans `/app/prediction-graphiques`.

## Limites actuellement observées dans le code

Le `prediction/main.py` actuellement présent contient encore `feature_1`, `feature_2`, `feature_3` et un import `creer_dataframe`. Ces champs ne correspondent pas aux sept variables du modèle entraîné. Le gateway actuel n’a pas de route `/api/prediction`, et les outils MCP actuels ne comprennent pas `predict_consumption`. Ainsi, le **démarrage des conteneurs** et l’**affichage des graphiques** ne prouvent pas encore qu’une question à Gemma 4 peut obtenir une prédiction sklearn.

Pour valider cette partie, il faudra tester séparément une requête de prédiction et vérifier dans la réponse de l’assistant quel outil MCP a été utilisé. Une prédiction doit toujours être nommée **estimation**, jamais mesure réelle.