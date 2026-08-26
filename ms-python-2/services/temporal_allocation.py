try:
    from .allocation import allocate
except ImportError:
    from allocation import allocate


def allocate_regional_demands(
    regional_demands,
    current_state,
    graph,
    plants_index,
    regions_index,
    simulation_parameters,
):


    next_state = current_state.copy()
    regional_results = {}

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

    return {
        "state": next_state,
        "regional_results": regional_results,
        "total_demand_mw": total_demand_mw,
        "current_production_mw": current_production_mw,
        "direction": direction,
        "requested_change_mw": requested_change_mw,
        "missing_mw": 0.0,
    }
    