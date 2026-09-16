# EnergIA

EnergIA réunit un moteur de simulation énergétique, une prévision de consommation électrique régionale, un assistant Gemma via Ollama et une interface web servie par un gateway.

## Architecture

| Dossier | Rôle |
| --- | --- |
| `gateway/` | Serveur Node.js/Express et pages web publiques. |
| `ms-python/` | Premier moteur de simulation régionale. |
| `ms-python-2/` | Moteur temporel des phases 1, 2 et 3. |
| `prediction/` | Extraction des données 2025, création du CSV, entraînement sklearn et graphiques. |
| `mcp_server/` | Outils MCP et orchestration des réponses de Gemma. |
| `llm/` | Données locales d’Ollama. |
| `index.py` | Préparation des données nécessaires, entraînement si nécessaire et démarrage Docker. |
| `docker-compose.yml` | Définition des six services Docker. |

Le navigateur appelle le gateway sur le port `3000`. Le gateway contacte les services Python et le serveur MCP. Le serveur MCP utilise Ollama pour formuler les réponses de l’assistant.

Les six services définis par Docker Compose sont `gateway`, `ms-python`, `ms-python-2`, `prediction-api`, `llm` et `mcp-server`.

## Prérequis

- Python et un environnement virtuel pour exécuter `index.py` et l’entraînement local.
- Docker Desktop démarré, avec Docker Compose disponible.
- Une connexion Internet pour construire les images Docker et télécharger le modèle Ollama au premier lancement.
- Les fichiers de données dans `prediction/data/`, ou un accès fonctionnel aux API utilisées par l’extraction.

