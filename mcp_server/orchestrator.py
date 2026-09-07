import asyncio
import json
import os
import traceback
from datetime import timedelta

from mcp import ClientSession
from mcp.client.streamable_http import (
    streamable_http_client,
)
from ollama import Client


MCP_URL = os.getenv(
    "MCP_URL",
    "http://mcp-server:8003/mcp",
)

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://llm:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "gemma4:e4b",
)


ollama_client = Client(
    host=OLLAMA_HOST,
)


SYSTEM_PROMPT = """
Tu es l'assistant du projet EnergIA

Tu réponds en français clairement et sans emoji

Tu disposes d'outils qui donnent accès aux données réelles
de l'application EnergIA

Pour toute question sur les centrales la consommation
ou les simulations tu dois utiliser un outil

Tu ne dois jamais inventer une valeur EnergIA

Après un appel d'outil tu dois répondre uniquement
à partir du résultat retourné

La consommation retournée par get_consumption est
une consommation de référence et non une mesure en temps réel

Les résultats de simulate_phase3 sont des résultats simulés
""".strip()


OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_plants",
            "description": (
                "Retourne la liste des centrales EnergIA "
                "avec leur disponibilité leur région "
                "leur puissance et leurs contraintes"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_consumption",
            "description": (
                "Retourne la consommation de référence "
                "d'une région à une heure donnée"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "region_id": {
                        "type": "string",
                        "description": (
                            "identifiant de région en minuscules "
                            "par exemple occitanie"
                        ),
                    },
                    "timestamp": {
                        "type": "string",
                        "description": (
                            "heure au format HH:MM "
                            "par exemple 18:00"
                        ),
                    },
                },
                "required": [
                    "region_id",
                    "timestamp",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_phase3",
            "description": (
                "Lance une simulation EnergIA de phase 3 "
                "avec un scénario une durée et une réserve"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario_id": {
                        "type": "string",
                        "description": (
                            "identifiant du scénario "
                            "par exemple evening_peak_occitanie"
                        ),
                    },
                    "number_of_steps": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 96,
                        "description": (
                            "nombre de quarts d'heure à simuler"
                        ),
                    },
                    "minimum_reserve_mw": {
                        "type": "number",
                        "minimum": 0,
                        "description": (
                            "réserve nucléaire minimale en MW"
                        ),
                    },
                },
                "required": [
                    "scenario_id",
                    "number_of_steps",
                    "minimum_reserve_mw",
                ],
            },
        },
    },
]


def validate_question(question):
    """
    Vérifie la question sans imposer un format précis
    """
    if not isinstance(question, str):
        raise ValueError(
            "La question doit être une chaîne"
        )

    question = question.strip()

    if not question:
        raise ValueError(
            "La question est obligatoire"
        )

    return question


def normalize_tool_arguments(
    tool_name,
    arguments,
):
    """
    Nettoie les paramètres produits par gemma 4
    """
    if not isinstance(arguments, dict):
        raise ValueError(
            "Les paramètres de l'outil sont invalides"
        )

    arguments = dict(arguments)

    if tool_name == "get_consumption":
        region_id = arguments.get(
            "region_id"
        )

        timestamp = arguments.get(
            "timestamp"
        )

        if isinstance(region_id, str):
            arguments["region_id"] = (
                region_id
                .strip()
                .casefold()
            )

        if isinstance(timestamp, str):
            timestamp = timestamp.strip()

            # transforme 18h en 18:00
            if (
                timestamp.endswith("h")
                and timestamp[:-1].isdigit()
            ):
                timestamp = (
                    timestamp[:-1].zfill(2)
                    + ":00"
                )

            # transforme 18 en 18:00
            elif timestamp.isdigit():
                timestamp = (
                    timestamp.zfill(2)
                    + ":00"
                )

            arguments["timestamp"] = timestamp

    if tool_name == "simulate_phase3":
        arguments.setdefault(
            "scenario_id",
            "evening_peak_occitanie",
        )

        arguments.setdefault(
            "number_of_steps",
            4,
        )

        arguments.setdefault(
            "minimum_reserve_mw",
            5000.0,
        )

        arguments["number_of_steps"] = int(
            arguments["number_of_steps"]
        )

        arguments["minimum_reserve_mw"] = float(
            arguments["minimum_reserve_mw"]
        )

    return arguments


