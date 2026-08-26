try:
    from .candidates import region_candidates
    from .capacity import dispatchable_margin, ramp_limit
    from .score import candidate_score
except ImportError:
    from candidates import region_candidates
    from capacity import dispatchable_margin, ramp_limit
    from score import candidate_score


def path_capacity(graph, path):
    # Capacité maximale de transfert (en MW)
    # la plus petite capacité parmi toutes les liaisons traversées
    # Pour une centrale locale (chemin d'un seul élément, aucune
    # liaison traversée)
    #
    if len(path) < 2:
        return float("inf")

    capacities = []
    for i in range(len(path) - 1):
        from_plant = path[i]
        to_plant = path[i + 1]
        edge = next((e for e in graph[from_plant] if e["to"] == to_plant), None)
        if edge is None:
            return 0.0
        capacities.append(edge["max_transfer_mw"])

    return min(capacities)


def allocate(
    region,
    additional_demand_mw,
    graph,
    plants_index,
    simulation_parameters,
    current_state=None,
    step_initial_state=None,
):
    candidates = region_candidates(graph, region)
    remaining_demand = additional_demand_mw
    allocations = []
    used_plants = set()

    while remaining_demand > 0:
        best_plant_id = None
        best_score = None
        best_amount = None

        for plant_id, info in candidates.items():
            if plant_id in used_plants:
                continue

            plant = plants_index[plant_id]
            if current_state is None:
                current_output_mw = float(
                plant["simulation"]["initial_output_mw"])
            else:
                current_output_mw = float(
                  current_state.get(
                 plant_id,
                plant["simulation"]["initial_output_mw"],))
        
            margin = dispatchable_margin(
                plant,
                current_output_mw=current_output_mw,
                )

            ramp = float(
                ramp_limit(plant)
            )

            if step_initial_state is None:
                remaining_ramp_mw = ramp
            else:
                output_at_step_start_mw = float(
                    step_initial_state.get(
                        plant_id,
                        current_output_mw,
                    )
                )

                already_added_mw = max(
                    0.0,
                    current_output_mw
                    - output_at_step_start_mw,
                )

                remaining_ramp_mw = max(
                    0.0,
                    ramp - already_added_mw,
                )
            link_capacity = path_capacity(graph, info["path"])

            max_deliverable = min(
                margin,
                remaining_ramp_mw,
                link_capacity,
                remaining_demand,
            )

            if max_deliverable <= 0:
                continue

            score = candidate_score(
                plant,
                info["distance_km"],
                info["loss_percent"],
                max_deliverable,
                info["is_local"],
                simulation_parameters,
                current_output_mw=current_output_mw,
            )

            if best_score is None or score < best_score:
                best_plant_id = plant_id
                best_score = score
                best_amount = max_deliverable

        if best_plant_id is None:
            break  # plus aucune centrale ne peut contribuer

        plant = plants_index[best_plant_id]

        if current_state is None:
            current_output_mw = float(
                plant["simulation"]["initial_output_mw"]
            )
        else:
            current_output_mw = float(
                current_state.get(
                    best_plant_id,
                    plant["simulation"]["initial_output_mw"],
                )
            )

        final_output_mw = (
            current_output_mw
            + best_amount
        )

        final_load_ratio = (
            final_output_mw
            / plant["installed_power_mw"]
        )

        allocations.append({
            "plant_id": best_plant_id,
            "allocated_mw": best_amount,
            "final_load_ratio": final_load_ratio,
            "path": candidates[best_plant_id]["path"],
            "distance_km": candidates[best_plant_id]["distance_km"],
            "loss_percent": candidates[best_plant_id]["loss_percent"],
            "score": best_score,
        })

        used_plants.add(best_plant_id)
        remaining_demand -= best_amount

    missing_mw = max(0.0, remaining_demand)

    return {
        "allocations": allocations,
        "missing_mw": missing_mw,
        "fully_satisfied": missing_mw == 0,
    }


if __name__ == "__main__":
    from graph_loader import load_data, build_graph, build_plants_index, build_regions_index

    data = load_data()
    graph = build_graph(data)
    plants_index = build_plants_index(data)
    regions_index = build_regions_index(data)
    simulation_parameters = data["simulation_parameters"]

    occitanie = regions_index["occitanie"]
    result = allocate(occitanie, 1200, graph, plants_index, simulation_parameters)
    print(" Occitanie, demande de 1200 MW ")
    for alloc in result["allocations"]:
        print(f"  {alloc['plant_id']}: {alloc['allocated_mw']:.1f} MW, taux final {alloc['final_load_ratio']:.3f}")
    print("MW manquants :", result["missing_mw"])
    print("Demande entièrement couverte :", result["fully_satisfied"])

    corse = regions_index["corse"]
    result_corse = allocate(corse, 300, graph, plants_index, simulation_parameters)
    print("=== Corse, demande de 300 MW ===")
    print("Allocations :", result_corse["allocations"])
    print("MW manquants :", result_corse["missing_mw"])
    print("Demande entièrement couverte :", result_corse["fully_satisfied"])