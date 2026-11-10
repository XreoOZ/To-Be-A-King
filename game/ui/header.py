"""
Top HUD / Resource Bar UI Component
"""
import pygame
from game.config import (
    WINDOW_WIDTH, COLOR_PANEL_BG, COLOR_PANEL_BORDER, COLOR_GOLD,
    COLOR_TEXT_WHITE, COLOR_TEXT_MUTED, COLOR_TEXT_GREEN, COLOR_BUTTON_NORMAL,
    COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE, COLOR_PRESTIGE, COLOR_PIETY
)
from game.data.provinces import reset_global_world_data
from game.core.state import GameState, setup_province_starter_cities

def render_header(screen, state, mouse_pos, mouse_clicked, is_popup_active, fonts, icons, on_reset=None):
    font_xs = fonts["xs"]
    font_sm = fonts["sm"]
    font_md = fonts["md"]
    font_lg = fonts["lg"]

    icon_gold = icons["gold"]
    icon_prestige = icons["prestige"]
    icon_troops = icons["troops"]
    icon_piety = icons["piety"]

    # ---------------------------------------------------------
    # 1. TOP HEADER BAR
    # ---------------------------------------------------------
    pygame.draw.rect(screen, COLOR_PANEL_BG, (0, 0, WINDOW_WIDTH, 52))
    pygame.draw.line(screen, COLOR_PANEL_BORDER, (0, 52), (WINDOW_WIDTH, 52), 2)
    
    t_surf = font_lg.render("CK2: THE WAR FOR BRITAIN", True, COLOR_GOLD)
    screen.blit(t_surf, (20, 12))
    
    # Calendar Date
    date_str = f"{state.day:02d} {state.months[state.month - 1]} {state.year} AD"
    d_surf = font_md.render(date_str, True, COLOR_TEXT_WHITE)
    screen.blit(d_surf, (340, 15))
    
    # Speed Controls — 0: Pause | 1: Very Slow | 2: Slow | 3: Normal | 4: Fast | 5: Very Fast
    speed_labels = {0: "||", 1: ">>", 2: ">>", 3: ">", 4: ">>", 5: ">>>"}
    speed_texts  = ["‖", "½×", "1×", "2×", "4×", "8×"]
    speed_colors = {
        0: (160, 160, 160),  # grey  – pause
        1: (100, 180, 255),  # blue  – very slow
        2: (100, 220, 180),  # teal  – slow
        3: COLOR_TEXT_GREEN, # green – normal
        4: COLOR_GOLD,       # gold  – fast
        5: (235, 75, 75),    # red   – very fast
    }
    for sp in range(6):
        btn_x = 460 + (sp * 36)
        btn_rect = pygame.Rect(btn_x, 8, 32, 32)
        is_active = (state.speed == sp)
        b_col = COLOR_BUTTON_ACTIVE if is_active else (COLOR_BUTTON_HOVER if btn_rect.collidepoint(mouse_pos) else COLOR_BUTTON_NORMAL)
        pygame.draw.rect(screen, b_col, btn_rect, border_radius=4)
        border_col = speed_colors[sp] if is_active else COLOR_PANEL_BORDER
        pygame.draw.rect(screen, border_col, btn_rect, 1 if not is_active else 2, border_radius=4)
        lbl = font_xs.render(speed_texts[sp], True, speed_colors[sp] if is_active else COLOR_TEXT_MUTED)
        screen.blit(lbl, (btn_x + 16 - lbl.get_width() // 2, 20 - lbl.get_height() // 2))
        if mouse_clicked and btn_rect.collidepoint(mouse_pos):
            if is_popup_active:
                state.pre_popup_speed = sp
            else:
                state.speed = sp
    
    # Player Resources
    stats_x = 590
    field_men = state.get_field_troops(state.player_id)
    garrison_men = state.get_unraised_levies(state.player_id)
    
    stats = [
        (icon_gold, str(state.player["gold"]), COLOR_GOLD),
        (icon_prestige, str(state.player["prestige"]), COLOR_PRESTIGE),
        (icon_troops, f"Field: {field_men:,}", COLOR_TEXT_GREEN if field_men > 0 else COLOR_TEXT_WHITE),
        (icon_piety, f"Garrison: {garrison_men:,}", COLOR_TEXT_MUTED)
    ]
    for icon, val_str, col in stats:
        screen.blit(icon, (stats_x, 14))
        v_surf = font_md.render(val_str, True, col)
        screen.blit(v_surf, (stats_x + 28, 15))
        stats_x += 125
    
    # RESET GAME BUTTON
    rst_btn = pygame.Rect(1100, 10, 85, 32)
    b_rst_hov = rst_btn.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (90, 30, 30) if b_rst_hov else (65, 25, 25), rst_btn, border_radius=4)
    pygame.draw.rect(screen, (220, 80, 80), rst_btn, 1, border_radius=4)
    rst_lbl = font_xs.render("RESET ↺", True, COLOR_TEXT_WHITE)
    screen.blit(rst_lbl, (rst_btn.x + (rst_btn.w - rst_lbl.get_width()) // 2, rst_btn.y + 8))
    if mouse_clicked and b_rst_hov:
        # Reinitialize entire game state and 1:1 starter cities matching vassals!
        state.reset()
        if on_reset:
            on_reset()
    # ---------------------------------------------------------
