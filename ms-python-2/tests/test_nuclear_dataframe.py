import unittest

from services.nuclear_dataframe import build_nuclear_dataframe


class TestNuclearDataFrame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataframe = build_nuclear_dataframe()

    def test_une_ligne_par_centrale(self):
        self.assertEqual(len(self.dataframe), 18)
        self.assertTrue(self.dataframe["plant_id"].is_unique)

    def test_fusionne_les_deux_sources(self):
        belleville = self.dataframe.set_index("plant_id").loc["belleville"]
        self.assertEqual(belleville["location_region_name"], "Centre-Val de Loire")
        self.assertEqual(belleville["maximum_power_mw"], 2620)
        self.assertEqual(belleville["max_ramp_down_mw_per_15_min"], 264)


if __name__ == "__main__":
    unittest.main()
