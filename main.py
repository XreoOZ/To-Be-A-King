"""
CK2-Lite (Modular Architecture Edition)

Main Entry Point
"""

import os
import sys
import pygame

# Enable Windows Per-Monitor High-DPI Awareness before initializing Pygame
try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

os.environ["SDL_RENDER_SCALE_QUALITY"] = "2"

# -------------------------------------------------------------
# Modular Architecture Imports
# -------------------------------------------------------------
from game.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, DAYS_PER_TILE, DAYS_PER_KOTAK,
    LEVY_RAISE_COOLDOWN_DAYS, COLOR_BG, COLOR_PANEL_BG, COLOR_PANEL_BORDER,
    COLOR_GOLD, COLOR_PRESTIGE, COLOR_PIETY, COLOR_TEXT_WHITE,
    COLOR_TEXT_MUTED, COLOR_TEXT_RED, COLOR_TEXT_GREEN, COLOR_BUTTON_NORMAL,
    COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE, COLOR_OCEAN,
    BASE_TILE_W, BASE_TILE_H, VIEWPORT_CENTER_X, VIEWPORT_CENTER_Y,
    PANEL_L_X, PANEL_L_W, PANEL_R_X, PANEL_R_W, MAP_VIEWPORT_X, MAP_VIEWPORT_W, PANEL_Y, PANEL_H,
    maximize_window, get_fonts
)
from game.data.characters import CHARACTERS, INITIAL_CHARACTERS, get_character
from game.data.provinces import (
    PROVINCES, INITIAL_PROVINCES, PROVINCE_FACTION_COLORS, ADJACENCY,
    reset_global_world_data, build_dynamic_province_adjacency, find_shortest_path
)
from game.data.buildings import BUILDING_SPECS, BARRACK_UPGRADE_COSTS, get_barrack_stats
from game.core.assets import (
    load_image, make_heraldic_shield, init_asset_caches,
    prov_flag_cache, portrait_cache, coa_cache,
    make_banner_cloth, get_scaled_banner_cloth, draw_waving_banner,
    SUB_FLAG_OFFSETS
)
from game.core.map import (
    RAW_GRID, CELL_TO_PROV, PROV_TO_TILES, PROV_CAPITAL_TILES,
    get_province_capital_tile, TILE_ADJACENCY, find_shortest_tile_path
)
from game.core.army import Army
from game.core.state import GameState, setup_province_starter_cities, carve_new_fief
from game.systems.economy import (
    sync_province_holdings_stats, get_vassal_landed_status,
    get_province_holdings, get_all_settlement_holdings, get_realm_finances
)
from game.systems.military import get_siegeable_holdings, is_province_contested
from game.systems.ai import standardize_enemy_ai_laws
from game.data.scenario import get_scenario

from game.ui.header import render_header
from game.ui.left_panel import render_left_panel
from game.ui.map_view import render_map_view
from game.ui.right_panel import render_right_panel
from game.ui.modals import render_modals
from game.ui.main_menu import render_main_menu
from game.core.world_generator import generate_world, install_generated_world

# Global screen reference
screen = None

