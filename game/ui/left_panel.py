"""
Left Panel Component (Player Profile, Armies, Demesne, Vassals, Laws, In/Expense)
"""
import pygame
from game.config import (
    WINDOW_HEIGHT, PANEL_L_X, PANEL_L_W, PANEL_Y, PANEL_H, COLOR_PANEL_BG, COLOR_PANEL_BORDER, COLOR_GOLD,
    COLOR_PRESTIGE, COLOR_PIETY, COLOR_TEXT_WHITE, COLOR_TEXT_MUTED,
    COLOR_TEXT_RED, COLOR_TEXT_GREEN, COLOR_BUTTON_NORMAL,
    COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE
)
from game.data.characters import CHARACTERS
from game.data.provinces import PROVINCES, ADJACENCY
from game.data.buildings import BUILDING_SPECS, BARRACK_UPGRADE_COSTS, get_barrack_stats
from game.systems.economy import (
    get_all_settlement_holdings, get_realm_finances,
    get_vassal_landed_status, sync_province_holdings_stats, fmt_gold
)

def get_feudal_badge(rank_or_title):
    """Returns (symbol, color) for feudal nobility ranks (CK2 style)."""
    t = str(rank_or_title).lower()
    if "king" in t or "emperor" in t:
        return "👑", (255, 215, 0)
    elif "duke" in t or "archon" in t or "ironlord" in t:
        return "⚜", (240, 190, 70)
    elif "count" in t or "thane" in t or "warden" in t:
        return "🛡", (180, 210, 255)
    else:
        return "🏰", (220, 180, 140)

def draw_feudal_pill(screen, font_xs, rank_or_title, x, y):
    """Draws a Crusader Kings style rank badge pill and returns (pill_width, fg_color)."""
    t = str(rank_or_title).lower()
    if "king" in t or "emperor" in t:
        txt, fg, bg = "👑 KING", (255, 215, 0), (70, 55, 15)
    elif "duke" in t or "archon" in t or "ironlord" in t:
        txt, fg, bg = "⚜ DUKE", (240, 190, 70), (60, 48, 20)
    elif "count" in t or "thane" in t or "warden" in t:
        txt, fg, bg = "🛡 COUNT", (180, 215, 255), (35, 55, 80)
    else:
        txt, fg, bg = "🏰 BARON", (230, 190, 150), (55, 42, 30)

    txt_surf = font_xs.render(txt, True, fg)
    w = txt_surf.get_width() + 8
    h = 16
    pill = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, bg, pill, border_radius=3)
    pygame.draw.rect(screen, fg, pill, 1, border_radius=3)
    screen.blit(txt_surf, (x + 4, y + 1))
    return w, fg

