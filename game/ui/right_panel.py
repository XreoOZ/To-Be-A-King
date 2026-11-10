"""
Right Panel Component (Selected Province, Commands, Overview, Buildings, Vassals, Fiefs)
"""
import random
import pygame
from game.config import (
    WINDOW_HEIGHT, PANEL_R_X, PANEL_R_W, PANEL_Y, PANEL_H, COLOR_PANEL_BG, COLOR_PANEL_BORDER, COLOR_GOLD,
    COLOR_TEXT_WHITE, COLOR_TEXT_MUTED, COLOR_TEXT_RED, COLOR_TEXT_GREEN,
    COLOR_BUTTON_NORMAL, COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE,
    LEVY_RAISE_COOLDOWN_DAYS, BASE_TILE_W, VIEWPORT_CENTER_X
)
from game.data.characters import CHARACTERS
from game.data.provinces import PROVINCES
from game.data.buildings import BUILDING_SPECS, BARRACK_UPGRADE_COSTS, get_barrack_stats
from game.core.map import CELL_TO_PROV
from game.core.assets import load_image, portrait_cache
from game.core.state import carve_new_fief
from game.systems.economy import (
    get_province_holdings, get_vassal_landed_status, sync_province_holdings_stats, fmt_gold
)
from game.systems.military import is_province_contested

