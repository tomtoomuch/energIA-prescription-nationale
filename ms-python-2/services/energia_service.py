import json

from services.graph_loader import (
    build_graph,
    build_plants_index,
    build_regions_index,
    load_data,
    load_non_dispatchable_production,
    load_reference_consumption,
)
from services.nuclear_dataframe import (
    build_nuclear_dataframe,
)
from services.temporal_engine import (
    simulate_day,
)


def _normalize_identifier(value, field_name):

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} doit être une chaîne"
        )

    normalized_value = value.strip().casefold()

    if not normalized_value:
        raise ValueError(
            f"{field_name} est obligatoire"
        )

    return normalized_value


def _normalize_timestamp(timestamp):

    if not isinstance(timestamp, str):
        raise ValueError(
            "L'horaire doit être une chaîne"
        )

    normalized_timestamp = timestamp.strip()

    if not normalized_timestamp:
        raise ValueError(
            "L'horaire est obligatoire"
        )

    return normalized_timestamp


def _ensure_json_serializable(value):
    # vérifie que le résultat peut être converti en JSON
    try:
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Les données EnergIA ne sont pas "
            "sérialisables en JSON"
        ) from error

    return value


def list_regions():
    # retourne la liste des régions
    data = load_data()
    regions = data.get("regions", [])

    if not regions:
        raise ValueError(
            "Aucune région EnergIA trouvée"
        )

    result_regions = []
    known_region_ids = set()

    for region in regions:
        region_id = region.get("id")
        region_name = region.get("name")

        if not region_id:
            raise ValueError(
                "Une région ne possède pas "
                "d'identifiant"
            )

        if not region_name:
            raise ValueError(
                f"La région {region_id} "
                "ne possède pas de nom"
            )

        if region_id in known_region_ids:
            raise ValueError(
                "Identifiant de région dupliqué : "
                f"{region_id}"
            )

        known_region_ids.add(region_id)

        result_regions.append({
            "id": region_id,
            "name": region_name,
        })

    return _ensure_json_serializable({
        "count": len(result_regions),
        "regions": result_regions,
    })


def list_plants():
    # retourne la liste des centrales nucléaires."""
    nuclear_dataframe = build_nuclear_dataframe()

    columns = [
        "plant_id",
        "plant_name",
        "location_region_id",
        "location_region_name",
        "available",
        "initial_output_mw_at_23_45_previous_day",
        "minimum_operating_power_mw",
        "maximum_power_mw",
        "max_ramp_up_mw_per_15_min",
        "max_ramp_down_mw_per_15_min",
    ]

    missing_columns = [
        column
        for column in columns
        if column not in nuclear_dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Colonnes manquantes dans les données "
            "des centrales : "
            + ", ".join(missing_columns)
        )

    plants_json = nuclear_dataframe[
        columns
    ].to_json(
        orient="records",
        force_ascii=False,
    )

    plants = json.loads(plants_json)

    return _ensure_json_serializable({
        "count": len(plants),
        "plants": plants,
    })


def get_plant_status(plant_id):
    # retourne la configuration initiale d'une centrale.

   # cette fonction ne lance pas de simulation.

    normalized_plant_id = _normalize_identifier(
        plant_id,
        "L'identifiant de la centrale",
    )

    plants = list_plants()["plants"]

    for plant in plants:
        current_plant_id = plant.get("plant_id")

        if (
            isinstance(current_plant_id, str)
            and current_plant_id.casefold()
            == normalized_plant_id
        ):
            return _ensure_json_serializable(
                plant
            )

    raise ValueError(
        f"Centrale inconnue : {plant_id}"
    )


def get_region_consumption(
    region_id,
    timestamp,
):
    # retourne la consommation de référence d'une région.

    # ex
    #     get_region_consumption(
    #         "occitanie",
    #         "18:00",
    #     )

    normalized_region_id = _normalize_identifier(
        region_id,
        "L'identifiant de la région",
    )

    normalized_timestamp = _normalize_timestamp(
        timestamp
    )

    data = load_reference_consumption()
    timestamps = data.get("timestamps", [])

    if normalized_timestamp not in timestamps:
        raise ValueError(
            f"Horaire inconnu : {timestamp}"
        )

    timestamp_index = timestamps.index(
        normalized_timestamp
    )

    for region in data.get("regions", []):
        current_region_id = region.get("id")

        if (
            isinstance(current_region_id, str)
            and current_region_id.casefold()
            == normalized_region_id
        ):
            consumptions = region.get(
                "consumption_mw",
                [],
            )

            if timestamp_index >= len(consumptions):
                raise ValueError(
                    "Consommation manquante pour "
                    f"{current_region_id} à "
                    f"{normalized_timestamp}"
                )

            return _ensure_json_serializable({
                "region_id": current_region_id,
                "region_name": region.get("name"),
                "timestamp": normalized_timestamp,
                "consumption_mw": (
                    consumptions[timestamp_index]
                ),
            })

    raise ValueError(
        f"Région inconnue : {region_id}"
    )


