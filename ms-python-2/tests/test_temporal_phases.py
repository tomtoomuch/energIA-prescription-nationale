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

class TestPhase1(
    TemporalTestBase
):
    def test_phase1_produit_96_pas(self):
        simulation = simulate_day(
            consumption_data=(
                self.consumption_data
            ),
            nuclear_dataframe=(
                self.nuclear_dataframe
            ),
            number_of_steps=96,
            **self.regional_context(),
        )

        self.assertEqual(
            simulation["phase"],
            1,
        )

        self.assertEqual(
            simulation["steps_count"],
            96,
        )

        self.assertTrue(
            simulation["complete_day"]
        )



# -------Phase 2------------
class TestPhase2(
    TemporalTestBase
):
    def test_phase2_produit_96_pas(self):
        simulation = simulate_day(
            consumption_data=(
                self.consumption_data
            ),
            nuclear_dataframe=(
                self.nuclear_dataframe
            ),
            number_of_steps=96,
            non_dispatchable_data=(
                self.non_dispatchable_data
            ),
            minimum_reserve_mw=5000,
            **self.regional_context(),
        )

        self.assertEqual(
            simulation["phase"],
            2,
        )

        self.assertEqual(
            simulation["steps_count"],
            96,
        )

        self.assertTrue(
            simulation["complete_day"]
        )

    def test_phase2_calcul_demande_residuelle(
        self
    ):
        simulation = simulate_day(
            consumption_data=(
                self.consumption_data
            ),
            nuclear_dataframe=(
                self.nuclear_dataframe
            ),
            number_of_steps=1,
            non_dispatchable_data=(
                self.non_dispatchable_data
            ),
            minimum_reserve_mw=5000,
            **self.regional_context(),
        )

        step = simulation["steps"][0]

        expected_residual_demand = max(
            0.0,
            step["total_consumption_mw"]
            - step[
                "solar_production_mw"
            ]
            - step[
                "wind_production_mw"
            ],
        )

        self.assertAlmostEqual(
            step["residual_demand_mw"],
            expected_residual_demand,
            places=3,
        )

    def test_phase2_calcule_la_reserve(
        self
    ):
        simulation = simulate_day(
            consumption_data=(
                self.consumption_data
            ),
            nuclear_dataframe=(
                self.nuclear_dataframe
            ),
            number_of_steps=1,
            non_dispatchable_data=(
                self.non_dispatchable_data
            ),
            minimum_reserve_mw=5000,
            **self.regional_context(),
        )

        step = simulation["steps"][0]

        self.assertGreaterEqual(
            step["nuclear_reserve_mw"],
            0,
        )

        self.assertEqual(
            step["reserve_sufficient"],
            (
                step["nuclear_reserve_mw"]
                >= step[
                    "minimum_reserve_mw"
                ]
            ),
        )

# ---------phase 3--------
class TestPhase3(
    TemporalTestBase
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        scenarios_data = (
            load_consumption_scenarios()
        )

        cls.scenario = (
            get_consumption_scenario(
                scenarios_data,
                "evening_peak_occitanie",
            )
        )

    def run_phase3_simulation(self):
        return simulate_day(
            consumption_data=(
                self.consumption_data
            ),
            nuclear_dataframe=(
                self.nuclear_dataframe
            ),
            number_of_steps=96,
            non_dispatchable_data=(
                self.non_dispatchable_data
            ),
            minimum_reserve_mw=5000,
            consumption_events=(
                self.scenario["events"]
            ),
            **self.regional_context(),
        )

    def test_phase3_produit_96_pas(self):
        simulation = (
            self.run_phase3_simulation()
        )

        self.assertEqual(
            simulation["phase"],
            3,
        )

        self.assertEqual(
            simulation["steps_count"],
            96,
        )

        self.assertTrue(
            simulation["complete_day"]
        )

    def test_phase3_applique_evenement(
        self
    ):
        simulation = (
            self.run_phase3_simulation()
        )

        active_steps = [
            step
            for step in simulation["steps"]
            if step["active_events"]
        ]

        self.assertGreater(
            len(active_steps),
            0,
        )

        for step in active_steps:
            self.assertNotEqual(
                step["event_delta_mw"],
                0,
            )

    def test_phase3_evenement_limite_aux_horaires(
        self
    ):
        simulation = (
            self.run_phase3_simulation()
        )

        step_before = next(
            step
            for step in simulation["steps"]
            if step["timestamp"] == "17:15"
        )

        step_start = next(
            step
            for step in simulation["steps"]
            if step["timestamp"] == "17:30"
        )

        step_end = next(
            step
            for step in simulation["steps"]
            if step["timestamp"] == "21:00"
        )

        self.assertEqual(
            step_before["event_delta_mw"],
            0,
        )

        self.assertGreater(
            step_start["event_delta_mw"],
            0,
        )

        self.assertEqual(
            step_end["event_delta_mw"],
            0,
        )

    def test_phase3_respecte_les_contraintes(
        self
    ):
        simulation = (
            self.run_phase3_simulation()
        )

        self.assertTrue(
            simulation[
                "all_constraints_respected"
            ]
        )


if __name__ == "__main__":
    unittest.main()