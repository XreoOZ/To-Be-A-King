"""Main menu and placeholder character setup screen."""
import pygame

from game.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_BG, COLOR_PANEL_BG, COLOR_PANEL_BORDER,
    COLOR_GOLD, COLOR_TEXT_WHITE, COLOR_TEXT_MUTED, COLOR_BUTTON_NORMAL,
    COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE,
)


def _draw_button(screen, rect, label, font, mouse_pos, selected=False, disabled=False):
    hovered = rect.collidepoint(mouse_pos) and not disabled
    color = COLOR_BUTTON_ACTIVE if selected else COLOR_BUTTON_HOVER if hovered else COLOR_BUTTON_NORMAL
    if disabled:
        color = (38, 42, 51)
    pygame.draw.rect(screen, color, rect, border_radius=6)
    pygame.draw.rect(
        screen,
        COLOR_GOLD if selected else COLOR_PANEL_BORDER,
        rect,
        2 if selected else 1,
        border_radius=6,
    )
    text_color = COLOR_TEXT_MUTED if disabled else COLOR_TEXT_WHITE
    label_surface = font.render(label, True, text_color)
    screen.blit(label_surface, label_surface.get_rect(center=rect.center))


def render_main_menu(screen, fonts, mouse_pos, stage, province_count):
    """Draws the active menu page and returns its button hitboxes."""
    screen.fill(COLOR_BG)
    buttons = {}

    pygame.draw.rect(screen, (24, 30, 42), (0, 0, WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.draw.ellipse(screen, (31, 40, 54), (WINDOW_WIDTH // 2 - 480, 115, 960, 820))
    panel = pygame.Rect(WINDOW_WIDTH // 2 - 360, 140, 720, 800)
    pygame.draw.rect(screen, COLOR_PANEL_BG, panel, border_radius=14)
    pygame.draw.rect(screen, COLOR_PANEL_BORDER, panel, 2, border_radius=14)

    title = fonts["banner"].render("CK2-LITE", True, COLOR_GOLD)
    screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 220)))
    subtitle = fonts["md"].render("A GENERATIVE MEDIEVAL STRATEGY", True, COLOR_TEXT_MUTED)
    screen.blit(subtitle, subtitle.get_rect(center=(WINDOW_WIDTH // 2, 263)))
    pygame.draw.line(screen, COLOR_PANEL_BORDER, (panel.x + 70, 300), (panel.right - 70, 300), 1)

    if stage == "main":
        button_w, button_h = 360, 58
        x = WINDOW_WIDTH // 2 - button_w // 2
        for key, label, y, disabled in (
            ("play_menu", "PLAY", 380, False),
            ("settings", "SETTINGS  -  COMING SOON", 462, True),
            ("exit", "EXIT GAME", 544, False),
        ):
            rect = pygame.Rect(x, y, button_w, button_h)
            buttons[key] = rect
            _draw_button(screen, rect, label, fonts["lg"], mouse_pos, disabled=disabled)
        footer = fonts["sm"].render("Build a new realm, then lead it to glory.", True, COLOR_TEXT_MUTED)
        screen.blit(footer, footer.get_rect(center=(WINDOW_WIDTH // 2, 680)))
    else:
        heading = fonts["lg"].render("CHARACTER MAKER", True, COLOR_TEXT_WHITE)
        screen.blit(heading, heading.get_rect(center=(WINDOW_WIDTH // 2, 345)))
        portrait_rect = pygame.Rect(WINDOW_WIDTH // 2 - 42, 375, 84, 84)
        pygame.draw.rect(screen, (43, 48, 59), portrait_rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_GOLD, portrait_rect, 1, border_radius=8)
        pygame.draw.circle(screen, (159, 119, 88), (portrait_rect.centerx, portrait_rect.y + 31), 17)
        pygame.draw.ellipse(screen, (88, 106, 130), (portrait_rect.x + 14, portrait_rect.y + 48, 56, 38))

        message = fonts["sm"].render(
            "Character customization is a mockup for now; rulers are randomized when you play.",
            True,
            COLOR_TEXT_MUTED,
        )
        screen.blit(message, message.get_rect(center=(WINDOW_WIDTH // 2, 485)))
        size_label = fonts["md"].render("WORLD SIZE  -  NUMBER OF PROVINCES", True, COLOR_TEXT_WHITE)
        screen.blit(size_label, size_label.get_rect(center=(WINDOW_WIDTH // 2, 550)))

        option_w, option_h, gap = 150, 56, 18
        options_x = WINDOW_WIDTH // 2 - (option_w * 3 + gap * 2) // 2
        for index, size in enumerate((10, 20, 30)):
            rect = pygame.Rect(options_x + index * (option_w + gap), 578, option_w, option_h)
            key = f"size_{size}"
            buttons[key] = rect
            _draw_button(
                screen,
                rect,
                f"{size} PROVINCES",
                fonts["md"],
                mouse_pos,
                selected=province_count == size,
            )

        back_rect = pygame.Rect(WINDOW_WIDTH // 2 - 230, 690, 200, 58)
        start_rect = pygame.Rect(WINDOW_WIDTH // 2 + 30, 690, 200, 58)
        buttons["back"] = back_rect
        buttons["start"] = start_rect
        _draw_button(screen, back_rect, "BACK", fonts["lg"], mouse_pos)
        _draw_button(screen, start_rect, "PLAY", fonts["lg"], mouse_pos, selected=True)

    return buttons
