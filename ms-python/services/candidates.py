"""Assemble priority.py (locale/externe) et dijkstra.shortest_paths_from
(le reste du graphe) pour donner, pour une région, TOUTES les centrales
candidates avec leur distance et leurs pertes
"""
try:
    from .priority import local_plant_ids, external_entry_plant_ids
    from .dijkstra import shortest_paths_from
except ImportError:
    from priority import local_plant_ids, external_entry_plant_ids
    from dijkstra import shortest_paths_from


def region_candidates(graph, region):

    candidates = {}

    for plant_id in local_plant_ids(region):
        candidates[plant_id] = {
            "distance_km": 0.0,
            "loss_percent": 0.0,
            "path": [plant_id],
            "is_local": True,
        }

    anchors = local_plant_ids(region) or external_entry_plant_ids(region)

    for anchor in anchors:
        if anchor not in graph:
            continue

        for plant_id, info in shortest_paths_from(graph, anchor).items():
            if candidates.get(plant_id, {}).get("is_local"):
                continue

            # On garde la distance la plus courte trouvée depuis n'importe quel ancrage
            if plant_id not in candidates or info["distance_km"] < candidates[plant_id]["distance_km"]:
                candidates[plant_id] = {
                    "distance_km": info["distance_km"],
                    "loss_percent": info["loss_percent"],
                    "path": info["path"],
                    "is_local": False,
                }

    return candidates


if __name__ == "__main__":
    from graph_loader import load_data, build_graph, build_regions_index

    data = load_data()
    graph = build_graph(data)
    regions_index = build_regions_index(data)

    occitanie = regions_index["occitanie"]
    candidates = region_candidates(graph, occitanie)
    print("Nombre de candidates pour l'Occitanie :", len(candidates))
    print("golfech (doit être locale, distance 0) :", candidates["golfech"])
    print("nogent (doit être trouvée via le graphe) :", candidates["nogent"])

    ile_de_france = regions_index["ile_de_france"]
    candidates_idf = region_candidates(graph, ile_de_france)
    print("Nombre de candidates pour l'Île-de-France (pas de locale) :", len(candidates_idf))
    print("nogent pour l'Île-de-France (doit être une des externes, distance > 0) :", candidates_idf["nogent"])