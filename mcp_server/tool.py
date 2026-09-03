import json
import math
import os
import sys

import httpx


def _get_api_data(path, params=None, timeout=30.0):

    base_url = os.getenv(
        "PYTHON_SERVICE_URL_2",
        "http://ms-python-2:8002",
    ).rstrip("/")

    security_token = os.getenv("SECURITY_TOKEN")

    if not security_token:
        raise RuntimeError(
            "SECURITY_TOKEN n'est pas configuré."
        )

    try:
        response = httpx.get(
            f"{base_url}{path}",
            headers={
                "x-api-key": security_token,
            },
            params=params,
            timeout=timeout,
        )

        response.raise_for_status()

    except httpx.TimeoutException as error:
        raise RuntimeError(
            "L'API EnergIA n'a pas répondu "
            "dans le délai autorisé."
        ) from error

    except httpx.HTTPStatusError as error:
        status = error.response.status_code

        if status in (401, 403):
            message = (
                "Accès refusé : vérifiez SECURITY_TOKEN."
            )
        else:
            message = (
                f"L'API EnergIA a retourné "
                f"une erreur HTTP {status}."
            )

        raise RuntimeError(message) from error

    except httpx.RequestError as error:
        raise RuntimeError(
            "Impossible de joindre l'API EnergIA."
        ) from error

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "L'API EnergIA n'a pas retourné "
            "un JSON valide."
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            "Réponse EnergIA invalide : "
            "un objet JSON est attendu."
        )

    return data


def get_plants():
    """Retourne les centrales reçues depuis FastAPI."""
    data = _get_api_data("/phase1/plants")

    if (
        not isinstance(data.get("plants"), list)
        or type(data.get("plants_count")) is not int
    ):
        raise RuntimeError(
            "Réponse EnergIA invalide : "
            "'plants' ou 'plants_count' est incorrect."
        )

    if data["plants_count"] != len(data["plants"]):
        raise RuntimeError(
            "Le nombre de centrales ne correspond "
            "pas à la liste."
        )

    return data


def get_region_consumption(region_id, timestamp):
    """
    Sélectionne la consommation d'une région et
    d'un horaire dans la réponse FastAPI.

    Aucun calcul de consommation n'est effectué.
    """
    if not isinstance(region_id, str):
        raise ValueError(
            "L'identifiant de région doit être une chaîne."
        )

    region_id = region_id.strip().casefold()

    if not region_id:
        raise ValueError(
            "L'identifiant de région est obligatoire."
        )

    if not isinstance(timestamp, str):
        raise ValueError(
            "L'horaire doit être une chaîne."
        )

    timestamp = timestamp.strip()

    if not timestamp:
        raise ValueError(
            "L'horaire est obligatoire."
        )

    data = _get_api_data("/phase1/consumption")
    steps = data.get("steps")

    if not isinstance(steps, list) or not steps:
        raise RuntimeError(
            "Réponse EnergIA invalide : "
            "la liste des horaires est absente ou vide."
        )

    for step in steps:
        if not isinstance(step, dict):
            raise RuntimeError(
                "Réponse EnergIA invalide : "
                "un pas de temps est incorrect."
            )

        if step.get("timestamp") != timestamp:
            continue

        consumptions = step.get(
            "regional_consumption_mw"
        )

        if not isinstance(consumptions, dict):
            raise RuntimeError(
                "Les consommations régionales "
                "sont absentes de la réponse."
            )

        if region_id not in consumptions:
            raise ValueError(
                f"Région inconnue : {region_id}"
            )

        consumption = consumptions[region_id]

        if (
            type(consumption) not in (int, float)
            or not math.isfinite(consumption)
            or consumption < 0
        ):
            raise RuntimeError(
                "Consommation absente ou invalide pour "
                f"{region_id} à {timestamp}."
            )

        return {
            "region_id": region_id,
            "timestamp": timestamp,
            "consumption_mw": consumption,
        }

    raise ValueError(
        f"Horaire inconnu : {timestamp}"
    )

def get_phase3_simulation(
    scenario_id="evening_peak_occitanie",
    number_of_steps=96,
    minimum_reserve_mw=5000.0,
):

    # simulation de phase 3 à FastAPI.

    if not isinstance(scenario_id, str):
        raise ValueError(
            "L'identifiant du scénario doit être une chaîne."
        )

    scenario_id = scenario_id.strip()

    if not scenario_id:
        raise ValueError(
            "L'identifiant du scénario est obligatoire."
        )

    if (
        type(number_of_steps) is not int
        or not 1 <= number_of_steps <= 96
    ):
        raise ValueError(
            "Le nombre de pas doit être un entier "
            "compris entre 1 et 96."
        )

    if (
        type(minimum_reserve_mw) not in (int, float)
        or not math.isfinite(minimum_reserve_mw)
        or minimum_reserve_mw < 0
    ):
        raise ValueError(
            "La réserve minimale doit être "
            "un nombre fini positif ou nul."
        )

    data = _get_api_data(
        "/phase3/simulate-day",
        params={
            "scenario_id": scenario_id,
            "number_of_steps": number_of_steps,
            "minimum_reserve_mw": minimum_reserve_mw,
        },
        timeout=120.0,
    )

    if data.get("phase") != 3:
        raise RuntimeError(
            "L'API n'a pas retourné une simulation "
            "de phase 3."
        )

    steps = data.get("steps")

    if not isinstance(steps, list):
        raise RuntimeError(
            "La simulation ne contient pas "
            "de liste de résultats."
        )

    if (
        len(steps) != number_of_steps
        or data.get("steps_count") != number_of_steps
    ):
        raise RuntimeError(
            "Le nombre de pas retourné "
            "ne correspond pas à la demande."
        )

    scenario = data.get("scenario")

    if (
        not isinstance(scenario, dict)
        or scenario.get("scenario_id") != scenario_id
    ):
        raise RuntimeError(
            "Le scénario retourné ne correspond "
            "pas au scénario demandé."
        )

    return data

# /simulate-day?scenario_id=evening_peak_occitanie&number_of_steps=96&minimum_reserve_mw=5000



if __name__ == "__main__":
    try:
        result = get_plants()

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
        )

    except (RuntimeError, ValueError) as error:
        print(
            f"Erreur : {error}",
            file=sys.stderr,
        )
        sys.exit(1)
