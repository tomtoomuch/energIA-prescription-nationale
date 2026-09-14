# Guide de démarrage et de test du projet EnergIA

Ce guide détaille les étapes nécessaires pour démarrer, vérifier, et tester l'écosystème de services lié au projet EnergIA, incluant l'intégration de FastAPI, d'un serveur MCP, et de Gemma 4 via Ollama.

## Prérequis

Avant de commencer, assurez-vous que les prérequis suivants sont remplis :

* Le service Docker Desktop doit être démarré.
* Le fichier `.env` doit contenir toutes les variables d'environnement nécessaires.
* Le modèle `gemma4:e4b` doit être disponible localement via Ollama. [!WARNING]à vérifier

### Configuration du fichier `.env`

Le fichier `.env` doit contenir au minimum les variables suivantes.
**Attention :** Veuillez conserver la vraie valeur du token déjà utilisée par le projet pour `SECURITY_TOKEN`.

```bash
GATEWAY_PORT=3000
PYTHON_PORT=8000
PYTHON_PORT_2=8002
MCP_PORT_3=8003
PYTHON_SERVICE_URL=[http://ms-python:8000](http://ms-python:8000)
PYTHON_SERVICE_URL_2=[http://ms-python-2:8002](http://ms-python-2:8002)
MCP_URL=[http://mcp-server:8003/mcp](http://mcp-server:8003/mcp)
OLLAMA_HOST=[http://llm:11434](http://llm:11434)
OLLAMA_MODEL=gemma4:e4b
SECURITY_TOKEN=votre_token
```

## Étapes de déploiement et de tests

### Étape 1 : Ouvrir le projet

Naviguez dans le répertoire racine du projet :

```bash
cd nergIA-prescription-nationale
```

### Étape 2 : Vérifier le fichier ```.env```

Voir les prérequis ci-dessus pour la structure minimale attendue.

### Étape 3 : Construire les images Docker

