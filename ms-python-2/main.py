import argparse
import os

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Header,
    Depends,
)

from services.graph_loader import (
    load_data,
    build_graph,
    build_plants_index,
    build_regions_index,
    load_reference_consumption,
    load_non_dispatchable_production,
    load_consumption_scenarios,
    get_consumption_scenario,
)


from services.nuclear_dataframe import (
    build_nuclear_dataframe,
)

from services.apply_consumption_events import (
    apply_consumption_events, 
)

from services.temporal_engine import (
    simulate_day,
)


app = FastAPI(
    title="EnergIA",
    description=(
        "Simulation temporelle du parc électrique "
        "pour les phases 1 et 2"
    ),
    version="2.0.0",
)


SECURITY_TOKEN = os.getenv(
    "SECURITY_TOKEN"
)


def verify_api_key(
    x_api_key: str = Header(
        alias="x-api-key"
    )
):
    if (
        not SECURITY_TOKEN
        or x_api_key != SECURITY_TOKEN
    ):
        raise HTTPException(
            status_code=401,
            detail="Clé API invalide",
        )


def run_phase1(
    number_of_steps=96
):
    # charge les données de la phase 1
    consumption_data = (
        load_reference_consumption()
    )

    fleet_data = load_data()

    graph = build_graph(
        fleet_data
    )

    plants_index = build_plants_index(
        fleet_data
    )

    regions_index = build_regions_index(
        fleet_data
    )

    simulation_parameters = fleet_data[
        "simulation_parameters"
    ]


    nuclear_dataframe = (
        build_nuclear_dataframe()
    )

    return simulate_day(
        consumption_data=consumption_data,
        nuclear_dataframe=nuclear_dataframe,
        number_of_steps=number_of_steps,
        graph=graph,
        plants_index=plants_index,
        regions_index=regions_index,
        simulation_parameters=(
            simulation_parameters
        ),
    )



def run_phase2(
    number_of_steps=96,
    minimum_reserve_mw=5000
):
    # charge les données de la phase 2
    consumption_data = (
        load_reference_consumption()
    )

    non_dispatchable_data = (
        load_non_dispatchable_production()
    )

    nuclear_dataframe = (
        build_nuclear_dataframe()
    )

    return simulate_day(
        consumption_data=consumption_data,
        nuclear_dataframe=nuclear_dataframe,
        number_of_steps=number_of_steps,
        non_dispatchable_data=non_dispatchable_data,
        minimum_reserve_mw=minimum_reserve_mw,
    )

def run_phase3(
    scenario_id,
    number_of_steps=96,
    minimum_reserve_mw=5000,
):
    # Chargement des données de la phase 3
    consumption_data = (
        load_reference_consumption()
    )

    non_dispatchable_data = (
        load_non_dispatchable_production()
    )

    nuclear_dataframe = (
        build_nuclear_dataframe()
    )

    scenarios_data = (
        load_consumption_scenarios()
    )

    scenario = (
        get_consumption_scenario(
            scenarios_data,
            scenario_id,
        )
    )

    events_list = (
        list(scenario.get("events"))
    )

    print("Events list : ", events_list)

    return simulate_day(
        consumption_data=consumption_data,
        nuclear_dataframe=nuclear_dataframe,
        number_of_steps=number_of_steps,
        non_dispatchable_data=non_dispatchable_data,
        minimum_reserve_mw=minimum_reserve_mw,
        apply_consumption_events=events_list
    )

@app.get("/")
def home():
    return {
        "application": "EnergIA",

        "phases": [
            1,
            2,
            3,
        ],

        "documentation": "/docs",

        "phase1_simulation":
            "/phase1/simulate-day",

        "phase2_simulation":
            "/phase2/simulate-day",

        "phase3_simulation":
            "/phase3/simulate-day",

        "fleet":
            "/phase1/plants",

        "consumption":
            "/phase1/consumption",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "EnergIA",
        "phases": [
            1,
            2,
            3
        ],
    }


@app.get(
    "/phase1/plants",
    dependencies=[
        Depends(verify_api_key)
    ],
)
def get_nuclear_plants():
    # affiche les centrales et leurs contraintes
    try:
        nuclear_dataframe = (
            build_nuclear_dataframe()
        )

        plants = nuclear_dataframe.to_dict(
            orient="records"
        )

        return {
            "plants_count": len(
                plants
            ),

            "plants": plants,
        }

    except (
        ValueError,
        FileNotFoundError,
        KeyError,
    ) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@app.get(
    "/phase1/consumption",
    dependencies=[
        Depends(verify_api_key)
    ],
)
def get_consumption():
    # affiche les consommations des 96 quarts d'heure
    try:
        consumption_data = (
            load_reference_consumption()
        )

        steps = []

        timestamps = consumption_data[
            "timestamps"
        ]

        national_consumptions = (
            consumption_data[
                "national_total_consumption_mw"
            ]
        )

        regions = consumption_data[
            "regions"
        ]

        for index, timestamp in enumerate(
            timestamps
        ):
            regional_consumption = {}

            for region in regions:
                region_id = region[
                    "id"
                ]

                consumption_mw = region[
                    "consumption_mw"
                ][index]

                regional_consumption[
                    region_id
                ] = consumption_mw

            steps.append({
                "index": index,

                "timestamp":
                    timestamp,

                "national_consumption_mw":
                    national_consumptions[
                        index
                    ],

                "regional_consumption_mw":
                    regional_consumption,
            })

        return {
            "step_minutes": 15,

            "steps_count": len(
                steps
            ),

            "steps": steps,
        }

    except (
        ValueError,
        FileNotFoundError,
        KeyError,
    ) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@app.get(
    "/phase2/non-dispatchable-production",
    dependencies=[
        Depends(verify_api_key)
    ],
)
def get_non_dispatchable_production():
    # affiche les productions solaire et éolienne
    try:
        production_data = (
            load_non_dispatchable_production()
        )

        timestamps = production_data[
            "timestamps"
        ]

        national_production = (
            production_data[
                "national_total_production_mw"
            ]
        )

        steps = []

        for index, timestamp in enumerate(
            timestamps
        ):
            steps.append({
                "index": index,

                "timestamp":
                    timestamp,

                "solar_production_mw":
                    national_production[
                        "solar"
                    ][index],

                "wind_production_mw":
                    national_production[
                        "wind"
                    ][index],

                "non_dispatchable_production_mw":
                    national_production[
                        "solar_plus_wind"
                    ][index],
            })

        return {
            "step_minutes": 15,

            "steps_count": len(
                steps
            ),

            "steps": steps,
        }

    except (
        ValueError,
        FileNotFoundError,
        KeyError,
    ) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@app.get(
    "/phase1/simulate-day",
    dependencies=[
        Depends(verify_api_key)
    ],
)
def simulate_phase1_api(
    number_of_steps: int = Query(
        default=96,
        ge=1,
        le=96,
        description=(
            "Nombre de quarts d'heure "
            "à simuler"
        ),
    )
):
    # lance la simulation de la phase 1
    try:
        return run_phase1(
            number_of_steps=number_of_steps
        )

    except (
        ValueError,
        FileNotFoundError,
        KeyError,
        TypeError,
    ) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@app.get(
    "/phase2/simulate-day",
    dependencies=[
        Depends(verify_api_key)
    ],
)
def simulate_phase2_api(
    number_of_steps: int = Query(
        default=96,
        ge=1,
        le=96,
        description=(
            "Nombre de quarts d'heure "
            "à simuler"
        ),
    ),

    minimum_reserve_mw: float = Query(
        default=5000,
        ge=0,
        description=(
            "Réserve nucléaire minimale "
            "en MW"
        ),
    ),
):
    # lance la simulation de la phase 2
    try:
        return run_phase2(
            number_of_steps=number_of_steps,

            minimum_reserve_mw=(
                minimum_reserve_mw
            ),
        )

    except (
        ValueError,
        FileNotFoundError,
        KeyError,
        TypeError,
    ) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

@app.get(
    "/phase3/simulate-day",
    dependencies=[
        Depends(verify_api_key)
    ],
)
def simulate_phase3_api(
    number_of_steps: int = Query(
        default=96,
        ge=1,
        le=96,
        description=(
            "Nombre de quarts d'heure "
            "à simuler"
        ),
    ),

    minimum_reserve_mw: float = Query(
        default=5000,
        ge=0,
        description=(
            "Réserve nucléaire minimale "
            "en MW"
        ),
    ),

    scenario_id: str = Query(
        default="evening_peak_occitanie",
        description=(
            "Intitulé du scénario de "
            "demande exceptionnelle à appliquer"
        ),
    ),
):
    # lance la simulation de la phase 3
    try:
        return run_phase3(
            scenario_id,
            number_of_steps=number_of_steps,
            minimum_reserve_mw=minimum_reserve_mw,
        
        )

    except (
        ValueError,
        FileNotFoundError,
        KeyError,
        TypeError,
    ) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error



def display_simulation(
    simulation
):
    # affiche la simulation dans le terminal
    print()
    print(
        f"=== EnergIA phase "
        f"{simulation['phase']} ==="
    )
    print()

    for step in simulation["steps"]:
        if simulation["phase"] == 2:
            print(
                f"{step['timestamp']} | "
                f"consommation="
                f"{step['total_consumption_mw']:.0f} MW | "
                f"solaire="
                f"{step['solar_production_mw']:.0f} MW | "
                f"éolien="
                f"{step['wind_production_mw']:.0f} MW | "
                f"demande résiduelle="
                f"{step['residual_demand_mw']:.0f} MW | "
                f"nucléaire="
                f"{step['production_mw']:.0f} MW"
            )

            print(
                f"  réserve="
                f"{step['nuclear_reserve_mw']:.0f} MW | "
                f"réserve minimale="
                f"{step['minimum_reserve_mw']:.0f} MW | "
                f"réserve suffisante="
                f"{step['reserve_sufficient']} | "
                f"situation="
                f"{step['situation']}"
            )

        else:
            print(
                f"{step['timestamp']} | "
                f"demande="
                f"{step['nuclear_required_mw']:.0f} MW | "
                f"production="
                f"{step['production_mw']:.0f} MW"
            )

        print(
            f"  manquant="
            f"{step['missing_mw']:.0f} MW | "
            f"surplus="
            f"{step['forced_surplus_mw']:.0f} MW | "
            f"direction="
            f"{step['direction']}"
        )

        print(
            "  consommation régionale"
        )

        if simulation["phase"] == 3:
            for (
                region_id,
                modified_consumption_mw
            ) in step[
                "regional_consumption_mw"
            ].items():
                print(
                    f"    - {region_id}: "
                    f"{modified_consumption_mw:.0f} MW"
                )
        else:
            for (
                region_id,
                consumption_mw
            ) in step[
                "regional_consumption_mw"
            ].items():
                print(
                    f"    - {region_id}: "
                    f"{consumption_mw:.0f} MW"
                )

        print(
            "  répartition des centrales"
        )

        for plant in step["plants"]:
            print(
                f"    - "
                f"{plant['plant_name']} "
                f"({plant['plant_id']}): "
                f"{plant['previous_output_mw']:.1f} "
                f"-> "
                f"{plant['output_mw']:.1f} MW "
                f"(variation "
                f"{plant['change_mw']:+.1f} MW)"
            )

        print()

    print("=== résumé ===")

    print(
        f"nombre de pas : "
        f"{simulation['steps_count']}"
    )

    print(
        f"journée complète : "
        f"{simulation['complete_day']}"
    )

    print(
        f"demande toujours satisfaite : "
        f"{simulation['all_demand_satisfied']}"
    )

    print(
        f"contraintes toujours respectées : "
        f"{simulation['all_constraints_respected']}"
    )

    print(
        f"production toujours équilibrée : "
        f"{simulation['all_production_balanced']}"
    )

    print(
        f"puissance totale manquante : "
        f"{simulation['total_missing_mw']:.1f} MW"
    )

    if simulation["phase"] == 2:
        print(
            f"réserve toujours suffisante : "
            f"{simulation['reserve_always_sufficient']}"
        )

        print(
            f"nombre de situations dégradées : "
            f"{simulation['degraded_steps_count']}"
        )


def run_command_line():
    parser = argparse.ArgumentParser(
        description=(
            "Simulation temporelle EnergIA"
        )
    )

    parser.add_argument(
        "--phase",
        type=int,
        default=1,
        choices=[
            1,
            2,
            3
        ],
        help=(
            "Phase à simuler"
        ),
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=96,
        choices=range(
            1,
            97
        ),
        metavar="[1-96]",
        help=(
            "Nombre de quarts d'heure "
            "à simuler"
        ),
    )

    parser.add_argument(
        "--minimum-reserve-mw",
        type=float,
        default=5000,
        help=(
            "Réserve nucléaire minimale "
            "en MW pour la phase 2"
        ),
    )

    parser.add_argument(
        "--scenario-id",
        type=str,
        default="evening_peak_occitanie",
        help=(
            "Chaîne de caractères qui "
            "identifie le scénario"
        ),
    )

    arguments = parser.parse_args()

    if arguments.phase == 2:
        simulation = run_phase2(
            number_of_steps=(
                arguments.steps
            ),

            minimum_reserve_mw=(
                arguments.minimum_reserve_mw
            ),
        )

    elif arguments.phase == 3:
        simulation = run_phase3(
            number_of_steps=(
                arguments.steps
            ),
            minimum_reserve_mw=(
                arguments.minimum_reserve_mw
            ),
            scenario_id=(
                arguments.scenario_id or "evening_peak_occitanie"
            )
        )
    else:
        simulation = run_phase1(
            number_of_steps=(
                arguments.steps
            )
        )

    display_simulation(
        simulation
    )


if __name__ == "__main__":
    run_command_line()



