import json

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from urllib.parse import unquote

from tool import (
    get_plants,
    get_region_consumption,
    get_phase3_simulation,
)


mcp = FastMCP(
    "EnergIA MCP Server",
    host="0.0.0.0",
    port=8003,
    streamable_http_path="/mcp",
)


def _to_json(data):
   # transforme les données en texte json valide
    return json.dumps(
        data,
        ensure_ascii=False,
        allow_nan=False,
    )


@mcp.resource(
    "energia://plants",
    name="energia_plants",
    mime_type="application/json",
)
def plants_resource() -> str:
    # retourne les centrales du jeu de données energ ia
    # les données sont récupérées depuis fastapi

    return _to_json(
        get_plants()
    )

@mcp.resource(
    "energia://consumption/{region_id}/{timestamp}",
    name="energia_reference_consumption",
    mime_type="application/json",
)
def consumption_resource(region_id: str, timestamp: str) -> str:
    # décode les paramètres provenant de l'uri
    region_id = unquote(region_id)
    timestamp = unquote(timestamp)

    # récupère les données depuis fastapi
    data = get_region_consumption(region_id, timestamp)

    # renvoie le résultat au format json
    return _to_json(data)
# la fonction standard unquote() transforme notamment 16%3A00 en 16:00



@mcp.resource(
    "energia://phase3/{scenario_id}/{number_of_steps}/{minimum_reserve_mw}",
    name="energia_phase3_simulation",
    mime_type="application/json",
)
def phase3_resource(
    scenario_id: str,
    number_of_steps: str,
    minimum_reserve_mw: str,
) -> str:

    # retourne une simulation de phase 3 avec scénario
    #
    # chaque lecture déclenche une nouvelle simulation
    # dans fastapi
    #
    # utiliser 96 pas pour une journée complète
    # les résultats sont simulés et non mesurés en direct

    try:
        steps_count = int(number_of_steps)
    except ValueError as error:
        raise ValueError(
            "le nombre de pas doit être un entier"
        ) from error

    try:
        reserve_mw = float(minimum_reserve_mw)
    except ValueError as error:
        raise ValueError(
            "la réserve minimale doit être un nombre"
        ) from error

    data = get_phase3_simulation(
        scenario_id=scenario_id,
        number_of_steps=steps_count,
        minimum_reserve_mw=reserve_mw,
    )

    return _to_json(data)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({
        "status": "ok",
        "service": "EnergIA MCP Server",
    })


if __name__ == "__main__":
    app = mcp.run(
        transport="streamable-http"
    )
