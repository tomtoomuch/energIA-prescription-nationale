

EPSILON = 0.000001


def build_initial_state(plants):
    #l'état de 23 h 45 qui précède la journée simulée

    # les centrales une par une,a chaque tour plant représente une centrale
    state = {}
    for plant in plants:
        plant_id = plant["plant_id"]
        output = float(plant["initial_output_mw_at_23_45_previous_day"])
        minimum = float(plant["minimum_operating_power_mw"])
        maximum = float(plant["maximum_power_mw"])
        if not minimum <= output <= maximum:
         # minimum ≤ production initiale ≤ maximum   520 ≤ 1493 ≤ 2620
            raise ValueError(f"Production initiale de {plant_id} hors limites: {output} MW")
        state[plant_id] = output
    return state


def available_flexibility(plant, current_output, direction):
    #retourne les MW réellement modifiables pendant un pas de 15 minutes
    if not plant.get("available", True):
        return 0.0
    # calculons d’abord la place disponible avant la puissance maximale
    if direction == "up":
        margin = float(plant["maximum_power_mw"]) - current_output
        ramp = float(plant["max_ramp_up_mw_per_15_min"])
    else:
        margin = current_output - float(plant["minimum_operating_power_mw"])
        ramp = float(plant["max_ramp_down_mw_per_15_min"])
    return max(0.0, min(margin, ramp))


def simulate_step(plants, previous_state, demand_mw):
    # calcule un état à partir de l'état du quart d'heure précédent
    demand_mw = float(demand_mw)
    if demand_mw < 0:
        raise ValueError("La consommation ne peut pas être négative")

    previous_total = sum(previous_state.values())
    difference = demand_mw - previous_total

    direction = "up" if difference >= 0 else "down"
    flexibilities = {
        plant["plant_id"]: available_flexibility(
            plant, previous_state[plant["plant_id"]], direction
        )
        for plant in plants
    }
    total_flexibility = sum(flexibilities.values())
    possible_change = min(abs(difference), total_flexibility)
    next_state = previous_state.copy()

    if total_flexibility > EPSILON:
        for plant in plants:
            plant_id = plant["plant_id"]
            share = possible_change * flexibilities[plant_id] / total_flexibility
            next_state[plant_id] += share if direction == "up" else -share

    production_mw = sum(next_state.values())
    missing_mw = max(0.0, demand_mw - production_mw)
    forced_surplus_mw = max(0.0, production_mw - demand_mw)
    plant_states = [
        {
            "plant_id": plant["plant_id"],
            "output_mw": round(next_state[plant["plant_id"]], 3),
            "change_mw": round(
                next_state[plant["plant_id"]] - previous_state[plant["plant_id"]], 3
            ),
        }
        for plant in plants
    ]
    return {
        "demand_mw": round(demand_mw, 3),
        "production_mw": round(production_mw, 3),
        "missing_mw": round(missing_mw, 3),
        "forced_surplus_mw": round(forced_surplus_mw, 3),
        "fully_satisfied": missing_mw <= EPSILON,
        "plants": plant_states,
        "state": next_state,
    }


def simulate_day(consumption_data, temporal_parameters, number_of_steps=None):
    # enchaîne les états de la journée, jusqu'à 96 quarts d'heure
    timestamps = consumption_data["timestamps"]
    consumptions = consumption_data["national_total_consumption_mw"]
    plants = temporal_parameters["plants"]
    steps_to_simulate = len(timestamps) if number_of_steps is None else number_of_steps
    if not 1 <= steps_to_simulate <= len(timestamps):
        raise ValueError("Le nombre de pas demandé est invalide")

    current_state = build_initial_state(plants)
    results = []
    for index in range(steps_to_simulate):
        result = simulate_step(plants, current_state, consumptions[index])
        current_state = result.pop("state")
        result["index"] = index
        result["timestamp"] = timestamps[index]
        results.append(result)

    return {
        "phase": 1,
        "step_minutes": 15,
        "steps_count": len(results),
        "complete_day": len(results) == 96,
        "all_demand_satisfied": all(step["fully_satisfied"] for step in results),
        "steps": results,
    }
