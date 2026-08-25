EPSILON = 0.000001


def build_initial_state(plants):


    state = {}

    for plant in plants:
        plant_id = plant["plant_id"]

        output_mw = float(
            plant[
                "initial_output_mw_at_23_45_previous_day"
            ]
        )

        minimum_mw = float(
            plant["minimum_operating_power_mw"]
        )

        maximum_mw = float(
            plant["maximum_power_mw"]
        )

        if minimum_mw > maximum_mw:
            raise ValueError(
                f"Limites incohérentes pour {plant_id} : "
                f"minimum={minimum_mw} MW, "
                f"maximum={maximum_mw} MW"
            )

        if not minimum_mw <= output_mw <= maximum_mw:
            raise ValueError(
                f"Production initiale de {plant_id} "
                f"hors limites : {output_mw} MW"
            )

        state[plant_id] = output_mw

    return state


def get_regional_consumption(
    consumption_data,
    index
):


    regional_consumption = {}

    for region in consumption_data["regions"]:
        region_id = region["id"]

        consumption_mw = float(
            region["consumption_mw"][index]
        )

        regional_consumption[region_id] = (
            consumption_mw
        )

    return regional_consumption


def calculate_plant_limits(
    plant,
    current_output_mw
):

    minimum_mw = float(
        plant["minimum_operating_power_mw"]
    )

    maximum_mw = float(
        plant["maximum_power_mw"]
    )

    ramp_up_mw = float(
        plant["max_ramp_up_mw_per_15_min"]
    )

    ramp_down_mw = float(
        plant["max_ramp_down_mw_per_15_min"]
    )

    available = bool(
        plant.get("available", True)
    )

    if not available:
        return {
            "minimum_reachable_mw":
                current_output_mw,

            "maximum_reachable_mw":
                current_output_mw,

            "up_flexibility_mw": 0.0,
            "down_flexibility_mw": 0.0,
        }

    minimum_reachable_mw = max(
        minimum_mw,
        current_output_mw - ramp_down_mw
    )

    maximum_reachable_mw = min(
        maximum_mw,
        current_output_mw + ramp_up_mw
    )

    return {
        "minimum_reachable_mw":
            minimum_reachable_mw,

        "maximum_reachable_mw":
            maximum_reachable_mw,

        "up_flexibility_mw": max(
            0.0,
            maximum_reachable_mw
            - current_output_mw
        ),

        "down_flexibility_mw": max(
            0.0,
            current_output_mw
            - minimum_reachable_mw
        ),
    }


def distribute_change(
    plants,
    previous_state,
    requested_change_mw,
    direction,
    plant_limits
):



    next_state = previous_state.copy()

    if requested_change_mw <= EPSILON:
        return next_state

    if direction == "up":
        flexibility_key = "up_flexibility_mw"
    else:
        flexibility_key = "down_flexibility_mw"

    total_flexibility_mw = sum(
        plant_limits[plant["plant_id"]][
            flexibility_key
        ]
        for plant in plants
    )

    possible_change_mw = min(
        requested_change_mw,
        total_flexibility_mw
    )

    if total_flexibility_mw <= EPSILON:
        return next_state

    remaining_change_mw = possible_change_mw
    flexible_plants = []

    for plant in plants:
        plant_id = plant["plant_id"]

        flexibility_mw = plant_limits[
            plant_id
        ][flexibility_key]

        if flexibility_mw > EPSILON:
            flexible_plants.append(plant)

    for index, plant in enumerate(
        flexible_plants
    ):
        plant_id = plant["plant_id"]

        flexibility_mw = plant_limits[
            plant_id
        ][flexibility_key]

        is_last_plant = (
            index == len(flexible_plants) - 1
        )

        if is_last_plant:
            allocated_change_mw = min(
                remaining_change_mw,
                flexibility_mw
            )
        else:
            allocated_change_mw = (
                possible_change_mw
                * flexibility_mw
                / total_flexibility_mw
            )

            allocated_change_mw = min(
                allocated_change_mw,
                flexibility_mw,
                remaining_change_mw
            )

        if direction == "up":
            next_state[plant_id] += (
                allocated_change_mw
            )
        else:
            next_state[plant_id] -= (
                allocated_change_mw
            )

        remaining_change_mw -= (
            allocated_change_mw
        )

    return next_state


