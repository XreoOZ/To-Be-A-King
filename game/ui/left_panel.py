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
from game.data.characters import CHARACTERS, get_short_name, get_display_name, get_realm_name
from game.data.provinces import PROVINCES, ADJACENCY
from game.data.scenario import get_scenario
from game.data.buildings import BUILDING_SPECS, BARRACK_UPGRADE_COSTS, get_barrack_stats
from game.systems.economy import (
    get_all_settlement_holdings, get_realm_finances,
    get_vassal_landed_status, sync_province_holdings_stats, fmt_gold, get_ruler_demesne_stats
)

def get_feudal_rank_key(rank_or_title):
    """Normalizes title tiers and ruler ranks to their display rank."""
    t = str(rank_or_title).lower()
    if "king" in t or "kingdom" in t or "emperor" in t or "empire" in t:
        return "king"
    if "duke" in t or "duchy" in t or "archon" in t or "ironlord" in t:
        return "duke"
    if "count" in t or "county" in t or "thane" in t or "warden" in t:
        return "count"
    return "baron"


def get_feudal_badge(rank_or_title):
    """Returns (symbol, color) for feudal nobility ranks (CK2 style)."""
    rank = get_feudal_rank_key(rank_or_title)
    if rank == "king":
        return "👑", (255, 215, 0)
    elif rank == "duke":
        return "⚜", (240, 190, 70)
    elif rank == "count":
        return "🛡", (180, 210, 255)
    else:
        return "🏰", (220, 180, 140)

def draw_feudal_pill(screen, font_xs, rank_or_title, x, y):
    """Draws a Crusader Kings style rank badge pill and returns (pill_width, fg_color)."""
    rank = get_feudal_rank_key(rank_or_title)
    if rank == "king":
        txt, fg, bg = "👑 KING", (255, 215, 0), (70, 55, 15)
    elif rank == "duke":
        txt, fg, bg = "⚜ DUKE", (240, 190, 70), (60, 48, 20)
    elif rank == "count":
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


