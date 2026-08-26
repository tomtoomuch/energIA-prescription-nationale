import unittest
from services.graph_loader import load_data, build_graph, build_plants_index, build_regions_index, load_temporal_nuclear_parameters
from services.dijkstra import dijkstra
from services.capacity import dispatchable_margin
from services.allocation import allocate
from services.temporal_allocation import allocate_regional_demands
from services.temporal_engine import build_initial_state




class TestDijkstra(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.graph = build_graph(cls.data)

    def test_chemin_simple_existe(self):
        path, distance = dijkstra(self.graph, "golfech", "nogent")
        self.assertIsNotNone(path)
        self.assertEqual(path[0], "golfech")
        self.assertEqual(path[-1], "nogent")
        self.assertGreater(distance, 0)

    def test_absence_de_chemin(self):
        mini_graph = {"a": [], "b": []}
        path, distance = dijkstra(mini_graph, "a", "b")
        self.assertIsNone(path)
        self.assertIsNone(distance)

class TestCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.plants_index = build_plants_index(cls.data)

    def test_calcul_marge_disponible(self):
        plant = self.plants_index["golfech"]
        
        margin = dispatchable_margin(plant)
        attendu = plant["simulation"]["initial_dispatchable_margin_mw"]
        self.assertEqual(margin, attendu)

    def test_calcul_marge_depuis_production_courante(self):
        plant = self.plants_index["golfech"]
        maximum = float(
            plant["simulation"]["soft_upper_bound_mw"]
        )
        current_output_mw = maximum - 100.0
        margin = dispatchable_margin(
            plant,
            current_output_mw=current_output_mw,
        )
        self.assertEqual(margin, 100.0)

class TestAllocation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.graph = build_graph(cls.data)
        cls.plants_index = build_plants_index(cls.data)
        cls.regions_index = build_regions_index(cls.data)
        cls.simulation_parameters = cls.data["simulation_parameters"]

    def test_demande_satisfaisable(self):
        region = self.regions_index["occitanie"]
        result = allocate(region, 100, self.graph, self.plants_index, self.simulation_parameters)
        self.assertTrue(result["fully_satisfied"])
        self.assertEqual(result["missing_mw"], 0.0)

    def test_demande_non_satisfaisable(self):
        region = self.regions_index["corse"]
        result = allocate(region, 300, self.graph, self.plants_index, self.simulation_parameters)
        self.assertFalse(result["fully_satisfied"])
        self.assertGreater(result["missing_mw"], 0)

class TestTemporalAllocation(unittest.TestCase):

    def test_calcul_de_la_montee_necessaire(self):
        regional_demands = {
            "occitanie": 18000.0,
            "grand_est": 16000.0,
        }

        current_state = {
            "golfech": 15000.0,
            "cattenom": 16000.0,
        }

        # Régions fictives sans aucune centrale candidate.
        empty_region = {
            "local_plant_ids": [],
            "external_entry_plant_ids": [],
        }

        result = allocate_regional_demands(
            regional_demands=regional_demands,
            current_state=current_state,
            graph={},
            plants_index={},
            regions_index={
                "occitanie": empty_region,
                "grand_est": empty_region,
            },
            simulation_parameters={},
        )

        self.assertEqual(
            result["total_demand_mw"],
            34000.0,
        )

        self.assertEqual(
            result["current_production_mw"],
            31000.0,
        )

        self.assertEqual(
            result["direction"],
            "up",
        )

        self.assertEqual(
            result["requested_change_mw"],
            3000.0,
        )

        self.assertEqual(
            result["missing_mw"],
            3000.0,
        )

    def test_allocation_reelle_modifie_etat(self):
        data = load_data()

        graph = build_graph(data)

        plants_index = build_plants_index(
            data
        )

        regions_index = build_regions_index(
            data
        )

        temporal_data = (
            load_temporal_nuclear_parameters()
        )

        current_state = build_initial_state(
            temporal_data["plants"]
        )

        initial_total_mw = sum(
            current_state.values()
        )

        # Le parc doit produire 100 MW supplémentaires.
        regional_demands = {
            "occitanie": initial_total_mw + 100.0
        }

        result = allocate_regional_demands(
            regional_demands=regional_demands,
            current_state=current_state,
            graph=graph,
            plants_index=plants_index,
            regions_index=regions_index,
            simulation_parameters=(
                data["simulation_parameters"]
            ),
        )

        final_total_mw = sum(
            result["state"].values()
        )

        self.assertAlmostEqual(
            result["requested_change_mw"],
            100.0,
        )

        self.assertAlmostEqual(
            final_total_mw,
            initial_total_mw + 100.0,
        )

        self.assertAlmostEqual(
            result["missing_mw"],
            0.0,
        )

        self.assertIn(
            "occitanie",
            result["regional_results"],
        )
        
    def test_descente_respecte_les_flexibilites(self):
        regional_demands = {
            "region_test": 1700.0,
        }

        current_state = {
            "centrale_a": 1000.0,
            "centrale_b": 1000.0,
        }

        plant_limits = {
            "centrale_a": {
                "down_flexibility_mw": 200.0,
            },
            "centrale_b": {
                "down_flexibility_mw": 100.0,
            },
        }

        result = allocate_regional_demands(
            regional_demands=regional_demands,
            current_state=current_state,
            graph={},
            plants_index={},
            regions_index={},
            simulation_parameters={},
            plant_limits=plant_limits,
        )

        self.assertEqual(
            result["direction"],
            "down",
        )

        self.assertEqual(
            result["requested_change_mw"],
            300.0,
        )

        self.assertAlmostEqual(
            result["state"]["centrale_a"],
            800.0,
        )

        self.assertAlmostEqual(
            result["state"]["centrale_b"],
            900.0,
        )

        self.assertAlmostEqual(
            result["forced_surplus_mw"],
            0.0,
        )
if __name__ == "__main__":

    unittest.main()
