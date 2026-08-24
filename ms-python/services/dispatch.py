"""
Répartit une demande supplémentaire entre plusieurs centrales.

Les centrales sont triées selon leur score.
La demande est distribuée jusqu'à satisfaction ou épuisement
des capacités disponibles.
"""




# Déclaration de la fonction dispatch_power qui prend en entrée
# l'index des centrales, les candidates, les paramètres de simulation et la demande en MW.
def dispatch_power(
    plants_index,
    candidates,
    simulation_parameters,
    requested_mw
):
    # Déclaration d'une liste vide pour stocker le classement des centrales.
    allocations = []

    # Construction de la liste des candidates avec leur score.
    for plant_id, candidate in candidates.items():

        plant = plants_index[plant_id]

        capacity = available_capacity(plant)

        if capacity <= 0:
            continue

        score = candidate_score(
            plant=plant,
            distance_km=candidate["distance_km"],
            loss_percent=candidate["loss_percent"],
            allocated_mw=capacity,
            is_local=candidate["is_local"],
            simulation_parameters=simulation_parameters
        )

        allocations.append({
            "plant_id": plant_id,
            "score": score,
            "capacity": capacity
        })

    # Les meilleures centrales en premier.
    allocations.sort(key=lambda x: x["score"])

    remaining = requested_mw

    # Déclaration d'une liste vide pour stocker la répartition de la demande.
    dispatch = []

    for plant in allocations:

        if remaining <= 0:
            break

        allocated = min(
            remaining,
            plant["capacity"]
        )

        dispatch.append({
            "plant_id": plant["plant_id"],
            "allocated_mw": allocated,
            "score": plant["score"]
        })

        remaining -= allocated

    return {
        "dispatch": dispatch,
        "remaining_mw": remaining
    }

# POINT D'ENTREE DU SCRIPT ms-python/services/dispatch.py
# Si le script est exécuté directement, on charge les données, on construit le graphe
# et les index, puis on appelle la fonction dispatch_power avec une demande de 500 MW pour la région Occitanie.
if __name__ == "__main__":

    from graph_loader import (
        load_data,
        build_graph,
        build_plants_index,
        build_regions_index
    )

    from candidates import region_candidates
    from capacity import available_capacity
    from score import candidate_score

    data = load_data()

    graph = build_graph(data)

    plants_index = build_plants_index(data)

    regions_index = build_regions_index(data)

    simulation_parameters = data["simulation_parameters"]

    occitanie = regions_index["occitanie"]

    candidates = region_candidates(
        graph,
        occitanie
    )

    result = dispatch_power(
        plants_index,
        candidates,
        simulation_parameters,
        requested_mw=500
    )

    print(result)