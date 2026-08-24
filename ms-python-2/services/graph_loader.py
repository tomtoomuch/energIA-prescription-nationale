
import json
import os


DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "parc_nucleaire_prescriptif_france.json"
)

REFERENCE_CONSUMPTION_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "energia-journee-reference-consommation.json"
)

TEMPORAL_NUCLEAR_PARAMETERS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "energia-parametres-temporels-nucleaire.json"
)


def load_data(path=DEFAULT_DATA_PATH):

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_reference_consumption(path=REFERENCE_CONSUMPTION_PATH):
    data = load_data(path)
    timestamps = data.get("timestamps", [])
    totals = data.get("national_total_consumption_mw", [])

    if len(timestamps) != 96 or len(totals) != 96:
        raise ValueError(
            "La journée de référence doit contenir 96 horaires et 96 consommations"
        )

    for region in data.get("regions", []):
        if len(region.get("consumption_mw", [])) != 96:
            raise ValueError(
                f"La région {region.get('id', 'inconnue')} ne contient pas 96 valeurs"
            )

    return data


def load_temporal_nuclear_parameters(path=TEMPORAL_NUCLEAR_PARAMETERS_PATH):
    data = load_data(path)
    plants = data.get("plants", [])
    if not plants:
        raise ValueError("Aucun paramètre temporel de centrale trouvé")

    required_fields = {
        "plant_id",
        "initial_output_mw_at_23_45_previous_day",
        "minimum_operating_power_mw",
        "maximum_power_mw",
        "max_ramp_up_mw_per_15_min",
        "max_ramp_down_mw_per_15_min",
    }
    for plant in plants:
        missing = required_fields - plant.keys()
        if missing:
            raise ValueError(
                f"Paramètres manquants pour {plant.get('plant_id', 'centrale inconnue')}: "
                f"{', '.join(sorted(missing))}"
            )
    return data


def build_graph(data):
    #un graphe à partir de data["plant_edges"].

    graph = {}

    for edge in data["plant_edges"]:
        plant_a = edge["from"]
        plant_b = edge["to"]

        graph.setdefault(plant_a, [])
        graph.setdefault(plant_b, [])

        edge_info_a_to_b = {
            "to": plant_b,
            "distance_km": edge["geodesic_distance_km"],
            "loss_percent": edge["estimated_loss_percent"],
            "max_transfer_mw": edge["max_transfer_mw"],
            "available": edge["available"],
        }
        edge_info_b_to_a = {
            "to": plant_a,
            "distance_km": edge["geodesic_distance_km"],
            "loss_percent": edge["estimated_loss_percent"],
            "max_transfer_mw": edge["max_transfer_mw"],
            "available": edge["available"],
        }

        graph[plant_a].append(edge_info_a_to_b)

        if edge.get("bidirectional", True):
            graph[plant_b].append(edge_info_b_to_a)

    return graph


def build_plants_index(data):
    return {plant["id"]: plant for plant in data["plants"]}


def build_regions_index(data):
    return {region["id"]: region for region in data["regions"]}


if __name__ == "__main__":
    data = load_data()
    graph = build_graph(data)

    print(f"Nombre de centrales dans le graphe : {len(graph)}")
    print(f"Voisins de golfech : {graph['golfech']}")
