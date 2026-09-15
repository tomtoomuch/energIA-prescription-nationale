
import argparse
import json
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

RACINE = Path(__file__).resolve().parent
PREDICTION = RACINE / "prediction"
DATA = PREDICTION / "data"
MODELES = PREDICTION / "modeles"
GRAPHIQUES = PREDICTION / "graphiques"

JSON_NECESSAIRES = [
    DATA / "eco2mix-regional.json",
    DATA / "meteo-regions.json",
    DATA / "calendrier-2025.json",
    DATA / "vacances-scolaires-regions.json",
]

SERVICES = {
    "gateway",
    "ms-python",
    "ms-python-2",
    "prediction-api",
    "llm",
    "mcp-server",
}


def executer(commande):
    print("\n>", " ".join(commande), flush=True)
    subprocess.run(commande, cwd=RACINE, check=True)


def port_gateway():

    fichier_env = RACINE / ".env"

    if fichier_env.exists():
        for ligne in fichier_env.read_text(encoding="utf-8").splitlines():
            ligne = ligne.strip()
            if ligne.startswith("GATEWAY_PORT="):
                return ligne.split("=", 1)[1].strip().strip("\"'")

    return "3000"


def lire_json_http(url):
    with urllib.request.urlopen(url, timeout=5) as reponse:
        return json.load(reponse)


def attendre_gateway(url):
    for _ in range(20):
        try:
            return lire_json_http(url)
        except Exception:
            time.sleep(2)

    raise RuntimeError(f"Le gateway ne répond pas : {url}")


def verifier_conteneurs():
    resultat = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        cwd=RACINE,
        check=True,
        capture_output=True,
        text=True,
    )

    actifs = set()


    texte = resultat.stdout.strip()
    if texte.startswith("["):
        lignes = json.loads(texte)
    else:
        lignes = [
            json.loads(ligne)
            for ligne in texte.splitlines()
            if ligne.strip()
        ]

    for conteneur in lignes:
        if conteneur.get("State", "").lower() == "running":
            actifs.add(conteneur.get("Service"))

    manquants = SERVICES - actifs
    if manquants:
        raise RuntimeError(
            "Services non démarrés : "
            + ", ".join(sorted(manquants))
            + "\nConsultez : docker compose logs --tail=50 "
            + " ".join(sorted(manquants))
        )

    print("Les six services Docker sont démarrés.")


def preparer_donnees(force):
    # construit les JSON et le CSV seulement si nécessaire
    json_absents = any(not fichier.exists() for fichier in JSON_NECESSAIRES)

    if force or json_absents:
        print("\n[1/4] Téléchargement des sources 2025")
        executer([
            sys.executable,
            str(PREDICTION / "etl" / "extraction.py"),
        ])
    else:
        print("\n[1/4] JSON déjà présents : téléchargement ignoré")

    dataset = DATA / "dataset_final.csv"
    if force or json_absents or not dataset.exists():
        print("\n[2/4] Construction du dataset")
        executer([
            sys.executable,
            str(PREDICTION / "etl" / "dataframe.py"),
        ])
    else:
        print("\n[2/4] Dataset déjà présent : construction ignorée")


def entrainer_si_necessaire(force):
    # entraîne sklearn si les résultats nécessaires sont absents
    modele = MODELES / "modele_consommation.joblib"
    informations = MODELES / "modele_consommation.json"
    graphique = (
        GRAPHIQUES
        / "reel_predit"
        / "bretagne"
        / "reel_predit_2025-09.png"
    )

    if force or not all(
        chemin.exists()
        for chemin in [modele, informations, graphique]
    ):
        print("\n[3/4] Entraînement et création des graphiques")
        executer([
            sys.executable,
            str(PREDICTION / "ConsomationML.py"),
        ])
    else:
        print("\n[3/4] Modèle et graphiques déjà présents : entraînement ignoré")


def demarrer_docker():
   # vérifie Compose puis construit et lance tous les services
    print("\n[4/4] Démarrage de tous les services")
    executer(["docker", "compose", "config", "--quiet"])
    executer(["docker", "compose", "up", "-d", "--build"])

    # conteneur peut s'arrêter juste après  up
    # on attend, puis on vérifie son état réel
    for tentative in range(10):
        try:
            verifier_conteneurs()
            return
        except RuntimeError:
            if tentative == 9:
                raise
            time.sleep(3)


def verifier_site(port):
    # connexions du gateway
    base = f"http://localhost:{port}"

    attendre_gateway(f"{base}/health")
    print("Gateway : OK")

    lire_json_http(f"{base}/health-ms")
    print("Gateway → ms-python : OK")

    lire_json_http(f"{base}/health-ms-2")
    print("Gateway → ms-python-2 : OK")

    graphiques = lire_json_http(f"{base}/api/graphiques")
    nombre_regions = len(graphiques.get("regions", []))
    if nombre_regions == 0:
        raise RuntimeError(
            "Le gateway fonctionne, mais /api/graphiques "
            "ne trouve aucune région."
        )

    print(f"Gateway → graphiques : {nombre_regions} régions")
    return base


def main():
    parser = argparse.ArgumentParser(
        description="Préparer et démarrer tout le projet EnergIA"
    )
    parser.add_argument(
        "--rebuild-data",
        action="store_true",
        help="Retélécharger les données, reconstruire le CSV et réentraîner",
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Réentraîner sklearn avec le dataset déjà présent",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Ne pas ouvrir le navigateur",
    )
    options = parser.parse_args()

    try:
        preparer_donnees(options.rebuild_data)
        entrainer_si_necessaire(
            options.retrain or options.rebuild_data
        )
        demarrer_docker()

        base = verifier_site(port_gateway())
        print(f"\nProjet prêt : {base}")
        print(f"Graphiques : {base}/graphiques.html")

        if not options.no_browser:
            webbrowser.open(base)

    except (OSError, subprocess.CalledProcessError, RuntimeError) as erreur:
        print(f"\nÉchec de la pipeline : {erreur}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()