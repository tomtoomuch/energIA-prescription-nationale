import json
from pathlib import Path


DATA_DIRECTORY = Path(__file__).resolve().parent.parent / "data"


FLEET_PATH = (
    DATA_DIRECTORY
    / "parc_nucleaire_prescriptif_france.json"
)


REFERENCE_CONSUMPTION_PATH = (
    DATA_DIRECTORY
    / "energia-journee-reference-consommation.json"
)


TEMPORAL_NUCLEAR_PARAMETERS_PATH = (
    DATA_DIRECTORY
    / "energia-parametres-temporels-nucleaire.json"
)


def load_json(path):


    with Path(path).open(
        mode="r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def load_data(path=FLEET_PATH):


    data = load_json(path)

    if not data.get("plants"):
        raise ValueError("Aucune centrale trouvée")

    if not data.get("regions"):
        raise ValueError("Aucune région trouvée")

    if not data.get("plant_edges"):
        raise ValueError("Aucune liaison trouvée")

    return data


def build_plants_index(data):


    return {
        plant["id"]: plant
        for plant in data.get("plants", [])
    }


def build_regions_index(data):

    return {
        region["id"]: region
        for region in data.get("regions", [])
    }


def build_graph(data):

    graph = {
        plant["id"]: []
        for plant in data.get("plants", [])
    }

    for edge in data.get("plant_edges", []):
        if not edge.get("available", True):
            continue

        from_plant = edge["from"]
        to_plant = edge["to"]

        graph.setdefault(from_plant, []).append({
            "id": edge["id"],
            "from": from_plant,
            "to": to_plant,
            "distance_km": float(
                edge["geodesic_distance_km"]
            ),
            "loss_percent": float(
                edge["estimated_loss_percent"]
            ),
            "max_transfer_mw": float(
                edge["max_transfer_mw"]
            ),
            "available": True,
        })

        if edge.get("bidirectional", False):
            graph.setdefault(to_plant, []).append({
                "id": edge["id"],
                "from": to_plant,
                "to": from_plant,
                "distance_km": float(
                    edge["geodesic_distance_km"]
                ),
                "loss_percent": float(
                    edge["estimated_loss_percent"]
                ),
                "max_transfer_mw": float(
                    edge["max_transfer_mw"]
                ),
                "available": True,
            })

    return graph


def load_reference_consumption(
    path=REFERENCE_CONSUMPTION_PATH
):


    data = load_json(path)

    timestamps = data.get("timestamps", [])

    national_consumptions = data.get(
        "national_total_consumption_mw",
        []
    )

    regions = data.get("regions", [])

    # une journée contient 24 heures × 4 quarts d'heure = 96 pas
    if len(timestamps) != 96:
        raise ValueError(
            "La journée de référence doit contenir "
            "exactement 96 horaires"
        )

    if len(national_consumptions) != 96:
        raise ValueError(
            "La journée de référence doit contenir "
            "exactement 96 consommations nationales"
        )

    if not regions:
        raise ValueError(
            "Aucune consommation régionale trouvée"
        )

    # chaque région doit également posséder une consommation pour chaque quart d'heure
    for region in regions:
        region_id = region.get(
            "id",
            "région inconnue"
        )

        regional_consumptions = region.get(
            "consumption_mw",
            []
        )

        if len(regional_consumptions) != 96:
            raise ValueError(
                f"La région {region_id} "
                "ne contient pas 96 consommations"
            )

    return data


def load_temporal_nuclear_parameters(
    path=TEMPORAL_NUCLEAR_PARAMETERS_PATH
):


    data = load_json(path)

    plants = data.get("plants", [])

    if not plants:
        raise ValueError(
            "Aucun paramètre temporel de centrale trouvé"
        )

    required_fields = {
        "plant_id",
        "initial_output_mw_at_23_45_previous_day",
        "minimum_operating_power_mw",
        "maximum_power_mw",
        "max_ramp_up_mw_per_15_min",
        "max_ramp_down_mw_per_15_min",
    }

    known_plant_ids = set()

    for plant in plants:
        plant_id = plant.get(
            "plant_id",
            "centrale inconnue"
        )

        # vérification de la présence des champs.
        missing_fields = (
            required_fields
            - plant.keys()
        )

        if missing_fields:
            raise ValueError(
                f"Paramètres manquants pour "
                f"{plant_id} : "
                f"{', '.join(sorted(missing_fields))}"
            )

        # deux centrales ne doivent pas utiliser # le même identifiant
        if plant_id in known_plant_ids:
            raise ValueError(
                f"Identifiant de centrale dupliqué : "
                f"{plant_id}"
            )

        known_plant_ids.add(plant_id)

        initial_output = float(
            plant[
                "initial_output_mw_at_23_45_previous_day"
            ]
        )

        minimum_output = float(
            plant["minimum_operating_power_mw"]
        )

        maximum_output = float(
            plant["maximum_power_mw"]
        )

        ramp_up = float(
            plant[
                "max_ramp_up_mw_per_15_min"
            ]
        )

        ramp_down = float(
            plant[
                "max_ramp_down_mw_per_15_min"
            ]
        )

        # le minimum doit être inférieur au maximum
        if minimum_output > maximum_output:
            raise ValueError(
                f"Limites incohérentes pour "
                f"{plant_id} : minimum supérieur "
                "au maximum"
            )

        # la production initiale doit être comprise entre le minimum et le maximum
        if not (
            minimum_output
            <= initial_output
            <= maximum_output
        ):
            raise ValueError(
                f"Production initiale hors limites "
                f"pour {plant_id} : "
                f"{initial_output} MW"
            )

        # Les rampes ne peuvent pas être négatives.
        if ramp_up < 0 or ramp_down < 0:
            raise ValueError(
                f"Rampe négative pour {plant_id}"
            )

    return data


if __name__ == "__main__":
    consumption_data = (
        load_reference_consumption()
    )

    nuclear_parameters = (
        load_temporal_nuclear_parameters()
    )

    print(
        "Nombre de pas de consommation :",
        len(consumption_data["timestamps"])
    )

    print(
        "Nombre de régions :",
        len(consumption_data["regions"])
    )

    print(
        "Nombre de centrales :",
        len(nuclear_parameters["plants"])
    )
