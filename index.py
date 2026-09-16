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
DATASET = PREDICTION / "data" / "dataset_final.csv"
DATA = PREDICTION / "data"
MODELES = PREDICTION / "modeles"
GRAPHIQUES = PREDICTION / "graphiques"

SERVICES = {
    "gateway",
    "ms-python",
    "ms-python-2",
    "prediction-api",
    "llm",
    "mcp-server",
}


def fichier_present(chemin):
    return chemin.is_file() and chemin.stat().st_size > 0


def preparer_donnees():
    """Crée seulement les JSON absents, puis le CSV si nécessaire."""
    from prediction.etl import extraction

    DATA.mkdir(parents=True, exist_ok=True)
    sources = [
        (
            extraction.FICHIER_ELECTRICITE,
            lambda: extraction.telecharger_electricite(
                extraction.URL_API_ELECTRICITE,
                extraction.FICHIER_ELECTRICITE,
            ),
        ),
        (
            extraction.FICHIER_METEO,
            lambda: extraction.telecharger_meteo(
                extraction.URL_API_METEO,
                extraction.FICHIER_METEO,
            ),
        ),
        (
            extraction.FICHIER_CALENDRIER,
            lambda: extraction.telecharger_calendrier(
                extraction.ANNEE,
                extraction.FICHIER_CALENDRIER,
            ),
        ),
        (
            extraction.FICHIER_VACANCES,
            lambda: extraction.telecharger_vacances(
                extraction.URL_API_VACANCES,
                extraction.FICHIER_VACANCES,
            ),
        ),
    ]

    source_creee = False
    for chemin, creer in sources:
        if fichier_present(chemin):
            print(f"Source déjà présente : {chemin.name}", flush=True)
            continue
        print(f"Création de la source : {chemin.name}", flush=True)
        creer()
        if not fichier_present(chemin):
            raise RuntimeError(f"Source non créée : {chemin}")
        source_creee = True

    if source_creee or not fichier_present(DATASET):
        print("\nCréation de dataset_final.csv", flush=True)
        executer([
            sys.executable,
            str(PREDICTION / "etl" / "dataframe.py"),
        ])
        if not fichier_present(DATASET):
            raise RuntimeError(f"Dataset non créé : {DATASET}")
        return True

    print("\nDataset déjà présent : reconstruction ignorée", flush=True)
    return False


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

    texte = resultat.stdout.strip()

    if texte.startswith("["):
        conteneurs = json.loads(texte)
    else:
        conteneurs = [
            json.loads(ligne)
            for ligne in texte.splitlines()
            if ligne.strip()
        ]

    actifs = {
        conteneur.get("Service")
        for conteneur in conteneurs
        if conteneur.get("State", "").lower() == "running"
    }

    manquants = SERVICES - actifs
    if manquants:
        raise RuntimeError(
            "Services non démarrés : "
            + ", ".join(sorted(manquants))
            + "\nConsultez : docker compose logs --tail=50 "
            + " ".join(sorted(manquants))
        )

    print("Les six services Docker sont démarrés.")


def entrainer_si_necessaire(force):
    if not DATASET.is_file():
        raise FileNotFoundError(
            f"Dataset absent : {DATASET}\n"
            "Exécutez d'abord extraction.py, puis dataframe.py."
        )

    modele = MODELES / "modele_consommation.joblib"
    informations = MODELES / "modele_consommation.json"
    graphique = (
        GRAPHIQUES
        / "reel_predit"
        / "bretagne"
        / "reel_predit_2025-09.png"
    )

    if force or not all(
        chemin.is_file()
        for chemin in (modele, informations, graphique)
    ):
        print("\n[1/2] Entraînement et création des graphiques")
        executer([
            sys.executable,
            str(PREDICTION / "ConsomationML.py"),
        ])
    else:
        print("\n[1/2] Modèle et graphiques présents : entraînement ignoré")


def demarrer_docker():
    print("\n[2/2] Démarrage des services Docker")
    executer(["docker", "compose", "config", "--quiet"])
    executer(["docker", "compose", "up", "-d", "--build"])

    for tentative in range(10):
        try:
            verifier_conteneurs()
            return
        except RuntimeError:
            if tentative == 9:
                raise
            time.sleep(3)


def verifier_site(port):
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
        description="Entraîner si nécessaire et démarrer EnergIA"
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Forcer un nouvel entraînement sklearn",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Ne pas ouvrir le navigateur",
    )
    options = parser.parse_args()

    try:
        dataset_reconstruit = preparer_donnees()
        entrainer_si_necessaire(options.retrain or dataset_reconstruit)
        demarrer_docker()

        base = verifier_site(port_gateway())
        print(f"\nProjet prêt : {base}")
        print(f"Graphiques : {base}/graphiques.html")

        if not options.no_browser:
            webbrowser.open(base)

    except (OSError, subprocess.CalledProcessError, RuntimeError) as erreur:
        print(f"\nÉchec du démarrage : {erreur}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
