from pathlib import Path

import pandas as pd

from services.graph_loader import load_json


DATA_DIRECTORY = (
    Path(__file__).resolve().parent.parent
    / "data"
)

FLEET_PATH = (
    DATA_DIRECTORY
    / "parc_nucleaire_prescriptif_france.json"
)

TEMPORAL_PARAMETERS_PATH = (
    DATA_DIRECTORY
    / "energia-parametres-temporels-nucleaire.json"
)


def build_nuclear_dataframe(
    fleet_path=FLEET_PATH,
    temporal_path=TEMPORAL_PARAMETERS_PATH,
):
    #historique du parc
    fleet_data = load_json(
        fleet_path
    )

    #paramètres temporels
    temporal_data = load_json(
        temporal_path
    )

    #les centralesde  premier JSON
    fleet_plants = fleet_data.get(
        "plants",
        []
    )

    #les centrales du second JSON
    temporal_plants = temporal_data.get(
        "plants",
        []
    )

    #paramètres communs au parc
    simulation_parameters = fleet_data.get(
        "simulation_parameters",
        {}
    )

    #liaisons entre centrales
    plant_edges = fleet_data.get(
        "plant_edges",
        []
    )

    if not fleet_plants:
        raise ValueError(
            "Aucune centrale trouvée "
            "dans le fichier du parc"
        )

    if not temporal_plants:
        raise ValueError(
            "Aucun paramètre temporel trouvé"
        )

    if not simulation_parameters:
        raise ValueError(
            "Aucun paramètre de simulation trouvé"
        )

    if not plant_edges:
        raise ValueError(
            "Aucune liaison entre centrales trouvée"
        )

    # transforme les centrales historiques en DataFrame
    # sep="_" transforme par exemple
    # location.region_id en location_region_id

    fleet_dataframe = pd.json_normalize(
        fleet_plants,
        sep="_"
    )

    # harmonise les noms des colonnes
    fleet_dataframe = (
        fleet_dataframe.rename(
            columns={
                "id": "plant_id",
                "name": "fleet_plant_name",
            }
        )
    )

    # les paramètres temporels en DataFrame
    temporal_dataframe = pd.DataFrame(
        temporal_plants
    )

    # evite un conflit entre les deux colonnes
    # contenant le nom de la centrale
    temporal_dataframe = (
        temporal_dataframe.rename(
            columns={
                "plant_name":
                    "temporal_plant_name"
            }
        )
    )

    # fusionne les deux DataFrames
    # à partir de plant_id
    dataframe = fleet_dataframe.merge(
        temporal_dataframe,
        on="plant_id",
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=(
            "_fleet",
            "_temporal"
        ),
    )

    # cherche les centrales présentes
    # dans un seul des deux fichiers
    unmatched = dataframe.loc[
        dataframe["_merge"] != "both",
        [
            "plant_id",
            "_merge"
        ]
    ]

    if not unmatched.empty:
        details = ", ".join(
            f"{row.plant_id} ({row._merge})"
            for row in unmatched.itertuples(
                index=False
            )
        )

        raise ValueError(
            "Centrales non appariées entre "
            f"les deux JSON : {details}"
        )

    # supprime la colonne technique utilisée
    # pendant la fusion
    dataframe = dataframe.drop(
        columns="_merge"
    )

    # utilise le nom temporel ou le nom
    # historique comme valeur de secours
    dataframe["plant_name"] = (
        dataframe[
            "temporal_plant_name"
        ].fillna(
            dataframe[
                "fleet_plant_name"
            ]
        )
    )

    def get_plant_edges(plant_id):

        connected_edges = []

        for edge in plant_edges:
            if (
                edge.get("from") == plant_id
                or edge.get("to") == plant_id
            ):
                connected_edges.append(
                    edge.copy()
                )

        return connected_edges

    # ajoute les liaisons dans une colonne.
    # chaque cellule contient une liste de dictionnaires.
    dataframe["plant_edges"] = (
        dataframe["plant_id"].apply(
            get_plant_edges
        )
    )

    # tous les paramètres de simulationnsous la forme de colonnes

    # les valeurs sont identiques pour toutes les centrales
    parameter_columns = []

    for (
        parameter_name,
        parameter_value
    ) in simulation_parameters.items():

        column_name = (
            f"parameter_{parameter_name}"
        )

        dataframe[column_name] = (
            parameter_value
        )

        parameter_columns.append(
            column_name
        )

    # colonnes importantes placées au début
    first_columns = [
        "plant_id",
        "plant_name",

        "location_latitude",
        "location_longitude",
        "location_commune",
        "location_department",
        "location_region_id",
        "location_region_name",

        # liaisons de la centrale
        "plant_edges",

        "reactor_count",
        "reactors",

        "installed_power_mw",

        "initial_output_mw_at_23_45_previous_day",
        "minimum_operating_power_mw",
        "maximum_power_mw",
        "max_ramp_up_mw_per_15_min",
        "max_ramp_down_mw_per_15_min",
        "available",
    ]

    # place les paramètres de simulation après les données principales
    first_columns.extend(
        parameter_columns
    )

    # conserve toutes les autres colonnes
    remaining_columns = [
        column
        for column in dataframe.columns
        if column not in first_columns
    ]

    # organise l’ordre des colonnes
    dataframe = dataframe[
        first_columns
        + remaining_columns
    ]

    # trie les centrales selon plant_id
    return dataframe.sort_values(
        "plant_id",
        ignore_index=True
    )


if __name__ == "__main__":
    #toutes les colonnes
    pd.set_option(
        "display.max_columns",
        None
    )

    # évite de tronquer le contenu des cellules
    pd.set_option(
        "display.max_colwidth",
        None
    )

    nuclear_dataframe = (
        build_nuclear_dataframe()
    )

    print(
        "Nombre de centrales :",
        len(nuclear_dataframe)
    )

    print(
        "Nombre de colonnes :",
        len(nuclear_dataframe.columns)
    )

    print(
        nuclear_dataframe.to_string(
            index=False
        )
    )