"""Regression tests for sovereign titles in the demesne UI."""
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.core.state import GameState
from game.data.characters import CHARACTERS
from game.data.provinces import PROVINCES
from game.ui.left_panel import get_feudal_rank_key


class DemesneTitleTests(unittest.TestCase):
    def test_title_tiers_map_to_their_actual_feudal_ranks(self):
        self.assertEqual(get_feudal_rank_key("kingdom"), "king")
        self.assertEqual(get_feudal_rank_key("duchy"), "duke")
        self.assertEqual(get_feudal_rank_key("county"), "count")
        self.assertEqual(get_feudal_rank_key("barony"), "baron")

    def test_sovereign_titles_include_their_province_seats(self):
        state = GameState()

        for ruler_id in CHARACTERS:
            with self.subTest(ruler_id=ruler_id):
                titles = state.get_held_titles(ruler_id)
                self.assertTrue(titles)
                self.assertEqual(titles[0].tier, "kingdom")
                self.assertTrue(any(title.tier == "duchy" for title in titles))
                self.assertTrue(any(title.tier == "barony" for title in titles))
                for title in titles:
                    self.assertIn(title.province_id, PROVINCES)

    def test_demesne_grant_flow_is_available_from_the_title_list(self):
        import pygame
        from game.config import get_fonts
        from game.core.assets import init_asset_caches, portrait_cache, coa_cache
        from game.ui.left_panel import render_left_panel

        pygame.init()
        screen = pygame.display.set_mode((1920, 1080))
        fonts = get_fonts()
        init_asset_caches()
        state = GameState()
        state.left_tab = "demesne"
        grantable_title = next(
            title for title in state.get_held_titles(state.player_id)
            if title.tier != "kingdom"
        )

        render_left_panel(
            screen, state, (390, 450), True, fonts, portrait_cache, coa_cache
        )
        self.assertEqual(state.title_grant_target_title_id, grantable_title.id)

        render_left_panel(
            screen, state, (200, 657), True, fonts, portrait_cache, coa_cache
        )
        self.assertIsNone(state.title_grant_target_title_id)

        state.left_tab = "vassals"
        render_left_panel(
            screen, state, (0, 0), False, fonts, portrait_cache, coa_cache
        )


if __name__ == "__main__":
    unittest.main()
