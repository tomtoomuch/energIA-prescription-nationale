import json
import os
import sys

import httpx


def get_plants():
    """
    Récupère les centrales depuis l'API FastAPI EnergIA.

    Aucun calcul métier et aucune lecture de fichier
    de données ne sont effectués ici.
    """
    base_url = os.getenv(
        "PYTHON_SERVICE_URL_2",
        "http://ms-python-2:8002",
    ).rstrip("/")

    security_token = os.getenv("SECURITY_TOKEN")

    if not security_token:
        raise RuntimeError(
            "SECURITY_TOKEN n'est pas configuré "
            "dans l'environnement MCP."
        )

    url = f"{base_url}/phase1/plants"

    try:
        response = httpx.get(
            url,
            headers={
                "x-api-key": security_token,
            },
            timeout=30.0,
        )

        # Refuse les réponses HTTP en erreur.
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
                "Accès à EnergIA refusé : "
                "vérifiez SECURITY_TOKEN."
            )
        else:
            message = (
                "L'API EnergIA a retourné "
                f"une erreur HTTP {status}."
            )

        raise RuntimeError(message) from error

    except httpx.RequestError as error:
        raise RuntimeError(
            "Impossible de joindre l'API EnergIA. "
            "Vérifiez son adresse et le conteneur "
            "ms-python-2."
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

    if (
        not isinstance(data.get("plants"), list)
        or type(data.get("plants_count")) is not int
    ):
        raise RuntimeError(
            "Réponse EnergIA invalide : "
            "'plants' ou 'plants_count' est absent "
            "ou incorrect."
        )

    if data["plants_count"] != len(data["plants"]):
        raise RuntimeError(
            "Réponse EnergIA incohérente : "
            "le nombre de centrales ne correspond "
            "pas à la liste."
        )

    return data


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