import json
import sys
from pathlib import Path


# racine du projet
PROJECT_DIRECTORY = (
    Path(__file__).resolve().parent.parent
)

# dossier contenant services/energia_service.py
MS_PYTHON_2_DIRECTORY = (
    PROJECT_DIRECTORY / "ms-python-2"
)

# permet à Python d'importer le dossier services
sys.path.insert(
    0,
    str(MS_PYTHON_2_DIRECTORY),
)


from services.energia_service import (
    get_simulation_results,
    list_plants,
    list_regions,
)


def get_all_energia_data():

    # regroupe toutes les données utiles dans un seul dictionnaire.

    regions = list_regions()
    plants = list_plants()

    simulation = get_simulation_results(
        number_of_steps=96,
        minimum_reserve_mw=5000,
    )

    return {
        "regions": regions,
        "plants": plants,
        "simulation": simulation,
    }


def main():
    try:
        all_data = get_all_energia_data()

        # conversion en texte JSON lisible
        json_data = json.dumps(
            all_data,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

        print(json_data)

    except (
        ValueError,
        FileNotFoundError,
        KeyError,
        TypeError,
    ) as error:
        print(
            f"Erreur EnergIA : {error}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
