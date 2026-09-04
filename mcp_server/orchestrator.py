# pour relier les composants, sans refaire les calculs

import asyncio
import json
import os
from datetime import timedelta
from urllib.parse import quote

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import AnyUrl

from ollama_client import ask_ollama


MCP_URL = os.getenv(
    "MCP_URL",
    "http://mcp-server:8003/mcp",
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

    async with streamable_http_client(MCP_URL) as (
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
        raise RuntimeError("Contenu de ressource inattendu")

    content = result.contents[0]

    if not hasattr(content, "text"):
        raise RuntimeError("La ressource doit contenir du texte json")

    data = json.loads(content.text)

    if not isinstance(data, dict):
        raise RuntimeError("La ressource doit retourner un objet json")

    if (
        data.get("region_id") != region_id
        or data.get("timestamp") != timestamp
        or data.get("consumption_mw") is None
    ):
        raise RuntimeError("Données absentes ou incohérentes")

    return data


def build_prompt(data):
    return (
        "Tu es l'assistant EnergIA.\n"
        "Tu n'utilises pas d'emojis.\n"
        "Tu réponds en français à la question posée.\n"
        "Tu ne réponds qu'en utilisant les données fournies par l'API.\n"
        "Tu ne réponds pas à la question si les données ne sont pas suffisantes.`\n"
        "Rédige une phrase courte.\n"
        "indique la consommation de référence pour la region"
        "et l'horaire présents dans le JSON.\n"
        "Conserve exactement la consommation et son unite MW\n"
        "Ne présente pas cette valeur comme une mesure en temps réel\n"
        "ou comme une simulation de phase 3.\n"
        "N'ajoute aucune estimation ni explication non fournie\n"
        "Données :\n"
        + json.dumps(data, ensure_ascii=False, allow_nan=False)
    )


def main():
    question = input(
        "Format attendu pour la saisie : consommation occitanie 18:00 -> "
    )

    try:
        region_id, timestamp = parse_question(question)

        print("Lecture de la consommation par mcp...", flush=True)
        data = asyncio.run(
            read_consumption(region_id, timestamp)
        )

    except Exception as error:
        print(f"Lecture impossible : {error}", flush=True)
        print("Aucune demande envoyée à Ollama.", flush=True)
        return

    # affiche les données avant de solliciter le modèle
    print("Données EnergIA : ", flush=True)
    print(
        json.dumps(data, ensure_ascii=False, indent=2),
        flush=True,
    )

    try:
        prompt = build_prompt(data)

        print("Envoi à Ollama, veuillez patienter...", flush=True)
        answer = ask_ollama(prompt)

        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Ollama a retourné une réponse vide")

        print("Réponse rédigée par Ollama :", flush=True)
        print(answer, flush=True)

    except Exception as error:
        print(f"Réponse Ollama indisponible : {error}", flush=True)
        print("Les données EnergIA restent disponibles ci-dessus", flush=True)



if __name__ == "__main__":
    main()