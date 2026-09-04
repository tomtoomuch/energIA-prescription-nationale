import asyncio
import json
import os
from datetime import timedelta
from urllib.parse import quote

from mcp import ClientSession
from mcp.client.streamable_http import (
    streamable_http_client,
)
from pydantic import AnyUrl

from ollama_client import ask_ollama


MCP_URL = os.getenv(
    "MCP_URL",
    "http://mcp-server:8003/mcp",
)


def parse_question(question):
    #format   consommation occitanie 18:00

    if not isinstance(question, str):
        raise ValueError(
            "La question doit être une chaîne"
        )

    parts = question.strip().split()

    if (
        len(parts) != 3
        or parts[0].casefold() != "consommation"
    ):
        raise ValueError(
            "Format attendu : "
            "consommation occitanie 18:00"
        )

    region_id = parts[1].casefold()
    timestamp = parts[2]

    return region_id, timestamp


async def read_consumption(
    region_id,
    timestamp,
):

    uri = (
        "energia://consumption/"
        f"{quote(region_id, safe='')}/"
        f"{quote(timestamp, safe='')}"
    )

    async with streamable_http_client(
        MCP_URL
    ) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
            read_timeout_seconds=timedelta(
                seconds=60
            ),
        ) as session:
            await session.initialize()

            print(
                "Connexion MCP : OK",
                flush=True,
            )

            result = await session.read_resource(
                AnyUrl(uri)
            )

    if len(result.contents) != 1:
        raise RuntimeError(
            "Contenu MCP inattendu"
        )

    content = result.contents[0]

    if not hasattr(content, "text"):
        raise RuntimeError(
            "La ressource MCP doit contenir "
            "du texte JSON"
        )

    try:
        data = json.loads(content.text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "La ressource MCP n'a pas retourné "
            "un JSON valide"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            "La ressource MCP doit retourner "
            "un objet JSON"
        )

    if data.get("consumption_mw") is None:
        raise RuntimeError(
            "La consommation est absente"
        )

    return data


def build_prompt(
    question,
    data,
):

    data_json = json.dumps(
        data,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    )

    return f"""
Tu es l'assistant du projet EnergIA.

Réponds en français, clairement et sans emoji.

La question de l'utilisateur est :
{question}

Tu dois répondre uniquement à partir des données EnergIA
présentes dans le JSON ci-dessous.

La valeur de consommation est une consommation de référence.
Elle ne représente pas une mesure en temps réel.

N'invente aucune valeur.
Conserve exactement la valeur et l'unité MW.
Si les données sont insuffisantes, dis-le clairement.

Données EnergIA :
{data_json}

Rédige une seule phrase courte.
""".strip()


async def main():
    question = input(
        "Question EnergIA "
        "(exemple : consommation occitanie 18:00) : "
    )

    try:
        region_id, timestamp = (
            parse_question(question)
        )

        print(
            "Récupération des données par MCP...",
            flush=True,
        )

        data = await read_consumption(
            region_id=region_id,
            timestamp=timestamp,
        )

        print()
        print("Données reçues de FastAPI via MCP :")
        print(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
        )

        prompt = build_prompt(
            question=question,
            data=data,
        )

        print()
        print(
            "Envoi du prompt à Gemma 4...",
            flush=True,
        )

        answer = ask_ollama(prompt)

        print()
        print("Réponse Gemma 4 :")
        print(answer)

    except Exception as error:
        print()
        print(
            f"Assistant indisponible : {error}"
        )


if __name__ == "__main__":
    asyncio.run(main())