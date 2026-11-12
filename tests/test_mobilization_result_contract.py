"""Regression tests for the province levy return contract."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.core.state import GameState
from game.data.provinces import PROVINCES, reset_global_world_data


class MobilizationResultContractTests(unittest.TestCase):
    def setUp(self):
        reset_global_world_data()
        self.state = GameState()

    def tearDown(self):
        reset_global_world_data()

    def test_emergency_mobilization_handles_provinces_with_no_levies(self):
        ruler_id = self.state.ai_rulers[0]
        ruler_provinces = [
            province for province in PROVINCES.values()
            if province.get("owner") == ruler_id
        ]
        self.assertTrue(ruler_provinces)
        for province in ruler_provinces:
            province["levies_current"] = 0
            province["raise_cooldown_days"] = 0

        self.assertEqual(
            self.state.raise_all_realm_levies(ruler_id, is_emergency=True),
            (0, 0),
        )

    def test_unknown_province_returns_zero_counts(self):
        self.assertEqual(self.state.raise_province_levy("missing_province"), (0, 0))


if __name__ == "__main__":
    unittest.main()