Sous PowerShell, depuis la racine du projet :

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r prediction\requirements.txt
Copy-Item .env.example .env
```

Ouvrir `.env` et remplacer `SECURITY_TOKEN=replace-with-a-shared-local-token` par un token local. Ne pas publier `.env` ni le token.

## Données de prédiction

Les quatre sources JSON attendues dans `prediction/data/` sont :

| Fichier | Contenu | Fonction dans `prediction/etl/extraction.py` |
| --- | --- | --- |
| `eco2mix-regional.json` | Mesures électriques régionales 2025 | `telecharger_electricite()` |
| `meteo-regions.json` | Météo historique des régions | `telecharger_meteo()` |
| `calendrier-2025.json` | Jours, week-ends et jours fériés | `telecharger_calendrier()` |
| `vacances-scolaires-regions.json` | Vacances scolaires associées aux régions | `telecharger_vacances()` |

`prediction/etl/dataframe.py` fusionne ces fichiers et écrit `prediction/data/dataset_final.csv`.

`prediction/ConsomationML.py` lit ce CSV, entraîne le modèle scikit-learn, enregistre le modèle dans `prediction/modeles/` et produit les résultats dans `prediction/graphiques/`. Les graphiques comprennent notamment les corrélations, les évaluations et les comparaisons entre consommation réelle et prédite.

### Préparer les données manuellement

Les scripts peuvent être exécutés séparément :

```powershell
.\.venv\Scripts\python.exe prediction\etl\extraction.py
.\.venv\Scripts\python.exe prediction\etl\dataframe.py
.\.venv\Scripts\python.exe prediction\ConsomationML.py
```

Respecter cet ordre. Il n’est pas nécessaire de relancer l’extraction si les quatre JSON existent déjà.

L’API ODRÉ peut répondre `429 Too Many Requests`. Si `eco2mix-regional.json` existe déjà et contient les données complètes, le réutiliser évite un nouveau téléchargement. Si ce fichier manque et que l’API refuse la requête, il faut attendre que l’accès soit rétabli ou obtenir le fichier auprès d’un membre de l’équipe.

### Ce que fait `index.py`

Le `index.py` **à la racine du dépôt** effectue ces étapes :

1. Vérifier chaque JSON. Si un fichier manque, appeler uniquement la fonction d’extraction qui le crée.
2. Créer `dataset_final.csv` s’il manque ou si un JSON vient d’être créé.
3. Entraîner sklearn si le modèle ou un graphique attendu manque, ou si le CSV vient d’être reconstruit.
4. Vérifier Docker Compose, construire et démarrer les services.
5. Vérifier le gateway et la liste des graphiques disponibles.

Il n’est donc pas obligatoire de lancer les trois scripts manuellement avant `index.py` lorsque les données nécessaires sont disponibles et que les API répondent.

## Démarrer le projet

Depuis la **racine** du dépôt, après avoir démarré Docker Desktop :

```powershell
.\.venv\Scripts\python.exe .\index.py
```

Pour ne pas ouvrir automatiquement le navigateur :

```powershell
.\.venv\Scripts\python.exe .\index.py --no-browser
```

Pour forcer un nouvel entraînement avec le CSV existant :

```powershell
.\.venv\Scripts\python.exe .\index.py --retrain
```

Au premier lancement, Docker construit les images et crée les conteneurs. Le téléchargement de l’image Ollama peut prendre du temps.

Après démarrage :

- Accueil : <http://localhost:3000/>
- Graphiques par région et par mois : <http://localhost:3000/graphiques.html>
- Santé du gateway : <http://localhost:3000/health>
- Liste des graphiques disponibles : <http://localhost:3000/api/graphiques>

La page des graphiques lit les images de `prediction/graphiques/` grâce au montage Docker du gateway. Si aucune région n’apparaît, vérifier la présence des images puis la réponse de `/api/graphiques`.

## Vérifier et arrêter Docker

```powershell
docker compose config --quiet
docker compose ps
docker compose logs --tail=50
```

Pour consulter les journaux d’un service précis :

```powershell
docker compose logs --tail=100 gateway
docker compose logs --tail=100 prediction-api
docker compose logs --tail=100 mcp-server
docker compose logs --tail=100 llm
```

Pour arrêter les services du projet :

```powershell
docker compose down
```

Si la construction du gateway indique `failed to read dockerfile`, vérifier que `gateway/Dockerfile` existe et que le service `gateway` dans `docker-compose.yml` indique exactement `dockerfile: Dockerfile`, avec un **D majuscule**.

## Interface et services

Le gateway sert l’interface web et relaie les requêtes vers les autres services. Parmi ses routes :

- `/health`, `/health-ms` et `/health-ms-2` pour les vérifications ;
- `/plants`, `/regions`, `/network` et `/simulate` pour le moteur initial ;
- `/phase1/...`, `/phase2/...` et `/phase3/...` pour le moteur temporel ;
- `POST /assistant` pour l’assistant MCP et Ollama ;
- `/graphiques.html` et `/api/graphiques` pour les graphiques de prédiction.

`ms-python-2` simule une journée sur 96 pas de 15 minutes. La phase 1 utilise le parc nucléaire, la phase 2 intègre le solaire et l’éolien, et la phase 3 applique des scénarios de variation de consommation.

L’assistant suit le trajet navigateur → gateway → serveur MCP → Gemma/Ollama → outils MCP → services Python. Les résultats des simulations viennent des services Python ; Gemma les explique en langage naturel.

## Installation 

Après avoir récupéré **la branche main** :

```powershell
git pull origin main
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r prediction\requirements.txt
Copy-Item .env.example .env
```

Adapter `.env`, démarrer Docker Desktop, puis lancer :

```powershell
.\.venv\Scripts\python.exe .\index.py
```

Attention : les données locales ne sont pas toutes transférées par Git. `dataset_final.csv`, les modèles et les graphiques sont ignorés. Le JSON électrique complet est volumineux et peut dépasser la limite d’un push GitHub classique. L’équipe doit donc vérifier quels fichiers de `prediction/data/` sont réellement publiés et transmettre séparément les données manquantes si nécessaire. Sans `eco2mix-regional.json`, le premier lancement tentera ODRÉ et pourra échouer avec `429`.

## État actuel et limites

- Les prévisions sklearn sont des estimations, pas des mesures réelles
- Les données utilisées pour les simulations ne sont pas toutes des mesures en temps réel
- La qualité du modèle de prédiction doit être appréciée à partir de son évaluation, pas seulement des graphiques
- Le code actuel de `prediction/main.py` doit être vérifié avant de considérer l’API de prédiction comme opérationnelle, son entrée générique à trois variables et son import ne correspondent pas clairement au modèle enregistré et au contenu copié par son Dockerfile.
- Les README plus anciens décrivent parfois une configuration à cinq services ou un démarrage Docker différent. La configuration actuelle est celle de `docker-compose.yml` et du `index.py` racine.

## Documentation détaillée

- [`prediction/README.md`](prediction/README.md) : sources, transformation des données et méthode de modélisation.
- [`DEMARRAGE-PROJET-ENERGIA.md`](DEMARRAGE-PROJET-ENERGIA.md) : commandes de diagnostic et tests des services.
- [`DEPLOIEMENT-INITIAL.md`](DEPLOIEMENT-INITIAL.md) : moteur initial.
- [`DEPLOIEMENT-PHASES.md`](DEPLOIEMENT-PHASES.md) : phases temporelles.
- [`DEPLOIEMENT-LLM.md`](DEPLOIEMENT-LLM.md) : intégration Ollama et MCP.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) : conventions de contribution.