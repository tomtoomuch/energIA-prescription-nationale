import os
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from services.graph_loader import load_data, build_plants_index, build_regions_index, build_graph
from services.allocation import allocate

app = FastAPI()

data = load_data()
plants_index = build_plants_index(data)
regions_index = build_regions_index(data)
graph = build_graph(data)
simulation_parameters = data["simulation_parameters"]

SECURITY_TOKEN = os.getenv("SECURITY_TOKEN")


def verify_api_key(x_api_key: str = Header(alias="x-api-key")):
    if not SECURITY_TOKEN or x_api_key != SECURITY_TOKEN:
        raise HTTPException(status_code=401, detail="Cle API invalide")


class SimulationRequest(BaseModel):
    region: str
    additional_demand_mw: float


@app.get("/health")
def read_health():
    return {"status": "Python MS Up and running"}


@app.get("/plants", dependencies=[Depends(verify_api_key)])
def read_plants():
    return list(plants_index.values())

@app.get("/regions", dependencies=[Depends(verify_api_key)])
def read_regions():
    return list(regions_index.values())



@app.get("/network", dependencies=[Depends(verify_api_key)])
def read_network():
    return graph



@app.post("/simulate", dependencies=[Depends(verify_api_key)])
def simulate(request: SimulationRequest):
    region = regions_index.get(request.region)

    if region is None:
        raise HTTPException(
            status_code=404,
            detail=f"Region inconnue: {request.region}"
        )

    return allocate(
        region,
        request.additional_demand_mw,
        graph,
        plants_index,
        simulation_parameters
    )