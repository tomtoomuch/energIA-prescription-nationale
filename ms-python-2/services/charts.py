from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


OUTPUT_DIRECTORY = (
    Path(__file__).resolve().parent.parent
    / "generated_charts"
)


REQUIRED_STEP_FIELDS = {
    "timestamp",
    "total_consumption_mw",
    "solar_production_mw",
    "wind_production_mw",
    "non_dispatchable_production_mw",
    "residual_demand_mw",
    "production_mw",
    "nuclear_reserve_mw",
    "minimum_reserve_mw",
    "forced_surplus_mw",
    "missing_mw",
}


def validate_chart_data(
    simulation
):
    if not isinstance(
        simulation,
        dict
    ):
        raise TypeError(
            "La simulation doit être "
            "un dictionnaire"
        )

    steps = simulation.get(
        "steps",
        []
    )

    if not steps:
        raise ValueError(
            "La simulation ne contient "
            "aucun quart d'heure"
        )

    for index, step in enumerate(
        steps
    ):
        missing_fields = (
            REQUIRED_STEP_FIELDS
            - step.keys()
        )

        if missing_fields:
            raise ValueError(
                f"Données manquantes au pas {index} : "
                f"{', '.join(sorted(missing_fields))}"
            )

    return steps


def get_chart_values(
    steps,
    field_name
):
    return [
        float(
            step[field_name]
        )
        for step in steps
    ]


def configure_time_axis(
    axis,
    timestamps
):
    steps_count = len(
        timestamps
    )

    label_interval = max(
        1,
        steps_count // 12
    )

    label_positions = list(
        range(
            0,
            steps_count,
            label_interval
        )
    )

    label_values = [
        timestamps[index]
        for index in label_positions
    ]

    axis.set_xticks(
        label_positions
    )

    axis.set_xticklabels(
        label_values,
        rotation=45,
        ha="right",
    )

    axis.set_xlim(
        0,
        steps_count - 1
    )

    axis.grid(
        True,
        alpha=0.3,
    )


