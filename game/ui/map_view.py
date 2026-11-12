"""
Center Map Viewport and Multi-Pass Renderer Component
"""
import math
import random
import pygame
from game.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_OCEAN, COLOR_PANEL_BORDER,
    COLOR_GOLD, COLOR_TEXT_WHITE, COLOR_TEXT_MUTED,
    COLOR_TEXT_RED, COLOR_TEXT_GREEN, BASE_TILE_W, BASE_TILE_H,
    VIEWPORT_CENTER_X, VIEWPORT_CENTER_Y,
    MAP_VIEWPORT_X, MAP_VIEWPORT_W, PANEL_Y, PANEL_H
)
from game.data.provinces import PROVINCES, PROVINCE_FACTION_COLORS, get_province_color
from game.data.characters import CHARACTERS, get_color, get_short_name, get_display_name
from game.data.buildings import BUILDING_SPECS
from game.core.map import (
    prov_grid_centroids,
    RAW_GRID,
    CELL_TO_PROV, PROV_TO_TILES, PROV_CAPITAL_TILES,
    get_province_capital_tile, find_shortest_tile_path, TILE_ADJACENCY
)
from game.core.assets import (
    prov_flag_cache,
    draw_waving_banner, get_scaled_banner_cloth, SUB_FLAG_OFFSETS
)
from game.systems.economy import get_all_settlement_holdings, sync_province_holdings_stats
from game.systems.military import is_province_contested


_WAGON_SPRITE_CACHE = {}

def get_supply_wagon_sprite(owner_id, is_player, facing_left, target_w=32, target_h=24):
    key = (owner_id, is_player, facing_left, target_w, target_h)
    if key in _WAGON_SPRITE_CACHE:
        return _WAGON_SPRITE_CACHE[key]

    w, h = 32, 24
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    # Faction colors derived from character data
    if is_player:
        col_accent = get_color(owner_id, (215, 45, 45))
        col_trim = (245, 210, 60)        # Gold
    else:
        col_accent = get_color(owner_id, (100, 95, 110))
        col_trim = (180, 180, 180)

    col_wood = (125, 80, 40)
    col_dark_wood = (80, 48, 22)
    col_canopy = (235, 225, 205)
    col_ox = (135, 90, 55)

    # Draw Draft Beast in front (facing right by default)
    # Beast body
    pygame.draw.ellipse(surf, col_ox, (19, 10, 11, 7))
    pygame.draw.ellipse(surf, (115, 75, 45), (25, 8, 6, 6))  # Head
    pygame.draw.line(surf, (50, 30, 15), (22, 17), (22, 21), 2)  # Legs
    pygame.draw.line(surf, (50, 30, 15), (27, 17), (27, 21), 2)

    # Wagon Hitch / Shaft
    pygame.draw.line(surf, (70, 45, 20), (14, 15), (20, 15), 2)

    # Wagon Bed / Box
    pygame.draw.rect(surf, col_wood, (2, 11, 15, 6))
    pygame.draw.rect(surf, col_dark_wood, (2, 11, 15, 6), 1)

    # Canvas Canopy (Arched)
    pygame.draw.ellipse(surf, col_canopy, (2, 4, 15, 11))
    # Faction decorative stripe on canopy
    pygame.draw.line(surf, col_accent, (4, 9), (15, 9), 2)
    pygame.draw.rect(surf, col_canopy, (2, 9, 15, 4))
    pygame.draw.ellipse(surf, (195, 180, 155), (2, 4, 15, 11), 1)

    # Spoked Wagon Wheels
    # Rear Wheel
    pygame.draw.circle(surf, col_dark_wood, (5, 18), 4)
    pygame.draw.circle(surf, (160, 110, 60), (5, 18), 3)
    pygame.draw.circle(surf, (50, 35, 20), (5, 18), 1)
    # Front Wheel
    pygame.draw.circle(surf, col_dark_wood, (14, 18), 4)
    pygame.draw.circle(surf, (160, 110, 60), (14, 18), 3)
    pygame.draw.circle(surf, (50, 35, 20), (14, 18), 1)

    if facing_left:
        surf = pygame.transform.flip(surf, True, False)

    if target_w != 32 or target_h != 24:
        surf = pygame.transform.smoothscale(surf, (target_w, target_h))

    _WAGON_SPRITE_CACHE[key] = surf
    return surf
_HORSE_SPRITE_CACHE = {}

def get_horse_courier_sprite(owner_id, is_player, facing_left, frame_idx, target_w=32, target_h=24):
    key = (owner_id, is_player, facing_left, frame_idx, target_w, target_h)
    if key in _HORSE_SPRITE_CACHE:
        return _HORSE_SPRITE_CACHE[key]

    base_key = (owner_id, is_player, facing_left, frame_idx, 32, 24)
    if base_key in _HORSE_SPRITE_CACHE:
        base_surf = _HORSE_SPRITE_CACHE[base_key]
    else:
        w, h = 32, 24
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        anim_phase = (frame_idx / 12.0) * (math.pi * 2)
        bob = int(math.sin(anim_phase * 2) * 1.5)

        # Realm & faction palette
        if is_player:
            col_horse = (175, 125, 75)      # Chestnut
            col_mane = (75, 45, 20)
            col_rider = get_color(owner_id, (215, 45, 45))
            col_trim = (245, 210, 60)       # Gold
        else:
            col_horse = (140, 130, 120)
            col_mane = (60, 55, 50)
            col_rider = get_color(owner_id, (90, 85, 100))
            col_trim = (200, 200, 200)

        col_skin = (235, 190, 150)
        cx = 16
        cy = 13 + bob

        # Galloping leg swings
        f_leg = math.sin(anim_phase) * 5
        b_leg = -math.sin(anim_phase) * 5

        # 1. Back legs (shadowed behind body)
        dark_horse = (max(0, col_horse[0] - 40), max(0, col_horse[1] - 40), max(0, col_horse[2] - 30))
        pygame.draw.line(surf, dark_horse, (cx - 7, cy + 2), (cx - 10 + int(b_leg), cy + 8), 2)
        pygame.draw.line(surf, dark_horse, (cx + 5, cy + 2), (cx + 9 + int(f_leg), cy + 8), 2)

        # 2. Tail (flowing back)
        tail_wave = math.sin(anim_phase + 1.0) * 2.5
        pygame.draw.line(surf, col_mane, (cx - 9, cy - 1), (cx - 14, cy + int(tail_wave)), 2)
        pygame.draw.line(surf, col_mane, (cx - 9, cy), (cx - 15, cy + 3 + int(tail_wave)), 2)

        # 3. Horse torso
        pygame.draw.ellipse(surf, col_horse, (cx - 9, cy - 4, 16, 9))

        # 4. Neck & head
        pygame.draw.polygon(surf, col_horse, [
            (cx + 3, cy - 2),
            (cx + 7, cy - 8),
            (cx + 12, cy - 7),
            (cx + 13, cy - 4),
            (cx + 8, cy + 1)
        ])
        # Ears & mane
        pygame.draw.polygon(surf, col_horse, [(cx + 9, cy - 8), (cx + 11, cy - 12), (cx + 12, cy - 8)])
        pygame.draw.line(surf, col_mane, (cx + 4, cy - 4), (cx + 6, cy - 7), 2)
        pygame.draw.line(surf, col_mane, (cx + 6, cy - 6), (cx + 8, cy - 9), 2)

        # 5. Front legs
        pygame.draw.line(surf, col_horse, (cx - 6, cy + 2), (cx - 11 - int(b_leg), cy + 9), 2)
        pygame.draw.line(surf, col_horse, (cx + 6, cy + 2), (cx + 12 - int(f_leg), cy + 9), 2)

        # 6. Courier Rider
        pygame.draw.ellipse(surf, col_rider, (cx - 4, cy - 9, 8, 8))
        # Cape flutter
        pygame.draw.polygon(surf, col_rider, [(cx - 4, cy - 7), (cx - 9, cy - 4 + int(tail_wave)), (cx - 3, cy - 3)])
        # Helmet & face
        pygame.draw.circle(surf, col_skin, (cx + 1, cy - 10), 3)
        pygame.draw.circle(surf, col_trim, (cx + 1, cy - 11), 3)
        # Reins
        pygame.draw.line(surf, (60, 40, 20), (cx + 2, cy - 6), (cx + 11, cy - 4), 1)

        if facing_left:
            surf = pygame.transform.flip(surf, True, False)

        base_surf = surf
        _HORSE_SPRITE_CACHE[base_key] = base_surf

    if (target_w, target_h) != (32, 24):
        final_surf = pygame.transform.smoothscale(base_surf, (target_w, target_h))
    else:
        final_surf = base_surf

    _HORSE_SPRITE_CACHE[key] = final_surf
    return final_surf

