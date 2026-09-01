from services.energia_service import (
    list_regions,
    list_plants,
    get_plant_status,
    get_region_consumption,
)

# mcp_server/tools.py
#       ↓ requête HTTP
# http://ms-python-2:8002/phase1/consumption
#       ↓
# FastAPI
#       ↓
# energia_service.py
#       ↓
# données EnergIA