def render_left_panel(screen, state, mouse_pos, mouse_clicked, fonts, portrait_cache, coa_cache):
    font_xs = fonts["xs"]
    font_sm = fonts["sm"]
    font_md = fonts["md"]
    font_lg = fonts["lg"]

    # 2. LEFT PANEL: PLAYER RULER & ACTIVE FORCES
    # ---------------------------------------------------------
    content_x = PANEL_L_X + 12
    content_w = PANEL_L_W - 24
    left_panel = pygame.Rect(PANEL_L_X, PANEL_Y, PANEL_L_W, PANEL_H)
    pygame.draw.rect(screen, COLOR_PANEL_BG, left_panel, border_radius=6)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, left_panel, 2, border_radius=6)
    
    # Portrait & Wessex Shield (Clickable Ruler Card)
    r_card_p = pygame.Rect(content_x, 70, content_w, 98)
    is_rcp_hov = r_card_p.collidepoint(mouse_pos)
    if is_rcp_hov:
        pygame.draw.rect(screen, (45, 55, 75), r_card_p, border_radius=6)
        pygame.draw.rect(screen, COLOR_GOLD, r_card_p, 1, border_radius=6)
    
    p_img = portrait_cache.get(state.player_id)
    if p_img:
        screen.blit(p_img, (content_x + 6, 75))
        pygame.draw.rect(screen, COLOR_GOLD, (content_x + 6, 75, 64, 64), 1)
    c_img = coa_cache.get(state.player_id)
    if c_img:
        screen.blit(c_img, (content_x + 52, 120))
    
    # Ruler Info
    name_surf = font_md.render(state.player["name"], True, COLOR_GOLD if is_rcp_hov else COLOR_TEXT_WHITE)
    title_surf = font_sm.render(state.player["realm"], True, COLOR_GOLD)
    dynasty_surf = font_sm.render(f"Martial Skill: {state.player['stats']['martial']}", True, COLOR_TEXT_RED)
    age_surf = font_sm.render(f"Age: {state.player['age']} • Gold: {state.player['gold']}", True, COLOR_TEXT_MUTED)
    
    screen.blit(name_surf, (content_x + 85, 75))
    screen.blit(title_surf, (content_x + 85, 96))
    screen.blit(dynasty_surf, (content_x + 85, 116))
    screen.blit(age_surf, (content_x + 85, 134))
    
    if mouse_clicked and is_rcp_hov:
        state.inspecting_ruler = state.player_id
        state.logs.append(f"Inspecting Sovereign Dossier for {state.player['name']}.")
    
    # Realm Mobilization Buttons
    pygame.draw.line(screen, COLOR_PANEL_BORDER, (content_x, 174), (content_x + content_w, 174), 1)

    # Standard Sovereign Mobilization: Raise All & Disband All Buttons
    btn_raise_all = pygame.Rect(content_x, 184, 192, 38)
    is_all_cd = (state.player_raise_cooldown > 0)
    b_hover = btn_raise_all.collidepoint(mouse_pos) and not is_all_cd
    if is_all_cd:
        m_left = (state.player_raise_cooldown + 29) // 30
        pygame.draw.rect(screen, (38, 42, 50), btn_raise_all, border_radius=4)
        pygame.draw.rect(screen, (60, 65, 78), btn_raise_all, 1, border_radius=4)
        cd_lbl = font_xs.render(f"COOLDOWN ({m_left}m)", True, (135, 145, 160))
        screen.blit(cd_lbl, (btn_raise_all.x + (btn_raise_all.w - cd_lbl.get_width()) // 2, 196))
    else:
        pygame.draw.rect(screen, (40, 110, 60) if b_hover else (30, 80, 45), btn_raise_all, border_radius=4)
        pygame.draw.rect(screen, COLOR_TEXT_GREEN, btn_raise_all, 1, border_radius=4)
        ra_lbl = font_sm.render("RAISE ALL (R)", True, COLOR_TEXT_WHITE)
        screen.blit(ra_lbl, (btn_raise_all.x + (btn_raise_all.w - ra_lbl.get_width()) // 2, 194))
        if mouse_clicked and b_hover:
            state.raise_all_levies()
    
    # Disband All Button
    btn_disband_all = pygame.Rect(content_x + 204, 184, 192, 38)
    b_hover_d = btn_disband_all.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (100, 40, 40) if b_hover_d else (75, 30, 30), btn_disband_all, border_radius=4)
    pygame.draw.rect(screen, COLOR_TEXT_RED, btn_disband_all, 1, border_radius=4)
    da_lbl = font_sm.render("DISBAND ALL", True, COLOR_TEXT_WHITE)
    screen.blit(da_lbl, (btn_disband_all.x + (btn_disband_all.w - da_lbl.get_width()) // 2, 194))
    if mouse_clicked and b_hover_d:
        state.disband_all_armies(state.player_id)
    
    # ---------------------------------------------------------
    # Left Panel Sub-Tabs: [ ⚔ Armies ]  [ ♟ Vassals ]  [ ♚ Demesne ]
    #                      [ ⚖ Realm Laws ]     [ ◆ In/Expense ]
    # ---------------------------------------------------------
    pygame.draw.line(screen, COLOR_PANEL_BORDER, (content_x, 232), (content_x + content_w, 232), 1)
    tab_y = 236
    tab_armies = pygame.Rect(content_x, tab_y, 126, 26)
    tab_vassals = pygame.Rect(content_x + 135, tab_y, 126, 26)
    tab_demesne = pygame.Rect(content_x + 270, tab_y, 126, 26)
    tab_laws = pygame.Rect(content_x, tab_y + 30, 126, 26)
    tab_economy = pygame.Rect(content_x + 135, tab_y + 30, 126, 26)
    tab_diplomacy = pygame.Rect(content_x + 270, tab_y + 30, 126, 26)
    
    is_hov_ta = tab_armies.collidepoint(mouse_pos)
    is_hov_tv = tab_vassals.collidepoint(mouse_pos)
    is_hov_td = tab_demesne.collidepoint(mouse_pos)
    is_hov_tl = tab_laws.collidepoint(mouse_pos)
    is_hov_te = tab_economy.collidepoint(mouse_pos)
    is_hov_tdip = tab_diplomacy.collidepoint(mouse_pos)
    
    is_a_active = (state.left_tab == "armies")
    is_v_active = (state.left_tab == "vassals")
    is_d_active = (state.left_tab == "demesne")
    is_l_active = (state.left_tab == "laws")
    is_e_active = (state.left_tab == "economy")
    is_dip_active = (state.left_tab == "diplomacy")
    
    # Row 1 Tabs: Armies, Vassals, Demesne
    pygame.draw.rect(screen, COLOR_BUTTON_ACTIVE if is_a_active else (COLOR_BUTTON_HOVER if is_hov_ta else COLOR_BUTTON_NORMAL), tab_armies, border_radius=4)
    pygame.draw.rect(screen, COLOR_GOLD if is_a_active else COLOR_PANEL_BORDER, tab_armies, 1, border_radius=4)
    lbl_a = font_xs.render("⚔ ARMIES", True, COLOR_TEXT_WHITE if not is_a_active else COLOR_GOLD)
    screen.blit(lbl_a, (tab_armies.x + (tab_armies.w - lbl_a.get_width()) // 2, tab_y + 5))
    
    pygame.draw.rect(screen, COLOR_BUTTON_ACTIVE if is_v_active else (COLOR_BUTTON_HOVER if is_hov_tv else COLOR_BUTTON_NORMAL), tab_vassals, border_radius=4)
    pygame.draw.rect(screen, COLOR_GOLD if is_v_active else COLOR_PANEL_BORDER, tab_vassals, 1, border_radius=4)
    lbl_v = font_xs.render("♟ VASSALS", True, COLOR_TEXT_WHITE if not is_v_active else COLOR_GOLD)
    screen.blit(lbl_v, (tab_vassals.x + (tab_vassals.w - lbl_v.get_width()) // 2, tab_y + 5))
    
    # Crown Demesne Tab Items Calculation
    player_crown_items = []
    covered_holding_tiles = set()
    for f in state.fiefs.values():
        prov_owner = PROVINCES.get(f.get("province"), {}).get("owner")
        is_player_fief = (
            f.get("owner") == state.player_id or
            f.get("holder") == state.player["name"] or
            (prov_owner == state.player_id and f.get("vassal_id") is None and f.get("holder") != state.enemy["name"])
        )
        # Prevent stealing AI fiefs
        if f.get("owner") in getattr(state, "ai_rulers", [state.enemy_id]):
            is_player_fief = False

        if f.get("vassal_id") is None and is_player_fief:
            f["holder"] = state.player["name"]
            f["is_crown_demesne"] = True
            player_crown_items.append({
                "id": f["id"],
                "name": f["name"],
                "province": f["province"],
                "tiles": f["tiles"],
                "is_fief": True
            })
            for t in f.get("tiles", []):
                covered_holding_tiles.add(t)
    
    for h in get_all_settlement_holdings(state):
        sdata = h["data"]
        pid = h["province"]
        prov_owner = PROVINCES.get(pid, {}).get("owner")
        is_player_holding = (
            sdata.get("owner") == state.player_id or
            sdata.get("lord") == f"{state.player['name']} (Crown Demesne)" or
            (prov_owner == state.player_id and sdata.get("vassal_id") is None and sdata.get("lord") != f"{state.enemy['name']} (Crown Demesne)")
        )
        # Prevent stealing AI holdings
        if sdata.get("owner") in getattr(state, "ai_rulers", [state.enemy_id]):
            is_player_holding = False

        if is_player_holding and sdata.get("vassal_id") is None:
            sdata["lord"] = f"{state.player['name']} (Crown Demesne)"
            sdata["is_crown_demesne"] = True
            if not any(t in covered_holding_tiles for t in h["tiles"]):
                p_short = PROVINCES[pid]["name"].split()[0]
                clean_hname = h["name"].replace("Royal Citadel of ", "").replace("Royal Castle of ", "").replace("Royal Borough of ", "")
                player_crown_items.append({
                    "id": f"holding_{h['primary_tile'][0]}_{h['primary_tile'][1]}",
                    "name": f"Crown Holding of {clean_hname}",
                    "province": pid,
                    "tiles": list(h["tiles"]),
                    "is_fief": False
                })
                for t in h["tiles"]:
                    covered_holding_tiles.add(t)
    
    d_title = f"♚ DEMESNE ({len(player_crown_items)})"
    pygame.draw.rect(screen, (60, 48, 20) if is_d_active else (COLOR_BUTTON_HOVER if is_hov_td else (35, 40, 52)), tab_demesne, border_radius=4)
    pygame.draw.rect(screen, COLOR_GOLD if is_d_active else (90, 140, 210), tab_demesne, 1, border_radius=4)
    d_lbl = font_xs.render(d_title, True, COLOR_GOLD if is_d_active else (210, 230, 255))
    screen.blit(d_lbl, (tab_demesne.x + (tab_demesne.w - d_lbl.get_width()) // 2, tab_y + 5))
    
    # Row 2 Tabs: Laws & Income/Expense
    l_title = "⚖ LAWS"
    pygame.draw.rect(screen, (60, 48, 20) if is_l_active else (COLOR_BUTTON_HOVER if is_hov_tl else (35, 40, 52)), tab_laws, border_radius=4)
    pygame.draw.rect(screen, COLOR_GOLD if is_l_active else (90, 140, 210), tab_laws, 1, border_radius=4)
    l_lbl = font_xs.render(l_title, True, COLOR_GOLD if is_l_active else (210, 230, 255))
    screen.blit(l_lbl, (tab_laws.x + (tab_laws.w - l_lbl.get_width()) // 2, tab_y + 34))
    
    e_title = "◆ IN/EXPENSE"
    pygame.draw.rect(screen, (60, 48, 20) if is_e_active else (COLOR_BUTTON_HOVER if is_hov_te else (35, 40, 52)), tab_economy, border_radius=4)
    pygame.draw.rect(screen, COLOR_GOLD if is_e_active else (90, 140, 210), tab_economy, 1, border_radius=4)
    e_lbl = font_xs.render(e_title, True, COLOR_GOLD if is_e_active else (210, 230, 255))
    screen.blit(e_lbl, (tab_economy.x + (tab_economy.w - e_lbl.get_width()) // 2, tab_y + 34))

    dip_title = "📜 DIPLOMACY"
    pygame.draw.rect(screen, (60, 48, 20) if is_dip_active else (COLOR_BUTTON_HOVER if is_hov_tdip else (35, 40, 52)), tab_diplomacy, border_radius=4)
    pygame.draw.rect(screen, COLOR_GOLD if is_dip_active else (90, 140, 210), tab_diplomacy, 1, border_radius=4)
    dip_lbl = font_xs.render(dip_title, True, COLOR_GOLD if is_dip_active else (210, 230, 255))
    screen.blit(dip_lbl, (tab_diplomacy.x + (tab_diplomacy.w - dip_lbl.get_width()) // 2, tab_y + 34))
    
    if mouse_clicked and is_hov_ta:
        state.left_tab = "armies"
    elif mouse_clicked and is_hov_tv:
        state.left_tab = "vassals"
        state.vassal_selected_province = None
        state.vassal_inspecting_liege_id = None
        state.vassal_page = 0
    elif mouse_clicked and is_hov_td:
        if state.left_tab != "demesne":
            state.left_tab = "demesne"
            state.demesne_selected_province = None
            state.demesne_page = 0
        else:
            state.demesne_selected_province = None
            state.demesne_page = 0
    elif mouse_clicked and is_hov_tl:
        state.left_tab = "laws"
    elif mouse_clicked and is_hov_te:
        state.left_tab = "economy"
        state.economy_vassal_page = 0
    elif mouse_clicked and is_hov_tdip:
        state.left_tab = "diplomacy"
    
    if state.left_tab == "armies":
        # Active Saxon Armies Roster
        screen.blit(font_md.render("Active Saxon Armies", True, COLOR_GOLD), (25, 302))
    
        player_armies = [a for a in state.armies if a.owner == state.player_id]
        if not player_armies:
            screen.blit(font_sm.render("No armies raised yet.", True, COLOR_TEXT_MUTED), (25, 330))
            screen.blit(font_sm.render("Click 'RAISE ALL' or select", True, COLOR_TEXT_MUTED), (25, 350))
            screen.blit(font_sm.render("a province to raise local fyrd.", True, COLOR_TEXT_MUTED), (25, 370))
        else:
            ay = 330
            for a in player_armies[:3]:
                a_rect = pygame.Rect(content_x, ay, content_w, 44)
                is_sel = (a.id == state.selected_army_id)
                b_hover_a = a_rect.collidepoint(mouse_pos)
                
                bg_col = COLOR_BUTTON_ACTIVE if is_sel else ((55, 65, 82) if b_hover_a else (38, 44, 58))
                pygame.draw.rect(screen, bg_col, a_rect, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if is_sel else COLOR_PANEL_BORDER, a_rect, 1, border_radius=4)
    
                screen.blit(font_sm.render(f"{a.name} ({a.troops:,} men)", True, COLOR_TEXT_WHITE), (35, ay + 4))
                
                status_str = "Idle"
                if a.in_battle: status_str = "⚔ IN BATTLE!"
                elif a.courier_en_route: status_str = f"✉ Courier En Route ({a.courier_days_left}d)"
                elif a.is_mustering: status_str = f"Mustering ({a.muster_days}d)"
                elif a.is_demobilizing: status_str = f"◆ Returning to {PROVINCES[a.flag_origin]['name'].split()[0]}"
                elif a.is_sieging: status_str = f"Besieging {a.siege_target_name or 'Holding'} ({a.siege_progress}%)"
                elif a.is_moving: status_str = f"Marching to {PROVINCES[a.next_province]['name'].split()[0]}"
                else: status_str = f"Stationed in {PROVINCES[a.province]['name'].split()[0]}"
    
                st_color = COLOR_GOLD if a.in_battle else ((255, 215, 80) if a.courier_en_route else ((255, 180, 50) if a.is_mustering else ((150, 200, 255) if a.is_demobilizing else COLOR_TEXT_MUTED)))
                screen.blit(font_xs.render(status_str, True, st_color), (35, ay + 24))
    
                if mouse_clicked and b_hover_a:
                    state.selected_army_id = a.id
                    state.selected_province = a.province
    
                ay += 48
    
        # Chronicle of Britain
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 505), (285, 505), 1)
        screen.blit(font_md.render("Chronicle of Britain", True, COLOR_GOLD), (25, 515))
    
        log_y = 545
        for log_msg in state.logs[-6:]:
            disp = log_msg[:34] + "..." if len(log_msg) > 37 else log_msg
            lm_surf = font_sm.render(f"• {disp}", True, COLOR_TEXT_MUTED)
            screen.blit(lm_surf, (25, log_y))
            log_y += 24
    
    elif state.left_tab == "demesne":
        # Group player crown holdings and fiefs by province
        crown_by_prov = {}
        for it in player_crown_items:
            pid = it["province"]
            if pid not in crown_by_prov:
                crown_by_prov[pid] = []
            crown_by_prov[pid].append(it)
    
        crown_provinces = sorted(
            list(crown_by_prov.keys()),
            key=lambda p: (0 if p == state.player_capital else 1, PROVINCES.get(p, {}).get("name", p))
        )
    
        # Safety check: if demesne_selected_province no longer exists in crown_by_prov, reset it
        if state.demesne_selected_province and state.demesne_selected_province not in crown_by_prov:
            state.demesne_selected_province = None
    
        # -------------------------------------------------------------
        # LEVEL 1: LIST OF PROVINCES CONTAINING PLAYER'S CROWN FIEFS
        # -------------------------------------------------------------
        if state.demesne_selected_province is None:
            total_provs = len(crown_provinces)
            total_holdings = len(player_crown_items)
            header_lbl = font_md.render(f"Crown Demesne ({total_holdings} Holdings)", True, COLOR_GOLD)
            screen.blit(header_lbl, (25, 302))
    
            per_page = 5
            max_pages = max(1, (total_provs + per_page - 1) // per_page)
            state.demesne_page = max(0, min(state.demesne_page, max_pages - 1))
    
            start_i = state.demesne_page * per_page
            cur_page_provs = crown_provinces[start_i:start_i + per_page]
    
            fy = 328
            for pid in cur_page_provs:
                p_items = crown_by_prov[pid]
                p_info = PROVINCES.get(pid, {})
                p_name = p_info.get("name", pid).split()[0]
                p_tiles_cnt = sum(len(it.get("tiles", [])) for it in p_items)
    
                p_card = pygame.Rect(content_x, fy, content_w, 50)
                is_p_hov = p_card.collidepoint(mouse_pos)
                is_active_prov = (state.selected_province == pid)
    
                bg_c = (60, 50, 24) if is_active_prov else ((50, 60, 78) if is_p_hov else (34, 40, 52))
                border_c = COLOR_GOLD if (is_p_hov or is_active_prov) else (80, 140, 220)
    
                pygame.draw.rect(screen, bg_c, p_card, border_radius=4)
                pygame.draw.rect(screen, border_c, p_card, 1, border_radius=4)
    
                screen.blit(font_sm.render(f"◆ {p_name}", True, COLOR_GOLD), (34, fy + 4))
                screen.blit(font_xs.render(f"Crown Fiefs: {len(p_items)} Holdings • {p_tiles_cnt}t", True, (210, 230, 255)), (34, fy + 26))
    
                arr_lbl = font_xs.render("View ›", True, COLOR_GOLD if is_p_hov else (160, 200, 240))
                screen.blit(arr_lbl, (280 - arr_lbl.get_width() - 8, fy + 16))
    
                if mouse_clicked and is_p_hov:
                    state.demesne_selected_province = pid
                    state.demesne_page = 0
                    state.selected_province = pid
                    state.logs.append(f"Opened Crown Demesne holdings in {p_name}.")
    
                fy += 54
    
            if not crown_provinces:
                screen.blit(font_sm.render("No crown holdings held directly.", True, COLOR_TEXT_MUTED), (25, 350))
                screen.blit(font_xs.render("Revoke fiefs to expand royal land.", True, COLOR_TEXT_MUTED), (25, 370))
    
            # Bottom Pagination Controls for Province List
            py_btn = 645
            btn_prev = pygame.Rect(content_x, py_btn, 110, 28)
            btn_next = pygame.Rect(content_x + content_w - 110, py_btn, 110, 28)
            is_prev_hov = btn_prev.collidepoint(mouse_pos)
            is_next_hov = btn_next.collidepoint(mouse_pos)
    
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
            screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.demesne_page > 0 else COLOR_TEXT_MUTED), (btn_prev.x + (btn_prev.w - font_xs.size("PREV")[0]) // 2, py_btn + 6))
    
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
            screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.demesne_page < max_pages - 1 else COLOR_TEXT_MUTED), (btn_next.x + (btn_next.w - font_xs.size("NEXT")[0]) // 2, py_btn + 6))
    
            page_str = f"Page {state.demesne_page + 1}/{max_pages}"
            p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
            screen.blit(p_lbl, (content_x + (content_w - p_lbl.get_width()) // 2, py_btn + 6))
    
            if mouse_clicked and is_prev_hov and state.demesne_page > 0:
                state.demesne_page -= 1
            elif mouse_clicked and is_next_hov and state.demesne_page < max_pages - 1:
                state.demesne_page += 1
    
        # -------------------------------------------------------------
        # LEVEL 2: LIST OF FIEFS/HOLDINGS INSIDE THE SELECTED PROVINCE
        # -------------------------------------------------------------
        else:
            sel_pid = state.demesne_selected_province
            prov_fiefs = crown_by_prov.get(sel_pid, [])
            p_info = PROVINCES.get(sel_pid, {})
            p_name = p_info.get("name", sel_pid).split()[0]
    
            # Back Button & Province Header
            back_btn = pygame.Rect(25, 298, 105, 24)
            is_back_hov = back_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (45, 65, 90) if is_back_hov else (30, 42, 60), back_btn, border_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD if is_back_hov else (80, 140, 220), back_btn, 1, border_radius=4)
            screen.blit(font_xs.render("◄ ALL PROVS", True, COLOR_GOLD if is_back_hov else COLOR_TEXT_WHITE), (33, 303))
    
            header_lbl = font_sm.render(f"◆ {p_name} ({len(prov_fiefs)})", True, COLOR_GOLD)
            screen.blit(header_lbl, (140, 302))
    
            per_page = 5
            max_pages = max(1, (len(prov_fiefs) + per_page - 1) // per_page)
            state.demesne_page = max(0, min(state.demesne_page, max_pages - 1))
    
            start_i = state.demesne_page * per_page
            cur_page_fiefs = prov_fiefs[start_i:start_i + per_page]
    
            if mouse_clicked and is_back_hov:
                state.demesne_selected_province = None
                state.demesne_page = 0
    
            fy = 328
            for f in cur_page_fiefs:
                f_rect = pygame.Rect(content_x, fy, content_w, 50)
                is_sel = (f["id"] == state.selected_fief_id or (not f["is_fief"] and f.get("tiles") and state.selected_settlement in f["tiles"]))
                b_hover_f = f_rect.collidepoint(mouse_pos)
    
                bg_col = (70, 55, 20) if is_sel else ((50, 60, 78) if b_hover_f else (34, 40, 52))
                pygame.draw.rect(screen, bg_col, f_rect, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if is_sel else (80, 140, 220), f_rect, 1, border_radius=4)
    
                # Determine building type in this fief
                h_type_str = "Crown Fief"
                for t in f.get("tiles", []):
                    if t in state.settlements:
                        stype = state.settlements[t].get("type", "city")
                        if stype in ("city", "town"):
                            h_type_str = "City (100 Gar • +3g)"
                        elif stype == "fort":
                            h_type_str = "Fortress (300 Gar • +1g)"
                        elif stype == "barrack":
                            h_type_str = "Barracks (Recruits)"
                        break
    
                f_disp_name = f['name']
                if len(f_disp_name) > 22:
                    f_disp_name = f_disp_name[:20] + "..."
    
                screen.blit(font_sm.render(f"♚ {f_disp_name}", True, COLOR_GOLD), (34, fy + 4))
                status_str = f"{len(f['tiles'])} Tile{'s' if len(f['tiles']) > 1 else ''} • {h_type_str}"
                screen.blit(font_xs.render(status_str, True, (210, 230, 255)), (34, fy + 26))
    
                if mouse_clicked and b_hover_f:
                    state.selected_province = f["province"]
                    if f["is_fief"]:
                        state.selected_fief_id = f["id"]
                    else:
                        state.selected_fief_id = None
                    if f.get("tiles"):
                        state.selected_settlement = f["tiles"][0]
                    state.selected_army_id = None
                    state.logs.append(f"Inspecting {f['name']} in {p_name}.")
    
                fy += 54
    
            if not prov_fiefs:
                screen.blit(font_sm.render(f"No crown fiefs in {p_name}.", True, COLOR_TEXT_MUTED), (25, 350))
    
            # Bottom Pagination Controls for Fiefs in this Province
            py_btn = 645
            btn_prev = pygame.Rect(content_x, py_btn, 110, 28)
            btn_next = pygame.Rect(content_x + content_w - 110, py_btn, 110, 28)
    
            is_prev_hov = btn_prev.collidepoint(mouse_pos)
            is_next_hov = btn_next.collidepoint(mouse_pos)
    
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
            screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.demesne_page > 0 else COLOR_TEXT_MUTED), (btn_prev.x + (btn_prev.w - font_xs.size("PREV")[0]) // 2, py_btn + 6))
    
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
            screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.demesne_page < max_pages - 1 else COLOR_TEXT_MUTED), (btn_next.x + (btn_next.w - font_xs.size("NEXT")[0]) // 2, py_btn + 6))
    
            page_str = f"Page {state.demesne_page + 1}/{max_pages}"
            p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
            screen.blit(p_lbl, (content_x + (content_w - p_lbl.get_width()) // 2, py_btn + 6))
    
            if mouse_clicked and is_prev_hov and state.demesne_page > 0:
                state.demesne_page -= 1
            elif mouse_clicked and is_next_hov and state.demesne_page < max_pages - 1:
                state.demesne_page += 1
    
    elif state.left_tab == "vassals":
        if not hasattr(state, "vassal_selected_province"):
            state.vassal_selected_province = None
        if not hasattr(state, "vassal_inspecting_liege_id"):
            state.vassal_inspecting_liege_id = None
        if not hasattr(state, "vassal_page"):
            state.vassal_page = 0

        # Gather realm provinces belonging to the player
        vassal_provinces = [pid for pid, prov in PROVINCES.items() if prov.get("owner") == state.player_id]

        # Feudal Hierarchy Metrics & Vassal Limit Calculation
        direct_vassal_count = sum(1 for pid in vassal_provinces for v in state.vassals.get(pid, []) if v.get("rank") in ("count", "duke"))
        vassal_limit = getattr(state, "vassal_limit", 5)
        is_over_limit = (direct_vassal_count > vassal_limit)
        limit_penalty = min(100, (direct_vassal_count - vassal_limit) * 10) if is_over_limit else 0

        # -------------------------------------------------------------
        # LEVEL 3: INSPECTING A COUNT'S DIRECT SUB-VASSALS (RETINUE)
        # -------------------------------------------------------------
        if state.vassal_inspecting_liege_id is not None:
            liege_id = state.vassal_inspecting_liege_id
            liege_v = next((v for plist in state.vassals.values() for v in plist if v.get("id") == liege_id), None)
            l_name = liege_v["name"].split()[1] if liege_v else "Count"
            l_rank = liege_v.get("rank", "count") if liege_v else "count"
            l_sym, l_col = get_feudal_badge(l_rank)

            # Back button to Level 2 (Province)
            back_btn = pygame.Rect(25, 298, 120, 24)
            is_back_hov = back_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (45, 65, 90) if is_back_hov else (30, 42, 60), back_btn, border_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD if is_back_hov else (80, 140, 220), back_btn, 1, border_radius=4)
            screen.blit(font_xs.render("◄ BACK TO PROV", True, COLOR_GOLD if is_back_hov else COLOR_TEXT_WHITE), (31, 303))

            hdr_lbl = font_xs.render(f"{l_sym} {l_name}'s Direct Vassals", True, COLOR_GOLD)
            screen.blit(hdr_lbl, (152, 302))

            if mouse_clicked and is_back_hov:
                state.vassal_inspecting_liege_id = None
                state.vassal_page = 0

            # Sub-vassals swearing direct fealty to this Count
            sub_list = [v for plist in state.vassals.values() for v in plist if v.get("liege_id") == liege_id or (liege_v and v.get("id") in liege_v.get("sub_vassals", []))]

            per_page = 5
            max_pages = max(1, (len(sub_list) + per_page - 1) // per_page)
            state.vassal_page = max(0, min(getattr(state, "vassal_page", 0), max_pages - 1))
            start_i = state.vassal_page * per_page
            cur_page_subs = sub_list[start_i:start_i + per_page]

            vy = 328
            for b_data in cur_page_subs:
                b_card = pygame.Rect(content_x, vy, content_w, 54)
                is_bc_hov = b_card.collidepoint(mouse_pos)

                gift_btn = pygame.Rect(content_x + content_w - 68, vy + 4, 62, 20)
                is_g_hov = gift_btn.collidepoint(mouse_pos)
                can_gift = (state.player["gold"] >= 50)

                pygame.draw.rect(screen, (50, 60, 78) if is_bc_hov else (34, 40, 52), b_card, border_radius=4)
                pygame.draw.rect(screen, (140, 180, 220) if is_bc_hov else COLOR_PANEL_BORDER, b_card, 1, border_radius=4)

                pw, b_col = draw_feudal_pill(screen, font_xs, b_data.get("rank", "baron"), 32, vy + 4)
                b_name_parts = b_data["name"].split(maxsplit=1)
                b_name_disp = b_name_parts[1] if len(b_name_parts) > 1 else b_data["name"]
                if len(b_name_disp) > 22: b_name_disp = b_name_disp[:20] + ".."
                screen.blit(font_xs.render(b_name_disp, True, COLOR_TEXT_WHITE), (32 + pw + 6, vy + 5))

                # Gift button
                g_bg = (30, 70, 40) if (is_g_hov and can_gift) else ((20, 50, 30) if can_gift else (40, 42, 48))
                g_bd = COLOR_TEXT_GREEN if can_gift else (80, 85, 95)
                pygame.draw.rect(screen, g_bg, gift_btn, border_radius=3)
                pygame.draw.rect(screen, g_bd, gift_btn, 1, border_radius=3)
                g_lbl = font_xs.render("+50g 🎁", True, COLOR_TEXT_WHITE if can_gift else COLOR_TEXT_MUTED)
                screen.blit(g_lbl, (gift_btn.x + (gift_btn.w - g_lbl.get_width()) // 2, gift_btn.y + 2))

                st = get_vassal_landed_status(state, b_data, b_data.get("province"))
                f_name = b_data.get("city_name") or "Barony Holding"
                if len(f_name) > 30: f_name = f_name[:28] + ".."
                screen.blit(font_xs.render(f"Fief: {f_name} • Liege: {l_name}", True, (210, 220, 235)), (32, vy + 20))

                screen.blit(font_xs.render(f"Gold: {fmt_gold(b_data['gold'])}g  •  Levy: +{st['levy_contribution']}  •  Tax to {l_name}: +{fmt_gold(st['tax_paid'])}g/m", True, COLOR_TEXT_MUTED), (32, vy + 36))

                if mouse_clicked:
                    if is_g_hov:
                        if can_gift:
                            state.player["gold"] = round(state.player["gold"] - 50, 1)
                            b_data["gold"] = round(b_data.get("gold", 0) + 50, 1)
                            state.logs.append(f"👑 Sent 50g royal subsidy to {b_data['name']} (Treasury: {fmt_gold(b_data['gold'])}g).")
                        else:
                            state.logs.append(f"⚠️ Need 50 gold to send subsidy to {b_data['name']}!")
                    elif is_bc_hov:
                        state.selected_province = b_data.get("province")
                        state.inspecting_vassal = {"province": b_data.get("province"), "vassal": b_data}
                        if b_data.get("tiles"): state.selected_settlement = b_data["tiles"][0]
                        state.logs.append(f"Opened royal dossier for vassal {b_data['name']}.")

                vy += 58

            if not sub_list:
                screen.blit(font_sm.render(f"{l_name} currently has no direct sub-vassals.", True, COLOR_TEXT_MUTED), (25, 350))

            # Pagination Controls
            py_btn = 645
            btn_prev = pygame.Rect(content_x, py_btn, 110, 28)
            btn_next = pygame.Rect(content_x + content_w - 110, py_btn, 110, 28)
            is_prev_hov = btn_prev.collidepoint(mouse_pos)
            is_next_hov = btn_next.collidepoint(mouse_pos)
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
            screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.vassal_page > 0 else COLOR_TEXT_MUTED), (btn_prev.x + (btn_prev.w - font_xs.size("PREV")[0]) // 2, py_btn + 6))
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
            screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.vassal_page < max_pages - 1 else COLOR_TEXT_MUTED), (btn_next.x + (btn_next.w - font_xs.size("NEXT")[0]) // 2, py_btn + 6))
            page_str = f"Page {state.vassal_page + 1}/{max_pages}"
            p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
            screen.blit(p_lbl, (content_x + (content_w - p_lbl.get_width()) // 2, py_btn + 6))
            if mouse_clicked and is_prev_hov and state.vassal_page > 0: state.vassal_page -= 1
            elif mouse_clicked and is_next_hov and state.vassal_page < max_pages - 1: state.vassal_page += 1

        # -------------------------------------------------------------
        # LEVEL 1: LIST OF PROVINCES IN THE REALM & DIRECT VASSALS
        # -------------------------------------------------------------
        elif state.vassal_selected_province is None:
            total_provs = len(vassal_provinces)
            header_lbl = font_md.render("Realm Feudal Vassals", True, COLOR_GOLD)
            screen.blit(header_lbl, (25, 300))

            # Vassal Limit Badge (CK2 Style)
            limit_col = COLOR_TEXT_RED if is_over_limit else COLOR_TEXT_GREEN
            limit_txt = f"Direct: {direct_vassal_count}/{vassal_limit}"
            if is_over_limit: limit_txt += f" (-{limit_penalty}%)"
            lim_lbl = font_xs.render(limit_txt, True, limit_col)
            screen.blit(lim_lbl, (content_x + content_w - lim_lbl.get_width() - 4, 304))

            per_page = 5
            max_pages = max(1, (total_provs + per_page - 1) // per_page)
            state.vassal_page = max(0, min(getattr(state, "vassal_page", 0), max_pages - 1))

            start_i = state.vassal_page * per_page
            cur_page_provs = vassal_provinces[start_i:start_i + per_page]

            vy = 328
            for pid in cur_page_provs:
                prov_v_list = state.vassals.get(pid, [])
                p_info = PROVINCES.get(pid, {})
                p_name = p_info.get("name", pid).split()[0]

                # Identify provincial lord (first lord in list)
                direct_v = prov_v_list[0] if prov_v_list else None
                is_dv_direct = direct_v.get("is_direct_vassal", False) if direct_v else False
                dv_name = direct_v["name"] if direct_v else "Royal Demesne"
                dv_rank = direct_v.get("rank", "crown") if direct_v else "crown"
                dv_subs = len(direct_v.get("sub_vassals", [])) if direct_v else 0

                # Calculate province total levy & tax paid
                total_levy = 0
                total_tax = 0.0
                if direct_v:
                    st = get_vassal_landed_status(state, direct_v, pid)
                    total_levy = st["levy_contribution"]
                    total_tax = st["tax_paid"]

                p_card = pygame.Rect(content_x, vy, content_w, 54)
                is_p_hov = p_card.collidepoint(mouse_pos)
                is_active_prov = (state.selected_province == pid)

                bg_c = (60, 50, 24) if is_active_prov else ((50, 60, 78) if is_p_hov else (34, 40, 52))
                border_c = COLOR_GOLD if (is_p_hov or is_active_prov) else (80, 140, 220)

                pygame.draw.rect(screen, bg_c, p_card, border_radius=4)
                pygame.draw.rect(screen, border_c, p_card, 1, border_radius=4)

                screen.blit(font_sm.render(f"◆ {p_name}", True, COLOR_GOLD), (34, vy + 4))
                p_name_w = font_sm.size(f"◆ {p_name}")[0]
                pw, dv_col = draw_feudal_pill(screen, font_xs, dv_rank, 34 + p_name_w + 10, vy + 4)
                
                dv_parts = dv_name.split(maxsplit=1)
                dv_name_disp = dv_parts[1] if len(dv_parts) > 1 else dv_name
                if len(dv_name_disp) > 15: dv_name_disp = dv_name_disp[:13] + ".."
                screen.blit(font_xs.render(dv_name_disp, True, COLOR_TEXT_WHITE), (34 + p_name_w + 10 + pw + 6, vy + 5))

                fief_seat = (direct_v.get("city_name") if direct_v else None) or "Capital Citadel"
                if len(fief_seat) > 22: fief_seat = fief_seat[:20] + ".."
                desc_str = f"Seat: {fief_seat} • 👥 {dv_subs} Barons • Fyrd: +{total_levy} • Tax: +{fmt_gold(total_tax)}g/m"
                screen.blit(font_xs.render(desc_str, True, (210, 230, 255)), (34, vy + 28))

                # Buttons on card: 1-click [ ⬇ Demote ] (to Baron) / [ ⬆ Promote ] (to Count) and [ View › ]
                act_btn = None
                is_act_hov = False
                is_count_tier = (dv_rank in ("count", "duke"))

                if direct_v and pid != "solaris_prime":
                    act_btn = pygame.Rect(content_x + content_w - 130, vy + 14, 58, 24)
                    is_act_hov = act_btn.collidepoint(mouse_pos)
                    if is_count_tier:
                        a_bg = (80, 40, 40) if is_act_hov else (60, 28, 28)
                        a_bd = (220, 100, 100) if is_act_hov else (160, 65, 65)
                        a_txt = "⬇ Demote"
                        a_col = COLOR_TEXT_WHITE if is_act_hov else (240, 190, 190)
                    else:
                        a_bg = (32, 70, 45) if is_act_hov else (22, 48, 30)
                        a_bd = (100, 210, 130) if is_act_hov else (60, 140, 80)
                        a_txt = "⬆ Promote"
                        a_col = COLOR_TEXT_WHITE if is_act_hov else (180, 240, 195)
                    pygame.draw.rect(screen, a_bg, act_btn, border_radius=3)
                    pygame.draw.rect(screen, a_bd, act_btn, 1, border_radius=3)
                    a_lbl = font_xs.render(a_txt, True, a_col)
                    screen.blit(a_lbl, (act_btn.x + (act_btn.w - a_lbl.get_width()) // 2, act_btn.y + 4))

                view_btn = pygame.Rect(content_x + content_w - 65, vy + 14, 58, 24)
                is_v_hov = view_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 65, 95) if is_v_hov else (28, 45, 68), view_btn, border_radius=3)
                pygame.draw.rect(screen, COLOR_GOLD if is_v_hov else (70, 120, 180), view_btn, 1, border_radius=3)
                v_lbl = font_xs.render("View ›", True, COLOR_GOLD if is_v_hov else COLOR_TEXT_WHITE)
                screen.blit(v_lbl, (view_btn.x + (view_btn.w - v_lbl.get_width()) // 2, view_btn.y + 4))

                if mouse_clicked:
                    if act_btn and is_act_hov:
                        if is_count_tier:
                            state.demote_to_baron(direct_v["id"])
                        else:
                            state.promote_to_direct_vassal(direct_v["id"])
                    elif is_v_hov or is_p_hov:
                        state.vassal_selected_province = pid
                        state.vassal_inspecting_liege_id = None
                        state.vassal_page = 0
                        state.selected_province = pid
                        state.logs.append(f"Viewing feudal administration of {p_name}.")

                vy += 58

            if not vassal_provinces:
                screen.blit(font_sm.render("No provinces under realm rule.", True, COLOR_TEXT_MUTED), (25, 350))

            # Bottom Pagination Controls for Province List
            py_btn = 645
            btn_prev = pygame.Rect(content_x, py_btn, 110, 28)
            btn_next = pygame.Rect(content_x + content_w - 110, py_btn, 110, 28)
            is_prev_hov = btn_prev.collidepoint(mouse_pos)
            is_next_hov = btn_next.collidepoint(mouse_pos)

            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
            screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.vassal_page > 0 else COLOR_TEXT_MUTED), (btn_prev.x + (btn_prev.w - font_xs.size("PREV")[0]) // 2, py_btn + 6))

            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
            screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.vassal_page < max_pages - 1 else COLOR_TEXT_MUTED), (btn_next.x + (btn_next.w - font_xs.size("NEXT")[0]) // 2, py_btn + 6))

            page_str = f"Page {state.vassal_page + 1}/{max_pages}"
            p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
            screen.blit(p_lbl, (content_x + (content_w - p_lbl.get_width()) // 2, py_btn + 6))

            if mouse_clicked and is_prev_hov and state.vassal_page > 0:
                state.vassal_page -= 1
            elif mouse_clicked and is_next_hov and state.vassal_page < max_pages - 1:
                state.vassal_page += 1

        # -------------------------------------------------------------
        # LEVEL 2: LIST OF VASSALS INSIDE THE SELECTED PROVINCE
        # -------------------------------------------------------------
        else:
            sel_pid = state.vassal_selected_province
            prov_vassals = state.vassals.get(sel_pid, [])
            p_info = PROVINCES.get(sel_pid, {})
            p_name = p_info.get("name", sel_pid).split()[0]

            # Back Button & Province Header
            back_btn = pygame.Rect(25, 298, 105, 24)
            is_back_hov = back_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (45, 65, 90) if is_back_hov else (30, 42, 60), back_btn, border_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD if is_back_hov else (80, 140, 220), back_btn, 1, border_radius=4)
            screen.blit(font_xs.render("◄ ALL PROVS", True, COLOR_GOLD if is_back_hov else COLOR_TEXT_WHITE), (33, 303))

            header_lbl = font_sm.render(f"◆ {p_name} ({len(prov_vassals)} Lords)", True, COLOR_GOLD)
            screen.blit(header_lbl, (140, 302))

            if mouse_clicked and is_back_hov:
                state.vassal_selected_province = None
                state.vassal_inspecting_liege_id = None
                state.vassal_page = 0

            per_page = 5
            max_pages = max(1, (len(prov_vassals) + per_page - 1) // per_page)
            state.vassal_page = max(0, min(getattr(state, "vassal_page", 0), max_pages - 1))

            start_i = state.vassal_page * per_page
            cur_page_vassals = prov_vassals[start_i:start_i + per_page]

            vy = 328
            for v_data in cur_page_vassals:
                is_direct = v_data.get("is_direct_vassal", True)
                card_h = 58 if is_direct else 52
                v_card = pygame.Rect(content_x, vy, content_w, card_h)
                is_vc_hov = v_card.collidepoint(mouse_pos)

                # Buttons on card: [ 👥 Vassals (N) › ] [ ⬇ Demote ] / [ ⬆ Direct ] [ +50g 🎁 ]
                is_sub_hov = False
                sub_btn = None
                is_dem_hov = False
                dem_btn = None
                is_prom_hov = False
                prom_btn = None

                gift_btn = pygame.Rect(content_x + content_w - 56, vy + 4, 52, 20)
                is_g_hov = gift_btn.collidepoint(mouse_pos)
                can_gift = (state.player["gold"] >= 50)

                if is_direct:
                    n_subs = len(v_data.get("sub_vassals", []))
                    dem_btn = pygame.Rect(content_x + content_w - 110, vy + 4, 50, 20)
                    is_dem_hov = dem_btn.collidepoint(mouse_pos)
                    sub_btn = pygame.Rect(content_x + content_w - 200, vy + 4, 86, 20)
                    is_sub_hov = sub_btn.collidepoint(mouse_pos)
                else:
                    prom_btn = pygame.Rect(content_x + content_w - 115, vy + 4, 55, 20)
                    is_prom_hov = prom_btn.collidepoint(mouse_pos)

                # Card styling (Direct Vassal has richer golden tint)
                if is_direct:
                    c_bg = (54, 58, 76) if is_vc_hov else (38, 44, 58)
                    c_bd = COLOR_GOLD if is_vc_hov else (140, 180, 230)
                else:
                    c_bg = (48, 56, 72) if is_vc_hov else (34, 40, 52)
                    c_bd = (140, 180, 220) if is_vc_hov else COLOR_PANEL_BORDER

                pygame.draw.rect(screen, c_bg, v_card, border_radius=4)
                pygame.draw.rect(screen, c_bd, v_card, 1, border_radius=4)

                # Vassal Name & Feudal Rank Pill
                pw, rk_col = draw_feudal_pill(screen, font_xs, v_data.get("rank", "count" if is_direct else "baron"), 32, vy + 4)
                v_parts = v_data["name"].split(maxsplit=1)
                v_name_disp = v_parts[1] if len(v_parts) > 1 else v_data["name"]
                max_chars = 14 if is_direct else 20
                if len(v_name_disp) > max_chars:
                    v_name_disp = v_name_disp[:max_chars - 2] + ".."
                screen.blit(font_xs.render(v_name_disp, True, COLOR_TEXT_WHITE), (32 + pw + 6, vy + 5))

                # Render Direct Vassals Button for Count
                if is_direct and sub_btn:
                    s_bg = (45, 75, 110) if is_sub_hov else (30, 50, 75)
                    s_bd = (120, 190, 255) if is_sub_hov else (80, 130, 180)
                    pygame.draw.rect(screen, s_bg, sub_btn, border_radius=3)
                    pygame.draw.rect(screen, s_bd, sub_btn, 1, border_radius=3)
                    s_lbl = font_xs.render(f"👥 Vassals ({n_subs}) ›", True, COLOR_TEXT_WHITE if is_sub_hov else (200, 230, 255))
                    screen.blit(s_lbl, (sub_btn.x + (sub_btn.w - s_lbl.get_width()) // 2, sub_btn.y + 2))

                # Render Demote Button for Count (Transfer Vassalage)
                if is_direct and dem_btn:
                    d_bg = (90, 45, 45) if is_dem_hov else (65, 30, 30)
                    d_bd = (220, 110, 110) if is_dem_hov else (160, 70, 70)
                    pygame.draw.rect(screen, d_bg, dem_btn, border_radius=3)
                    pygame.draw.rect(screen, d_bd, dem_btn, 1, border_radius=3)
                    d_lbl = font_xs.render("⬇ Demote", True, COLOR_TEXT_WHITE if is_dem_hov else (240, 190, 190))
                    screen.blit(d_lbl, (dem_btn.x + (dem_btn.w - d_lbl.get_width()) // 2, dem_btn.y + 2))

                # Render Promote Button for Baron
                if not is_direct and prom_btn:
                    p_bg = (40, 75, 55) if is_prom_hov else (25, 50, 38)
                    p_bd = (110, 210, 140) if is_prom_hov else (70, 150, 95)
                    pygame.draw.rect(screen, p_bg, prom_btn, border_radius=3)
                    pygame.draw.rect(screen, p_bd, prom_btn, 1, border_radius=3)
                    p_lbl = font_xs.render("⬆ Direct", True, COLOR_TEXT_WHITE if is_prom_hov else (190, 240, 205))
                    screen.blit(p_lbl, (prom_btn.x + (prom_btn.w - p_lbl.get_width()) // 2, prom_btn.y + 2))

                # Draw Gift Button
                g_bg = (30, 70, 40) if (is_g_hov and can_gift) else ((20, 50, 30) if can_gift else (40, 42, 48))
                g_bd = COLOR_TEXT_GREEN if can_gift else (80, 85, 95)
                pygame.draw.rect(screen, g_bg, gift_btn, border_radius=3)
                pygame.draw.rect(screen, g_bd, gift_btn, 1, border_radius=3)
                g_lbl = font_xs.render("+50g 🎁", True, COLOR_TEXT_WHITE if can_gift else COLOR_TEXT_MUTED)
                screen.blit(g_lbl, (gift_btn.x + (gift_btn.w - g_lbl.get_width()) // 2, gift_btn.y + 2))

                st = get_vassal_landed_status(state, v_data, sel_pid)
                f_seat = v_data.get("city_name") or "Landed Holding"
                if len(f_seat) > 28: f_seat = f_seat[:26] + ".."

                if is_direct:
                    tile_cnt = len(v_data.get("tiles", []))
                    screen.blit(font_xs.render(f"Fief: {f_seat} ({tile_cnt} Tiles • Province Liege)", True, (220, 235, 255)), (32, vy + 21))
                    screen.blit(font_xs.render(f"Gold: {fmt_gold(v_data['gold'])}g • Tax to King: +{fmt_gold(st['tax_paid'])}g/m • Sub-Tax: +{fmt_gold(st.get('sub_tax_collected', 0))}g", True, COLOR_TEXT_MUTED), (32, vy + 38))
                else:
                    c_liege = next((cv for cv in prov_vassals if cv.get("is_direct_vassal", True)), None)
                    l_short = c_liege["name"].split()[1] if c_liege else "Count"
                    screen.blit(font_xs.render(f"Fief: {f_seat} (Subordinate to {l_short})", True, (200, 215, 235)), (32, vy + 19))
                    screen.blit(font_xs.render(f"Gold: {fmt_gold(v_data['gold'])}g • Levy: +{st['levy_contribution']} • Tax to {l_short}: +{fmt_gold(st['tax_paid'])}g/m", True, COLOR_TEXT_MUTED), (32, vy + 34))

                if mouse_clicked:
                    if is_direct and is_dem_hov:
                        state.vassal_subordinate_target_id = v_data["id"]
                        state.logs.append(f"Selecting new liege for {v_data['name']} to reduce direct vassals...")
                    elif not is_direct and is_prom_hov:
                        state.promote_to_direct_vassal(v_data["id"])
                    elif is_direct and is_sub_hov:
                        state.vassal_inspecting_liege_id = v_data["id"]
                        state.vassal_page = 0
                        state.logs.append(f"Inspecting direct vassals of {v_data['name']}.")
                    elif is_g_hov:
                        if can_gift:
                            state.player["gold"] = round(state.player["gold"] - 50, 1)
                            v_data["gold"] = round(v_data.get("gold", 0) + 50, 1)
                            state.logs.append(f"👑 Sent 50g royal subsidy to {v_data['name']} (Treasury: {fmt_gold(v_data['gold'])}g).")
                        else:
                            state.logs.append(f"⚠️ Need 50 gold to send subsidy to {v_data['name']}!")
                    elif is_vc_hov:
                        state.selected_province = sel_pid
                        state.inspecting_vassal = {"province": sel_pid, "vassal": v_data}
                        if v_data.get("tiles"):
                            state.selected_settlement = v_data["tiles"][0]
                        state.logs.append(f"Opened royal dossier for vassal {v_data['name']}.")

                vy += (card_h + 4)

            if not prov_vassals:
                screen.blit(font_sm.render(f"No vassals currently in {p_name}.", True, COLOR_TEXT_MUTED), (25, 350))

            # Bottom Pagination Controls for Vassal List
            py_btn = 645
            btn_prev = pygame.Rect(content_x, py_btn, 110, 28)
            btn_next = pygame.Rect(content_x + content_w - 110, py_btn, 110, 28)

            is_prev_hov = btn_prev.collidepoint(mouse_pos)
            is_next_hov = btn_next.collidepoint(mouse_pos)

            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
            screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.vassal_page > 0 else COLOR_TEXT_MUTED), (btn_prev.x + (btn_prev.w - font_xs.size("PREV")[0]) // 2, py_btn + 6))

            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
            screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.vassal_page < max_pages - 1 else COLOR_TEXT_MUTED), (btn_next.x + (btn_next.w - font_xs.size("NEXT")[0]) // 2, py_btn + 6))

            page_str = f"Page {state.vassal_page + 1}/{max_pages}"
            p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
            screen.blit(p_lbl, (content_x + (content_w - p_lbl.get_width()) // 2, py_btn + 6))

            if mouse_clicked and is_prev_hov and state.vassal_page > 0:
                state.vassal_page -= 1
            elif mouse_clicked and is_next_hov and state.vassal_page < max_pages - 1:
                state.vassal_page += 1
    
    elif state.left_tab == "laws":
        # Feudal Realm Laws View (Customizable per-vassal tax and levy rates 0% - 90%)
        if not hasattr(state, "universal_tax_target"):
            state.universal_tax_target = 10
        if not hasattr(state, "universal_levy_target"):
            state.universal_levy_target = 20
    
        # -------------------------------------------------------------
        # Universal Realm Law Enactment Bar ("STANDARDIZE ALL")
        # -------------------------------------------------------------
        uni_rect = pygame.Rect(content_x, 298, content_w, 56)
        pygame.draw.rect(screen, (32, 38, 50), uni_rect, border_radius=5)
        pygame.draw.rect(screen, (70, 95, 130), uni_rect, 1, border_radius=5)
    
        # Row 1: Tax target controls & Levy target controls
        screen.blit(font_xs.render("Tax:", True, COLOR_GOLD), (31, 304))
        btn_uni_t_dec = pygame.Rect(58, 303, 16, 17)
        box_uni_t_rate = pygame.Rect(76, 303, 34, 17)
        btn_uni_t_inc = pygame.Rect(112, 303, 16, 17)
    
        screen.blit(font_xs.render("Levy:", True, COLOR_GOLD), (138, 304))
        btn_uni_l_dec = pygame.Rect(168, 303, 16, 17)
        box_uni_l_rate = pygame.Rect(186, 303, 34, 17)
        btn_uni_l_inc = pygame.Rect(222, 303, 16, 17)
    
        # Row 2: Standardize All Button
        btn_uni_apply = pygame.Rect(content_x + 6, 326, content_w - 12, 22)
    
        hov_uni_t_dec = btn_uni_t_dec.collidepoint(mouse_pos)
        hov_uni_t_inc = btn_uni_t_inc.collidepoint(mouse_pos)
        hov_uni_l_dec = btn_uni_l_dec.collidepoint(mouse_pos)
        hov_uni_l_inc = btn_uni_l_inc.collidepoint(mouse_pos)
        hov_uni_apply = btn_uni_apply.collidepoint(mouse_pos)
    
        # Tax [-]
        pygame.draw.rect(screen, (60, 70, 90) if hov_uni_t_dec else (42, 48, 62), btn_uni_t_dec, border_radius=3)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_uni_t_dec, 1, border_radius=3)
        screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE if hov_uni_t_dec else (200, 210, 230)), (63, 303))
    
        # Tax Box
        pygame.draw.rect(screen, (24, 30, 42), box_uni_t_rate, border_radius=3)
        pygame.draw.rect(screen, (80, 120, 180), box_uni_t_rate, 1, border_radius=3)
        ut_lbl = font_xs.render(f"{state.universal_tax_target}%", True, COLOR_GOLD)
        screen.blit(ut_lbl, (box_uni_t_rate.x + (box_uni_t_rate.w - ut_lbl.get_width()) // 2, 304))
    
        # Tax [+]
        pygame.draw.rect(screen, (60, 70, 90) if hov_uni_t_inc else (42, 48, 62), btn_uni_t_inc, border_radius=3)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_uni_t_inc, 1, border_radius=3)
        screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE if hov_uni_t_inc else (200, 210, 230)), (117, 303))
    
        # Levy [-]
        pygame.draw.rect(screen, (60, 70, 90) if hov_uni_l_dec else (42, 48, 62), btn_uni_l_dec, border_radius=3)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_uni_l_dec, 1, border_radius=3)
        screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE if hov_uni_l_dec else (200, 210, 230)), (173, 303))
    
        # Levy Box
        pygame.draw.rect(screen, (24, 30, 42), box_uni_l_rate, border_radius=3)
        pygame.draw.rect(screen, (80, 120, 180), box_uni_l_rate, 1, border_radius=3)
        ul_lbl = font_xs.render(f"{state.universal_levy_target}%", True, COLOR_GOLD)
        screen.blit(ul_lbl, (box_uni_l_rate.x + (box_uni_l_rate.w - ul_lbl.get_width()) // 2, 304))
    
        # Levy [+]
        pygame.draw.rect(screen, (60, 70, 90) if hov_uni_l_inc else (42, 48, 62), btn_uni_l_inc, border_radius=3)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_uni_l_inc, 1, border_radius=3)
        screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE if hov_uni_l_inc else (200, 210, 230)), (227, 303))
    
        # [ ⚡ STANDARDIZE ALL ] button
        pygame.draw.rect(screen, (35, 95, 52) if hov_uni_apply else (25, 72, 40), btn_uni_apply, border_radius=3)
        pygame.draw.rect(screen, COLOR_TEXT_GREEN, btn_uni_apply, 1, border_radius=3)
        apply_txt = font_xs.render("⚡ STANDARDIZE ALL UNLOCKED", True, COLOR_TEXT_WHITE)
        screen.blit(apply_txt, (btn_uni_apply.x + (btn_uni_apply.w - apply_txt.get_width()) // 2, 329))
    
        if mouse_clicked:
            if hov_uni_t_dec:
                state.universal_tax_target = max(0, state.universal_tax_target - 5)
            elif hov_uni_t_inc:
                state.universal_tax_target = min(90, state.universal_tax_target + 5)
            elif hov_uni_l_dec:
                state.universal_levy_target = max(0, state.universal_levy_target - 5)
            elif hov_uni_l_inc:
                state.universal_levy_target = min(90, state.universal_levy_target + 5)
            elif hov_uni_apply:
                app_count = 0
                lock_count = 0
                for r_pid, r_prov in PROVINCES.items():
                    if r_prov["owner"] == state.player_id:
                        for v_item in state.vassals.get(r_pid, []):
                            is_locked = v_item.get("laws_locked", v_item.get("tax_locked", False) or v_item.get("levy_locked", False))
                            if is_locked:
                                lock_count += 1
                            else:
                                v_item["tax_rate"] = state.universal_tax_target
                                v_item["levy_rate"] = state.universal_levy_target
                                st_v = get_vassal_landed_status(state, v_item, r_pid)
                                v_item["tax_contribution"] = st_v["tax_paid"]
                                v_item["levy_contribution"] = st_v["levy_contribution"]
                                sync_province_holdings_stats(state, r_pid)
                                app_count += 1
                state.logs.append(f"Royal Decree: Standardized Tax ({state.universal_tax_target}%) & Levies ({state.universal_levy_target}%) across {app_count} vassals! ({lock_count} locked vassals unchanged).")
    
        # -------------------------------------------------------------
        # Vassals List with Dual Settings (Tax + Levies) & LOCK Toggles
        # -------------------------------------------------------------
        realm_vassals = []
        for pid, prov in PROVINCES.items():
            if prov["owner"] == state.player_id:
                for v in state.vassals.get(pid, []):
                    realm_vassals.append((pid, v))
    
        total_v = len(realm_vassals)
        header_text = f"Feudal Laws ({total_v} Lords)"
        header_lbl = font_md.render(header_text, True, COLOR_GOLD)
        screen.blit(header_lbl, (25, 359))
    
        per_page = 3
        max_pages = max(1, (total_v + per_page - 1) // per_page)
        state.laws_page = max(0, min(getattr(state, "laws_page", 0), max_pages - 1))
    
        # Header Top Pagination Controls (< 1/7 >)
        top_btn_prev = pygame.Rect(216, 359, 18, 18)
        top_btn_next = pygame.Rect(268, 359, 18, 18)
        is_top_prev_hov = top_btn_prev.collidepoint(mouse_pos)
        is_top_next_hov = top_btn_next.collidepoint(mouse_pos)
    
        p_top_prev_col = COLOR_TEXT_WHITE if (state.laws_page > 0 and not is_top_prev_hov) else (COLOR_GOLD if is_top_prev_hov else (70, 75, 85))
        p_top_next_col = COLOR_TEXT_WHITE if (state.laws_page < max_pages - 1 and not is_top_next_hov) else (COLOR_GOLD if is_top_next_hov else (70, 75, 85))
        screen.blit(font_xs.render("<", True, p_top_prev_col), (221, 361))
        p_top_str = f"{state.laws_page + 1}/{max_pages}"
        p_top_lbl = font_xs.render(p_top_str, True, COLOR_TEXT_MUTED)
        screen.blit(p_top_lbl, (244 - p_top_lbl.get_width() // 2, 361))
        screen.blit(font_xs.render(">", True, p_top_next_col), (content_x + content_w - 14, 361))
    
        if mouse_clicked and is_top_prev_hov and state.laws_page > 0:
            state.laws_page -= 1
        elif mouse_clicked and is_top_next_hov and state.laws_page < max_pages - 1:
            state.laws_page += 1
    
        start_i = state.laws_page * per_page
        cur_page_vassals = realm_vassals[start_i:start_i + per_page]
    
        vy = 380
        for v_pid, v_data in cur_page_vassals:
            v_card = pygame.Rect(content_x, vy, content_w, 74)
            is_vc_hov = v_card.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (46, 54, 70) if is_vc_hov else (32, 38, 50), v_card, border_radius=5)
            pygame.draw.rect(screen, COLOR_GOLD if is_vc_hov else COLOR_PANEL_BORDER, v_card, 1, border_radius=5)
    
            prov_short = PROVINCES[v_pid]["name"].split()[0]
            lord_name = v_data['name']
            if len(lord_name) > 23:
                lord_name = lord_name[:21] + ".."
            screen.blit(font_xs.render(f"♟ {lord_name}", True, COLOR_GOLD), (32, vy + 4))
            p_tag = font_xs.render(f"[{prov_short}]", True, (140, 200, 255))
            screen.blit(p_tag, (content_x + content_w - p_tag.get_width() - 8, vy + 4))
    
            st = get_vassal_landed_status(state, v_data, v_pid)
            if st["is_landed"]:
                h_name = v_data.get("city_name") or (st["held_fiefs"][0].get("name") if st.get("held_fiefs") else None) or (st["held_settlements"][0].get("name") if st.get("held_settlements") else None) or "Landed Noble"
            else:
                h_name = "Landless Noble"
            if len(h_name) > 17:
                h_name = h_name[:15] + ".."
            screen.blit(font_xs.render(f"Fief: {h_name}", True, (200, 215, 230)), (32, vy + 19))
    
            # Lock Button at top right of card
            is_locked = v_data.get("laws_locked", v_data.get("tax_locked", False) or v_data.get("levy_locked", False))
            btn_lock = pygame.Rect(content_x + content_w - 92, vy + 18, 86, 18)
            hov_lock = btn_lock.collidepoint(mouse_pos)
    
            lock_bg = (65, 50, 20) if is_locked else ((45, 52, 68) if hov_lock else (28, 34, 46))
            lock_bd = COLOR_GOLD if is_locked else ((120, 160, 210) if hov_lock else (70, 80, 95))
            pygame.draw.rect(screen, lock_bg, btn_lock, border_radius=3)
            pygame.draw.rect(screen, lock_bd, btn_lock, 1, border_radius=3)
            l_txt = "◈ LOCKED" if is_locked else "◇ UNLOCK"
            l_col = COLOR_GOLD if is_locked else COLOR_TEXT_MUTED
            l_lbl = font_xs.render(l_txt, True, l_col)
            screen.blit(l_lbl, (btn_lock.x + (btn_lock.w - l_lbl.get_width()) // 2, vy + 19))
    
            # Row 3: Gold Tax Controls [ 💰 Tax: [-] [XX%] [+] (+Xg/m) ]
            cur_tax = v_data.get("tax_rate", 10)
            screen.blit(font_xs.render("💰 Tax:", True, COLOR_GOLD), (32, vy + 37))
    
            btn_t_dec = pygame.Rect(74, vy + 36, 16, 16)
            box_t_rate = pygame.Rect(92, vy + 36, 34, 16)
            btn_t_inc = pygame.Rect(128, vy + 36, 16, 16)
    
            hov_t_dec = btn_t_dec.collidepoint(mouse_pos)
            hov_t_rate = box_t_rate.collidepoint(mouse_pos)
            hov_t_inc = btn_t_inc.collidepoint(mouse_pos)
    
            pygame.draw.rect(screen, (70, 80, 100) if hov_t_dec else (42, 48, 62), btn_t_dec, border_radius=3)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_t_dec, 1, border_radius=3)
            screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE), (79, vy + 36))
    
            pygame.draw.rect(screen, (28, 34, 46), box_t_rate, border_radius=3)
            pygame.draw.rect(screen, (90, 140, 210) if hov_t_rate else COLOR_PANEL_BORDER, box_t_rate, 1, border_radius=3)
            t_lbl = font_xs.render(f"{cur_tax}%", True, COLOR_GOLD)
            screen.blit(t_lbl, (box_t_rate.x + (box_t_rate.w - t_lbl.get_width()) // 2, vy + 37))
    
            pygame.draw.rect(screen, (70, 80, 100) if hov_t_inc else (42, 48, 62), btn_t_inc, border_radius=3)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_t_inc, 1, border_radius=3)
            screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE), (133, vy + 36))
    
            tax_info = f"+{fmt_gold(st['tax_paid'])}g/m" if st["is_landed"] else "0g"
            screen.blit(font_xs.render(tax_info, True, COLOR_TEXT_GREEN if st['tax_paid'] > 0 else COLOR_TEXT_MUTED), (150, vy + 37))
    
            # Row 4: Levy Duty Controls [ ⚔ Levy: [-] [XX%] [+] (+X Men) ]
            cur_levy = v_data.get("levy_rate", 20)
            screen.blit(font_xs.render("⚔ Levy:", True, COLOR_GOLD), (32, vy + 55))
    
            btn_l_dec = pygame.Rect(74, vy + 54, 16, 16)
            box_l_rate = pygame.Rect(92, vy + 54, 34, 16)
            btn_l_inc = pygame.Rect(128, vy + 54, 16, 16)
    
            hov_l_dec = btn_l_dec.collidepoint(mouse_pos)
            hov_l_rate = box_l_rate.collidepoint(mouse_pos)
            hov_l_inc = btn_l_inc.collidepoint(mouse_pos)
    
            pygame.draw.rect(screen, (70, 80, 100) if hov_l_dec else (42, 48, 62), btn_l_dec, border_radius=3)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_l_dec, 1, border_radius=3)
            screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE), (79, vy + 54))
    
            pygame.draw.rect(screen, (28, 34, 46), box_l_rate, border_radius=3)
            pygame.draw.rect(screen, (90, 140, 210) if hov_l_rate else COLOR_PANEL_BORDER, box_l_rate, 1, border_radius=3)
            l_lbl = font_xs.render(f"{cur_levy}%", True, COLOR_GOLD)
            screen.blit(l_lbl, (box_l_rate.x + (box_l_rate.w - l_lbl.get_width()) // 2, vy + 55))
    
            pygame.draw.rect(screen, (70, 80, 100) if hov_l_inc else (42, 48, 62), btn_l_inc, border_radius=3)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_l_inc, 1, border_radius=3)
            screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE), (133, vy + 54))
    
            levy_info = f"+{st['levy_contribution']}m" if st["is_landed"] else "0m"
            screen.blit(font_xs.render(levy_info, True, COLOR_TEXT_GREEN if st['levy_contribution'] > 0 else COLOR_TEXT_MUTED), (150, vy + 55))
    
            if mouse_clicked:
                if hov_lock:
                    v_data["laws_locked"] = not is_locked
                    v_data["tax_locked"] = v_data["laws_locked"]
                    v_data["levy_locked"] = v_data["laws_locked"]
                    st_str = "LOCKED (exempt from realm changes)" if v_data["laws_locked"] else "UNLOCKED"
                    state.logs.append(f"Feudal Law: {v_data['name']} is now {st_str}.")
                elif hov_t_dec:
                    new_rate = max(0, cur_tax - 5)
                    v_data["tax_rate"] = new_rate
                    st_new = get_vassal_landed_status(state, v_data, v_pid)
                    v_data["tax_contribution"] = st_new["tax_paid"]
                    sync_province_holdings_stats(state, v_pid)
                    state.logs.append(f"Decreased {v_data['name']}'s tax obligation to {new_rate}%.")
                elif hov_t_inc:
                    new_rate = min(90, cur_tax + 5)
                    v_data["tax_rate"] = new_rate
                    st_new = get_vassal_landed_status(state, v_data, v_pid)
                    v_data["tax_contribution"] = st_new["tax_paid"]
                    sync_province_holdings_stats(state, v_pid)
                    state.logs.append(f"Increased {v_data['name']}'s tax obligation to {new_rate}%.")
                elif hov_t_rate:
                    cycle = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
                    next_i = (cycle.index(cur_tax) + 1) % len(cycle) if cur_tax in cycle else 1
                    new_rate = cycle[next_i]
                    v_data["tax_rate"] = new_rate
                    st_new = get_vassal_landed_status(state, v_data, v_pid)
                    v_data["tax_contribution"] = st_new["tax_paid"]
                    sync_province_holdings_stats(state, v_pid)
                    state.logs.append(f"Adjusted {v_data['name']}'s tax rate to {new_rate}%.")
                elif hov_l_dec:
                    new_rate = max(0, cur_levy - 5)
                    v_data["levy_rate"] = new_rate
                    st_new = get_vassal_landed_status(state, v_data, v_pid)
                    v_data["levy_contribution"] = st_new["levy_contribution"]
                    sync_province_holdings_stats(state, v_pid)
                    state.logs.append(f"Decreased {v_data['name']}'s levy obligation to {new_rate}%.")
                elif hov_l_inc:
                    new_rate = min(90, cur_levy + 5)
                    v_data["levy_rate"] = new_rate
                    st_new = get_vassal_landed_status(state, v_data, v_pid)
                    v_data["levy_contribution"] = st_new["levy_contribution"]
                    sync_province_holdings_stats(state, v_pid)
                    state.logs.append(f"Increased {v_data['name']}'s levy obligation to {new_rate}%.")
                elif hov_l_rate:
                    cycle = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
                    next_i = (cycle.index(cur_levy) + 1) % len(cycle) if cur_levy in cycle else 2
                    new_rate = cycle[next_i]
                    v_data["levy_rate"] = new_rate
                    st_new = get_vassal_landed_status(state, v_data, v_pid)
                    v_data["levy_contribution"] = st_new["levy_contribution"]
                    sync_province_holdings_stats(state, v_pid)
                    state.logs.append(f"Adjusted {v_data['name']}'s levy rate to {new_rate}%.")
                elif is_vc_hov:
                    state.selected_province = v_pid
                    state.inspecting_vassal = {"province": v_pid, "vassal": v_data}
                    if v_data.get("tiles"):
                        state.selected_settlement = v_data["tiles"][0]
                    state.logs.append(f"Inspecting feudal dossier for {v_data['name']}.")
    
            vy += 78
    
        # Bottom Pagination Controls (py_btn = 618)
        py_btn = 618
        btn_prev = pygame.Rect(content_x, py_btn, 110, 28)
        btn_next = pygame.Rect(content_x + content_w - 110, py_btn, 110, 28)
    
        is_prev_hov = btn_prev.collidepoint(mouse_pos)
        is_next_hov = btn_next.collidepoint(mouse_pos)
    
        pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
        screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.laws_page > 0 else COLOR_TEXT_MUTED), (btn_prev.x + (btn_prev.w - font_xs.size("PREV")[0]) // 2, py_btn + 6))
    
        pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
        screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.laws_page < max_pages - 1 else COLOR_TEXT_MUTED), (btn_next.x + (btn_next.w - font_xs.size("NEXT")[0]) // 2, py_btn + 6))
    
        page_str = f"Page {state.laws_page + 1}/{max_pages}"
        p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
        screen.blit(p_lbl, (content_x + (content_w - p_lbl.get_width()) // 2, py_btn + 6))
    
        if mouse_clicked and is_prev_hov and state.laws_page > 0:
            state.laws_page -= 1
        elif mouse_clicked and is_next_hov and state.laws_page < max_pages - 1:
            state.laws_page += 1
    
    elif state.left_tab == "economy":
        # Royal Financial Ledger & Budget View (Income & Expenses Breakdown)
        fin = get_realm_finances(state, state.player_id)
    
        # 1. Summary Treasury Card (y = 298 to 364)
        sum_card = pygame.Rect(content_x, 298, content_w, 66)
        pygame.draw.rect(screen, (34, 42, 56), sum_card, border_radius=6)
        pygame.draw.rect(screen, COLOR_GOLD, sum_card, 1, border_radius=6)
    
        screen.blit(font_md.render("◆ Royal Treasury Ledger", True, COLOR_GOLD), (34, 303))
        screen.blit(font_xs.render(f"Treasury: {fin['treasury']:,} Gold", True, COLOR_GOLD), (34, 323))
    
        net_col = COLOR_TEXT_GREEN if fin['net_monthly'] >= 0 else COLOR_TEXT_RED
        net_sign = "+" if fin['net_monthly'] >= 0 else ""
        net_lbl = font_xs.render(f"Net: {net_sign}{fin['net_monthly']}g/m", True, net_col)
        screen.blit(net_lbl, (275 - net_lbl.get_width(), 323))
    
        screen.blit(font_xs.render(f"Income: +{fin['total_income']}g/m", True, (160, 225, 180)), (34, 342))
        exp_lbl = font_xs.render(f"Expense: -{fin['total_expense']}g/m", True, (255, 140, 140))
        screen.blit(exp_lbl, (275 - exp_lbl.get_width(), 342))
    
        # 2. Sub-tab navigation: [ ▲ INCOME (+XXg) ] and [ ▼ EXPENSES (-XXg) ]
        if not hasattr(state, "economy_subtab") or state.economy_subtab not in ("income", "expense"):
            state.economy_subtab = "income"
    
        tab_inc = pygame.Rect(content_x, 370, 193, 26)
        tab_exp = pygame.Rect(content_x + 203, 370, 193, 26)
    
        is_inc_active = (state.economy_subtab == "income")
        is_exp_active = (state.economy_subtab == "expense")
    
        is_hov_inc = tab_inc.collidepoint(mouse_pos)
        is_hov_exp = tab_exp.collidepoint(mouse_pos)
    
        pygame.draw.rect(screen, (40, 70, 50) if is_inc_active else ((45, 52, 65) if is_hov_inc else (32, 38, 48)), tab_inc, border_radius=4)
        pygame.draw.rect(screen, COLOR_TEXT_GREEN if is_inc_active else COLOR_PANEL_BORDER, tab_inc, 1, border_radius=4)
        lbl_inc_txt = font_xs.render(f"▲ INCOME (+{fin['total_income']}g)", True, COLOR_TEXT_GREEN if is_inc_active else (200, 220, 240))
        screen.blit(lbl_inc_txt, (tab_inc.x + (tab_inc.w - lbl_inc_txt.get_width()) // 2, 374))
    
        pygame.draw.rect(screen, (75, 40, 40) if is_exp_active else ((45, 52, 65) if is_hov_exp else (32, 38, 48)), tab_exp, border_radius=4)
        pygame.draw.rect(screen, COLOR_TEXT_RED if is_exp_active else COLOR_PANEL_BORDER, tab_exp, 1, border_radius=4)
        lbl_exp_txt = font_xs.render(f"▼ EXPENSES (-{fin['total_expense']}g)", True, COLOR_TEXT_RED if is_exp_active else (200, 220, 240))
        screen.blit(lbl_exp_txt, (tab_exp.x + (tab_exp.w - lbl_exp_txt.get_width()) // 2, 374))
    
        if mouse_clicked and is_hov_inc and not is_inc_active:
            state.economy_subtab = "income"
            state.economy_vassal_page = 0
        elif mouse_clicked and is_hov_exp and not is_exp_active:
            state.economy_subtab = "expense"
            state.economy_vassal_page = 0
    
        if is_inc_active:
            # -------------------------------------------------------------
            # INCOME BREAKDOWN
            # -------------------------------------------------------------
            # 1. Provincial Land Tax & Customs Card (y = 400, h = 92)
            card_p = pygame.Rect(content_x, 400, content_w, 92)
            pygame.draw.rect(screen, (32, 38, 50), card_p, border_radius=5)
            pygame.draw.rect(screen, (80, 110, 150), card_p, 1, border_radius=5)
    
            screen.blit(font_xs.render("◆ Provincial Tax Income", True, COLOR_GOLD), (32, 404))
            p_tot_lbl = font_xs.render(f"+{fin['total_prov_tax']}g/m", True, COLOR_TEXT_GREEN)
            screen.blit(p_tot_lbl, (275 - p_tot_lbl.get_width(), 404))
    
            screen.blit(font_xs.render("Tolls & trade customs from royal provinces:", True, COLOR_TEXT_MUTED), (32, 420))
    
            # Show up to 6 provinces in 2 rows of 3
            r1_provs = fin['prov_incomes'][:3]
            r2_provs = fin['prov_incomes'][3:6]
    
            r1_str = " • ".join([f"{p['name']}: +{p['tax']}g" for p in r1_provs])
            screen.blit(font_xs.render(r1_str, True, (190, 225, 255)), (32, 440))
    
            if r2_provs:
                r2_str = " • ".join([f"{p['name']}: +{p['tax']}g" for p in r2_provs])
                screen.blit(font_xs.render(r2_str, True, (190, 225, 255)), (32, 458))
            else:
                screen.blit(font_xs.render("• Expand realm to collect more tolls", True, COLOR_TEXT_MUTED), (32, 458))
    
            screen.blit(font_xs.render("Tip: Upgrade towns to increase province wealth", True, (150, 180, 210)), (32, 474))
    
            # 2. Feudal Vassal Tithes Card (y = 498, h = 118)
            card_v = pygame.Rect(content_x, 498, content_w, 118)
            pygame.draw.rect(screen, (32, 38, 50), card_v, border_radius=5)
            pygame.draw.rect(screen, (80, 110, 150), card_v, 1, border_radius=5)
    
            screen.blit(font_xs.render("♚ Feudal Vassal Tithes", True, COLOR_GOLD), (32, 502))
            v_tot_lbl = font_xs.render(f"+{fmt_gold(fin['total_vassal_tax'])}g/m", True, COLOR_TEXT_GREEN)
            screen.blit(v_tot_lbl, (275 - v_tot_lbl.get_width(), 502))
    
            screen.blit(font_xs.render("Taxes levied from vassals under Realm Laws:", True, COLOR_TEXT_MUTED), (32, 518))
    
            # Vassals pagination (< 1/X >)
            v_tithes = fin['vassal_tithes']
            per_v_page = 3
            max_v_pages = max(1, (len(v_tithes) + per_v_page - 1) // per_v_page)
            state.economy_vassal_page = max(0, min(getattr(state, "economy_vassal_page", 0), max_v_pages - 1))
    
            btn_vp_prev = pygame.Rect(216, 501, 16, 16)
            btn_vp_next = pygame.Rect(256, 501, 16, 16)
            is_vpp_hov = btn_vp_prev.collidepoint(mouse_pos)
            is_vpn_hov = btn_vp_next.collidepoint(mouse_pos)
    
            screen.blit(font_xs.render("<", True, COLOR_TEXT_WHITE if state.economy_vassal_page > 0 else (70, 75, 85)), (220, 502))
            v_pg_lbl = font_xs.render(f"{state.economy_vassal_page + 1}/{max_v_pages}", True, COLOR_TEXT_MUTED)
            screen.blit(v_pg_lbl, (244 - v_pg_lbl.get_width() // 2, 502))
            screen.blit(font_xs.render(">", True, COLOR_TEXT_WHITE if state.economy_vassal_page < max_v_pages - 1 else (70, 75, 85)), (260, 502))
    
            if mouse_clicked and is_vpp_hov and state.economy_vassal_page > 0:
                state.economy_vassal_page -= 1
            elif mouse_clicked and is_vpn_hov and state.economy_vassal_page < max_v_pages - 1:
                state.economy_vassal_page += 1
    
            cur_v_slice = v_tithes[state.economy_vassal_page * per_v_page : (state.economy_vassal_page + 1) * per_v_page]
            vy_item = 536
            if cur_v_slice:
                for v_item in cur_v_slice:
                    v_short = v_item['name'].split()[1] if len(v_item['name'].split()) > 1 else v_item['name']
                    screen.blit(font_xs.render(f"• {v_short[:10]} ({v_item['prov']}):", True, (210, 220, 235)), (34, vy_item))
                    screen.blit(font_xs.render(f"{v_item['tax_rate']}% -> +{fmt_gold(v_item['tax_paid'])}g/m", True, COLOR_TEXT_GREEN), (170, vy_item))
                    vy_item += 18
            else:
                screen.blit(font_xs.render("• No landed vassals paying tithes yet", True, COLOR_TEXT_MUTED), (34, 545))
    
            screen.blit(font_xs.render("Adjust individual rates under [ ⚖ LAWS ] tab", True, COLOR_GOLD), (34, 596))
    
            # 3. Direct Crown Demesne Revenue Card (y = 622, h = 54)
            card_c = pygame.Rect(content_x, 622, content_w, 54)
            pygame.draw.rect(screen, (32, 38, 50), card_c, border_radius=5)
            pygame.draw.rect(screen, (80, 110, 150), card_c, 1, border_radius=5)
    
            screen.blit(font_xs.render("[Fort] Crown Demesne Rents", True, COLOR_GOLD), (32, 626))
            c_tot_lbl = font_xs.render(f"+{fin['total_crown_income']}g/m", True, COLOR_TEXT_GREEN)
            screen.blit(c_tot_lbl, (275 - c_tot_lbl.get_width(), 626))
    
            screen.blit(font_xs.render(f"Direct rents from {state.player['name']}'s royal seats:", True, COLOR_TEXT_MUTED), (32, 642))
            c_sample = fin['crown_holdings'][:2]
            if c_sample:
                c_str = " • ".join([f"{c['name'][:10]}: +{c['val']}g" for c in c_sample])
                screen.blit(font_xs.render(f"• {c_str}", True, (160, 225, 180)), (32, 658))
            else:
                screen.blit(font_xs.render("• Winchester: +3g  • Wilton: +3g", True, (160, 225, 180)), (32, 658))
    
        else:
            # -------------------------------------------------------------
            # EXPENSES BREAKDOWN
            # -------------------------------------------------------------
            # 1. Army Field Mobilization Upkeep Card (y = 400, h = 112)
            card_a = pygame.Rect(content_x, 400, content_w, 112)
            pygame.draw.rect(screen, (42, 34, 38), card_a, border_radius=5)
            pygame.draw.rect(screen, (150, 80, 80), card_a, 1, border_radius=5)
    
            screen.blit(font_xs.render("⚔ Army Field Upkeep", True, COLOR_GOLD), (32, 404))
            a_tot_lbl = font_xs.render(f"-{fin['total_army_upkeep']}g/m", True, COLOR_TEXT_RED)
            screen.blit(a_tot_lbl, (275 - a_tot_lbl.get_width(), 404))
    
            screen.blit(font_xs.render("Crown Troops: 1g/100m • Feudal Levies: FREE", True, COLOR_TEXT_MUTED), (32, 420))
    
            ay_item = 438
            if fin['army_expenses']:
                for a_exp in fin['army_expenses'][:3]:
                    nm = a_exp['name'][:14]
                    t_cnt = a_exp['troops']
                    cost = a_exp['cost']
                    if cost > 0:
                        c_cnt = a_exp.get('crown_troops', 0)
                        screen.blit(font_xs.render(f"• {nm} ({c_cnt}c/{t_cnt:,}m):", True, (230, 215, 215)), (34, ay_item))
                        screen.blit(font_xs.render(f"-{cost}g/m", True, COLOR_TEXT_RED), (220, ay_item))
                    else:
                        screen.blit(font_xs.render(f"• {nm} ({t_cnt:,}m):", True, (200, 225, 200)), (34, ay_item))
                        screen.blit(font_xs.render("0g (FREE)", True, COLOR_TEXT_GREEN), (210, ay_item))
                    ay_item += 18
            else:
                screen.blit(font_xs.render("• All levies garrisoned at home", True, (200, 230, 200)), (34, 444))
                screen.blit(font_xs.render("  (0 active field armies = 0g upkeep)", True, COLOR_TEXT_MUTED), (34, 462))
    
            # 2. Military Facilities & Barracks Upkeep Card (y = 518, h = 64)
            card_b = pygame.Rect(content_x, 518, content_w, 64)
            pygame.draw.rect(screen, (42, 34, 38), card_b, border_radius=5)
            pygame.draw.rect(screen, (150, 80, 80), card_b, 1, border_radius=5)
    
            screen.blit(font_xs.render("⚔ Forts & Barracks Maintenance", True, COLOR_GOLD), (32, 522))
            b_tot_lbl = font_xs.render(f"-{fin['total_facility_upkeep']}g/m", True, COLOR_TEXT_RED)
            screen.blit(b_tot_lbl, (275 - b_tot_lbl.get_width(), 522))
    
            screen.blit(font_xs.render("Drillmasters & garrison maintenance (1+Lv gold):", True, COLOR_TEXT_MUTED), (32, 538))
            if fin['barrack_expenses']:
                by_item = 556
                for b_exp in fin['barrack_expenses'][:2]:
                    screen.blit(font_xs.render(f"• {b_exp['name']} ({b_exp['prov']}):", True, (230, 215, 215)), (34, by_item))
                    screen.blit(font_xs.render(f"-{b_exp['cost']}g/m", True, COLOR_TEXT_RED), (225, by_item))
                    by_item += 16
            else:
                screen.blit(font_xs.render("• Standard wooden palisades (0g additional upkeep)", True, COLOR_TEXT_MUTED), (34, 556))

            # 3. Feudal Liege Suzerainty Tax Card (Dedicated Card when vassalized)
            has_tribute = (fin.get('total_tribute', 0) > 0)
            if has_tribute:
                card_t = pygame.Rect(content_x, 588, content_w, 64)
                pygame.draw.rect(screen, (46, 32, 36), card_t, border_radius=5)
                pygame.draw.rect(screen, (180, 75, 75), card_t, 1, border_radius=5)

                screen.blit(font_xs.render("♚ Feudal Liege Suzerainty Tax (20%)", True, COLOR_GOLD), (32, 592))
                t_tot_lbl = font_xs.render(f"-{fmt_gold(fin['total_tribute'])}g/m", True, COLOR_TEXT_RED)
                screen.blit(t_tot_lbl, (275 - t_tot_lbl.get_width(), 592))

                t_info = fin.get('tribute_expenses', [{}])[0]
                liege_name = t_info.get('liege', 'Overlord')
                screen.blit(font_xs.render(f"Mandatory tribute paid to Suzerain {liege_name}:", True, COLOR_TEXT_MUTED), (32, 608))
                screen.blit(font_xs.render(f"• 20% feudal tax on gross domain (+{fmt_gold(fin['total_income'])}g) -> -{fmt_gold(fin['total_tribute'])}g/m", True, (255, 190, 190)), (34, 626))

            # 4. Monthly Financial Statement Card
            cs_y = 658 if has_tribute else 590
            cs_h = 58 if has_tribute else 70
            card_s = pygame.Rect(content_x, cs_y, content_w, cs_h)
            pygame.draw.rect(screen, (32, 40, 52), card_s, border_radius=5)
            pygame.draw.rect(screen, COLOR_GOLD, card_s, 1, border_radius=5)
    
            screen.blit(font_xs.render("⚖ Monthly Financial Bottom Line", True, COLOR_GOLD), (32, cs_y + 4))
            screen.blit(font_xs.render(f"Gross Inflow: +{fmt_gold(fin['total_income'])}g / month", True, (160, 225, 180)), (34, cs_y + 20))
            screen.blit(font_xs.render(f"Gross Outflow: -{fmt_gold(fin['total_expense'])}g / month", True, (255, 140, 140)), (34, cs_y + 36))
            if not has_tribute:
                net_st_lbl = font_xs.render(f"Net Cash Flow: {net_sign}{fmt_gold(abs(fin['net_monthly']))}g / month", True, net_col)
                screen.blit(net_st_lbl, (34, cs_y + 52))

    elif state.left_tab == "diplomacy":
        # -------------------------------------------------------------
        # DIPLOMACY TAB: Foreign Relations & Truce / War Treaties
        # -------------------------------------------------------------
        screen.blit(font_md.render("Foreign Relations & Diplomacy", True, COLOR_GOLD), (content_x, 302))

        ai_targets = [("char_ironpeak", "Ironpeak Dominion"), ("char_sylvan", "Sylvandell Sovereignty")]
        curr_target = getattr(state, "active_diplomacy_target", "char_ironpeak")
        if curr_target not in [t[0] for t in ai_targets]:
            curr_target = "char_ironpeak"
            state.active_diplomacy_target = curr_target

        pill_w = (content_w - 6) // 2
        for idx, (t_id, t_title) in enumerate(ai_targets):
            p_rect = pygame.Rect(content_x + idx * (pill_w + 6), 326, pill_w, 24)
            is_sel = (t_id == curr_target)
            is_hov = p_rect.collidepoint(mouse_pos)
            bg = (55, 65, 85) if is_sel else ((40, 48, 62) if is_hov else (28, 34, 45))
            bd = COLOR_GOLD if is_sel else ((100, 120, 150) if is_hov else (50, 60, 75))
            pygame.draw.rect(screen, bg, p_rect, border_radius=4)
            pygame.draw.rect(screen, bd, p_rect, 1, border_radius=4)
            t_lbl = font_xs.render(t_title.split()[0], True, COLOR_GOLD if is_sel else COLOR_TEXT_MUTED)
            screen.blit(t_lbl, (p_rect.x + (p_rect.w - t_lbl.get_width()) // 2, p_rect.y + 4))
            if mouse_clicked and is_hov:
                state.active_diplomacy_target = t_id

        target_id = curr_target
        target_char = CHARACTERS.get(target_id, {})
        t_name = target_char.get("name", "Foreign Sovereign")
        t_realm = target_char.get("realm", "Foreign Realm")
        t_martial = target_char.get("martial", 16)
        t_age = target_char.get("age", 35)
        f_prov_count = sum(1 for p in PROVINCES.values() if p.get("owner") == target_id)
        f_troops = sum(a.troops for a in state.armies if a.owner == target_id)

        # 1. Foreign Ruler Card
        d_card = pygame.Rect(content_x, 356, content_w, 88)
        pygame.draw.rect(screen, (32, 38, 50), d_card, border_radius=6)
        pygame.draw.rect(screen, (70, 85, 110), d_card, 1, border_radius=6)

        f_p_img = portrait_cache.get(target_id)
        if f_p_img:
            screen.blit(f_p_img, (content_x + 8, 362))
            pygame.draw.rect(screen, COLOR_GOLD, (content_x + 8, 362, 64, 64), 1)
        f_c_img = coa_cache.get(target_id)
        if f_c_img:
            screen.blit(f_c_img, (content_x + 52, 400))

        screen.blit(font_sm.render(t_name, True, COLOR_GOLD), (content_x + 82, 360))
        screen.blit(font_xs.render(f"{t_realm} ({f_prov_count} Prov)", True, (200, 220, 245)), (content_x + 82, 380))
        screen.blit(font_xs.render(f"Martial: {t_martial}  •  Age: {t_age}  •  Field: {f_troops:,} men", True, COLOR_TEXT_MUTED), (content_x + 82, 398))

        # Status Badge
        is_war = state.are_hostile(state.player_id, target_id)
        st_rect = pygame.Rect(content_x + 82, 418, 160, 20)
        st_bg = (145, 30, 30) if is_war else (30, 100, 60)
        st_txt = "⚔ STATUS: AT WAR" if is_war else "🕊 STATUS: AT PEACE"
        pygame.draw.rect(screen, st_bg, st_rect, border_radius=3)
        st_lbl = font_xs.render(st_txt, True, (255, 255, 255))
        screen.blit(st_lbl, (st_rect.x + (st_rect.w - st_lbl.get_width()) // 2, st_rect.y + 2))

        # 2. Primary Functional Action Button (Declare War / Offer Peace)
        act_y = 450
        btn_act = pygame.Rect(content_x, act_y, content_w, 34)
        b_hov = btn_act.collidepoint(mouse_pos)

        if is_war:
            pygame.draw.rect(screen, (30, 110, 70) if b_hov else (20, 80, 50), btn_act, border_radius=4)
            pygame.draw.rect(screen, (80, 220, 140), btn_act, 1, border_radius=4)
            act_lbl = font_sm.render("🕊 OFFER PEACE (Conclude Truce)", True, (240, 255, 240))
            screen.blit(act_lbl, (btn_act.x + (btn_act.w - act_lbl.get_width()) // 2, act_y + 7))
            if mouse_clicked and b_hov:
                state.offer_peace(state.player_id, target_id)
        else:
            pygame.draw.rect(screen, (135, 30, 30) if b_hov else (95, 20, 20), btn_act, border_radius=4)
            pygame.draw.rect(screen, (240, 80, 80), btn_act, 1, border_radius=4)
            act_lbl = font_sm.render(f"⚔ DECLARE WAR ({t_realm.split()[0]})", True, (255, 235, 235))
            screen.blit(act_lbl, (btn_act.x + (btn_act.w - act_lbl.get_width()) // 2, act_y + 7))
            if mouse_clicked and b_hov:
                state.declare_war(state.player_id, target_id, reason="Territorial Expansion")

        # 3. Frontier Intelligence & Standoff Status (SIAGA)
        foreign_at_border = []
        player_provs = [pid for pid, p in PROVINCES.items() if p.get('owner') == state.player_id]
        for a in state.armies:
            if a.owner != state.player_id and a.troops > 0:
                for pp in player_provs:
                    if a.province in ADJACENCY.get(pp, []):
                        foreign_at_border.append(a)
                        break

        info_y = act_y + 46
        info_rect = pygame.Rect(content_x, info_y, content_w, 42)
        if foreign_at_border:
            pygame.draw.rect(screen, (60, 40, 15), info_rect, border_radius=4)
            pygame.draw.rect(screen, (220, 160, 40), info_rect, 1, border_radius=4)
            screen.blit(font_xs.render("⚠ FRONTIER ALERT (SIAGA): Border Standoff Active", True, (255, 215, 80)), (content_x + 8, info_y + 4))
            screen.blit(font_xs.render(f"{len(foreign_at_border)} foreign host(s) vigilant on marches. Disbanding will trigger stand-down.", True, (220, 210, 190)), (content_x + 8, info_y + 22))
        else:
            pygame.draw.rect(screen, (20, 35, 45), info_rect, border_radius=4)
            pygame.draw.rect(screen, (60, 110, 160), info_rect, 1, border_radius=4)
            screen.blit(font_xs.render("🕊 FRONTIER STATUS: Quiet & Peaceful", True, (160, 220, 255)), (content_x + 8, info_y + 4))
            screen.blit(font_xs.render("No foreign forces massing on border marches.", True, COLOR_TEXT_MUTED), (content_x + 8, info_y + 22))

        # 4. Feudal Diplomatic Actions (Inactive Preview as requested)
        screen.blit(font_sm.render("Feudal Diplomatic Actions (Pending)", True, (185, 200, 220)), (content_x, info_y + 52))

        dip_actions = [
            ("🤝 Form Non-Aggression Pact", "Guarantees no attacks for 10 years", "Locked"),
            ("💍 Arrange Dynastic Betrothal", "Seal peace through royal marriage", "Locked"),
            ("💰 Send Diplomatic Gift (100g)", "Improve foreign relations & opinion", "Locked"),
            ("🛡 Sign Defensive Alliance", "Mutual defense against external raids", "Locked"),
            ("👑 Demand Danegeld / Feudal Tribute", "Extract monthly gold under threat of war", "Locked"),
            ("🕵 Fabricate Border Shire Claim", "Dispatch Chancellor to forge de jure rights", "Locked"),
            ("📜 Demand Royal Hostage Exchange", "Exchange noble heirs to guarantee truce", "Locked"),
        ]

        opt_y = info_y + 76
        for title, desc, tag in dip_actions:
            opt_rect = pygame.Rect(content_x, opt_y, content_w, 40)
            is_o_hov = opt_rect.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (34, 38, 48) if is_o_hov else (26, 30, 40), opt_rect, border_radius=4)
            pygame.draw.rect(screen, (65, 75, 95) if is_o_hov else (45, 52, 68), opt_rect, 1, border_radius=4)

            t_col = (200, 210, 225) if is_o_hov else (145, 155, 170)
            screen.blit(font_xs.render(title, True, t_col), (content_x + 8, opt_y + 5))
            screen.blit(font_xs.render(desc, True, (115, 125, 140)), (content_x + 8, opt_y + 22))

            tag_rect = pygame.Rect(content_x + content_w - 62, opt_y + 11, 54, 18)
            pygame.draw.rect(screen, (40, 45, 58), tag_rect, border_radius=3)
            pygame.draw.rect(screen, (75, 82, 98), tag_rect, 1, border_radius=3)
            tag_lbl = font_xs.render(tag, True, (140, 150, 168))
            screen.blit(tag_lbl, (tag_rect.x + (tag_rect.w - tag_lbl.get_width()) // 2, tag_rect.y + 1))

            opt_y += 46
    
