"""Tests for shared player/AI levy summons and fief-level demobilization."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.core.state import GameState
from game.data.characters import CHARACTERS
from game.data.provinces import PROVINCES, reset_global_world_data


class MobilizationReturnTests(unittest.TestCase):
    def setUp(self):
        reset_global_world_data()
        self.state = GameState()

    def tearDown(self):
        reset_global_world_data()

    def test_player_and_ai_vassal_levies_receive_fief_couriers(self):
        rulers = list(CHARACTERS)
        for ruler_id in rulers:
            with self.subTest(ruler=ruler_id):
                self.state.armies.clear()
                for province in PROVINCES.values():
                    province["levies_current"] = province.get("levies_max", 0)
                    province["raise_cooldown_days"] = 0

                if ruler_id == self.state.player_id:
                    raised, _ = self.state.raise_all_levies(ruler_id)
                else:
                    raised, _ = self.state.raise_all_realm_levies(
                        ruler_id, is_emergency=True
                    )

                vassal_hosts = [
                    army for army in self.state.armies
                    if army.owner == ruler_id and army.vassal_id
                ]
                self.assertGreater(raised, 0)
                self.assertTrue(vassal_hosts)
                self.assertTrue(all(army.courier_en_route for army in vassal_hosts))
                self.assertTrue(all(army.muster_days == 30 for army in vassal_hosts))

    def test_merged_armies_return_each_contingent_to_its_home_fief(self):
        ruler_id = self.state.player_id
        province_id = next(
            pid for pid, province in PROVINCES.items()
            if province.get("owner") == ruler_id
        )
        self.state.raise_province_levy(province_id, ruler_id)
        raised_hosts = [
            army for army in self.state.armies
            if army.owner == ruler_id and army.province == province_id
        ]
        self.assertGreaterEqual(len(raised_hosts), 2)

        for army in raised_hosts:
            army.courier_en_route = False
            army.is_mustering = False
            army.tile = raised_hosts[0].tile
            army.province = province_id

        merged = self.state.merge_armies_at_tile(raised_hosts[0].tile, ruler_id)
        self.assertIsNotNone(merged)
        expected_home_tiles = {
            self.state.get_sub_unit_home_tile(unit)
            for unit in merged.sub_units
            if unit.get("vassal_id")
        }

        self.state.disband_all_armies(ruler_id)

        returning = [
            army for army in self.state.armies
            if army.owner == ruler_id and army.is_demobilizing
        ]
        self.assertEqual(
            {army.return_tile for army in returning},
            expected_home_tiles,
        )
        self.assertTrue(all(
            all(self.state.get_sub_unit_home_tile(unit) == army.return_tile
                for unit in army.sub_units)
            for army in returning
        ))

        for army in returning:
            army.tile_path = [army.return_tile]
            army.move_progress = 0
        self.state.update_armies()
        self.assertFalse(any(army.is_demobilizing for army in self.state.armies))

    def test_muster_countdown_starts_after_courier_arrives(self):
        ruler_id = self.state.player_id
        province_id = next(
            pid for pid, province in PROVINCES.items()
            if province.get("owner") == ruler_id
        )
        self.state.raise_province_levy(province_id, ruler_id)
        army = next(
            army for army in self.state.armies
            if army.owner == ruler_id and army.courier_en_route
        )
        army.courier_tile_path = [army.courier_tile_path[-1]]
        army.courier_progress = 80

        self.state.update_ai_border_standoffs = lambda: None
        self.state.monthly_tick = lambda: None
        self.state.update_armies = lambda: None
        self.state.update_supply_wagons = lambda: None
        self.state.update_expeditionary_and_starvation = lambda: None
        self.state.check_subjugation_and_vassalage = lambda: None
        self.state.sync_conquered_rulers = lambda: None
        self.state.ai_routine = lambda: None

        self.state.advance_day()
        self.assertFalse(army.courier_en_route)
        self.assertTrue(army.is_mustering)
        self.assertEqual(army.muster_days, 30)

        for _ in range(29):
            self.state.advance_day()
        self.assertTrue(army.is_mustering)
        self.assertEqual(army.muster_days, 1)

        self.state.advance_day()
        self.assertFalse(army.is_mustering)


if __name__ == "__main__":
    unittest.main()
