"""
Popup Modals & Dossiers (Build Petition, Grant Fief, Vassal Dossier, Sovereign Dossier, Confirm Build)
"""
import random
import pygame
from game.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, BASE_TILE_H, VIEWPORT_CENTER_Y, COLOR_PANEL_BG, COLOR_PANEL_BORDER,
    COLOR_GOLD, COLOR_TEXT_WHITE, COLOR_TEXT_MUTED, COLOR_TEXT_RED,
    COLOR_TEXT_GREEN, COLOR_BUTTON_NORMAL, COLOR_BUTTON_HOVER,
    COLOR_BUTTON_ACTIVE, BASE_TILE_W, VIEWPORT_CENTER_X
)
from game.data.characters import CHARACTERS
from game.data.provinces import PROVINCES
from game.core.map import PROV_CAPITAL_TILES, CELL_TO_PROV
from game.data.buildings import BUILDING_SPECS
from game.core.assets import prov_flag_cache
from game.systems.economy import get_vassal_landed_status, sync_province_holdings_stats, fmt_gold

def render_modals(screen, state, mouse_pos, modal_mouse_clicked, fonts, portrait_cache, coa_cache):
    font_xs = fonts["xs"]
    font_sm = fonts["sm"]
    font_md = fonts["md"]
    font_lg = fonts["lg"]

    curr_tile_w = max(18, int(BASE_TILE_W * state.zoom))

    curr_tile_h = max(16, int(BASE_TILE_H * state.zoom))
    curr_tw = curr_tile_w
    curr_th = curr_tile_h

    # ---------------------------------------------------------
    # 5. VASSAL AUTONOMOUS BUILD PETITION POPUP MODAL
    # ---------------------------------------------------------
    if state.vassal_build_requests:
        req = state.vassal_build_requests[0]
        # Darkened backdrop
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 160))
        screen.blit(dim_surf, (0, 0))
    
        pop_w, pop_h = 520, 230
        pop_x = (WINDOW_WIDTH - pop_w) // 2
        pop_y = (WINDOW_HEIGHT - pop_h) // 2
        pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)
    
        pygame.draw.rect(screen, COLOR_PANEL_BG, pop_rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_GOLD, pop_rect, 2, border_radius=8)
    
        screen.blit(font_lg.render("ROYAL PETITION FROM VASSAL", True, COLOR_GOLD), (pop_x + 25, pop_y + 20))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 25, pop_y + 55), (pop_x + pop_w - 25, pop_y + 55), 1)
    
        fief_label = req.get("fief_name") or "their fief"
        b_tiles = req.get("build_tiles", [])
        req_type = req.get("build_type", "city")
        req_cost = req.get("cost", BUILDING_SPECS.get(req_type, {}).get("cost", 600))
        req_name = BUILDING_SPECS.get(req_type, {}).get("title", "Holding")
    
        t1 = font_sm.render(f"My Liege, {req['vassal']} humbly requests your royal charter", True, COLOR_TEXT_WHITE)
        t2 = font_sm.render(f"to construct a {req_name} inside {fief_label}.", True, COLOR_TEXT_WHITE)
        t3 = font_xs.render(f"• Granting Charter: Vassal pays {req_cost}g, boosts provincial prosperity.", True, COLOR_TEXT_GREEN)
        t4 = font_xs.render(f"• Location: {len(b_tiles)} vacant tile(s) strictly inside {fief_label} ({req['province_name']}).", True, COLOR_GOLD)
    
        screen.blit(t1, (pop_x + 25, pop_y + 70))
        screen.blit(t2, (pop_x + 25, pop_y + 92))
        screen.blit(t3, (pop_x + 25, pop_y + 122))
        screen.blit(t4, (pop_x + 25, pop_y + 142))
    
        # Approve Button
        app_btn = pygame.Rect(pop_x + 35, pop_y + 170, 210, 38)
        app_hov = app_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (35, 110, 55) if app_hov else (25, 80, 40), app_btn, border_radius=6)
        pygame.draw.rect(screen, COLOR_TEXT_GREEN, app_btn, 1, border_radius=6)
        screen.blit(font_md.render("GRANT CHARTER (YES)", True, COLOR_TEXT_WHITE), (pop_x + 48, pop_y + 178))
    
        # Deny Button
        den_btn = pygame.Rect(pop_x + 275, pop_y + 170, 210, 38)
        den_hov = den_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (110, 35, 35) if den_hov else (80, 25, 25), den_btn, border_radius=6)
        pygame.draw.rect(screen, COLOR_TEXT_RED, den_btn, 1, border_radius=6)
        screen.blit(font_md.render("DENY REQUEST (NO)", True, COLOR_TEXT_WHITE), (pop_x + 295, pop_y + 178))
    
        if modal_mouse_clicked and app_hov:
            pid = req["province_id"]
            p_obj = PROVINCES.get(pid)
            if p_obj:
                if req_type == "city":
                    city_title = f"{req['vassal'].split()[1]}'s {random.choice(['Borough', 'Burgh', 'Town', 'Market'])}"
                else:
                    city_title = f"{req['vassal'].split()[1]}'s {random.choice(['Keep', 'Castle', 'Fortress'])}"
    
                req["vassal_ref"]["gold"] = max(0, req["vassal_ref"]["gold"] - req_cost)
    
                # Construct holding strictly on free tiles within this vassal's owned fief!
                b_tiles = req.get("build_tiles", [])
                state.settlement_id_counter += 1
                s_id = f"settlement_{state.settlement_id_counter}"
                for t in b_tiles:
                    state.settlements[t] = {
                        "id": s_id,
                        "province": pid,
                        "type": req_type,
                        "name": city_title,
                        "lord": req["vassal"],
                        "vassal_id": req["vassal_ref"]["id"],
                        "is_crown_demesne": False,
                        "is_crown_fief": False,
                        "level": 0
                    }
                    if "tiles" not in req["vassal_ref"]:
                        req["vassal_ref"]["tiles"] = []
                    if t not in req["vassal_ref"]["tiles"]:
                        req["vassal_ref"]["tiles"].append(t)
    
                if not req["vassal_ref"].get("city_name"):
                    req["vassal_ref"]["city_name"] = city_title
    
                sync_province_holdings_stats(state, pid)
                st = get_vassal_landed_status(state, req["vassal_ref"], pid)
                req["vassal_ref"]["tax_contribution"] = st["tax_paid"]
                req["vassal_ref"]["levy_contribution"] = st["levy_contribution"]
    
                state.logs.append(f"Granted charter! {req['vassal']} established {city_title} ({req_name}) inside {fief_label}.")
            state.vassal_build_requests.pop(0)
    
        elif modal_mouse_clicked and den_hov:
            state.logs.append(f"Denied charter to {req['vassal']}. Funds remain unspent.")
            state.vassal_build_requests.pop(0)
    
    # ---------------------------------------------------------
    # 6. GRANT FIEFDOM TO VASSAL SELECTION MODAL
    # ---------------------------------------------------------
    if state.granting_fief_id and state.granting_fief_id in state.fiefs:
        f_target = state.fiefs[state.granting_fief_id]
        
        # Dimmed backdrop
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 175))
        screen.blit(dim_surf, (0, 0))
    
        pop_w, pop_h = 600, 480
        pop_x = (WINDOW_WIDTH - pop_w) // 2
        pop_y = (WINDOW_HEIGHT - pop_h) // 2
        pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)
    
        pygame.draw.rect(screen, COLOR_PANEL_BG, pop_rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_GOLD, pop_rect, 2, border_radius=8)
    
        # Header
        screen.blit(font_lg.render("ROYAL INVESTITURE: GRANT FIEFDOM", True, COLOR_GOLD), (pop_x + 25, pop_y + 18))
        p_name = PROVINCES.get(f_target['province'], {}).get('name', 'Province')
        t_sub = font_sm.render(f"Bestow: {f_target['name']} ({len(f_target['tiles'])} Tiles in {p_name})", True, COLOR_TEXT_WHITE)
        screen.blit(t_sub, (pop_x + 25, pop_y + 48))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 25, pop_y + 72), (pop_x + pop_w - 25, pop_y + 72), 1)
    
        # Collect Vassal Candidates: Local vassals first, then wider realm
        local_vassals = state.vassals.get(f_target["province"], [])
        other_vassals = []
        for pid, prov in PROVINCES.items():
            if prov["owner"] == state.player_id and pid != f_target["province"]:
                for v in state.vassals.get(pid, []):
                    other_vassals.append((pid, v))
        
        candidates = [(f_target["province"], v, True) for v in local_vassals]
        candidates += [(pid, v, False) for (pid, v) in other_vassals]
    
        if not candidates:
            screen.blit(font_md.render("No eligible vassals found in the realm.", True, COLOR_TEXT_MUTED), (pop_x + 40, pop_y + 120))
        else:
            # Pagination (3 vassals per page)
            page_size = 3
            total_pages = max(1, (len(candidates) + page_size - 1) // page_size)
            state.grant_page = max(0, min(state.grant_page, total_pages - 1))
            start_i = state.grant_page * page_size
            page_candidates = candidates[start_i:start_i + page_size]
    
            vy = pop_y + 85
            for c_pid, c_v, is_loc in page_candidates:
                c_rect = pygame.Rect(pop_x + 25, vy, pop_w - 50, 92)
                is_c_hov = c_rect.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (45, 52, 68) if is_c_hov else (34, 40, 54), c_rect, border_radius=6)
                pygame.draw.rect(screen, (80, 130, 200) if is_loc else COLOR_PANEL_BORDER, c_rect, 1, border_radius=6)
    
                # Vassal title & name
                v_title_str = f"♚ {c_v['name']}"
                screen.blit(font_md.render(v_title_str, True, COLOR_GOLD), (pop_x + 40, vy + 10))
                
                # Locality & holdings
                loc_str = f"Home: {PROVINCES[c_pid]['name'].split()[0]}" + (" (Local Vassal)" if is_loc else " (Realm Lord)")
                n_held_fiefs = sum(1 for f in state.fiefs.values() if f.get("holder") == c_v["name"])
                status_str = f"{loc_str}  •  Holds {n_held_fiefs} Fief(s)"
                screen.blit(font_xs.render(status_str, True, (150, 210, 255) if is_loc else COLOR_TEXT_MUTED), (pop_x + 40, vy + 34))
    
                st_cv = get_vassal_landed_status(state, c_v, f_target.get("province"))
                if st_cv["is_landed"]:
                    econ_str = f"Treasury: {c_v.get('gold', 150)}g  •  Levy Support: +{st_cv['levy_contribution']} soldiers"
                else:
                    econ_str = f"Treasury: {c_v.get('gold', 150)}g  •  Status: Landless Noble (Unlanded)"
                screen.blit(font_xs.render(econ_str, True, COLOR_TEXT_GREEN if st_cv["is_landed"] else COLOR_TEXT_MUTED), (pop_x + 40, vy + 56))
    
                # Grant Button
                g_btn = pygame.Rect(pop_x + pop_w - 180, vy + 28, 140, 36)
                b_g_hov = g_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 140, 70) if b_g_hov else (28, 100, 50), g_btn, border_radius=6)
                pygame.draw.rect(screen, COLOR_TEXT_GREEN, g_btn, 1, border_radius=6)
                screen.blit(font_sm.render("BESTOW FIEF ⚔", True, COLOR_TEXT_WHITE), (pop_x + pop_w - 170, vy + 37))
    
                if modal_mouse_clicked and b_g_hov:
                    # Assign Fief
                    f_target["holder"] = c_v["name"]
                    f_target["vassal_id"] = c_v["id"]
                    f_target["is_crown_demesne"] = False
                    f_target["is_newly_carved"] = False
                    v_short_name = c_v["name"].split()[1] if len(c_v["name"].split()) > 1 else c_v["name"]
                    f_target["name"] = f"Barony of {v_short_name}"
    
                    # Update all city settlements located on this fief to the chosen vassal!
                    for t in f_target["tiles"]:
                        if t in state.settlements:
                            state.settlements[t]["lord"] = c_v["name"]
                            state.settlements[t]["vassal_id"] = c_v["id"]
                            state.settlements[t]["is_crown_demesne"] = False
                            state.settlements[t]["is_crown_fief"] = False
                    
                    # Update Vassal details
                    if "tiles" not in c_v:
                        c_v["tiles"] = []
                    for t in f_target["tiles"]:
                        if t not in c_v["tiles"]:
                            c_v["tiles"].append(t)
                    c_v["gold"] = c_v.get("gold", 150) + 100
                    if not c_v.get("city_name"):
                        c_v["city_name"] = f_target["name"]
                    st_new = get_vassal_landed_status(state, c_v, f_target["province"])
                    c_v["tax_contribution"] = st_new["tax_paid"]
                    c_v["levy_contribution"] = st_new["levy_contribution"]
                    sync_province_holdings_stats(state, f_target["province"])
                    
                    state.logs.append(f"Royal Investiture: Bestowed {f_target['name']} upon {c_v['name']} (+100g)!")
                    state.granting_fief_id = None
                    break
    
                vy += 100
    
            # Pagination Controls
            if total_pages > 1:
                pg_str = font_xs.render(f"Page {state.grant_page + 1} of {total_pages}", True, COLOR_TEXT_MUTED)
                screen.blit(pg_str, (pop_x + pop_w // 2 - pg_str.get_width() // 2, pop_y + 395))
    
                if state.grant_page > 0:
                    prev_btn = pygame.Rect(pop_x + 140, pop_y + 390, 80, 26)
                    p_hov = prev_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (55, 62, 78) if p_hov else (38, 44, 56), prev_btn, border_radius=4)
                    screen.blit(font_xs.render("← Prev", True, COLOR_TEXT_WHITE), (pop_x + 158, pop_y + 395))
                    if modal_mouse_clicked and p_hov:
                        state.grant_page -= 1
    
                if state.grant_page < total_pages - 1:
                    next_btn = pygame.Rect(pop_x + pop_w - 220, pop_y + 390, 80, 26)
                    n_hov = next_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (55, 62, 78) if n_hov else (38, 44, 56), next_btn, border_radius=4)
                    screen.blit(font_xs.render("Next →", True, COLOR_TEXT_WHITE), (pop_x + pop_w - 202, pop_y + 395))
                    if modal_mouse_clicked and n_hov:
                        state.grant_page += 1
    
        # Close / Cancel Button
        close_btn = pygame.Rect(pop_x + (pop_w - 200) // 2, pop_y + pop_h - 45, 200, 32)
        c_hov = close_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (75, 35, 35) if c_hov else (55, 25, 25), close_btn, border_radius=6)
        pygame.draw.rect(screen, (220, 80, 80), close_btn, 1, border_radius=6)
        screen.blit(font_sm.render("CANCEL INVESTITURE", True, (255, 220, 220)), (pop_x + (pop_w - 200) // 2 + 25, pop_y + pop_h - 38))
        if modal_mouse_clicked and c_hov:
            state.granting_fief_id = None
    
    # ---------------------------------------------------------
    # 7. VASSAL PROFILE & FEUDAL DOSSIER MODAL
    # ---------------------------------------------------------
    if state.inspecting_vassal:
        v_pid = state.inspecting_vassal.get("province")
        v_obj = state.inspecting_vassal.get("vassal")
    
        # Dimmed backdrop
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 185))
        screen.blit(dim_surf, (0, 0))
    
        pop_w, pop_h = 780, 540
        pop_x = (WINDOW_WIDTH - pop_w) // 2
        pop_y = (WINDOW_HEIGHT - pop_h) // 2
        pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)
    
        pygame.draw.rect(screen, COLOR_PANEL_BG, pop_rect, border_radius=10)
        pygame.draw.rect(screen, COLOR_GOLD, pop_rect, 2, border_radius=10)
    
        # Close 'X' Button at top right
        x_btn = pygame.Rect(pop_x + pop_w - 38, pop_y + 12, 26, 26)
        x_hov = x_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (85, 30, 30) if x_hov else (48, 22, 22), x_btn, border_radius=4)
        pygame.draw.rect(screen, (225, 80, 80), x_btn, 1, border_radius=4)
        x_lbl = font_sm.render("✕", True, COLOR_TEXT_WHITE)
        screen.blit(x_lbl, (x_btn.x + 7, x_btn.y + 3))
        if modal_mouse_clicked and x_hov:
            state.inspecting_vassal = None
    
        prov_data = PROVINCES.get(v_pid, {})
        p_owner = prov_data.get("owner", state.player_id)
        liege_char = CHARACTERS.get(p_owner, state.player)
        is_enemy = (p_owner != state.player_id)
    
        # Header Title
        title_text = "ENEMY VASSAL DOSSIER" if is_enemy else "FEUDAL VASSAL DOSSIER"
        title_col = (255, 110, 110) if is_enemy else COLOR_GOLD
        screen.blit(font_lg.render(title_text, True, title_col), (pop_x + 25, pop_y + 16))
        p_full = prov_data.get("name", "Capital")
        sub_text = f"Feudal Subject of {liege_char['name']} ({liege_char['realm']}) • Province of {p_full}"
        screen.blit(font_xs.render(sub_text, True, (255, 180, 180) if is_enemy else COLOR_TEXT_MUTED), (pop_x + 25, pop_y + 44))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 25, pop_y + 64), (pop_x + pop_w - 25, pop_y + 64), 1)
    
        # Top Character Banner Section
        # Crest / Heraldic Flag
        emblem = prov_flag_cache.get(v_pid)
        if emblem:
            screen.blit(pygame.transform.smoothscale(emblem, (44, 50)), (pop_x + 30, pop_y + 74))
        else:
            pygame.draw.rect(screen, (50, 60, 80), (pop_x + 30, pop_y + 74, 44, 50), border_radius=4)
    
        v_status = get_vassal_landed_status(state, v_obj, v_pid)
        held_fiefs = v_status["held_fiefs"]
        total_held_tiles = v_status["total_tiles"]
        is_landed = v_status["is_landed"]
        tax_rate = v_status["tax_rate"]
        tax_paid = v_status["tax_paid"]
        monthly_gross = v_status["gross_income"]
        net_profit = v_status["net_savings"]
        levy_rate = v_status.get("levy_rate", 20)
        levies_contrib = v_status["levy_contribution"]
        household_guard = v_status.get("household_guard", 0)
        total_garrison = v_status.get("total_garrison", 0)
    
        # Name and Titles
        is_direct = v_obj.get("is_direct_vassal", True)
        rk_val = str(v_obj.get("rank", "count" if is_direct else "baron")).lower()
        rk_sym = "🛡" if ("count" in rk_val or "thane" in rk_val or "warden" in rk_val) else ("⚜" if "duke" in rk_val else "🏰")
        screen.blit(font_md.render(f"{rk_sym} {v_obj['name']}", True, (255, 120, 120) if is_enemy else COLOR_GOLD), (pop_x + 90, pop_y + 74))
        v_religion = "Norse Pagan" if p_owner == state.enemy_id else prov_data.get("faith", "Catholic")
        v_culture = "Norse" if p_owner == state.enemy_id else prov_data.get("culture", "Anglo-Saxon")
        feud_role = "Direct Province Liege" if is_direct else "Sub-Vassal (Barony)"
        rank_str = f"Feudal Rank: {v_obj.get('title', 'Count')} ({feud_role})  •  Faith: {v_religion} ({v_culture})"
        screen.blit(font_xs.render(rank_str, True, COLOR_TEXT_WHITE), (pop_x + 90, pop_y + 98))
        seat_str = f"Seat of Power: {v_obj.get('city_name')}" if is_landed and v_obj.get('city_name') else "Seat of Power: Landless Subject"
        if is_direct and v_obj.get("sub_vassals"):
            seat_str += f"  •  Retinue: 👥 {len(v_obj['sub_vassals'])} Barons"
        screen.blit(font_xs.render(seat_str, True, (140, 205, 255)), (pop_x + 90, pop_y + 114))
    
        # Feudal Attributes Grid (Martial, Stewardship, Diplomacy, Feudal Oath)
        oath_val = f"100% ({liege_char['name'].split()[1]})" if is_enemy else "100%"
        oath_sub = "(Enemy)" if is_enemy else "(Faithful)"
        stats_list = [
            ("⚔ Martial", f"{10 + (levies_contrib // 30)}" if is_landed else "8", "(Commands Fyrd)"),
            ("◆ Stewardship", f"{11 + int(round(tax_paid * 2))}" if is_landed else "9", "(Manages Estates)"),
            ("◆ Diplomacy", "11" if is_enemy else "13", "(Foreign Court)" if is_enemy else "(Royal Harmony)"),
            ("⚔ Feudal Oath", oath_val, oath_sub)
        ]
        box_w = 175
        for s_i, (s_name, s_val, s_sub) in enumerate(stats_list):
            bx = pop_x + 25 + s_i * 185
            by = pop_y + 138
            b_rect = pygame.Rect(bx, by, box_w, 44)
            pygame.draw.rect(screen, (34, 40, 54), b_rect, border_radius=4)
            pygame.draw.rect(screen, (160, 60, 60) if is_enemy else COLOR_PANEL_BORDER, b_rect, 1, border_radius=4)
            screen.blit(font_xs.render(s_name, True, COLOR_TEXT_MUTED), (bx + 8, by + 4))
            v_surf = font_md.render(s_val, True, (255, 120, 120) if is_enemy else COLOR_GOLD)
            screen.blit(v_surf, (bx + 8, by + 18))
            screen.blit(font_xs.render(s_sub, True, (120, 160, 200)), (bx + 12 + v_surf.get_width(), by + 22))
    
        # Two Main Columns: Economy & Treasury (Left), Military & Fiefs (Right)
        col_w = 355
        col_y = pop_y + 194

        # LEFT COLUMN: ECONOMY & INCOME
        left_rect = pygame.Rect(pop_x + 25, col_y, col_w, 245)
        pygame.draw.rect(screen, (30, 36, 48), left_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, left_rect, 1, border_radius=6)

        lx = pop_x + 38
        screen.blit(font_md.render("◆ Vassal Finances & Revenue", True, COLOR_GOLD), (lx, col_y + 10))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (lx, col_y + 32), (pop_x + 25 + col_w - 15, col_y + 32), 1)

        screen.blit(font_sm.render(f"Treasury: {fmt_gold(v_obj['gold'])} Gold", True, COLOR_GOLD), (lx, col_y + 40))

        # Breakdown of monthly finances
        if is_landed:
            screen.blit(font_xs.render(f"• Gross Domain Income: +{fmt_gold(monthly_gross)}g / month", True, (160, 220, 180)), (lx, col_y + 66))
            screen.blit(font_xs.render("  (From tenant rents, tolls & agricultural yield)", True, COLOR_TEXT_MUTED), (lx, col_y + 82))
            screen.blit(font_xs.render(f"• Royal Feudal Tax ({tax_rate}%): -{fmt_gold(tax_paid)}g/m", True, COLOR_TEXT_RED if tax_paid > 0 else COLOR_TEXT_MUTED), (lx, col_y + 102))

            # Interactive Tax Controls in Dossier (Player only)
            if not is_enemy:
                d_t_dec = pygame.Rect(pop_x + 25 + col_w - 110, col_y + 100, 18, 18)
                d_t_inc = pygame.Rect(pop_x + 25 + col_w - 90, col_y + 100, 18, 18)
                d_t_lock = pygame.Rect(pop_x + 25 + col_w - 70, col_y + 100, 60, 18)

                h_t_dec = d_t_dec.collidepoint(mouse_pos)
                h_t_inc = d_t_inc.collidepoint(mouse_pos)
                h_t_lock = d_t_lock.collidepoint(mouse_pos)

                is_t_locked = v_obj.get("tax_locked", False)
                pygame.draw.rect(screen, (70, 80, 100) if h_t_dec else (42, 48, 62), d_t_dec, border_radius=3)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, d_t_dec, 1, border_radius=3)
                screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE), (d_t_dec.x + 6, col_y + 100))

                pygame.draw.rect(screen, (70, 80, 100) if h_t_inc else (42, 48, 62), d_t_inc, border_radius=3)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, d_t_inc, 1, border_radius=3)
                screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE), (d_t_inc.x + 5, col_y + 100))

                l_t_bg = (65, 50, 20) if is_t_locked else ((45, 52, 68) if h_t_lock else (28, 34, 46))
                l_t_bd = COLOR_GOLD if is_t_locked else ((120, 160, 210) if h_t_lock else (70, 80, 95))
                pygame.draw.rect(screen, l_t_bg, d_t_lock, border_radius=3)
                pygame.draw.rect(screen, l_t_bd, d_t_lock, 1, border_radius=3)
                l_t_txt = "◈ LOCKED" if is_t_locked else "◇ UNLOCK"
                l_t_col = COLOR_GOLD if is_t_locked else COLOR_TEXT_MUTED
                l_t_lbl = font_xs.render(l_t_txt, True, l_t_col)
                screen.blit(l_t_lbl, (d_t_lock.x + (d_t_lock.w - l_t_lbl.get_width()) // 2, col_y + 101))

                if modal_mouse_clicked:
                    if h_t_lock:
                        v_obj["tax_locked"] = not is_t_locked
                        state.logs.append(f"Feudal Law: {v_obj['name']}'s tax rate is now {'LOCKED' if v_obj['tax_locked'] else 'UNLOCKED'}.")
                    elif h_t_dec:
                        v_obj["tax_rate"] = max(0, tax_rate - 5)
                        st_new = get_vassal_landed_status(state, v_obj, v_pid)
                        v_obj["tax_contribution"] = st_new["tax_paid"]
                        sync_province_holdings_stats(state, v_pid)
                        state.logs.append(f"Decreased {v_obj['name']}'s tax obligation to {v_obj['tax_rate']}%.")
                    elif h_t_inc:
                        v_obj["tax_rate"] = min(90, tax_rate + 5)
                        st_new = get_vassal_landed_status(state, v_obj, v_pid)
                        v_obj["tax_contribution"] = st_new["tax_paid"]
                        sync_province_holdings_stats(state, v_pid)
                        state.logs.append(f"Increased {v_obj['name']}'s tax obligation to {v_obj['tax_rate']}%.")

            screen.blit(font_xs.render(f"  (Directly enriches {liege_char['name']}'s treasury)", True, COLOR_TEXT_MUTED), (lx, col_y + 120))
            screen.blit(font_xs.render(f"• Net Monthly Savings: +{fmt_gold(net_profit)}g / month", True, COLOR_TEXT_GREEN), (lx, col_y + 138))
        else:
            screen.blit(font_xs.render("• Gross Domain Income: 0g / month", True, COLOR_TEXT_MUTED), (lx, col_y + 66))
            screen.blit(font_xs.render("  (Landless noble holds no estates or tolls)", True, COLOR_TEXT_MUTED), (lx, col_y + 82))
            screen.blit(font_xs.render(f"• Feudal Royal Tax ({tax_rate}%): 0g / month", True, COLOR_TEXT_MUTED), (lx, col_y + 102))
            screen.blit(font_xs.render(f"  (No domain revenue subject to royal taxation)", True, COLOR_TEXT_MUTED), (lx, col_y + 120))
            screen.blit(font_xs.render("• Net Monthly Savings: 0g / month", True, COLOR_TEXT_MUTED), (lx, col_y + 138))

        # Autonomous Feudal Construction Fund (City 600g, Barracks 800g, Fort 1000g)
        v_gold_val = v_obj.get('gold', 0)
        c_city = BUILDING_SPECS["city"]["cost"]       # 600
        c_barrack = BUILDING_SPECS["barrack"]["cost"] # 800
        c_fort = BUILDING_SPECS["fort"]["cost"]       # 1000

        if v_gold_val >= c_fort:
            target_cost = c_fort
            target_name = "Fortress"
        elif v_gold_val >= c_barrack:
            target_cost = c_barrack
            target_name = "Barracks"
        else:
            target_cost = c_city
            target_name = "Commercial City"

        screen.blit(font_xs.render(f"• Autonomy Construction Fund ({target_cost}g for {target_name}):", True, COLOR_GOLD), (lx, col_y + 164))
        bar_w = col_w - 30
        bar_h = 16
        bx = lx
        by = col_y + 184
        pygame.draw.rect(screen, (20, 24, 32), (bx, by, bar_w, bar_h), border_radius=3)
        fill_pct = min(1.0, max(0.0, v_gold_val / float(target_cost)))
        if fill_pct > 0:
            pygame.draw.rect(screen, COLOR_GOLD if fill_pct >= 1.0 else (80, 150, 240), (bx, by, int(bar_w * fill_pct), bar_h), border_radius=3)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, (bx, by, bar_w, bar_h), 1, border_radius=3)
        p_text = f"{fmt_gold(v_gold_val)} / {target_cost}g ({int(fill_pct * 100)}%)"
        p_lbl = font_xs.render(p_text, True, COLOR_TEXT_WHITE)
        screen.blit(p_lbl, (bx + (bar_w - p_lbl.get_width()) // 2, by + 1))

        if v_gold_val >= target_cost:
            status_str = f"Treasury ready to autonomously erect {target_name}!"
        else:
            rem = target_cost - v_gold_val
            status_str = f"Needs {fmt_gold(rem)}g more to autonomously erect {target_name}"
        screen.blit(font_xs.render(status_str, True, COLOR_GOLD if v_gold_val >= target_cost else (180, 190, 205)), (lx, col_y + 208))

        # RIGHT COLUMN: MILITARY & DOMAIN (Clean enclosed alignment within box)
        right_rect = pygame.Rect(pop_x + 400, col_y, col_w, 245)
        pygame.draw.rect(screen, (30, 36, 48), right_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, right_rect, 1, border_radius=6)

        rx = pop_x + 415
        screen.blit(font_md.render("⚔ Military Duty & Fiefdoms", True, COLOR_GOLD), (rx, col_y + 10))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (rx, col_y + 32), (pop_x + 400 + col_w - 15, col_y + 32), 1)

        if is_landed:
            screen.blit(font_sm.render(f"Fyrd Levies ({levy_rate}%): +{levies_contrib} Soldiers", True, COLOR_TEXT_GREEN), (rx, col_y + 40))

            # Interactive Levy Controls in Dossier (Player only)
            if not is_enemy:
                d_l_dec = pygame.Rect(pop_x + 400 + col_w - 110, col_y + 38, 18, 18)
                d_l_inc = pygame.Rect(pop_x + 400 + col_w - 90, col_y + 38, 18, 18)
                d_l_lock = pygame.Rect(pop_x + 400 + col_w - 70, col_y + 38, 60, 18)

                h_l_dec = d_l_dec.collidepoint(mouse_pos)
                h_l_inc = d_l_inc.collidepoint(mouse_pos)
                h_l_lock = d_l_lock.collidepoint(mouse_pos)

                is_l_locked = v_obj.get("levy_locked", False)
                pygame.draw.rect(screen, (70, 80, 100) if h_l_dec else (42, 48, 62), d_l_dec, border_radius=3)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, d_l_dec, 1, border_radius=3)
                screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE), (d_l_dec.x + 6, col_y + 38))

                pygame.draw.rect(screen, (70, 80, 100) if h_l_inc else (42, 48, 62), d_l_inc, border_radius=3)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, d_l_inc, 1, border_radius=3)
                screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE), (d_l_inc.x + 5, col_y + 38))

                l_l_bg = (65, 50, 20) if is_l_locked else ((45, 52, 68) if h_l_lock else (28, 34, 46))
                l_l_bd = COLOR_GOLD if is_l_locked else ((120, 160, 210) if h_l_lock else (70, 80, 95))
                pygame.draw.rect(screen, l_l_bg, d_l_lock, border_radius=3)
                pygame.draw.rect(screen, l_l_bd, d_l_lock, 1, border_radius=3)
                l_l_txt = "◈ LOCKED" if is_l_locked else "◇ UNLOCK"
                l_l_col = COLOR_GOLD if is_l_locked else COLOR_TEXT_MUTED
                l_l_lbl = font_xs.render(l_l_txt, True, l_l_col)
                screen.blit(l_l_lbl, (d_l_lock.x + (d_l_lock.w - l_l_lbl.get_width()) // 2, col_y + 39))

                if modal_mouse_clicked:
                    if h_l_lock:
                        v_obj["levy_locked"] = not is_l_locked
                        state.logs.append(f"Feudal Law: {v_obj['name']}'s levy rate is now {'LOCKED' if v_obj['levy_locked'] else 'UNLOCKED'}.")
                    elif h_l_dec:
                        v_obj["levy_rate"] = max(0, levy_rate - 5)
                        st_new = get_vassal_landed_status(state, v_obj, v_pid)
                        v_obj["levy_contribution"] = st_new["levy_contribution"]
                        sync_province_holdings_stats(state, v_pid)
                        state.logs.append(f"Decreased {v_obj['name']}'s levy obligation to {v_obj['levy_rate']}%.")
                    elif h_l_inc:
                        v_obj["levy_rate"] = min(90, levy_rate + 5)
                        st_new = get_vassal_landed_status(state, v_obj, v_pid)
                        v_obj["levy_contribution"] = st_new["levy_contribution"]
                        sync_province_holdings_stats(state, v_pid)
                        state.logs.append(f"Increased {v_obj['name']}'s levy obligation to {v_obj['levy_rate']}%.")

            screen.blit(font_xs.render(f"• Household Guards (Kept): {household_guard} Men", True, COLOR_TEXT_WHITE), (rx, col_y + 66))
            screen.blit(font_xs.render(f"• Total Domain Force: {total_garrison} Men", True, (170, 200, 230)), (rx, col_y + 84))
            service_text = f"• Feudal Service: Pledged to {liege_char['name'].split()[1]}'s banner" if is_enemy else "• Feudal Service: Ready to march on King's call"
            screen.blit(font_xs.render(service_text, True, COLOR_TEXT_MUTED), (rx, col_y + 102))
            screen.blit(font_xs.render(f"• Fiefdoms Controlled: {len(held_fiefs)} Fief(s) ({total_held_tiles} Tiles)", True, (150, 215, 255)), (rx, col_y + 120))
        else:
            screen.blit(font_sm.render(f"Fyrd Levies ({levy_rate}%): 0 Soldiers", True, COLOR_TEXT_MUTED), (rx, col_y + 40))
            screen.blit(font_xs.render("• Household Guards: None (Unlanded)", True, COLOR_TEXT_MUTED), (rx, col_y + 66))
            screen.blit(font_xs.render("• Total Domain Force: 0 Men", True, COLOR_TEXT_MUTED), (rx, col_y + 84))
            screen.blit(font_xs.render("• Feudal Service: Awaiting royal fief or title", True, COLOR_TEXT_MUTED), (rx, col_y + 102))
            screen.blit(font_xs.render("• Fiefdoms Controlled: 0 Fiefs (0 Tiles)", True, COLOR_TEXT_MUTED), (rx, col_y + 120))

        # List held fiefs
        fy_item = col_y + 140
        if not held_fiefs:
            screen.blit(font_xs.render("• No fiefdoms granted yet (Unlanded)", True, COLOR_TEXT_MUTED), (rx, fy_item))
        else:
            for h_f in held_fiefs[:4]:
                f_prov = PROVINCES.get(h_f.get("province", ""), {}).get("name", "").split()[0]
                f_sub = f"  - {h_f['name']} ({len(h_f.get('tiles', []))}t in {f_prov})"
                screen.blit(font_xs.render(f_sub, True, COLOR_GOLD), (rx, fy_item))
                fy_item += 19

        # Action Buttons at Bottom
        if not is_enemy:
            btn_h = 36
            loc_btn = pygame.Rect(pop_x + 30, pop_y + pop_h - 56, 170, btn_h)
            gift50_btn = pygame.Rect(pop_x + 215, pop_y + pop_h - 56, 155, btn_h)
            gift100_btn = pygame.Rect(pop_x + 385, pop_y + pop_h - 56, 155, btn_h)
            close_btn = pygame.Rect(pop_x + 555, pop_y + pop_h - 56, 195, btn_h)

            loc_hov = loc_btn.collidepoint(mouse_pos)
            g50_hov = gift50_btn.collidepoint(mouse_pos)
            g100_hov = gift100_btn.collidepoint(mouse_pos)
            c_hov = close_btn.collidepoint(mouse_pos)

            can_g50 = (state.player["gold"] >= 50)
            can_g100 = (state.player["gold"] >= 100)

            # Button 1: Locate
            pygame.draw.rect(screen, (40, 85, 130) if loc_hov else (28, 60, 95), loc_btn, border_radius=6)
            pygame.draw.rect(screen, (100, 180, 255), loc_btn, 1, border_radius=6)
            loc_lbl = font_xs.render("▶ LOCATE SEAT", True, COLOR_TEXT_WHITE)
            screen.blit(loc_lbl, (loc_btn.x + (loc_btn.w - loc_lbl.get_width()) // 2, loc_btn.y + 10))

            # Button 2: Gift 50g
            pygame.draw.rect(screen, (35, 75, 45) if (g50_hov and can_g50) else ((25, 55, 35) if can_g50 else (40, 42, 48)), gift50_btn, border_radius=6)
            pygame.draw.rect(screen, COLOR_TEXT_GREEN if can_g50 else (80, 85, 95), gift50_btn, 1, border_radius=6)
            g50_lbl = font_xs.render("🎁 GIFT 50g", True, COLOR_TEXT_WHITE if can_g50 else COLOR_TEXT_MUTED)
            screen.blit(g50_lbl, (gift50_btn.x + (gift50_btn.w - g50_lbl.get_width()) // 2, gift50_btn.y + 10))

            # Button 3: Gift 100g
            pygame.draw.rect(screen, (75, 65, 25) if (g100_hov and can_g100) else ((55, 45, 20) if can_g100 else (40, 42, 48)), gift100_btn, border_radius=6)
            pygame.draw.rect(screen, COLOR_GOLD if can_g100 else (80, 85, 95), gift100_btn, 1, border_radius=6)
            g100_lbl = font_xs.render("👑 GIFT 100g", True, COLOR_GOLD if can_g100 else COLOR_TEXT_MUTED)
            screen.blit(g100_lbl, (gift100_btn.x + (gift100_btn.w - g100_lbl.get_width()) // 2, gift100_btn.y + 10))

            # Button 4: Close
            pygame.draw.rect(screen, (75, 35, 35) if c_hov else (55, 25, 25), close_btn, border_radius=6)
            pygame.draw.rect(screen, (220, 80, 80), close_btn, 1, border_radius=6)
            cls_lbl = font_xs.render("CLOSE DOSSIER (ESC)", True, (255, 220, 220))
            screen.blit(cls_lbl, (close_btn.x + (close_btn.w - cls_lbl.get_width()) // 2, close_btn.y + 10))

            if modal_mouse_clicked:
                if loc_hov:
                    state.selected_province = v_pid
                    if v_obj.get("tiles"):
                        tc, tr = v_obj["tiles"][0]
                        state.selected_settlement = (tc, tr)
                        state.cam_pan_x = VIEWPORT_CENTER_X - (tc * curr_tile_w + curr_tile_w // 2)
                        state.cam_pan_y = VIEWPORT_CENTER_Y - (tr * curr_tile_h + curr_tile_h // 2)
                    state.inspecting_vassal = None
                    state.logs.append(f"Centering camera on {v_obj['name']}'s seat in {p_full}.")
                elif g50_hov:
                    if can_g50:
                        state.player["gold"] = round(state.player["gold"] - 50, 1)
                        v_obj["gold"] = round(v_obj.get("gold", 0) + 50, 1)
                        state.logs.append(f"👑 Sent 50g royal subsidy to {v_obj['name']}. Vassal treasury: {fmt_gold(v_obj['gold'])}g.")
                    else:
                        state.logs.append(f"⚠️ Need 50 gold to send subsidy to {v_obj['name']}!")
                elif g100_hov:
                    if can_g100:
                        state.player["gold"] = round(state.player["gold"] - 100, 1)
                        v_obj["gold"] = round(v_obj.get("gold", 0) + 100, 1)
                        state.logs.append(f"👑 Sent 100g royal subsidy to {v_obj['name']}. Vassal treasury: {fmt_gold(v_obj['gold'])}g.")
                    else:
                        state.logs.append(f"⚠️ Need 100 gold to send subsidy to {v_obj['name']}!")
                elif c_hov:
                    state.inspecting_vassal = None
        else:
            btn_w, btn_h = 340, 38
            loc_btn = pygame.Rect(pop_x + 40, pop_y + pop_h - 60, btn_w, btn_h)
            loc_hov = loc_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (40, 85, 130) if loc_hov else (28, 60, 95), loc_btn, border_radius=6)
            pygame.draw.rect(screen, (100, 180, 255), loc_btn, 1, border_radius=6)
            screen.blit(font_sm.render("▶ LOCATE SEAT ON MAP", True, COLOR_TEXT_WHITE), (loc_btn.x + (loc_btn.w - font_sm.size("▶ LOCATE SEAT ON MAP")[0]) // 2, loc_btn.y + 10))

            close_btn = pygame.Rect(pop_x + pop_w - 40 - btn_w, pop_y + pop_h - 60, btn_w, btn_h)
            c_hov = close_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (75, 35, 35) if c_hov else (55, 25, 25), close_btn, border_radius=6)
            pygame.draw.rect(screen, (220, 80, 80), close_btn, 1, border_radius=6)
            screen.blit(font_sm.render("CLOSE DOSSIER (ESC)", True, (255, 220, 220)), (close_btn.x + (close_btn.w - font_sm.size("CLOSE DOSSIER (ESC)")[0]) // 2, close_btn.y + 10))

            if modal_mouse_clicked:
                if loc_hov:
                    state.selected_province = v_pid
                    if v_obj.get("tiles"):
                        tc, tr = v_obj["tiles"][0]
                        state.selected_settlement = (tc, tr)
                        state.cam_pan_x = VIEWPORT_CENTER_X - (tc * curr_tile_w + curr_tile_w // 2)
                        state.cam_pan_y = VIEWPORT_CENTER_Y - (tr * curr_tile_h + curr_tile_h // 2)
                    state.inspecting_vassal = None
                    state.logs.append(f"Centering camera on {v_obj['name']}'s seat in {p_full}.")
                elif c_hov:
                    state.inspecting_vassal = None
    
    # ---------------------------------------------------------
    # 8. SOVEREIGN RULER DOSSIER MODAL (Player & Enemy High Rulers)
    # ---------------------------------------------------------
    if state.inspecting_ruler:
        r_id = state.inspecting_ruler
        r_char = CHARACTERS.get(r_id, state.player)
        is_ruler_enemy = (r_id != state.player_id)
    
        # Dimmed backdrop
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 185))
        screen.blit(dim_surf, (0, 0))
    
        pop_w, pop_h = 780, 520
        pop_x = (WINDOW_WIDTH - pop_w) // 2
        pop_y = (WINDOW_HEIGHT - pop_h) // 2
        pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)
    
        pygame.draw.rect(screen, COLOR_PANEL_BG, pop_rect, border_radius=10)
        pygame.draw.rect(screen, (220, 70, 70) if is_ruler_enemy else COLOR_GOLD, pop_rect, 2, border_radius=10)
    
        # Close 'X' Button at top right
        x_btn = pygame.Rect(pop_x + pop_w - 38, pop_y + 12, 26, 26)
        x_hov = x_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (85, 30, 30) if x_hov else (48, 22, 22), x_btn, border_radius=4)
        pygame.draw.rect(screen, (225, 80, 80), x_btn, 1, border_radius=4)
        x_lbl = font_sm.render("✕", True, COLOR_TEXT_WHITE)
        screen.blit(x_lbl, (x_btn.x + 7, x_btn.y + 3))
        if modal_mouse_clicked and x_hov:
            state.inspecting_ruler = None
    
        # Header Title
        title_text = "SOVEREIGN WARLORD DOSSIER" if is_ruler_enemy else "ROYAL SOVEREIGN DOSSIER"
        screen.blit(font_lg.render(title_text, True, (255, 110, 110) if is_ruler_enemy else COLOR_GOLD), (pop_x + 25, pop_y + 16))
        screen.blit(font_xs.render(f"Supreme Liege Lord of {r_char['realm']} • AD 867 Campaign", True, COLOR_TEXT_MUTED), (pop_x + 25, pop_y + 44))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 25, pop_y + 64), (pop_x + pop_w - 25, pop_y + 64), 1)
    
        # Top Character Banner Section
        r_portrait = portrait_cache.get(r_id)
        if r_portrait:
            screen.blit(pygame.transform.smoothscale(r_portrait, (50, 56)), (pop_x + 30, pop_y + 72))
            pygame.draw.rect(screen, (220, 70, 70) if is_ruler_enemy else COLOR_GOLD, (pop_x + 30, pop_y + 72, 50, 56), 2, border_radius=4)
        r_coa = coa_cache.get(r_id)
        if r_coa:
            screen.blit(pygame.transform.smoothscale(r_coa, (38, 44)), (pop_x + 86, pop_y + 84))
    
        # Name and Titles
        screen.blit(font_md.render(f"♚ {r_char['name']}", True, (255, 120, 120) if is_ruler_enemy else COLOR_GOLD), (pop_x + 135, pop_y + 72))
        rank_str = f"Realm Title: {r_char['title']} • {r_char.get('dynasty', '')}"
        screen.blit(font_xs.render(rank_str, True, COLOR_TEXT_WHITE), (pop_x + 135, pop_y + 96))
        
        # Traits string
        traits_str = "Traits: " + ", ".join(r_char.get("traits", ["Warlord", "Fierce"]))
        screen.blit(font_xs.render(traits_str, True, (160, 215, 255)), (pop_x + 135, pop_y + 114))
    
        # Feudal Attributes Grid (Martial, Stewardship, Diplomacy, Intrigue)
        stats = r_char.get("stats", {})
        stats_list = [
            ("⚔ Martial", str(stats.get("martial", 16)), "(Grand Marshal)"),
            ("◆ Stewardship", str(stats.get("stewardship", 14)), "(Lord Treasurer)"),
            ("◆ Diplomacy", str(stats.get("diplomacy", 12)), "(Royal Envoy)"),
            ("⚔ Intrigue", str(stats.get("intrigue", 13)), "(Spymaster)")
        ]
        for s_i, (s_name, s_val, s_sub) in enumerate(stats_list):
            bx = pop_x + 25 + s_i * 158
            by = pop_y + 138
            b_rect = pygame.Rect(bx, by, 150, 44)
            pygame.draw.rect(screen, (34, 40, 54), b_rect, border_radius=4)
            pygame.draw.rect(screen, (160, 70, 70) if is_ruler_enemy else COLOR_PANEL_BORDER, b_rect, 1, border_radius=4)
            screen.blit(font_xs.render(s_name, True, COLOR_TEXT_MUTED), (bx + 8, by + 4))
            screen.blit(font_md.render(s_val, True, (255, 120, 120) if is_ruler_enemy else COLOR_GOLD), (bx + 8, by + 18))
            screen.blit(font_xs.render(s_sub, True, (120, 160, 200)), (bx + 48, by + 22))
    
        # Two Main Columns: Economy & Treasury (Left), Military & Fiefs (Right)
        col_w = 355
        col_y = pop_y + 194
    
        # Calculate ruler's realm stats
        r_provs = [p for p in PROVINCES.values() if p["owner"] == r_id]
        r_prov_names = [p["name"].split()[0] for p in r_provs]
        total_prov_tax = sum(p.get("tax", 0) for p in r_provs)
        total_garrison = sum(p.get("levies_current", 0) for p in r_provs)
        total_field = sum(a.troops for a in state.armies if a.owner == r_id)
        total_armies_count = sum(1 for a in state.armies if a.owner == r_id)
    
        r_vassals = []
        for pid, prov in PROVINCES.items():
            if prov["owner"] == r_id:
                r_vassals.extend(state.vassals.get(pid, []))
    
        total_vassal_tax = sum(get_vassal_landed_status(state, v, v.get("province"))["tax_paid"] for v in r_vassals)
        crown_holdings_count = sum(1 for s in state.settlements.values() if s.get("is_crown_demesne") and PROVINCES.get(s.get("province"), {}).get("owner") == r_id)
    
        # LEFT COLUMN: ROYAL TREASURY & REALM ECONOMY
        left_rect = pygame.Rect(pop_x + 25, col_y, col_w, 235)
        pygame.draw.rect(screen, (30, 36, 48), left_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, left_rect, 1, border_radius=6)
    
        screen.blit(font_md.render("◆ Royal Treasury & Economy", True, COLOR_GOLD), (pop_x + 35, col_y + 10))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 35, col_y + 32), (pop_x + 35 + col_w - 20, col_y + 32), 1)
    
        screen.blit(font_sm.render(f"Treasury: {r_char.get('gold', 0):,} Gold", True, COLOR_GOLD), (pop_x + 40, col_y + 40))
        screen.blit(font_xs.render(f"• Prestige: {r_char.get('prestige', 0)}  •  Piety/Devotion: {r_char.get('piety', 0)}", True, (150, 200, 255)), (pop_x + 40, col_y + 66))
        screen.blit(font_xs.render(f"• Provincial Tax Income: +{total_prov_tax}g / month", True, (160, 220, 180)), (pop_x + 40, col_y + 86))
        screen.blit(font_xs.render(f"  (Direct tolls & tariffs from {len(r_provs)} provinces)", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 100))
        screen.blit(font_xs.render(f"• Feudal Vassal Tithes: +{total_vassal_tax}g / month", True, COLOR_TEXT_GREEN), (pop_x + 40, col_y + 116))
        screen.blit(font_xs.render(f"  (Taxes levied from {len(r_vassals)} lords via Tax Laws)", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 130))
        screen.blit(font_xs.render(f"• Crown Demesne Holdings: {crown_holdings_count} Direct Seats", True, COLOR_TEXT_WHITE), (pop_x + 40, col_y + 148))
        screen.blit(font_xs.render(f"• Total Controlled Lands: {len(r_provs)} of 12 Provinces", True, COLOR_GOLD), (pop_x + 40, col_y + 166))
        
        p_list_str = ", ".join(r_prov_names[:6]) + ("..." if len(r_prov_names) > 6 else "")
        screen.blit(font_xs.render(f"  ({p_list_str})", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 182))
    
        stance_str = "⚔ AT WAR (Invading Britain)" if is_ruler_enemy else "⚔ AT WAR (Defending England)"
        stance_col = (255, 100, 100) if is_ruler_enemy else COLOR_GOLD
        screen.blit(font_xs.render(f"• Feudal Stance: {stance_str}", True, stance_col), (pop_x + 40, col_y + 204))
    
        # RIGHT COLUMN: MILITARY MIGHT & VASSAL LORDS
        right_rect = pygame.Rect(pop_x + 350, col_y, col_w, 235)
        pygame.draw.rect(screen, (30, 36, 48), right_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, right_rect, 1, border_radius=6)
    
        screen.blit(font_md.render("⚔ Military Might & Feudal Roster", True, COLOR_GOLD), (pop_x + 415, col_y + 10))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 415, col_y + 32), (pop_x + 415 + col_w - 30, col_y + 32), 1)
    
        screen.blit(font_sm.render(f"Available Levies: {total_garrison:,} Men", True, COLOR_TEXT_GREEN), (pop_x + 415, col_y + 40))
        screen.blit(font_xs.render(f"• Active Armies in Field: {total_armies_count} Hosts ({total_field:,} Men)", True, (255, 200, 120)), (pop_x + 365, col_y + 66))
        screen.blit(font_xs.render(f"• Sworn Feudal Lords: {len(r_vassals)} Vassals", True, COLOR_TEXT_WHITE), (pop_x + 415, col_y + 88))
        r_cap_pid = state.get_realm_capital(r_id)
        r_cap_name = PROVINCES.get(r_cap_pid, {}).get("name", "Capital")
        screen.blit(font_xs.render(f"• Capital Province: {r_cap_name}", True, (150, 215, 255)), (pop_x + 365, col_y + 110))
        
        # Vassals preview list
        screen.blit(font_xs.render("• Key Vassal Lords:", True, COLOR_TEXT_MUTED), (pop_x + 365, col_y + 132))
        v_preview_y = col_y + 152
        for v_sample in r_vassals[:3]:
            screen.blit(font_xs.render(f"  - {v_sample['name'][:28]}", True, COLOR_GOLD if not is_ruler_enemy else (255, 180, 180)), (pop_x + 365, v_preview_y))
            v_preview_y += 18
        if len(r_vassals) > 3:
            screen.blit(font_xs.render(f"  ... and {len(r_vassals) - 3} other feudal lords", True, COLOR_TEXT_MUTED), (pop_x + 365, v_preview_y))
    
        # Action Buttons at Bottom
        btn_w, btn_h = 280, 38
        
        # Button 1: Locate Capital on Map
        loc_btn = pygame.Rect(pop_x + 40, pop_y + pop_h - 55, btn_w, btn_h)
        loc_hov = loc_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (40, 85, 130) if loc_hov else (28, 60, 95), loc_btn, border_radius=6)
        pygame.draw.rect(screen, (100, 180, 255), loc_btn, 1, border_radius=6)
        cap_name = r_cap_name.upper()
        screen.blit(font_sm.render(f"▶ LOCATE CAPITAL ({cap_name})", True, COLOR_TEXT_WHITE), (pop_x + 75, pop_y + pop_h - 45))
        if modal_mouse_clicked and loc_hov:
            state.selected_province = r_cap_pid
            cap_coord = PROV_CAPITAL_TILES.get(r_cap_pid, (12, 10))
            curr_tw = max(18, int(BASE_TILE_W * state.zoom))
            curr_th = max(16, int(BASE_TILE_H * state.zoom))
            state.cam_pan_x = VIEWPORT_CENTER_X - (cap_coord[0] * curr_tw + curr_tw // 2)
            state.cam_pan_y = VIEWPORT_CENTER_Y - (cap_coord[1] * curr_th + curr_th // 2)
            state.inspecting_ruler = None
            state.logs.append(f"Focusing camera on {r_char['name']}'s seat in {r_cap_name}.")
    
        # Button 2: Close Dossier (ESC)
        close_btn = pygame.Rect(pop_x + pop_w - 40 - btn_w, pop_y + pop_h - 55, btn_w, btn_h)
        c_hov = close_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (90, 40, 40) if c_hov else (60, 28, 28), close_btn, border_radius=6)
        pygame.draw.rect(screen, COLOR_TEXT_RED, close_btn, 1, border_radius=6)
        screen.blit(font_sm.render("CLOSE DOSSIER (ESC)", True, (255, 220, 220)), (close_btn.x + 70, pop_y + pop_h - 45))
        if modal_mouse_clicked and c_hov:
            state.inspecting_ruler = None
    
    # ---------------------------------------------------------
    # 8. VASSAL FIEF CONSTRUCTION CONFIRMATION MODAL
    # ---------------------------------------------------------
    if state.vassal_build_confirm:
        conf = state.vassal_build_confirm
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 180))
        screen.blit(dim_surf, (0, 0))
    
        pop_w, pop_h = 580, 275
        pop_x = (WINDOW_WIDTH - pop_w) // 2
        pop_y = (WINDOW_HEIGHT - pop_h) // 2
        pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)
    
        pygame.draw.rect(screen, COLOR_PANEL_BG, pop_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 205, 50), pop_rect, 2, border_radius=10)
    
        # Close 'X' Button at top right
        x_btn = pygame.Rect(pop_x + pop_w - 36, pop_y + 12, 24, 24)
        x_hov = x_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (85, 30, 30) if x_hov else (48, 22, 22), x_btn, border_radius=4)
        pygame.draw.rect(screen, (225, 80, 80), x_btn, 1, border_radius=4)
        screen.blit(font_xs.render("✕", True, COLOR_TEXT_WHITE), (x_btn.x + 6, x_btn.y + 4))
        if modal_mouse_clicked and x_hov:
            state.vassal_build_confirm = None
    
        # Header
        p_full = PROVINCES.get(conf["province_id"], {}).get("name", "Realm")
        screen.blit(font_lg.render("⚠ BUILDING ON VASSAL FIEFDOM", True, (255, 215, 60)), (pop_x + 25, pop_y + 16))
        screen.blit(font_xs.render(f"Feudal Investiture Notice • {p_full}", True, COLOR_TEXT_MUTED), (pop_x + 25, pop_y + 44))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 25, pop_y + 64), (pop_x + pop_w - 25, pop_y + 64), 1)
    
        # Body Warning & Description
        v_name = conf["vassal_name"]
        f_name = conf["fief_name"]
        b_cost = conf.get("cost", 1000)
        b_type = conf.get("build_type", "city")
        b_spec = BUILDING_SPECS.get(b_type, BUILDING_SPECS["city"])
    
        t1 = font_sm.render(f"My Liege, you are establishing a {b_spec['name']} inside {f_name}.", True, COLOR_TEXT_WHITE)
        t2 = font_sm.render(f"This land is legally held by your feudal subject, {v_name}.", True, (255, 235, 140))
        t3 = font_xs.render(f"• Under Feudal Law, all holdings founded on vassal fiefs belong to the Vassal.", True, (160, 210, 255))
        t4 = font_xs.render(f"• Lordship and revenue of this {b_spec['name']} will be granted to {v_name}.", True, COLOR_TEXT_GREEN)
        b_desc = b_spec.get("desc") or b_spec.get("title", "Holding")
        t5 = font_xs.render(f"• Royal Treasury: -{b_cost:,} Gold  |  Constructs {b_spec['name']} ({b_desc}).", True, COLOR_GOLD)
    
        screen.blit(t1, (pop_x + 25, pop_y + 76))
        screen.blit(t2, (pop_x + 25, pop_y + 98))
        screen.blit(t3, (pop_x + 25, pop_y + 128))
        screen.blit(t4, (pop_x + 25, pop_y + 148))
        screen.blit(t5, (pop_x + 25, pop_y + 168))
    
        # Buttons
        btn_w, btn_h = 240, 38
        # Confirm Button
        c_btn = pygame.Rect(pop_x + 35, pop_y + 215, btn_w, btn_h)
        c_hov = c_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (35, 115, 60) if c_hov else (25, 85, 42), c_btn, border_radius=6)
        pygame.draw.rect(screen, COLOR_TEXT_GREEN, c_btn, 1, border_radius=6)
        screen.blit(font_sm.render("CONFIRM & BESTOW (YES)", True, COLOR_TEXT_WHITE), (pop_x + 55, pop_y + 225))
    
        # Cancel Button
        can_btn = pygame.Rect(pop_x + pop_w - 35 - btn_w, pop_y + 215, btn_w, btn_h)
        can_hov = can_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (110, 35, 35) if can_hov else (80, 25, 25), can_btn, border_radius=6)
        pygame.draw.rect(screen, COLOR_TEXT_RED, can_btn, 1, border_radius=6)
        screen.blit(font_sm.render("CANCEL (DO NOT BUILD)", True, COLOR_TEXT_WHITE), (pop_x + pop_w - 35 - btn_w + 42, pop_y + 225))
    
        if modal_mouse_clicked and c_hov:
            state.player["gold"] -= b_cost
            v_obj = None
            for v in state.vassals.get(conf["province_id"], []):
                if v.get("id") == conf.get("vassal_id") or v.get("name") == conf.get("vassal_name"):
                    v_obj = v
                    break
    
            v_short = v_name.split()[1] if len(v_name.split()) > 1 else v_name
            if b_type == "city":
                city_name = f"{v_short}'s {random.choice(['Borough', 'Burgh', 'Town', 'Market'])}"
            elif b_type == "fort":
                city_name = f"{v_short}'s {random.choice(['Keep', 'Castle', 'Fortress'])}"
            else:
                city_name = f"{v_short}'s Barracks"
    
            state.settlement_id_counter += 1
            s_id = f"settlement_{state.settlement_id_counter}"
    
            for tc, tr in conf["target_tiles"]:
                state.settlements[(tc, tr)] = {
                    "id": s_id,
                    "province": conf["province_id"],
                    "type": b_type,
                    "name": city_name,
                    "lord": v_name,
                    "vassal_id": conf.get("vassal_id"),
                    "is_crown_demesne": False,
                    "is_crown_fief": False,
                    "level": 0
                }
                if v_obj:
                    if "tiles" not in v_obj:
                        v_obj["tiles"] = []
                    if (tc, tr) not in v_obj["tiles"]:
                        v_obj["tiles"].append((tc, tr))
    
            if v_obj:
                if not v_obj.get("city_name"):
                    v_obj["city_name"] = city_name
                v_obj["gold"] = v_obj.get("gold", 150) + 100
    
            sync_province_holdings_stats(state, conf["province_id"])
            if v_obj:
                st = get_vassal_landed_status(state, v_obj, conf["province_id"])
                v_obj["tax_contribution"] = st["tax_paid"]
                v_obj["levy_contribution"] = st["levy_contribution"]
    
            state.logs.append(f"Invested {b_cost:,}g in {f_name}! Constructed {city_name} owned by {v_name}.")
            state.vassal_build_confirm = None
    
        elif modal_mouse_clicked and can_hov:
            state.logs.append("Cancelled construction on vassal territory.")
            state.vassal_build_confirm = None

    # ---------------------------------------------------------
    # 6. FEUDAL SUBJUGATION / VASSALAGE EVENT MODAL
    # ---------------------------------------------------------
    if getattr(state, "subjugation_event", None):
        ev = state.subjugation_event
        # Dark backdrop
        dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 195))
        screen.blit(dim_surf, (0, 0))

        pop_w, pop_h = 740, 460
        pop_x = (WINDOW_WIDTH - pop_w) // 2
        pop_y = (WINDOW_HEIGHT - pop_h) // 2
        pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)

        is_subjugated = (ev.get("type") == "player_vassalized")
        border_col = (235, 140, 45) if is_subjugated else COLOR_GOLD

        pygame.draw.rect(screen, (22, 26, 36), pop_rect, border_radius=10)
        pygame.draw.rect(screen, border_col, pop_rect, 2, border_radius=10)

        # Header Title
        t_col = (255, 190, 80) if is_subjugated else COLOR_GOLD
        t_surf = font_lg.render(ev["title"], True, t_col)
        screen.blit(t_surf, (pop_x + (pop_w - t_surf.get_width()) // 2, pop_y + 24))
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 30, pop_y + 64), (pop_x + pop_w - 30, pop_y + 64), 1)

        # Liege & Vassal Portraits / Heraldic Crests
        liege_cid = state.player_liege or state.enemy_liege or state.player_id
        vassal_cid = state.player_id if state.player_liege else state.enemy_id
        left_char = portrait_cache.get(liege_cid)
        right_char = portrait_cache.get(vassal_cid)
        left_coa = coa_cache.get(liege_cid)
        right_coa = coa_cache.get(vassal_cid)

        if left_char:
            s_left = pygame.transform.smoothscale(left_char, (58, 58))
            screen.blit(s_left, (pop_x + 40, pop_y + 76))
            pygame.draw.rect(screen, COLOR_GOLD, (pop_x + 40, pop_y + 76, 58, 58), 2)
        if left_coa:
            screen.blit(left_coa, (pop_x + 104, pop_y + 86))

        # Relationship badge in middle
        rel_txt = "⇦ SUZERAIN LIEGE • VASSAL SUBJECT ⇨"
        rel_surf = font_xs.render(rel_txt, True, (255, 220, 120))
        screen.blit(rel_surf, (pop_x + (pop_w - rel_surf.get_width()) // 2, pop_y + 95))

        if right_char:
            s_right = pygame.transform.smoothscale(right_char, (58, 58))
            screen.blit(s_right, (pop_x + pop_w - 98, pop_y + 76))
            pygame.draw.rect(screen, (160, 170, 190), (pop_x + pop_w - 98, pop_y + 76, 58, 58), 2)
        if right_coa:
            screen.blit(right_coa, (pop_x + pop_w - 146, pop_y + 86))

        pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 30, pop_y + 148), (pop_x + pop_w - 30, pop_y + 148), 1)

        # Story description text
        ty = pop_y + 164
        for line in ev["text_lines"]:
            if line:
                screen.blit(font_xs.render(line, True, COLOR_TEXT_WHITE), (pop_x + 40, ty))
            ty += 24

        # Action / Continue Button
        btn_w, btn_h = 360, 44
        btn_x = pop_x + (pop_w - btn_w) // 2
        btn_y = pop_y + pop_h - 66
        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        b_hov = btn_rect.collidepoint(mouse_pos)

        btn_bg = (40, 110, 60) if b_hov else (28, 80, 42)
        btn_bdr = COLOR_TEXT_GREEN
        if is_subjugated:
            btn_bg = (120, 65, 30) if b_hov else (85, 45, 20)
            btn_bdr = (255, 180, 80)

        pygame.draw.rect(screen, btn_bg, btn_rect, border_radius=6)
        pygame.draw.rect(screen, btn_bdr, btn_rect, 1, border_radius=6)
        btn_txt = font_sm.render(ev["button_text"], True, COLOR_TEXT_WHITE)
        screen.blit(btn_txt, (btn_rect.x + (btn_rect.w - btn_txt.get_width()) // 2, btn_rect.y + 12))

        if modal_mouse_clicked and b_hov:
            state.subjugation_event = None