def get_simulation_results(
    number_of_steps=96,
    minimum_reserve_mw=5000,
):

    # lance la simulation complète
    # La simulation contient
    # la consommation
    # la production nucléaire
    # la production solaire et éolienne
    # l'état calculé des centrales
    # la réserve nucléaire
    # les résultats régionaux
    #  les contraintes et les éventuels manques

    if not isinstance(number_of_steps, int):
        raise ValueError(
            "Le nombre d'étapes doit être un entier"
        )

    if not 1 <= number_of_steps <= 96:
        raise ValueError(
            "Le nombre d'étapes doit être compris "
            "entre 1 et 96"
        )

    if not isinstance(
        minimum_reserve_mw,
        (int, float),
    ):
        raise ValueError(
            "La réserve minimale doit être un nombre"
        )

    if minimum_reserve_mw < 0:
        raise ValueError(
            "La réserve minimale ne peut pas "
            "être négative"
        )

    fleet_data = load_data()

    result = simulate_day(
        consumption_data=(
            load_reference_consumption()
        ),
        nuclear_dataframe=(
            build_nuclear_dataframe()
        ),
        number_of_steps=number_of_steps,
        non_dispatchable_data=(
            load_non_dispatchable_production()
        ),
        minimum_reserve_mw=(
            minimum_reserve_mw
        ),
        graph=build_graph(fleet_data),
        plants_index=build_plants_index(
            fleet_data
        ),
        regions_index=build_regions_index(
            fleet_data
        ),
        simulation_parameters=fleet_data[
            "simulation_parameters"
        ],
    )

    return _ensure_json_serializable(result)


def get_simulation_step(timestamp):
    # retourne le résultat calculé à une heure précise
    normalized_timestamp = _normalize_timestamp(
        timestamp
    )

    simulation = get_simulation_results()

    for step in simulation.get("steps", []):
        if (
            step.get("timestamp")
            == normalized_timestamp
        ):
            return _ensure_json_serializable(
                step
            )

    raise ValueError(
        f"Horaire inconnu : {timestamp}"
    )


def get_plant_simulated_status(
    plant_id,
    timestamp,
):
  # retourne l'état calculé d'une centrale à une heure précise

    normalized_plant_id = _normalize_identifier(
        plant_id,
        "L'identifiant de la centrale",
    )

    step = get_simulation_step(timestamp)

    for plant in step.get("plants", []):
        current_plant_id = plant.get("plant_id")

        if (
            isinstance(current_plant_id, str)
            and current_plant_id.casefold()
            == normalized_plant_id
        ):
            return _ensure_json_serializable({
                "timestamp": step["timestamp"],
                **plant,
            })

    raise ValueError(
        f"Centrale inconnue : {plant_id}"
    )


def get_region_energy_status(
    region_id,
    timestamp,
):
    # retourne la situation calculée d'une région à une heure précise
    normalized_region_id = _normalize_identifier(
        region_id,
        "L'identifiant de la région",
    )

    step = get_simulation_step(timestamp)

    region = next(
        (
            current_region
            for current_region
            in list_regions()["regions"]
            if current_region["id"].casefold()
            == normalized_region_id
        ),
        None,
    )

    if region is None:
        raise ValueError(
            f"Région inconnue : {region_id}"
        )

    regional_consumptions = step.get(
        "regional_consumption_mw",
        {},
    )

    regional_allocations = step.get(
        "regional_allocations",
        {},
    )

    regional_plants = [
        plant
        for plant in step.get("plants", [])
        if plant.get("region_id")
        == region["id"]
    ]

    return _ensure_json_serializable({
        "region_id": region["id"],
        "region_name": region["name"],
        "timestamp": step["timestamp"],
        "consumption_mw": (
            regional_consumptions.get(
                region["id"]
            )
        ),
        "regional_allocation": (
            regional_allocations.get(
                region["id"],
                {},
            )
        ),
        "plants": regional_plants,
        "national_situation": step.get(
            "situation"
        ),
    })