def render_right_panel(screen, state, mouse_pos, mouse_clicked, fonts, coa_cache, icons=None, box_start=None, box_end=None):
    font_xs = fonts["xs"]
    font_sm = fonts["sm"]
    font_md = fonts["md"]
    font_lg = fonts["lg"]

    cell_to_prov = CELL_TO_PROV

    icon_gold = icons.get("gold") if icons else None
    icon_troops = icons.get("troops") if icons else None

    # 4. RIGHT PANEL: SELECTED PROVINCE & ARMY COMMANDS
    # ---------------------------------------------------------
    content_x = PANEL_R_X + 12
    content_w = PANEL_R_W - 24
    right_panel = pygame.Rect(PANEL_R_X, PANEL_Y, PANEL_R_W, PANEL_H)
    pygame.draw.rect(screen, COLOR_PANEL_BG, right_panel, border_radius=6)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, right_panel, 2, border_radius=6)
    
    sel_prov = PROVINCES.get(state.selected_province)
    sel_army = state.get_selected_army()
    
    # If a city or holding is specifically selected, display Holding Inspector Card!
    if state.selected_settlement and state.selected_settlement in state.settlements:
        s_coord = state.selected_settlement
        s_data = state.settlements[s_coord]
        p_parent = PROVINCES.get(s_data["province"])
        
        h_type = s_data.get("type", "city")
        if h_type == "town":
            h_type = "city"
    
        c_head = font_lg.render(s_data["name"], True, COLOR_GOLD)
        screen.blit(c_head, (content_x, 80))
        
        p_cap = s_data['province'].replace("_", " ").title()
        if h_type == "city":
            sub_c = font_sm.render(f"Holding Type: [City] Commercial City ({p_cap})", True, COLOR_TEXT_WHITE)
        elif h_type == "fort":
            sub_c = font_sm.render(f"Holding Type: [Fort] Stone Fortress ({p_cap})", True, COLOR_TEXT_WHITE)
        else:
            lvl = s_data.get("level", 0)
            sub_c = font_sm.render(f"Holding Type: ⚔ Military Barracks Lvl {lvl} ({p_cap})", True, COLOR_TEXT_WHITE)
        screen.blit(sub_c, (content_x, 110))
        
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (content_x, 135), (content_x + content_w, 135), 1)
        screen.blit(font_md.render("Holding Overview", True, COLOR_GOLD), (content_x, 145))
        h_matching_tiles = [coord for coord, s in state.settlements.items() if s.get("name") == s_data["name"] and s.get("province") == s_data["province"]]
        t_loc_str = ", ".join(f"({c},{r})" for c, r in h_matching_tiles)
        screen.blit(font_sm.render(f"Location: {t_loc_str} ({len(h_matching_tiles)} Tiles)", True, COLOR_TEXT_MUTED), (content_x, 172))
        lord_str = s_data.get('lord', 'Crown Demesne').replace("Royal Demesne", "Crown Demesne")
        screen.blit(font_sm.render(f"Ruling Lord: {lord_str}", True, COLOR_GOLD), (content_x, 194))
    
        cur_y = 216
        if h_type == "city":
            screen.blit(font_sm.render("Economic Income: +3 Gold / month", True, COLOR_TEXT_GREEN), (content_x, cur_y))
            screen.blit(font_sm.render("Recruitment Rate: +10 Men / month", True, COLOR_TEXT_GREEN), (content_x, cur_y + 22))
            screen.blit(font_sm.render("Local Garrison: 100 Defenders", True, COLOR_TEXT_WHITE), (content_x, cur_y + 44))
            screen.blit(font_xs.render("• Generates gold and recruits to supply and replenish realm fyrd.", True, COLOR_TEXT_MUTED), (content_x, cur_y + 66))
            cur_y += 90
    
        elif h_type == "fort":
            screen.blit(font_sm.render("Economic Income: +1 Gold / month (Tolls)", True, COLOR_TEXT_GREEN), (content_x, cur_y))
            screen.blit(font_sm.render("Recruitment Rate: +10 Men / month", True, COLOR_TEXT_GREEN), (content_x, cur_y + 22))
            screen.blit(font_sm.render("Local Garrison: 300 Defenders", True, COLOR_TEXT_WHITE), (content_x, cur_y + 44))
            screen.blit(font_sm.render("Fortification: High Defense (Twin Turrets)", True, (160, 210, 255)), (content_x, cur_y + 66))
            screen.blit(font_xs.render("• Shields the province and trains +10 garrison defenders monthly.", True, COLOR_TEXT_MUTED), (content_x, cur_y + 88))
            cur_y += 112
    
        else: # Barracks
            lvl = s_data.get("level", 0)
            bstats = get_barrack_stats(lvl)
            screen.blit(font_sm.render(f"Recruitment Rate: +{bstats['recruits']} Men / month", True, COLOR_TEXT_GREEN), (content_x, cur_y))
            screen.blit(font_sm.render(f"Holding Upkeep: -{bstats['upkeep']} Gold / month", True, (255, 120, 120)), (content_x, cur_y + 22))
            screen.blit(font_sm.render(f"Garrison Capacity: {bstats['garrison']} / 500 Men", True, COLOR_TEXT_WHITE), (content_x, cur_y + 44))
            cur_y += 70
    
            # Upgrade & Downgrade buttons for Barracks
            is_crown_barrack = s_data.get("is_crown_demesne", False)
            if is_crown_barrack and p_parent and p_parent["owner"] == state.player_id:
                # Upgrade button
                if lvl < 5:
                    up_cost = BARRACK_UPGRADE_COSTS.get(lvl, 500)
                    can_afford = state.player["gold"] >= up_cost
                    up_btn = pygame.Rect(content_x, cur_y, content_w, 32)
                    up_hov = up_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (35, 95, 50) if (up_hov and can_afford) else ((25, 65, 35) if can_afford else (45, 45, 50)), up_btn, border_radius=4)
                    pygame.draw.rect(screen, COLOR_TEXT_GREEN if can_afford else (90, 90, 95), up_btn, 1, border_radius=4)
                    up_txt = font_xs.render(f"▲ UPGRADE TO LEVEL {lvl+1} ({up_cost}g  •  +5 Recruits/m)", True, COLOR_TEXT_WHITE if can_afford else COLOR_TEXT_MUTED)
                    screen.blit(up_txt, (up_btn.x + (up_btn.w - up_txt.get_width()) // 2, cur_y + 8))
                    if mouse_clicked and up_hov and can_afford:
                        state.player["gold"] -= up_cost
                        new_lvl = lvl + 1
                        for tc in h_matching_tiles:
                            state.settlements[tc]["level"] = new_lvl
                        sync_province_holdings_stats(state, s_data["province"])
                        state.logs.append(f"Upgraded {s_data['name']} to Level {new_lvl} (-{up_cost}g)! Now generates +{10 + new_lvl * 5} recruits/mo.")
                    cur_y += 38
    
                # Downgrade button
                if lvl > 0:
                    down_btn = pygame.Rect(content_x, cur_y, content_w, 30)
                    down_hov = down_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (90, 45, 30) if down_hov else (65, 32, 22), down_btn, border_radius=4)
                    pygame.draw.rect(screen, (220, 110, 60), down_btn, 1, border_radius=4)
                    down_txt = font_xs.render(f"▼ DEMOBILIZE / DOWNGRADE (Save 1g/m Upkeep)", True, (255, 210, 190))
                    screen.blit(down_txt, (down_btn.x + (down_btn.w - down_txt.get_width()) // 2, cur_y + 7))
                    if mouse_clicked and down_hov:
                        new_lvl = lvl - 1
                        for tc in h_matching_tiles:
                            state.settlements[tc]["level"] = new_lvl
                        sync_province_holdings_stats(state, s_data["province"])
                        state.logs.append(f"Downgraded {s_data['name']} to Level {new_lvl}. Saved 1 Gold/month upkeep.")
                    cur_y += 36
        
        if s_data.get("vassal_id"):
            v_btn = pygame.Rect(content_x, cur_y + 8, content_w, 34)
            b_v_hov = v_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (40, 75, 110) if b_v_hov else (30, 55, 85), v_btn, border_radius=6)
            pygame.draw.rect(screen, (100, 180, 255), v_btn, 1, border_radius=6)
            v_lbl = font_xs.render("♚ VIEW VASSAL PROFILE & DOSSIER", True, COLOR_TEXT_WHITE)
            screen.blit(v_lbl, (v_btn.x + (v_btn.w - v_lbl.get_width()) // 2, cur_y + 11))
            if mouse_clicked and b_v_hov:
                v_list = state.vassals.get(s_data["province"], [])
                matching_v = next((v for v in v_list if v.get("id") == s_data["vassal_id"] or v.get("name") == s_data["lord"]), None)
                if matching_v:
                    state.inspecting_vassal = {"province": s_data["province"], "vassal": matching_v}
                    state.logs.append(f"Opened royal dossier for vassal {matching_v['name']}.")
            cls_y = cur_y + 48
        else:
            cls_y = cur_y + 8
    
        # Close/Back button
        cls_btn = pygame.Rect(content_x, cls_y, content_w, 34)
        b_c_hov = cls_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, COLOR_BUTTON_HOVER if b_c_hov else COLOR_BUTTON_NORMAL, cls_btn, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, cls_btn, 1, border_radius=6)
        b_lbl = font_sm.render("← Back to Province View", True, COLOR_TEXT_WHITE)
        screen.blit(b_lbl, (cls_btn.x + (cls_btn.w - b_lbl.get_width()) // 2, cls_y + 8))
        if mouse_clicked and b_c_hov:
            state.selected_settlement = None
            state.selected_vassal_idx = None
    
    # If an army is selected, show Army Command Card!
    elif sel_army and sel_army.owner == state.player_id:
        # Header
        a_title = font_lg.render(sel_army.name, True, COLOR_GOLD)
        screen.blit(a_title, (content_x, 80))
        
        sub_title = font_sm.render(f"Strength: {sel_army.troops:,} Men  •  Owner: Wessex", True, COLOR_TEXT_WHITE)
        screen.blit(sub_title, (content_x, 110))
    
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (content_x, 135), (content_x + content_w, 135), 1)
    
        # Location & Status
        screen.blit(font_md.render("Host Status", True, COLOR_GOLD), (content_x, 145))
        screen.blit(font_sm.render(f"Current Location: {PROVINCES[sel_army.province]['name']}", True, COLOR_TEXT_WHITE), (content_x, 175))
        
        if sel_army.in_battle:
            screen.blit(font_md.render("STATUS: ⚔ IN PITCHED BATTLE!", True, COLOR_TEXT_RED), (content_x, 202))
        elif sel_army.courier_en_route:
            screen.blit(font_md.render(f"STATUS: ROYAL COURIER EN ROUTE ({sel_army.courier_days_left}d left)", True, (255, 215, 80)), (content_x, 202))
            dest_p = PROVINCES[sel_army.province]["name"].split()[0]
            cap_p = "Winchester" if sel_army.owner == state.player_id else "Jorvik"
            screen.blit(font_xs.render(f"Decree riding from {cap_p} to {dest_p}.", True, COLOR_TEXT_WHITE), (content_x, 222))
        elif sel_army.is_mustering:
            screen.blit(font_md.render(f"STATUS: MUSTERING ({sel_army.muster_days}d left)", True, COLOR_GOLD), (content_x, 202))
        elif sel_army.is_demobilizing:
            home_p = PROVINCES[sel_army.flag_origin]["name"].split()[0]
            screen.blit(font_md.render(f"STATUS: ◆ Returning Home to {home_p}", True, (140, 200, 255)), (content_x, 202))
        elif sel_army.is_sieging:
            t_lbl = sel_army.siege_target_name or 'Holding'
            screen.blit(font_md.render(f"STATUS: [Fort] Besieging {t_lbl} ({sel_army.siege_progress}%)", True, COLOR_GOLD), (content_x, 202))
        elif sel_army.is_moving:
            screen.blit(font_sm.render(f"Marching to: {PROVINCES[sel_army.next_province]['name']} ({int(sel_army.move_progress)}%)", True, COLOR_TEXT_WHITE), (content_x, 202))
        else:
            screen.blit(font_sm.render("Status: Standing Ready", True, COLOR_TEXT_GREEN), (content_x, 202))
    
        # March Instruction Box
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (content_x, 235), (content_x + content_w, 235), 1)
        screen.blit(font_md.render("March Orders", True, COLOR_GOLD), (content_x, 245))
        screen.blit(font_sm.render("Click any province on the map to", True, COLOR_TEXT_MUTED), (content_x, 275))
        screen.blit(font_sm.render("order this army to march there!", True, COLOR_TEXT_MUTED), (content_x, 295))
        screen.blit(font_xs.render("• March into enemy land to begin SIEGE.", True, COLOR_GOLD), (content_x, 320))
        screen.blit(font_xs.render("• March into Viking army to CLASH.", True, COLOR_TEXT_RED), (content_x, 340))
    
        # Action Buttons for Army
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (content_x, 365), (content_x + content_w, 365), 1)
        
        # Merge button if other armies in same province
        other_armies = [a for a in state.armies if a.province == sel_army.province and a.owner == state.player_id and a.id != sel_army.id]
        if other_armies:
            merge_btn = pygame.Rect(content_x, 385, content_w, 40)
            b_m_hover = merge_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (40, 90, 140) if b_m_hover else (30, 65, 105), merge_btn, border_radius=6)
            pygame.draw.rect(screen, (80, 160, 240), merge_btn, 1, border_radius=6)
            m_lbl = font_md.render("MERGE WITH OTHER HOSTS", True, COLOR_TEXT_WHITE)
            screen.blit(m_lbl, (merge_btn.x + (merge_btn.w - m_lbl.get_width()) // 2, 394))
            if mouse_clicked and b_m_hover:
                state.merge_armies_in_province(sel_army.province, state.player_id)
    
        # Disband / Cancel Muster / Cancel Summons Button
        if sel_army.is_mustering or sel_army.courier_en_route:
            dis_btn = pygame.Rect(content_x, 435, content_w, 40)
            b_d_hover = dis_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (90, 40, 40) if b_d_hover else (70, 30, 30), dis_btn, border_radius=6)
            pygame.draw.rect(screen, (240, 90, 90), dis_btn, 1, border_radius=6)
            btn_txt = "CANCEL SUMMONS (Recall Courier)" if sel_army.courier_en_route else "CANCEL MUSTER (Refund Men)"
            b_lbl = font_md.render(btn_txt, True, (255, 220, 220))
            screen.blit(b_lbl, (dis_btn.x + (dis_btn.w - b_lbl.get_width()) // 2, 444))
            if mouse_clicked and b_d_hover:
                state.disband_army(sel_army)
        elif sel_army.is_demobilizing:
            dis_btn = pygame.Rect(content_x, 435, content_w, 40)
            b_d_hover = dis_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (40, 90, 140) if b_d_hover else (30, 65, 105), dis_btn, border_radius=6)
            pygame.draw.rect(screen, (80, 160, 240), dis_btn, 1, border_radius=6)
            c_lbl = font_md.render("CANCEL DISBAND (Resume War)", True, COLOR_TEXT_WHITE)
            screen.blit(c_lbl, (dis_btn.x + (dis_btn.w - c_lbl.get_width()) // 2, 444))
            if mouse_clicked and b_d_hover:
                sel_army.is_demobilizing = False
                sel_army.path = []
                state.logs.append(f"{sel_army.name} cancelled return march and is standing ready.")
        else:
            dis_btn = pygame.Rect(content_x, 435, content_w, 40)
            b_d_hover = dis_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (80, 35, 35) if b_d_hover else (60, 28, 28), dis_btn, border_radius=6)
            pygame.draw.rect(screen, COLOR_TEXT_RED, dis_btn, 1, border_radius=6)
            d_lbl = font_md.render("ORDER DISBAND (Return Home)", True, (255, 220, 220))
            screen.blit(d_lbl, (dis_btn.x + (dis_btn.w - d_lbl.get_width()) // 2, 444))
            if mouse_clicked and b_d_hover:
                state.disband_army(sel_army)
    
        # Deselect Army Button
        desel_btn = pygame.Rect(content_x, 485, content_w, 36)
        b_ds_hover = desel_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, COLOR_BUTTON_HOVER if b_ds_hover else COLOR_BUTTON_NORMAL, desel_btn, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, desel_btn, 1, border_radius=6)
        ds_lbl = font_sm.render("Deselect Army (View Province)", True, COLOR_TEXT_MUTED)
        screen.blit(ds_lbl, (desel_btn.x + (desel_btn.w - ds_lbl.get_width()) // 2, 493))
        if mouse_clicked and b_ds_hover:
            state.selected_army_id = None
    
    elif sel_prov:
        owner_char = CHARACTERS.get(sel_prov["owner"], CHARACTERS["char_alfred"])
        is_player_owned = (sel_prov["owner"] == state.player_id)
    
        # Province Header
        p_title = font_lg.render(sel_prov["name"], True, COLOR_GOLD)
        screen.blit(p_title, (content_x, 75))
        sub_title = font_xs.render(f"Culture: {sel_prov['culture']}  •  Faith: {sel_prov['religion']}", True, COLOR_TEXT_MUTED)
        screen.blit(sub_title, (content_x, 102))

        # Realm Capital Status Badge / Change Capital Button
        active_player_cap = state.get_realm_capital(state.player_id)
        active_enemy_cap = state.get_realm_capital(state.enemy_id)
        
        if state.selected_province == active_player_cap:
            cap_rect = pygame.Rect(content_x + content_w - 150, 73, 150, 26)
            pygame.draw.rect(screen, (50, 42, 20), cap_rect, border_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD, cap_rect, 1, border_radius=4)
            lbl = font_xs.render("★ REALM CAPITAL", True, COLOR_GOLD)
            screen.blit(lbl, (cap_rect.x + (cap_rect.w - lbl.get_width()) // 2, cap_rect.y + 5))
        elif is_player_owned:
            cap_btn = pygame.Rect(content_x + content_w - 150, 73, 150, 26)
            cb_hov = cap_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (45, 65, 95) if cb_hov else (30, 42, 60), cap_btn, border_radius=4)
            pygame.draw.rect(screen, (100, 180, 255) if cb_hov else COLOR_PANEL_BORDER, cap_btn, 1, border_radius=4)
            lbl = font_xs.render("★ MAKE CAPITAL", True, (220, 240, 255) if cb_hov else COLOR_TEXT_WHITE)
            screen.blit(lbl, (cap_btn.x + (cap_btn.w - lbl.get_width()) // 2, cap_btn.y + 5))
            if mouse_clicked and cb_hov:
                state.set_player_capital(state.selected_province)
        elif state.selected_province == active_enemy_cap:
            cap_rect = pygame.Rect(content_x + content_w - 150, 73, 150, 26)
            pygame.draw.rect(screen, (55, 25, 25), cap_rect, border_radius=4)
            pygame.draw.rect(screen, (220, 80, 80), cap_rect, 1, border_radius=4)
            lbl = font_xs.render("★ ENEMY CAPITAL", True, (255, 160, 160))
            screen.blit(lbl, (cap_rect.x + (cap_rect.w - lbl.get_width()) // 2, cap_rect.y + 5))
    
        # CLEAN TAB NAVIGATION BAR (Province Overview | Buildings | Vassals | Fiefs)
        tabs = [("overview", "Overview"), ("buildings", "Buildings"), ("vassals", "Vassals"), ("fiefs", "Fiefs")]
        tab_w = (content_w - 12) // 4
        for t_i, (t_key, t_label) in enumerate(tabs):
            t_rect = pygame.Rect(content_x + t_i * (tab_w + 4), 120, tab_w, 30)
            is_t_active = (state.right_tab == t_key)
            is_t_hov = t_rect.collidepoint(mouse_pos)
            t_bg = (60, 75, 100) if is_t_active else ((45, 52, 68) if is_t_hov else (32, 36, 48))
            pygame.draw.rect(screen, t_bg, t_rect, border_top_left_radius=4, border_top_right_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD if is_t_active else COLOR_PANEL_BORDER, t_rect, 1, border_top_left_radius=4, border_top_right_radius=4)
            lbl_s = font_xs.render(t_label, True, COLOR_GOLD if is_t_active else COLOR_TEXT_WHITE)
            screen.blit(lbl_s, (t_rect.x + (t_rect.w - lbl_s.get_width()) // 2, t_rect.y + 7))
            if mouse_clicked and is_t_hov:
                state.right_tab = t_key
                state.build_mode = False
    
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (content_x, 150), (content_x + content_w, 150), 2)
    
        # -------------------------------------------------------------
        # TAB 1: OVERVIEW
        # -------------------------------------------------------------
        if state.right_tab == "overview":
            # Owner Info (Clickable Sovereign Ruler Card)
            r_card = pygame.Rect(content_x, 156, content_w, 58)
            is_rc_hov = r_card.collidepoint(mouse_pos)
            if is_rc_hov:
                pygame.draw.rect(screen, (48, 55, 75) if is_player_owned else (65, 36, 40), r_card, border_radius=6)
                pygame.draw.rect(screen, COLOR_GOLD if is_player_owned else (240, 100, 100), r_card, 1, border_radius=6)
    
            owner_p = portrait_cache.get(sel_prov["owner"])
            if owner_p:
                mini_p = pygame.transform.smoothscale(owner_p, (46, 46))
                screen.blit(mini_p, (content_x + 8, 162))
                pygame.draw.rect(screen, COLOR_GOLD if is_player_owned else (220, 80, 80), (content_x + 8, 162, 46, 46), 1)
            owner_c = coa_cache.get(sel_prov["owner"])
            if owner_c:
                screen.blit(owner_c, (content_x + 60, 162))
    
            screen.blit(font_md.render(owner_char["name"], True, COLOR_GOLD if is_player_owned else COLOR_TEXT_RED), (content_x + 100, 162))
            screen.blit(font_xs.render(owner_char["title"], True, COLOR_TEXT_WHITE), (content_x + 100, 184))
            
            # Click to inspect hint
            hint_str = "♚ Click to Inspect Sovereign Dossier"
            hint_col = (255, 220, 130) if is_player_owned else (255, 180, 180)
            screen.blit(font_xs.render(hint_str, True, hint_col), (content_x + 100, 200))
    
            if mouse_clicked and is_rc_hov:
                state.inspecting_ruler = sel_prov["owner"]
                state.logs.append(f"Opened royal dossier for Sovereign {owner_char['name']}.")
    
            # Province Stats Box
            s_box = pygame.Rect(content_x, 220, content_w, 80)
            pygame.draw.rect(screen, (35, 40, 54), s_box, border_radius=6)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, s_box, 1, border_radius=6)
            if icon_gold:
                screen.blit(icon_gold, (content_x + 14, 230))
            screen.blit(font_sm.render(f"Monthly Tax Revenue: +{sel_prov['tax']} Gold", True, COLOR_TEXT_WHITE), (content_x + 46, 233))
            if icon_troops:
                screen.blit(icon_troops, (content_x + 14, 265))
            screen.blit(font_sm.render(f"Levies Available: {sel_prov['levies_current']} / {sel_prov['levies_max']}", True, COLOR_TEXT_WHITE), (content_x + 46, 268))
    
            if is_player_owned:
                # Military Orders
                screen.blit(font_md.render("Military Orders", True, COLOR_GOLD), (content_x, 320))
                p_cd = sel_prov.get("raise_cooldown_days", 0)
                is_p_cd = (p_cd > 0)
                is_in_field = state.is_province_levy_in_field(state.selected_province, sel_prov["owner"])
                
                raise_btn = pygame.Rect(content_x, 345, content_w, 40)
                b_r_hov = raise_btn.collidepoint(mouse_pos) and not is_p_cd and not is_in_field
                
                if is_in_field:
                    pygame.draw.rect(screen, (38, 42, 50), raise_btn, border_radius=6)
                    pygame.draw.rect(screen, (60, 65, 78), raise_btn, 1, border_radius=6)
                    p_short = sel_prov["name"].split()[0]
                    f_lbl = font_sm.render(f"LEVIES IN FIELD ({p_short} Deployed)", True, (160, 170, 185))
                    screen.blit(f_lbl, (raise_btn.x + (raise_btn.w - f_lbl.get_width()) // 2, 356))
                elif is_p_cd:
                    m_left = (p_cd + 29) // 30
                    pygame.draw.rect(screen, (38, 42, 50), raise_btn, border_radius=6)
                    pygame.draw.rect(screen, (60, 65, 78), raise_btn, 1, border_radius=6)
                    cd_txt = f"MUSTERING COOLDOWN ({p_cd}d / {m_left}m left)"
                    cd_surf = font_sm.render(cd_txt, True, (140, 150, 165))
                    screen.blit(cd_surf, (raise_btn.x + (raise_btn.w - cd_surf.get_width()) // 2, 356))
                else:
                    pygame.draw.rect(screen, (35, 95, 50) if b_r_hov else (25, 70, 38), raise_btn, border_radius=6)
                    pygame.draw.rect(screen, COLOR_TEXT_GREEN, raise_btn, 1, border_radius=6)
                    r_lbl = font_md.render(f"RAISE LOCAL LEVY ({sel_prov['levies_current']} Men)", True, COLOR_TEXT_WHITE)
                    screen.blit(r_lbl, (raise_btn.x + (raise_btn.w - r_lbl.get_width()) // 2, 354))
                    if mouse_clicked and b_r_hov:
                        state.raise_province_levy(state.selected_province)
    
                rally_btn = pygame.Rect(content_x, 395, content_w, 40)
                b_rl_hov = rally_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (35, 65, 110) if b_rl_hov else (25, 48, 85), rally_btn, border_radius=6)
                pygame.draw.rect(screen, (70, 130, 220), rally_btn, 1, border_radius=6)
                rl_lbl = font_md.render("RALLY ALL ARMIES HERE (M)", True, COLOR_TEXT_WHITE)
                screen.blit(rl_lbl, (rally_btn.x + (rally_btn.w - rl_lbl.get_width()) // 2, 404))
                if mouse_clicked and b_rl_hov:
                    state.rally_all_armies_to(state.selected_province)
            else:
                screen.blit(font_md.render("Enemy Held Territory", True, COLOR_TEXT_RED), (content_x, 320))
                screen.blit(font_xs.render("• Right click your armies to march and conquer.", True, COLOR_TEXT_MUTED), (content_x, 350))
    
        # -------------------------------------------------------------
        # TAB 2: BUILDINGS
        # -------------------------------------------------------------
        elif state.right_tab == "buildings":
            screen.blit(font_md.render("Constructed Province Holdings", True, COLOR_GOLD), (content_x, 160))
            # List all unique holdings in this province
            prov_holdings = {}
            for coord, sdata in state.settlements.items():
                if sdata["province"] == state.selected_province:
                    hid = sdata.get("id") or sdata.get("name")
                    if hid not in prov_holdings:
                        prov_holdings[hid] = {
                            "name": sdata["name"],
                            "lord": sdata.get("lord", "None"),
                            "type": sdata.get("type", "city"),
                            "level": sdata.get("level", 0),
                            "tile": coord
                        }
    
            cy = 190
            for hid, h_info in list(prov_holdings.items())[:6]:
                c_box = pygame.Rect(content_x, cy, content_w, 42)
                is_c_hov = c_box.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (45, 52, 68) if is_c_hov else (32, 38, 50), c_box, border_radius=4)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, c_box, 1, border_radius=4)
    
                htype = h_info["type"]
                if htype == "town":
                    htype = "city"
                h_icon = "[City]" if htype == "city" else ("[Fort]" if htype == "fort" else "⚔")
                screen.blit(font_xs.render(f"{h_icon} {h_info['name']}", True, COLOR_GOLD), (content_x + 8, cy + 5))
    
                if htype == "city":
                    stat_sub = f"Lord: {h_info['lord']}  •  +3g  •  +10 Rec/m  •  100 Gar"
                elif htype == "fort":
                    stat_sub = f"Lord: {h_info['lord']}  •  +1g  •  +10 Rec/m  •  300 Gar"
                else:
                    bstats = get_barrack_stats(h_info['level'])
                    stat_sub = f"Lord: {h_info['lord']}  •  -{bstats['upkeep']}g Upk  •  +{bstats['recruits']} Rec/m"
                screen.blit(font_xs.render(stat_sub, True, COLOR_TEXT_MUTED), (content_x + 8, cy + 22))
    
                if mouse_clicked and is_c_hov:
                    state.selected_settlement = h_info["tile"]
                cy += 48
    
            if is_player_owned:
                pygame.draw.line(screen, COLOR_PANEL_BORDER, (content_x, cy + 6), (content_x + content_w, cy + 6), 1)
                screen.blit(font_md.render("Construct New Holding", True, COLOR_GOLD), (content_x, cy + 14))
    
                menu_specs = [
                    ("city", "[City] CITY (1 Tile - 600g)", "+100 Gar  •  +10 Recruits/m  •  +3 Gold/m", 600),
                    ("fort", "[Fort] FORT (2 Tiles - 1,000g)", "+300 Gar  •  +10 Recruits/m  •  +1 Gold/m  [T: Rotate]", 1000),
                    ("barrack", "⚔ BARRACKS (1 Tile - 800g)", "+100 Gar  •  +10 Recruits/m (Upgr)  •  -1g Upkeep", 800)
                ]
    
                btn_y = cy + 36
                for b_type_key, b_title, b_sub, b_cost in menu_specs:
                    b_rect = pygame.Rect(content_x, btn_y, content_w, 36)
                    b_hov = b_rect.collidepoint(mouse_pos)
                    is_active = (state.build_mode and state.build_type == b_type_key)
                    can_afford = (state.player["gold"] >= b_cost)
    
                    if is_active:
                        bg_c = (140, 80, 20)
                        border_c = COLOR_GOLD
                    elif b_hov and can_afford:
                        bg_c = (55, 42, 28)
                        border_c = (230, 180, 50)
                    elif not can_afford:
                        bg_c = (35, 36, 42)
                        border_c = (70, 72, 80)
                    else:
                        bg_c = (38, 34, 30)
                        border_c = (140, 110, 50)
    
                    pygame.draw.rect(screen, bg_c, b_rect, border_radius=4)
                    pygame.draw.rect(screen, border_c, b_rect, 2 if is_active else 1, border_radius=4)
    
                    title_col = COLOR_GOLD if is_active else (COLOR_TEXT_WHITE if can_afford else COLOR_TEXT_MUTED)
                    screen.blit(font_xs.render(b_title, True, title_col), (content_x + 8, btn_y + 4))
                    screen.blit(font_xs.render(b_sub, True, (240, 220, 170) if is_active else COLOR_TEXT_MUTED), (content_x + 8, btn_y + 19))
    
                    if mouse_clicked and b_hov:
                        if is_active:
                            state.build_mode = False
                        else:
                            state.build_mode = True
                            state.build_type = b_type_key
    
                    btn_y += 42
    
                if state.build_mode:
                    cur_spec = BUILDING_SPECS.get(state.build_type, BUILDING_SPECS["city"])
                    hint1 = font_xs.render(f"• Active: Placing {cur_spec['name']} ({cur_spec['tiles']} Tile{'s' if cur_spec['tiles'] > 1 else ''})", True, (255, 225, 100))
                    screen.blit(hint1, (content_x, btn_y + 6))
                    if cur_spec["tiles"] > 1:
                        hint2 = font_xs.render("• Press 'T' to rotate (Horiz / Vert)", True, COLOR_GOLD)
                    else:
                        hint2 = font_xs.render("• Hover 1 free tile in this province", True, COLOR_TEXT_WHITE)
                    hint3 = font_xs.render("• Click to establish holding  •  ESC to cancel", True, COLOR_TEXT_GREEN)
                    screen.blit(hint2, (content_x, btn_y + 22))
                    screen.blit(hint3, (content_x, btn_y + 38))
    
        # -------------------------------------------------------------
        # TAB 3: VASSALS (Detailed Realm & Province Vassals)
        # -------------------------------------------------------------
        elif state.right_tab == "vassals":
            screen.blit(font_md.render("Provincial Vassals List", True, COLOR_GOLD), (content_x, 160))
            v_list = state.vassals.get(state.selected_province, [])
            vy = 190
            for v_idx, v in enumerate(v_list[:5]):
                v_box = pygame.Rect(content_x, vy, content_w, 56)
                is_v_hov = v_box.collidepoint(mouse_pos)
                is_v_sel = (state.selected_vassal_idx == v_idx)
                v_bg = (55, 65, 85) if is_v_sel else ((42, 48, 62) if is_v_hov else (32, 36, 48))
                pygame.draw.rect(screen, v_bg, v_box, border_radius=4)
                pygame.draw.rect(screen, (100, 255, 120) if is_v_sel else COLOR_PANEL_BORDER, v_box, 1, border_radius=4)
    
                screen.blit(font_xs.render(f"♚ {v['name']}", True, COLOR_GOLD if is_v_sel else COLOR_TEXT_WHITE), (content_x + 8, vy + 4))
                st = get_vassal_landed_status(state, v, state.selected_province)
                c_info = v.get('city_name') if st["is_landed"] else 'Landless Noble (Unlanded)'
                screen.blit(font_xs.render(f"Fief: {c_info}", True, (200, 230, 255)), (content_x + 8, vy + 21))
                levy_txt = f"+{st['levy_contribution']}" if st["is_landed"] else "0"
                tax_txt = f"+{fmt_gold(st['tax_paid'])}g/m" if st["is_landed"] else "0g/m"
                screen.blit(font_xs.render(f"Gold: {fmt_gold(v['gold'])}g  •  Levies: {levy_txt}  •  Tax: {tax_txt}", True, COLOR_TEXT_MUTED), (content_x + 8, vy + 37))
    
                if mouse_clicked and is_v_hov:
                    state.selected_vassal_idx = v_idx
                    state.inspecting_vassal = {"province": state.selected_province, "vassal": v}
                    if v.get("tiles"):
                        state.selected_settlement = v["tiles"][0]
                    state.logs.append(f"Opened royal dossier for vassal {v['name']}.")
    
                vy += 62
    
        # -------------------------------------------------------------
        # TAB 4: FIEFS (Fiefs Management, Redrawing, Granting, Revoking)
        # -------------------------------------------------------------
        elif state.right_tab == "fiefs":
            prov_fiefs = [f for f in state.fiefs.values() if f.get("province") == state.selected_province]
            total_fiefs = len(prov_fiefs)
            per_page = 5 if not state.editing_fief_id else 4
            total_pages = max(1, (total_fiefs + per_page - 1) // per_page)
            state.fief_page = max(0, min(getattr(state, "fief_page", 0), total_pages - 1))
    
            screen.blit(font_md.render(f"Provincial Fiefs & Baronies ({total_fiefs})", True, COLOR_GOLD), (content_x, 155))
    
            if total_pages > 1:
                # Quick Top Pagination buttons: < Page X/Y >
                h_next_btn = pygame.Rect(content_x + content_w - 26, 152, 22, 22)
                h_prev_btn = pygame.Rect(content_x + content_w - 96, 152, 22, 22)
                hp_hov = h_prev_btn.collidepoint(mouse_pos)
                hn_hov = h_next_btn.collidepoint(mouse_pos)
    
                pygame.draw.rect(screen, (50, 62, 85) if hp_hov else (32, 38, 52), h_prev_btn, border_radius=3)
                pygame.draw.rect(screen, COLOR_GOLD if hp_hov else COLOR_PANEL_BORDER, h_prev_btn, 1, border_radius=3)
                screen.blit(font_xs.render("<", True, COLOR_TEXT_WHITE if state.fief_page > 0 else COLOR_TEXT_MUTED), (h_prev_btn.x + 7, 155))
    
                pygame.draw.rect(screen, (50, 62, 85) if hn_hov else (32, 38, 52), h_next_btn, border_radius=3)
                pygame.draw.rect(screen, COLOR_GOLD if hn_hov else COLOR_PANEL_BORDER, h_next_btn, 1, border_radius=3)
                screen.blit(font_xs.render(">", True, COLOR_TEXT_WHITE if state.fief_page < total_pages - 1 else COLOR_TEXT_MUTED), (h_next_btn.x + 7, 155))
    
                h_pg_txt = font_xs.render(f"{state.fief_page + 1}/{total_pages}", True, COLOR_GOLD)
                screen.blit(h_pg_txt, (h_prev_btn.right + (h_next_btn.left - h_prev_btn.right - h_pg_txt.get_width()) // 2, 156))
    
                if mouse_clicked and hp_hov and state.fief_page > 0:
                    state.fief_page -= 1
                elif mouse_clicked and hn_hov and state.fief_page < total_pages - 1:
                    state.fief_page += 1
    
            # Header action: Edit banner or Carve New Fief button
            if state.editing_fief_id:
                edit_f = state.fiefs.get(state.editing_fief_id)
                f_name = edit_f["name"] if edit_f else "Fief"
                num_tiles = len(edit_f.get("tiles", [])) if edit_f else 0
                eb_rect = pygame.Rect(content_x, 180, content_w, 46)
                pygame.draw.rect(screen, (70, 50, 15), eb_rect, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD, eb_rect, 2, border_radius=4)
                screen.blit(font_xs.render(f"✎ CARVING: {f_name} ({num_tiles} tiles)", True, COLOR_GOLD), (content_x + 8, 184))
                screen.blit(font_xs.render("Click green tiles on map (Min 1)", True, (240, 240, 240)), (content_x + 8, 202))
                
                # CANCEL button
                can_btn = pygame.Rect(content_x + content_w - 75, 186, 68, 28)
                can_hov = can_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (100, 35, 35) if can_hov else (75, 25, 25), can_btn, border_radius=4)
                pygame.draw.rect(screen, COLOR_TEXT_RED, can_btn, 1, border_radius=4)
                can_lbl = font_xs.render("CANCEL", True, COLOR_TEXT_WHITE)
                screen.blit(can_lbl, (can_btn.x + (can_btn.w - can_lbl.get_width()) // 2, 193))

                # DONE button
                done_btn = pygame.Rect(content_x + content_w - 150, 186, 68, 28)
                d_hov = done_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (35, 100, 50) if d_hov else (25, 75, 40), done_btn, border_radius=4)
                pygame.draw.rect(screen, COLOR_TEXT_GREEN, done_btn, 1, border_radius=4)
                done_lbl = font_xs.render("DONE ✓", True, COLOR_TEXT_WHITE)
                screen.blit(done_lbl, (done_btn.x + (done_btn.w - done_lbl.get_width()) // 2, 193))
    
                if mouse_clicked and d_hov:
                    if edit_f and len(edit_f.get("tiles", [])) < 1:
                        del state.fiefs[state.editing_fief_id]
                        state.editing_fief_id = None
                        state.logs.append(f"Cancelled carving {f_name}: No tiles were selected.")
                    else:
                        if edit_f:
                            # Synchronize all settlement holdings in this newly expanded/merged fief!
                            is_f_crown = (edit_f.get("is_crown_demesne", False) or 
                                          edit_f.get("holder") == state.player["name"])
                            for t in edit_f.get("tiles", []):
                                if t in state.settlements:
                                    if is_f_crown:
                                        state.settlements[t]["lord"] = f"{state.player['name']} (Crown Demesne)"
                                        state.settlements[t]["vassal_id"] = None
                                        state.settlements[t]["is_crown_demesne"] = True
                                        state.settlements[t]["is_crown_fief"] = True
                                    elif edit_f.get("vassal_id") or edit_f.get("holder"):
                                        state.settlements[t]["lord"] = edit_f["holder"]
                                        state.settlements[t]["vassal_id"] = edit_f.get("vassal_id")
                                        state.settlements[t]["is_crown_demesne"] = False
                                        state.settlements[t]["is_crown_fief"] = False
                                    else:
                                        # Ungranted fief (no governor/holder yet)
                                        state.settlements[t]["lord"] = "Ungranted (No Governor)"
                                        state.settlements[t]["vassal_id"] = None
                                        state.settlements[t]["is_crown_demesne"] = False
                                        state.settlements[t]["is_crown_fief"] = False
                        state.editing_fief_id = None
                        state.logs.append(f"Successfully established boundaries for {f_name} ({len(edit_f['tiles'])} tiles)!")
    
                elif mouse_clicked and can_hov:
                    if edit_f and (edit_f.get("is_newly_carved") or len(edit_f.get("tiles", [])) == 0):
                        del state.fiefs[state.editing_fief_id]
                        state.logs.append(f"Cancelled carving: {f_name} removed.")
                    else:
                        state.logs.append(f"Cancelled editing boundaries for {f_name}.")
                    state.editing_fief_id = None
    
                fy = 232
            else:
                # Carve New Fief Button
                carve_btn = pygame.Rect(content_x, 182, content_w, 28)
                c_hov = carve_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 75, 110) if c_hov else (30, 55, 85), carve_btn, border_radius=4)
                pygame.draw.rect(screen, (100, 180, 255), carve_btn, 1, border_radius=4)
                crv_lbl = font_xs.render("+ CARVE NEW FIEF (Partition Land)", True, COLOR_TEXT_WHITE)
                screen.blit(crv_lbl, (carve_btn.x + (carve_btn.w - crv_lbl.get_width()) // 2, 188))
                if mouse_clicked and c_hov:
                    carve_new_fief(state, state.selected_province)
                fy = 216
    
            # Pagination slice
            start_i = state.fief_page * per_page
            page_fiefs = prov_fiefs[start_i:start_i + per_page]
    
            for f_data in page_fiefs:
                f_box = pygame.Rect(content_x, fy, content_w, 64)
                is_f_hov = f_box.collidepoint(mouse_pos)
                is_f_sel = (state.selected_fief_id == f_data["id"])
                is_f_editing = (state.editing_fief_id == f_data["id"])
    
                bg_c = (65, 55, 30) if is_f_editing else ((55, 65, 85) if is_f_sel else ((42, 48, 62) if is_f_hov else (32, 36, 48)))
                pygame.draw.rect(screen, bg_c, f_box, border_radius=4)
                b_color = COLOR_GOLD if is_f_editing else ((100, 255, 120) if is_f_sel else COLOR_PANEL_BORDER)
                pygame.draw.rect(screen, b_color, f_box, 2 if (is_f_sel or is_f_editing) else 1, border_radius=4)
    
                is_ungranted = (f_data.get("holder") is None and f_data.get("vassal_id") is None and not f_data.get("is_crown_demesne"))
                is_crown_owned = (not is_ungranted) and (f_data.get("holder") == state.player["name"] or f_data.get("is_crown_demesne", False))
    
                if is_ungranted:
                    holder_str = "Lord: Ungranted (No Governor)"
                    h_col = (255, 185, 90)
                elif is_crown_owned:
                    holder_str = f"Lord: {state.player['name']} (Crown Demesne)"
                    h_col = COLOR_GOLD
                else:
                    holder_str = f"Lord: {f_data.get('holder', 'Unknown')}"
                    h_col = (180, 255, 180)
    
                screen.blit(font_xs.render(f"⚔ {f_data['name']} ({len(f_data['tiles'])} Tiles)", True, COLOR_GOLD), (content_x + 8, fy + 4))
                screen.blit(font_xs.render(holder_str, True, h_col), (content_x + 8, fy + 18))
    
                # Action buttons on fief card
                e_hov = False
                g_hov = False
                d_hov = False
                r_hov = False
    
                # 1. Edit Tiles Button
                b_edit = pygame.Rect(content_x + 8, fy + 36, 75, 22)
                e_hov = b_edit.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (80, 70, 30) if e_hov else (50, 45, 25), b_edit, border_radius=3)
                pygame.draw.rect(screen, COLOR_GOLD, b_edit, 1, border_radius=3)
                edt_lbl = font_xs.render("EDIT ✎" if not is_f_editing else "STOP ✕", True, COLOR_GOLD)
                screen.blit(edt_lbl, (b_edit.x + (b_edit.w - edt_lbl.get_width()) // 2, fy + 40))
                if mouse_clicked and e_hov:
                    state.editing_fief_id = None if is_f_editing else f_data["id"]
                    state.selected_fief_id = f_data["id"]
                    if state.editing_fief_id:
                        state.selected_settlement = None
    
                # 2. Grant / Revoke Buttons
                if is_ungranted or is_crown_owned:
                    # Grant Fief Button (Opens Vassal Selection Modal)
                    b_grant = pygame.Rect(content_x + 90, fy + 36, 140, 22)
                    g_hov = b_grant.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (40, 110, 60) if g_hov else (30, 80, 45), b_grant, border_radius=3)
                    pygame.draw.rect(screen, COLOR_TEXT_GREEN, b_grant, 1, border_radius=3)
                    grt_lbl = font_xs.render("GRANT TO VASSAL", True, COLOR_TEXT_WHITE)
                    screen.blit(grt_lbl, (b_grant.x + (b_grant.w - grt_lbl.get_width()) // 2, fy + 40))
                    if mouse_clicked and g_hov:
                        state.granting_fief_id = f_data["id"]
                        state.grant_page = 0
    
                    # 3. Dissolve Button
                    b_del = pygame.Rect(content_x + content_w - 85, fy + 36, 78, 22)
                    d_hov = b_del.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (85, 30, 30) if d_hov else (60, 25, 25), b_del, border_radius=3)
                    pygame.draw.rect(screen, (220, 80, 80), b_del, 1, border_radius=3)
                    del_lbl = font_xs.render("DISSOLVE", True, (255, 200, 200))
                    screen.blit(del_lbl, (b_del.x + (b_del.w - del_lbl.get_width()) // 2, fy + 40))
                    if mouse_clicked and d_hov:
                        fid_to_del = f_data["id"]
                        for t in f_data["tiles"]:
                            if t in state.settlements:
                                state.settlements[t]["lord"] = f"{state.player['name']} (Crown Demesne)"
                                state.settlements[t]["vassal_id"] = None
                                state.settlements[t]["is_crown_demesne"] = True
                                state.settlements[t]["is_crown_fief"] = False
                        del state.fiefs[fid_to_del]
                        if state.selected_fief_id == fid_to_del:
                            state.selected_fief_id = None
                        if state.editing_fief_id == fid_to_del:
                            state.editing_fief_id = None
                        state.logs.append(f"Dissolved {f_data['name']}. Land returned to Crown province.")
                        break
                else:
                    # Revoke Fief Button (Transfers vassal ownership to Crown Demesne and dissolves fief partition)
                    b_revoke = pygame.Rect(content_x + 90, fy + 36, content_w - 98, 22)
                    r_hov = b_revoke.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (100, 45, 45) if r_hov else (70, 30, 30), b_revoke, border_radius=3)
                    pygame.draw.rect(screen, (240, 100, 100), b_revoke, 1, border_radius=3)
                    rev_lbl = font_xs.render("REVOKE FIEF (♚ Return to Crown)", True, COLOR_TEXT_WHITE)
                    screen.blit(rev_lbl, (b_revoke.x + (b_revoke.w - rev_lbl.get_width()) // 2, fy + 40))
                    if mouse_clicked and r_hov:
                        v_prev = f_data["holder"]
                        v_prev_id = f_data.get("vassal_id")
                        fid_to_del = f_data["id"]
    
                        # 1. Transfer all settlements on this fief directly to the King (Crown Demesne)
                        for t in f_data["tiles"]:
                            if t in state.settlements:
                                state.settlements[t]["lord"] = f"{state.player['name']} (Crown Demesne)"
                                state.settlements[t]["vassal_id"] = None
                                state.settlements[t]["is_crown_demesne"] = True
                                state.settlements[t]["is_crown_fief"] = False
    
                        # 2. Update former vassal's held tiles
                        for pid, v_list in state.vassals.items():
                            for v in v_list:
                                if v["name"] == v_prev or v["id"] == v_prev_id:
                                    v["tiles"] = [t for t in v.get("tiles", []) if t not in f_data["tiles"]]
                                    if not v["tiles"]:
                                        v["city_name"] = None
                                    st_v = get_vassal_landed_status(state, v, pid)
                                    v["tax_contribution"] = st_v["tax_paid"]
                                    v["levy_contribution"] = st_v["levy_contribution"]
    
                        # 3. Dissolve the fief partition so land returns directly to the King as unpartitioned Crown land
                        del state.fiefs[fid_to_del]
                        if state.selected_fief_id == fid_to_del:
                            state.selected_fief_id = None
                        if state.editing_fief_id == fid_to_del:
                            state.editing_fief_id = None
    
                        state.logs.append(f"Revoked & dissolved {f_data['name']} from {v_prev}! Returned directly to Crown Demesne.")
                        break
    
                if mouse_clicked and is_f_hov and not (e_hov or g_hov or d_hov or r_hov):
                    state.selected_fief_id = f_data["id"]
    
                fy += 68
    
            # Pagination Controls for Fiefs list (Bottom bar)
            if total_pages > 1:
                py_bar = max(562, fy + 6)
                prev_btn = pygame.Rect(content_x, py_bar, 90, 26)
                next_btn = pygame.Rect(content_x + content_w - 90, py_bar, 90, 26)
                p_hov = prev_btn.collidepoint(mouse_pos)
                n_hov = next_btn.collidepoint(mouse_pos)
    
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if p_hov else COLOR_BUTTON_NORMAL, prev_btn, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if p_hov else COLOR_PANEL_BORDER, prev_btn, 1, border_radius=4)
                prv_lbl = font_xs.render("< PREV", True, COLOR_TEXT_WHITE if state.fief_page > 0 else COLOR_TEXT_MUTED)
                screen.blit(prv_lbl, (prev_btn.x + (prev_btn.w - prv_lbl.get_width()) // 2, py_bar + 6))
    
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if n_hov else COLOR_BUTTON_NORMAL, next_btn, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if n_hov else COLOR_PANEL_BORDER, next_btn, 1, border_radius=4)
                nxt_lbl = font_xs.render("NEXT >", True, COLOR_TEXT_WHITE if state.fief_page < total_pages - 1 else COLOR_TEXT_MUTED)
                screen.blit(nxt_lbl, (next_btn.x + (next_btn.w - nxt_lbl.get_width()) // 2, py_bar + 6))
    
                pg_lbl = font_xs.render(f"Page {state.fief_page + 1}/{total_pages} ({total_fiefs} Fiefs)", True, COLOR_GOLD)
                screen.blit(pg_lbl, (content_x + (content_w - pg_lbl.get_width()) // 2, py_bar + 6))
    
                if mouse_clicked and p_hov and state.fief_page > 0:
                    state.fief_page -= 1
                elif mouse_clicked and n_hov and state.fief_page < total_pages - 1:
                    state.fief_page += 1
        else:
            # Enemy Province Instructions
            screen.blit(font_md.render("Viking Controlled Territory", True, COLOR_TEXT_RED), (content_x, 415))
            screen.blit(font_sm.render("To conquer this province:", True, COLOR_TEXT_MUTED), (content_x, 445))
            screen.blit(font_xs.render("1. Raise levies from your provinces.", True, COLOR_TEXT_WHITE), (content_x, 470))
            screen.blit(font_xs.render("2. Rally & merge your hosts into an army.", True, COLOR_TEXT_WHITE), (content_x, 490))
            screen.blit(font_xs.render("3. Select your army and click here to march!", True, COLOR_GOLD), (content_x, 510))
    
    # ---------------------------------------------------------
    # DRAW BOX SELECTION RECTANGLE
    # ---------------------------------------------------------
    if box_start and box_end:
        x1, y1 = box_start
        x2, y2 = box_end
        bx, by = min(x1, x2), min(y1, y2)
        bw, bh = abs(x2 - x1), abs(y2 - y1)
        if bw > 2 and bh > 2:
            # Semi-transparent fill
            sel_surface = pygame.Surface((bw, bh), pygame.SRCALPHA)
            sel_surface.fill((100, 220, 100, 35))
            screen.blit(sel_surface, (bx, by))
            # Bright green border
            pygame.draw.rect(screen, (100, 255, 120), pygame.Rect(bx, by, bw, bh), 1)
    
    
