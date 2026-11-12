"""
Top HUD / Resource Bar UI Component (Full HD 1920x1080)
"""
import pygame
from game.config import (
    WINDOW_WIDTH, COLOR_PANEL_BG, COLOR_PANEL_BORDER, COLOR_GOLD,
    COLOR_TEXT_WHITE, COLOR_TEXT_MUTED, COLOR_TEXT_GREEN, COLOR_BUTTON_NORMAL,
    COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE, COLOR_PRESTIGE, COLOR_PIETY
)
from game.systems.economy import fmt_gold
from game.data.scenario import get_scenario

def render_header(screen, state, mouse_pos, mouse_clicked, is_popup_active, fonts, icons, on_reset=None):
    font_xs = fonts["xs"]
    font_sm = fonts["sm"]
    font_md = fonts["md"]
    font_lg = fonts["lg"]

    icon_gold = icons.get("gold")
    icon_prestige = icons.get("prestige")
    icon_troops = icons.get("troops")
    icon_piety = icons.get("piety")

    # ---------------------------------------------------------
    # 1. TOP HEADER BAR (Full HD 1920x54)
    # ---------------------------------------------------------
    pygame.draw.rect(screen, COLOR_PANEL_BG, (0, 0, WINDOW_WIDTH, 54))
    pygame.draw.line(screen, COLOR_PANEL_BORDER, (0, 54), (WINDOW_WIDTH, 54), 2)
    
    t_surf = font_lg.render(get_scenario().get("title", "CK2-Lite"), True, COLOR_GOLD)
    screen.blit(t_surf, (24, 15))
    
    # Calendar Date Pill Badge
    date_rect = pygame.Rect(315, 10, 165, 34)
    pygame.draw.rect(screen, (22, 26, 36), date_rect, border_radius=6)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, date_rect, 1, border_radius=6)
    date_str = f"{state.day:02d} {state.months[state.month - 1]} {state.year} AD"
    d_surf = font_md.render(date_str, True, COLOR_TEXT_WHITE)
    screen.blit(d_surf, (date_rect.x + (date_rect.w - d_surf.get_width()) // 2, date_rect.y + 6))
    
    # Speed Controls - 0: Pause | 1: Very Slow | 2: Slow | 3: Normal | 4: Fast | 5: Very Fast
    speed_texts  = ["||", "½x", "1x", "2x", "4x", "8x"]
    speed_colors = {
        0: (160, 160, 160),  # grey   - pause
        1: (100, 180, 255),  # blue   - very slow
        2: (100, 220, 180),  # teal   - slow
        3: COLOR_TEXT_GREEN, # green  - normal
        4: COLOR_GOLD,       # gold   - fast
        5: (235, 75, 75),    # red    - very fast
    }
    speed_start_x = 500
    for sp in range(6):
        btn_x = speed_start_x + (sp * 38)
        btn_rect = pygame.Rect(btn_x, 10, 34, 34)
        is_active = (state.speed == sp)
        b_col = COLOR_BUTTON_ACTIVE if is_active else (COLOR_BUTTON_HOVER if btn_rect.collidepoint(mouse_pos) else COLOR_BUTTON_NORMAL)
        pygame.draw.rect(screen, b_col, btn_rect, border_radius=4)
        border_col = speed_colors[sp] if is_active else COLOR_PANEL_BORDER
        pygame.draw.rect(screen, border_col, btn_rect, 1 if not is_active else 2, border_radius=4)
        lbl = font_xs.render(speed_texts[sp], True, speed_colors[sp] if is_active else COLOR_TEXT_MUTED)
        screen.blit(lbl, (btn_x + (34 - lbl.get_width()) // 2, 10 + (34 - lbl.get_height()) // 2))
        if mouse_clicked and btn_rect.collidepoint(mouse_pos):
            if is_popup_active:
                state.pre_popup_speed = sp
            else:
                state.speed = sp
    
    # Player Resources (Starting at x=770 with plenty of breathing room)
    field_men = state.get_field_troops(state.player_id)
    garrison_men = state.get_unraised_levies(state.player_id)
    
    stats = [
        (icon_gold, f"{fmt_gold(state.player['gold'])}", COLOR_GOLD, 770),
        (icon_prestige, f"{state.player['prestige']:,}", COLOR_PRESTIGE, 920),
        (icon_piety, f"{state.player.get('piety', 0):,}", COLOR_PIETY, 1070),
        (icon_troops, f"Field: {field_men:,}", COLOR_TEXT_GREEN if field_men > 0 else COLOR_TEXT_WHITE, 1220),
        (icon_troops, f"Garrison: {garrison_men:,}", COLOR_TEXT_MUTED, 1450)
    ]
    for icon, val_str, col, sx in stats:
        if icon:
            screen.blit(icon, (sx, 15))
        v_surf = font_md.render(val_str, True, col)
        screen.blit(v_surf, (sx + 28, 16))
    
    # RESET GAME BUTTON (Far right, comfortable margin)
    rst_btn = pygame.Rect(WINDOW_WIDTH - 145, 10, 120, 34)
    b_rst_hov = rst_btn.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (90, 30, 30) if b_rst_hov else (65, 25, 25), rst_btn, border_radius=5)
    pygame.draw.rect(screen, (220, 80, 80), rst_btn, 1, border_radius=5)
    rst_lbl = font_sm.render("RESET ↺", True, COLOR_TEXT_WHITE)
    screen.blit(rst_lbl, (rst_btn.x + (rst_btn.w - rst_lbl.get_width()) // 2, rst_btn.y + 7))
    if mouse_clicked and b_rst_hov:
        state.reset()
        if on_reset:
            on_reset()