def run_game():
    global screen
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption(get_scenario().get("window_title", "CK2-Lite"))
    maximize_window()
    clock = pygame.time.Clock()

    fonts = get_fonts()

    icons = {
        "gold": load_image(os.path.join("icons", "gold.png"), (24, 24)),
        "prestige": load_image(os.path.join("icons", "prestige.png"), (24, 24)),
        "piety": load_image(os.path.join("icons", "piety.png"), (24, 24)),
        "troops": load_image(os.path.join("icons", "troops.png"), (24, 24)),
        "speed_pause": load_image(os.path.join("icons", "speed_pause.png"), (24, 24)),
        "speed_play": load_image(os.path.join("icons", "speed_play.png"), (24, 24)),
        "speed_fast": load_image(os.path.join("icons", "speed_fast.png"), (24, 24)),
    }

    state = None
    game_started = False
    menu_stage = "main"
    world_size = 10
    banner_cloth_large = {}
    banner_cloth_small = {}

    def start_campaign():
        nonlocal state, game_started, banner_cloth_large, banner_cloth_small
        world = generate_world(world_size)
        install_generated_world(world)
        pygame.display.set_caption(get_scenario().get("window_title", "CK2-Lite"))
        init_asset_caches()
        banner_cloth_large = {pid: make_banner_cloth(pid, 32, 22, is_large=True) for pid in prov_flag_cache}
        banner_cloth_small = {pid: make_banner_cloth(pid, 18, 13, is_large=False) for pid in prov_flag_cache}
        state = GameState()
        state.min_zoom = float(get_scenario().get("min_zoom", state.min_zoom))
        setup_province_starter_cities(state)
        game_started = True

    map_viewport = pygame.Rect(MAP_VIEWPORT_X, PANEL_Y, MAP_VIEWPORT_W, PANEL_H)

    running = True
    box_start = None
    box_end = None

    while running:
        dt = clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False
        right_clicked = False
        mouse_down = pygame.mouse.get_pressed()[0]

        if not game_started:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if menu_stage == "character":
                        menu_stage = "main"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    buttons = render_main_menu(screen, fonts, mouse_pos, menu_stage, world_size)
                    if menu_stage == "main":
                        if buttons["play_menu"].collidepoint(event.pos):
                            menu_stage = "character"
                        elif buttons["exit"].collidepoint(event.pos):
                            running = False
                    else:
                        for size in (10, 20, 30):
                            if buttons[f"size_{size}"].collidepoint(event.pos):
                                world_size = size
                                break
                        if buttons["back"].collidepoint(event.pos):
                            menu_stage = "main"
                        elif buttons["start"].collidepoint(event.pos):
                            start_campaign()
            render_main_menu(screen, fonts, mouse_pos, menu_stage, world_size)
            pygame.display.flip()
            continue

        curr_tile_w = max(18, int(BASE_TILE_W * state.zoom))
        curr_tile_h = max(16, int(BASE_TILE_H * state.zoom))
        map_center_col = (len(RAW_GRID[0]) - 1) / 2 if RAW_GRID else 0
        map_center_row = (len(RAW_GRID) - 1) / 2
        default_ox = VIEWPORT_CENTER_X - int(map_center_col * curr_tile_w)
        default_oy = VIEWPORT_CENTER_Y - int(map_center_row * curr_tile_h)
        origin_x = default_ox + state.cam_pan_x
        origin_y = default_oy + state.cam_pan_y

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEWHEEL:
                r_panel_rect = pygame.Rect(PANEL_R_X, PANEL_Y, PANEL_R_W, PANEL_H)
                l_panel_rect = pygame.Rect(PANEL_L_X, PANEL_Y, PANEL_L_W, PANEL_H)
                if r_panel_rect.collidepoint(mouse_pos) and state.right_tab == "fiefs":
                    if event.y > 0:
                        state.fief_page = max(0, state.fief_page - 1)
                    elif event.y < 0:
                        state.fief_page += 1
                elif l_panel_rect.collidepoint(mouse_pos) and state.left_tab == "vassals":
                    if event.y > 0:
                        state.vassal_page = max(0, state.vassal_page - 1)
                    elif event.y < 0:
                        state.vassal_page += 1
                elif l_panel_rect.collidepoint(mouse_pos) and state.left_tab == "demesne":
                    if event.y > 0:
                        state.demesne_page = max(0, state.demesne_page - 1)
                    elif event.y < 0:
                        state.demesne_page += 1
                elif l_panel_rect.collidepoint(mouse_pos) and state.left_tab == "laws":
                    if event.y > 0:
                        state.laws_page = max(0, state.laws_page - 1)
                    elif event.y < 0:
                        state.laws_page += 1
                elif l_panel_rect.collidepoint(mouse_pos) and state.left_tab == "economy":
                    if event.y > 0:
                        state.economy_vassal_page = max(0, state.economy_vassal_page - 1)
                    elif event.y < 0:
                        state.economy_vassal_page += 1
                elif map_viewport.collidepoint(mouse_pos):
                    old_zoom = state.zoom
                    zoom_delta = 0.12 * event.y
                    new_zoom = max(state.min_zoom, min(state.max_zoom, round(state.zoom + zoom_delta, 2)))
                    if new_zoom != old_zoom:
                        old_tw = max(18, int(BASE_TILE_W * old_zoom))
                        old_th = max(16, int(BASE_TILE_H * old_zoom))
                        old_ox = (VIEWPORT_CENTER_X - int(map_center_col * old_tw)) + state.cam_pan_x
                        old_oy = (VIEWPORT_CENTER_Y - int(map_center_row * old_th)) + state.cam_pan_y
                        
                        mx, my = mouse_pos
                        gc = (mx - old_ox) / old_tw
                        gr = (my - old_oy) / old_th
                        
                        new_tw = max(18, int(BASE_TILE_W * new_zoom))
                        new_th = max(16, int(BASE_TILE_H * new_zoom))
                        new_def_x = VIEWPORT_CENTER_X - int(map_center_col * new_tw)
                        new_def_y = VIEWPORT_CENTER_Y - int(map_center_row * new_th)
                        
                        new_ox = mx - gc * new_tw
                        new_oy = my - gr * new_th
                        state.cam_pan_x = int(new_ox - new_def_x)
                        state.cam_pan_y = int(new_oy - new_def_y)
                        state.zoom = new_zoom

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
                    box_start = event.pos
                    box_end   = event.pos
                elif event.button == 2:
                    state.is_panning = True
                    state.pan_start_mouse = event.pos
                    state.pan_start_cam = (state.cam_pan_x, state.cam_pan_y)
                elif event.button == 3:
                    right_clicked = True

            elif event.type == pygame.MOUSEMOTION:
                if box_start:
                    box_end = event.pos
                if state.is_panning:
                    dx = event.pos[0] - state.pan_start_mouse[0]
                    dy = event.pos[1] - state.pan_start_mouse[1]
                    state.cam_pan_x = state.pan_start_cam[0] + dx
                    state.cam_pan_y = state.pan_start_cam[1] + dy

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    state.is_panning = False
                if event.button == 1 and box_start:
                    x1, y1 = box_start
                    x2, y2 = box_end
                    sel_rect = pygame.Rect(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
                    if sel_rect.width > 5 or sel_rect.height > 5:
                        state.selected_army_ids = []
                        for a in state.armies:
                            if a.owner == state.player_id:
                                tc, tr = getattr(a, "tile", get_province_capital_tile(a.province))
                                ax = origin_x + (tc * curr_tile_w) + (curr_tile_w // 2)
                                ay = origin_y + (tr * curr_tile_h) + (curr_tile_h // 2)
                                if a.is_moving and getattr(a, "next_tile", None):
                                    nc, nr = a.next_tile
                                    nx = origin_x + (nc * curr_tile_w) + (curr_tile_w // 2)
                                    ny = origin_y + (nr * curr_tile_h) + (curr_tile_h // 2)
                                    pct = a.move_progress / 100.0
                                    ax = int(ax + (nx - ax) * pct)
                                    ay = int(ay + (ny - ay) * pct)
                                badge_rect = pygame.Rect(ax - curr_tile_w, ay - curr_tile_h, curr_tile_w * 2, int(curr_tile_h * 1.5))
                                if sel_rect.colliderect(badge_rect):
                                    state.selected_army_ids.append(a.id)
                        if state.selected_army_ids:
                            state.selected_army_id = state.selected_army_ids[0]
                    box_start = None
                    box_end   = None

            elif event.type == pygame.KEYDOWN:
                # 1. Handle Universal Rename Keyboard Input
                if getattr(state, "rename_modal", None) and state.rename_modal.get("active"):
                    if event.key == pygame.K_ESCAPE:
                        state.rename_modal = None
                    elif event.key == pygame.K_RETURN:
                        state.commit_rename()
                    elif event.key == pygame.K_BACKSPACE:
                        state.rename_modal["text"] = state.rename_modal["text"][:-1]
                    else:
                        if len(event.unicode) > 0 and event.unicode.isprintable() and len(state.rename_modal.get("text", "")) < 32:
                            state.rename_modal["text"] += event.unicode
                    continue

                # 2. Handle Split Modal Keyboard Input
                if getattr(state, "split_army_target_id", None):
                    if event.key == pygame.K_ESCAPE:
                        state.split_army_target_id = None
                        state.split_selected_units = set()
                    continue

                is_popup_open = bool(state.vassal_build_requests or state.granting_fief_id or state.inspecting_vassal or state.inspecting_ruler or state.vassal_build_confirm)
                if is_popup_open:
                    if event.key == pygame.K_ESCAPE:
                        if state.inspecting_ruler:
                            state.inspecting_ruler = None
                        elif state.inspecting_vassal:
                            state.inspecting_vassal = None
                        elif state.granting_fief_id:
                            state.granting_fief_id = None
                        elif state.vassal_build_confirm:
                            state.vassal_build_confirm = None
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                        state.pre_popup_speed = int(event.unicode)
                else:
                    if event.key == pygame.K_SPACE:
                        state.speed = 0 if state.speed > 0 else 3
                    elif event.key == pygame.K_1:
                        state.speed = 1
                    elif event.key == pygame.K_2:
                        state.speed = 2
                    elif event.key == pygame.K_3:
                        state.speed = 3
                    elif event.key == pygame.K_4:
                        state.speed = 4
                    elif event.key == pygame.K_5:
                        state.speed = 5
                    elif event.key == pygame.K_r:
                        state.raise_all_levies()
                    elif event.key == pygame.K_m:
                        if state.selected_province:
                            state.rally_all_armies_to(state.selected_province)
                    elif event.key == pygame.K_b:
                        state.build_mode = not state.build_mode
                    elif event.key == pygame.K_t:
                        state.build_orientation = "V" if state.build_orientation == "H" else "H"
                    elif event.key == pygame.K_ESCAPE:
                        if state.build_mode:
                            state.build_mode = False
                        else:
                            state.selected_army_ids = []
                            state.selected_army_id  = None
                    elif event.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()

        is_popup_active = bool(state.vassal_build_requests or state.granting_fief_id or state.inspecting_vassal or state.inspecting_ruler or state.vassal_build_confirm or getattr(state, 'subjugation_event', None))
        
        # CK2 Style: Floating moveable popups; game continues running in background at state.speed!
        modal_mouse_clicked = mouse_clicked
        active_modal_rect = getattr(state, "active_modal_rect", None)
        if is_popup_active and active_modal_rect and active_modal_rect.collidepoint(mouse_pos):
            mouse_clicked = False
            box_start = None
            box_end = None
            right_clicked = False

        keys = pygame.key.get_pressed()
        pan_step = int(12 / max(0.5, state.zoom))
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            state.cam_pan_x += pan_step
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            state.cam_pan_x -= pan_step
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            state.cam_pan_y += pan_step
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            state.cam_pan_y -= pan_step

        # Tactical right-clicks and march orders are handled authoritatively in render_map_view with pixel-perfect hitboxes

        if state.speed > 0:
            state.tick_timer += dt
            tick_interval = state.speed_factors.get(state.speed, 500)
            if state.tick_timer >= tick_interval:
                state.advance_day()
                state.tick_timer = 0

        # Background
        screen.fill(COLOR_BG)

        # 1. Top Header Bar
        render_header(screen, state, mouse_pos, mouse_clicked, is_popup_active, fonts, icons)

        # 2. Left Panel
        render_left_panel(screen, state, mouse_pos, mouse_clicked, fonts, portrait_cache, coa_cache)

        # 3. Center Map Viewport
        ticks = pygame.time.get_ticks()
        render_map_view(screen, state, mouse_pos, mouse_clicked, right_clicked, mouse_down, fonts, banner_cloth_large, banner_cloth_small, ticks=ticks)

        # 4. Right Panel
        render_right_panel(screen, state, mouse_pos, mouse_clicked, fonts, coa_cache, icons=icons, box_start=box_start, box_end=box_end)

        # 5. Modals & Dossiers
        render_modals(screen, state, mouse_pos, modal_mouse_clicked, fonts, portrait_cache, coa_cache)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_game()
