"""
Center Map Viewport and Multi-Pass Renderer Component
"""
import math
import random
import pygame
from game.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_OCEAN, COLOR_PANEL_BORDER, COLOR_WESSEX,
    COLOR_DANELAW, COLOR_GOLD, COLOR_TEXT_WHITE, COLOR_TEXT_MUTED,
    COLOR_TEXT_RED, COLOR_TEXT_GREEN, BASE_TILE_W, BASE_TILE_H,
    VIEWPORT_CENTER_X, VIEWPORT_CENTER_Y,
    MAP_VIEWPORT_X, MAP_VIEWPORT_W, PANEL_Y, PANEL_H
)
from game.data.provinces import PROVINCES, PROVINCE_FACTION_COLORS
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

def render_map_view(screen, state, mouse_pos, mouse_clicked, right_clicked, mouse_down, fonts, banner_cloth_large, banner_cloth_small, ticks=0):
    raw_grid = RAW_GRID
    cell_to_prov = CELL_TO_PROV
    font_xs = fonts["xs"]
    font_sm = fonts["sm"]
    font_md = fonts["md"]
    font_lg = fonts["lg"]

    curr_tile_w = max(18, int(BASE_TILE_W * state.zoom))
    curr_tile_h = max(16, int(BASE_TILE_H * state.zoom))
    default_ox = VIEWPORT_CENTER_X - int(10 * curr_tile_w)
    default_oy = VIEWPORT_CENTER_Y - int(13 * curr_tile_h)
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
    
    # Territory Control Bar (Wessex vs Danelaw)
    wessex_count = state.get_provinces_count(state.player_id)
    danelaw_count = state.get_provinces_count(state.enemy_id)
    total_provs = 12
    
    bar_x = MAP_VIEWPORT_X + 26
    bar_y = PANEL_Y + 12
    bar_w = MAP_VIEWPORT_W - 52
    bar_h = 24
    
    pygame.draw.rect(screen, (25, 30, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
    wessex_pixel_w = int((wessex_count / total_provs) * bar_w)
    pygame.draw.rect(screen, COLOR_WESSEX, (bar_x, bar_y, wessex_pixel_w, bar_h), border_radius=4)
    pygame.draw.rect(screen, COLOR_DANELAW, (bar_x + wessex_pixel_w, bar_y, bar_w - wessex_pixel_w, bar_h), border_radius=4)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
    
    w_lbl = font_sm.render(f"WESSEX: {wessex_count} Provinces", True, (255, 230, 230))
    d_lbl = font_sm.render(f"DANELAW: {danelaw_count} Provinces", True, (230, 240, 255))
    screen.blit(w_lbl, (bar_x + 10, bar_y + 3))
    screen.blit(d_lbl, (bar_x + bar_w - d_lbl.get_width() - 10, bar_y + 3))
    
    # Floating Zoom HUD rect anchor
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
            owner = prov_info.get("owner", "char_alfred") if prov_info else "char_alfred"
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
    
            # Contested Province Hatching (Diagonal Striped Hazard Pattern ala CK2)
            is_contested, occupier = is_province_contested(state, prov_id)
            if is_contested:
                stripe_col = (220, 50, 50) if occupier == state.player_id else (45, 65, 95)
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
                    # CK2 style: Left-clicking a province inspects that province and unselects armies!
                    state.selected_province = prov_id
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
            occ_key = "wessex" if occ_id == state.player_id else "jorvik"
            occ_flag = prov_flag_cache.get(occ_key)
            if occ_flag:
                mini_f = pygame.transform.smoothscale(occ_flag, (12, 14))
                screen.blit(mini_f, (cx + cw - 12, cy - 8))
    
        # Click city to inspect settlement details (only when not building or editing fiefs)!
        if mouse_clicked and is_city_hover and not state.build_mode and not state.editing_fief_id:
            state.selected_settlement = h["primary_tile"]
            state.selected_province = h["province"]
            state.selected_army_id = None
    
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
    active_enemy_cap = state.get_realm_capital(state.enemy_id)

    # Province Name Labels (Medieval Plaque / Banner)
    for pid, (lx, ly) in province_anchors.items():
        p_data = PROVINCES.get(pid)
        if p_data:
            short_name = p_data["name"].split()[0]
            is_player_cap = (pid == active_player_cap)
            is_enemy_cap = (pid == active_enemy_cap)
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
            pct = army.move_progress / 100.0
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
    # DRAW ARMIES ON MAP (Waving War Banners & Troop Standard)
    # ---------------------------------------------------------
    anim_ticks = pygame.time.get_ticks()
    
    for army in state.armies:
        tc, tr = getattr(army, "tile", get_province_capital_tile(army.province))
        cx = origin_x + (tc * curr_tile_w) + (curr_tile_w // 2)
        cy = origin_y + (tr * curr_tile_h) + (curr_tile_h // 2)
    
        # If moving, interpolate position smoothly along route
        if army.is_moving and getattr(army, "next_tile", None) and not army.in_battle:
            nc, nr = army.next_tile
            nx = origin_x + (nc * curr_tile_w) + (curr_tile_w // 2)
            ny = origin_y + (nr * curr_tile_h) + (curr_tile_h // 2)
            pct = army.move_progress / 100.0
            cx = int(cx + (nx - cx) * pct)
            cy = int(cy + (ny - cy) * pct)
    
        is_player = (army.owner == state.player_id)
        is_sel_army = (army.id == state.selected_army_id or army.id in state.selected_army_ids)
    
        # Current tile scale relative to base tile size (tracks camera zoom perfectly!)
        tile_scale = curr_tile_w / BASE_TILE_W
    
        # RTS Golden Ground Selection Ring (scaled to 1.4 tiles)
        if is_sel_army:
            ring_w = int(curr_tile_w * 1.4)
            ring_h = int(curr_tile_h * 0.42)
            sel_surf = pygame.Surface((ring_w, ring_h), pygame.SRCALPHA)
            pygame.draw.ellipse(sel_surf, (240, 195, 50, 190), (0, 0, ring_w, ring_h), 2)
            screen.blit(sel_surf, (cx - ring_w // 2, cy - ring_h // 2))
    
        # -------------------------------------------------------------
        # STANDARDIZED 2-TILE BANNER HIERARCHY:
        # Entire unit cluster is dynamically scaled to fit within ~2 tiles width
        # across all zoom levels, keeping all standards visible and proportional.
        # -------------------------------------------------------------
        n_sub = len(army.sub_flags)
    
        # Main banner dimensions
        if n_sub == 0:
            cw_main = max(16, int(26 * tile_scale))
            ch_main = max(11, int(18 * tile_scale))
            pole_h_main = max(22, int(34 * tile_scale))
        else:
            cw_main = max(15, int(22 * tile_scale))
            ch_main = max(10, int(15 * tile_scale))
            pole_h_main = max(20, int(30 * tile_scale))
    
        # Sub-banner dimensions (scaled slightly if army has many merged contingents)
        if n_sub <= 2:
            sub_factor = 1.0
        else:
            sub_factor = max(0.68, 1.0 - (n_sub - 2) * 0.05)
    
        cw_sub = max(9, int(14 * tile_scale * sub_factor))
        ch_sub = max(6, int(10 * tile_scale * sub_factor))
        pole_h_sub = max(13, int(20 * tile_scale * sub_factor))
    
        banner_draw_queue = []
        # Grand standard in center (dy = 0)
        banner_draw_queue.append((0, True, army.flag_origin, cx, cy, 0, cw_main, ch_main, pole_h_main))
    
        # Sub contingents encircling the grand standard within the 2-tile footprint
        for idx, sf in enumerate(army.sub_flags):
            side = -1 if (idx % 2 == 0) else 1
            rank = idx // 2
            
            if rank == 0:
                dx = int(side * curr_tile_w * 0.28)
                dy = int(2 * tile_scale)
            elif rank == 1:
                dx = int(side * curr_tile_w * 0.52)
                dy = int(-3 * tile_scale)
            elif rank == 2:
                dx = int(side * curr_tile_w * 0.70)
                dy = int(1 * tile_scale)
            elif rank == 3:
                dx = int(side * curr_tile_w * 0.38)
                dy = int(-8 * tile_scale)
            else:
                dx = int(side * curr_tile_w * (0.50 + (rank % 3) * 0.12))
                dy = int(-6 * tile_scale)
    
            banner_draw_queue.append((dy, False, sf, cx + dx, cy + dy, (idx + 1) * 750, cw_sub, ch_sub, pole_h_sub))
    
        # Sort by depth so background banners render behind foreground banners
        banner_draw_queue.sort(key=lambda b: b[0])
    
        for dy, is_main, f_id, px, py, t_off, b_cw, b_ch, b_ph in banner_draw_queue:
            c_surf = get_scaled_banner_cloth(f_id, b_cw, b_ch, is_large=is_main)
            draw_waving_banner(screen, c_surf, px, py, pole_h=b_ph, ticks=anim_ticks + t_off, amp=max(1.2, (3.0 if is_main else 1.8) * (b_cw / 30.0)), freq=0.25 if is_main else 0.30, is_main=is_main)
    
        # -------------------------------------------------------------
        # Sleek Troop Count Pill Under Standard Base (No Clunky Red Box)
        # -------------------------------------------------------------
        txt_badge = f"{army.troops:,}"
        if army.in_battle:
            txt_badge = f"⚔ {army.troops:,}"
            p_bg = (185, 35, 35)
            p_border = (255, 220, 50)
        elif army.courier_en_route:
            txt_badge = f"✉ Summons ({army.courier_days_left}d + {army.muster_days}d)"
            p_bg = (55, 42, 18)
            p_border = (245, 205, 70)
        elif army.is_mustering:
            txt_badge = f" {army.muster_days}d ({army.troops:,})"
            p_bg = (65, 52, 20)
            p_border = COLOR_GOLD
        elif army.is_demobilizing:
            txt_badge = f"◆ HOME ({army.troops:,})"
            p_bg = (30, 48, 70)
            p_border = (120, 180, 240)
        elif army.is_sieging:
            if army.siege_target_name:
                clean_name = army.siege_target_name
                for pfx in ["Royal City of ", "Royal Citadel of ", "Royal Castle of ", "Royal Borough of ", "Royal "]:
                    clean_name = clean_name.replace(pfx, "")
                t_str = clean_name[:12]
            else:
                t_str = "City"
            txt_badge = f"⚑ {army.siege_progress}% {t_str}"
            p_bg = (155, 85, 25)
            p_border = COLOR_GOLD
        elif is_sel_army:
            p_bg = (175, 30, 30) if is_player else (35, 55, 95)
            p_border = COLOR_GOLD
        else:
            p_bg = (24, 28, 38)
            p_border = (165, 45, 45) if is_player else (65, 95, 145)
    
        lbl = font_xs.render(txt_badge, True, COLOR_TEXT_WHITE if not is_sel_army else (255, 235, 140))
        tw = lbl.get_width()
        pw = max(int(36 * tile_scale), tw + 8)
        ph = 16
        px_pill = cx - pw // 2
        py_pill = cy + max(2, int(4 * tile_scale))
    
        pill_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pill_surf.fill((*p_bg, 225))
        pygame.draw.rect(pill_surf, p_border, (0, 0, pw, ph), 2 if is_sel_army else 1, border_radius=4)
        screen.blit(pill_surf, (px_pill, py_pill))
        screen.blit(lbl, (px_pill + (pw - tw) // 2, py_pill + 1))
    
        # Hitbox covering all banners + pill for natural mouse selection
        all_x = [cx, cx + cw_main, px_pill, px_pill + pw]
        for dy_val, is_m, sf, b_px, b_py, t_off, b_cw, b_ch, b_ph in banner_draw_queue:
            all_x.extend([b_px - 2, b_px + b_cw + 2])
        min_x = min(all_x) - 4
        max_x = max(all_x) + 4
        hit_rect = pygame.Rect(min_x, cy - pole_h_main - 6, max_x - min_x, (py_pill + ph + 4) - (cy - pole_h_main - 6))
    
        is_badge_hover = hit_rect.collidepoint(mouse_pos)
    
        # Click banner or count pill to select army
        if mouse_clicked and is_badge_hover:
            state.selected_army_id = army.id
            state.selected_province = army.province
    
    # -------------------------------------------------------------
    # DRAW TRAVELLING ROYAL COURIERS (Riders Galloping Between Shires)
    # -------------------------------------------------------------
    for army in state.armies:
        if army.courier_en_route and army.courier_current_prov and army.courier_next_prov:
            c_pos = province_anchors.get(army.courier_current_prov)
            n_pos = province_anchors.get(army.courier_next_prov)
            dest_pos = province_anchors.get(army.province)
            if c_pos and n_pos:
                pct = army.courier_progress / 100.0
                mx = int(c_pos[0] + (n_pos[0] - c_pos[0]) * pct)
                my = int(c_pos[1] + (n_pos[1] - c_pos[1]) * pct)
                
                is_player = (army.owner == state.player_id)
                dest_name = PROVINCES[army.province]["name"].split()[0]
                
                # Subtle guide line connecting courier to destination
                if dest_pos:
                    guide_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                    pygame.draw.line(guide_surf, (250, 215, 80, 85) if is_player else (120, 180, 255, 85), (mx, my), dest_pos, 2)
                    screen.blit(guide_surf, (0, 0))
                
                # Galloping Courier Pill Badge
                c_text = f"✉ Courier -> {dest_name} ({army.courier_days_left}d left)"
                c_lbl = font_xs.render(c_text, True, (255, 240, 180) if is_player else (220, 240, 255))
                cw = c_lbl.get_width() + 16
                ch = 18
                
                c_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
                c_surf.fill((25, 20, 10, 230) if is_player else (15, 22, 35, 230))
                pygame.draw.rect(c_surf, COLOR_GOLD if is_player else (100, 160, 240), (0, 0, cw, ch), 1, border_radius=9)
                c_surf.blit(c_lbl, (8, 1))
                screen.blit(c_surf, (mx - cw // 2, my - 24))
                
                # Gold / Blue courier marker pip
                pygame.draw.circle(screen, COLOR_GOLD if is_player else (100, 160, 240), (mx, my), 5)
                pygame.draw.circle(screen, (255, 255, 255), (mx, my), 2)
    
    # Victory / Defeat Banner
    if wessex_count == total_provs:
        vic_rect = pygame.Rect(340, 260, 480, 110)
        pygame.draw.rect(screen, (20, 50, 25), vic_rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_GOLD, vic_rect, 3, border_radius=8)
        vb_title = font_banner.render("VICTORY!", True, COLOR_GOLD)
        vb_sub = font_md.render("All Britain is united under King Alfred!", True, COLOR_TEXT_WHITE)
        screen.blit(vb_title, (vic_rect.x + (vic_rect.w - vb_title.get_width()) // 2, vic_rect.y + 18))
        screen.blit(vb_sub, (vic_rect.x + (vic_rect.w - vb_sub.get_width()) // 2, vic_rect.y + 65))
    elif danelaw_count == total_provs:
        def_rect = pygame.Rect(340, 260, 480, 110)
        pygame.draw.rect(screen, (50, 20, 25), def_rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_TEXT_RED, def_rect, 3, border_radius=8)
        db_title = font_banner.render("DEFEAT!", True, COLOR_TEXT_RED)
        db_sub = font_md.render("Wessex has fallen to the Viking conquerors.", True, COLOR_TEXT_WHITE)
        screen.blit(db_title, (def_rect.x + (def_rect.w - db_title.get_width()) // 2, def_rect.y + 18))
        screen.blit(db_sub, (def_rect.x + (def_rect.w - db_sub.get_width()) // 2, def_rect.y + 65))
    
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
    
    # Unclip screen so right panel and remaining UI render normally across the whole display
    screen.set_clip(None)
    
