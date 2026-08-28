import json
from pathlib import Path


SCENARIO_EXPORT_DIRECTORY = (
    Path(__file__).resolve().parent.parent
    / "exported_scenarios"
)


def validate_complete_scenario(
    complete_scenario
):
    if not isinstance(
        complete_scenario,
        dict
    ):
        raise TypeError(
            "Le scénario complet doit être "
            "un dictionnaire"
        )

    required_fields = {
        "format_version",
        "scenario",
        "simulation_parameters",
    }

    missing_fields = (
        required_fields
        - complete_scenario.keys()
    )

    if missing_fields:
        raise ValueError(
            "Champs manquants dans le scénario : "
            f"{', '.join(sorted(missing_fields))}"
        )

    scenario = complete_scenario[
        "scenario"
    ]

    if not isinstance(
        scenario,
        dict
    ):
        raise TypeError(
            "Le champ scenario doit être "
            "un dictionnaire"
        )

    required_scenario_fields = {
        "id",
        "name",
        "events",
    }

    missing_scenario_fields = (
        required_scenario_fields
        - scenario.keys()
    )

    if missing_scenario_fields:
        raise ValueError(
            "Champs manquants dans scenario : "
            f"{', '.join(sorted(missing_scenario_fields))}"
        )

    if not isinstance(
        scenario["events"],
        list
    ):
        raise TypeError(
            "Les événements doivent être "
            "contenus dans une liste"
        )

    simulation_parameters = (
        complete_scenario[
            "simulation_parameters"
        ]
    )

    if not isinstance(
        simulation_parameters,
        dict
    ):
        raise TypeError(
            "Les paramètres de simulation doivent être "
            "un dictionnaire"
        )

    required_parameter_fields = {
        "number_of_steps",
        "minimum_reserve_mw",
    }

    missing_parameter_fields = (
        required_parameter_fields
        - simulation_parameters.keys()
    )

    if missing_parameter_fields:
        raise ValueError(
            "Paramètres manquants : "
            f"{', '.join(sorted(missing_parameter_fields))}"
        )

    number_of_steps = int(
        simulation_parameters[
            "number_of_steps"
        ]
    )

    minimum_reserve_mw = float(
        simulation_parameters[
            "minimum_reserve_mw"
        ]
    )

    if number_of_steps < 1:
        raise ValueError(
            "Le nombre de pas doit être positif"
        )

    if minimum_reserve_mw < 0:
        raise ValueError(
            "La réserve minimale ne peut pas "
            "être négative"
        )

    return True


def build_complete_scenario(
    scenario,
    number_of_steps=96,
    minimum_reserve_mw=5000
):
    complete_scenario = {
        "format_version": 1,
        "scenario": scenario,
        "simulation_parameters": {
            "number_of_steps": int(
                number_of_steps
            ),
            "minimum_reserve_mw": float(
                minimum_reserve_mw
            ),
        },
    }

    validate_complete_scenario(
        complete_scenario
    )

    return complete_scenario


def export_complete_scenario(
    complete_scenario,
    output_path
):
    validate_complete_scenario(
        complete_scenario
    )

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as json_file:
        json.dump(
            complete_scenario,
            json_file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def import_complete_scenario(
    input_path
):
    input_path = Path(
        input_path
    )

    if not input_path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {input_path}"
        )

    with input_path.open(
        "r",
        encoding="utf-8"
    ) as json_file:
        complete_scenario = json.load(
            json_file
        )

    validate_complete_scenario(
        complete_scenario
    )

    return complete_scenario


if __name__ == "__main__":
    from services.graph_loader import (
        get_consumption_scenario,
        load_consumption_scenarios,
    )

    scenarios_data = (
        load_consumption_scenarios()
    )

    scenario = get_consumption_scenario(
        scenarios_data,
        "evening_peak_occitanie",
    )

    complete_scenario = (
        build_complete_scenario(
            scenario=scenario,
            number_of_steps=96,
            minimum_reserve_mw=5000,
        )
    )

    output_path = (
        SCENARIO_EXPORT_DIRECTORY
        / "evening_peak_occitanie.json"
    )

    export_complete_scenario(
        complete_scenario,
        output_path,
    )

    imported_scenario = (
        import_complete_scenario(
            output_path
        )
    )

    print(
        "Scénario exporté dans :",
        output_path,
    )

    print(
        "Scénario réimporté :",
        imported_scenario[
            "scenario"
        ][
            "name"
        ],
    )