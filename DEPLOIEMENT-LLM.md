# README LLM

## Ajout du LLM au coeur de notre application

Cette phase de déploiement consiste à ajouter dans notre flux de traitement des données et de production de prescriptions, un grand modèle de langage.

Nous choisissons `gemma4:e4b` car il offre un équilibre entre raisonnement, appels d'outils et linguistique. De plus, il foncitonne, un peu plus lentement, mais tout aussi bien en sollicitant les CPUs que les GPUs.

Nous procédons donc à l'ajout d'un serveur MCP pour gérer les prompts et appels d'outils pour la récupération des données indispensables à la production de réponse par le LLM.

```mermaid
---
config:
  layoout:elk
  theme:redux
---
flowchart TB
    n1["Human"] --> n2["Gateway"]
    n3["MCP"] -- interroge --> n4["EnergIA Service(services/eneergia-service.py)"]
    n3 -- répond --> n2
    n3 -- prompte --> n5["LLM"]
    n5 -- répond --> n3
    n2 -- requête --> n3
    n4 -- renvoie les résultats --> n3

    n1@{ shape: rect}
```

## Changement lancement projet

Afin de solutionner le fait que tous les membres de l'équipe ne disposent pas de GPU pour faire fonctionner le modèle d'IA, nous avons un docker-compose.gpu_or_cpu.yml spécifique pour compiler et monter les conteneurs de notre application en prenant en charge ou non l'utilisation du CPU.

1. Créer un fichier dans le répertoire racine de notre application, côte à côte avec le docker-compose.yml.

    J'ai choisi comme nom pour ce fichier : ```docker-compose.gpu_or_cpu.yml```, il est ensuite nécessaire d'y ajouter le contenu suivant :

    ```yml
    services:
      llm:
    #    deploy:
    #     resources:
    #        limits:
    #          cpus: '2'
    #
    #        reservations:
    #          cpus: '1'
        deploy:
          resources:
            reservations:
              devices:
                - driver: nvidia
                  count: all
                  capabilities: [gpu]
    ```

2. Tu l'enregistres

3. Puis dans un terminal ouvert dans le dossier racine du projet :

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu_or_cpu.yml up -d --build
```

## Déploiement du LLM et du serveur MCP

Le parcours utilisateur du projet EnergIA déployé initialement est très simple :

```mermaid
---
config:
  layout: elk
---
graph LR
    Utilisateur[Utilisateur]
    Gateway[Gateway]
    FastAPI[FastAPI<br/>ms-python]
    EnergIA[Moteur EnergIA]
    Resultat[Affichage du résultat]
    
    Utilisateur -->|Requête| Gateway
    Gateway -->|Route| FastAPI
    FastAPI -->|Traite| EnergIA
    EnergIA -->|Retourne données| FastAPI
    FastAPI -->|Répond| Resultat
    
    classDef userNode stroke:#818cf8,fill:#eef2ff
    classDef gatewayNode stroke:#2dd4bf,fill:#f0fdfa
    classDef apiNode stroke:#38bdf8,fill:#f0f9ff
    classDef engineNode stroke:#a78bfa,fill:#f5f3ff
    classDef resultNode stroke:#4ade80,fill:#f0fdf4
    
    class Utilisateur userNode
    class Gateway gatewayNode
    class FastAPI apiNode
    class EnergIA engineNode
    class Resultat resultNode
```

A l'issue des 3 phases de déploiement des différentes fonctionnalités et services composant notre application, le parcours utilisateur a notablement été modifié :

```mermaid
flowchart LR
 subgraph FRONT["Interface web"]
        HTML["index.html<br>s2"]
        CSS["style.css<br>s3"]
        JS["input_checks.js<br>s4"]
        NODE["index.js<br>s5"]
  end
 subgraph INTELLIGENCE["Intelligence et orchestration"]
        SERVER["server.py<br>s6"]
        ORCH["orchestrator.py<br>s7"]
        GEMMA["Gemma 4<br>s8"]
  end
 subgraph OUTILS["Outils MCP"]
        PLANTS["list_plants<br>s9"]
        CONSUMPTION["get_consumption<br>s10"]
        SIMULATION["simulate_phase3<br>s11"]
        TOOLPY["tool.py<br>s12"]
  end
 subgraph DATA["Moteur EnergIA"]
        FASTAPI["ms-python-2<br>s13"]
        SERVICES["services/<br>s14"]
        JSON["data/<br>s15"]
  end
    HTML --- CSS
    HTML --> JS
    JS --> NODE
    SERVER --> ORCH & NODE
    ORCH --> GEMMA & SERVER
    GEMMA --> ORCH
    PLANTS --> TOOLPY
    CONSUMPTION --> TOOLPY
    SIMULATION --> TOOLPY
    FASTAPI --> SERVICES
    SERVICES --> JSON
    USER(["👤 utilisateur"]) -- question --> HTML
    NODE -- POST /assistant --> SERVER
    ORCH -- outil choisi --> PLANTS & CONSUMPTION & SIMULATION
    TOOLPY -- requête avec SECURITY_TOKEN --> FASTAPI
    FASTAPI -- données --> TOOLPY
    TOOLPY -- résultat MCP --> ORCH
    ORCH -- résultat à expliquer --> GEMMA
    GEMMA -- réponse en français --> ORCH
    NODE --> JS
    JS -- affichage --> USER

     HTML:::frontend
     CSS:::frontend
     JS:::frontend
     NODE:::frontend
     SERVER:::intelligence
     ORCH:::intelligence
     GEMMA:::intelligence
     PLANTS:::tools
     CONSUMPTION:::tools
     SIMULATION:::tools
     TOOLPY:::tools
     FASTAPI:::data
     SERVICES:::data
     JSON:::data
     USER:::user
    classDef user fill:#fef3c7,stroke:#f59e0b,color:#78350f,stroke-width:3px
    classDef frontend fill:#dbeafe,stroke:#2563eb,color:#1e3a8a,stroke-width:2px
    classDef intelligence fill:#ede9fe,stroke:#7c3aed,color:#4c1d95,stroke-width:2px
    classDef tools fill:#dcfce7,stroke:#16a34a,color:#14532d,stroke-width:2px
    classDef data fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px
