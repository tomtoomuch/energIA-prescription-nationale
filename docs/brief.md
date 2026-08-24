# EnergIA, Simulation temporelle et adaptation du mix énergétique

EnergIA évolue : le moteur prescriptif ne doit plus traiter un état isolé, mais simuler l’évolution du réseau au pas de 15 minutes. Vous construirez d’abord une journée de référence reposant uniquement sur le nucléaire, puis intégrerez des productions non pilotables comme le solaire et l’éolien. Enfin, vous introduirez des variations temporaires de consommation dans une ou plusieurs régions. Le moteur devra adapter progressivement la production tout en respectant les capacités des centrales, leurs vitesses de montée et de descente en puissance ainsi qu’une réserve minimale de sécurité.

## Ressources

- [Tests en Node.js](https://nodejs.org/api/test.html "Tests en Node.js")
    
- [Gestion des erreurs Express](https://expressjs.com/fr/guide/error-handling "Gestion des erreurs Express")
    
- [Dates et heures en JS](https://developer.mozilla.org/fr/docs/Web/JavaScript/Reference/Global_Objects/Date "Dates et heures en JS")
    
- [Débuter avec matplotlib](https://matplotlib.org/stable/users/explain/quick_start.html "Débuter avec matplotlib")
    
- [Datetime en Python](https://docs.python.org/3/library/datetime.html "Datetime en Python")
    
- [Documentation de Docker Compose](https://docs.docker.com/compose "Documentation de Docker Compose")
    
- [energia_journee_reference_consommation.json](https://simplonline-v3-prod.s3.eu-west-3.amazonaws.com/media/file/json/energia-journee-reference-consommation-6a8af634296c9604008122.json "energia_journee_reference_consommation.json")
    
- [energia_production_non_pilotable.json](https://simplonline-v3-prod.s3.eu-west-3.amazonaws.com/media/file/json/energia-production-non-pilotable-6a8af636a1f77556257972.json "energia_production_non_pilotable.json")
    
- [energia_parametres_temporels_nucleaire.json](https://simplonline-v3-prod.s3.eu-west-3.amazonaws.com/media/file/json/energia-parametres-temporels-nucleaire-6a8af638c43d9213214318.json "energia_parametres_temporels_nucleaire.json")
    
- [energia_scenarios_phase3_exemples](https://simplonline-v3-prod.s3.eu-west-3.amazonaws.com/media/file/json/energia-scenarios-phase3-exemples-6a8af63a53417379561753.json "energia_scenarios_phase3_exemples.json")
## Contexte du projet

Lors du premier brief EnergIA, vous avez développé un moteur prescriptif capable de répartir une augmentation de consommation entre plusieurs centrales nucléaires. Votre moteur était cependant utilisé sur une situation ponctuelle : un état du réseau, une variation de consommation et une prescription. Le commanditaire souhaite désormais faire évoluer EnergIA afin de représenter le comportement du réseau dans le temps.

Une journée de référence vous sera fournie au pas de 15 minutes. Elle représente une journée de printemps proche de l’équinoxe, sans épisode de froid nécessitant un recours important au chauffage électrique et sans forte chaleur générant une utilisation massive de la climatisation. Une journée comporte donc 96 états successifs.

Contrairement au premier prototype, chaque calcul devra désormais dépendre du précédent. Une centrale produisant 2 000 MW à 10h00 et 2 300 MW à 10h15 commencera le calcul de 10h30 depuis son état de 10h15, et non depuis son état initial.

Cette évolution implique également une nouvelle contrainte métier : une centrale ne peut pas modifier instantanément sa puissance. Une vitesse maximale de montée et de descente en puissance devra être associée à chaque centrale et respectée lors de chaque transition de 15 minutes.

Le travail sera réalisé progressivement en trois phases.

#### Phase 1 : Une journée reposant sur la production nucléaire

Dans un premier temps, vous considérerez que l’ensemble de la consommation électrique doit être couvert par la production nucléaire.

Pour chaque quart d’heure, EnergIA devra :

- connaître la consommation de chaque région ;
- déterminer la production nucléaire nécessaire ;
- répartir cette production entre les centrales ;
- respecter leurs puissances minimales et maximales ;
- respecter leurs vitesses de montée et de descente en puissance ;
- prendre en compte les contraintes déjà développées lors du premier brief ;
- conserver l’état obtenu pour le quart d’heure suivant.

Le moteur devra être capable de simuler une journée complète et de produire l’état du parc pour chacun des 96 pas de temps.

#### Phase 2 : Prendre en compte les autres sources d’énergie

Le nucléaire ne constitue pas l’unique source de production électrique.

Vous intégrerez ensuite plusieurs productions considérées comme non pilotables par EnergIA, notamment le solaire et l’éolien. Des valeurs simulées vous seront fournies pour chaque quart d’heure.

Le moteur devra désormais raisonner sur la demande résiduelle :

consommation totale – production non pilotable = production restant à fournir

La production solaire pourra par exemple être nulle pendant la nuit, augmenter progressivement le matin, atteindre son maximum dans la journée puis diminuer jusqu’au coucher du soleil. L’éolien pourra évoluer de manière moins régulière.

EnergIA devra adapter la production nucléaire à cette nouvelle demande résiduelle.

À partir de cette phase, le moteur devra également chercher à conserver une réserve minimale de capacité disponible sur le parc nucléaire. Une situation dans laquelle la consommation est satisfaite mais où la totalité du parc fonctionne pratiquement à sa limite devra être identifiée comme une situation dégradée.

La valeur de cette réserve devra être configurable.

#### Phase 3 : Perturber la consommation

La journée de référence pourra ensuite être modifiée par des événements de consommation.

Un événement pourra représenter une hausse ou une baisse temporaire de consommation dans une région.

Exemples :

{

  "regionId": "occitanie",

  "start": "17:30",

  "end": "21:00",

  "deltaMw": 850

}

ou :

{

  "regionId": "grand-est",

  "start": "10:00",

  "end": "12:30",

  "deltaPercent": -12

}

Plusieurs événements pourront concerner différentes régions et se produire simultanément. Le moteur devra appliquer les perturbations aux pas de temps concernés, recalculer la répartition de la production et continuer à respecter l’ensemble des contraintes du parc.

Une difficulté importante devra être correctement gérée : la capacité totale du parc peut être théoriquement suffisante sans être mobilisable assez rapidement en raison des limites de montée en puissance. Lorsque la demande ne peut pas être satisfaite, EnergIA devra clairement identifier le quart d’heure concerné et la quantité de puissance manquante.

Le moteur temporel devra rester indépendant de la source des données. Les valeurs utilisées dans ce brief sont encore simulées, mais elles devront pouvoir être remplacées ultérieurement par des séries issues d’une base de données ou d’un autre service sans nécessiter une réécriture du moteur.

Quelques tests unitaires devront accompagner le développement. Il n’est toujours pas demandé de rechercher une couverture exhaustive du projet : les tests devront cibler quelques comportements métier importants.

#### Bonus

Après réalisation complète des trois phases, vous pourrez ajouter, de manière facultative :

- un format permettant d’exporter et de réimporter un scénario complet en JSON ;
- la génération de courbes représentant les indicateurs que vous jugez pertinents : consommation, production nucléaire, solaire, éolienne, puissance d’une centrale, réserve disponible, demande non satisfaite, etc. ;
- l’exécution d’une simulation sur une semaine, un mois ou une année ;
- une réflexion sur les performances du moteur lorsque le nombre de pas de temps devient important.

## Modalités pédagogiques

Durée : 3 jours

Travail en groupes de 4.

Vous poursuivrez le projet EnergIA réalisé lors du brief précédent. Il n’est pas demandé de recommencer l’application ni de modifier inutilement l’architecture déjà mise en place.

Le projet continuera à être développé et exécuté dans son environnement Docker.

Le travail devra être réalisé progressivement.

#### Première étape

Commencez par transformer le moteur existant afin qu’il puisse enchaîner plusieurs états successifs.

Travaillez d’abord avec quelques pas de temps seulement, puis avec une heure complète, avant de passer aux 96 quarts d’heure de la journée.

Vérifiez notamment que l’état produit à un instant donné devient bien l’état de départ du calcul suivant.

Ajoutez ensuite les contraintes de montée et de descente en puissance.

#### Deuxième étape

Lorsque la journée nucléaire fonctionne correctement, introduisez progressivement les autres productions.

Commencez par une seule source, par exemple le solaire, puis ajoutez l’éolien.

Vérifiez que le moteur adapte correctement la production nucléaire lorsque la production non pilotable augmente ou diminue.

Ajoutez ensuite la notion de réserve minimale du parc.

#### Troisième étape

Introduisez les événements de consommation.

Commencez par une seule région et une variation simple sur quelques heures.

Ajoutez ensuite :

- une baisse de consommation ;
- plusieurs régions ;
- des événements qui se chevauchent ;
- une variation suffisamment importante pour mettre le parc sous contrainte.

Chaque groupe reste libre d’organiser son travail et de développer un frontend pendant cette période s’il le souhaite. Aucun frontend particulier n’est cependant imposé par ce brief : l’ensemble des fonctionnalités doit rester accessible et vérifiable par les API.

Quelques tests unitaires devront être réalisés au fur et à mesure du développement. Vous pourrez notamment tester :

- le respect d’une limite de montée en puissance ;
- le respect d’une limite de descente ;
- le calcul de la demande résiduelle ;
- l’application correcte d’un événement ;
- une situation dans laquelle la demande ne peut pas être entièrement satisfaite.

Le dépôt Git partagé devra continuer à être utilisé avec des commits réguliers et compréhensibles.

Le formateur pourra proposer des démonstrations ou points techniques courts lorsque cela sera nécessaire.

## Modalités d'évaluation

L’évaluation portera notamment sur : la capacité du moteur à gérer une succession d’états dans le temps ; la conservation correcte de l’état entre deux pas de 15 minutes ; le respect des vitesses maximales de montée et de descente en puissance ; la simulation complète des 96 quarts d’heure d’une journée ; la prise en compte correcte des productions non pilotables ; le calcul de la demande résiduelle ; la prise en compte d’une réserve minimale de capacité ; la gestion des hausses et baisses temporaires de consommation ; la gestion de plusieurs événements simultanés ; la détection des situations où la demande ne peut pas être satisfaite ; la réutilisation pertinente du moteur développé lors du premier brief ; la séparation entre le moteur de simulation et la source des données ; la qualité et la lisibilité du code ; la présence et la pertinence des quelques tests unitaires; la qualité de la gestion des erreurs ; l’utilisation de Git ; la capacité du groupe à expliquer les choix réalisés. Les fonctionnalités bonus ne seront prises en compte qu’après validation des trois phases obligatoires.

## Livrables

À la fin du brief, chaque groupe devra fournir : le dépôt Git à jour du projet EnergIA ; le moteur de simulation temporelle ; les données utilisées pour la journée de référence ; les données simulées de production solaire et éolienne ; le mécanisme permettant de définir les perturbations de consommation ; les quelques tests unitaires réalisés ; les éventuelles modifications nécessaires aux services et à Docker Compose ; un README mis à jour. Le README devra notamment préciser : comment lancer une simulation ; le format des données temporelles attendues ; la manière dont les états successifs sont calculés ; les règles de montée et de descente en puissance ; le calcul de la demande résiduelle ; le fonctionnement de la réserve minimale ; le format utilisé pour définir une perturbation de consommation ; les principales limites connues du moteur. Les éventuels éléments bonus devront également être documentés.

## Critères de performance

Le projet continue à démarrer correctement dans son environnement Docker. Une journée complète de 96 pas de temps peut être simulée. Chaque état est calculé à partir de l’état précédent. Une centrale ne dépasse jamais sa puissance maximale. Une centrale ne modifie pas sa production plus rapidement que la limite autorisée. La production nucléaire s’adapte à l’évolution de la consommation. En phase 2, les productions non pilotables sont déduites de la demande avant le calcul nucléaire. Une hausse de production solaire ou éolienne entraîne, lorsque cela est possible, une diminution cohérente de la production nucléaire nécessaire. La réserve minimale du parc est calculée et surveillée. Une situation dans laquelle la réserve devient insuffisante est clairement identifiable. Une perturbation n’affecte que les régions et les périodes auxquelles elle s’applique. Une hausse comme une baisse de consommation peut être simulée. Plusieurs perturbations peuvent être appliquées au cours d’une même journée. Le moteur continue à respecter ses contraintes lors d’une perturbation. Une demande impossible à couvrir est explicitement signalée. Le quart d’heure concerné et la puissance manquante peuvent être identifiés. Les données temporelles peuvent être remplacées sans réécrire la logique du moteur. Quelques comportements essentiels sont couverts par des tests unitaires. Le code reste suffisamment modulaire pour permettre les évolutions prévues lors des prochains briefs. Le README permet à une autre équipe de comprendre et d’exécuter la simulation.