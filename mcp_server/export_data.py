# LLM ou client MCP
#         ↓
# mcp_server/tool.py
#         ↓
# services/energia_service.py
#         ↓
# moteur de simulation EnergIA


import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


PROJECT_DIRECTORY = (
    Path(__file__).resolve().parent.parent
)

MS_PYTHON_2_DIRECTORY = (
    PROJECT_DIRECTORY / "ms-python-2"
)

sys.path.insert(
    0,
    str(MS_PYTHON_2_DIRECTORY),
)


from services.energia_service import (
    get_plant_simulated_status,
    get_plant_status,
    get_region_consumption,
    get_region_energy_status,
    get_simulation_step,
    list_plants,
    list_regions,
)


mcp = FastMCP(
    "EnergIA MCP Server",
    host="127.0.0.1",
    port=8003,
)

@mcp.tool()
def energia_list_regions():
    return list_regions()


@mcp.tool()
def energia_list_plants():
   # la liste des centrales nucléaires

    return list_plants()


@mcp.tool()
def energia_get_plant_configuration(
    plant_id: str,
):
    # la configuration initiale d'une centrale

    # ex plant_id : golfech.

    return get_plant_status(plant_id)


@mcp.tool()
def energia_get_region_consumption(
    region_id: str,
    timestamp: str,
):
    # la consommation de référence d'une région à une heure donnée

    #ex
    # region_id = occitanie
    # timestamp = 18:00

    return get_region_consumption(
        region_id,
        timestamp,
    )


@mcp.tool()
def energia_get_simulation_step(
    timestamp: str,
):
    # retourne tous les résultats de la simulation pour un quart d'heure précis
    return get_simulation_step(timestamp)


@mcp.tool()
def energia_get_plant_simulated_status(
    plant_id: str,
    timestamp: str,
):
    # retourne la production et les contraintes calculées d'une centrale à une heure précise
    return get_plant_simulated_status(
        plant_id,
        timestamp,
    )


@mcp.tool()
def energia_get_region_status(
    region_id: str,
    timestamp: str,
):
    #retourne la situation énergétique calculée d'une région à une heure précise.
    return get_region_energy_status(
        region_id,
        timestamp,
    )
from starlette.responses import JSONResponse


@mcp.custom_route("/", methods=["GET"])
async def home(request):
    return JSONResponse({
        "application": "EnergIA MCP Server",
        "status": "running",
        "mcp_endpoint": "/mcp",
    })


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({
        "status": "ok",
        "service": "EnergIA MCP Server",
    })



if __name__ == "__main__":
    mcp.run(
        transport="streamable-http"
    )