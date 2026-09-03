# pour relier les composants, sans refaire les calculs

import asyncio
import json
import os
from datetime import timedelta
from urllib.parse import quote

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import AnyUrl

from ollama_client import ask_ollama


MCP_URL = os.getenv(
    "MCP_URL",
    "http://127.0.0.1:8003/mcp",
)


def parse_question(question):
    parts = question.strip().split()

    if len(parts) != 3 or parts[0].casefold() != "consommation":
        raise ValueError(
            "format attendu : consommation occitanie 18:00"
        )

    region_id = parts[1].casefold()
    timestamp = parts[2]

    return region_id, timestamp


async def read_consumption(region_id, timestamp):
    # encode les paramètres pour construire une uri valide
    uri = (
        "energia://consumption/"
        f"{quote(region_id, safe='')}/"
        f"{quote(timestamp, safe='')}"
    )

    async with streamablehttp_client(MCP_URL) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
            read_timeout_seconds=timedelta(seconds=60),
        ) as session:
            await session.initialize()

            print("connexion mcp : ok", flush=True)
            result = await session.read_resource(AnyUrl(uri))

    if len(result.contents) != 1:
        raise RuntimeError("contenu de ressource inattendu")

    content = result.contents[0]

    if not hasattr(content, "text"):
        raise RuntimeError("la ressource doit contenir du texte json")

    data = json.loads(content.text)

    if not isinstance(data, dict):
        raise RuntimeError("la ressource doit retourner un objet json")

    if (
        data.get("region_id") != region_id
        or data.get("timestamp") != timestamp
        or data.get("consumption_mw") is None
    ):
        raise RuntimeError("donnees absentes ou incoherentes")

    return data


def build_prompt(data):
    return (
        "redige une phrase courte en francais\n"
        "indique la consommation de reference pour la region "
        "et l'horaire presents dans le json\n"
        "utilise uniquement les donnees fournies\n"
        "conserve exactement la consommation et son unite MW\n"
        "ne presente pas cette valeur comme une mesure en direct "
        "ou comme une simulation de phase 3\n"
        "n'ajoute aucune estimation ni explication non fournie\n"
        "donnees :\n"
        + json.dumps(data, ensure_ascii=False, allow_nan=False)
    )


def main():
    question = input(
        "demande, exemple consommation occitanie 18:00 : "
    )

    try:
        region_id, timestamp = parse_question(question)

        print("lecture de la consommation par mcp", flush=True)
        data = asyncio.run(
            read_consumption(region_id, timestamp)
        )

    except Exception as error:
        print(f"lecture impossible : {error}", flush=True)
        print("aucune demande envoyee a ollama", flush=True)
        return

    # affiche les données avant de solliciter le modèle
    print("donnees EnergIA :", flush=True)
    print(
        json.dumps(data, ensure_ascii=False, indent=2),
        flush=True,
    )

    try:
        prompt = build_prompt(data)

        print("envoi a ollama, veuillez patienter", flush=True)
        answer = ask_ollama(prompt)

        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("ollama a retourne une reponse vide")

        print("reponse redigee par ollama :", flush=True)
        print(answer, flush=True)

    except Exception as error:
        print(f"reponse ollama indisponible : {error}", flush=True)
        print(
            "les donnees EnergIA restent disponibles ci-dessus",
            flush=True,
        )


if __name__ == "__main__":
    main()