def render_map_view(screen, state, mouse_pos, mouse_clicked, right_clicked, mouse_down, fonts, banner_cloth_large, banner_cloth_small, ticks=0):
    raw_grid = RAW_GRID
    cell_to_prov = CELL_TO_PROV
    font_xs = fonts["xs"]
    font_sm = fonts["sm"]
    font_md = fonts["md"]
    font_lg = fonts["lg"]

    curr_tile_w = max(18, int(BASE_TILE_W * state.zoom))
    curr_tile_h = max(16, int(BASE_TILE_H * state.zoom))
    map_center_col = (len(raw_grid[0]) - 1) / 2 if raw_grid else 0
    map_center_row = (len(raw_grid) - 1) / 2
    default_ox = VIEWPORT_CENTER_X - int(map_center_col * curr_tile_w)
    default_oy = VIEWPORT_CENTER_Y - int(map_center_row * curr_tile_h)
    origin_x = default_ox + state.cam_pan_x
    origin_y = default_oy + state.cam_pan_y

    font_banner = fonts.get("banner", font_lg)
    def get_prov_anchor(pid):
        if pid not in prov_grid_centroids:
            return (0, 0)
        gc, gr = prov_grid_centroids[pid]
        return (int(origin_x + gc * curr_tile_w + curr_tile_w / 2),
                int(origin_y + gr * curr_tile_h + curr_tile_h / 2))
    province_anchors = {pid: get_prov_anchor(pid) for pid in prov_grid_centroids}

    # 3. CENTER: TERRITORY BALANCE & MAP
    # ---------------------------------------------------------
    map_bg_rect = pygame.Rect(MAP_VIEWPORT_X, PANEL_Y, MAP_VIEWPORT_W, PANEL_H)
    pygame.draw.rect(screen, COLOR_OCEAN, map_bg_rect, border_radius=6)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, map_bg_rect, 2, border_radius=6)
    
    # Floating Zoom HUD rect anchor
    bar_y = PANEL_Y + 12
    bar_h = 24
    hud_w, hud_h = 36, 118
    hud_x, hud_y = map_bg_rect.right - 48, bar_y + bar_h + 12
    hud_rect = pygame.Rect(hud_x, hud_y, hud_w, hud_h)
    
    # Clip all map rendering inside the map viewport
    screen.set_clip(map_bg_rect)
    
    state.hovered_province = None
    
    # -----------------------------------------------------------
    # PASS 1: Fill all land tiles (full tile, no gap = seamless)
    # -----------------------------------------------------------
    for r, row in enumerate(raw_grid):
        for c, ch in enumerate(row):
            cell_x = origin_x + (c * curr_tile_w)
            cell_y = origin_y + (r * curr_tile_h)
            cell_rect = pygame.Rect(cell_x, cell_y, curr_tile_w, curr_tile_h)
    
            if ch == ".":
                # Ocean dashes
                if (r + c) % 7 == 0:
                    pygame.draw.line(screen, (28, 48, 76),
                                     (cell_x + 4, cell_y + 12), (cell_x + 12, cell_y + 12))
                continue
    
            prov_id  = cell_to_prov.get((c, r))
            prov_info = PROVINCES.get(prov_id)
            owner = prov_info.get("owner") if prov_info else None
            col = PROVINCE_FACTION_COLORS.get(owner, {}).get(prov_id)
            if not col:
                col = tuple(prov_info["color"]) if prov_info else (150, 150, 150)
    
            is_hovered  = cell_rect.collidepoint(mouse_pos) and map_bg_rect.collidepoint(mouse_pos) and not hud_rect.collidepoint(mouse_pos)
            is_selected = (prov_id == state.selected_province)
    
            if is_hovered:
                state.hovered_province = prov_id
                col = (min(255, col[0] + 45), min(255, col[1] + 45), min(255, col[2] + 45))
    
            # Draw full tile (no 1-px gap → seamless within province)
            pygame.draw.rect(screen, col, (cell_x, cell_y, curr_tile_w, curr_tile_h))

            # Vassal territory highlight (when hovering a vassal card in left panel)
            if hasattr(state, 'hovered_vassal_tiles') and (c, r) in state.hovered_vassal_tiles:
                hl_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                hl_surf.fill((255, 255, 100, 100))  # Bright yellow semi-transparent
                screen.blit(hl_surf, (cell_x, cell_y))
                pygame.draw.rect(screen, (255, 230, 50), (cell_x, cell_y, curr_tile_w, curr_tile_h), 2)
    
            # Contested Province Hatching (Diagonal Striped Hazard Pattern ala CK2)
            is_contested, occupier = is_province_contested(state, prov_id)
            if is_contested:
                stripe_col = get_color(occupier, (220, 50, 50))
                stripe_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                for off in range(-curr_tile_h, curr_tile_w + curr_tile_h, 8):
                    pygame.draw.line(stripe_surf, (*stripe_col, 140), (off, 0), (off + curr_tile_h, curr_tile_h), 2)
                screen.blit(stripe_surf, (cell_x, cell_y))
    
            # Subtle inner highlight (top/left edges only within same province)
            pygame.draw.line(screen,
                (min(255, col[0]+18), min(255, col[1]+18), min(255, col[2]+18)),
                (cell_x, cell_y), (cell_x + curr_tile_w - 1, cell_y))
            pygame.draw.line(screen,
                (min(255, col[0]+18), min(255, col[1]+18), min(255, col[2]+18)),
                (cell_x, cell_y), (cell_x, cell_y + curr_tile_h - 1))
    
            # Visual Hover Feedback while Editing Fief Boundaries
            if state.editing_fief_id and prov_id == state.selected_province and is_hovered:
                f_edit = state.fiefs.get(state.editing_fief_id)
                t_coord = (c, r)
                if f_edit and t_coord not in f_edit.get("tiles", []):
                    occupied_f = next((other_f for other_fid, other_f in state.fiefs.items()
                                       if other_fid != state.editing_fief_id and other_f.get("province") == prov_id and t_coord in other_f.get("tiles", [])), None)
                    if occupied_f:
                        # Occupied by another fief: red locked warning tint
                        warn_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                        warn_surf.fill((220, 50, 50, 110))
                        screen.blit(warn_surf, (cell_x, cell_y))
                        pygame.draw.rect(screen, (255, 80, 80), (cell_x, cell_y, curr_tile_w, curr_tile_h), 2)
                    else:
                        # Unclaimed: green claimable preview tint
                        free_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                        free_surf.fill((60, 220, 100, 110))
                        screen.blit(free_surf, (cell_x, cell_y))
                        pygame.draw.rect(screen, (100, 255, 120), (cell_x, cell_y, curr_tile_w, curr_tile_h), 2)
    
            if mouse_clicked and is_hovered:
                if state.editing_fief_id and prov_id == state.selected_province:
                    f_edit = state.fiefs.get(state.editing_fief_id)
                    if f_edit:
                        t_coord = (c, r)
                        if t_coord in f_edit["tiles"]:
                            f_edit["tiles"].remove(t_coord)
                            state.logs.append(f"Removed tile {t_coord} from {f_edit['name']} ({len(f_edit['tiles'])} tiles remaining).")
                        else:
                            # Check if tile already belongs to another fief in this province!
                            claimed_by = None
                            for other_fid, other_f in state.fiefs.items():
                                if other_fid != state.editing_fief_id and other_f.get("province") == prov_id:
                                    if t_coord in other_f.get("tiles", []):
                                        claimed_by = other_f
                                        break
                            if claimed_by:
                                state.logs.append(f"Cannot claim tile {t_coord}: Already belongs to '{claimed_by['name']}'! Fiefs cannot overlap.")
                            else:
                                f_edit["tiles"].append(t_coord)
                                state.logs.append(f"Assigned unclaimed tile {t_coord} to {f_edit['name']} ({len(f_edit['tiles'])} tiles)!")
                elif not state.build_mode:
                    # CK2 style: Left-clicking an empty tile inspects that province and unselects armies.
                    # If this tile contains player armies, do NOT clear army selection so unit clicks work!
                    state.selected_province = prov_id
                    has_armies_here = any(a.owner == state.player_id and getattr(a, "tile", None) == (c, r) and a.troops > 0 for a in state.armies)
                    if not has_armies_here:
                        state.selected_army_id = None
                        state.selected_army_ids = []
                    state.selected_settlement = None
                    state.selected_vassal_idx = None
                    state.fief_page = 0
    
    # -----------------------------------------------------------
    # PASS 2: Draw Fiefdom Sub-divisions & Interior Borders
    #         (Only highlight fiefs of the selected province, or when editing/selecting a fief)
    # -----------------------------------------------------------
    def get_prov(col_i, row_i):
        return cell_to_prov.get((col_i, row_i))
    
    fief_palette = [(120, 200, 255), (255, 175, 90), (190, 130, 255), (90, 255, 190), (255, 120, 150), (240, 220, 90)]
    for f_idx, (fid, fdata) in enumerate(state.fiefs.items()):
        f_color = fief_palette[f_idx % len(fief_palette)]
        is_f_sel = (state.selected_fief_id == fid)
        is_f_edit = (state.editing_fief_id == fid)
        is_cur_prov = (fdata.get("province") == state.selected_province)
        f_prov = fdata.get("province")
        f_tiles_set = set(fdata["tiles"])
    
        # Keep unselected provinces visually clean and uncluttered so provincial boundaries are prominent
        if not (is_f_edit or is_f_sel or is_cur_prov):
            continue
    
        for (fc, fr) in fdata["tiles"]:
            fx = origin_x + (fc * curr_tile_w)
            fy = origin_y + (fr * curr_tile_h)
            
            # Fief fill tint
            if is_f_edit:
                f_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                f_surf.fill((255, 220, 50, 105))
                screen.blit(f_surf, (fx, fy))
            elif is_f_sel:
                f_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                f_surf.fill((100, 255, 120, 85))
                screen.blit(f_surf, (fx, fy))
            elif is_cur_prov and state.right_tab == "fiefs":
                f_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                fill_col = (*f_color, 45) if fdata.get("holder") else (235, 195, 100, 45)
                f_surf.fill(fill_col)
                screen.blit(f_surf, (fx, fy))
    
            # Fief border:
            # CRITICAL: Only draw interior fief borders if the neighbor tile belongs to the SAME province!
            # If neighbor is outside province, DO NOT draw here; the bold Province Boundary will frame it!
            edge_col = (255, 225, 60) if is_f_edit else ((100, 255, 120) if is_f_sel else (f_color if state.right_tab == "fiefs" else (180, 200, 225)))
            edge_w = 3 if is_f_edit else (2 if is_f_sel else 1)
    
            # Right edge: only if neighbor is in same province but not in this fief
            if get_prov(fc + 1, fr) == f_prov and (fc + 1, fr) not in f_tiles_set:
                pygame.draw.line(screen, edge_col, (fx + curr_tile_w - 1, fy), (fx + curr_tile_w - 1, fy + curr_tile_h - 1), edge_w)
            # Left edge
            if get_prov(fc - 1, fr) == f_prov and (fc - 1, fr) not in f_tiles_set:
                pygame.draw.line(screen, edge_col, (fx, fy), (fx, fy + curr_tile_h - 1), edge_w)
            # Bottom edge
            if get_prov(fc, fr + 1) == f_prov and (fc, fr + 1) not in f_tiles_set:
                pygame.draw.line(screen, edge_col, (fx, fy + curr_tile_h - 1), (fx + curr_tile_w - 1, fy + curr_tile_h - 1), edge_w)
            # Top edge
            if get_prov(fc, fr - 1) == f_prov and (fc, fr - 1) not in f_tiles_set:
                pygame.draw.line(screen, edge_col, (fx, fy), (fx + curr_tile_w - 1, fy), edge_w)
    
    # -----------------------------------------------------------
    # PASS 2.5: Draw Outer Province Boundaries Framing All Land
    #           (Bold, Crisp, High-Contrast Provincial Borders)
    # -----------------------------------------------------------
    # Stage 1: Prominent dark borders (3px) separating all provinces & coasts
    for r, row in enumerate(raw_grid):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            cell_x = origin_x + (c * curr_tile_w)
            cell_y = origin_y + (r * curr_tile_h)
            prov_id = get_prov(c, r)
    
            # Right edge
            n_right = get_prov(c + 1, r)
            if n_right != prov_id:
                b_col = (10, 14, 22) if n_right is None else (18, 24, 34)
                pygame.draw.line(screen, b_col, (cell_x + curr_tile_w - 1, cell_y), (cell_x + curr_tile_w - 1, cell_y + curr_tile_h - 1), 3)
            # Bottom edge
            n_bot = get_prov(c, r + 1)
            if n_bot != prov_id:
                b_col = (10, 14, 22) if n_bot is None else (18, 24, 34)
                pygame.draw.line(screen, b_col, (cell_x, cell_y + curr_tile_h - 1), (cell_x + curr_tile_w - 1, cell_y + curr_tile_h - 1), 3)
            # Left edge
            n_left = get_prov(c - 1, r)
            if n_left != prov_id:
                b_col = (10, 14, 22) if n_left is None else (18, 24, 34)
                pygame.draw.line(screen, b_col, (cell_x, cell_y), (cell_x, cell_y + curr_tile_h - 1), 3)
            # Top edge
            n_top = get_prov(c, r - 1)
            if n_top != prov_id:
                b_col = (10, 14, 22) if n_top is None else (18, 24, 34)
                pygame.draw.line(screen, b_col, (cell_x, cell_y), (cell_x + curr_tile_w - 1, cell_y), 3)
    
    # Stage 2: Highlighting hovered and selected provinces on top with glowing borders
    for target_pid, is_sel, b_col, b_w in [
        (state.hovered_province, False, (225, 235, 255), 2),
        (state.selected_province, True, (255, 215, 60), 3)
    ]:
        if not target_pid:
            continue
        for r, row in enumerate(raw_grid):
            for c, ch in enumerate(row):
                if ch == ".":
                    continue
                if get_prov(c, r) != target_pid:
                    continue
                cell_x = origin_x + (c * curr_tile_w)
                cell_y = origin_y + (r * curr_tile_h)
    
                # Right edge
                if get_prov(c + 1, r) != target_pid:
                    pygame.draw.line(screen, b_col, (cell_x + curr_tile_w - 1, cell_y), (cell_x + curr_tile_w - 1, cell_y + curr_tile_h - 1), b_w)
                # Bottom edge
                if get_prov(c, r + 1) != target_pid:
                    pygame.draw.line(screen, b_col, (cell_x, cell_y + curr_tile_h - 1), (cell_x + curr_tile_w - 1, cell_y + curr_tile_h - 1), b_w)
                # Left edge
                if get_prov(c - 1, r) != target_pid:
                    pygame.draw.line(screen, b_col, (cell_x, cell_y), (cell_x, cell_y + curr_tile_h - 1), b_w)
                # Top edge
                if get_prov(c, r - 1) != target_pid:
                    pygame.draw.line(screen, b_col, (cell_x, cell_y), (cell_x + curr_tile_w - 1, cell_y), b_w)
    
    # -----------------------------------------------------------
    # PASS 3: Draw Built Settlements / Cities (Unified Holdings)
    # -----------------------------------------------------------
    unified_holdings = get_all_settlement_holdings(state)
    for h in unified_holdings:
        min_c, max_c = h["min_c"], h["max_c"]
        min_r, max_r = h["min_r"], h["max_r"]
        orient = h["orient"]
        h_tiles = h["tiles"]
        sdata = h["data"]
    
        sx = origin_x + (min_c * curr_tile_w)
        sy = origin_y + (min_r * curr_tile_h)
        total_w = (max_c - min_c + 1) * curr_tile_w
        total_h = (max_r - min_r + 1) * curr_tile_h
    
        is_city_hover = pygame.Rect(sx, sy, total_w, total_h).collidepoint(mouse_pos) and map_bg_rect.collidepoint(mouse_pos) and not hud_rect.collidepoint(mouse_pos)
        is_city_sel = (state.selected_settlement in h_tiles)
    
        # Center the city castle inside the holding with comfortable padding
        # so the terrain color, grid lines, and fief borders are clearly visible around it!
        if orient == "H":
            pad_x = max(5, int(total_w * 0.14))
            pad_y = max(3, int(total_h * 0.16))
        elif orient == "V":
            pad_x = max(3, int(total_w * 0.16))
            pad_y = max(5, int(total_h * 0.14))
        else:
            pad_x = max(4, int(total_w * 0.16))
            pad_y = max(4, int(total_h * 0.16))
    
        cw = total_w - 2 * pad_x
        ch = total_h - 2 * pad_y
        cx = sx + pad_x
        cy = sy + pad_y
    
        base_rect = pygame.Rect(cx, cy, cw, ch)
    
        # Drop shadow on terrain
        shadow_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 80))
        screen.blit(shadow_surf, (cx + 2, cy + 2))
    
        # City Foundation Block with Stone Ramparts
        city_bg = (60, 68, 86) if is_city_hover else (42, 48, 62)
        pygame.draw.rect(screen, city_bg, base_rect, border_radius=3)
        
        # Border trim (Gold for Crown Demesne, Green for Selected, Slate/Silver for Vassals)
        if is_city_sel:
            border_city_col = (100, 255, 120)
        elif sdata.get("is_crown_demesne"):
            border_city_col = COLOR_GOLD
        else:
            border_city_col = (175, 190, 210)
        pygame.draw.rect(screen, border_city_col, base_rect, 2 if is_city_sel else 1, border_radius=3)
    
        tw, th = cw - 4, ch - 4
        tx, ty = cx + 2, cy + 2
    
        h_type = sdata.get("type", "fort" if len(h_tiles) == 2 else "city")
        if h_type == "town":
            h_type = "city"
    
        if h_type == "city":
            # Medieval Commercial City / Market Burgh (Warm Timber & Terracotta Gable Roof)
            # Foundation stone & half-timbered walls
            pygame.draw.rect(screen, (150, 138, 122), (tx + 1, ty + int(th * 0.38), tw - 2, th - int(th * 0.38)))
            pygame.draw.line(screen, (60, 45, 30), (tx + 1, ty + int(th * 0.38)), (tx + tw - 1, ty + int(th * 0.38)), 1)
            pygame.draw.line(screen, (60, 45, 30), (tx + tw // 2, ty + int(th * 0.38)), (tx + tw // 2, ty + th - 1), 1)
            # Peaked terracotta roof
            roof_poly = [(tx + tw // 2, ty - 1), (tx, ty + int(th * 0.4)), (tx + tw, ty + int(th * 0.4))]
            pygame.draw.polygon(screen, (185, 78, 42), roof_poly)
            pygame.draw.polygon(screen, (220, 105, 55), roof_poly, 1)
            # Golden weathervane finial
            pygame.draw.rect(screen, COLOR_GOLD, (tx + tw // 2 - 1, ty - 3, 3, 3))
            # Glowing warm window lights
            w_w, w_h = max(2, int(tw * 0.12)), max(2, int(th * 0.12))
            pygame.draw.rect(screen, (245, 215, 80), (tx + max(2, int(tw * 0.18)), ty + int(th * 0.52), w_w, w_h))
            pygame.draw.rect(screen, (245, 215, 80), (tx + tw - max(2, int(tw * 0.18)) - w_w, ty + int(th * 0.52), w_w, w_h))
            # Market entrance arch
            gate_w = max(3, int(tw * 0.28))
            gate_h = max(3, int(th * 0.3))
            pygame.draw.rect(screen, (25, 20, 16), (tx + tw // 2 - gate_w // 2, ty + th - gate_h, gate_w, gate_h))
    
        elif h_type == "barrack":
            # Sturdy Military Garrison & Fyrd Training Hall
            pygame.draw.rect(screen, (68, 75, 88), (tx + 1, ty + 2, tw - 2, th - 2))
            # Iron battlements / crenellations on roof
            pygame.draw.rect(screen, (88, 96, 110), (tx, ty, 3, 4))
            pygame.draw.rect(screen, (88, 96, 110), (tx + tw - 3, ty, 3, 4))
            pygame.draw.rect(screen, (88, 96, 110), (tx + tw // 2 - 2, ty, 4, 3))
            pygame.draw.rect(screen, (40, 44, 52), (tx, ty + 3, tw, 2))
            # Red military pennant on top pole
            pygame.draw.line(screen, (190, 195, 205), (tx + tw - 3, ty - 6), (tx + tw - 3, ty + 3), 1)
            pygame.draw.polygon(screen, (220, 45, 45), [(tx + tw - 3, ty - 6), (tx + tw + 6, ty - 3), (tx + tw - 3, ty)])
            # Iron-studded door
            gate_w = max(4, int(tw * 0.32))
            gate_h = max(4, int(th * 0.38))
            pygame.draw.rect(screen, (28, 30, 36), (tx + tw // 2 - gate_w // 2, ty + th - gate_h, gate_w, gate_h))
            # Golden crossed spears / insignia
            pygame.draw.rect(screen, COLOR_GOLD, (tx + tw // 2 - 2, ty + int(th * 0.28), 4, 3))
            # Level badge if upgraded
            b_lvl = sdata.get("level", 0)
            if b_lvl > 0:
                lvl_badge = font_xs.render(f"L{b_lvl}", True, COLOR_GOLD)
                screen.blit(lvl_badge, (tx + 2, ty + 2))
    
        else: # Fort
            if orient == "H":
                # Grand Castle / Fortified Burgh spanning across 2 horizontal tiles
                curtain_h = max(4, int(th * 0.65))
                pygame.draw.rect(screen, (75, 85, 105), (tx + 1, ty + th - curtain_h, tw - 2, curtain_h))
                
                # Left defensive tower
                tow_w = max(4, int(tw * 0.18))
                pygame.draw.rect(screen, (85, 95, 115), (tx + 1, ty + 1, tow_w, th - 1))
                pygame.draw.rect(screen, COLOR_GOLD, (tx, ty - 1, tow_w + 2, 3))
                pygame.draw.rect(screen, (20, 24, 32), (tx + tow_w // 2 - 1, ty + 4, 2, 4))
                
                # Right defensive tower
                pygame.draw.rect(screen, (85, 95, 115), (tx + tw - tow_w - 1, ty + 1, tow_w, th - 1))
                pygame.draw.rect(screen, COLOR_GOLD, (tx + tw - tow_w - 1, ty - 1, tow_w + 2, 3))
                pygame.draw.rect(screen, (20, 24, 32), (tx + tw - tow_w // 2 - 1, ty + 4, 2, 4))
                
                # Central Great Keep
                keep_w = max(6, int(tw * 0.32))
                keep_x = tx + (tw - keep_w) // 2
                pygame.draw.rect(screen, (100, 112, 134), (keep_x, ty, keep_w, th))
                pygame.draw.rect(screen, COLOR_GOLD, (keep_x, ty - 2, 3, 3))
                pygame.draw.rect(screen, COLOR_GOLD, (keep_x + keep_w // 2 - 2, ty - 3, 4, 4))
                pygame.draw.rect(screen, COLOR_GOLD, (keep_x + keep_w - 3, ty - 2, 3, 3))
                
                # Grand Arch Gatehouse
                gate_w = max(4, int(keep_w * 0.45))
                gate_h = max(4, int(th * 0.42))
                pygame.draw.rect(screen, (20, 24, 32), (tx + tw // 2 - gate_w // 2, ty + th - gate_h, gate_w, gate_h))
    
            elif orient == "V":
                # High Citadel Tower spanning across 2 vertical tiles
                tow_w = tw
                up_h = max(6, int(th * 0.45))
                pygame.draw.rect(screen, (100, 112, 134), (tx + 1, ty + 1, tow_w - 2, up_h))
                pygame.draw.rect(screen, COLOR_GOLD, (tx, ty - 1, 4, 3))
                pygame.draw.rect(screen, COLOR_GOLD, (tx + tow_w - 4, ty - 1, 4, 3))
                pygame.draw.rect(screen, COLOR_GOLD, (tx + tow_w // 2 - 2, ty - 2, 4, 3))
                pygame.draw.rect(screen, (20, 24, 32), (tx + tow_w // 2 - 1, ty + 5, 3, 4))
                pygame.draw.rect(screen, COLOR_GOLD, (tx, ty + up_h, tow_w, 2))
                pygame.draw.rect(screen, (85, 95, 115), (tx + 1, ty + up_h + 2, tow_w - 2, th - up_h - 2))
                gate_w = max(4, int(tow_w * 0.35))
                gate_h = max(4, int(th * 0.25))
                pygame.draw.rect(screen, (20, 24, 32), (tx + tow_w // 2 - gate_w // 2, ty + th - gate_h, gate_w, gate_h))
    
            else:
                # Compact single tile keep
                pygame.draw.rect(screen, (85, 95, 115), (tx + 1, ty + 2, tw - 2, th - 2))
                pygame.draw.rect(screen, COLOR_GOLD, (tx, ty, 3, 4))
                pygame.draw.rect(screen, COLOR_GOLD, (tx + tw - 3, ty, 3, 4))
                pygame.draw.rect(screen, COLOR_GOLD, (tx + tw // 2 - 2, ty - 1, 4, 3))
                gate_w = max(4, int(tw * 0.3))
                gate_h = max(4, int(th * 0.35))
                pygame.draw.rect(screen, (20, 24, 32), (tx + tw // 2 - gate_w // 2, ty + th - gate_h, gate_w, gate_h))
    
        # If holding is occupied by enemy, display conqueror's miniature banner on keep turret!
        if h.get("occupied_by"):
            occ_id = h["occupied_by"]
            occ_key = state.get_realm_capital(occ_id)
            occ_flag = prov_flag_cache.get(occ_key)
            if occ_flag:
                mini_f = pygame.transform.smoothscale(occ_flag, (12, 14))
                screen.blit(mini_f, (cx + cw - 12, cy - 8))
    
        # Click city to inspect settlement details (only when not building or editing fiefs and no army is clicked)!
        has_armies_on_holding = any(a.owner == state.player_id and getattr(a, "tile", None) in h_tiles and a.troops > 0 for a in state.armies)
        if mouse_clicked and is_city_hover and not state.build_mode and not state.editing_fief_id and not has_armies_on_holding:
            state.selected_settlement = h["primary_tile"]
            state.selected_province = h["province"]
            state.selected_army_id = None
            state.selected_army_ids = []
    
    # -----------------------------------------------------------
    # PASS 4: Build Mode Hover & Placement Ghost (Modular Preview)
    # -----------------------------------------------------------
    if state.build_mode and state.selected_province:
        # Determine tile hovered
        mx, my = mouse_pos
        hc = int((mx - origin_x) // curr_tile_w)
        hr = int((my - origin_y) // curr_tile_h)
    
        b_spec = BUILDING_SPECS.get(state.build_type, BUILDING_SPECS["city"])
        b_cost = b_spec["cost"]
        b_tiles_num = b_spec["tiles"]
    
        target_tiles = []
        if b_tiles_num == 1:
            target_tiles = [(hc, hr)]
        else:
            if state.build_orientation == "H":
                target_tiles = [(hc, hr), (hc + 1, hr)]
            else:
                target_tiles = [(hc, hr), (hc, hr + 1)]
    
        # Check validity
        prov_obj = PROVINCES.get(state.selected_province)
        is_valid = True
        invalid_reason = ""
        if not prov_obj or prov_obj["owner"] != state.player_id:
            is_valid = False
            invalid_reason = "Not Player Territory"
        elif state.player["gold"] < b_cost:
            is_valid = False
            invalid_reason = f"Requires {b_cost:,} Gold"
        else:
            for tc, tr in target_tiles:
                if cell_to_prov.get((tc, tr)) != state.selected_province:
                    is_valid = False
                    invalid_reason = "Outside Province"
                    break
                if (tc, tr) in state.settlements:
                    is_valid = False
                    invalid_reason = "Tile Occupied"
                    break
    
        # Fief jurisdiction check
        target_fief = None
        is_vassal_fief = False
        if is_valid:
            tile_fiefs = []
            for tc, tr in target_tiles:
                tf = None
                for f in state.fiefs.values():
                    if (tc, tr) in f.get("tiles", []):
                        tf = f
                        break
                tile_fiefs.append(tf)
    
            if b_tiles_num > 1 and tile_fiefs[0] != tile_fiefs[1]:
                is_valid = False
                invalid_reason = "Across Fief Borders"
            else:
                target_fief = tile_fiefs[0]
                if target_fief:
                    is_crown = (target_fief.get("is_crown_demesne", False) and 
                                (target_fief.get("holder") == state.player["name"] or target_fief.get("holder") is None) and 
                                target_fief.get("vassal_id") is None)
                    if not is_crown:
                        is_vassal_fief = True
    
        # Draw Ghost Box (Continuous 1-tile or 2-tile preview)
        if not is_valid:
            ghost_col = (220, 50, 50, 140)
            border_c = (255, 80, 80)
        elif is_vassal_fief:
            ghost_col = (235, 175, 45, 150)
            border_c = (255, 215, 60)
        else:
            ghost_col = (50, 220, 80, 140)
            border_c = (80, 255, 110)
    
        min_gc = min(tc for tc, tr in target_tiles)
        max_gc = max(tc for tc, tr in target_tiles)
        min_gr = min(tr for tc, tr in target_tiles)
        max_gr = max(tr for tc, tr in target_tiles)
        gx = origin_x + (min_gc * curr_tile_w)
        gy = origin_y + (min_gr * curr_tile_h)
        gw = (max_gc - min_gc + 1) * curr_tile_w
        gh = (max_gr - min_gr + 1) * curr_tile_h
        
        # Preview centered ghost
        pad_x = max(4, int(gw * 0.14))
        pad_y = max(3, int(gh * 0.16))
        cw = gw - 2 * pad_x
        ch = gh - 2 * pad_y
        cx = gx + pad_x
        cy = gy + pad_y
    
        gsurf = pygame.Surface((cw, ch), pygame.SRCALPHA)
        gsurf.fill(ghost_col)
        screen.blit(gsurf, (cx, cy))
        pygame.draw.rect(screen, border_c, (cx, cy, cw, ch), 2, border_radius=3)
    
        # Contextual Ghost Tag / Hint
        tag_label = f"Build {b_spec['name']} ({b_cost}g)"
        if is_valid and is_vassal_fief and target_fief:
            v_holder = target_fief.get("holder", "Vassal")
            v_hint = font_xs.render(f"⚠ Vassal Fief ({v_holder})", True, (255, 235, 120))
            screen.blit(v_hint, (cx, max(0, cy - 16)))
        elif not is_valid and invalid_reason:
            r_hint = font_xs.render(f"✕ {invalid_reason}", True, (255, 140, 140))
            screen.blit(r_hint, (cx, max(0, cy - 16)))
        else:
            t_hint = font_xs.render(tag_label, True, (200, 255, 220))
            screen.blit(t_hint, (cx, max(0, cy - 16)))
    
        # Left click to place
        if mouse_clicked and is_valid:
            if is_vassal_fief and target_fief:
                v_holder = target_fief.get("holder", "Vassal")
                state.vassal_build_confirm = {
                    "target_tiles": list(target_tiles),
                    "province_id": state.selected_province,
                    "fief_id": target_fief["id"],
                    "fief_name": target_fief.get("name", "Vassal Fief"),
                    "vassal_id": target_fief.get("vassal_id"),
                    "vassal_name": v_holder,
                    "cost": b_cost,
                    "build_type": state.build_type
                }
                state.build_mode = False
            else:
                state.player["gold"] -= b_cost
                p_short = prov_obj['name'].split()[0]
                if state.build_type == "city":
                    city_name = f"{p_short} City"
                elif state.build_type == "fort":
                    city_name = f"{p_short} Citadel"
                else:
                    city_name = f"{p_short} Barracks"
    
                state.settlement_id_counter += 1
                s_id = f"settlement_{state.settlement_id_counter}"
                for tc, tr in target_tiles:
                    state.settlements[(tc, tr)] = {
                        "id": s_id,
                        "province": state.selected_province,
                        "type": state.build_type,
                        "name": city_name,
                        "lord": f"{state.player['name']} (Crown Demesne)",
                        "vassal_id": None,
                        "is_crown_demesne": True,
                        "is_crown_fief": True,
                        "level": 0
                    }
                # Ensure these tiles belong to a Crown Fief if not already claimed
                if target_fief is None:
                    state.fief_id_counter += 1
                    fid = f"fief_{state.fief_id_counter}"
                    state.fiefs[fid] = {
                        "id": fid,
                        "province": state.selected_province,
                        "tiles": list(target_tiles),
                        "name": f"Crown Demesne of {p_short}",
                        "holder": state.player["name"],
                        "vassal_id": None,
                        "is_crown_demesne": True
                    }
                sync_province_holdings_stats(state, state.selected_province)
                state.logs.append(f"Constructed Crown {b_spec['name']} in {prov_obj['name']} (-{b_cost}g)!")
                state.build_mode = False
    
    active_player_cap = state.get_realm_capital(state.player_id)
    active_ai_caps = {state.get_realm_capital(cid) for cid in state.get_active_rulers(include_player=False)}

    # Province Name Labels (Medieval Plaque / Banner)
    for pid, (lx, ly) in province_anchors.items():
        p_data = PROVINCES.get(pid)
        if p_data:
            short_name = p_data["name"].split()[0]
            is_player_cap = (pid == active_player_cap)
            is_enemy_cap = (pid in active_ai_caps)
            if is_player_cap or is_enemy_cap:
                short_name = f"★ {short_name}"

            is_sel = (pid == state.selected_province)
            is_hov = (pid == state.hovered_province)
            
            if is_sel:
                txt_col = (255, 220, 60)
            elif is_player_cap:
                txt_col = (255, 230, 130)
            elif is_enemy_cap:
                txt_col = (255, 170, 170)
            elif is_hov:
                txt_col = (225, 235, 255)
            else:
                txt_col = (240, 244, 250)

            txt_surf = font_xs.render(short_name, True, txt_col)
            bw = txt_surf.get_width() + 14
            bh = 18
            bx = lx - bw // 2
            by = ly - bh // 2
            
            plaque_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            plaque_surf.fill((16, 20, 30, 215))
            screen.blit(plaque_surf, (bx, by))
            
            if is_sel:
                border_c = (255, 215, 60)
            elif is_player_cap:
                border_c = (230, 190, 60)
            elif is_enemy_cap:
                border_c = (210, 70, 70)
            elif is_hov:
                border_c = (160, 180, 210)
            else:
                border_c = (55, 70, 95)

            pygame.draw.rect(screen, border_c, (bx, by, bw, bh), 1, border_radius=3)
            screen.blit(txt_surf, (bx + 7, by + 2))
    
    # ---------------------------------------------------------
    # DRAW MOVEMENT ARROWS (before armies, so badges render on top)
    # ---------------------------------------------------------
    import math as _math
    
    def draw_arrow(surface, color, start, end, width=3, head_size=10):
        """Draw a line with an arrowhead at 'end'."""
        if start == end:
            return
        pygame.draw.line(surface, color, start, end, width)
        dx, dy = end[0] - start[0], end[1] - start[1]
        angle = _math.atan2(dy, dx)
        left  = (int(end[0] - head_size * _math.cos(angle - _math.pi/6)),
                 int(end[1] - head_size * _math.sin(angle - _math.pi/6)))
        right = (int(end[0] - head_size * _math.cos(angle + _math.pi/6)),
                 int(end[1] - head_size * _math.sin(angle + _math.pi/6)))
        pygame.draw.polygon(surface, color, [end, left, right])
    
    # ---------------------------------------------------------
    # PASS 3.7: RTS Tactical Destination Reticle when army is selected
    # ---------------------------------------------------------
    if (state.selected_army_id or state.selected_army_ids) and not state.build_mode:
        mx, my = mouse_pos
        if map_bg_rect.collidepoint((mx, my)) and not hud_rect.collidepoint((mx, my)):
            hc = int((mx - origin_x) // curr_tile_w)
            hr = int((my - origin_y) // curr_tile_h)
            if (hc, hr) in cell_to_prov:
                hx = origin_x + hc * curr_tile_w
                hy = origin_y + hr * curr_tile_h
                h_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                h_surf.fill((255, 215, 60, 45))
                screen.blit(h_surf, (hx, hy))
                pygame.draw.rect(screen, (255, 225, 80), (hx, hy, curr_tile_w, curr_tile_h), 1)
                # Corner brackets for tactical RTS reticle
                cs = 5
                pygame.draw.line(screen, COLOR_GOLD, (hx, hy), (hx + cs, hy), 2)
                pygame.draw.line(screen, COLOR_GOLD, (hx, hy), (hx, hy + cs), 2)
                pygame.draw.line(screen, COLOR_GOLD, (hx + curr_tile_w - 1, hy), (hx + curr_tile_w - 1 - cs, hy), 2)
                pygame.draw.line(screen, COLOR_GOLD, (hx + curr_tile_w - 1, hy), (hx + curr_tile_w - 1, hy + cs), 2)
                pygame.draw.line(screen, COLOR_GOLD, (hx, hy + curr_tile_h - 1), (hx + cs, hy + curr_tile_h - 1), 2)
                pygame.draw.line(screen, COLOR_GOLD, (hx, hy + curr_tile_h - 1), (hx, hy + curr_tile_h - 1 - cs), 2)
                pygame.draw.line(screen, COLOR_GOLD, (hx + curr_tile_w - 1, hy + curr_tile_h - 1), (hx + curr_tile_w - 1 - cs, hy + curr_tile_h - 1), 2)
                pygame.draw.line(screen, COLOR_GOLD, (hx + curr_tile_w - 1, hy + curr_tile_h - 1), (hx + curr_tile_w - 1, hy + curr_tile_h - 1 - cs), 2)
    
    # Sub-day frame interpolation for buttery-smooth 60 FPS visual movement
    sub_day = 0.0
    if getattr(state, "speed", 0) > 0:
        interval = state.speed_factors.get(state.speed, 500)
        sub_day = min(1.0, max(0.0, getattr(state, "tick_timer", 0) / float(interval)))

    # ---------------------------------------------------------
    # PASS 3.8: Tactical March Path Arrows (Tile-by-Tile)
    # ---------------------------------------------------------
    for army in state.armies:
        if not army.is_moving or army.in_battle or not getattr(army, "tile_path", None):
            continue
        is_player_army = (army.owner == state.player_id)
        arrow_col = (240, 180, 50) if is_player_army else (80, 130, 220)
    
        # Build waypoints through each tile center in route
        waypoints = []
        cur_tc, cur_tr = getattr(army, "tile", get_province_capital_tile(army.province))
        cur_ax = origin_x + (cur_tc * curr_tile_w) + (curr_tile_w // 2)
        cur_ay = origin_y + (cur_tr * curr_tile_h) + (curr_tile_h // 2)
        if army.is_moving and getattr(army, "next_tile", None):
            nc, nr = army.next_tile
            nx = origin_x + (nc * curr_tile_w) + (curr_tile_w // 2)
            ny = origin_y + (nr * curr_tile_h) + (curr_tile_h // 2)
            # Smooth 60 FPS sub-day position interpolation
            eff_prog = army.move_progress + (sub_day * getattr(army, "move_speed", 100.0))
            pct = min(1.0, max(0.0, eff_prog / 100.0))
            cur_ax = int(cur_ax + (nx - cur_ax) * pct)
            cur_ay = int(cur_ay + (ny - cur_ay) * pct)
        waypoints.append((cur_ax, cur_ay))
    
        for (tc, tr) in army.tile_path:
            wx = origin_x + (tc * curr_tile_w) + (curr_tile_w // 2)
            wy = origin_y + (tr * curr_tile_h) + (curr_tile_h // 2)
            waypoints.append((wx, wy))
    
        # Draw path segments with arrowhead on destination leg
        for i in range(len(waypoints) - 1):
            src = waypoints[i]
            dst = waypoints[i + 1]
            if src and dst:
                is_last = (i == len(waypoints) - 2)
                if is_last:
                    draw_arrow(screen, arrow_col, src, dst, width=3, head_size=9)
                else:
                    pygame.draw.line(screen, arrow_col, src, dst, 2)
                    pygame.draw.circle(screen, arrow_col, dst, 3)
    
    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # DRAW ARMIES ON MAP (Waving War Banners & CK2 Unit Clusters)
    # ---------------------------------------------------------
    anim_ticks = pygame.time.get_ticks()
    tile_scale = curr_tile_w / BASE_TILE_W
    right_click_handled = False
    menu_just_opened = False

    # Partition armies: moving hosts vs stationary tile clusters
    moving_armies = []
    stationary_clusters = {}  # (tile, owner) -> list of armies

    for a in state.armies:
        if a.troops <= 0:
            continue
        if a.is_moving and not a.in_battle and getattr(a, "next_tile", None):
            moving_armies.append(a)
        else:
            t = getattr(a, "tile", get_province_capital_tile(a.province))
            stationary_clusters.setdefault((t, a.owner), []).append(a)

    # 1. RENDER MOVING ARMIES (Smooth 60 FPS sub-day position interpolation)
    for army in moving_armies:
        tc, tr = getattr(army, "tile", get_province_capital_tile(army.province))
        cur_ax = origin_x + (tc * curr_tile_w) + (curr_tile_w // 2)
        cur_ay = origin_y + (tr * curr_tile_h) + (curr_tile_h // 2)
        nc, nr = army.next_tile
        nx = origin_x + (nc * curr_tile_w) + (curr_tile_w // 2)
        ny = origin_y + (nr * curr_tile_h) + (curr_tile_h // 2)
        eff_prog = army.move_progress + (sub_day * getattr(army, "move_speed", 100.0))
        pct = min(1.0, max(0.0, eff_prog / 100.0))
        cx = int(cur_ax + (nx - cur_ax) * pct)
        cy = int(cur_ay + (ny - cur_ay) * pct)

        is_player = (army.owner == state.player_id)
        is_sel = (army.id == state.selected_army_id or army.id in getattr(state, "selected_army_ids", []))

        if is_sel:
            ring_w = int(curr_tile_w * 1.4)
            ring_h = int(curr_tile_h * 0.42)
            sel_surf = pygame.Surface((ring_w, ring_h), pygame.SRCALPHA)
            pygame.draw.ellipse(sel_surf, (240, 195, 50, 190), (0, 0, ring_w, ring_h), 2)
            screen.blit(sel_surf, (cx - ring_w // 2, cy - ring_h // 2))

        cw_main = max(16, int(24 * tile_scale))
        ch_main = max(11, int(17 * tile_scale))
        pole_h_main = max(22, int(32 * tile_scale))

        c_surf = get_scaled_banner_cloth(army.flag_origin, cw_main, ch_main, is_large=True)
        draw_waving_banner(screen, c_surf, cx, cy, pole_h=pole_h_main, ticks=anim_ticks, amp=max(1.2, 3.0 * (cw_main / 30.0)), freq=0.25, is_main=True)

        txt_badge = f"{army.troops:,}"
        if getattr(army, "is_starving", False):
            txt_badge = f"☠ STARVING ({army.troops:,})"
            p_bg = (165, 22, 22); p_border = (255, 65, 65)
        elif army.is_demobilizing:
            txt_badge = f"◆ HOME ({army.troops:,})"
            p_bg = (30, 48, 70); p_border = (120, 180, 240)
        elif getattr(army, "is_expeditionary", False):
            txt_badge = f"🏕 {army.troops:,} (Exped)"
            p_bg = (55, 42, 20); p_border = (245, 185, 55)
        elif is_sel:
            p_bg = (175, 30, 30) if is_player else (35, 55, 95); p_border = COLOR_GOLD
        else:
            p_bg = (24, 28, 38); p_border = (165, 45, 45) if is_player else (65, 95, 145)

        lbl = font_xs.render(txt_badge, True, COLOR_TEXT_WHITE if not is_sel else (255, 235, 140))
        tw = lbl.get_width()
        pw = max(int(36 * tile_scale), tw + 8)
        ph = 16
        px_pill = cx - pw // 2
        py_pill = cy + max(2, int(4 * tile_scale))

        pill_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pill_surf.fill((*p_bg, 225))
        pygame.draw.rect(pill_surf, p_border, (0, 0, pw, ph), 2 if is_sel else 1, border_radius=4)
        screen.blit(pill_surf, (px_pill, py_pill))
        screen.blit(lbl, (px_pill + (pw - tw) // 2, py_pill + 1))

        hit_rect = pygame.Rect(min(cx - 2, px_pill) - 4, cy - pole_h_main - 6, max(cw_main + 4, pw) + 8, (py_pill + ph + 4) - (cy - pole_h_main - 6))
        is_hov = hit_rect.collidepoint(mouse_pos)
        if mouse_clicked and is_hov:
            state.selected_army_id = army.id
            state.selected_army_ids = [army.id]
            state.selected_province = army.province
        if right_clicked and is_hov and is_player:
            right_click_handled = True
            state.selected_army_id = army.id
            state.selected_army_ids = [army.id]
            state.selected_province = army.province
            state.siege_context_menu = {
                "tile": (tc, tr),
                "pos": mouse_pos,
                "name": army.name,
                "is_hostile_holding": False,
                "armies": [army.id]
            }
            menu_just_opened = True

    # 2. RENDER STATIONARY TILE CLUSTERS (CK2 Multi-Army Stacking & Visual Mini-Banners)
    for (tile, owner), cluster in stationary_clusters.items():
        tc, tr = tile
        cx = origin_x + (tc * curr_tile_w) + (curr_tile_w // 2)
        cy = origin_y + (tr * curr_tile_h) + (curr_tile_h // 2)
        is_player = (owner == state.player_id)
        is_sel_cluster = any(a.id == state.selected_army_id or a.id in getattr(state, "selected_army_ids", []) for a in cluster)

        if is_sel_cluster:
            ring_w = int(curr_tile_w * 1.4)
            ring_h = int(curr_tile_h * 0.42)
            sel_surf = pygame.Surface((ring_w, ring_h), pygame.SRCALPHA)
            pygame.draw.ellipse(sel_surf, (240, 195, 50, 190), (0, 0, ring_w, ring_h), 2)
            screen.blit(sel_surf, (cx - ring_w // 2, cy - ring_h // 2))

        n_hosts = len(cluster)
        total_troops = sum(a.troops for a in cluster)

        # Pick primary host: currently selected host, or host with largest army
        primary_army = next((a for a in cluster if a.id == state.selected_army_id or a.id in getattr(state, "selected_army_ids", [])), None)
        if not primary_army:
            primary_army = max(cluster, key=lambda a: a.troops)
        other_armies = [a for a in cluster if a != primary_army]

        # Standard size for primary grand standard
        cw_main = max(16, int(24 * tile_scale))
        ch_main = max(11, int(17 * tile_scale))
        pole_h_main = max(22, int(32 * tile_scale))

        # Compact size for surrounding mini-banners (scaled down to ~55-60%)
        cw_mini = max(9, int(13 * tile_scale))
        ch_mini = max(6, int(9 * tile_scale))
        pole_h_mini = max(13, int(19 * tile_scale))

        banner_draw_queue = []
        if n_hosts == 2:
            # 2 Armies: Display TWO full side-by-side banners so both are prominent and clickable!
            a_left, a_right = cluster[0], cluster[1]
            dx_step = max(14, int(16 * tile_scale))
            banner_draw_queue.append((0, True, a_left.flag_origin, cx - dx_step, cy, 0, cw_main, ch_main, pole_h_main, a_left))
            banner_draw_queue.append((0, True, a_right.flag_origin, cx + dx_step, cy, 650, cw_main, ch_main, pole_h_main, a_right))
        elif n_hosts == 3:
            # 3 Armies: Display THREE distinct banners side-by-side
            dx_step = max(11, int(14 * tile_scale))
            banner_draw_queue.append((-1, True, cluster[0].flag_origin, cx - dx_step, cy - 2, 0, cw_main, ch_main, pole_h_main, cluster[0]))
            banner_draw_queue.append((0, True, cluster[1].flag_origin, cx, cy, 650, cw_main, ch_main, pole_h_main, cluster[1]))
            banner_draw_queue.append((1, True, cluster[2].flag_origin, cx + dx_step, cy - 2, 1300, cw_main, ch_main, pole_h_main, cluster[2]))
        else:
            # 1 or >3 Armies: Primary in center, surrounding mini-banners around
            banner_draw_queue.append((0, True, primary_army.flag_origin, cx, cy, 0, cw_main, ch_main, pole_h_main, primary_army))
            max_spread = min(int(curr_tile_w * 0.40), max(16, int(26 * tile_scale)))
            for idx, o_army in enumerate(other_armies):
                side = -1 if (idx % 2 == 0) else 1
                rank = idx // 2
                dx = int(side * min(max_spread, (rank + 1) * 6 * tile_scale))
                dy = int(((idx % 3) - 1) * 3 * tile_scale)
                t_off = (idx + 1) * 650
                banner_draw_queue.append((dy, False, o_army.flag_origin, cx + dx, cy + dy, t_off, cw_mini, ch_mini, pole_h_mini, o_army))

            # If primary army has merged sub_flags, also display them compactly
            for idx, sf in enumerate(getattr(primary_army, "sub_flags", [])):
                side = 1 if (idx % 2 == 0) else -1
                rank = (idx // 2) + 1
                dx = int(side * min(max_spread, (rank + 1) * 6 * tile_scale))
                dy = int(-4 * tile_scale)
                t_off = (idx + 5) * 500
                banner_draw_queue.append((dy, False, sf, cx + dx, cy + dy, t_off, cw_mini, ch_mini, pole_h_mini, primary_army))

        # Sort banners by depth (back to front)
        banner_draw_queue.sort(key=lambda b: b[0])

        banner_clicked = False
        for dy, is_main, f_id, px, py, t_off, b_cw, b_ch, b_ph, b_army in banner_draw_queue:
            c_surf = get_scaled_banner_cloth(f_id, b_cw, b_ch, is_large=is_main)
            draw_waving_banner(screen, c_surf, px, py, pole_h=b_ph, ticks=anim_ticks + t_off, amp=max(1.2, (3.0 if is_main else 1.8) * (b_cw / 30.0)), freq=0.25 if is_main else 0.30, is_main=is_main)

            # Highlight selected army banner with a golden base ring and pole star!
            cur_sel = getattr(state, "selected_army_ids", [])
            is_this_sel = (b_army.id in cur_sel) or (b_army.id == state.selected_army_id and len(cur_sel) <= 1)
            if is_this_sel and b_army.owner == state.player_id:
                rw = max(18, int(b_cw * 1.3))
                rh = max(8, int(b_ph * 0.32))
                r_surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
                pygame.draw.ellipse(r_surf, (255, 215, 50, 210), (0, 0, rw, rh), 2)
                screen.blit(r_surf, (px - rw // 2, py - rh // 2))
                star_lbl = font_xs.render("★", True, COLOR_GOLD)
                screen.blit(star_lbl, (px - star_lbl.get_width() // 2, py - b_ph - 14))

            # Direct click on individual banner selects THAT specific army!
            b_flag_rect = pygame.Rect(px - 3, py - b_ph - 4, b_cw + 6, b_ph + 6)
            if mouse_clicked and b_flag_rect.collidepoint(mouse_pos) and b_army.owner == state.player_id and not banner_clicked:
                state.selected_army_id = b_army.id
                state.selected_army_ids = [b_army.id]
                state.selected_province = b_army.province
                state.selected_settlement = None
                banner_clicked = True

        # -------------------------------------------------------------
        # UNIFIED CK2 TROOP COUNT PILL BADGE:
        # '(unit count) total men' format (e.g. '(11) 3,248 Men')
        # -------------------------------------------------------------
        any_battle = any(a.in_battle for a in cluster)
        any_starving = any(getattr(a, "is_starving", False) for a in cluster)
        any_sieging = any(a.is_sieging for a in cluster)
        any_exped = any(getattr(a, "is_expeditionary", False) for a in cluster)
        any_mustering = any(a.is_mustering for a in cluster)
        any_demobilizing = any(a.is_demobilizing for a in cluster)

        if n_hosts > 1:
            # Multi-army stack format
            if any_battle:
                txt_badge = f"⚔ ({n_hosts}) {total_troops:,} Men"
                p_bg = (185, 35, 35); p_border = (255, 220, 50)
            elif any_starving:
                txt_badge = f"☠ STARVING ({n_hosts}) {total_troops:,} Men"
                p_bg = (165, 22, 22); p_border = (255, 65, 65)
            elif any_sieging:
                s_prog = max(getattr(a, "siege_progress", 0) for a in cluster)
                txt_badge = f"⚑ {s_prog}% ({n_hosts}) {total_troops:,} Men"
                p_bg = (155, 85, 25); p_border = COLOR_GOLD
            elif any_exped:
                txt_badge = f"🏕 ({n_hosts}) {total_troops:,} Men"
                p_bg = (55, 42, 20); p_border = (245, 185, 55)
            elif any_mustering:
                txt_badge = f"⛺ ({n_hosts}) {total_troops:,} Men"
                p_bg = (65, 52, 20); p_border = COLOR_GOLD
            elif any_demobilizing:
                txt_badge = f"◆ HOME ({n_hosts}) {total_troops:,} Men"
                p_bg = (30, 48, 70); p_border = (120, 180, 240)
            elif is_sel_cluster:
                cur_ids = getattr(state, "selected_army_ids", [])
                p_hosts = [a for a in cluster if a.owner == state.player_id]
                if len(cur_ids) == 1 and cur_ids[0] in [a.id for a in p_hosts]:
                    sel_h = next(a for a in p_hosts if a.id == cur_ids[0])
                    idx_h = p_hosts.index(sel_h) + 1
                    txt_badge = f"★ [{idx_h}/{n_hosts}] {sel_h.name[:12]}: {sel_h.troops:,}"
                elif len(cur_ids) == len(p_hosts) and len(p_hosts) > 1:
                    txt_badge = f"★ ALL ({n_hosts}) {total_troops:,} Men"
                else:
                    txt_badge = f"({n_hosts}) {total_troops:,} Men"
                p_bg = (175, 30, 30) if is_player else (35, 55, 95); p_border = COLOR_GOLD
            else:
                txt_badge = f"({n_hosts}) {total_troops:,} Men"
                p_bg = (24, 28, 38); p_border = (165, 45, 45) if is_player else (65, 95, 145)
        else:
            # Single army format
            a_single = cluster[0]
            if a_single.in_battle:
                txt_badge = f"⚔ {a_single.troops:,}"
                p_bg = (185, 35, 35); p_border = (255, 220, 50)
            elif getattr(a_single, "is_starving", False):
                txt_badge = f"☠ STARVING ({a_single.troops:,}) -5/d"
                p_bg = (165, 22, 22); p_border = (255, 65, 65)
            elif a_single.courier_en_route:
                txt_badge = f"✉ Summons ({a_single.courier_days_left}d)"
                p_bg = (55, 42, 18); p_border = (245, 205, 70)
            elif a_single.is_mustering:
                txt_badge = f" {a_single.muster_days}d ({a_single.troops:,})"
                p_bg = (65, 52, 20); p_border = COLOR_GOLD
            elif a_single.is_demobilizing:
                txt_badge = f"◆ HOME ({a_single.troops:,})"
                p_bg = (30, 48, 70); p_border = (120, 180, 240)
            elif getattr(a_single, "siege_prep_days", 0) > 0:
                txt_badge = f"⛺ Prep {a_single.siege_prep_days}d"
                p_bg = (140, 75, 20); p_border = (255, 200, 70)
            elif getattr(a_single, "siege_packup_days", 0) > 0:
                txt_badge = f"⛺ Pack {a_single.siege_packup_days}d"
                p_bg = (110, 50, 20); p_border = (220, 140, 50)
            elif a_single.is_sieging:
                clean_name = a_single.siege_target_name or "City"
                for pfx in ["Royal City of ", "Royal Citadel of ", "Royal Castle of ", "Royal Borough of ", "Royal "]:
                    clean_name = clean_name.replace(pfx, "")
                txt_badge = f"⚑ {a_single.siege_progress}% {clean_name[:12]}"
                p_bg = (155, 85, 25); p_border = COLOR_GOLD
            elif getattr(a_single, "is_expeditionary", False):
                txt_badge = f"🏕 {a_single.troops:,} (Exped)"
                p_bg = (55, 42, 20); p_border = (245, 185, 55)
            elif is_sel_cluster:
                txt_badge = f"{a_single.troops:,}"
                p_bg = (175, 30, 30) if is_player else (35, 55, 95); p_border = COLOR_GOLD
            else:
                txt_badge = f"{a_single.troops:,}"
                p_bg = (24, 28, 38); p_border = (165, 45, 45) if is_player else (65, 95, 145)

        lbl = font_xs.render(txt_badge, True, COLOR_TEXT_WHITE if not is_sel_cluster else (255, 235, 140))
        tw = lbl.get_width()
        pw = max(int(36 * tile_scale), tw + 10)
        ph = 17
        px_pill = cx - pw // 2
        py_pill = cy + max(2, int(4 * tile_scale))

        pill_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pill_surf.fill((*p_bg, 225))
        pygame.draw.rect(pill_surf, p_border, (0, 0, pw, ph), 2 if is_sel_cluster else 1, border_radius=4)
        screen.blit(pill_surf, (px_pill, py_pill))
        screen.blit(lbl, (px_pill + (pw - tw) // 2, py_pill + 1))

        # Unified Hitbox covering all cluster banners + count pill
        all_x = [cx, cx + cw_main, px_pill, px_pill + pw]
        for dy_val, is_m, sf, b_px, b_py, t_off, b_cw, b_ch, b_ph, *extra in banner_draw_queue:
            all_x.extend([b_px - 2, b_px + b_cw + 2])
        min_x = min(all_x) - 4
        max_x = max(all_x) + 4
        hit_rect = pygame.Rect(min_x, cy - pole_h_main - 6, max_x - min_x, (py_pill + ph + 4) - (cy - pole_h_main - 6))

        # Compute clicked tile to ensure clicks on adjacent tiles never get falsely intercepted
        mx_cur, my_cur = mouse_pos
        c_col = int((mx_cur - origin_x) // curr_tile_w)
        c_row = int((my_cur - origin_y) // curr_tile_h)
        pill_rect = pygame.Rect(px_pill, py_pill, pw, ph)
        is_badge_hover = (hit_rect.collidepoint(mouse_pos) or pill_rect.collidepoint(mouse_pos)) and ((c_col, c_row) == tile)

        # Left Click: Cycle through individual armies in cluster (Host 1 -> Host 2 -> ALL -> Host 1)
        if mouse_clicked and is_badge_hover and not banner_clicked:
            p_hosts = [a for a in cluster if a.owner == state.player_id]
            if len(p_hosts) > 1:
                cur_sel_ids = getattr(state, "selected_army_ids", [])
                if len(cur_sel_ids) == 1 and cur_sel_ids[0] in [a.id for a in p_hosts]:
                    cur_idx = [a.id for a in p_hosts].index(cur_sel_ids[0])
                    if cur_idx + 1 < len(p_hosts):
                        next_army = p_hosts[cur_idx + 1]
                        state.selected_army_id = next_army.id
                        state.selected_army_ids = [next_army.id]
                    else:
                        # Reached end of single armies -> select ALL
                        state.selected_army_id = p_hosts[0].id
                        state.selected_army_ids = [a.id for a in p_hosts]
                elif len(cur_sel_ids) == len(p_hosts):
                    # Currently ALL selected -> cycle back to first single army
                    next_army = p_hosts[0]
                    state.selected_army_id = next_army.id
                    state.selected_army_ids = [next_army.id]
                else:
                    # None or other -> select first single army
                    next_army = p_hosts[0]
                    state.selected_army_id = next_army.id
                    state.selected_army_ids = [next_army.id]
                sel_obj = next((a for a in cluster if a.id == state.selected_army_id), None)
                if sel_obj:
                    state.selected_province = sel_obj.province
                state.selected_settlement = None
            elif p_hosts:
                state.selected_army_id = p_hosts[0].id
                state.selected_army_ids = [p_hosts[0].id]
                state.selected_province = p_hosts[0].province
                state.selected_settlement = None

        # Right Click on cluster: Open Tactical Context Menu immediately (1-Click Guarantee!)
        if right_clicked and is_badge_hover and is_player:
            right_click_handled = True
            if len(getattr(state, "selected_army_ids", [])) != 1:
                state.selected_army_id = primary_army.id
                state.selected_army_ids = [a.id for a in cluster if a.owner == state.player_id]
            state.selected_province = primary_army.province
            state.selected_settlement = None

            settlement = state.settlements.get(tile)
            target_prov_id = cell_to_prov.get(tile)
            prov = PROVINCES.get(target_prov_id)
            is_hostile_holding = False
            if settlement and prov:
                occ = settlement.get("occupied_by")
                if state.are_hostile(state.player_id, prov["owner"]):
                    if occ != state.player_id:
                        is_hostile_holding = True
                elif occ is not None and state.are_hostile(state.player_id, occ):
                    is_hostile_holding = True

            state.siege_context_menu = {
                "tile": tile,
                "pos": mouse_pos,
                "name": settlement.get("name", primary_army.name) if settlement else primary_army.name,
                "is_hostile_holding": is_hostile_holding,
                "armies": [a.id for a in cluster if a.owner == state.player_id]
            }
            menu_just_opened = True

    # 3. DIRECT MAP RIGHT-CLICK DISPATCHER (1-Click Responsive Orders Anywhere on Map)
    if right_clicked and not right_click_handled and map_bg_rect.collidepoint(mouse_pos):
        # Check if clicking inside open context menu
        ctx_menu = getattr(state, "siege_context_menu", None)
        # Determine clicked tile
        mx, my = mouse_pos
        col_idx = int((mx - origin_x) // curr_tile_w)
        row_idx = int((my - origin_y) // curr_tile_h)
        click_tile = (col_idx, row_idx)

        armies_to_order = []
        if getattr(state, "selected_army_ids", None):
            armies_to_order = [a for a in state.armies if a.id in state.selected_army_ids and a.owner == state.player_id and a.troops > 0]
        elif getattr(state, "selected_army_id", None):
            s_single = next((a for a in state.armies if a.id == state.selected_army_id and a.owner == state.player_id and a.troops > 0), None)
            if s_single:
                armies_to_order = [s_single]

        if armies_to_order and click_tile in cell_to_prov:
            is_standing_on = any(getattr(a, "tile", None) == click_tile for a in armies_to_order)
            settlement = state.settlements.get(click_tile)
            target_prov_id = cell_to_prov.get(click_tile)
            prov = PROVINCES.get(target_prov_id)
            is_hostile_holding = False
            if settlement and prov:
                occ = settlement.get("occupied_by")
                if state.are_hostile(state.player_id, prov["owner"]):
                    if occ != state.player_id:
                        is_hostile_holding = True
                elif occ is not None and state.are_hostile(state.player_id, occ):
                    is_hostile_holding = True

            if is_standing_on:
                # Right-clicked directly on the city/camp where armies are standing: open tactical context menu instantly!
                state.siege_context_menu = {
                    "tile": click_tile,
                    "pos": (mx, my),
                    "name": settlement.get("name", "Host Camp") if settlement else "Host Camp",
                    "is_hostile_holding": is_hostile_holding,
                    "armies": [a.id for a in armies_to_order]
                }
                menu_just_opened = True
            else:
                # March order: Move directly to target tile (NO POPUP!)
                state.siege_context_menu = None
                for a_obj in armies_to_order:
                    state.order_army_march_to_tile(a_obj, click_tile)

    # DRAW TRAVELLING ROYAL COURIERS (Riders Galloping Between Shires)
    # -------------------------------------------------------------
    anim_ticks = pygame.time.get_ticks()
    frame_idx = int((anim_ticks // 70) % 12)
    hop_courier_counts = {}

    tile_scale = curr_tile_w / BASE_TILE_W
    hw = max(14, int(28 * tile_scale))
    hh = max(10, int(21 * tile_scale))
    spacing_step = max(16.0, 32.0 * tile_scale)
    stagger_step = max(3, int(6 * tile_scale))

    for army in state.armies:
        if army.courier_en_route:
            mx, my = None, None
            dest_pos = None
            facing_left = False
            is_player = (army.owner == state.player_id)

            if getattr(army, "courier_tile_path", None):
                cap_pid = state.get_realm_capital(army.owner)
                cur_t = getattr(army, "courier_tile", None) or PROV_CAPITAL_TILES.get(cap_pid, (4, 8))
                next_t = army.courier_tile_path[0] if army.courier_tile_path else army.tile
                from game.config import DAYS_PER_TILE
                courier_step = 100.0 / max(1.0, float(DAYS_PER_TILE))
                eff_c_prog = army.courier_progress + (sub_day * courier_step)
                pct = min(1.0, max(0.0, eff_c_prog / 100.0))
                col_f = cur_t[0] + (next_t[0] - cur_t[0]) * pct
                row_f = cur_t[1] + (next_t[1] - cur_t[1]) * pct
                base_x = origin_x + col_f * curr_tile_w + curr_tile_w / 2
                base_y = origin_y + row_f * curr_tile_h + curr_tile_h / 2
                dest_pos = (int(origin_x + army.tile[0] * curr_tile_w + curr_tile_w / 2), int(origin_y + army.tile[1] * curr_tile_h + curr_tile_h / 2))
                mx = int(base_x)
                my = int(base_y)
                facing_left = (next_t[0] < cur_t[0])
            elif army.courier_current_prov and army.courier_next_prov:
                c_pos = province_anchors.get(army.courier_current_prov)
                n_pos = province_anchors.get(army.courier_next_prov)
                dest_pos = province_anchors.get(army.province)
                if not (c_pos and n_pos):
                    continue
                from game.config import DAYS_PER_TILE
                courier_step = 100.0 / max(1.0, float(DAYS_PER_TILE))
                eff_c_prog = army.courier_progress + (sub_day * courier_step)
                pct = min(1.0, max(0.0, eff_c_prog / 100.0))
                base_x = c_pos[0] + (n_pos[0] - c_pos[0]) * pct
                base_y = c_pos[1] + (n_pos[1] - c_pos[1]) * pct
                facing_left = (n_pos[0] < c_pos[0])

                # Spread multiple riders sharing the same path side-by-side cleanly
                hop_key = (army.courier_current_prov, army.courier_next_prov)
                c_idx = hop_courier_counts.get(hop_key, 0)
                hop_courier_counts[hop_key] = c_idx + 1

                dx = float(n_pos[0] - c_pos[0])
                dy = float(n_pos[1] - c_pos[1])
                dist = math.hypot(dx, dy)
                if dist > 0.001 and c_idx > 0:
                    nx = -dy / dist
                    ny = dx / dist
                    tx = dx / dist
                    ty = dy / dist
                    offset_mag = ((c_idx + 1) // 2) * spacing_step * (1 if c_idx % 2 == 1 else -1)
                    stagger = (c_idx % 2) * stagger_step
                    mx = int(base_x + nx * offset_mag + tx * stagger)
                    my = int(base_y + ny * offset_mag + ty * stagger)
                else:
                    mx = int(base_x)
                    my = int(base_y)

            if mx is not None and my is not None:
                # Subtle dotted/thin guide line connecting courier to destination
                if dest_pos:
                    guide_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                    pygame.draw.line(guide_surf, (250, 215, 80, 50) if is_player else (120, 180, 255, 50), (mx, my), dest_pos, 1)
                    screen.blit(guide_surf, (0, 0))

                # Dynamically Scaled Galloping Horse Sprite (Tracks Zoom Level)
                horse_surf = get_horse_courier_sprite(army.owner, is_player, facing_left, frame_idx, hw, hh)
                screen.blit(horse_surf, (mx - hw // 2, my - hh + 2))

                # Compact Days Left Badge: "Xd left" (or "Xd" if zoomed far out)
                if tile_scale < 0.78:
                    b_text = f"{army.courier_days_left}d"
                else:
                    b_text = f"{army.courier_days_left}d left"
                b_lbl = font_xs.render(b_text, True, (255, 235, 170) if is_player else (220, 235, 255))
                bw = b_lbl.get_width() + max(4, int(6 * tile_scale))
                bh = max(11, int(14 * tile_scale))
                badge_y = my + 2

                badge_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
                badge_surf.fill((16, 18, 24, 225))
                pygame.draw.rect(badge_surf, COLOR_GOLD if is_player else (100, 160, 240), (0, 0, bw, bh), 1, border_radius=3)
                badge_surf.blit(b_lbl, ((bw - b_lbl.get_width()) // 2, (bh - b_lbl.get_height()) // 2))
                screen.blit(badge_surf, (mx - bw // 2, badge_y))
    
    # (No hard victory / defeat banners: dynamic feudal subjugation replaces game over)
    
    # -------------------------------------------------------------
    # DRAW SUPPLY WAGONS (Logistics Convoys Rolling to Frontlines)
    # -------------------------------------------------------------
    ww = max(18, int(30 * tile_scale))
    wh = max(12, int(20 * tile_scale))

    for wagon in getattr(state, "supply_wagons", []):
        next_t = wagon.tile_path[0] if wagon.tile_path else wagon.tile
        cur_t = wagon.tile
        pct = min(1.0, max(0.0, wagon.move_progress / 100.0))

        col_f = cur_t[0] + (next_t[0] - cur_t[0]) * pct
        row_f = cur_t[1] + (next_t[1] - cur_t[1]) * pct

        wx = int(origin_x + col_f * curr_tile_w + curr_tile_w / 2)
        wy = int(origin_y + row_f * curr_tile_h + curr_tile_h / 2)

        is_player_wagon = (wagon.owner == state.player_id)
        facing_left = (next_t[0] < cur_t[0])

        # Draw line connecting to destination army
        t_army = next((a for a in state.armies if a.id == wagon.target_army_id), None)
        if t_army and getattr(t_army, "tile", None):
            ax = int(origin_x + t_army.tile[0] * curr_tile_w + curr_tile_w / 2)
            ay = int(origin_y + t_army.tile[1] * curr_tile_h + curr_tile_h / 2)
            sup_line_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            line_col = (245, 195, 60, 70) if is_player_wagon else (100, 165, 240, 70)
            pygame.draw.line(sup_line_surf, line_col, (wx, wy), (ax, ay), 1)
            screen.blit(sup_line_surf, (0, 0))

        # Render wagon sprite
        w_surf = get_supply_wagon_sprite(wagon.owner, is_player_wagon, facing_left, ww, wh)
        screen.blit(w_surf, (wx - ww // 2, wy - wh // 2))

        # Cargo / Reinforcements pill badge
        if wagon.reinforcements > 0:
            c_text = f"📦 +{wagon.reinforcements} men"
        else:
            c_text = "📦 Rations"

        c_lbl = font_xs.render(c_text, True, (255, 235, 160) if is_player_wagon else (210, 230, 255))
        cw = c_lbl.get_width() + 6
        ch = 14
        c_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
        c_surf.fill((20, 24, 32, 220))
        pygame.draw.rect(c_surf, COLOR_GOLD if is_player_wagon else (80, 140, 220), (0, 0, cw, ch), 1, border_radius=3)
        c_surf.blit(c_lbl, (3, 0))
        screen.blit(c_surf, (wx - cw // 2, wy + wh // 2 + 1))

    # ---------------------------------------------------------
    # FLOATING MAP ZOOM & CAMERA CONTROLS HUD
    # ---------------------------------------------------------
    hud_w, hud_h = 36, 118
    hud_x, hud_y = map_bg_rect.right - 48, bar_y + bar_h + 12
    hud_rect = pygame.Rect(hud_x, hud_y, hud_w, hud_h)
    hud_surf = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
    hud_surf.fill((22, 28, 40, 220))
    screen.blit(hud_surf, (hud_x, hud_y))
    pygame.draw.rect(screen, COLOR_GOLD, hud_rect, 1, border_radius=4)
    
    # Zoom In (+)
    zin_rect = pygame.Rect(hud_x + 3, hud_y + 4, 30, 26)
    zin_hov = zin_rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (50, 62, 85) if zin_hov else (32, 38, 52), zin_rect, border_radius=3)
    zin_txt = font_md.render("+", True, COLOR_GOLD if zin_hov else COLOR_TEXT_WHITE)
    screen.blit(zin_txt, (zin_rect.x + (zin_rect.w - zin_txt.get_width()) // 2, zin_rect.y + 1))
    if mouse_clicked and zin_hov:
        state.zoom = min(state.max_zoom, round(state.zoom + 0.15, 2))
    
    # Current Zoom percentage label
    pct_lbl = font_xs.render(f"{int(state.zoom * 100)}%", True, COLOR_GOLD)
    screen.blit(pct_lbl, (hud_x + (hud_w - pct_lbl.get_width()) // 2, hud_y + 35))
    
    # Zoom Out (-)
    zout_rect = pygame.Rect(hud_x + 3, hud_y + 54, 30, 26)
    zout_hov = zout_rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (50, 62, 85) if zout_hov else (32, 38, 52), zout_rect, border_radius=3)
    zout_txt = font_md.render("–", True, COLOR_GOLD if zout_hov else COLOR_TEXT_WHITE)
    screen.blit(zout_txt, (zout_rect.x + (zout_rect.w - zout_txt.get_width()) // 2, zout_rect.y + 1))
    if mouse_clicked and zout_hov:
        state.zoom = max(state.min_zoom, round(state.zoom - 0.15, 2))
    
    # Reset Camera & Zoom (⟲)
    zres_rect = pygame.Rect(hud_x + 3, hud_y + 86, 30, 26)
    zres_hov = zres_rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (50, 62, 85) if zres_hov else (32, 38, 52), zres_rect, border_radius=3)
    zres_txt = font_sm.render("⟲", True, (140, 200, 255) if zres_hov else COLOR_TEXT_MUTED)
    screen.blit(zres_txt, (zres_rect.x + (zres_rect.w - zres_txt.get_width()) // 2, zres_rect.y + 4))
    if mouse_clicked and zres_hov:
        state.zoom = 0.85
        state.cam_pan_x = 0
        state.cam_pan_y = 0
    
    # ---------------------------------------------------------
    # TERRITORY CONTROL HUD BAR (Floating cleanly on top of map)
    # ---------------------------------------------------------
    total_provs = max(1, len(PROVINCES))
    bar_x = MAP_VIEWPORT_X + 26
    bar_y = PANEL_Y + 12
    bar_w = MAP_VIEWPORT_W - 52
    bar_h = 24

    ruler_shares = []
    for cid in state.get_active_rulers(include_player=True):
        count = state.get_provinces_count(cid)
        if count <= 0:
            continue
        ruler_shares.append((cid, count, get_color(cid)))

    pygame.draw.rect(screen, (25, 30, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
    cursor_x = bar_x
    for idx, (cid, count, color) in enumerate(ruler_shares):
        seg_w = bar_w - (cursor_x - bar_x) if idx == len(ruler_shares) - 1 else int((count / total_provs) * bar_w)
        seg_w = max(0, seg_w)
        radius = 4 if idx in (0, len(ruler_shares) - 1) else 0
        if seg_w > 0:
            pygame.draw.rect(screen, color, (cursor_x, bar_y, seg_w, bar_h), border_radius=radius)
        label = f"{get_short_name(cid).upper()}: {count}"
        lbl = font_xs.render(label, True, (240, 244, 250))
        lbl_x = cursor_x + max(4, (seg_w - lbl.get_width()) // 2)
        if 0 <= lbl_x <= bar_x + bar_w - lbl.get_width():
            screen.blit(lbl, (lbl_x, bar_y + 4))
        cursor_x += seg_w
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)

    # ---------------------------------------------------------
    # FLOATING TACTICAL CONTEXT MENU (Siege / Reorganize / Split / Merge)
    # ---------------------------------------------------------
    if getattr(state, "siege_context_menu", None):
        ctx = state.siege_context_menu
        cx_x, cx_y = ctx["pos"]
        h_name = ctx.get("name", "Host Camp")
        is_hostile = ctx.get("is_hostile_holding", False)
        c_tile = ctx.get("tile")

        army_ids = ctx.get("armies", [])
        p_army = next((a for a in state.armies if a.id in army_ids and a.owner == state.player_id), None)

        menu_items = []
        same_tile = [ha for ha in state.armies if ha.owner == state.player_id and ha.troops > 0 and getattr(ha, "tile", None) == c_tile and not ha.in_battle]
        if len(same_tile) > 1:
            # Individual host pickers so player can choose exactly which host to control!
            for ha in same_tile:
                is_this_sel = (ha.id in getattr(state, "selected_army_ids", []) and len(state.selected_army_ids) == 1)
                star = "★ " if is_this_sel else "  "
                menu_items.append(("pick_single_" + ha.id, f"{star}SELECT: {ha.name[:11]} ({ha.troops:,}m)", (35, 55, 80) if is_this_sel else (25, 40, 60), COLOR_GOLD if is_this_sel else (80, 130, 190)))
            tot_same = sum(ha.troops for ha in same_tile)
            is_all_sel = (len(getattr(state, "selected_army_ids", [])) == len(same_tile))
            menu_items.append(("pick_all", f"{'★ ' if is_all_sel else '  '}SELECT ALL {len(same_tile)} HOSTS ({tot_same:,}m)", (55, 45, 25), COLOR_GOLD))
        else:
            menu_items.append(("march", "➔ MARCH / MOVE HERE", (26, 75, 45), (70, 195, 110)))

        if is_hostile:
            menu_items.append(("siege", "⚔ SIEGE THE CASTLE", (140, 42, 22), (255, 110, 70)))

        if p_army and not p_army.in_battle and not p_army.is_demobilizing:
            n_levies = len(getattr(p_army, "sub_units", []))
            menu_items.append(("reorganize", f"➦ REORGANIZE HOST ({n_levies} Levies)", (35, 75, 120), (100, 175, 255)))
            if p_army.troops >= 2:
                menu_items.append(("half", "⚡ SPLIT IN HALF (50/50)", (125, 90, 25), COLOR_GOLD))

        # Check merge
        same_tile = [ha for ha in state.armies if ha.owner == state.player_id and ha.troops > 0 and getattr(ha, "tile", None) == c_tile and not ha.in_battle]
        if len(same_tile) > 1:
            menu_items.append(("merge", f"🛡 MERGE {len(same_tile)} HOSTS HERE", (90, 50, 120), (200, 130, 255)))

        m_w = 260
        btn_h = 28
        spacing = 5
        m_h = 32 + len(menu_items) * (btn_h + spacing) + 6
        m_x = min(map_bg_rect.right - m_w - 12, max(map_bg_rect.left + 12, cx_x - m_w // 2))
        m_y = min(map_bg_rect.bottom - m_h - 12, max(map_bg_rect.top + 12, cx_y - m_h - 10))

        menu_rect = pygame.Rect(m_x, m_y, m_w, m_h)
        pygame.draw.rect(screen, (20, 24, 34), menu_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_GOLD, menu_rect, 1, border_radius=6)

        header_txt = f"Orders: {h_name[:24]}" if is_hostile else f"Host: {h_name[:24]}"
        screen.blit(font_xs.render(header_txt, True, (240, 220, 160)), (m_x + 10, m_y + 8))

        by = m_y + 28
        btn_clicked = False
        for action_type, label, col_bg, col_border in menu_items:
            b_rect = pygame.Rect(m_x + 8, by, m_w - 16, btn_h)
            b_hov = b_rect.collidepoint(mouse_pos)

            c_bg = tuple(min(255, c + 35) for c in col_bg) if b_hov else col_bg
            pygame.draw.rect(screen, c_bg, b_rect, border_radius=4)
            pygame.draw.rect(screen, col_border, b_rect, 1, border_radius=4)

            lbl_surf = font_sm.render(label, True, COLOR_TEXT_WHITE)
            screen.blit(lbl_surf, (b_rect.x + (b_rect.w - lbl_surf.get_width()) // 2, b_rect.y + 4))

            if mouse_clicked and b_hov:
                btn_clicked = True
                if action_type.startswith("pick_single_"):
                    tgt_id = action_type.replace("pick_single_", "")
                    tgt_a = next((a for a in state.armies if a.id == tgt_id), None)
                    if tgt_a:
                        state.selected_army_id = tgt_a.id
                        state.selected_army_ids = [tgt_a.id]
                        state.selected_province = tgt_a.province
                        state.selected_settlement = None
                        state.logs.append(f"Selected {tgt_a.name} ({tgt_a.troops:,} men). Right-click map to move this host.")
                elif action_type == "pick_all":
                    same_hosts = [ha for ha in state.armies if ha.owner == state.player_id and ha.troops > 0 and getattr(ha, "tile", None) == ctx["tile"] and not ha.in_battle]
                    state.selected_army_ids = [ha.id for ha in same_hosts]
                    state.selected_army_id = same_hosts[0].id if same_hosts else None
                    state.selected_settlement = None
                elif action_type == "march_single":
                    if p_army:
                        state.selected_army_id = p_army.id
                        state.selected_army_ids = [p_army.id]
                        state.order_army_march_to_tile(p_army, ctx["tile"])
                elif action_type == "march_all":
                    same_hosts = [ha for ha in state.armies if ha.owner == state.player_id and ha.troops > 0 and getattr(ha, "tile", None) == ctx["tile"] and not ha.in_battle]
                    state.selected_army_ids = [ha.id for ha in same_hosts]
                    for ha in same_hosts:
                        state.order_army_march_to_tile(ha, ctx["tile"])
                elif action_type == "march":
                    for aid in ctx["armies"]:
                        a_obj = next((a for a in state.armies if a.id == aid), None)
                        if a_obj:
                            state.order_army_march_to_tile(a_obj, ctx["tile"])
                elif action_type == "siege":
                    for aid in ctx["armies"]:
                        a_obj = next((a for a in state.armies if a.id == aid), None)
                        if a_obj:
                            state.order_army_siege_holding(a_obj, ctx["tile"])
                elif action_type == "reorganize":
                    if p_army:
                        state.split_army_target_id = p_army.id
                        state.split_selected_units = set()
                elif action_type == "half":
                    if p_army:
                        state.split_army_in_half(p_army.id)
                elif action_type == "merge":
                    state.merge_armies_at_tile(ctx["tile"], state.player_id)

                state.siege_context_menu = None
                break

            by += btn_h + spacing

        if not menu_just_opened and (mouse_clicked or right_clicked) and not menu_rect.collidepoint(mouse_pos) and not btn_clicked:
            state.siege_context_menu = None

    # Unclip screen so right panel and remaining UI render normally across the whole display
    screen.set_clip(None)
    
