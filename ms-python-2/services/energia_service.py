from services.graph_loader import (
    load_data,
    load_reference_consumption,
)

from services.nuclear_dataframe import (
    build_nuclear_dataframe,
)


def list_regions():
    data = load_data()
    regions = data["regions"]

    return {
        "count": len(regions),
        "regions": [
            {
                "id": region["id"],
                "name": region["name"],
            }
            for region in regions
        ],
    }


def list_plants():
    nuclear_dataframe = (
        build_nuclear_dataframe()
    )

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

    plants = nuclear_dataframe[
        columns
    ].to_dict(
        orient="records"
    )

    return {
        "count": len(plants),
        "plants": plants,
    }


def get_plant_status(plant_id):
    if not isinstance(plant_id, str):
        raise ValueError(
            "L'identifiant de la centrale "
            "doit être une chaîne"
        )

    normalized_plant_id = (
        plant_id.strip().lower()
    )

    if not normalized_plant_id:
        raise ValueError(
            "L'identifiant de la centrale "
            "est obligatoire"
        )

    plants = list_plants()["plants"]

    for plant in plants:
        if (
            plant["plant_id"].lower()
            == normalized_plant_id
        ):
            return plant

    raise ValueError(
        f"Centrale inconnue : {plant_id}"
    )


def get_region_consumption(
    region_id,
    timestamp,
):
    if not isinstance(region_id, str):
        raise ValueError(
            "L'identifiant de la région "
            "doit être une chaîne"
        )

    if not isinstance(timestamp, str):
        raise ValueError(
            "L'horaire doit être une chaîne"
        )

    normalized_region_id = (
        region_id.strip().lower()
    )

    normalized_timestamp = (
        timestamp.strip()
    )

    data = load_reference_consumption()
    timestamps = data["timestamps"]

    if normalized_timestamp not in timestamps:
        raise ValueError(
            f"Horaire inconnu : {timestamp}"
        )

    timestamp_index = timestamps.index(
        normalized_timestamp
    )

    for region in data["regions"]:
        if (
            region["id"].lower()
            == normalized_region_id
        ):
            return {
                "region_id": region["id"],
                "region_name": region["name"],
                "timestamp":
                    normalized_timestamp,
                "consumption_mw":
                    region["consumption_mw"][
                        timestamp_index
                    ],
            }

    raise ValueError(
        f"Région inconnue : {region_id}"
    )



list_regions()