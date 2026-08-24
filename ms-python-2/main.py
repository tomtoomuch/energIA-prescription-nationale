import argparse

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
)

from services.graph_loader import (
    load_reference_consumption,
)

from services.nuclear_dataframe import (
    build_nuclear_dataframe,
)

from services.temporal_engine import (
    simulate_day,
)


app = FastAPI(
    title="EnergIA",
    description=(
        "Simulation temporelle du parc nucléaire pour la phase 1"
    ),
    version="1.0.0",
)


def run_phase1(number_of_steps=96):
    # les données et lance la simulation
    consumption_data = (
        load_reference_consumption()
    )

    nuclear_dataframe = (
        build_nuclear_dataframe()
    )

    return simulate_day(
        consumption_data=consumption_data,
        nuclear_dataframe=nuclear_dataframe,
        number_of_steps=number_of_steps,
    )


@app.get("/")
def home():
    return {
        "application": "EnergIA",
        "phase": 1,
        "documentation": "/docs",
        "simulation": "/phase1/simulate-day",
        "fleet": "/phase1/plants",
        "consumption": "/phase1/consumption",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "EnergIA Phase 1",
    }


@app.get("/phase1/plants")
def get_nuclear_plants():
    # ffiche toutes les centrales et leurs contraintes
    try:
        nuclear_dataframe = (
            build_nuclear_dataframe()
        )

        plants = nuclear_dataframe.to_dict(
            orient="records"
        )

        return {
            "plants_count": len(plants),
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


@app.get("/phase1/consumption")
def get_consumption():
    # affiche la consommation nationale et régionale
    #     pour les 96 quarts d'heure

    try:
        consumption_data = (
            load_reference_consumption()
        )

        steps = []

        timestamps = consumption_data[
            "timestamps"
        ]

        national_consumptions = consumption_data[
            "national_total_consumption_mw"
        ]

        regions = consumption_data[
            "regions"
        ]

        for index, timestamp in enumerate(
            timestamps
        ):
            regional_consumption = {}

            for region in regions:
                regional_consumption[
                    region["id"]
                ] = region[
                    "consumption_mw"
                ][index]

            steps.append({
                "index": index,
                "timestamp": timestamp,

                "national_consumption_mw":
                    national_consumptions[index],

                "regional_consumption_mw":
                    regional_consumption,
            })

        return {
            "step_minutes": 15,
            "steps_count": len(steps),
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


@app.get("/phase1/simulate-day")
def simulate_phase1_api(
    number_of_steps: int = Query(
        default=96,
        ge=1,
        le=96,
        description=(
            "Nombre de quarts d'heure à simuler"
        ),
    )
):
    # lance la simulation temporelle de la phase 1

    try:
        return run_phase1(
            number_of_steps
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


def display_simulation(simulation):
    # affiche la simulation dans le terminal
    print()
    print("=== EnergIA — Phase 1 ===")
    print()

    for step in simulation["steps"]:
        print(
            f"{step['timestamp']} | "
            f"demande={step['nuclear_required_mw']:.0f} MW | "
            f"production={step['production_mw']:.0f} MW | "
            f"manquant={step['missing_mw']:.0f} MW | "
            f"surplus={step['forced_surplus_mw']:.0f} MW | "
            f"direction={step['direction']}"
        )

        print("  Consommation régionale :")

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

        print("  Répartition des centrales :")

        for plant in step["plants"]:
            print(
                f"    - {plant['plant_name']} "
                f"({plant['plant_id']}): "
                f"{plant['previous_output_mw']:.1f} "
                f"-> {plant['output_mw']:.1f} MW "
                f"(variation "
                f"{plant['change_mw']:+.1f} MW)"
            )

        print()

    print("=== Résumé ===")

    print(
        f"Nombre de pas : "
        f"{simulation['steps_count']}"
    )

    print(
        f"Journée complète : "
        f"{simulation['complete_day']}"
    )

    print(
        f"Demande toujours satisfaite : "
        f"{simulation['all_demand_satisfied']}"
    )

    print(
        f"Contraintes toujours respectées : "
        f"{simulation['all_constraints_respected']}"
    )

    print(
        f"Production toujours équilibrée : "
        f"{simulation['all_production_balanced']}"
    )

    print(
        f"Puissance totale manquante : "
        f"{simulation['total_missing_mw']:.1f} MW"
    )


def run_command_line():
    parser = argparse.ArgumentParser(
        description=(
            "Simulation temporelle "
            "- Phase 1"
        )
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=96,
        choices=range(1, 97),
        metavar="[1-96]",
        help=(
            "Nombre de quarts d'heure "
            "à simuler"
        ),
    )

    arguments = parser.parse_args()

    simulation = run_phase1(
        arguments.steps
    )

    display_simulation(
        simulation
    )


if __name__ == "__main__":
    run_command_line()