"""
Game Configuration, Constants, Colors, and Display Setup
"""
import os
import pygame

# Game Window Dimensions
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 720
FPS = 60

# Map Viewport & Base Tile Dimensions
BASE_TILE_W = 34
BASE_TILE_H = 32
VIEWPORT_CENTER_X = 575
VIEWPORT_CENTER_Y = 385

# Travel & Simulation Constants
DAYS_PER_TILE = 5  # Number of in-game days it takes to traverse one province
DAYS_PER_KOTAK = 1.0  # Number of in-game days it takes to traverse one tile (kotak)
LEVY_RAISE_COOLDOWN_DAYS = 90  # 3 months cooldown between levy summons (prevents spam)

# Colors
COLOR_BG = (20, 24, 32)
COLOR_PANEL_BG = (30, 35, 46)
COLOR_PANEL_BORDER = (52, 60, 76)
COLOR_GOLD = (235, 185, 50)
COLOR_PRESTIGE = (80, 160, 240)
COLOR_PIETY = (240, 240, 255)
COLOR_TEXT_WHITE = (235, 240, 250)
COLOR_TEXT_MUTED = (150, 160, 175)
COLOR_TEXT_RED = (235, 75, 75)
COLOR_TEXT_GREEN = (75, 215, 110)
COLOR_BUTTON_NORMAL = (45, 52, 68)
COLOR_BUTTON_HOVER = (65, 75, 98)
COLOR_BUTTON_ACTIVE = (90, 105, 135)
COLOR_OCEAN = (18, 32, 54)

# Realm Theme Colors
COLOR_WESSEX = (195, 35, 35)      # Saxon Crimson
COLOR_DANELAW = (55, 75, 100)     # Norse Iron Slate

# Base Directories
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
DATA_DIR = os.path.join(ROOT_DIR, "data")

def maximize_window():
    try:
        import ctypes
        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 3)
    except Exception:
        pass

def get_fonts():
    """Initializes and returns the game font dictionary."""
    available_sysfonts = pygame.font.get_fonts()
    font_name = "segoeuisymbol" if "segoeuisymbol" in available_sysfonts else "segoeui"
    return {
        "xs": pygame.font.SysFont(font_name, 12, bold=True),
        "sm": pygame.font.SysFont(font_name, 14),
        "md": pygame.font.SysFont(font_name, 17, bold=True),
        "lg": pygame.font.SysFont(font_name, 22, bold=True),
        "title": pygame.font.SysFont("georgia", 25, bold=True),
        "banner": pygame.font.SysFont("georgia", 32, bold=True)
    }
