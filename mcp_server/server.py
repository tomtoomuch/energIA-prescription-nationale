from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

from tool import get_plants


mcp = FastMCP(
    "EnergIA MCP Server",
    host="0.0.0.0",
    port=8003,
    streamable_http_path="/mcp",
)


@mcp.tool()
def energia_list_plants() -> dict:
    """
    Retourne la liste des centrales nucléaires EnergIA.

    Les données sont récupérées par HTTP auprès de
    l'API métier EnergIA. Elles ne sont pas inventées
    et ne sont pas calculées par le LLM.
    """
    return get_plants()


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