Afin de construire toutes les images nécessaires au déploiement de l'application, en prenant en considération le fait que la machine dispose de GPUs ou non, nous compilons à l'aide de plusieurs fichiers de configuration 'Compose' (l'option -f nous permet de sélectionner les fichiers à fusionner lors de la compilation et/ou du montage) :

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu_or_cpu.yml build --no-cache
```

Toutes les images sont disponibles depuis le repository DockerHub.

### Étape 4 : Démarrer les services

Lancer tous les services en arrière-plan :
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu_or_cpu.yml up -d
```

Pour effectuer la compilation et le montage des images pour lancer les services en une seule ligne de commande :

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu_or_cpu.yml up -d --build
```

### Étape 5 : Vérifier les conteneurs

Vérifier que les services essentiels sont bien actifs :

```bash
docker compose ps
```

Le terminal doit vous afficher :

| NAME                  | IMAGE                          | COMMAND                | SERVICE     | CREATED        | STATUS        | PORTS                                           |
| --------------------- | ------------------------------ | ---------------------- | ----------- | -------------- | ------------- | ----------------------------------------------- |
| energia-gateway-1     | energia-gateway                | "docker-entrypoint.s…" | gateway     | 24 seconds ago | **Up** 22 seconds | 0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp     |
| energia-llm-1         | ollama/ollama:latest           | "/bin/sh -c ' ollama…" | llm         | 4 hours ago    | **Up** 23 seconds | 0.0.0.0:11434->11434/tcp, [::]:11434->11434/tcp |
| energia-mcp-server-1  | energia-mcp-server             | "python server.py"     | mcp-server  | 24 seconds ago | **Up** 23 seconds | 0.0.0.0:8003->8003/tcp, [::]:8003->8003/tcp     |
| energia-ms-python-1   | tomtoomuch/energia-ms-python   | "uvicorn main:app --…" | ms-python   | 4 hours ago    | **Up** 23 seconds | 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp     |
| energia-ms-python-2-1 | tomtoomuch/energia-ms-python-2 | "uvicorn main:app --…" | ms-python-2 | 4 hours ago    | **Up** 23 seconds | 0.0.0.0:8002->8002/tcp, [::]:8002->8002/tcp     |

**Vérification attendue :** Les services gateway, ms-python, ms-python-2, llm, et mcp-server doivent être en statut actif (```Up```).

### Étape 6 : Consulter les erreurs éventuelles (Logs)

* Pour **suivre** uniquement le serveur **MCP** :

   ```bash
   docker compose logs -f mcp-server
   ```

* Pour **suivre** uniquement **Ollama** :

```bash
docker compose logs -f llm
```

* Pour **suivre** les **logs généraux** (en récupérant les 100 dernières lignes à l'aide de l'option ```--tail```) :

```bash
docker compose logs --tail=100
```

### Étape 7 : Vérifier FastAPI

Tester l'endpoint de santé de l'application FastAPI (ms-python-2) :

```powershell
Invoke-RestMethod http://127.0.0.1:8002/health
```

La réponse attendue doit indiquer que le service EnergIA fonctionne :

```powershell
status service phases
------ ------- ------
ok     EnergIA {1, 2, 3}
```

### Étape 8 : Vérifier le serveur MCP

Tester l'endpoint de santé du serveur MCP :
```powershell
Invoke-RestMethod http://127.0.0.1:8003/health
```

L'objet JSON retourné dans la réponse du système doit contenir :

```powershell
status service
------ -------
ok     EnergIA MCP Server
```

### Étape 9 : Vérifier Ollama

Vérifier la présence et le bon fonctionnement du modèle ```gemma4:e4b``` :

1. Lister les modèles installés :

   ```powershell
   Invoke-RestMethod http://127.0.0.1:11434/api/tags
   ```

   >Les commandes Powershell Invoke-RestMethod peuvent être remplacés par l'utilisation de l'instruction curl dans l'invite de commande cmd.exe.

2. Vérifier la présence du modèle :

   En vous plaçant dans le dossier racine du projet :

   ```bash
   docker compose exec llm ollama list
   ```

   L'instruction vous retourne normalement : 

   ```bash
      NAME          ID              SIZE      MODIFIED
   qwen3:1.7b    8f68893c685c    1.4 GB    4 days ago
   gemma4:e4b    c6eb396dbd59    9.6 GB    6 days ago
   ```

   Si gemma4:e4b est absent, exécutez :

   ```bash
   docker compose exec llm ollama pull gemma4:e4b
   ```

3. Tester le modèle :

   ```bash
   docker compose exec llm ollama run gemma4:e4b "réponds uniquement par ok"
   ```

### Étape 10 : Tester la connexion MCP vers FastAPI

Vérifier que le serveur MCP peut interagir avec les données des centrales EnergIA.

1. Afficher toutes les centrales :

   ```bash
   docker compose exec mcp-server python tool.py
   ```

2. Afficher uniquement le nombre de centrales :

   ```bash
   docker compose exec mcp-server python -c "import tool; print(tool.get_plants()['plants_count'])"
   ```

   Le terminal doit vous retourner : **```18```**

### Étape 11 : Lancer MCP Inspector en local

1. Ouvrir un nouveau terminal.

2. Naviguer vers le répertoire du micro-service du serveur MCP à l'aide de la commande ```cd```.

3. Activer l'environnement virtuel (adapter le chemin si nécessaire) :

   ```bash
   .\.venv\Scripts\Activate.ps1
   ```

4. Définir l'adresse locale de FastAPI (si elle diffère de la valeur par défaut) :

   ```env
   PYTHON_SERVICE_URL_2="http://127.0.0.1:8002"
   ```

5. Tester l'importation des outils :

   ```bash
   python -c "import tool; print(tool.get_plants()['plants_count'])"
   ```

6. Lancer l'inspecteur du serveur MCP :

   ```bash
   mcp dev server.py
   ```

   * Dans l'interface, tester les ressources dans l'onglet Resources.
   * Dans l'interface, tester les outils dans l'onglet Tools.

### Étape 12 : Tester la consommation (Appel de données)

Utiliser l'inspecteur MCP pour simuler une demande de consommation :

```json
{
"region_id": "occitanie",
"timestamp": "16:00"
}
```

**Résultat attendu :** Une consommation provenant de FastAPI doit être reçue.

### Étape 13 : Envoyer la question à Gemma 4 (Orchestration complète)

Depuis la racine du projet :

```bash
cd C:\python-projs\energIA-prescription-nationale
```

Lancer l'orchestrateur :

```bash
docker compose exec -it mcp-server python orchestrator.py
```

Poser la question de test :

```txt
consommation occitanie 16:00
```

**Opérations effectuées à l'exécution :**

1. _**orchestrator.py**_ reçoit la question.
2. Le _**MCP**_ récupère les données de consommation.
3. _**tool.py**_ appelle FastAPI (ms-python-2).
4. _**FastAPI**_ retourne la donnée EnergIA.
5. _**orchestrator.py**_ construit le prompt.
6. _**ollama_client.py**_ envoie le prompt à Gemma 4.
7. _**Gemma 4**_ rédige la réponse finale.

### Étape 14 : Accéder à la Gateway

Ouvrir le navigateur et naviguer vers :

```bash
http://127.0.0.1:3000
```

### Étape 15 : Arrêter le projet

Arrêter proprement tous les services Docker :

```bash
docker compose down
```

### Étape 16 : Redémarrer après une modification Python

En cas de modification de code dans le service mcp-server :

1. Reconstruire l'image :

   ```bash
   docker compose build mcp-server
   ```

2. Redémarrer en forçant la recréation du conteneur :

```bash
docker compose up -d --force-recreate mcp-server
```

### Étape 17 : Vérifier Git et l'inspecteur MCP

Vérifications finales du contrôle de version et de l'outil local :
```bash
git status
git log --oneline -10
npx @modelcontextprotocol/inspector
```