```

L'utilisateur a le choix d'utiliser le moteur prescriptif régional mais peut également faire sa demande au système d'aide à la décision qui s'appuie sur un modèle Gemma4:e4b hébergé dans conteneur Ollama.

![Page d'accueil EnergIA](./docs/web-ui-homepage.png "Aperçu de la page d'accueil du système d'aide à la décision EnergIA")

[!WARNING]
Tout le fonctionnement de l'application est régie par des règles simples mais importantes :

* Les calculs _**métier**_ sont isolés au sein du micro-service `ms-python-2` (Le serveur MCP ne refait pas les calculs).
* `tool.py` récupère les données en appelant FastAPI (ms-python-2).
* `gemma 4` ne doit pas inventer les données energIA.
* La réponse doit être construite à partir du JSON retourné par FastAPI.

### Conteneurisation

* **gateway** : Utilise Node.js et Express, écoute sur le port 3000.
Point d'entrée pour l'utilisateur, la passerelle fournit l'interface web et transmet les requêtes au réseau de micro-services (_ms-python-2_, _mcp-server_, _llm_).

> ```docker pull tomtoomuch/energia-gateway```

* **ms-python** : Utilise FastAPI, écoute sur le port 8000.
Ce conteneur contient le moteur prescriptif régional issu de la phase de déploiement initial.

> ```docker pull tomtoomuch/energia-ms-python```

* **ms-python-2** : Utilise FastAPI, écoute sur le port 8002. Ce conteneur contient le moteur temporel actuel, qui permet de lancer des simulations (Phases 1, 2 et 3) et fournit les outils et données au serveur MCP.

> ```docker pull tomtoomuch/energia-ms-python-2```

* **llm** : Utilise l'image officielle d'Ollama fournie par Docker, écoute sur le port 11434. Le modèle est récupéré puis chargé automatiquement au montage du conteneur. Nous utilisons le modèle [`gemma4:e4b`](https://ollama.com/library/gemma4 "Lien vers la page du modèle de langage gemma4:e4b disponible dans la bibliothèque de modèle d'Ollama). Un fichier docker-commpose.gpu_or_cpu.yml permet d'activer la prise en charge des GPU pour le LLM au montage de l'application.

> ```docker pull tomtoomuch/energia-llm```

* **mcp-server** : Utilise FastMCP, écoute sur le port 8003. Expose les ressources, les outils MCP et la route HTTP (```/assistant```) vers le système d'aide à la décision.

> ```docker pull tomtoomuch/energia-mcp-server```

### Arborescence du projet

#### Fichiers à la racine

* `docker-compose.yml` : Configure les ports, les dépendances et les fichiers `.env`.
* `.env` : Contient les variables de configuration (ports, adresses internes, `SECURITY_TOKEN`, modèle ollama).
* [`README.md`](./README.md "Fichier README.md du déploiement initial du moteur prescriptif régional") : Présente le moteur principal et les commandes historiques.
* [`README-PHASES.md`](./README-PHASES.md "Fichier README-PHASES.md décrivant les 3 phases de déploiement successives") : Décrit le système de simulation de consommation dans le temps par le moteur prescriptif national.
* `Comment-Demarer-proj.txt` : Contient les commandes de démarrage et de vérification.
* `introduction.txt` : Explique l’évolution du moteur et les différentes parties du projet.

#### Structure des dossiers

**gateway/**

* `Dockerfile` : construit le conteneur Node.js, installe les dépendances et démarre gatewawy/index.js
* `package.json` : contient les dépendances Node.js (`express`, `axios`), fournit le serveur HTTP et permet d'envoyer les requêtes sur le réseau de microservices
* `index.js` : crée la gateway Express et expose l'ensemble des fonctionnalités de notre application avec endpoints pour la santé (`/health*`), récupération de données (`/plants`, `/regions`, `/network`), simulation (`/simulate`), et l'assistant (`POST /assistant`).

**mcp_server/**

* `Dockerfile` : Construit l'image du serveur MCP.
* `requirements.txt` : Contient les dépendances Python (`mcp`, `httpx`, `ollama`, `python-dotenv`).
* `tool.py` : Le client HTTP de FastAPI, gère la construction des requêtes vers FastAPI en y ajoutant `SECURITY_TOKEN`.
* `services/apply_consumption_events.py` : Détermine et applique la variation d’un événement.
* `services/scenario_json.py` : Valide, exporte ou importe un scénario.
* `services/charts.py` : Génère les graphiques de la phase 2.
* `services/long_simulation.py` : Répète les données journalières pour simuler sur une semaine, un mois ou une année.
* `services/energia_service.py` : Contient une façade métier expérimentale (appelée par MCP).
* `services/dispatch.py` : Contient une fonction historique simple de répartition.

### Fichiers de données

* `energia-journee-reference-consommation.json` : Contient les 96 horaires de la journée (consommation nationale et régionale).
* `energia-parametres-temporels-nucleaire.json` : Contient la production initiale, les puissances min/max, et les rampes.
* `energia-production-non-pilotable.json` : Contient la production solaire et éolienne.
* `energia-scenarios-phase3-exemples.json` : Contient les scénarios (ex: `evening_peak_occitanie`).
* `parc_nucleaire_prescriptif_france.json` : Contient les centrales, régions, liaisons et paramètres de simulation.

### Tests

* `ms-python/tests` : Contient les tests du premier moteur.
* `ms-python-2/tests/test_engine.py` : Teste le moteur et les allocations.
* `ms-python-2/tests/test_temporal_phases.py` : Teste les phases 1, 2 et 3.

### Variables d’environnement

**Dans Docker :**

* `PYTHON_SERVICE_URL_2`: `http://ms-python-2:8002`
* `PYTHON_MCP_URL`: `http://mcp-server:8003`
* `MCP_URL`: `http://mcp-server:8003/mcp`
* `OLLAMA_HOST`: `http://llm:11434`
* `OLLAMA_MODEL`: `gemma4:e4b`

