import json
from pathlib import Path


DATA_DIRECTORY = (
    Path(__file__).resolve().parent.parent
    / "data"
)


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


NON_DISPATCHABLE_PRODUCTION_PATH = (
    DATA_DIRECTORY
    / "energia-production-non-pilotable.json"
)

CONSUMPTION_SCENARIOS_PATH = (
    DATA_DIRECTORY
    / "energia-scenarios-phase3-exemples.json"
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
        raise ValueError(
            "Aucune centrale trouvée"
        )

    if not data.get("regions"):
        raise ValueError(
            "Aucune région trouvée"
        )

    if not data.get("plant_edges"):
        raise ValueError(
            "Aucune liaison trouvée"
        )

    return data


def build_plants_index(data):
    return {
        plant["id"]: plant
        for plant in data.get(
            "plants",
            []
        )
    }


def build_regions_index(data):
    return {
        region["id"]: region
        for region in data.get(
            "regions",
            []
        )
    }


def build_graph(data):
    graph = {
        plant["id"]: []
        for plant in data.get(
            "plants",
            []
        )
    }

    for edge in data.get(
        "plant_edges",
        []
    ):
        if not edge.get(
            "available",
            True
        ):
            continue

        from_plant = edge["from"]
        to_plant = edge["to"]

        graph.setdefault(
            from_plant,
            []
        ).append({
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

        if edge.get(
            "bidirectional",
            False
        ):
            graph.setdefault(
                to_plant,
                []
            ).append({
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

    timestamps = data.get(
        "timestamps",
        []
    )

    national_consumptions = data.get(
        "national_total_consumption_mw",
        []
    )

    regions = data.get(
        "regions",
        []
    )

    # une journée contient 96 quarts d'heure
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

    for consumption_mw in national_consumptions:
        if float(consumption_mw) < 0:
            raise ValueError(
                "Une consommation nationale "
                "ne peut pas être négative"
            )

    # chaque région doit posséder 96 consommations
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

        for consumption_mw in regional_consumptions:
            if float(consumption_mw) < 0:
                raise ValueError(
                    f"La région {region_id} contient "
                    "une consommation négative"
                )

    return data


def load_temporal_nuclear_parameters(
    path=TEMPORAL_NUCLEAR_PARAMETERS_PATH
):
    data = load_json(path)

    plants = data.get(
        "plants",
        []
    )

    if not plants:
        raise ValueError(
            "Aucun paramètre temporel "
            "de centrale trouvé"
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

        # vérifie la présence des champs obligatoires
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

        # vérifie que chaque identifiant est unique
        if plant_id in known_plant_ids:
            raise ValueError(
                "Identifiant de centrale dupliqué : "
                f"{plant_id}"
            )

        known_plant_ids.add(
            plant_id
        )

        initial_output_mw = float(
            plant[
                "initial_output_mw_at_23_45_previous_day"
            ]
        )

        minimum_output_mw = float(
            plant[
                "minimum_operating_power_mw"
            ]
        )

        maximum_output_mw = float(
            plant[
                "maximum_power_mw"
            ]
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

        # vérifie la cohérence des limites
        if minimum_output_mw > maximum_output_mw:
            raise ValueError(
                f"Limites incohérentes pour "
                f"{plant_id} : minimum supérieur "
                "au maximum"
            )

        # vérifie la production initiale
        if not (
            minimum_output_mw
            <= initial_output_mw
            <= maximum_output_mw
        ):
            raise ValueError(
                f"Production initiale hors limites "
                f"pour {plant_id} : "
                f"{initial_output_mw} MW"
            )

        # vérifie que les rampes sont positives
        if (
            ramp_up_mw < 0
            or ramp_down_mw < 0
        ):
            raise ValueError(
                f"Rampe négative pour {plant_id}"
            )

    return data


def load_non_dispatchable_production(
    path=NON_DISPATCHABLE_PRODUCTION_PATH
):
    data = load_json(path)

    timestamps = data.get(
        "timestamps",
        []
    )

    regions = data.get(
        "regions",
        []
    )

    national_production = data.get(
        "national_total_production_mw",
        {}
    )



    # vérifie le nombre de quarts d'heure
    if len(timestamps) != 96:
        raise ValueError(
            "La production non pilotable doit "
            "contenir exactement 96 horaires"
        )

    if not regions:
        raise ValueError(
            "Aucune production non pilotable "
            "régionale trouvée"
        )

    required_sources = {
        "solar",
        "wind",
        "solar_plus_wind",
    }

    missing_sources = (
        required_sources
        - national_production.keys()
    )

    if missing_sources:
        raise ValueError(
            "Productions nationales manquantes : "
            f"{', '.join(sorted(missing_sources))}"
        )
    # print(regions)

    # vérifie les séries nationales
    for source in required_sources:
        production_values = (
            national_production[source]
        )

        if len(production_values) != 96:
            raise ValueError(
                f"La production nationale {source} "
                "ne contient pas 96 valeurs"
            )

        for production_mw in production_values:
            if float(production_mw) < 0:
                raise ValueError(
                    f"La production nationale {source} "
                    "contient une valeur négative"
                )

    known_region_ids = set()

    # vérifie les séries régionales
    for region in regions:
        region_id = region.get(
            "id"
        )

        if not region_id:
            raise ValueError(
                "Une région de production "
                "ne possède pas d'identifiant"
            )

        if region_id in known_region_ids:
            raise ValueError(
                "Identifiant de région dupliqué : "
                f"{region_id}"
            )

        known_region_ids.add(
            region_id
        )

        regional_production = region.get(
            "production_mw",
            {}
        )

        for source in (
            "solar",
            "wind"
        ):
            production_values = (
                regional_production.get(
                    source,
                    []
                )
            )

            if len(production_values) != 96:
                raise ValueError(
                    f"La région {region_id} "
                    f"ne contient pas 96 valeurs "
                    f"pour {source}"
                )

            for production_mw in production_values:
                if float(production_mw) < 0:
                    raise ValueError(
                        f"La région {region_id} "
                        f"contient une production "
                        f"{source} négative"
                    )

    return data


def validate_phase2_compatibility(
    consumption_data,
    non_dispatchable_data
):
    consumption_timestamps = (
        consumption_data.get(
            "timestamps",
            []
        )
    )

    production_timestamps = (
        non_dispatchable_data.get(
            "timestamps",
            []
        )
    )

    # les horaires doivent correspondre exactement
    if (
        consumption_timestamps
        != production_timestamps
    ):
        raise ValueError(
            "Les horaires de consommation et de "
            "production non pilotable "
            "ne correspondent pas"
        )

    consumption_region_ids = {
        region["id"]
        for region in consumption_data.get(
            "regions",
            []
        )
    }

    production_region_ids = {
        region["id"]
        for region in non_dispatchable_data.get(
            "regions",
            []
        )
    }

    # les deux fichiers doivent contenir les mêmes régions
    if (
        consumption_region_ids
        != production_region_ids
    ):
        missing_production_regions = (
            consumption_region_ids
            - production_region_ids
        )

        missing_consumption_regions = (
            production_region_ids
            - consumption_region_ids
        )

        details = []

        if missing_production_regions:
            details.append(
                "production manquante pour "
                + ", ".join(
                    sorted(
                        missing_production_regions
                    )
                )
            )

        if missing_consumption_regions:
            details.append(
                "consommation manquante pour "
                + ", ".join(
                    sorted(
                        missing_consumption_regions
                    )
                )
            )

        raise ValueError(
            "Régions incompatibles entre les fichiers : "
            + " ; ".join(details)
        )

    return True




# --------Start Phase3-----

def validate_consumption_event(
    event,
    known_region_ids,
    known_timestamps
):
    required_fields = {
        "type",
        "region_id",
        "start",
        "end",
    }

    missing_fields = (
        required_fields
        - event.keys()
    )

    if missing_fields:
        raise ValueError(
            "champs manquants dans un événement "
            f"{', '.join(sorted(missing_fields))}"
        )

    if event["type"] != "consumption_delta":
        raise ValueError(
            "type d'événement inconnu "
            f"{event['type']}"
        )

    region_id = event["region_id"]

    if region_id not in known_region_ids:
        raise ValueError(
            "région inconnue dans un événement  "
            f"{region_id}"
        )

    start = event["start"]
    end = event["end"]

    valid_end_timestamps = (
        list(known_timestamps)
        + ["24:00"]
    )

    if start not in known_timestamps:
        raise ValueError(
            "horaire de début invalide "
            f"{start}"
        )

    if end not in valid_end_timestamps:
        raise ValueError(
            "horaire de fin invalide "
            f"{end}"
        )

    if start >= end:
        raise ValueError(
            "l'horaire de début doit être "
            "antérieur à l'horaire de fin"
        )

    has_delta_mw = (
        "delta_mw" in event
    )

    has_delta_percent = (
        "delta_percent" in event
    )

    if (
        has_delta_mw
        == has_delta_percent
    ):
        raise ValueError(
            "Un événement doit contenir "
            "delta_mw ou delta_percent"
        )

    if has_delta_mw:
        float(
            event["delta_mw"]
        )

    if has_delta_percent:
        float(
            event["delta_percent"]
        )

    return True


def load_consumption_scenarios(
    path=CONSUMPTION_SCENARIOS_PATH
):
    data = load_json(path)

    scenarios = data.get(
        "scenarios",
        []
    )

    if not scenarios:
        raise ValueError(
            "Aucun scénario de consommation trouvé"
        )

    consumption_data = (
        load_reference_consumption()
    )

    known_region_ids = {
        region["id"]
        for region in consumption_data[
            "regions"
        ]
    }

    known_timestamps = (
        consumption_data[
            "timestamps"
        ]
    )

    known_scenario_ids = set()

    for scenario in scenarios:
        scenario_id = scenario.get(
            "id"
        )

        if not scenario_id:
            raise ValueError(
                "Un scénario ne possède pas "
                "d'identifiant"
            )

        if scenario_id in known_scenario_ids:
            raise ValueError(
                "Identifiant de scénario dupliqué : "
                f"{scenario_id}"
            )

        known_scenario_ids.add(
            scenario_id
        )

        events = scenario.get(
            "events",
            []
        )

        if not events:
            raise ValueError(
                f"Le scénario {scenario_id} "
                "ne contient aucun événement"
            )

        for event in events:
            validate_consumption_event(
                event=event,
                known_region_ids=known_region_ids,
                known_timestamps=known_timestamps,
            )

    return data


def get_consumption_scenario(
    scenarios_data,
    scenario_id
):
    for scenario in scenarios_data.get(
        "scenarios",
        []
    ):
        if scenario["id"] == scenario_id:
            return scenario

    raise ValueError(
        "Scénario inconnu : "
        f"{scenario_id}"
    )








# ----------End Phase 3------

if __name__ == "__main__":
    consumption_data = (
        load_reference_consumption()
    )

    nuclear_parameters = (
        load_temporal_nuclear_parameters()
    )

    non_dispatchable_data = (
        load_non_dispatchable_production()
    )

    validate_phase2_compatibility(
        consumption_data,
        non_dispatchable_data
    )

    # ajoute ton code ici

    timestamps = consumption_data[
        "timestamps"
    ]

    national_consumptions = consumption_data[
        "national_total_consumption_mw"
    ]

    national_production = non_dispatchable_data[
        "national_total_production_mw"
    ]

    solar_productions = national_production[
        "solar"
    ]

    wind_productions = national_production[
        "wind"
    ]

    non_dispatchable_productions = (
        national_production[
            "solar_plus_wind"
        ]
    )

    print("------phase 2------")
    print()

    for index, timestamp in enumerate(
        timestamps
    ):
        total_consumption_mw = float(
            national_consumptions[index]
        )

        solar_production_mw = float(
            solar_productions[index]
        )

        wind_production_mw = float(
            wind_productions[index]
        )

        non_dispatchable_production_mw = float(
            non_dispatchable_productions[index]
        )

        residual_demand_mw = max(
            0.0,
            total_consumption_mw
            - non_dispatchable_production_mw
        )

        print(
            f"{timestamp} | "
            f"consommation="
            f"{total_consumption_mw:.0f} MW | "
            f"solaire="
            f"{solar_production_mw:.0f} MW | "
            f"éolien="
            f"{wind_production_mw:.0f} MW | "
            f"non pilotable="
            f"{non_dispatchable_production_mw:.0f} MW | "
            f"demande résiduelle="
            f"{residual_demand_mw:.0f} MW"
        )

        print("------phase 3------")
        print()