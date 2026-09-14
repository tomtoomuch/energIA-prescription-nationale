energIA
│
├── docker-compose.yml
│     "démarre tous les services"
│
├── .env
│     "contient les ports les URLs le modèle et le token"
│
├── gateway
│   │
│   ├── Dockerfile
│   │     "construit le conteneur de la gateway"
│   │
│   ├── package.json
│   │     "contient les dépendances node js"
│   │
│   ├── index.js
│   │     "reçoit les requêtes du navigateur"
│   │     "transmet les requêtes aux autres services"
│   │
│   └── public
│       │
│       └── index.html
│             "affiche la carte"
│             "affiche le formulaire assistant"
│             "envoie la question vers POST /assistant"
│
├── mcp_server
│   │
│   ├── dockerfile
│   │     "construit le conteneur MCP""
│   │
│   ├── requirements.txt
│   │     "contient les dépendances python"
│   │
│   ├── server.py
│   │     "crée le serveur MCP"
│   │     "expose les outils MCP"
│   │     "expose les ressources MCP"
│   │     "expose POST /assistant"
│   │
│   ├── tool.py
│   │     "appelle les routes FastAPI"
│   │     "transmet x-api-key"
│   │     "vérifie les réponses JSON"
│   │
│   ├── orchestrator.py
│   │     "reçoit la question"
│   │     "extrait la région et l’heure"
│   │     "demande la donnée à MCP"
│   │     "construit le prompt"
│   │     "demande la réponse à gemma 4"
│   │
│   └── ollama_client.py
│         "se connecte à ollama"
│         "utilise gemma4:e4b"
│         "envoie le prompt"
│         "retourne la réponse"
│
├── ms-python-2
│   │
│   ├── main.py
│   │     "crée l’API FastAPI"
│   │     "expose les phases 1 2 et 3"
│   │
│   ├── data
│   │   │
│   │   ├── parc_nucleaire_prescriptif_france.json
│   │   │     "centrales régions et réseau"
│   │   │
│   │   ├── energia-journee-reference-consommation.json
│   │   │     "consommations des 96 quarts d’heure"
│   │   │
│   │   ├── energia-production-non-pilotable.json
│   │   │     "production solaire et éolienne"
│   │   │
│   │   ├── energia-parametres-temporels-nucleaire.json
│   │   │     "limites et rampes des centrales"
│   │   │
│   │   └── energia-scenarios-phase3-exemples.json
│   │         "événements des scénarios"
│   │
│   ├── services
│   │   │
│   │   ├── graph_loader.py
│   │   │     "charge et valide les données"
│   │   │
│   │   ├── nuclear_dataframe.py
│   │   │     "prépare les centrales dans une DataFrame"
│   │   │
│   │   ├── dijkstra.py
│   │   │     "cherche le meilleur chemin"
│   │   │
│   │   ├── capacity.py
│   │   │     "calcule les capacités disponibles"
│   │   │
│   │   ├── candidates.py
│   │   │     "sélectionne les centrales candidates"
│   │   │
│   │   ├── priority.py
│   │   │     "détermine les priorités"
│   │   │
│   │   ├── score.py
│   │   │     "calcule le score des centrales"
│   │   │
│   │   ├── allocation.py
│   │   │     "répartit la production"
│   │   │
│   │   ├── temporal_allocation.py
│   │   │     "répartit les variations régionales"
│   │   │
│   │   ├── temporal_engine.py
│   │   │     "exécute les simulations temporelles"
│   │   │
│   │   ├── apply_consumption_events.py
│   │   │     "applique les événements de phase 3"
│   │   │
│   │   ├── scenario_json.py
│   │   │     "importe et exporte les scénarios"
│   │   │
│   │   ├── charts.py
│   │   │     "génère les graphiques"
│   │   │
│   │   └── long_simulation.py
│   │         "simule une période longue"
│   │
│   └── tests
│         "vérifie le moteur et les phases"
│
└── ms-python
      "contient la première version historique du moteur"


```mermaid
---
config:
  layout: elk
  markdownAutoWrap: false
---
flowchart LR
    root["energIA/"]

    tree["`├── docker-compose.yml<br/>├── .env<br/>├── gateway/<br/>│   ├── Dockerfile<br/>│   ├── package.json<br/>│   ├── index.js<br/>│   └── public/<br/>│       └── index.html<br/>├── mcp_server/<br/>│   ├── dockerfile<br/>│   ├── requirements.txt<br/>│   ├── server.py<br/>│   ├── tool.py<br/>│   ├── orchestrator.py<br/>│   └── ollama_client.py<br/>├── ms-python-2/<br/>│   ├── main.py<br/>│   ├── data/<br/>│   │   ├── parc_nucleaire_prescriptif_france.json<br/>│   │   ├── energia-journee-reference-consommation.json<br/>│   │   ├── energia-production-non-pilotable.json<br/>│   │   ├── energia-parametres-temporels-nucleaire.json<br/>│   │   └── energia-scenarios-phase3-exemples.json<br/>│   ├── services/<br/>│   │   ├── graph_loader.py<br/>│   │   ├── nuclear_dataframe.py<br/>│   │   ├── dijkstra.py<br/>│   │   ├── capacity.py<br/>│   │   ├── candidates.py<br/>│   │   ├── priority.py<br/>│   │   ├── score.py<br/>│   │   ├── allocation.py<br/>│   │   ├── temporal_allocation.py<br/>│   │   ├── temporal_engine.py<br/>│   │   ├── apply_consumption_events.py<br/>│   │   ├── scenario_json.py<br/>│   │   ├── charts.py<br/>│   │   └── long_simulation.py<br/>│   └── tests/<br/>└── ms-python/`"]

    notes@{ shape: comment, label: "`démarre tous les services<br/>contient les ports, les URLs, le modèle et le token<br/><br/>construit le conteneur de la gateway<br/>contient les dépendances Node.js<br/>reçoit les requêtes du navigateur ; les transmet aux autres services<br/><br/>affiche la carte et le formulaire assistant ; envoie la question vers POST /assistant<br/><br/>construit le conteneur MCP<br/>contient les dépendances Python<br/>crée le serveur MCP ; expose les outils, les ressources et POST /assistant<br/>appelle les routes FastAPI ; transmet x-api-key ; vérifie les réponses JSON<br/>reçoit la question ; extrait la région et l’heure ; demande la donnée ; construit le prompt<br/>se connecte à Ollama ; utilise gemma4:e4b ; envoie le prompt ; retourne la réponse<br/><br/>crée l’API FastAPI ; expose les phases 1, 2 et 3<br/><br/>centrales, régions et réseau<br/>consommations des 96 quarts d’heure<br/>production solaire et éolienne<br/>limites et rampes des centrales<br/>événements des scénarios<br/><br/>charge et valide les données<br/>prépare les centrales dans une DataFrame<br/>cherche le meilleur chemin<br/>calcule les capacités disponibles<br/>sélectionne les centrales candidates<br/>détermine les priorités<br/>calcule le score des centrales<br/>répartit la production<br/>répartit les variations régionales<br/>exécute les simulations temporelles<br/>applique les événements de phase 3<br/>importe et exporte les scénarios<br/>génère les graphiques<br/>simule une période longue<br/><br/>vérifie le moteur et les phases<br/>contient la première version historique du moteur`" }

    root --> tree
    tree -.-> notes
```