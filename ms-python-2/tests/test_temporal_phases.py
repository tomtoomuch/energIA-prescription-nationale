import unittest

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

from services.temporal_engine import (
    simulate_day,
)


class TemporalTestBase(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.consumption_data = (
            load_reference_consumption()
        )

        cls.non_dispatchable_data = (
            load_non_dispatchable_production()
        )

        cls.nuclear_dataframe = (
            build_nuclear_dataframe()
        )

        cls.fleet_data = load_data()

        cls.graph = build_graph(
            cls.fleet_data
        )

        cls.plants_index = (
            build_plants_index(
                cls.fleet_data
            )
        )

        cls.regions_index = (
            build_regions_index(
                cls.fleet_data
            )
        )

        cls.simulation_parameters = (
            cls.fleet_data[
                "simulation_parameters"
            ]
        )

    def regional_context(self):
        return {
            "graph": self.graph,
            "plants_index":
                self.plants_index,
            "regions_index":
                self.regions_index,
            "simulation_parameters":
                self.simulation_parameters,
        }