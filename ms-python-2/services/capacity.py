# calcul de la puissance mobilisable pour une centrale


def dispatchable_margin(plant):


    sim = plant["simulation"]

    if not sim["available"]:
        return 0.0

    margin = sim["soft_upper_bound_mw"] - sim["initial_output_mw"]
    return max(0.0, margin)


def ramp_limit(plant):
    # vitesse maximale de montée en puissance (MW / 15 minutes) pour cette centrale
    return plant["simulation"]["max_ramp_up_mw_per_15_min"]


def dispatchable_margins_all(data):
    # pareil que dispatchable_margin, mais pour toutes les centrales à la fois
    return {plant["id"]: dispatchable_margin(plant) for plant in data["plants"]}

def available_capacity(plant):
    # calcule la puissance mobilisable par une centrale pendant une période de 15 minutes


    sim = plant["simulation"]

    if not sim.get("available", False):
        return 0.0

    margin = dispatchable_margin(plant)
    ramp = ramp_limit(plant)

    return max(0.0, min(margin, ramp))


def available_capacities_all(data):
    #
    # Calcule la puissance mobilisable
    # pour toutes les centrales.

    return {
        plant["id"]: available_capacity(plant)
        for plant in data["plants"]
    }


if __name__ == "__main__":
    from graph_loader import load_data

    data = load_data()
    capacities = available_capacities_all(data)

    for plant_id, capacity in capacities.items():
        print(plant_id, capacity)