def simulate_step(
    plants,
    previous_state,
    demand_mw
):


    demand_mw = float(demand_mw)

    if demand_mw < 0:
        raise ValueError(
            "La consommation ne peut pas être négative"
        )

    plant_ids = {
        plant["plant_id"]
        for plant in plants
    }

    state_ids = set(
        previous_state.keys()
    )

    if plant_ids != state_ids:
        raise ValueError(
            "L'état précédent ne correspond pas "
            "aux centrales de la DataFrame"
        )

    previous_total_mw = sum(
        previous_state.values()
    )

    plant_limits = {}

    for plant in plants:
        plant_id = plant["plant_id"]

        plant_limits[plant_id] = (
            calculate_plant_limits(
                plant,
                previous_state[plant_id]
            )
        )

    maximum_reachable_total_mw = sum(
        limits["maximum_reachable_mw"]
        for limits in plant_limits.values()
    )

    minimum_reachable_total_mw = sum(
        limits["minimum_reachable_mw"]
        for limits in plant_limits.values()
    )

    difference_mw = (
        demand_mw - previous_total_mw
    )

    if difference_mw > EPSILON:
        direction = "up"

        next_state = distribute_change(
            plants=plants,
            previous_state=previous_state,
            requested_change_mw=difference_mw,
            direction=direction,
            plant_limits=plant_limits,
        )

    elif difference_mw < -EPSILON:
        direction = "down"

        next_state = distribute_change(
            plants=plants,
            previous_state=previous_state,
            requested_change_mw=abs(
                difference_mw
            ),
            direction=direction,
            plant_limits=plant_limits,
        )

    else:
        direction = "stable"
        next_state = previous_state.copy()

    production_mw = sum(
        next_state.values()
    )

    missing_mw = max(
        0.0,
        demand_mw - production_mw
    )

    forced_surplus_mw = max(
        0.0,
        production_mw - demand_mw
    )

    plant_states = []

    for plant in plants:
        plant_id = plant["plant_id"]

        previous_output_mw = (
            previous_state[plant_id]
        )

        output_mw = next_state[plant_id]

        change_mw = (
            output_mw - previous_output_mw
        )

        minimum_mw = float(
            plant["minimum_operating_power_mw"]
        )

        maximum_mw = float(
            plant["maximum_power_mw"]
        )

        ramp_up_mw = float(
            plant[
                "max_ramp_up_mw_per_15_min"
            ]
        )

        ramp_down_mw = float(
            plant[
                "max_ramp_down_mw_per_15_min"
            ]
        )

        respects_minimum = (
            output_mw >= minimum_mw - EPSILON
        )

        respects_maximum = (
            output_mw <= maximum_mw + EPSILON
        )

        respects_ramp_up = (
            change_mw
            <= ramp_up_mw + EPSILON
        )

        respects_ramp_down = (
            change_mw
            >= -ramp_down_mw - EPSILON
        )

        constraints_respected = all([
            respects_minimum,
            respects_maximum,
            respects_ramp_up,
            respects_ramp_down,
        ])

        plant_states.append({
            "plant_id": plant_id,
            "plant_name": plant["plant_name"],

            "region_id": plant.get(
                "location_region_id"
            ),

            "available": bool(
                plant.get("available", True)
            ),

            "previous_output_mw": round(
                previous_output_mw,
                3
            ),

            "output_mw": round(
                output_mw,
                3
            ),

            "change_mw": round(
                change_mw,
                3
            ),

            "minimum_operating_power_mw":
                minimum_mw,

            "maximum_power_mw":
                maximum_mw,

            "max_ramp_up_mw_per_15_min":
                ramp_up_mw,

            "max_ramp_down_mw_per_15_min":
                ramp_down_mw,

            "minimum_reachable_mw": round(
                plant_limits[plant_id][
                    "minimum_reachable_mw"
                ],
                3
            ),

            "maximum_reachable_mw": round(
                plant_limits[plant_id][
                    "maximum_reachable_mw"
                ],
                3
            ),

            "respects_minimum":
                respects_minimum,

            "respects_maximum":
                respects_maximum,

            "respects_ramp_up":
                respects_ramp_up,

            "respects_ramp_down":
                respects_ramp_down,

            "constraints_respected":
                constraints_respected,

            "plant_edges": plant.get(
                "plant_edges",
                []
            ),
        })

    all_constraints_respected = all(
        plant["constraints_respected"]
        for plant in plant_states
    )

    return {
        "nuclear_required_mw": round(
            demand_mw,
            3
        ),

        "previous_production_mw": round(
            previous_total_mw,
            3
        ),

        "production_mw": round(
            production_mw,
            3
        ),

        "minimum_reachable_total_mw": round(
            minimum_reachable_total_mw,
            3
        ),

        "maximum_reachable_total_mw": round(
            maximum_reachable_total_mw,
            3
        ),

        "direction": direction,

        "missing_mw": round(
            missing_mw,
            3
        ),

        "forced_surplus_mw": round(
            forced_surplus_mw,
            3
        ),

        "fully_satisfied": (
            missing_mw <= EPSILON
        ),

        "production_balanced": (
            missing_mw <= EPSILON
            and forced_surplus_mw <= EPSILON
        ),

        "all_constraints_respected":
            all_constraints_respected,

        "plants": plant_states,

        # Cet état sera utilisé pour calculer
        # le prochain quart d'heure.
        "state": next_state,
    }


