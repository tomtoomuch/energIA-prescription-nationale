"""
Calcule le score d'une centrale candidate.
La formule et les pondérations sont lues depuis le fichier JSON.
Plus le score est faible, plus la centrale est intéressante.
"""


def candidate_score(
    plant,
    distance_km,
    loss_percent,
    allocated_mw,
    is_local,
    simulation_parameters
):
    simulation = plant["simulation"]

    # Production après l'ajout proposé.
    final_output_mw = (
        simulation["initial_output_mw"]
        + allocated_mw
    )

    # Taux de saturation final de la centrale.
    final_load_ratio = (
        final_output_mw
        / plant["installed_power_mw"]
    )

    # Score pondéré défini dans simulation_parameters.
    score = (
        distance_km
        * simulation_parameters["distance_weight"]
        + loss_percent
        * simulation_parameters["loss_weight"]
        + (final_load_ratio ** 4)
        * simulation_parameters["saturation_weight"]
        + simulation["technical_penalty"]
        * simulation_parameters["technical_penalty_weight"]
    )

    # Le bonus régional est négatif :
    # il réduit le score d'une centrale locale.
    if is_local:
        score += simulation_parameters["regional_priority_bonus"]

    return round(score, 2)


if __name__ == "__main__":
    from graph_loader import (
        load_data,
        build_graph,
        build_plants_index,
        build_regions_index
    )
    from candidates import region_candidates
    from capacity import dispatchable_margin

    # Chargement des données et construction des index.
    data = load_data()
    graph = build_graph(data)
    plants_index = build_plants_index(data)
    regions_index = build_regions_index(data)

    # Les poids sont lus directement depuis le JSON.
    simulation_parameters = data["simulation_parameters"]

    # Région étudiée.
    occitanie = regions_index["occitanie"]

    # Toutes les centrales candidates avec distance,
    # pertes, chemin et statut local/externe.
    candidates = region_candidates(graph, occitanie)

    # Exemple avec une centrale locale.
    golfech = plants_index["golfech"]
    golfech_candidate = candidates["golfech"]
    golfech_margin = dispatchable_margin(golfech)
    golfech_score = candidate_score(
        plant=golfech,
        distance_km=golfech_candidate["distance_km"],
        loss_percent=golfech_candidate["loss_percent"],
        allocated_mw=golfech_margin,
        is_local=golfech_candidate["is_local"],
        simulation_parameters=simulation_parameters
    )
    print("Centrale :", golfech["name"])
    print("Chemin :", golfech_candidate["path"])
    print("Distance :", golfech_candidate["distance_km"], "km")
    print("Pertes estimées :", golfech_candidate["loss_percent"], "%")
    print("Puissance mobilisable :", golfech_margin, "MW")
    print("Est locale :", golfech_candidate["is_local"])
    print("Score :", golfech_score)
    print()

    # Exemple avec une centrale externe.
    plant_id = "tricastin"
    plant = plants_index[plant_id]
    candidate = candidates[plant_id]
    allocated_mw = dispatchable_margin(plant)
    score = candidate_score(
        plant=plant,
        distance_km=candidate["distance_km"],
        loss_percent=candidate["loss_percent"],
        allocated_mw=allocated_mw,
        is_local=candidate["is_local"],
        simulation_parameters=simulation_parameters
    )
    print("Centrale :", plant["name"])
    print("Chemin :", candidate["path"])
    print("Distance :", candidate["distance_km"], "km")
    print("Pertes estimées :", candidate["loss_percent"], "%")
    print("Puissance mobilisable :", allocated_mw, "MW")
    print("Est locale :", candidate["is_local"])
    print("Score :", score)