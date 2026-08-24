<!-- CONTRIBUTING.md -->
# Guide de contribution au projet EnergIA

Nous encourageons toute contribution en suivant les directives suivantes :

## Branches de Travail

Toutes les nouvelles fonctionnalités doivent être développées sur des branches spécifiques aux micro-services (```nodeAPI``` ou ```pythonAPI```) puis fusionnées dans la branche principale ```dev```. Les tests sont effectués sur ```dev``` avant mise en production sur ```main```.

## Conventions de Commit

L'usage d'étiquettes est obligatoire pour classer le type de modification :

```<feat>```: Nouvelle fonctionnalité.

```<fix>```: Correction de bug.

```<doc>```: Mise à jour documentaire (dans un fichier .md).

```<devops>```: Changement lié au déploiement, infrastructure ou CI/CD.