def generate_phase2_charts(
    simulation,
    output_directory=OUTPUT_DIRECTORY
):
    steps = validate_chart_data(
        simulation
    )

    output_directory = Path(
        output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamps = [
        step["timestamp"]
        for step in steps
    ]

    time_indexes = list(
        range(
            len(steps)
        )
    )

    total_consumptions = (
        get_chart_values(
            steps,
            "total_consumption_mw",
        )
    )

    solar_productions = (
        get_chart_values(
            steps,
            "solar_production_mw",
        )
    )

    wind_productions = (
        get_chart_values(
            steps,
            "wind_production_mw",
        )
    )

    non_dispatchable_productions = (
        get_chart_values(
            steps,
            "non_dispatchable_production_mw",
        )
    )

    residual_demands = (
        get_chart_values(
            steps,
            "residual_demand_mw",
        )
    )

    nuclear_productions = (
        get_chart_values(
            steps,
            "production_mw",
        )
    )

    nuclear_reserves = (
        get_chart_values(
            steps,
            "nuclear_reserve_mw",
        )
    )

    minimum_reserves = (
        get_chart_values(
            steps,
            "minimum_reserve_mw",
        )
    )

    forced_surpluses = (
        get_chart_values(
            steps,
            "forced_surplus_mw",
        )
    )

    missing_productions = (
        get_chart_values(
            steps,
            "missing_mw",
        )
    )

    figure, axes = plt.subplots(
        nrows=4,
        ncols=1,
        figsize=(
            16,
            20
        ),
        sharex=True,
    )

    figure.suptitle(
        "EnergIA phase 2",
        fontsize=18,
        fontweight="bold",
    )

    consumption_axis = axes[0]

    consumption_axis.plot(
        time_indexes,
        total_consumptions,
        label="consommation totale",
        color="#1f77b4",
        linewidth=2,
    )

    consumption_axis.plot(
        time_indexes,
        residual_demands,
        label="demande résiduelle",
        color="#ff7f0e",
        linewidth=2,
    )

    consumption_axis.plot(
        time_indexes,
        nuclear_productions,
        label="production nucléaire",
        color="#d62728",
        linewidth=2,
        linestyle="--",
    )

    consumption_axis.set_title(
        "consommation et production nucléaire"
    )

    consumption_axis.set_ylabel(
        "puissance en MW"
    )

    consumption_axis.legend(
        loc="best"
    )

    configure_time_axis(
        consumption_axis,
        timestamps,
    )

    renewable_axis = axes[1]

    renewable_axis.plot(
        time_indexes,
        solar_productions,
        label="production solaire",
        color="#f2c500",
        linewidth=2,
    )

    renewable_axis.plot(
        time_indexes,
        wind_productions,
        label="production éolienne",
        color="#2ca02c",
        linewidth=2,
    )

    renewable_axis.plot(
        time_indexes,
        non_dispatchable_productions,
        label="production non pilotable",
        color="#17becf",
        linewidth=2,
        linestyle="--",
    )

    renewable_axis.set_title(
        "productions non pilotables"
    )

    renewable_axis.set_ylabel(
        "puissance en MW"
    )

    renewable_axis.legend(
        loc="best"
    )

    configure_time_axis(
        renewable_axis,
        timestamps,
    )

    reserve_axis = axes[2]

    reserve_axis.plot(
        time_indexes,
        nuclear_reserves,
        label="réserve disponible",
        color="#9467bd",
        linewidth=2,
    )

    reserve_axis.plot(
        time_indexes,
        minimum_reserves,
        label="réserve minimale",
        color="#d62728",
        linewidth=2,
        linestyle="--",
    )

    reserve_axis.fill_between(
        time_indexes,
        nuclear_reserves,
        minimum_reserves,
        where=[
            reserve
            < minimum
            for reserve, minimum in zip(
                nuclear_reserves,
                minimum_reserves
            )
        ],
        color="#d62728",
        alpha=0.25,
        label="réserve insuffisante",
    )

    reserve_axis.set_title(
        "réserve nucléaire"
    )

    reserve_axis.set_ylabel(
        "puissance en MW"
    )

    reserve_axis.legend(
        loc="best"
    )

    configure_time_axis(
        reserve_axis,
        timestamps,
    )

    balance_axis = axes[3]

    balance_axis.plot(
        time_indexes,
        forced_surpluses,
        label="surplus nucléaire",
        color="#ff7f0e",
        linewidth=2,
    )

    balance_axis.plot(
        time_indexes,
        missing_productions,
        label="puissance manquante",
        color="#d62728",
        linewidth=2,
    )

    balance_axis.fill_between(
        time_indexes,
        missing_productions,
        color="#d62728",
        alpha=0.25,
    )

    balance_axis.set_title(
        "surplus et puissance manquante"
    )

    balance_axis.set_xlabel(
        "heure"
    )

    balance_axis.set_ylabel(
        "puissance en MW"
    )

    balance_axis.legend(
        loc="best"
    )

    configure_time_axis(
        balance_axis,
        timestamps,
    )

    figure.tight_layout(
        rect=(
            0,
            0,
            1,
            0.98
        )
    )

    output_path = (
        output_directory
        / "energia-phase2-courbes.png"
    )

    figure.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(
        figure
    )

    return output_path


if __name__ == "__main__":
    from services.graph_loader import (
        load_reference_consumption,
        load_non_dispatchable_production,
    )

    from services.nuclear_dataframe import (
        build_nuclear_dataframe,
    )

    from services.temporal_engine import (
        simulate_day,
    )

    consumption_data = (
        load_reference_consumption()
    )

    non_dispatchable_data = (
        load_non_dispatchable_production()
    )

    nuclear_dataframe = (
        build_nuclear_dataframe()
    )

    simulation = simulate_day(
        consumption_data=consumption_data,
        nuclear_dataframe=nuclear_dataframe,
        number_of_steps=96,
        non_dispatchable_data=non_dispatchable_data,
        minimum_reserve_mw=5000,
    )

    chart_path = generate_phase2_charts(
        simulation
    )

    print(
        "Courbes générées dans :",
        chart_path,
    )