def simulate_day(
    consumption_data,
    nuclear_dataframe,
    number_of_steps=None
):
    """
    Simule une journée complète ou un nombre limité
    de quarts d'heure.
    """

    timestamps = consumption_data[
        "timestamps"
    ]

    national_consumptions = consumption_data[
        "national_total_consumption_mw"
    ]

    if not hasattr(
        nuclear_dataframe,
        "to_dict"
    ):
        raise TypeError(
            "Le moteur attend une DataFrame "
            "pour les centrales nucléaires"
        )

    plants = nuclear_dataframe.to_dict(
        orient="records"
    )

    if not plants:
        raise ValueError(
            "La DataFrame des centrales est vide"
        )

    if number_of_steps is None:
        steps_to_simulate = len(timestamps)
    else:
        steps_to_simulate = int(
            number_of_steps
        )

    if not 1 <= steps_to_simulate <= len(
        timestamps
    ):
        raise ValueError(
            "Le nombre de pas demandé est invalide"
        )

    current_state = build_initial_state(
        plants
    )

    results = []

    for index in range(steps_to_simulate):
        regional_consumption = (
            get_regional_consumption(
                consumption_data,
                index
            )
        )

        regional_total_mw = sum(
            regional_consumption.values()
        )

        national_total_mw = float(
            national_consumptions[index]
        )

        if abs(
            regional_total_mw
            - national_total_mw
        ) > 1:
            raise ValueError(
                f"Consommation incohérente à "
                f"{timestamps[index]} : "
                f"régions={regional_total_mw} MW, "
                f"national={national_total_mw} MW"
            )

        result = simulate_step(
            plants=plants,
            previous_state=current_state,
            demand_mw=national_total_mw,
        )

        # Le résultat du quart d'heure actuel devient
        # le point de départ du quart d'heure suivant.
        current_state = result.pop(
            "state"
        )

        result["index"] = index

        result["timestamp"] = (
            timestamps[index]
        )

        result["regional_consumption_mw"] = (
            regional_consumption
        )

        result["regional_total_consumption_mw"] = (
            round(
                regional_total_mw,
                3
            )
        )

        results.append(result)

    return {
        "phase": 1,
        "energy_source": "nuclear",
        "step_minutes": 15,

        "steps_count": len(results),

        "complete_day": (
            len(results) == 96
        ),

        "all_demand_satisfied": all(
            step["fully_satisfied"]
            for step in results
        ),

        "all_production_balanced": all(
            step["production_balanced"]
            for step in results
        ),

        "all_constraints_respected": all(
            step["all_constraints_respected"]
            for step in results
        ),

        "total_missing_mw": round(
            sum(
                step["missing_mw"]
                for step in results
            ),
            3
        ),

        "steps": results,
    }