**Depuis Windows :**

* `http://127.0.0.1:8002`
* `http://127.0.0.1:8003`
* `http://127.0.0.1:11434`

_**Note :**_ Les noms de services (`ms-python-2`, `mcp-server`, `llm`) ne fonctionnent que dans le réseau Docker.

### Limitations actuelles

* La question doit respecter le format : `consommation région heure` (Ex: consommation occitanie 18:00).
* La consommation retournée est une référence, pas une mesure en temps réel.
* Gemma 4 ne choisit pas encore automatiquement l'outil MCP.
* Une simulation phase 3 complète peut produire un très grand JSON.
* Les réponses de Gemma 4 peuvent varier.
* `mcp_server` ne possède pas encore de tests automatisés.

## Commandes pour tester le projet

1. **Préparation :**

    ```powershell
    cd C:\python-projs\energIA-prescription-nationale
    ```

2. **Vérification Docker :**

    ```powershell
    docker version
    ```

3. **Construction et Démarrage :**

    ```powershell
    docker compose build
    docker compose up -d
    ```

4. **Vérification des services :**

    ```powershell
    docker compose ps
    # Doivent être Up : gateway, ms-python, ms-python-2, llm, mcp-server
    ```

5. **Tests API :**

    ```powershell
    # Vérifier FastAPI
    Invoke-RestMethod http://127.0.0.1:8002/health

    # Vérifier MCP
    Invoke-RestMethod http://127.0.0.1:8003/health

    # Vérifier la gateway
    Invoke-RestMethod http://127.0.0.1:3000/health

    # Vérifier ollama
    Invoke-RestMethod http://127.0.0.1:11434/api/tags

    # Lister les modèles installés
    docker compose exec llm ollama list
    # Modèle attendu : gemma4:e4b
    ```

6. **Test des interactions :**

    ```powershell
    # Tester MCP vers FastAPI
    docker compose exec mcp-server python -c "import tool; print(tool.get_plants()['plants_count'])"
    # Résultat attendu : 18

    # Tester l’assistant dans le terminal
    docker compose exec -it mcp-server python orchestrator.py
    # Quesiton à poser 
    consommation occitanie 18:00

    # Tester l’interface web
    # Ouvrir dans le navigateur : http://127.0.0.1:3000
    # Écrire : consommation occitanie 18:00
    # Cliquer sur : envoyer la question
    ```

7. **Journaux et maintenance :**

    ```powershell
    # Consulter les logs (dernier filtre)
    docker compose logs --tail=100 gateway
    # logs de FastAPI
    docker compose logs --tail=100 ms-python-2
    # logs du serveur MCP
    docker compose logs --tail=100 mcp-server
    # logs de ollama
    docker compose logs --tail=100 llm

    # Suivre tous les logs en direct
    docker compose logs -f

    # Reconstruire après une modification (Ex: mcp_server)
    docker compose build mcp-server
    docker compose up -d --force-recreate mcp-server

    # Arrêter le projet
    docker compose down

    # Vérifier git avant le transfert
    git status
    git log --oneline -15
    ```
