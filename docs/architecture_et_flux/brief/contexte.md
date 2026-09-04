# EnergIA

## Contexte

Le projet EnergIA n'a pour l'instant aucune modélisation de flux de données ni de base de données : tout repose sur un fichier JSON statique. Avant d'intégrer un module de prédiction de consommation dans l'architecture microservices existante (gateway Express + service Python), vous devez réfléchir à quelles données sont pertinentes, d'où elles viennent, comment elles circulent, et où elles sont stockées.

En data science comme en ingénierie de données, la qualité d'une prédiction dépend d'abord de la pertinence des données utilisées, pas seulement de l'algorithme choisi. Un excellent modèle nourri avec les mauvaises variables donnera de mauvais résultats ; un modèle simple nourri avec les bonnes variables peut suffire.

## Travail attendu

-> Cataloguer les dimensions intéressantes pour prédire une consommation

Avant de chercher des sources de données, listez et discutez en groupe quelles variables (dimensions) pourraient réellement expliquer les variations de consommation électrique. Le tableau ci-dessous n'est pas à recopier tel quel : il sert de point de départ à compléter, discuter, et prioriser.

### Dimensions temporelles exemples

| Dimension | Pourquoi c'est intéressant |

| Heure de la journée | Pics de consommation matin/soir (lever, retour du travail, préparation des repas) |

| Vacances scolaires | En France, zones A/B/C avec des dates différentes selon les régions |

| Saison / mois | Effet chauffage l'hiver, effet climatisation l'été |

| Tendance longue durée | Évolution année après année : croissance démographique, efficacité énergétique des logements, électrification des usages (ex. véhicules électriques) qui augmente la conso de fond |

### Dimensions météo

| Dimension | Pourquoi c'est intéressant |

| Température | Le signal le plus fort en général : chauffage l'hiver, climatisation l'été |

| Ensoleillement | Impacte l'éclairage etc |

### Autres dimensions à envisager

| Type de jour ouvré/non ouvré | Grèves, ponts, événements exceptionnels modifiant l'activité |

| Événements exceptionnels | Canicule, confinement, grand événement sportif retransmis massivement |

| Profil régional | Population, densité, part d'industrie lourde (une région très industrielle a un profil de conso différent d'une région résidentielle) |

| Tarification électrique | Heures creuses/pleines, dispositifs d'effacement, qui influencent le comportement de consommation |

## À produire par le groupe

>sélectionner les 4 à 6 dimensions jugées les plus utiles pour un premier modèle, en justifiant les choix (pertinence attendue vs facilité d'obtention de la donnée).

    **Pourquoi ne pas tout prendre**

    Ajouter des dimensions n'améliore pas toujours un modèle : au-delà d'un certain nombre de variables peu informatives ou redondantes, le risque de surapprentissage (le modèle "mémorise" du bruit plutôt que d'apprendre un vrai pattern) augmente, et la complexité du pipeline de données aussi. Mieux vaut un petit nombre de dimensions bien choisies et bien comprises qu'une liste exhaustive mal maîtrisée.

-> Cartographier les sources de données disponibles

Pour chaque dimension retenue à l'étape 1, identifiez une source de données réelle et remplissez :

| Source | Dimension(s) couverte(s) | Fréquence de mise à jour | Format | Contraintes d'accès |

| API météo (à choisir) | Température, humidité, ensoleillement | Horaire | JSON | Clé API, quota d'appels gratuits limité |

**Livrable de cette étape :** le tableau complété, avec au moins une source réelle testée (un appel ou téléchargement simple, même sans exploitation complète).
Distinguer les types de flux

    Batch (traitement périodique) : ex. récupérer l'historique RTE une fois par jour via un script planifié (cron).
    Streaming/temps réel : ex. interroger une API météo à chaque requête de prédiction.

Pour chaque source retenue, précisez si elle relève d'un flux batch ou temps réel, et pourquoi.

    batch vs streaming

    Un flux batch traite des données par lots, à intervalles réguliers (ex. une fois par jour) : adapté aux données qui ne changent pas en permanence (calendrier scolaire, historique de consommation). Un flux temps réel répond à la demande, au moment où l'information est nécessaire. Le choix conditionne l'architecture

Schématiser le flux de données

Questions à trancher :

    Le module de prédiction est-il un nouveau microservice séparé, ou une extension du service existant?
    Comment le résultat de prédiction (ex. additional_demand_mw) est-il transmis au moteur déjà développé ?
    Qui gère les erreurs si une source externe (météo, calendrier) est indisponible (fallback, valeur par défaut, message d'erreur propagé) ?

Modéliser un schéma de base de données
Anticiper les questions opérationnelles

    Où et comment stocker les clés API (météo, éventuellement autres) de façon sécurisée (variables d'environnement, jamais en dur dans le code) ?
    Que se passe-t-il si le modèle ML n'est pas encore entraîné au moment de la requête (valeur par défaut, erreur explicite) ?
    Faut-il mettre en cache les prédictions récentes pour éviter de recalculer à chaque appel ?

Piloter le modèle une fois en production (MLOps)

Un modèle entraîné une fois n'est pas figé pour toujours : la consommation réelle évolue (nouveaux usages, nouveaux logements, nouvelles habitudes), et un modèle entraîné sur des données passées se dégrade progressivement. Réfléchissez à comment vous sauriez qu'il faut agir.

    Traçabilité : Une table prediction qui stocke aussimodele_utilise Pourquoi est-ce indispensable pour pouvoir un jour comparer les performances de différentes versions du modèle ?
    Suivi de la performance dans le temps : une fois la vraie consommation connue (quelques heures ou jours plus tard), comment comparer automatiquement la prédiction stockée à la réalité observée, et recalculer une métrique (MAE) glissante sur les derniers jours ?
    Détection de dérive (*drift*) : si l'erreur moyenne augmente progressivement semaine après semaine, qu'est-ce que cela peut signifier (changement de comportement réel, nouvelle source de données mal alignée, saison inhabituelle) ?
    Réentraînement : faut-il réentraîner le modèle à intervalle fixe (ex. chaque mois), ou seulement quand un seuil de dégradation est dépassé ? Quels sont les avantages/inconvénients de chaque approche ?
    Versionning : comment garder une trace des différentes versions du modèle entraîné (fichier horodaté, numéro de version, date d'entraînement) pour pouvoir revenir en arrière si une nouvelle version se révèle moins bonne ?