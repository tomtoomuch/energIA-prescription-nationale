try:
    from .allocation import allocate
except ImportError:
    from allocation import allocate


def distribute_change_between_regions(
    regional_demands,
    requested_change_mw,
):
    """
    Répartit la variation nationale entre les régions
    proportionnellement à leur consommation.
    """

    total_demand_mw = sum(
        float(demand_mw)
        for demand_mw in regional_demands.values()
    )

    if total_demand_mw <= 0:
        return {
            region_id: 0.0
            for region_id in regional_demands
        }

    return {
        region_id: (
            float(requested_change_mw)
            * float(demand_mw)
            / total_demand_mw
        )
        for region_id, demand_mw
        in regional_demands.items()
    }

def distribute_down_change(
    current_state,
    requested_change_mw,
    plant_limits,
):
    """
    Répartit une baisse entre les centrales selon
    leur flexibilité de descente.
    """

    next_state = current_state.copy()

    total_down_flexibility_mw = sum(
        float(
            limits.get(
                "down_flexibility_mw",
                0.0,
            )
        )
        for limits in plant_limits.values()
    )

    possible_change_mw = min(
        float(requested_change_mw),
        total_down_flexibility_mw,
    )

    plant_changes = {}

    if total_down_flexibility_mw <= 0:
        return {
            "state": next_state,
            "plant_changes": plant_changes,
            "applied_change_mw": 0.0,
            "forced_surplus_mw": float(
                requested_change_mw
            ),
        }

    for plant_id, limits in plant_limits.items():
        flexibility_mw = float(
            limits.get(
                "down_flexibility_mw",
                0.0,
            )
        )

        if flexibility_mw <= 0:
            continue

        allocated_change_mw = (
            possible_change_mw
            * flexibility_mw
            / total_down_flexibility_mw
        )

        allocated_change_mw = min(
            allocated_change_mw,
            flexibility_mw,
        )

        next_state[plant_id] -= (
            allocated_change_mw
        )

        plant_changes[plant_id] = (
            -allocated_change_mw
        )

    applied_change_mw = sum(
        abs(change_mw)
        for change_mw in plant_changes.values()
    )

    return {
        "state": next_state,
        "plant_changes": plant_changes,
        "applied_change_mw": applied_change_mw,
        "forced_surplus_mw": max(
            0.0,
            float(requested_change_mw)
            - applied_change_mw,
        ),
    }

def allocate_regional_demands(
    regional_demands,
    current_state,
    graph,
    plants_index,
    regions_index,
    simulation_parameters,
    plant_limits=None,
):


    next_state = current_state.copy()
    regional_results = {}
    if plant_limits is None:
        plant_limits = {}

    total_demand_mw = sum(
        float(demand_mw)
        for demand_mw in regional_demands.values()
    )

    current_production_mw = sum(
        float(output_mw)
        for output_mw in current_state.values()
    )

    production_difference_mw = (
        total_demand_mw
        - current_production_mw
    )

    if production_difference_mw > 0:
        direction = "up"
        requested_change_mw = production_difference_mw

    elif production_difference_mw < 0:
        direction = "down"
        requested_change_mw = abs(
            production_difference_mw
        )

    else:
        direction = "stable"
        requested_change_mw = 0.0

    if direction == "up":
        regional_requested_changes = (
            distribute_change_between_regions(
                regional_demands,
                requested_change_mw,
            )
        )
    else:
        regional_requested_changes = {
            region_id: 0.0
            for region_id in regional_demands
        }

    total_missing_mw = 0.0
    forced_surplus_mw = 0.0

    if direction == "up":

        step_initial_state = (
            current_state.copy()
        )

        for (
            region_id,
            regional_change_mw,
        ) in regional_requested_changes.items():

            if regional_change_mw <= 0:
                continue

            if region_id not in regions_index:
                raise ValueError(
                    f"Région inconnue : {region_id}"
                )

            region = regions_index[region_id]

            allocation_result = allocate(
                region=region,
                additional_demand_mw=regional_change_mw,
                graph=graph,
                plants_index=plants_index,
                simulation_parameters=(
                    simulation_parameters
                ),
                current_state=next_state,
                step_initial_state=(
                    step_initial_state
                ),
                plant_limits=plant_limits,
            )

            for allocation in allocation_result[
                "allocations"
            ]:
                plant_id = allocation["plant_id"]
                allocated_mw = float(
                    allocation["allocated_mw"]
                )

                next_state[plant_id] = (
                    next_state[plant_id]
                    + allocated_mw
                )

            regional_results[region_id] = (
                allocation_result
            )

            total_missing_mw += float(
                allocation_result["missing_mw"]
            )

    elif direction == "down":
        down_result = distribute_down_change(
            current_state=current_state,
            requested_change_mw=(
                requested_change_mw
            ),
            plant_limits=plant_limits,
        )

        next_state = down_result["state"]

        regional_results[
            "production_down"
        ] = down_result

        forced_surplus_mw = float(
            down_result["forced_surplus_mw"]
        )
    
    return {
        "state": next_state,
        "regional_results": regional_results,
        "total_demand_mw": total_demand_mw,
        "current_production_mw": current_production_mw,
        "direction": direction,
        "requested_change_mw": requested_change_mw,
        "regional_requested_changes":regional_requested_changes,
        "missing_mw": total_missing_mw,
        "forced_surplus_mw":forced_surplus_mw,

    }
    