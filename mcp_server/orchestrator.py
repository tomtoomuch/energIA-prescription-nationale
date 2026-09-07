import asyncio
import json
import os
import traceback
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
    """
    Analyse une question au format

    consommation occitanie 18:00
    """
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
    """
    Récupère une consommation en passant par MCP
    """
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
    """
    Construit le prompt envoyé à gemma 4
    """
    data_json = json.dumps(
        data,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    )

    return f"""
Tu es l'assistant du projet EnergIA

Réponds en français clairement et sans emoji

La question de l'utilisateur est
{question}

Tu dois répondre uniquement à partir des données EnergIA
présentes dans le JSON ci-dessous

La consommation est une consommation de référence
elle ne représente pas une mesure en temps réel

N'invente aucune valeur
conserve exactement la valeur et l'unité MW
si les données sont insuffisantes dis le clairement

Données EnergIA
{data_json}

Rédige une seule phrase courte
""".strip()


async def ask_energia(question):
    """
    Exécute le parcours complet et retourne
    les données nécessaires à l'interface web
    """
    region_id, timestamp = parse_question(
        question
    )

    steps = [
        "question reçue",
    ]

    data = await read_consumption(
        region_id=region_id,
        timestamp=timestamp,
    )

    steps.append(
        "connexion MCP réussie"
    )

    steps.append(
        "données FastAPI récupérées"
    )

    prompt = build_prompt(
        question=question,
        data=data,
    )

    steps.append(
        "prompt construit avec les données EnergIA"
    )

    # ollama est synchrone
    # to_thread évite de bloquer le serveur MCP
    answer = await asyncio.to_thread(
        ask_ollama,
        prompt,
    )

    steps.append(
        "réponse générée par gemma 4"
    )

    return {
        "question": question,
        "steps": steps,
        "data": data,
        "answer": answer,
    }


async def main():
    question = input(
        "Question EnergIA "
        "(exemple : consommation occitanie 18:00) : "
    )

    try:
        result = await ask_energia(
            question
        )

        print()
        print("Processus")

        for step in result["steps"]:
            print(f"  {step}")

        print()
        print("Données EnergIA")
        print(
            json.dumps(
                result["data"],
                ensure_ascii=False,
                indent=2,
            )
        )

        print()
        print("Réponse gemma 4")
        print(result["answer"])

    except Exception as error:
        print()
        print(
            f"Assistant indisponible : {error}"
        )
        traceback.print_exception(error)


if __name__ == "__main__":
    asyncio.run(main())