def render_title_grant_selector(screen, state, mouse_pos, mouse_clicked, fonts, content_x, content_w):
    """Shows the eligible nobles when the player is granting a held title."""
    font_xs = fonts["xs"]
    font_md = fonts["md"]
    target_title_id = state.title_grant_target_title_id
    title = state.titles.get(target_title_id)
    title_name = title.name if title else "Feudal Title"
    tier_name = title.tier.capitalize() if title else "Title"

    pygame.draw.rect(screen, COLOR_PANEL_BG, pygame.Rect(content_x - 2, 294, content_w + 4, 385))
    screen.blit(font_md.render(f"🎁 Grant {tier_name}", True, COLOR_GOLD), (25, 298))
    screen.blit(font_xs.render(f"Bestow {title_name} upon a Noble:", True, (255, 200, 140)), (25, 320))
    screen.blit(font_xs.render("The title changes their rank and feudal obligations.", True, (150, 230, 170)), (25, 336))

    all_vassals = [
        vassal
        for province_vassals in state.vassals.values()
        for vassal in province_vassals
        if PROVINCES.get(vassal.get("province"), {}).get("owner") == state.player_id
    ]
    recipients = [
        vassal for vassal in all_vassals
        if vassal.get("id") != getattr(title, "holder_id", None)
    ]

    if not recipients:
        screen.blit(font_xs.render("No eligible nobles to receive this title.", True, COLOR_TEXT_MUTED), (content_x, 365))

    vy = 358
    for recipient in recipients[:5]:
        clean_name = state.get_character_clean_name(recipient.get("name", "Noble"))
        card = pygame.Rect(content_x, vy, content_w, 52)
        hovered = card.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (48, 56, 74) if hovered else (32, 38, 52), card, border_radius=4)
        pygame.draw.rect(screen, COLOR_GOLD if hovered else (70, 110, 170), card, 1, border_radius=4)

        pill_width, _ = draw_feudal_pill(
            screen, font_xs, recipient.get("rank", "baron"), 34, vy + 4
        )
        screen.blit(font_xs.render(clean_name, True, COLOR_TEXT_WHITE), (34 + pill_width + 6, vy + 5))

        seat = recipient.get("city_name") or "Fiefdom"
        if len(seat) > 24:
            seat = seat[:22] + ".."
        screen.blit(
            font_xs.render(f"Seat: {seat} • Gold: {fmt_gold(recipient.get('gold', 0))}g", True, (180, 215, 255)),
            (34, vy + 28),
        )

        bestow_button = pygame.Rect(content_x + content_w - 95, vy + 13, 85, 26)
        button_hovered = bestow_button.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (40, 85, 55) if button_hovered else (28, 65, 40), bestow_button, border_radius=3)
        pygame.draw.rect(screen, COLOR_TEXT_GREEN, bestow_button, 1, border_radius=3)
        label = font_xs.render("🎁 Bestow", True, COLOR_TEXT_WHITE)
        screen.blit(label, (bestow_button.centerx - label.get_width() // 2, bestow_button.y + 5))

        if mouse_clicked and (hovered or button_hovered):
            state.grant_title(target_title_id, recipient["id"])
            state.title_grant_target_title_id = None
            return
        vy += 56

    cancel_button = pygame.Rect(content_x, 645, content_w, 28)
    cancel_hovered = cancel_button.collidepoint(mouse_pos)
    pygame.draw.rect(
        screen,
        (75, 35, 35) if cancel_hovered else (55, 25, 25),
        cancel_button,
        border_radius=4,
    )
    pygame.draw.rect(screen, (220, 80, 80), cancel_button, 1, border_radius=4)
    label = font_xs.render("✖ CANCEL GRANT", True, (255, 210, 210))
    screen.blit(label, (cancel_button.centerx - label.get_width() // 2, cancel_button.y + 6))
    if mouse_clicked and cancel_hovered:
        state.title_grant_target_title_id = None


def get_vassal_liege_name(state, v_data):
    """Returns the clean display name of a vassal's direct liege."""
    if v_data.get("is_direct_vassal", False):
        return state.player.get("name", "Ruler").split()[0]
    actual_liege_id = v_data.get("liege_id")
    if actual_liege_id in (state.player_id, None):
        return state.player.get("name", "Ruler").split()[0]
    all_v = [v for plist in state.vassals.values() for v in plist]
    c_liege = next((cv for cv in all_v if cv.get("id") == actual_liege_id), None)
    if not c_liege:
        c_liege = next((cv for cv in all_v if v_data.get("id") in cv.get("sub_vassals", [])), None)
    if c_liege:
        clean_name = state.get_character_clean_name(c_liege.get("name", "Liege"))
        return clean_name.split()[0]
    if actual_liege_id in CHARACTERS:
        clean_name = state.get_character_clean_name(CHARACTERS[actual_liege_id].get("name", "Liege"))
        return clean_name.split()[0]
    return state.player.get("name", "Ruler").split()[0]

def render_left_panel(screen, state, mouse_pos, mouse_clicked, fonts, portrait_cache, coa_cache):
    font_xs = fonts["xs"]
    font_sm = fonts["sm"]
    font_md = fonts["md"]
    font_lg = fonts["lg"]
    font_micro = fonts.get("micro", font_xs)

    # Clear vassal tile highlight each frame (will be re-set if hovering a vassal card)
    state.hovered_vassal_tiles = set()

    # 2. LEFT PANEL: PLAYER RULER & ACTIVE FORCES
    # ---------------------------------------------------------
    content_x = PANEL_L_X + 12
    content_w = PANEL_L_W - 24
    left_panel = pygame.Rect(PANEL_L_X, PANEL_Y, PANEL_L_W, PANEL_H)
    pygame.draw.rect(screen, COLOR_PANEL_BG, left_panel, border_radius=6)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, left_panel, 2, border_radius=6)
    
    # Portrait & Realm Shield (Clickable Ruler Card)
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
    has_field_army = any(a.owner == state.player_id and a.troops > 0 and not getattr(a, "is_demobilizing", False) for a in state.armies)
    if has_field_army:
        days_left = state.get_next_supply_days(state.player_id)
        b_hover = btn_raise_all.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (34, 46, 64) if b_hover else (26, 35, 50), btn_raise_all, border_radius=4)
        pygame.draw.rect(screen, (90, 160, 240) if b_hover else (65, 120, 185), btn_raise_all, 1, border_radius=4)
        sup_lbl = font_xs.render(f"Next Supply in : {days_left} d", True, (220, 238, 255))
        screen.blit(sup_lbl, (btn_raise_all.x + (btn_raise_all.w - sup_lbl.get_width()) // 2, 196))
        if mouse_clicked and b_hover:
            state.logs.append(f"Armies are already raised! Next supply convoy arrives in {days_left} days.")
    else:
        b_hover = btn_raise_all.collidepoint(mouse_pos)
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
    
    # Crown / Ducal Demesne Tab Items Calculation
    player_crown_items = []
    covered_holding_tiles = set()
    p_name = state.player.get("name", "")
    clean_pname = state.get_character_clean_name(p_name) if hasattr(state, "get_character_clean_name") else p_name

    for f in state.fiefs.values():
        prov_owner = PROVINCES.get(f.get("province"), {}).get("owner")
        f_holder = f.get("holder", "")
        f_owner = f.get("owner")
        f_vid = f.get("vassal_id")

        is_player_fief = (
            f_owner == state.player_id or
            f_holder == p_name or
            (clean_pname and clean_pname in f_holder) or
            (f_vid == f"duke_{state.player_id}") or
            (prov_owner == state.player_id and f_vid is None and f_owner in (None, state.player_id))
        )
        if f_owner in getattr(state, "ai_rulers", [state.enemy_id]) and f_owner != state.player_id:
            if not (f_holder == p_name or (clean_pname and clean_pname in f_holder) or f_vid == f"duke_{state.player_id}"):
                is_player_fief = False

        if is_player_fief and f_vid in (None, f"duke_{state.player_id}"):
            f["holder"] = p_name
            f["owner"] = state.player_id
            f["is_crown_demesne"] = True
            f["vassal_id"] = None
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
        s_lord = sdata.get("lord", "")
        s_owner = sdata.get("owner")
        s_vid = sdata.get("vassal_id")

        is_player_holding = (
            s_owner == state.player_id or
            s_lord == f"{p_name} (Crown Demesne)" or
            (clean_pname and clean_pname in s_lord) or
            (s_vid == f"duke_{state.player_id}") or
            (prov_owner == state.player_id and s_vid is None and s_owner in (None, state.player_id))
        )
        if s_owner in getattr(state, "ai_rulers", [state.enemy_id]) and s_owner != state.player_id:
            if not (s_lord == f"{p_name} (Crown Demesne)" or (clean_pname and clean_pname in s_lord) or s_vid == f"duke_{state.player_id}"):
                is_player_holding = False

        if is_player_holding and s_vid in (None, f"duke_{state.player_id}"):
            sdata["lord"] = f"{p_name} (Crown Demesne)"
            sdata["owner"] = state.player_id
            sdata["is_crown_demesne"] = True
            sdata["vassal_id"] = None
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
        # Header with Make an Army button
        screen.blit(font_md.render("Active Field Armies", True, COLOR_GOLD), (25, 302))

        mk_btn = pygame.Rect(content_x + content_w - 95, 298, 95, 26)
        b_mk_hov = mk_btn.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (35, 85, 52) if b_mk_hov else (24, 62, 38), mk_btn, border_radius=4)
        pygame.draw.rect(screen, (80, 210, 110), mk_btn, 1, border_radius=4)
        mk_lbl = font_xs.render("➕ Make Army", True, COLOR_TEXT_WHITE)
        screen.blit(mk_lbl, (mk_btn.x + (mk_btn.w - mk_lbl.get_width()) // 2, mk_btn.y + 5))
        if mouse_clicked and b_mk_hov:
            state.make_army_from_garrison()

        player_armies = [a for a in state.armies if a.owner == state.player_id]
        if not player_armies:
            screen.blit(font_sm.render("No armies in the field.", True, COLOR_TEXT_MUTED), (25, 335))
            screen.blit(font_xs.render("Click 'RAISE ALL' or '➕ Make Army' to summon hosts.", True, COLOR_TEXT_MUTED), (25, 355))
        else:
            ay = 330
            for a in player_armies[:4]:
                a_rect = pygame.Rect(content_x, ay, content_w, 48)
                is_sel = (a.id == state.selected_army_id)
                b_hover_a = a_rect.collidepoint(mouse_pos)
                
                bg_col = COLOR_BUTTON_ACTIVE if is_sel else ((55, 65, 82) if b_hover_a else (38, 44, 58))
                pygame.draw.rect(screen, bg_col, a_rect, border_radius=6)
                pygame.draw.rect(screen, COLOR_GOLD if is_sel else COLOR_PANEL_BORDER, a_rect, 1, border_radius=6)

                n_sub = len(getattr(a, "sub_units", []))
                sub_txt = f"({n_sub} Levies)" if n_sub > 1 else ""
                disp_n = a.name[:16] + ".." if len(a.name) > 17 else a.name
                screen.blit(font_sm.render(disp_n, True, COLOR_TEXT_WHITE), (content_x + 8, ay + 5))
                screen.blit(font_xs.render(f"{a.troops:,}m {sub_txt}", True, COLOR_GOLD), (content_x + content_w - 95, ay + 6))
                
                # Small Split Button on card
                sp_btn = pygame.Rect(content_x + content_w - 42, ay + 26, 18, 16)
                b_sp_hov = sp_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 75, 120) if b_sp_hov else (25, 45, 75), sp_btn, border_radius=3)
                pygame.draw.rect(screen, (100, 175, 255), sp_btn, 1, border_radius=3)
                screen.blit(font_micro.render("➦", True, (210, 235, 255)), (sp_btn.x + 3, sp_btn.y + 1))
                if mouse_clicked and b_sp_hov:
                    if len(getattr(a, "sub_units", [])) > 1:
                        state.split_army_target_id = a.id
                        state.split_selected_units = set()
                    else:
                        state.split_army_in_half(a.id)

                # Small Rename Button on card
                rn_btn = pygame.Rect(content_x + content_w - 20, ay + 26, 18, 16)
                b_rn_hov = rn_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (50, 60, 80) if b_rn_hov else (30, 36, 48), rn_btn, border_radius=3)
                pygame.draw.rect(screen, (100, 150, 220), rn_btn, 1, border_radius=3)
                screen.blit(font_micro.render("✎", True, (210, 230, 255)), (rn_btn.x + 4, rn_btn.y + 1))
                if mouse_clicked and b_rn_hov:
                    state.open_rename_modal("army", a.id, a.name)

                # Status string
                status_str = "Standing Ready"
                if a.in_battle: status_str = "⚔ Engaged in Battle"
                elif getattr(a, "is_starving", False): status_str = "☠ Starving (-5/day)"
                elif getattr(a, "is_expeditionary", False): status_str = "🚩 Expeditionary Campaign"
                elif a.courier_en_route: status_str = f"✉ Courier En Route ({a.courier_days_left}d)"
                elif a.is_mustering: status_str = f"⏳ Mustering ({a.muster_days}d left)"
                elif a.is_sieging: status_str = f"🛡 Besieging ({a.siege_progress}%)"
                elif a.is_moving: status_str = f"➔ Marching..."
                else: status_str = f"📍 Position: {a.tile}"

                st_color = COLOR_GOLD if a.in_battle else ((255, 65, 65) if getattr(a, "is_starving", False) else ((245, 185, 60) if getattr(a, "is_expeditionary", False) else ((255, 215, 80) if a.courier_en_route else ((255, 180, 50) if a.is_mustering else ((150, 200, 255) if a.is_demobilizing else COLOR_TEXT_MUTED)))))
                screen.blit(font_xs.render(status_str, True, st_color), (content_x + 8, ay + 27))

                if mouse_clicked and b_hover_a and not b_rn_hov and not b_sp_hov:
                    state.selected_army_id = a.id
                    state.selected_army_ids = [a.id]
                    state.selected_province = a.province

                ay += 52

        # Chronicle heading from the scenario.
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 545), (285, 545), 1)
        screen.blit(font_md.render(get_scenario().get("chronicle_heading", "Chronicle"), True, COLOR_GOLD), (25, 555))
    
        log_y = 582
        for log_msg in state.logs[-5:]:
            disp = log_msg[:34] + "..." if len(log_msg) > 37 else log_msg
            lm_surf = font_sm.render(f"• {disp}", True, COLOR_TEXT_MUTED)
            screen.blit(lm_surf, (25, log_y))
            log_y += 24

    elif state.left_tab == "demesne":
        if getattr(state, "title_grant_target_title_id", None) is not None:
            render_title_grant_selector(
                screen, state, mouse_pos, mouse_clicked, fonts, content_x, content_w
            )
            return

        if not hasattr(state, "demesne_selected_ruler_id"):
            state.demesne_selected_ruler_id = state.player_id
        if not hasattr(state, "demesne_selected_province"):
            state.demesne_selected_province = None
        if not hasattr(state, "demesne_page"):
            state.demesne_page = 0

        curr_ruler_id = state.demesne_selected_ruler_id

        # -------------------------------------------------------------
        # REALM / RULER SELECTOR PILLS (PLAYER & AI DEMESNES)
        # -------------------------------------------------------------
        rulers_list = []
        for r_id in state.get_active_rulers(include_player=True):
            role = "Player" if r_id == state.player_id else "AI"
            rulers_list.append((r_id, get_short_name(r_id), role))
        if not rulers_list:
            rulers_list = [(state.player_id, get_short_name(state.player_id), "Player")]

        # Paginate the roster when it does not fit the panel width.
        pill_min_w = 54
        arrow_w = 16
        max_visible = max(1, (content_w + 4) // (pill_min_w + 4))
        total_pages = max(1, (len(rulers_list) + max_visible - 1) // max_visible)
        ruler_page = max(0, min(getattr(state, "demesne_ruler_page", 0), total_pages - 1))
        # Always keep the selected ruler's page visible.
        sel_idx = next((i for i, r in enumerate(rulers_list) if r[0] == curr_ruler_id), 0)
        if sel_idx // max_visible != ruler_page:
            ruler_page = sel_idx // max_visible
        state.demesne_ruler_page = ruler_page

        page_rulers = rulers_list[ruler_page * max_visible:(ruler_page + 1) * max_visible]
        has_pages = total_pages > 1
        avail_w = content_w - (arrow_w * 2 + 8 if has_pages else 0)

        if has_pages:
            prev_rect = pygame.Rect(content_x, 298, arrow_w, 24)
            next_rect = pygame.Rect(content_x + content_w - arrow_w, 298, arrow_w, 24)
            for arrow_rect, enabled, delta, glyph in (
                (prev_rect, ruler_page > 0, -1, "‹"),
                (next_rect, ruler_page < total_pages - 1, 1, "›"),
            ):
                a_hov = arrow_rect.collidepoint(mouse_pos)
                a_bg = (40, 50, 70) if a_hov and enabled else (24, 30, 42)
                a_bd = (120, 160, 220) if a_hov and enabled else (60, 75, 100)
                pygame.draw.rect(screen, a_bg, arrow_rect, border_radius=4)
                pygame.draw.rect(screen, a_bd, arrow_rect, 1, border_radius=4)
                a_txt = font_sm.render(glyph, True, COLOR_TEXT_WHITE if enabled else COLOR_TEXT_MUTED)
                screen.blit(a_txt, (arrow_rect.x + (arrow_rect.w - a_txt.get_width()) // 2,
                                    arrow_rect.y + (arrow_rect.h - a_txt.get_height()) // 2))
                if mouse_clicked and a_hov and enabled:
                    state.demesne_ruler_page = ruler_page + delta

        pill_count = len(page_rulers)
        rw = (avail_w - 4 * (pill_count - 1)) // max(1, pill_count) if pill_count else avail_w
        rx = content_x + (arrow_w + 4 if has_pages else 0)
        for r_id, r_label, r_type in page_rulers:
            is_r_sel = (r_id == curr_ruler_id)
            r_btn = pygame.Rect(rx, 298, rw, 24)
            is_rb_hov = r_btn.collidepoint(mouse_pos)

            rb_bg = (60, 48, 20) if is_r_sel else ((40, 50, 70) if is_rb_hov else (28, 34, 48))
            rb_bd = COLOR_GOLD if is_r_sel else ((120, 160, 220) if is_rb_hov else (70, 90, 125))

            pygame.draw.rect(screen, rb_bg, r_btn, border_radius=4)
            pygame.draw.rect(screen, rb_bd, r_btn, 1, border_radius=4)

            btn_txt = font_xs.render(r_label, True, COLOR_GOLD if is_r_sel else COLOR_TEXT_WHITE)
            screen.blit(btn_txt, (r_btn.x + (r_btn.w - btn_txt.get_width()) // 2, 303))

            if mouse_clicked and is_rb_hov and r_id != curr_ruler_id:
                state.demesne_selected_ruler_id = r_id
                state.demesne_selected_province = None
                state.demesne_page = 0
                state.demesne_titles_page = 0
                state.logs.append(f"Inspecting direct demesne of {get_display_name(r_id)}.")
            rx += rw + 4

        # Keep the selected ruler valid if the roster changed.
        if curr_ruler_id not in CHARACTERS:
            curr_ruler_id = state.player_id
            state.demesne_selected_ruler_id = curr_ruler_id

        # Compute comprehensive demesne stats for selected ruler
        ruler_stats = get_ruler_demesne_stats(state, curr_ruler_id)
        r_char_info = CHARACTERS.get(curr_ruler_id, {})
        r_full_name = r_char_info.get("name", "Sovereign Ruler")
        clean_rname = state.get_character_clean_name(r_full_name)

        # -------------------------------------------------------------
        # MASTER DEMESNE OVERVIEW CARD (INCOME, EXPENSES, GARRISON, BLDGS)
        # -------------------------------------------------------------
        overview_card = pygame.Rect(content_x, 328, content_w, 66)
        pygame.draw.rect(screen, (32, 38, 52), overview_card, border_radius=4)
        pygame.draw.rect(screen, (80, 130, 200), overview_card, 1, border_radius=4)

        # Line 1: Header + Holdings count
        screen.blit(font_sm.render(f"♚ {clean_rname}'s Demesne", True, COLOR_GOLD), (34, 332))
        h_lim_txt = f"{ruler_stats['holdings_count']} / 5 Holdings"
        hl_surf = font_xs.render(h_lim_txt, True, (190, 230, 255))
        screen.blit(hl_surf, (content_x + content_w - hl_surf.get_width() - 8, 334))

        # Line 2: Finances (Income, Upkeep, Net)
        fin_txt = f"💰 Gross: +{fmt_gold(ruler_stats['gross_income'])}g  •  Expense: -{fmt_gold(ruler_stats['total_upkeep'])}g  •  Net: +{fmt_gold(ruler_stats['net_income'])}g/m"
        screen.blit(font_xs.render(fin_txt, True, (160, 240, 180) if ruler_stats['net_income'] >= 0 else (255, 160, 160)), (34, 350))

        # Line 3: Military & Manpower
        mil_txt = f"🛡️ Standing Garrison: {ruler_stats['total_garrison']} Defenders  •  ⚔️ Recruits: +{ruler_stats['total_recruits']}/m"
        screen.blit(font_xs.render(mil_txt, True, (215, 230, 255)), (34, 365))

        # Line 4: Buildings Breakdown
        b_items = [f"{cnt}x {bname}" for bname, cnt in ruler_stats['building_counts'].items()]
        b_str = ", ".join(b_items) if b_items else "No developed holdings"
        if len(b_str) > 42: b_str = b_str[:40] + ".."
        screen.blit(font_xs.render(f"🏛️ Buildings: {b_str}", True, (240, 215, 160)), (34, 379))

        prov_dict = ruler_stats["by_province"]
        prov_keys = list(prov_dict.keys())

        # -------------------------------------------------------------
        # LEVEL 1: LIST OF PROVINCES CONTAINING RULER'S DEMESNE
        # -------------------------------------------------------------
        if state.demesne_selected_province is None:
            held_titles = state.get_held_titles(curr_ruler_id)
            titles_per_page = 3
            title_pages = max(1, (len(held_titles) + titles_per_page - 1) // titles_per_page)
            state.demesne_titles_page = max(
                0, min(getattr(state, "demesne_titles_page", 0), title_pages - 1)
            )
            title_start = state.demesne_titles_page * titles_per_page
            visible_titles = held_titles[title_start:title_start + titles_per_page]

            screen.blit(
                font_xs.render(f"Titles Held by {get_short_name(curr_ruler_id)} ({len(held_titles)}):", True, COLOR_GOLD),
                (25, 400),
            )
            title_prev = pygame.Rect(content_x + content_w - 54, 398, 18, 18)
            title_next = pygame.Rect(content_x + content_w - 18, 398, 18, 18)
            title_prev_hovered = title_prev.collidepoint(mouse_pos)
            title_next_hovered = title_next.collidepoint(mouse_pos)
            page_label = font_xs.render(
                f"{state.demesne_titles_page + 1}/{title_pages}", True, COLOR_TEXT_MUTED
            )
            screen.blit(page_label, (title_prev.x - page_label.get_width() - 3, 400))
            screen.blit(
                font_xs.render("‹", True, COLOR_TEXT_WHITE if state.demesne_titles_page > 0 else COLOR_TEXT_MUTED),
                (title_prev.x + 5, title_prev.y + 1),
            )
            screen.blit(
                font_xs.render("›", True, COLOR_TEXT_WHITE if state.demesne_titles_page < title_pages - 1 else COLOR_TEXT_MUTED),
                (title_next.x + 5, title_next.y + 1),
            )
            if mouse_clicked and title_prev_hovered and state.demesne_titles_page > 0:
                state.demesne_titles_page -= 1
            elif mouse_clicked and title_next_hovered and state.demesne_titles_page < title_pages - 1:
                state.demesne_titles_page += 1

            owned_provinces = [
                pid for pid, province in PROVINCES.items()
                if province.get("owner") == curr_ruler_id
            ]
            for title_index, held_title in enumerate(visible_titles):
                title_y = 416 + title_index * 24
                title_rect = pygame.Rect(content_x, title_y, content_w, 22)
                title_hovered = title_rect.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (38, 44, 58) if title_hovered else (28, 34, 46), title_rect, border_radius=3)
                pygame.draw.rect(screen, (100, 130, 170), title_rect, 1, border_radius=3)

                pill_width, _ = draw_feudal_pill(
                    screen, font_xs, held_title.tier, content_x + 4, title_y + 3
                )
                province_id = held_title.province_id
                province_name = PROVINCES.get(province_id, {}).get("name", province_id or "Unassigned")
                if held_title.tier == "kingdom":
                    province_word = "province" if len(owned_provinces) == 1 else "provinces"
                    territory = f"Realm ({len(owned_provinces)} {province_word})"
                else:
                    territory = province_name.split()[0] if province_name else "Unassigned"
                title_text = f"{held_title.name} • {territory}"
                grant_button = None
                if held_title.tier != "kingdom" and curr_ruler_id == state.player_id:
                    grant_button = pygame.Rect(content_x + content_w - 52, title_y + 2, 48, 18)
                available_text_width = content_w - pill_width - 18
                if grant_button:
                    available_text_width -= grant_button.w + 4
                title_surface = font_xs.render(title_text, True, COLOR_TEXT_WHITE)
                if title_surface.get_width() > available_text_width:
                    shortened = title_text
                    while shortened and font_xs.size(shortened + "..")[0] > available_text_width:
                        shortened = shortened[:-1]
                    title_surface = font_xs.render(shortened + "..", True, COLOR_TEXT_WHITE)
                screen.blit(title_surface, (content_x + pill_width + 12, title_y + 4))

                if grant_button:
                    grant_hovered = grant_button.collidepoint(mouse_pos)
                    pygame.draw.rect(
                        screen,
                        (35, 75, 45) if grant_hovered else (25, 55, 35),
                        grant_button,
                        border_radius=3,
                    )
                    pygame.draw.rect(screen, COLOR_TEXT_GREEN, grant_button, 1, border_radius=3)
                    grant_label = font_xs.render("Grant", True, COLOR_TEXT_WHITE)
                    screen.blit(
                        grant_label,
                        (grant_button.centerx - grant_label.get_width() // 2, grant_button.y + 2),
                    )
                    if mouse_clicked and grant_hovered:
                        state.title_grant_target_title_id = held_title.id

            total_provs = len(prov_keys)
            screen.blit(font_xs.render(f"Demesne Territories ({total_provs} Provinces):", True, (200, 220, 245)), (25, 492))

            per_page = 2
            max_pages = max(1, (total_provs + per_page - 1) // per_page)
            state.demesne_page = max(0, min(state.demesne_page, max_pages - 1))

            start_i = state.demesne_page * per_page
            cur_pkeys = prov_keys[start_i:start_i + per_page]

            fy = 508
            for pid in cur_pkeys:
                p_data = prov_dict[pid]
                p_info = PROVINCES.get(pid, {})
                p_name = p_info.get("name", pid).split()[0]

                p_card = pygame.Rect(content_x, fy, content_w, 52)
                is_p_hov = p_card.collidepoint(mouse_pos)
                is_active_prov = (state.selected_province == pid)

                bg_c = (60, 50, 24) if is_active_prov else ((50, 60, 78) if is_p_hov else (34, 40, 52))
                border_c = COLOR_GOLD if (is_p_hov or is_active_prov) else (80, 140, 220)

                pygame.draw.rect(screen, bg_c, p_card, border_radius=4)
                pygame.draw.rect(screen, border_c, p_card, 1, border_radius=4)

                screen.blit(font_sm.render(f"◆ {p_name}", True, COLOR_GOLD), (34, fy + 4))
                p_h_cnt = len(p_data["holdings"])
                screen.blit(font_xs.render(f"Holdings: {p_h_cnt}", True, (200, 225, 255)), (110, fy + 6))

                # Province Financials & Garrison
                p_fin_str = f"Net: +{fmt_gold(p_data['net_income'])}g/m  •  🛡️ {p_data['total_garrison']} Gar  •  ⚔️ +{p_data['total_recruits']}/m"
                screen.blit(font_xs.render(p_fin_str, True, (180, 240, 190)), (34, fy + 22))

                # Province Buildings
                pb_items = [f"{cnt}x {bname}" for bname, cnt in p_data["building_counts"].items()]
                pb_str = ", ".join(pb_items)
                if len(pb_str) > 36: pb_str = pb_str[:34] + ".."
                screen.blit(font_xs.render(f"🏛️ {pb_str}", True, (230, 215, 170)), (34, fy + 36))

                view_btn = pygame.Rect(content_x + content_w - 60, fy + 14, 52, 22)
                is_vb_hov = view_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 65, 95) if is_vb_hov else (28, 45, 68), view_btn, border_radius=3)
                pygame.draw.rect(screen, COLOR_GOLD if is_vb_hov else (70, 120, 180), view_btn, 1, border_radius=3)
                v_lbl = font_xs.render("View ›", True, COLOR_GOLD if is_vb_hov else COLOR_TEXT_WHITE)
                screen.blit(v_lbl, (view_btn.x + (view_btn.w - v_lbl.get_width()) // 2, fy + 16))

                if mouse_clicked and (is_p_hov or is_vb_hov):
                    state.demesne_selected_province = pid
                    state.demesne_page = 0
                    state.selected_province = pid
                    state.logs.append(f"Viewing demesne holdings in {p_name}.")

                fy += 56

            if not prov_keys:
                screen.blit(font_sm.render("No direct demesne holdings held.", True, COLOR_TEXT_MUTED), (25, 430))

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
        # LEVEL 2: DETAILED HOLDINGS & BUILDINGS INSIDE SELECTED PROVINCE
        # -------------------------------------------------------------
        else:
            sel_pid = state.demesne_selected_province
            p_data = prov_dict.get(sel_pid, {"holdings": []})
            p_holdings = p_data["holdings"]
            p_info = PROVINCES.get(sel_pid, {})
            p_name = p_info.get("name", sel_pid).split()[0]

            # Back Button & Header
            back_btn = pygame.Rect(25, 400, 105, 24)
            is_back_hov = back_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (45, 65, 90) if is_back_hov else (30, 42, 60), back_btn, border_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD if is_back_hov else (80, 140, 220), back_btn, 1, border_radius=4)
            screen.blit(font_xs.render("◄ ALL PROVS", True, COLOR_GOLD if is_back_hov else COLOR_TEXT_WHITE), (33, 405))

            header_lbl = font_sm.render(f"◆ {p_name} ({len(p_holdings)} Holdings)", True, COLOR_GOLD)
            screen.blit(header_lbl, (140, 404))

            if mouse_clicked and is_back_hov:
                state.demesne_selected_province = None
                state.demesne_page = 0

            per_page = 4
            max_pages = max(1, (len(p_holdings) + per_page - 1) // per_page)
            state.demesne_page = max(0, min(state.demesne_page, max_pages - 1))

            start_i = state.demesne_page * per_page
            cur_holdings = p_holdings[start_i:start_i + per_page]

            fy = 430
            for h in cur_holdings:
                h_card = pygame.Rect(content_x, fy, content_w, 50)
                is_hc_hov = h_card.collidepoint(mouse_pos)
                is_sel_t = (state.selected_settlement == h["coord"])

                bg_col = (70, 55, 20) if is_sel_t else ((50, 60, 78) if is_hc_hov else (34, 40, 52))
                pygame.draw.rect(screen, bg_col, h_card, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if is_sel_t else (80, 140, 220), h_card, 1, border_radius=4)

                # Line 1: Type Badge + Holding Name
                stype = h["type"]
                badge_lbl = "🏛 CITY" if stype == "city" else ("🏰 FORT" if stype == "fort" else "⚔ BARRACKS")
                b_badge_w, _ = draw_feudal_pill(screen, font_xs, badge_lbl, 34, fy + 4)

                h_disp_name = h["name"]
                if len(h_disp_name) > 22: h_disp_name = h_disp_name[:20] + ".."
                screen.blit(font_xs.render(h_disp_name, True, COLOR_TEXT_WHITE), (34 + b_badge_w + 6, fy + 5))

                coord_txt = f"({h['coord'][0]},{h['coord'][1]})"
                screen.blit(font_xs.render(coord_txt, True, COLOR_TEXT_MUTED), (content_x + content_w - font_xs.size(coord_txt)[0] - 6, fy + 5))

                # Line 2: Income / Upkeep / Net
                h_fin_txt = f"💰 Income: +{fmt_gold(h['income'])}g  •  Expense: -{fmt_gold(h['upkeep'])}g  •  Net: +{fmt_gold(h['net'])}g/m"
                screen.blit(font_xs.render(h_fin_txt, True, (160, 240, 180) if h['net'] >= 0 else (255, 170, 170)), (34, fy + 20))

                # Line 3: Garrison Defenders & Recruits
                h_mil_txt = f"🛡️ Garrison: {h['garrison']} Defenders  •  ⚔️ Recruits: +{h['recruits']} Men/mo"
                screen.blit(font_xs.render(h_mil_txt, True, (210, 230, 255)), (34, fy + 34))

                if mouse_clicked and is_hc_hov:
                    state.selected_province = h["province"]
                    state.selected_settlement = h["coord"]
                    state.selected_army_id = None
                    state.logs.append(f"Inspecting {h['name']} ({h['title']}) at {h['coord']}.")

                fy += 54

            if not p_holdings:
                screen.blit(font_sm.render(f"No demesne holdings in {p_name}.", True, COLOR_TEXT_MUTED), (25, 450))

            # Bottom Pagination Controls for Holdings List
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
        if not hasattr(state, "title_grant_target_title_id"):
            state.title_grant_target_title_id = None
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
        # TITLE GRANT SELECTOR: BESTOW FEUDAL TITLE UPON VASSAL (CK2)
        # -------------------------------------------------------------
        if getattr(state, "title_grant_target_title_id", None) is not None:
            render_title_grant_selector(
                screen, state, mouse_pos, mouse_clicked, fonts, content_x, content_w
            )

        # -------------------------------------------------------------
        # LEVEL 3: INSPECTING A COUNT'S DIRECT SUB-VASSALS (RETINUE)
        # -------------------------------------------------------------
        elif state.vassal_inspecting_liege_id is not None:
            liege_id = state.vassal_inspecting_liege_id
            liege_v = next((v for plist in state.vassals.values() for v in plist if v.get("id") == liege_id), None)
            l_name = state.get_character_clean_name(liege_v["name"]).split()[0] if liege_v else "Count"
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
                card_h = 62
                b_card = pygame.Rect(content_x, vy, content_w, card_h)
                is_bc_hov = b_card.collidepoint(mouse_pos)

                # Highlight baron territory on map when hovering this card
                if is_bc_hov:
                    state.hovered_vassal_tiles = set(tuple(t) for t in b_data.get("tiles", []))

                b_titles = state.get_held_titles(b_data["id"])
                b_subs = len(b_data.get("sub_vassals", []))

                pygame.draw.rect(screen, (50, 60, 78) if is_bc_hov else (34, 40, 52), b_card, border_radius=4)
                pygame.draw.rect(screen, (140, 180, 220) if is_bc_hov else COLOR_PANEL_BORDER, b_card, 1, border_radius=4)

                # 1. Rank pill & Clean name
                pw, b_col = draw_feudal_pill(screen, font_xs, b_data.get("rank", "baron"), 32, vy + 4)
                b_clean = state.get_character_clean_name(b_data["name"])
                max_l3_chars = 14 if b_subs > 0 else 18
                b_disp = b_clean[:max_l3_chars - 2] + ".." if len(b_clean) > max_l3_chars else b_clean
                screen.blit(font_xs.render(b_disp, True, COLOR_TEXT_WHITE), (32 + pw + 6, vy + 5))

                # Action buttons
                # [ +50g 🎁 ]
                gift_btn = pygame.Rect(content_x + content_w - 44, vy + 4, 40, 18)
                is_g_hov = gift_btn.collidepoint(mouse_pos)
                can_gift = (state.player["gold"] >= 50)
                g_bg = (30, 70, 40) if (is_g_hov and can_gift) else ((20, 50, 30) if can_gift else (40, 42, 48))
                g_bd = COLOR_TEXT_GREEN if can_gift else (80, 85, 95)
                pygame.draw.rect(screen, g_bg, gift_btn, border_radius=3)
                pygame.draw.rect(screen, g_bd, gift_btn, 1, border_radius=3)
                g_lbl = font_xs.render("+50g", True, COLOR_TEXT_WHITE if can_gift else COLOR_TEXT_MUTED)
                screen.blit(g_lbl, (gift_btn.x + (gift_btn.w - g_lbl.get_width()) // 2, vy + 2))

                # [ ⤺ Revoke ] (Revoke Barony to King)
                rev_btn = None
                is_rev_hov = False
                if b_titles:
                    rev_btn = pygame.Rect(content_x + content_w - 96, vy + 4, 48, 18)
                    is_rev_hov = rev_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (70, 36, 56) if is_rev_hov else (48, 25, 38), rev_btn, border_radius=3)
                    pygame.draw.rect(screen, (220, 100, 180), rev_btn, 1, border_radius=3)
                    r_lbl = font_xs.render("⤺ Revoke", True, (255, 215, 240))
                    screen.blit(r_lbl, (rev_btn.x + (rev_btn.w - r_lbl.get_width()) // 2, vy + 2))

                # [ ↑ Direct ]
                dir_x = content_x + content_w - (146 if b_titles else 94)
                dir_btn = pygame.Rect(dir_x, vy + 4, 46, 18)
                is_dir_hov = dir_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (38, 70, 50) if is_dir_hov else (26, 50, 36), dir_btn, border_radius=3)
                pygame.draw.rect(screen, (110, 210, 140) if is_dir_hov else (70, 140, 95), dir_btn, 1, border_radius=3)
                screen.blit(font_xs.render("↑ Direct", True, COLOR_TEXT_WHITE if is_dir_hov else (190, 240, 205)), (dir_btn.x + (dir_btn.w - font_xs.size("↑ Direct")[0]) // 2, vy + 2))

                # 2. DAFTAR TITLE YANG DIMILIKI KARAKTER
                if b_titles:
                    t_str = ", ".join(t.name for t in b_titles)
                    if len(t_str) > 34: t_str = t_str[:32] + ".."
                    screen.blit(font_xs.render(f"Held: {t_str}", True, COLOR_GOLD), (32, vy + 23))
                else:
                    screen.blit(font_xs.render("Held: None (Unlanded Courtier)", True, COLOR_TEXT_MUTED), (32, vy + 23))

                # 3. Fief Seat & Liege & Taxes
                st = get_vassal_landed_status(state, b_data, b_data.get("province"))
                f_name = b_data.get("city_name") or "Holding"
                if len(f_name) > 22: f_name = f_name[:20] + ".."
                screen.blit(font_xs.render(f"Fief: {f_name} • Liege: {l_name} • Tax to {l_name}: +{fmt_gold(st['tax_paid'])}g/m", True, (210, 220, 235)), (32, vy + 41))

                if mouse_clicked:
                    if is_rev_hov and rev_btn:
                        state.revoke_title(b_titles[0].id)
                    elif is_dir_hov:
                        state.retract_to_direct_vassal(b_data["id"])
                    elif is_g_hov:
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

                vy += (card_h + 4)

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
        # LIEGE SELECTOR: DYNAMIC VASSAL TRANSFER & FEUDAL HIERARCHY
        # -------------------------------------------------------------
        elif getattr(state, "vassal_subordinate_target_id", None):
            all_v = [v for plist in state.vassals.values() for v in plist]
            t_v = next((v for v in all_v if v.get("id") == state.vassal_subordinate_target_id), None)
            t_name = t_v["name"] if t_v else "Vassal"
            t_rank = t_v.get("rank", "count") if t_v else "count"
            t_prov = PROVINCES.get(t_v.get("province", ""), {}).get("name", "").split()[0] if t_v else ""

            # Header
            if t_rank == "count":
                hdr_text = f"⚜ Transfer / Assign Count {t_name}"
                sub_text = "Place Count under a Duke (frees limit), or keep Direct:"
            else:
                hdr_text = f"🏰 Transfer Baron {t_name}"
                sub_text = "Place Baron under a Count/Duke, or keep Direct Crown Baron:"

            screen.blit(font_md.render(hdr_text, True, COLOR_GOLD), (25, 298))
            screen.blit(font_xs.render(sub_text, True, (255, 200, 140)), (25, 320))
            if t_rank == "count":
                screen.blit(font_xs.render("Subordinate Counts under a Duke DO NOT count against your 5 Vassal Limit!", True, (150, 230, 170)), (25, 336))
            else:
                screen.blit(font_xs.render("Barons never count towards the Vassal Limit!", True, (150, 230, 170)), (25, 336))

            vy = 356

            # ---------------------------------------------------------
            # OPTION 1: DIRECTLY UNDER THE SOVEREIGN RULER
            # ---------------------------------------------------------
            king_card = pygame.Rect(content_x, vy, content_w, 54)
            is_k_hov = king_card.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (52, 44, 24) if is_k_hov else (38, 32, 18), king_card, border_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD if is_k_hov else (180, 140, 50), king_card, 1, border_radius=4)

            screen.blit(font_sm.render(f"👑 Direct Under {get_display_name(state.player_id)}", True, COLOR_GOLD), (34, vy + 4))
            desc_k = "Direct Count (Consumes 1 Limit)" if t_rank == "count" else "Direct Crown Baron • 0 Limit Cost • Direct Tax to King"
            screen.blit(font_xs.render(desc_k, True, (230, 240, 200)), (34, vy + 28))

            k_btn = pygame.Rect(content_x + content_w - 110, vy + 14, 100, 26)
            is_kb_hov = k_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (40, 85, 55) if is_kb_hov else (28, 65, 40), k_btn, border_radius=3)
            pygame.draw.rect(screen, COLOR_TEXT_GREEN, k_btn, 1, border_radius=3)
            kb_txt = font_xs.render("Make Direct", True, COLOR_TEXT_WHITE)
            screen.blit(kb_txt, (k_btn.x + (k_btn.w - kb_txt.get_width()) // 2, k_btn.y + 5))

            if mouse_clicked and (is_k_hov or is_kb_hov):
                state.retract_to_direct_vassal(state.vassal_subordinate_target_id)
                state.vassal_subordinate_target_id = None

            vy += 60

            # ---------------------------------------------------------
            # OPTION 2..N: SERAHKAN KE DUKE ATAU COUNT LAIN
            # ---------------------------------------------------------
            # If target is Count: can be placed under any Duke!
            # If target is Baron: can be placed under any Count or Duke!
            if t_rank == "count":
                avail_lieges = [
                    v for plist in state.vassals.values() for v in plist 
                    if v.get("rank") == "duke" and v.get("id") != state.vassal_subordinate_target_id
                    and PROVINCES.get(v.get("province"), {}).get("owner") == state.player_id
                ]
            else:
                avail_lieges = [
                    v for plist in state.vassals.values() for v in plist 
                    if v.get("rank") in ("count", "duke") and v.get("id") != state.vassal_subordinate_target_id
                    and PROVINCES.get(v.get("province"), {}).get("owner") == state.player_id
                ]

            if not avail_lieges and t_rank == "count":
                screen.blit(font_sm.render("No Dukes currently in the realm to receive Counts.", True, COLOR_TEXT_MUTED), (content_x + 10, vy + 10))
                screen.blit(font_xs.render("Promote a Count to Duke first, or demote to Baron below.", True, (200, 210, 225)), (content_x + 10, vy + 32))
                vy += 54

            for cv in avail_lieges[:4]:
                cp_name = PROVINCES.get(cv.get("province", ""), {}).get("name", "").split()[0]
                c_subs = len(cv.get("sub_vassals", []))
                f_seat = (cv.get("city_name") or "Fortress").replace("Fortress", "Castle")
                if len(f_seat) > 20: f_seat = f_seat[:18] + ".."

                c_card = pygame.Rect(content_x, vy, content_w, 52)
                is_c_hov = c_card.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (48, 56, 74) if is_c_hov else (32, 38, 52), c_card, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if is_c_hov else (70, 110, 170), c_card, 1, border_radius=4)

                screen.blit(font_sm.render(f"◆ {cp_name}", True, COLOR_GOLD), (34, vy + 4))
                p_w = font_sm.size(f"◆ {cp_name}")[0]
                pw, _ = draw_feudal_pill(screen, font_xs, cv.get("rank", "count"), 34 + p_w + 10, vy + 4)
                c_name = cv["name"]
                if len(c_name) > 18: c_name = c_name[:16] + ".."
                screen.blit(font_xs.render(c_name, True, COLOR_TEXT_WHITE), (34 + p_w + 10 + pw + 6, vy + 5))

                screen.blit(font_xs.render(f"Seat: {f_seat} • 👥 Retinue: {c_subs} Vassals", True, (180, 215, 255)), (34, vy + 28))

                sel_btn = pygame.Rect(content_x + content_w - 110, vy + 13, 100, 26)
                is_sel_hov = sel_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (35, 65, 95) if is_sel_hov else (25, 48, 70), sel_btn, border_radius=3)
                pygame.draw.rect(screen, (100, 180, 255), sel_btn, 1, border_radius=3)
                btn_lbl = "Assign to Duke" if cv.get("rank") == "duke" else "Assign to Count"
                s_txt = font_xs.render(btn_lbl, True, COLOR_TEXT_WHITE)
                screen.blit(s_txt, (sel_btn.x + (sel_btn.w - s_txt.get_width()) // 2, sel_btn.y + 5))

                if mouse_clicked and (is_c_hov or is_sel_hov):
                    state.transfer_vassal_to_liege(state.vassal_subordinate_target_id, cv["id"])
                    state.vassal_subordinate_target_id = None
                    break

                vy += 56

            # Demote to Baron option if target is Count
            if t_rank == "count":
                d_baron_btn = pygame.Rect(content_x, 608, content_w, 28)
                is_db_hov = d_baron_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (65, 45, 30) if is_db_hov else (45, 32, 22), d_baron_btn, border_radius=4)
                pygame.draw.rect(screen, (220, 160, 80), d_baron_btn, 1, border_radius=4)
                db_txt = font_xs.render("⬇ Demote Count to Baron Instead (Strip County Title)", True, COLOR_GOLD if is_db_hov else COLOR_TEXT_WHITE)
                screen.blit(db_txt, (d_baron_btn.x + (d_baron_btn.w - db_txt.get_width()) // 2, d_baron_btn.y + 6))
                if mouse_clicked and is_db_hov:
                    state.demote_vassal(state.vassal_subordinate_target_id)
                    state.vassal_subordinate_target_id = None

            # Cancel Button at bottom
            cancel_btn = pygame.Rect(content_x, 645, content_w, 28)
            is_canc_hov = cancel_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (75, 35, 35) if is_canc_hov else (55, 25, 25), cancel_btn, border_radius=4)
            pygame.draw.rect(screen, (220, 80, 80), cancel_btn, 1, border_radius=4)
            c_lbl = font_xs.render("✖ CANCEL DEMOTION", True, (255, 210, 210))
            screen.blit(c_lbl, (cancel_btn.x + (cancel_btn.w - c_lbl.get_width()) // 2, 651))

            if mouse_clicked and is_canc_hov:
                state.vassal_subordinate_target_id = None

        # -------------------------------------------------------------
        # LEVEL 1: LIST OF PROVINCES IN THE REALM & DIRECT VASSALS
        # -------------------------------------------------------------
        elif state.vassal_selected_province is None:
            total_provs = len(vassal_provinces)
            header_lbl = font_md.render("Realm Feudal Vassals", True, COLOR_GOLD)
            screen.blit(header_lbl, (25, 298))

            # Vassal Limit Badge (CK2 Style)
            limit_col = COLOR_TEXT_RED if is_over_limit else COLOR_TEXT_GREEN
            limit_txt = f"Direct: {direct_vassal_count}/{vassal_limit}"
            if is_over_limit: limit_txt += f" (-{limit_penalty}%)"
            lim_lbl = font_xs.render(limit_txt, True, limit_col)
            screen.blit(lim_lbl, (content_x + content_w - lim_lbl.get_width() - 4, 302))

            screen.blit(
                font_xs.render(f"Realm Provinces ({total_provs}):", True, (210, 225, 245)),
                (25, 322),
            )
            vy = 340

            per_page = 4
            max_pages = max(1, (total_provs + per_page - 1) // per_page)
            state.vassal_page = max(0, min(getattr(state, "vassal_page", 0), max_pages - 1))

            start_i = state.vassal_page * per_page
            cur_page_provs = vassal_provinces[start_i:start_i + per_page]
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

                # Highlight whole province territory on map when hovering province card
                if is_p_hov:
                    p_coords = PROVINCES.get(pid, {}).get('coords', [])
                    state.hovered_vassal_tiles = set(tuple(c) for c in p_coords)

                bg_c = (60, 50, 24) if is_active_prov else ((50, 60, 78) if is_p_hov else (34, 40, 52))
                border_c = COLOR_GOLD if (is_p_hov or is_active_prov) else (80, 140, 220)

                pygame.draw.rect(screen, bg_c, p_card, border_radius=4)
                pygame.draw.rect(screen, border_c, p_card, 1, border_radius=4)

                screen.blit(font_sm.render(f"◆ {p_name}", True, COLOR_GOLD), (34, vy + 4))
                p_name_w = font_sm.size(f"◆ {p_name}")[0]
                pw, dv_col = draw_feudal_pill(screen, font_xs, dv_rank, 34 + p_name_w + 10, vy + 4)
                
                clean_name = state.get_character_clean_name(dv_name)
                dv_name_disp = clean_name
                if len(dv_name_disp) > 15: dv_name_disp = dv_name_disp[:13] + ".."
                screen.blit(font_xs.render(dv_name_disp, True, COLOR_TEXT_WHITE), (34 + p_name_w + 10 + pw + 6, vy + 5))

                fief_seat = (direct_v.get("city_name") if direct_v else None) or "Capital Citadel"
                if len(fief_seat) > 22: fief_seat = fief_seat[:20] + ".."
                desc_str = f"Seat: {fief_seat} • 👥 {dv_subs} Barons • Fyrd: +{total_levy} • Tax: +{fmt_gold(total_tax)}g/m"
                screen.blit(font_xs.render(desc_str, True, (210, 230, 255)), (34, vy + 28))

                # Buttons on card: [ ⤺ Revoke ] (if holds titles) and [ View › ]
                dv_titles = state.get_held_titles(direct_v["id"]) if direct_v else []
                rev_btn = None
                is_rev_hov = False

                if direct_v and dv_titles:
                    # [ ⤺ Revoke ] button (Revokes Duchy/County directly into King's Crown Demesne)
                    rev_btn = pygame.Rect(content_x + content_w - 130, vy + 14, 58, 24)
                    is_rev_hov = rev_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (70, 36, 56) if is_rev_hov else (48, 25, 38), rev_btn, border_radius=3)
                    pygame.draw.rect(screen, (220, 100, 180), rev_btn, 1, border_radius=3)
                    r_lbl = font_xs.render("⤺ Revoke", True, (255, 215, 240))
                    screen.blit(r_lbl, (rev_btn.x + (rev_btn.w - r_lbl.get_width()) // 2, rev_btn.y + 4))

                view_btn = pygame.Rect(content_x + content_w - 65, vy + 14, 58, 24)
                is_v_hov = view_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 65, 95) if is_v_hov else (28, 45, 68), view_btn, border_radius=3)
                pygame.draw.rect(screen, COLOR_GOLD if is_v_hov else (70, 120, 180), view_btn, 1, border_radius=3)
                v_lbl = font_xs.render("View ›", True, COLOR_GOLD if is_v_hov else COLOR_TEXT_WHITE)
                screen.blit(v_lbl, (view_btn.x + (view_btn.w - v_lbl.get_width()) // 2, view_btn.y + 4))

                if mouse_clicked:
                    if rev_btn and is_rev_hov and dv_titles:
                        state.revoke_title(dv_titles[0].id)
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
                card_h = 62
                v_card = pygame.Rect(content_x, vy, content_w, card_h)
                is_vc_hov = v_card.collidepoint(mouse_pos)

                # Highlight vassal territory on map when hovering this card
                if is_vc_hov:
                    vtiles = set(tuple(t) for t in v_data.get("tiles", []))
                    # For Counts, also include sub-vassal tiles
                    for sv_id in v_data.get("sub_vassals", []):
                        sv = next((v for plist in state.vassals.values() for v in plist if v.get("id") == sv_id), None)
                        if sv:
                            vtiles.update(tuple(t) for t in sv.get("tiles", []))
                    state.hovered_vassal_tiles = vtiles

                v_rank = v_data.get("rank", "baron")
                n_subs = len(v_data.get("sub_vassals", []))
                v_titles = state.get_held_titles(v_data["id"])

                # Card styling (Direct Vassal has richer golden tint)
                if is_direct:
                    c_bg = (54, 58, 76) if is_vc_hov else (38, 44, 58)
                    c_bd = COLOR_GOLD if is_vc_hov else (140, 180, 230)
                else:
                    c_bg = (48, 56, 72) if is_vc_hov else (34, 40, 52)
                    c_bd = (140, 180, 220) if is_vc_hov else COLOR_PANEL_BORDER

                pygame.draw.rect(screen, c_bg, v_card, border_radius=4)
                pygame.draw.rect(screen, c_bd, v_card, 1, border_radius=4)

                # 1. Vassal Name & Feudal Rank Pill
                pw, rk_col = draw_feudal_pill(screen, font_xs, v_rank, 32, vy + 4)
                v_clean = state.get_character_clean_name(v_data["name"])
                max_name_len = 16 if len(v_titles) > 0 else 22
                v_disp = v_clean[:max_name_len - 2] + ".." if len(v_clean) > max_name_len else v_clean
                screen.blit(font_xs.render(v_disp, True, COLOR_TEXT_WHITE), (32 + pw + 6, vy + 5))
                
                # Rename Noble Button
                rn_v_btn = pygame.Rect(32 + pw + 6 + font_xs.size(v_disp)[0] + 4, vy + 4, 18, 16)
                is_rnv_hov = rn_v_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (50, 60, 80) if is_rnv_hov else (30, 36, 48), rn_v_btn, border_radius=3)
                pygame.draw.rect(screen, (100, 150, 220), rn_v_btn, 1, border_radius=3)
                screen.blit(font_micro.render("✎", True, (210, 230, 255)), (rn_v_btn.x + 4, rn_v_btn.y + 1))
                if mouse_clicked and is_rnv_hov:
                    state.open_rename_modal("character", v_data["id"], v_data["name"])

                # Action Buttons Row
                # [ +50g 🎁 ]
                gift_btn = pygame.Rect(content_x + content_w - 44, vy + 4, 40, 18)
                is_g_hov = gift_btn.collidepoint(mouse_pos)
                can_gift = (state.player["gold"] >= 50)
                g_bg = (30, 70, 40) if (is_g_hov and can_gift) else ((20, 50, 30) if can_gift else (40, 42, 48))
                g_bd = COLOR_TEXT_GREEN if can_gift else (80, 85, 95)
                pygame.draw.rect(screen, g_bg, gift_btn, border_radius=3)
                pygame.draw.rect(screen, g_bd, gift_btn, 1, border_radius=3)
                g_lbl = font_xs.render("+50g", True, COLOR_TEXT_WHITE if can_gift else COLOR_TEXT_MUTED)
                screen.blit(g_lbl, (gift_btn.x + (gift_btn.w - g_lbl.get_width()) // 2, vy + 2))

                # [ ⤺ Revoke ] (Revokes primary title directly into King's demesne)
                rev_btn = None
                is_rev_hov = False
                if v_titles:
                    rev_btn = pygame.Rect(content_x + content_w - 96, vy + 4, 48, 18)
                    is_rev_hov = rev_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (70, 36, 56) if is_rev_hov else (48, 25, 38), rev_btn, border_radius=3)
                    pygame.draw.rect(screen, (220, 100, 180), rev_btn, 1, border_radius=3)
                    r_lbl = font_xs.render("⤺ Revoke", True, (255, 215, 240))
                    screen.blit(r_lbl, (rev_btn.x + (rev_btn.w - r_lbl.get_width()) // 2, vy + 2))

                # [ ⬇ Sub ] / [ ↑ Direct ] (Fealty reassignment)
                dir_btn = None
                is_dir_hov = False
                dir_lbl = "⬇ Sub" if is_direct else "↑ Direct"
                dir_x = content_x + content_w - (146 if v_titles else 94)
                dir_btn = pygame.Rect(dir_x, vy + 4, 46, 18)
                is_dir_hov = dir_btn.collidepoint(mouse_pos)
                d_bg = (38, 70, 50) if is_dir_hov else (26, 50, 36) if not is_direct else ((70, 45, 45) if is_dir_hov else (50, 30, 30))
                d_bd = (110, 210, 140) if is_dir_hov else (70, 140, 95) if not is_direct else ((210, 110, 110) if is_dir_hov else (150, 75, 75))
                pygame.draw.rect(screen, d_bg, dir_btn, border_radius=3)
                pygame.draw.rect(screen, d_bd, dir_btn, 1, border_radius=3)
                d_txt = font_xs.render(dir_lbl, True, COLOR_TEXT_WHITE)
                screen.blit(d_txt, (dir_btn.x + (dir_btn.w - d_txt.get_width()) // 2, vy + 2))

                # [ 👥 Vassals (N) › ] if Duke or Count
                sub_btn = None
                is_sub_hov = False
                if v_rank in ("duke", "count"):
                    sub_x = dir_x - 72
                    sub_btn = pygame.Rect(sub_x, vy + 4, 68, 18)
                    is_sub_hov = sub_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (45, 75, 110) if is_sub_hov else (30, 50, 75), sub_btn, border_radius=3)
                    pygame.draw.rect(screen, (120, 190, 255) if is_sub_hov else (80, 130, 180), sub_btn, 1, border_radius=3)
                    s_lbl = font_xs.render(f"👥 Vassals ({n_subs})", True, COLOR_TEXT_WHITE if is_sub_hov else (200, 230, 255))
                    screen.blit(s_lbl, (sub_btn.x + (sub_btn.w - s_lbl.get_width()) // 2, vy + 2))

                # 2. DAFTAR TITLE YANG DIMILIKI KARAKTER (HELD TITLES)
                if v_titles:
                    t_str = ", ".join(t.name for t in v_titles)
                    if len(t_str) > 36: t_str = t_str[:34] + ".."
                    screen.blit(font_xs.render(f"Held Titles: {t_str}", True, COLOR_GOLD), (32, vy + 23))
                else:
                    screen.blit(font_xs.render("Held Titles: None (Unlanded Courtier)", True, COLOR_TEXT_MUTED), (32, vy + 23))

                # 3. Fief Seat & Liege & Taxes
                st = get_vassal_landed_status(state, v_data, sel_pid)
                f_seat = v_data.get("city_name") or "Landed Holding"
                if len(f_seat) > 20: f_seat = f_seat[:18] + ".."
                l_short = get_vassal_liege_name(state, v_data)

                if is_direct:
                    screen.blit(font_xs.render(f"Fief: {f_seat} • Tax to King: +{fmt_gold(st['tax_paid'])}g/m", True, (210, 225, 245)), (32, vy + 41))
                else:
                    screen.blit(font_xs.render(f"Fief: {f_seat} • Liege: {l_short} • Tax to {l_short}: +{fmt_gold(st['tax_paid'])}g/m", True, (200, 215, 235)), (32, vy + 41))

                # Click interactions
                if mouse_clicked:
                    if is_sub_hov and sub_btn:
                        state.vassal_inspecting_liege_id = v_data["id"]
                        state.vassal_page = 0
                        state.logs.append(f"Inspecting vassals under {v_data['name']}.")
                    elif is_rev_hov and rev_btn:
                        state.revoke_title(v_titles[0].id)
                    elif is_dir_hov and dir_btn:
                        if is_direct:
                            state.vassal_subordinate_target_id = v_data["id"]
                            state.logs.append(f"Selecting new liege for {v_data['name']}...")
                        else:
                            state.retract_to_direct_vassal(v_data["id"])
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
                    v_short = state.get_character_clean_name(v_item["name"]).split()[0]
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
                screen.blit(font_xs.render("• No crown holdings currently generate rent.", True, (160, 225, 180)), (32, 658))
    
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

        rivals = [cid for cid in state.get_active_rulers(include_player=True) if cid != state.player_id]
        ai_targets = [(cid, get_realm_name(cid, get_display_name(cid))) for cid in rivals]
        curr_target = getattr(state, "active_diplomacy_target", None)
        if curr_target not in [t[0] for t in ai_targets]:
            curr_target = ai_targets[0][0] if ai_targets else state.player_id
            state.active_diplomacy_target = curr_target

        pill_w = (content_w - 6 * max(0, len(ai_targets) - 1)) // max(1, len(ai_targets)) if ai_targets else content_w
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
    
