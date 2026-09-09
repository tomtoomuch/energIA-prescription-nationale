# README LLM

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

Afin de solutionner le fait que tous les membres  de l'équipe ne disposent pas de GPU pour faire fonctionner le modèle d'IA, nous avons un docker-compose.gpu_or_cpu.yml spécifique pour compiler et monter les conteneurs de notre application en prenant en charge ou non l'utilisation du CPU.

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

