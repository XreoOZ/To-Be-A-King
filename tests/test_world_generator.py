"""Tests for generated maps, rulers, and live world installation."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.core.world_generator import generate_world, install_generated_world


class WorldGeneratorTests(unittest.TestCase):
    def test_world_sizes_create_connected_provinces_with_valid_rulers(self):
        for province_count in (10, 20, 30):
            with self.subTest(province_count=province_count):
                world = generate_world(province_count, seed=province_count * 100)
                provinces = world["provinces"]
                characters = world["characters"]

                self.assertEqual(len(provinces), province_count)
                self.assertGreaterEqual(len(characters), 6)
                self.assertLessEqual(len(characters), 10)
                self.assertEqual(len(world["ai_rulers"]), len(characters) - 1)

                for province in provinces.values():
                    self.assertGreaterEqual(len(province["coords"]), 30)
                    self.assertLessEqual(len(province["coords"]), 80)
                    self.assertIn(province["owner"], characters)
                    self.assertTrue(province["neighbors"])

                reached = set()
                pending = [next(iter(provinces))]
                while pending:
                    province_id = pending.pop()
                    if province_id in reached:
                        continue
                    reached.add(province_id)
                    pending.extend(provinces[province_id]["neighbors"])
                self.assertEqual(reached, set(provinces))

                for character in characters.values():
                    self.assertEqual(provinces[character["capital_province"]]["owner"], character["id"])

                glyphs = world["map_data"]["char_to_prov"]
                land_tiles = sum(row.count(glyph) for row in world["map_data"]["raw_grid"] for glyph in glyphs)
                self.assertEqual(land_tiles, sum(len(p["coords"]) for p in provinces.values()))

    def test_new_seed_changes_generated_roster(self):
        first_world = generate_world(10, seed=111)
        second_world = generate_world(10, seed=222)
        first_roster = {
            character["name"] for character in first_world["characters"].values()
        }
        second_roster = {
            character["name"] for character in second_world["characters"].values()
        }

        self.assertNotEqual(first_roster, second_roster)

    def test_install_updates_map_and_can_start_a_game_state(self):
        from game.core.map import (
            CELL_TO_PROV, MAP_DATA, RAW_GRID, apply_map_data,
        )
        from game.core.state import GameState
        from game.data.characters import CHARACTERS
        from game.data.provinces import (
            ADJACENCY, PROVINCES, PROVINCE_FACTION_COLORS,
            refresh_province_faction_colors,
        )
        from game.data.scenario import SCENARIO

        original_characters = copy.deepcopy(CHARACTERS)
        original_provinces = copy.deepcopy(PROVINCES)
        original_scenario = copy.deepcopy(SCENARIO)
        original_map = copy.deepcopy(MAP_DATA)
        try:
            world = generate_world(30, seed=333)
            install_generated_world(world)
            state = GameState()

            self.assertEqual(set(CELL_TO_PROV.values()), set(PROVINCES))
            self.assertEqual(set(ADJACENCY), set(PROVINCES))
            self.assertEqual(set(PROVINCE_FACTION_COLORS), set(CHARACTERS))
            self.assertEqual(len(state.ai_rulers), len(CHARACTERS) - 1)
            self.assertIn(state.selected_province, PROVINCES)
        finally:
            CHARACTERS.clear()
            CHARACTERS.update(original_characters)
            PROVINCES.clear()
            PROVINCES.update(original_provinces)
            SCENARIO.clear()
            SCENARIO.update(original_scenario)
            apply_map_data(original_map)
            refresh_province_faction_colors()
            self.assertEqual(RAW_GRID, original_map["raw_grid"])


if __name__ == "__main__":
    unittest.main()
