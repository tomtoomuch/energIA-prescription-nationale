
import json
import os

# Chemin par défaut du fichier de données, relatif à ce fichier.
DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "parc_nucleaire_prescriptif_france.json"
)


def load_data(path=DEFAULT_DATA_PATH):
    """
    Ouvre le fichier JSON et retourne son contenu sous forme de dictionnaire Python.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_graph(data):
    """
    Construit un graphe à partir de data["plant_edges"].

"""
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
    """Dictionnaire {plant_id: plant_dict}, utile pour les étapes suivantes."""
    return {plant["id"]: plant for plant in data["plants"]}


def build_regions_index(data):
    """Pareil que build_plants_index, mais pour les régions."""
    return {region["id"]: region for region in data["regions"]}


if __name__ == "__main__":
    data = load_data()
    graph = build_graph(data)

    print(f"Nombre de centrales dans le graphe : {len(graph)}")
    print(f"Voisins de golfech : {graph['golfech']}")