def mcp_result_to_text(result):
    """
    Transforme le résultat MCP en texte JSON
    utilisable par gemma 4
    """
    if result.isError:
        error_messages = []

        for content in result.content:
            if hasattr(content, "text"):
                error_messages.append(
                    content.text
                )

        message = "\n".join(
            error_messages
        )

        raise RuntimeError(
            message
            or "L'outil MCP a retourné une erreur"
        )

    if result.structuredContent is not None:
        return json.dumps(
            result.structuredContent,
            ensure_ascii=False,
            allow_nan=False,
        )

    text_parts = []

    for content in result.content:
        if hasattr(content, "text"):
            text_parts.append(
                content.text
            )

    if not text_parts:
        raise RuntimeError(
            "L'outil MCP n'a retourné aucune donnée"
        )

    return "\n".join(
        text_parts
    )


def parse_result_for_interface(
    result_text,
):
    """
    Transforme le résultat en objet pour l'interface
    lorsque le résultat contient du JSON
    """
    try:
        return json.loads(
            result_text
        )
    except json.JSONDecodeError:
        return {
            "raw_result": result_text,
        }


async def ask_model(
    messages,
    with_tools=True,
):
    """
    Appelle ollama sans bloquer le serveur HTTP
    """
    parameters = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    if with_tools:
        parameters["tools"] = (
            OLLAMA_TOOLS
        )

    return await asyncio.to_thread(
        ollama_client.chat,
        **parameters,
    )


async def ask_energia(question):
    """
    Laisse gemma 4 choisir un ou plusieurs outils MCP
    puis lui demande de produire la réponse finale
    """
    question = validate_question(
        question
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    steps = [
        "question reçue",
        "question envoyée à gemma 4",
    ]

    tools_used = []
    collected_data = []

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
                seconds=180
            ),
        ) as session:
            await session.initialize()

            steps.append(
                "connexion MCP réussie"
            )

            # maximum trois tours pour éviter
            # une boucle infinie du modèle
            for _ in range(3):
                response = await ask_model(
                    messages=messages,
                    with_tools=True,
                )

                messages.append(
                    response.message
                )

                tool_calls = (
                    response.message.tool_calls
                    or []
                )

                if not tool_calls:
                    answer = (
                        response.message.content
                        or ""
                    ).strip()

                    if not answer:
                        raise RuntimeError(
                            "Gemma 4 n'a produit "
                            "ni réponse ni appel d'outil"
                        )

                    if not tools_used:
                        steps.append(
                            "aucun outil MCP sélectionné"
                        )
                    else:
                        steps.append(
                            "réponse finale générée "
                            "par gemma 4"
                        )

                    return {
                        "question": question,
                        "steps": steps,
                        "tools_used": tools_used,
                        "data": (
                            collected_data[0]
                            if len(collected_data) == 1
                            else collected_data
                        ),
                        "answer": answer,
                    }

                for tool_call in tool_calls:
                    tool_name = (
                        tool_call.function.name
                    )

                    if tool_name not in {
                        "list_plants",
                        "get_consumption",
                        "simulate_phase3",
                    }:
                        raise RuntimeError(
                            "Outil interdit ou inconnu : "
                            f"{tool_name}"
                        )

                    arguments = (
                        normalize_tool_arguments(
                            tool_name,
                            tool_call.function.arguments,
                        )
                    )

                    steps.append(
                        f"outil sélectionné : {tool_name}"
                    )

                    result = await session.call_tool(
                        tool_name,
                        arguments=arguments,
                    )

                    result_text = (
                        mcp_result_to_text(
                            result
                        )
                    )

                    result_data = (
                        parse_result_for_interface(
                            result_text
                        )
                    )

                    tools_used.append({
                        "name": tool_name,
                        "arguments": arguments,
                    })

                    collected_data.append(
                        result_data
                    )

                    steps.append(
                        f"résultat reçu pour {tool_name}"
                    )

                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": result_text,
                    })

    raise RuntimeError(
        "Gemma 4 a dépassé le nombre "
        "maximal d'appels d'outils"
    )


async def main():
    question = input(
        "Question pour EnergIA : "
    )

    try:
        result = await ask_energia(
            question
        )

        print()
        print("Processus")

        for step in result["steps"]:
            print(
                f"  {step}"
            )

        print()
        print("Outils utilisés")

        if result["tools_used"]:
            for tool in result["tools_used"]:
                print(
                    f"  {tool['name']} "
                    f"{tool['arguments']}"
                )
        else:
            print(
                "  aucun outil"
            )

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
        print(
            result["answer"]
        )

    except Exception as error:
        print()
        print(
            f"Assistant indisponible : {error}"
        )

        traceback.print_exception(
            error
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )