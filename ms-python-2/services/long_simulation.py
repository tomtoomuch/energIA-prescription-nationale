import argparse
from copy import deepcopy
from time import perf_counter

from services.graph_loader import (
    get_consumption_scenario,
    load_consumption_scenarios,
    load_non_dispatchable_production,
    load_reference_consumption,
)
from services.nuclear_dataframe import (
    build_nuclear_dataframe,
)
from services.temporal_engine import (
    simulate_day,
)


STEPS_PER_DAY = 96


def repeat_values(
    values,
    number_of_days
):
    return list(values) * number_of_days


def build_long_consumption_data(
    consumption_data,
    number_of_days
):
    long_consumption_data = deepcopy(
        consumption_data
    )

    long_consumption_data["timestamps"] = (
        repeat_values(
            consumption_data["timestamps"],
            number_of_days,
        )
    )

    long_consumption_data[
        "national_total_consumption_mw"
    ] = repeat_values(
        consumption_data[
            "national_total_consumption_mw"
        ],
        number_of_days,
    )

    for region in long_consumption_data[
        "regions"
    ]:
        region["consumption_mw"] = (
            repeat_values(
                region["consumption_mw"],
                number_of_days,
            )
        )

    long_consumption_data[
        "metadata"
    ][
        "steps"
    ] = (
        STEPS_PER_DAY
        * number_of_days
    )

    long_consumption_data[
        "metadata"
    ][
        "simulation_days"
    ] = number_of_days

    return long_consumption_data


def build_long_non_dispatchable_data(
    non_dispatchable_data,
    number_of_days
):
    long_production_data = deepcopy(
        non_dispatchable_data
    )

    long_production_data["timestamps"] = (
        repeat_values(
            non_dispatchable_data[
                "timestamps"
            ],
            number_of_days,
        )
    )

    national_production = (
        long_production_data[
            "national_total_production_mw"
        ]
    )

    for source_name in national_production:
        national_production[
            source_name
        ] = repeat_values(
            national_production[
                source_name
            ],
            number_of_days,
        )

    for region in long_production_data[
        "regions"
    ]:
        regional_production = region[
            "production_mw"
        ]

        for source_name in regional_production:
            regional_production[
                source_name
            ] = repeat_values(
                regional_production[
                    source_name
                ],
                number_of_days,
            )

    long_production_data[
        "metadata"
    ][
        "steps"
    ] = (
        STEPS_PER_DAY
        * number_of_days
    )

    long_production_data[
        "metadata"
    ][
        "simulation_days"
    ] = number_of_days

    return long_production_data


def add_day_information(
    simulation
):
    for index, step in enumerate(
        simulation["steps"]
    ):
        day_number = (
            index // STEPS_PER_DAY
        ) + 1

        daily_timestamp = step[
            "timestamp"
        ]

        step["day"] = day_number

        step[
            "daily_timestamp"
        ] = daily_timestamp

        step["timestamp"] = (
            f"jour {day_number} "
            f"{daily_timestamp}"
        )

    return simulation


def simulate_period(
    number_of_days,
    minimum_reserve_mw=5000,
    scenario_id=None,
):
    number_of_days = int(
        number_of_days
    )

    if number_of_days < 1:
        raise ValueError(
            "Le nombre de jours doit être positif"
        )

    consumption_data = (
        load_reference_consumption()
    )

    non_dispatchable_data = (
        load_non_dispatchable_production()
    )

    long_consumption_data = (
        build_long_consumption_data(
            consumption_data,
            number_of_days,
        )
    )

    long_production_data = (
        build_long_non_dispatchable_data(
            non_dispatchable_data,
            number_of_days,
        )
    )

    consumption_events = []

    if scenario_id is not None:
        scenarios_data = (
            load_consumption_scenarios()
        )

        scenario = get_consumption_scenario(
            scenarios_data,
            scenario_id,
        )

        consumption_events = scenario[
            "events"
        ]

    nuclear_dataframe = (
        build_nuclear_dataframe()
    )

    steps_count = (
        STEPS_PER_DAY
        * number_of_days
    )

    start_time = perf_counter()

    simulation = simulate_day(
        consumption_data=long_consumption_data,
        nuclear_dataframe=nuclear_dataframe,
        number_of_steps=steps_count,
        non_dispatchable_data=(
            long_production_data
        ),
        minimum_reserve_mw=(
            minimum_reserve_mw
        ),
        consumption_events=(
            consumption_events
        ),
    )

    duration_seconds = (
        perf_counter()
        - start_time
    )

    add_day_information(
        simulation
    )

    simulation[
        "period_information"
    ] = {
        "number_of_days": number_of_days,
        "steps_count": steps_count,
        "duration_seconds": round(
            duration_seconds,
            3
        ),
        "average_step_duration_ms": round(
            (
                duration_seconds
                / steps_count
            )
            * 1000,
            6
        ),
    }

    return simulation


def display_period_summary(
    simulation
):
    information = simulation[
        "period_information"
    ]

    print()
    print("=== simulation longue ===")
    print(
        "nombre de jours :",
        information[
            "number_of_days"
        ],
    )
    print(
        "nombre de pas :",
        information[
            "steps_count"
        ],
    )
    print(
        "durée totale :",
        information[
            "duration_seconds"
        ],
        "secondes",
    )
    print(
        "durée moyenne par pas :",
        information[
            "average_step_duration_ms"
        ],
        "millisecondes",
    )
    print(
        "puissance totale manquante :",
        simulation[
            "total_missing_mw"
        ],
        "MW",
    )
    print(
        "contraintes respectées :",
        simulation[
            "all_constraints_respected"
        ],
    )


def run_command_line():
    parser = argparse.ArgumentParser(
        description=(
            "Simulation EnergIA "
            "sur plusieurs jours"
        )
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help=(
            "Nombre de jours à simuler"
        ),
    )

    parser.add_argument(
        "--minimum-reserve-mw",
        type=float,
        default=5000,
        help=(
            "Réserve nucléaire minimale "
            "en MW"
        ),
    )

    parser.add_argument(
        "--scenario-id",
        type=str,
        default=None,
        help=(
            "Scénario de consommation "
            "à appliquer chaque jour"
        ),
    )

    arguments = parser.parse_args()

    simulation = simulate_period(
        number_of_days=arguments.days,
        minimum_reserve_mw=(
            arguments.minimum_reserve_mw
        ),
        scenario_id=arguments.scenario_id,
    )

    display_period_summary(
        simulation
    )


if __name__ == "__main__":
    run_command_line()