"""Headless smoke test: init, tick, and render every tab for each playable ruler.

Run from the repository root:

    python tests/smoke_dynamic.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()
pygame.display.set_mode((1920, 1080))

from game.config import get_fonts
from game.core.state import GameState, setup_province_starter_cities
from game.core.assets import init_asset_caches, prov_flag_cache, portrait_cache, coa_cache
from game.core.assets import make_banner_cloth, load_image
from game.ui.header import render_header
from game.ui.left_panel import render_left_panel
from game.ui.map_view import render_map_view
from game.ui.right_panel import render_right_panel
from game.ui.modals import render_modals
from game.data.characters import CHARACTERS
from game.data.provinces import PROVINCES
from game.data.scenario import SCENARIO, INITIAL_SCENARIO

fonts = get_fonts()
init_asset_caches()
icons = {}
for k in ("gold", "prestige", "piety", "troops"):
    icons[k] = load_image(os.path.join("icons", k + ".png"), (24, 24))

DEFAULT_PLAYER = INITIAL_SCENARIO.get("player_id") or next(iter(CHARACTERS))


def render_frame(state):
    screen = pygame.display.get_surface()
    big = {pid: make_banner_cloth(pid, 32, 22, is_large=True) for pid in prov_flag_cache}
    small = {pid: make_banner_cloth(pid, 18, 13, is_large=False) for pid in prov_flag_cache}
    render_header(screen, state, (0, 0), False, False, fonts, icons)
    for tab in ("armies", "demesne", "diplomacy", "vassals"):
        state.left_tab = tab
        render_left_panel(screen, state, (0, 0), False, fonts, portrait_cache, coa_cache)
    render_map_view(screen, state, (700, 400), False, False, False, fonts, big, small, ticks=10)
    render_right_panel(screen, state, (0, 0), False, fonts, coa_cache, icons=icons)
    render_modals(screen, state, (0, 0), False, fonts, portrait_cache, coa_cache)


for player in list(CHARACTERS.keys()):
    SCENARIO["player_id"] = player
    state = GameState()
    setup_province_starter_cities(state)
    render_frame(state)
    # Advance a month and a year through real ticks.
    for _ in range(32):
        state.advance_day()
    state.yearly_tick()
    render_frame(state)
    print("PLAYER", player, "OK", "provinces", len(PROVINCES), "ai", state.ai_rulers,
          "gold", {c: CHARACTERS[c].get("gold") for c in CHARACTERS})

# Generic subjugation: strip a ruler's provinces, then force check.
SCENARIO["player_id"] = DEFAULT_PLAYER
state = GameState()
setup_province_starter_cities(state)
victim = state.ai_rulers[0]
for pid, p in PROVINCES.items():
    if p.get("owner") == victim:
        p["owner"] = state.player_id
state.check_subjugation_and_vassalage()
print("SUBJUGATION", victim, "liege", state.get_liege(victim), "event", bool(state.subjugation_event))

print("SMOKE OK")
