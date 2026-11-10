"""
CK2-Lite: Britain AD 867 (Army Raising & Gathering Edition)
Kingdom of Wessex (Saxons) vs The Danelaw (Vikings)

New Features:
- Must RAISE LEVIES from provinces (individually or 'Raise All Levies')
- Armies exist as units on the map (with troop count badges)
- Move & march armies between adjacent provinces (with BFS pathfinding)
- GATHER & MERGE armies into a single mighty Royal Army host!
- March into enemy territory to besiege provinces
- Clash with enemy armies in tactical Pitched Battles!
- Danelaw (Halfdan) AI raises Viking hosts, rallies them, and counter-attacks
- No pop-up interruptions, smooth calendar ticks
"""

import sys
import os
import json
import random
import math
from collections import deque

# Enable Windows Per-Monitor High-DPI Awareness before initializing Pygame
# This prevents Windows DWM from forcibly blurring/stretching the application window on high-DPI / scaled displays (e.g. 125%, 150%).
try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# High-definition hardware texture scaling (2 = anisotropic / high-fidelity hardware scaling in SDL2)
os.environ["SDL_RENDER_SCALE_QUALITY"] = "2"

import pygame

# Initialize Pygame
pygame.init()
pygame.font.init()

# Game Window Dimensions
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 720
FPS = 60

# Maximize Window helper for Windows OS
def maximize_window():
    try:
        import ctypes
        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        if hwnd:
            # 3 = SW_MAXIMIZE
            ctypes.windll.user32.ShowWindow(hwnd, 3)
    except Exception:
        pass

# Set display mode immediately with SCALED & RESIZABLE for hardware-accelerated scaling
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("CK2-Lite: The War for Britain (Army Raising & Rally Edition)")
maximize_window()

# Palette
# Added constant for travel days per tile
DAYS_PER_TILE = 5  # Number of in‑game days it takes to traverse one province

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")

# High-Fidelity Vector Fonts with Full Unicode Symbol Support (Crown, Swords, Shields, Hourglass)
available_sysfonts = pygame.font.get_fonts()
font_name = "segoeuisymbol" if "segoeuisymbol" in available_sysfonts else "segoeui"
font_xs = pygame.font.SysFont(font_name, 12, bold=True)
font_sm = pygame.font.SysFont(font_name, 14)
font_md = pygame.font.SysFont(font_name, 17, bold=True)
font_lg = pygame.font.SysFont(font_name, 22, bold=True)
font_title = pygame.font.SysFont("georgia", 25, bold=True)
font_banner = pygame.font.SysFont("georgia", 32, bold=True)

# -------------------------------------------------------------
# Asset Loader Helper
# -------------------------------------------------------------
def load_image(subpath, size=None):
    full_path = os.path.join(ASSETS_DIR, subpath)
    if os.path.exists(full_path):
        img = pygame.image.load(full_path)
        if pygame.display.get_surface() is not None:
            img = img.convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    surf = pygame.Surface(size or (32, 32), pygame.SRCALPHA)
    surf.fill((120, 120, 120, 180))
    return surf

import copy

# Load Data
with open(os.path.join(DATA_DIR, "characters.json"), "r", encoding="utf-8") as f:
    INITIAL_CHARACTERS = json.load(f)

with open(os.path.join(DATA_DIR, "provinces.json"), "r", encoding="utf-8") as f:
    INITIAL_PROVINCES = json.load(f)

CHARACTERS = copy.deepcopy(INITIAL_CHARACTERS)
PROVINCES = copy.deepcopy(INITIAL_PROVINCES)

# Harmonic Provincial Color Palettes per Faction (Distinct, highly readable tones for every province)
PROVINCE_FACTION_COLORS = {
    # If owned by Wessex (Kingdom of Wessex / Saxons - rich crimson/burgundy/terracotta palette)
    "char_alfred": {
        "wessex": (196, 38, 42),       # Wessex Royal Red
        "kent_essex": (170, 32, 50),   # Kent Burgundy
        "mercia": (185, 60, 36),       # Mercia Terracotta Crimson
        "east_anglia": (205, 52, 36),  # East Anglia Vermilion
        "cornwall": (175, 42, 60),     # Cornwall Celtic Crimson
        "wales": (155, 26, 38),        # Wales Dark Dragon Red
        "jorvik": (168, 46, 46),       # Jorvik Northern Red
        "deira": (180, 52, 44),        # Deira Northumbrian Red
        "bernicia": (160, 38, 50),     # Bernicia Coastal Crimson
        "strathclyde": (172, 48, 55),  # Strathclyde Red
        "lothian": (184, 55, 48),      # Lothian Red
        "highlands": (150, 30, 42),    # Highlands Red
    },
    # If owned by Danelaw (Vikings - navy/slate/cobalt/storm palette)
    "char_halfdan": {
        "jorvik": (44, 68, 98),        # Jorvik Viking Navy
        "deira": (58, 84, 114),        # Deira Northumbrian Slate Blue
        "bernicia": (38, 60, 88),      # Bernicia North Sea Cobalt
        "strathclyde": (52, 76, 104),  # Strathclyde Storm Blue
        "lothian": (46, 72, 98),       # Lothian Midnight Teal
        "highlands": (35, 54, 78),     # Scottish Highlands Deep Pine
        "mercia": (50, 72, 96),        # Mercia Conquered Slate
        "east_anglia": (62, 86, 112),  # East Anglia Conquered Blue
        "wessex": (42, 64, 92),        # Wessex Conquered Navy
        "kent_essex": (48, 70, 96),    # Kent Conquered Navy
        "cornwall": (40, 58, 84),      # Cornwall Conquered Navy
        "wales": (36, 56, 82),         # Wales Conquered Blue
    }
}

# Apply harmonic colors to initial provinces
for pid, p in PROVINCES.items():
    owner = p.get("owner", "char_alfred")
    if owner in PROVINCE_FACTION_COLORS and pid in PROVINCE_FACTION_COLORS[owner]:
        p["color"] = list(PROVINCE_FACTION_COLORS[owner][pid])

def reset_global_world_data():
    """Restores PROVINCES and CHARACTERS dictionaries to pristine AD 867 state."""
    CHARACTERS.clear()
    CHARACTERS.update(copy.deepcopy(INITIAL_CHARACTERS))
    PROVINCES.clear()
    PROVINCES.update(copy.deepcopy(INITIAL_PROVINCES))
    for pid, p in PROVINCES.items():
        owner = p.get("owner", "char_alfred")
        if owner in PROVINCE_FACTION_COLORS and pid in PROVINCE_FACTION_COLORS[owner]:
            p["color"] = list(PROVINCE_FACTION_COLORS[owner][pid])

with open(os.path.join(ASSETS_DIR, "map", "britain_map.json"), "r", encoding="utf-8") as f:
    MAP_DATA = json.load(f)

# Load Icons
icon_gold = load_image(os.path.join("icons", "gold.png"), (24, 24))
icon_prestige = load_image(os.path.join("icons", "prestige.png"), (24, 24))
icon_piety = load_image(os.path.join("icons", "piety.png"), (24, 24))
icon_troops = load_image(os.path.join("icons", "troops.png"), (24, 24))
icon_speed_pause = load_image(os.path.join("icons", "speed_pause.png"), (24, 24))
icon_speed_play = load_image(os.path.join("icons", "speed_play.png"), (24, 24))
icon_speed_fast = load_image(os.path.join("icons", "speed_fast.png"), (24, 24))

# Load Portraits & Heraldry
portrait_cache = {}
coa_cache = {}

for cid, char in CHARACTERS.items():
    pfile = char.get("portrait", "portrait_default.png")
    portrait_cache[cid] = load_image(os.path.join("portraits", pfile), (80, 80))
    cfile = char.get("coa", "coa_wessex.png")
    coa_cache[cid] = load_image(os.path.join("heraldry", cfile), (36, 42))

# Procedural Distinct Heraldry for Kent & Cornwall
def make_heraldic_shield(bg_color, is_cornwall=False, is_kent=False):
    s = pygame.Surface((24, 28), pygame.SRCALPHA)
    s.fill(bg_color)
    if is_cornwall:
        # Saint Piran's Cross: Bold White Cross on Pitch Black Field
        pygame.draw.line(s, (255, 255, 255), (0, 14), (24, 14), 4)
        pygame.draw.line(s, (255, 255, 255), (8, 0), (8, 28), 4)
    elif is_kent:
        # Saxon Invicta Cross on Crimson Field
        pygame.draw.line(s, (255, 255, 255), (0, 14), (24, 14), 3)
        pygame.draw.line(s, (255, 255, 255), (8, 0), (8, 28), 3)
        pygame.draw.polygon(s, (255, 255, 255), [(13, 6), (19, 10), (13, 14)])
    pygame.draw.rect(s, COLOR_GOLD, (0, 0, 24, 28), 1, border_radius=3)
    return s

# Province Heraldic Shields for Armies
prov_flag_cache = {
    "wessex": load_image(os.path.join("heraldry", "coa_wessex.png"), (24, 28)),
    "mercia": load_image(os.path.join("heraldry", "coa_mercia.png"), (24, 28)),
    "east_anglia": load_image(os.path.join("heraldry", "coa_east_anglia.png"), (24, 28)),
    "kent_essex": make_heraldic_shield((175, 25, 45), is_kent=True),
    "cornwall": make_heraldic_shield((24, 24, 28), is_cornwall=True),
    "wales": load_image(os.path.join("heraldry", "coa_wales.png"), (24, 28)),
    "jorvik": load_image(os.path.join("heraldry", "coa_danelaw.png"), (24, 28)),
    "deira": load_image(os.path.join("heraldry", "coa_northumbria.png"), (24, 28)),
    "bernicia": load_image(os.path.join("heraldry", "coa_northumbria.png"), (24, 28)),
    "strathclyde": load_image(os.path.join("heraldry", "coa_scotland.png"), (24, 28)),
    "lothian": load_image(os.path.join("heraldry", "coa_scotland.png"), (24, 28)),
    "highlands": load_image(os.path.join("heraldry", "coa_scotland.png"), (24, 28)),
}

# -------------------------------------------------------------
# Waving War Banners & Cloth Generation
# -------------------------------------------------------------
def make_banner_cloth(pid, width, height, is_large=True):
    bg_palette = {
        "wessex": (190, 30, 30),
        "mercia": (22, 50, 130),
        "east_anglia": (30, 80, 160),
        "kent_essex": (170, 25, 45),
        "cornwall": (24, 24, 28),
        "wales": (28, 110, 50),
        "jorvik": (35, 40, 50),
        "deira": (135, 38, 42),
        "bernicia": (30, 42, 85),
        "strathclyde": (20, 55, 135),
        "lothian": (20, 55, 135),
        "highlands": (20, 55, 135),
    }
    bg = bg_palette.get(pid, (120, 30, 30))
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill(bg)

    # Blit heraldic shield onto banner cloth
    emblem = prov_flag_cache.get(pid)
    if emblem:
        ew = int(width * 0.65)
        eh = int(height * 0.78)
        scaled_emblem = pygame.transform.smoothscale(emblem, (ew, eh))
        surf.blit(scaled_emblem, (2, (height - eh) // 2))

    # Golden fringe borders
    pygame.draw.line(surf, COLOR_GOLD, (0, 0), (width, 0), 1)
    pygame.draw.line(surf, COLOR_GOLD, (0, height - 1), (width, height - 1), 1)

    # Swallowtail pennon notch for grand banners
    if is_large and width >= 26:
        cut_w = 6
        pts = [(width - cut_w, height // 2), (width + 1, 0), (width + 1, height)]
        cut_mask = pygame.Surface((width, height), pygame.SRCALPHA)
        cut_mask.fill((255, 255, 255, 255))
        pygame.draw.polygon(cut_mask, (0, 0, 0, 0), pts)
        surf.blit(cut_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.line(surf, COLOR_GOLD, (width - 1, 0), (width - cut_w, height // 2), 1)
        pygame.draw.line(surf, COLOR_GOLD, (width - cut_w, height // 2), (width - 1, height - 1), 1)
    else:
        pygame.draw.line(surf, COLOR_GOLD, (width - 1, 0), (width - 1, height - 1), 1)

    return surf

banner_cloth_large = {pid: make_banner_cloth(pid, 32, 22, is_large=True) for pid in prov_flag_cache}
banner_cloth_small = {pid: make_banner_cloth(pid, 18, 13, is_large=False) for pid in prov_flag_cache}
_cloth_scaled_cache = {}

def get_scaled_banner_cloth(pid, width, height, is_large=True):
    width = max(8, width)
    height = max(6, height)
    key = (pid, width, height, is_large)
    if key in _cloth_scaled_cache:
        return _cloth_scaled_cache[key]
    cloth = make_banner_cloth(pid, width, height, is_large=is_large)
    _cloth_scaled_cache[key] = cloth
    return cloth

def draw_waving_banner(surface, cloth_surf, pole_x, pole_y, pole_h, ticks, amp=3.0, freq=0.25, is_main=False):
    # Wooden flagpole
    top_y = pole_y - pole_h
    pygame.draw.line(surface, (45, 30, 20), (pole_x, top_y), (pole_x, pole_y), 2 if is_main else 1)
    pygame.draw.line(surface, (95, 70, 48), (pole_x - 1, top_y), (pole_x - 1, pole_y), 1)

    # Golden Spearhead Finial on top
    finial_h = max(3, int(pole_h * 0.18)) if is_main else max(2, int(pole_h * 0.14))
    finial_w = max(2, int(pole_h * 0.10)) if is_main else max(1, int(pole_h * 0.08))
    pygame.draw.polygon(surface, COLOR_GOLD, [
        (pole_x, top_y - finial_h),
        (pole_x - finial_w, top_y),
        (pole_x + finial_w, top_y)
    ])
    if is_main:
        pygame.draw.line(surface, (255, 235, 120), (pole_x - finial_w, top_y), (pole_x + finial_w, top_y), 1)

    # Waving cloth flutter animation
    cw, ch = cloth_surf.get_size()
    strip_w = 2
    cloth_top = top_y + max(2, int(pole_h * 0.10))
    time_val = ticks * 0.0055

    for sx in range(0, cw, strip_w):
        cur_w = min(strip_w, cw - sx)
        progress = sx / max(1, cw - 1)
        cur_amp = amp * progress
        wave_y = int(math.sin(time_val + sx * freq) * cur_amp)
        
        draw_x = pole_x + 1 + sx
        draw_y = cloth_top + wave_y
        surface.blit(cloth_surf, (draw_x, draw_y), (sx, 0, cur_w, ch))

        # Dynamic lighting shading on wave ripples
        shade = int(math.cos(time_val + sx * freq) * (18 if is_main else 12))
        if shade != 0:
            s_surf = pygame.Surface((cur_w, ch), pygame.SRCALPHA)
            if shade > 0:
                s_surf.fill((255, 255, 255, min(45, shade * 2)))
            else:
                s_surf.fill((0, 0, 0, min(65, -shade * 2)))
            surface.blit(s_surf, (draw_x, draw_y))

# Surrounding banner relative coordinates (encircling the grand central banner)
SUB_FLAG_OFFSETS = [
    (-22,  3),   # 0: left flank forward
    (+24,  3),   # 1: right flank forward
    (-36, -5),   # 2: left flank rear
    (+38, -5),   # 3: right flank rear
    (-50,  2),   # 4: far-left flank
    (+52,  2),   # 5: far-right flank
    (-14, -12),  # 6: center-left rear
    (+14, -12),  # 7: center-right rear
    (-64, -3),   # 8: extra far left
    (+66, -3),   # 9: extra far right
    (-28, -14),  # 10
    (+28, -14),  # 11
]

# -------------------------------------------------------------
# Province Adjacency Graph for Movement & Pathfinding
# -------------------------------------------------------------
ADJACENCY = {
    "cornwall": ["wessex"],
    "wessex": ["cornwall", "kent_essex", "mercia", "wales"],
    "kent_essex": ["east_anglia", "mercia", "wessex"],
    "mercia": ["deira", "east_anglia", "jorvik", "kent_essex", "wales", "wessex"],
    "wales": ["mercia", "wessex"],
    "east_anglia": ["kent_essex", "mercia"],
    "jorvik": ["bernicia", "deira", "mercia"],
    "deira": ["bernicia", "jorvik", "mercia"],
    "bernicia": ["deira", "jorvik", "lothian"],
    "strathclyde": ["highlands", "lothian"],
    "lothian": ["bernicia", "highlands", "strathclyde"],
    "highlands": ["lothian", "strathclyde"]
}

def build_dynamic_province_adjacency(cell_to_prov, max_reach=2, extra_connections=None):
    """
    Dynamically generates the adjacency graph of provinces from the tile map grid.
    Uses Chebyshev/Manhattan distance <= max_reach between cells so narrow rivers, 
    straits, or diagonal borders between provinces are automatically detected as neighbors.
    
    This ensures any custom or newly imported map grid will automatically produce
    topologically valid, seamless pathfinding without manual hardcoding or teleport bugs.
    """
    adj = {pid: set() for pid in set(cell_to_prov.values()) if pid}
    
    for (c, r), p_a in cell_to_prov.items():
        if not p_a:
            continue
        for dc in range(-max_reach, max_reach + 1):
            for dr in range(-max_reach, max_reach + 1):
                if dc == 0 and dr == 0:
                    continue
                if abs(dc) + abs(dr) > max_reach:
                    continue
                p_b = cell_to_prov.get((c + dc, r + dr))
                if p_b and p_b != p_a:
                    adj[p_a].add(p_b)
                    adj[p_b].add(p_a)
                    
    if extra_connections:
        for p1, p2 in extra_connections:
            if p1 in adj and p2 in adj:
                adj[p1].add(p2)
                adj[p2].add(p1)
                
    return {p: sorted(list(neighbors)) for p, neighbors in adj.items()}

def find_shortest_path(start, goal):
    if start == goal:
        return [start]
    queue = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        node = path[-1]
        for neighbor in ADJACENCY.get(node, []):
            if neighbor == goal:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None

# -------------------------------------------------------------
# Army Class
# -------------------------------------------------------------
class Army:
    def __init__(self, army_id, owner_id, province_id, troops, name="Levy Host", flag_origin=None, rank=1):
        self.id = army_id
        self.owner = owner_id
        self.province = province_id
        self.troops = troops
        self.name = name
        self.flag_origin = flag_origin or province_id
        self.rank = rank  # 3 = King, 2 = Duke/Ealdorman, 1 = Thane/Baron
        self.sub_flags = []  # List of secondary province flags when merged
        self.crown_troops = 0   # Regular / Crown Demesne troops (costs 1g per 100 soldiers)
        self.vassal_levies = troops  # Feudal Vassal Levies (FREE 0g/m under feudal duty)
        
        # Movement & Path
        self.path = []              # list of province_ids to march through
        self.move_progress = 0.0    # 0 to 100%
        self.move_speed = 100.0 / DAYS_PER_TILE      # % per day (takes DAYS_PER_TILE days per province)
        
        # Combat & Siege
        self.is_sieging = False
        self.siege_progress = 0     # 0 to 100%
        self.in_battle = False
        self.target_city = None
        self.siege_target_name = None
        
        # Mobilization, Royal Courier Summons & Demobilization
        self.is_mustering = False
        self.muster_days = 0
        self.is_demobilizing = False
        self.courier_en_route = False
        self.courier_path = []
        self.courier_current_prov = None
        self.courier_next_prov = None
        self.courier_progress = 0.0
        self.courier_days_left = 0

    @property
    def is_moving(self):
        return len(self.path) > 0

    @property
    def next_province(self):
        return self.path[0] if self.path else None

# -------------------------------------------------------------
# Modular Building System Specifications & Balancing
# -------------------------------------------------------------
BUILDING_SPECS = {
    "city": {
        "name": "City",
        "title": "Commercial Town",
        "tiles": 1,
        "cost": 600,
        "income": 3,
        "upkeep": 0,
        "garrison": 100,
        "recruits": 10,
        "icon": "[City]"
    },
    "fort": {
        "name": "Fort",
        "title": "Stone Fortress",
        "tiles": 2,
        "cost": 1000,
        "income": 1,
        "upkeep": 0,
        "garrison": 300,
        "recruits": 10,
        "icon": "[Fort]"
    },
    "barrack": {
        "name": "Barracks",
        "title": "Military Barracks",
        "tiles": 1,
        "cost": 800,
        "income": 0,
        "upkeep": 1,
        "garrison": 100,
        "recruits": 10,
        "icon": "⚔"
    }
}

BARRACK_UPGRADE_COSTS = {
    0: 300,   # Level 0 -> 1
    1: 450,   # Level 1 -> 2
    2: 600,   # Level 2 -> 3
    3: 750,   # Level 3 -> 4
    4: 1000   # Level 4 -> 5
}

def get_barrack_stats(level):
    lvl = max(0, min(5, int(level)))
    garrison = 100 + min(400, lvl * 100)
    recruits = 10 + lvl * 5
    upkeep = 1 + lvl
    return {"level": lvl, "garrison": garrison, "recruits": recruits, "upkeep": upkeep}

def sync_province_holdings_stats(state, pid=None, is_init=False):
    """
    Synchronizes province tax revenue and maximum garrison/levies strictly with its physical holdings:
    - City (1 Tile): +3 Gold/month, +100 Garrison
    - Fort (2 Tiles): +1 Gold/month, +300 Garrison
    - Barracks (1 Tile): +100 Garrison slot (+100 per upgrade level, up to 500)
    For holdings held by vassals, the liege receives the percentage defined by the vassal's Levy & Tax Laws.
    For Crown Demesne holdings, the ruler commands 100% of the garrison and tax.
    """
    target_pids = [pid] if pid else list(PROVINCES.keys())
    for p_key in target_pids:
        prov = PROVINCES.get(p_key)
        if not prov:
            continue

        p_holdings = {}
        for coord, sdata in state.settlements.items():
            if sdata.get("province") == p_key:
                hid = sdata.get("id") or coord
                if hid not in p_holdings:
                    p_holdings[hid] = sdata

        total_tax = 0
        total_garrison = 0
        crown_garrison = 0
        vassal_garrison = 0
        for s in p_holdings.values():
            stype = s.get("type", "city")
            base_tax = 0
            base_garrison = 0
            if stype in ("city", "town"):
                base_tax = 3
                base_garrison = 100
            elif stype == "fort":
                base_tax = 1
                base_garrison = 300
            elif stype == "barrack":
                lvl = s.get("level", 0)
                bstats = get_barrack_stats(lvl)
                base_garrison = bstats["garrison"]
                base_tax = 0

            # Crown Demesne or unassigned -> 100% to liege
            if s.get("is_crown_demesne", False) or not s.get("vassal_id"):
                total_tax += base_tax
                total_garrison += base_garrison
                crown_garrison += base_garrison
            else:
                # Holding held by a vassal -> liege receives their feudal law levy and tax share
                v_id = s.get("vassal_id")
                v_obj = None
                for v in state.vassals.get(p_key, []):
                    if v.get("id") == v_id or v.get("name") == s.get("lord"):
                        v_obj = v
                        break
                levy_pct = (max(0, min(90, v_obj.get("levy_rate", 20))) / 100.0) if v_obj else 0.20
                tax_pct = (max(0, min(90, v_obj.get("tax_rate", 10))) / 100.0) if v_obj else 0.10
                v_garr = max(0, int(round(base_garrison * levy_pct)))
                total_garrison += v_garr
                vassal_garrison += v_garr
                total_tax += max(0, int(round(base_tax * tax_pct)))

        if not p_holdings:
            total_tax = 0
            total_garrison = 50  # Rural baseline if zero constructed holdings
            vassal_garrison = 50

        prev_max = prov.get("levies_max", 0)
        prov["tax"] = total_tax
        prov["levies_max"] = total_garrison
        prov["crown_levies_max"] = crown_garrison
        prov["vassal_levies_max"] = vassal_garrison
        if is_init or "levies_current" not in prov:
            prov["levies_current"] = total_garrison
        else:
            diff = total_garrison - prev_max
            if diff > 0:
                prov["levies_current"] = min(prov["levies_max"], prov.get("levies_current", 0) + diff)
            else:
                prov["levies_current"] = min(prov["levies_max"], max(0, prov.get("levies_current", total_garrison)))

def get_vassal_landed_status(state, v_dict, prov_id=None):
    """
    Returns detailed landed status, held fiefs, held settlements,
    gross monthly income, tax rate (0-90%), tax paid to liege, net savings,
    total garrison, levy rate (0-90%), levy contribution to liege, and household guard.
    If a vassal has NO fiefs or settlement tiles, they are LANDLESS:
    Gross = 0, Tax = 0, Levies = 0, Net Savings = 0.
    """
    v_name = v_dict["name"]
    v_id = v_dict.get("id")

    # Check held fiefs
    held_fiefs = [f for f in state.fiefs.values() if f.get("holder") == v_name or f.get("vassal_id") == v_id]

    # Check held settlement tiles
    held_tiles = list(v_dict.get("tiles", []))
    for f in held_fiefs:
        for t in f.get("tiles", []):
            if t not in held_tiles:
                held_tiles.append(t)

    # Check physical settlements owned by this vassal
    held_settlements = []
    seen_hids = set()
    for t in held_tiles:
        if t in state.settlements:
            sdata = state.settlements[t]
            if sdata.get("vassal_id") == v_id or sdata.get("lord") == v_name:
                hid = sdata.get("id") or sdata.get("name")
                if hid not in seen_hids:
                    seen_hids.add(hid)
                    held_settlements.append(sdata)

    is_landed = (len(held_fiefs) > 0 or len(held_settlements) > 0 or len(held_tiles) > 0)
    tax_rate = max(0, min(90, v_dict.get("tax_rate", 10)))
    levy_rate = max(0, min(90, v_dict.get("levy_rate", 20)))

    if not is_landed:
        return {
            "is_landed": False,
            "held_fiefs": [],
            "held_settlements": [],
            "total_tiles": 0,
            "gross_income": 0,
            "tax_rate": tax_rate,
            "tax_paid": 0,
            "net_savings": 0,
            "total_garrison": 0,
            "levy_rate": levy_rate,
            "levy_contribution": 0,
            "household_guard": 0
        }

    # Calculate gross domain income & total military garrison from owned physical holdings
    gross = 0
    total_garrison = 0
    if held_settlements:
        for s in held_settlements:
            stype = s.get("type", "city")
            if stype in ("city", "town"):
                gross += 30
                total_garrison += 100
            elif stype == "fort":
                gross += 15
                total_garrison += 300
            elif stype == "barrack":
                gross += 10
                lvl = s.get("level", 0)
                total_garrison += (100 + min(400, lvl * 100))
    else:
        # Fief without constructed holding yet (agricultural land)
        gross = len(held_tiles) * 10
        total_garrison = len(held_tiles) * 35

    tax_paid = max(0, int(round(gross * (tax_rate / 100.0))))
    net_savings = max(0, gross - tax_paid)

    levy_contribution = max(0, int(round(total_garrison * (levy_rate / 100.0))))
    household_guard = max(0, total_garrison - levy_contribution)

    return {
        "is_landed": True,
        "held_fiefs": held_fiefs,
        "held_settlements": held_settlements,
        "total_tiles": len(held_tiles),
        "gross_income": gross,
        "tax_rate": tax_rate,
        "tax_paid": tax_paid,
        "net_savings": net_savings,
        "total_garrison": total_garrison,
        "levy_rate": levy_rate,
        "levy_contribution": levy_contribution,
        "household_guard": household_guard
    }

def standardize_enemy_ai_laws(state):
    """
    Uniformly standardizes all Danelaw / Viking AI vassals' feudal obligations (Tax & Levies).
    Ensures enemy AI forces always maintain a streamlined, formidable wartime mobilization rate
    (80% levies, 20% tax) across all Norse Jarls and Lothian barons without requiring manual player-like micro-management.
    """
    danelaw_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == state.enemy_id]
    for pid in danelaw_provs:
        for v in state.vassals.get(pid, []):
            v["tax_rate"] = 20    # Uniform standard 20% tax
            v["levy_rate"] = 80   # Uniform standard 80% levy obligation for martial Great Viking Army
            v["tax_locked"] = True
            v["levy_locked"] = True
            st = get_vassal_landed_status(state, v, pid)
            v["tax_contribution"] = st["tax_paid"]
            v["levy_contribution"] = st["levy_contribution"]
        sync_province_holdings_stats(state, pid)

# -------------------------------------------------------------
# City Siege & Contested Province Helpers
# -------------------------------------------------------------
def get_province_holdings(state, pid):
    """Return dict of holding_key -> list of (c, r) tiles in that province."""
    holdings = {}
    for (c, r), s in state.settlements.items():
        if s.get("province") == pid:
            h_key = s.get("id") or s.get("name", "Unknown Holding")
            holdings.setdefault(h_key, []).append((c, r))
    return holdings

def get_all_settlement_holdings(state):
    """Groups settlement tiles into unified multi-tile holding objects strictly per holding/settlement ID."""
    has_ids = any("id" in s for s in state.settlements.values())
    
    if has_ids:
        holdings_by_id = {}
        for coord, sdata in state.settlements.items():
            s_id = sdata.get("id") or coord
            if s_id not in holdings_by_id:
                holdings_by_id[s_id] = {
                    "id": s_id,
                    "name": sdata.get("name", "Holding"),
                    "province": sdata.get("province"),
                    "tiles": [],
                    "primary_tile": coord,
                    "data": sdata,
                    "occupied_by": sdata.get("occupied_by")
                }
            holdings_by_id[s_id]["tiles"].append(coord)

        holdings = []
        for s_id, h in holdings_by_id.items():
            comp = sorted(h["tiles"])
            min_c = min(c for c, r in comp)
            max_c = max(c for c, r in comp)
            min_r = min(r for c, r in comp)
            max_r = max(r for c, r in comp)
            orient = "single"
            if len(comp) == 2:
                if min_r == max_r:
                    orient = "H"
                elif min_c == max_c:
                    orient = "V"
                else:
                    orient = "H"
            elif len(comp) > 2:
                orient = "H" if (max_c - min_c) >= (max_r - min_r) else "V"
            h["min_c"] = min_c
            h["max_c"] = max_c
            h["min_r"] = min_r
            h["max_r"] = max_r
            h["orient"] = orient
            holdings.append(h)
        return holdings

    # Fallback for legacy state without 'id' (strictly limit to at most 2 contiguous tiles per holding)
    visited = set()
    holdings = []
    for coord, sdata in state.settlements.items():
        if coord in visited:
            continue
        comp = []
        queue = [coord]
        visited.add(coord)
        while queue:
            curr = queue.pop(0)
            comp.append(curr)
            if len(comp) >= 2:
                break
            cx, cy = curr
            for nxt in [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]:
                if nxt in state.settlements and nxt not in visited:
                    n_data = state.settlements[nxt]
                    if (n_data.get("province") == sdata.get("province") and
                        n_data.get("name") == sdata.get("name") and
                        n_data.get("vassal_id") == sdata.get("vassal_id") and
                        n_data.get("is_crown_demesne") == sdata.get("is_crown_demesne")):
                        visited.add(nxt)
                        queue.append(nxt)
                        break
        comp.sort()
        min_c = min(c for c, r in comp)
        max_c = max(c for c, r in comp)
        min_r = min(r for c, r in comp)
        max_r = max(r for c, r in comp)
        orient = "single"
        if len(comp) > 1:
            if min_r == max_r:
                orient = "H"
            elif min_c == max_c:
                orient = "V"
            else:
                orient = "H"
        holdings.append({
            "name": sdata.get("name", "Holding"),
            "province": sdata.get("province"),
            "tiles": comp,
            "primary_tile": comp[0],
            "data": sdata,
            "occupied_by": sdata.get("occupied_by"),
            "min_c": min_c, "max_c": max_c,
            "min_r": min_r, "max_r": max_r,
            "orient": orient
        })
    return holdings

def get_realm_finances(state, char_id=None):
    """
    Returns complete itemized breakdown of realm finances:
    - Provincial Tax Income (Tolls, tariffs & customs per province)
    - Feudal Vassal Tithes (Taxes levied under Realm Laws 0-90%)
    - Crown Demesne Direct Revenue (King's royal seats)
    - Army Field Upkeep (1g per 100 Crown Demesne troops; Vassal Levies are FREE!)
    - Military Facilities Upkeep (Barracks & garrison drillmasters)
    - Net monthly cash flow & Treasury balance
    """
    if char_id is None:
        char_id = state.player_id
    r_char = CHARACTERS.get(char_id, {})

    # 1. Provincial Land Tax & Customs
    prov_incomes = []
    total_prov_tax = 0
    for pid, prov in PROVINCES.items():
        if prov["owner"] == char_id:
            ptax = prov.get("tax", 0)
            total_prov_tax += ptax
            prov_incomes.append({
                "pid": pid,
                "name": prov["name"].split()[0],
                "tax": ptax
            })

    # 2. Feudal Vassal Tithes (Taxes collected under Realm Laws)
    vassal_tithes = []
    total_vassal_tax = 0
    for pid, prov in PROVINCES.items():
        if prov["owner"] == char_id:
            for v in state.vassals.get(pid, []):
                st = get_vassal_landed_status(state, v, pid)
                if st["is_landed"] and st["tax_paid"] > 0:
                    total_vassal_tax += st["tax_paid"]
                    vassal_tithes.append({
                        "name": v["name"],
                        "pid": pid,
                        "prov": PROVINCES[pid]["name"].split()[0],
                        "tax_rate": st["tax_rate"],
                        "tax_paid": st["tax_paid"],
                        "gross": st["gross_income"]
                    })

    # 3. Direct Crown Demesne Revenue (Direct modular holdings)
    crown_holdings = []
    total_crown_income = 0
    for h in get_all_settlement_holdings(state):
        sdata = h["data"]
        pid = h["province"]
        if PROVINCES.get(pid, {}).get("owner") == char_id and sdata.get("is_crown_demesne"):
            htype = sdata.get("type", "city")
            if htype == "fort":
                val = 1
            elif htype == "barrack":
                val = 0
            else:
                val = 3
            total_crown_income += val
            clean_name = h["name"].replace("Royal Citadel of ", "").replace("Royal Castle of ", "").replace("Royal Borough of ", "")
            crown_holdings.append({
                "name": clean_name,
                "prov": PROVINCES[pid]["name"].split()[0],
                "type": htype.capitalize(),
                "val": val
            })

    total_income = total_prov_tax + total_vassal_tax + total_crown_income

    # 4. Army Field Upkeep (1 gold per 100 Crown Demesne troops; Feudal Vassal Levies are FREE!)
    army_expenses = []
    total_army_upkeep = 0
    for a in state.armies:
        if a.owner == char_id:
            c_tr = getattr(a, "crown_troops", 0)
            v_tr = getattr(a, "vassal_levies", max(0, a.troops - c_tr))
            cost = c_tr // 100
            total_army_upkeep += cost
            army_expenses.append({
                "name": a.name,
                "troops": a.troops,
                "crown_troops": c_tr,
                "vassal_levies": v_tr,
                "cost": cost,
                "status": "Courier En Route" if a.courier_en_route else ("Mustering" if a.is_mustering else ("In Battle" if a.in_battle else "Mobilized"))
            })

    # 5. Barracks & Garrison Maintenance
    barrack_expenses = []
    total_facility_upkeep = 0
    for coord, sdata in state.settlements.items():
        if sdata.get("is_crown_demesne") and sdata.get("type") == "barrack":
            pid = sdata.get("province")
            if PROVINCES.get(pid, {}).get("owner") == char_id:
                lvl = sdata.get("level", 0)
                cost = 1 + lvl
                total_facility_upkeep += cost
                barrack_expenses.append({
                    "name": sdata.get("name", "Royal Barracks"),
                    "prov": PROVINCES[pid]["name"].split()[0],
                    "lvl": lvl,
                    "cost": cost
                })

    total_expense = total_army_upkeep + total_facility_upkeep
    net_monthly = total_income - total_expense

    return {
        "treasury": r_char.get("gold", 0),
        "total_prov_tax": total_prov_tax,
        "prov_incomes": prov_incomes,
        "total_vassal_tax": total_vassal_tax,
        "vassal_tithes": vassal_tithes,
        "total_crown_income": total_crown_income,
        "crown_holdings": crown_holdings,
        "total_income": total_income,
        "total_army_upkeep": total_army_upkeep,
        "army_expenses": army_expenses,
        "total_facility_upkeep": total_facility_upkeep,
        "barrack_expenses": barrack_expenses,
        "total_expense": total_expense,
        "net_monthly": net_monthly
    }

def get_siegeable_holdings(state, province_id, army_owner):
    prov = PROVINCES.get(province_id)
    if not prov:
        return []
    is_enemy_prov = (prov["owner"] != army_owner)
    holdings = get_province_holdings(state, province_id)
    
    siegeable = []
    for h_name, tiles in holdings.items():
        t0 = tiles[0]
        s_data = state.settlements[t0]
        occ = s_data.get("occupied_by")
        if is_enemy_prov:
            # In enemy territory: holding is siegeable if not yet occupied by army_owner
            if occ != army_owner:
                siegeable.append((h_name, tiles))
        else:
            # In friendly territory: holding is siegeable (liberatable) if occupied by an enemy
            if occ is not None and occ != army_owner:
                siegeable.append((h_name, tiles))
    return siegeable

def is_province_contested(state, pid):
    """Returns True, occupier_id if any settlement in the province is occupied by non-owner."""
    prov = PROVINCES.get(pid)
    if not prov:
        return False, None
    owner = prov["owner"]
    for s in state.settlements.values():
        if s.get("province") == pid:
            occ = s.get("occupied_by")
            if occ is not None and occ != owner:
                return True, occ
    return False, None

# -------------------------------------------------------------
# Game State
# -------------------------------------------------------------
class GameState:
    def __init__(self):
        self.player_id = "char_alfred"
        self.enemy_id = "char_halfdan"
        self.selected_province = "wessex"
        self.selected_army_id = None
        self.hovered_province = None
        self.hovered_army_id = None
        
        # Selection handling for RTS box‑select
        self.drag_start = None          # (x, y) when left mouse button pressed
        self.drag_rect = None           # pygame.Rect of current drag area
        self.selected_army_ids = []     # list of army.id currently selected
        
        # Modular Building Mode State
        self.build_mode = False          # True when placing a holding
        self.build_type = "city"         # "city" (1 tile), "fort" (2 tiles), "barrack" (1 tile)
        self.build_orientation = "H"     # "H" (Horizontal) or "V" (Vertical) for 2-tile fort
        self.settlements = {}            # (c, r) -> {"province": pid, "type": "city", "name": str, ...}
        self.selected_settlement = None  # (c, r) coordinate if a city is clicked
        self.settlement_id_counter = 1
        
        # Vassal System State
        self.vassals = {}                # pid -> list of Vassal dicts
        self.vassal_build_requests = []  # list of pending requests
        self.selected_vassal_idx = None  # index of vassal clicked in roster
        
        # Right Panel Tab System ('overview', 'buildings', 'vassals', 'fiefs')
        self.right_tab = "overview"
        self.selected_fief_id = None
        self.fiefs = {}                  # fief_id -> {"province": pid, "tiles": [...], "holder": vassal_name or None, "name": str}
        self.fief_id_counter = 1
        self.fief_mode = False
        self.active_fief_id = None
        self.fief_brushes = {}
        self.editing_fief_id = None      # Current fief ID being edited/painted
        self.granting_fief_id = None     # Fief currently being granted via modal
        self.grant_page = 0              # Pagination index for grant modal
        self.inspecting_vassal = None    # {"province": pid, "vassal": v_dict} when inspecting vassal profile
        self.inspecting_ruler = None     # char_id when inspecting a sovereign ruler/king profile
        self.vassal_build_confirm = None # Pending confirmation modal to build on vassal fief
        self.pre_popup_speed = None      # Saved game speed before a popup paused the game
        self.popup_was_active = False    # Track whether a popup was active on previous frame
        
        # Left Panel Sub-Tab System ('armies', 'vassals', 'demesne', or 'laws')
        self.left_tab = "armies"
        self.vassal_page = 0
        self.demesne_page = 0
        self.demesne_selected_province = None  # None = show province list; str = province id to show fiefs inside
        self.fief_page = 0
        self.laws_page = 0
        self.laws_subtab = "tax"         # "tax" or "levy" sub-tab in Realm Laws
        self.universal_tax_target = 10   # default realm-wide tax target (0-90%)
        self.universal_levy_target = 20  # default realm-wide levy target (0-90%)
        self.economy_subtab = "income"   # "income" or "expense" sub-tab in Royal Finances
        self.economy_vassal_page = 0     # Pagination for vassal tithes breakdown
        
        # Camera & Map Viewport Zoom / Pan State
        self.zoom = 0.85                 # default initial zoom factor (0.85 frames whole Britain, 1.0 = standard, up to 2.4 = zoomed in)
        self.min_zoom = 0.65
        self.max_zoom = 2.40
        self.cam_pan_x = 0
        self.cam_pan_y = 0
        self.is_panning = False
        self.pan_start_mouse = (0, 0)
        self.pan_start_cam = (0, 0)
        
        # Calendar: Start 1 January 867 AD
        self.year = 867
        self.month = 1
        self.day = 1
        self.months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        self.month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Speed: 0 = Pause, 1 = Very Slow, 2 = Slow, 3 = Normal, 4 = Fast, 5 = Very Fast
        self.speed = 3  # start at Normal
        self.speed_factors = {1:2000, 2:1000, 3:500, 4:250, 5:125}
        self.tick_timer = 0
        
        # Army management
        self.armies = []
        self.army_id_counter = 1
        
        # AI decision timer
        self.ai_timer = 30
        
        # Chronicle Logs
        self.logs = [
            "AD 867: Britain stands divided between Saxons and Vikings.",
            "Raise your levies from the provinces, assemble your army, and march!"
        ]
        
        # Generate random 1-5 vassals for all provinces
        self.generate_province_vassals()

    def generate_province_vassals(self):
        saxon_first_names = ["Aethelred", "Aelfric", "Leofric", "Godric", "Wulfstan", "Eadric", "Beorn", "Ordgar", "Cenwulf", "Dunstan", "Brihtnoth", "Aldhelm"]
        saxon_epithets = ["the Bold", "the Stout", "of the Marches", "Iron-Arm", "the Pious", "the Wealthy", "the Fierce", "the Wise", "Fair-Haired"]
        viking_first_names = ["Ivar", "Ubba", "Sigurd", "Bjorn", "Guthrum", "Torstein", "Ragnar", "Hakon", "Harald", "Sven", "Einar", "Gorm"]
        viking_epithets = ["Bloodaxe", "Skull-Cleaver", "the Raven", "Sea-Wolf", "the Dane", "the Ruthless", "Iron-Side", "Oath-Breaker", "Snake-Eye"]
        
        self.vassals = {}
        for pid, pdata in PROVINCES.items():
            is_norse = (pdata["owner"] == self.enemy_id)
            if pid == "jorvik":
                count = 1  # 1 landed Norse Jarl alongside Halfdan's Citadel and War Camp in 4-tile Jorvik
            elif pid in ("deira", "strathclyde", "kent_essex", "lothian"):
                count = random.randint(2, 3)
            else:
                count = random.randint(3, 5)

            v_list = []
            for i in range(count):
                fn = random.choice(viking_first_names if is_norse else saxon_first_names)
                ep = random.choice(viking_epithets if is_norse else saxon_epithets)
                title = random.choice(["Jarl", "Hersir", "Gothi"] if is_norse else ["Thane", "Baron", "Ealdorman"])
                # AI Danelaw vassals start with standardized 80% levy and 20% tax
                t_rate = 20 if is_norse else 10
                l_rate = 80 if is_norse else 20
                v_list.append({
                    "id": f"{pid}_vassal_{i}",
                    "name": f"{title} {fn} '{ep}'",
                    "levy_contribution": 0,
                    "tax_contribution": 0,
                    "tax_rate": t_rate,
                    "levy_rate": l_rate,
                    "tax_locked": is_norse,
                    "levy_locked": is_norse,
                    "gold": random.randint(150, 450),
                    "title": title,
                    "city_name": None,
                    "tiles": []
                })
            self.vassals[pid] = v_list

    @property
    def player(self):
        return CHARACTERS[self.player_id]

    @property
    def enemy(self):
        return CHARACTERS[self.enemy_id]

    def get_provinces_count(self, char_id):
        return sum(1 for p in PROVINCES.values() if p["owner"] == char_id)

    def get_unraised_levies(self, char_id):
        return sum(p["levies_current"] for p in PROVINCES.values() if p["owner"] == char_id)

    def get_field_troops(self, char_id):
        return sum(a.troops for a in self.armies if a.owner == char_id)

    def get_selected_army(self):
        for a in self.armies:
            if a.id == self.selected_army_id:
                return a
        return None

    # ---------------------------------------------------------
    # Army Operations
    # ---------------------------------------------------------
    def raise_province_levy(self, province_id):
        prov = PROVINCES.get(province_id)
        if not prov or prov["owner"] != self.player_id:
            return
        
        available = prov["levies_current"]
        if available <= 0:
            self.logs.append(f"No levies available to raise in {prov['name']}.")
            return

        army_id = f"army_{self.army_id_counter}"
        self.army_id_counter += 1
        
        army_name = f"{prov['name'].split()[0]} Fyrd"
        capital_pid = "wessex"
        is_royal = (province_id == capital_pid)
        new_army = Army(army_id, self.player_id, province_id, available, army_name,
                        flag_origin=province_id, rank=3 if is_royal else 1)
        
        # Partition into Crown Demesne troops (upkeep 1g/100) vs Feudal Vassal Levies (FREE)
        c_max = prov.get("crown_levies_max", 0)
        t_max = prov.get("levies_max", available)
        if t_max > 0 and c_max > 0:
            c_troops = min(available, int(round(available * (c_max / float(t_max)))))
        else:
            c_troops = 0
        v_troops = max(0, available - c_troops)
        new_army.crown_troops = c_troops
        new_army.vassal_levies = v_troops
        
        if is_royal:
            new_army.is_mustering = True
            new_army.muster_days = 30
            new_army.courier_en_route = False
            self.logs.append(f"Summoned {available:,} men in royal capital {prov['name']}! Mustering troops (30 days)...")
        else:
            full_route = find_shortest_path(capital_pid, province_id)
            if full_route and len(full_route) > 1:
                hops = len(full_route) - 1
                total_days = hops * DAYS_PER_TILE
                new_army.courier_en_route = True
                new_army.courier_path = full_route[1:]
                new_army.courier_current_prov = full_route[0]
                new_army.courier_next_prov = full_route[1]
                new_army.courier_progress = 0.0
                new_army.courier_days_left = total_days
                new_army.is_mustering = False
                new_army.muster_days = 30
                p_short = prov["name"].split()[0]
                self.logs.append(f"Royal Courier dispatched from Winchester to {p_short} ({hops} shires away, {total_days}d ride)! 30d muster begins upon arrival.")
            else:
                new_army.is_mustering = True
                new_army.muster_days = 30
                new_army.courier_en_route = False
                self.logs.append(f"Summoned {available:,} men in {prov['name']}! Mustering troops (30 days)...")

        self.armies.append(new_army)
        prov["levies_current"] = 0
        self.selected_army_id = army_id

    def raise_all_levies(self):
        raised_count = 0
        total_men = 0
        capital_pid = "wessex"
        courier_count = 0
        for pid, prov in PROVINCES.items():
            if prov["owner"] == self.player_id and prov["levies_current"] > 0:
                available = prov["levies_current"]
                army_id = f"army_{self.army_id_counter}"
                self.army_id_counter += 1
                army_name = f"{prov['name'].split()[0]} Fyrd"
                is_royal = (pid == capital_pid)
                new_army = Army(army_id, self.player_id, pid, available, army_name,
                                flag_origin=pid, rank=3 if is_royal else 1)
                
                # Partition into Crown Demesne troops (upkeep 1g/100) vs Feudal Vassal Levies (FREE)
                c_max = prov.get("crown_levies_max", 0)
                t_max = prov.get("levies_max", available)
                if t_max > 0 and c_max > 0:
                    c_troops = min(available, int(round(available * (c_max / float(t_max)))))
                else:
                    c_troops = 0
                v_troops = max(0, available - c_troops)
                new_army.crown_troops = c_troops
                new_army.vassal_levies = v_troops
                
                if is_royal:
                    new_army.is_mustering = True
                    new_army.muster_days = 30
                    new_army.courier_en_route = False
                else:
                    full_route = find_shortest_path(capital_pid, pid)
                    if full_route and len(full_route) > 1:
                        hops = len(full_route) - 1
                        total_days = hops * DAYS_PER_TILE
                        new_army.courier_en_route = True
                        new_army.courier_path = full_route[1:]
                        new_army.courier_current_prov = full_route[0]
                        new_army.courier_next_prov = full_route[1]
                        new_army.courier_progress = 0.0
                        new_army.courier_days_left = total_days
                        new_army.is_mustering = False
                        new_army.muster_days = 30
                        courier_count += 1
                    else:
                        new_army.is_mustering = True
                        new_army.muster_days = 30
                        new_army.courier_en_route = False

                self.armies.append(new_army)
                prov["levies_current"] = 0
                raised_count += 1
                total_men += available
        
        if raised_count > 0:
            if courier_count > 0:
                self.logs.append(f"Royal Couriers dispatched from Winchester to {courier_count} shires! ({total_men:,} total men summoned, 30d muster begins as couriers arrive)")
            else:
                self.logs.append(f"Mobilized royal capital levies: {total_men:,} men! (Mustering for 30 days)")
        else:
            self.logs.append("All available levies are already raised.")

    def raise_all_enemy_levies(self, is_emergency=False):
        """Mobilizes ALL available levies across 100% of Danelaw provinces (All-In with war couriers)."""
        raised_count = 0
        total_men = 0
        capital_pid = "jorvik"
        danelaw_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.enemy_id]
        has_enemy_field = any(a.owner == self.enemy_id for a in self.armies)
        min_to_raise = 1 if (is_emergency or not has_enemy_field) else 30

        for pid in danelaw_provs:
            prov = PROVINCES[pid]
            available = prov.get("levies_current", 0)
            if available >= min_to_raise:
                army_id = f"army_{self.army_id_counter}"
                self.army_id_counter += 1
                p_short = prov["name"].split()[0]
                army_name = f"{p_short} Warband"
                is_royal = (pid == capital_pid)
                new_army = Army(army_id, self.enemy_id, pid, available, army_name,
                                flag_origin=pid, rank=3 if is_royal else 1)
                
                # Partition into Crown Demesne troops vs Feudal Vassal Levies (FREE)
                c_max = prov.get("crown_levies_max", 0)
                t_max = prov.get("levies_max", available)
                if t_max > 0 and c_max > 0:
                    c_troops = min(available, int(round(available * (c_max / float(t_max)))))
                else:
                    c_troops = 0
                v_troops = max(0, available - c_troops)
                new_army.crown_troops = c_troops
                new_army.vassal_levies = v_troops
                
                m_days = 8 if is_emergency else 14
                if is_royal:
                    new_army.is_mustering = True
                    new_army.muster_days = m_days
                    new_army.courier_en_route = False
                else:
                    full_route = find_shortest_path(capital_pid, pid)
                    if full_route and len(full_route) > 1:
                        hops = len(full_route) - 1
                        total_days = hops * (1 if is_emergency else 2)
                        new_army.courier_en_route = True
                        new_army.courier_path = full_route[1:]
                        new_army.courier_current_prov = full_route[0]
                        new_army.courier_next_prov = full_route[1]
                        new_army.courier_progress = 0.0
                        new_army.courier_days_left = total_days
                        new_army.is_mustering = False
                        new_army.muster_days = m_days
                    else:
                        new_army.is_mustering = True
                        new_army.muster_days = m_days
                        new_army.courier_en_route = False

                self.armies.append(new_army)
                prov["levies_current"] = 0
                raised_count += 1
                total_men += available
        return raised_count, total_men

    def rally_all_armies_to(self, target_province_id):
        player_armies = [a for a in self.armies if a.owner == self.player_id]
        if not player_armies:
            self.logs.append("No active armies to rally! Raise levies first.")
            return

        rallied = 0
        for a in player_armies:
            if a.province != target_province_id and not a.in_battle and not a.is_mustering and not a.courier_en_route:
                path = find_shortest_path(a.province, target_province_id)
                if path and len(path) > 1:
                    a.path = path[1:]
                    a.move_progress = 0.0
                    a.is_sieging = False
                    rallied += 1
        
        target_name = PROVINCES[target_province_id]["name"]
        self.logs.append(f"Rally orders issued! {len(player_armies)} hosts marching to {target_name}.")

    def merge_armies_in_province(self, province_id, owner_id):
        armies_here = [a for a in self.armies if a.province == province_id and a.owner == owner_id and not a.is_moving and not a.is_demobilizing and not a.is_mustering and not a.courier_en_route]
        if len(armies_here) <= 1:
            return

        total_troops = sum(a.troops for a in armies_here)
        total_crown = sum(getattr(a, "crown_troops", 0) for a in armies_here)
        total_vassal = sum(getattr(a, "vassal_levies", a.troops) for a in armies_here)
        # Sort by rank descending, then troops descending to find dominant host
        armies_here.sort(key=lambda x: (x.rank, x.troops), reverse=True)
        dominant_army = armies_here[0]
        dominant_army.troops = total_troops
        dominant_army.crown_troops = total_crown
        dominant_army.vassal_levies = total_vassal
        dominant_army.name = f"Royal Host of {PROVINCES[province_id]['name'].split()[0]}"
        
        # Collect all contingent flags from every joining host (no truncation)
        all_origins = []
        for a in armies_here:
            if a.flag_origin not in all_origins:
                all_origins.append(a.flag_origin)
            for sf in a.sub_flags:
                if sf not in all_origins:
                    all_origins.append(sf)
        dominant_army.sub_flags = [f for f in all_origins if f != dominant_army.flag_origin]
        
        for a in armies_here[1:]:
            if a.id == self.selected_army_id:
                self.selected_army_id = dominant_army.id
            self.armies.remove(a)
            
        self.logs.append(f"Combined {len(armies_here)} hosts under the banner of {dominant_army.name} ({total_troops:,} men)!")

    def disband_army(self, army):
        if not army:
            return
        if army.in_battle:
            self.logs.append(f"{army.name} is locked in combat and cannot disband!")
            return

        # If mustering or courier en route, cancel summons and refund troops immediately
        if army.is_mustering or army.courier_en_route:
            prov = PROVINCES.get(army.flag_origin)
            if prov:
                prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + army.troops)
            if army.courier_en_route:
                self.logs.append(f"Summons recalled for {army.name}. Royal courier stopped; {army.troops:,} men remain in garrison.")
            else:
                self.logs.append(f"Muster cancelled for {army.name}. {army.troops:,} men returned to garrison.")
            if army.id == self.selected_army_id:
                self.selected_army_id = None
            if army in self.armies:
                self.armies.remove(army)
            return

        # If merged host, split back into individual provincial contingents!
        contingents_to_disband = []
        if army.sub_flags:
            n_contingents = len(army.sub_flags) + 1
            share = army.troops // n_contingents
            dom_troops = army.troops - (share * len(army.sub_flags))
            army.troops = dom_troops
            
            for sf in army.sub_flags:
                new_id = f"army_{self.army_id_counter}"
                self.army_id_counter += 1
                p_short = PROVINCES[sf]["name"].split()[0]
                sf_host = Army(new_id, army.owner, army.province, share, f"{p_short} Fyrd", flag_origin=sf)
                self.armies.append(sf_host)
                contingents_to_disband.append(sf_host)
                
            army.sub_flags = []
            army.name = f"{PROVINCES[army.flag_origin]['name'].split()[0]} Fyrd"
        
        contingents_to_disband.append(army)

        for host in contingents_to_disband:
            if host.province == host.flag_origin:
                # Already at home province: instant disband
                prov = PROVINCES.get(host.flag_origin)
                if prov:
                    prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + host.troops)
                self.logs.append(f"{host.name} disbanded at home in {PROVINCES[host.flag_origin]['name']}. {host.troops:,} men returned to garrison.")
                if host.id == self.selected_army_id:
                    self.selected_army_id = None
                if host in self.armies:
                    self.armies.remove(host)
            else:
                # Away from home: set demobilizing and march towards home province
                host.is_demobilizing = True
                host.is_sieging = False
                host.is_mustering = False
                path = find_shortest_path(host.province, host.flag_origin)
                if path and len(path) > 1:
                    host.path = path[1:]
                    host.move_progress = 0.0
                    self.logs.append(f"{host.name} demobilizing! ({host.troops:,} men marching home to {PROVINCES[host.flag_origin]['name']}...)")
                else:
                    self.logs.append(f"Demobilizing order: {host.name} seeking route home to {PROVINCES[host.flag_origin]['name']}.")

    def order_army_march(self, army, target_province_id):
        if not army:
            return
        if army.in_battle:
            self.logs.append(f"{army.name} is locked in combat and cannot retreat!")
            return
        if army.courier_en_route:
            self.logs.append(f"{army.name} is awaiting the Royal Courier ({army.courier_days_left}d left) and has not begun muster!")
            return
        if army.is_mustering:
            self.logs.append(f"{army.name} is still mustering ({army.muster_days} days left) and cannot march!")
            return
        if army.is_demobilizing:
            army.is_demobilizing = False
            self.logs.append(f"March order issued! {army.name} cancelled demobilization and returned to war.")
        if army.province == target_province_id:
            return
        
        path = find_shortest_path(army.province, target_province_id)
        if path and len(path) > 1:
            army.path = path[1:] # steps to traverse
            army.move_progress = 0.0
            army.is_sieging = False
            t_name = PROVINCES[target_province_id]["name"]
            self.logs.append(f"{army.name} is marching towards {t_name}...")
        else:
            self.logs.append(f"No valid march route from {army.province} to {target_province_id}!")

    # ---------------------------------------------------------
    # Game Loop Ticks
    # ---------------------------------------------------------
    def advance_day(self):
        self.day += 1
        max_d = self.month_days[self.month - 1]
        if self.day > max_d:
            self.day = 1
            self.month += 1
            self.monthly_tick()
            if self.month > 12:
                self.month = 1
                self.year += 1
                self.yearly_tick()

        # 1. Update Royal Couriers En Route
        for a in list(self.armies):
            if a.courier_en_route:
                a.courier_days_left = max(0, a.courier_days_left - 1)
                a.courier_progress += (100.0 / DAYS_PER_TILE)
                if a.courier_progress >= 100.0:
                    a.courier_progress = 0.0
                    if a.courier_path:
                        a.courier_current_prov = a.courier_path.pop(0)
                        if a.courier_path:
                            a.courier_next_prov = a.courier_path[0]
                        else:
                            a.courier_next_prov = None

                    # Courier has arrived at destination province!
                    if not a.courier_path:
                        a.courier_en_route = False
                        a.is_mustering = True
                        p_short = PROVINCES[a.province]["name"].split()[0]
                        if a.owner == self.player_id:
                            self.logs.append(f"Royal Courier arrived in {p_short}! King Alfred's seal delivered to Ealdorman. {a.troops:,} {a.name} begins {a.muster_days}-day muster!")
                        else:
                            self.logs.append(f"War summons reached {p_short}! {a.troops:,} {a.name} begins {a.muster_days}-day muster.")

        # 2. Update Muster Preparation Days (only for armies where courier has already arrived)
        for a in list(self.armies):
            if a.is_mustering and not a.courier_en_route:
                a.muster_days -= 1
                if a.muster_days <= 0:
                    a.is_mustering = False
                    self.logs.append(f"⚔ {a.name} is fully assembled and battle-ready!")

        # Update Army Movements & Combat
        self.update_armies()

        # AI Behavior
        self.ai_timer -= 1
        if self.ai_timer <= 0:
            self.ai_timer = random.randint(10, 20)
            self.ai_routine()

    def monthly_tick(self):
        # 1. Base Province & Vassal monthly economy
        for pid, prov in PROVINCES.items():
            owner = CHARACTERS.get(prov["owner"])
            if owner:
                owner["gold"] += prov.get("tax", 0)
                # Slow passive replenishment
                if prov["levies_current"] < prov["levies_max"]:
                    prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + 15)
                # Vassal tax contribution & economy (calculated strictly via landed domain status)
                for v in self.vassals.get(pid, []):
                    st = get_vassal_landed_status(self, v, pid)
                    if st["is_landed"]:
                        owner["gold"] += st["tax_paid"]
                        v["gold"] = v.get("gold", 150) + st["net_savings"]
                        v["tax_contribution"] = st["tax_paid"]
                        v["levy_contribution"] = st["levy_contribution"]
                    else:
                        # Landless noble holds no land/holdings -> generates 0 gold, pays 0 tax, provides 0 levies
                        v["tax_contribution"] = 0
                        v["levy_contribution"] = 0

        # Maintain standardized enemy AI feudal laws uniformly across all Danelaw vassals
        standardize_enemy_ai_laws(self)

        # 2. Modular Building Economic & Recruitment Tick
        processed_holdings = set()
        for coord, sdata in self.settlements.items():
            hid = sdata.get("id") or coord
            if hid in processed_holdings:
                continue
            processed_holdings.add(hid)

            htype = sdata.get("type", "city")
            if htype == "town":
                htype = "city"
            pid = sdata.get("province")
            prov = PROVINCES.get(pid)
            if not prov:
                continue

            is_crown = sdata.get("is_crown_demesne", False)
            prov_ruler = CHARACTERS.get(prov["owner"])

            if htype == "city":
                if is_crown and prov_ruler:
                    prov_ruler["gold"] += 3
                # City contributes +10 recruits per month to provincial levy pool
                prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + 10)

            elif htype == "fort":
                if is_crown and prov_ruler:
                    prov_ruler["gold"] += 1
                # Fort contributes +10 recruits per month to provincial levy pool
                prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + 10)

            elif htype == "barrack":
                lvl = sdata.get("level", 0)
                bstats = get_barrack_stats(lvl)
                upkeep = bstats["upkeep"]
                recruits = bstats["recruits"]

                if is_crown and prov_ruler:
                    prov_ruler["gold"] = max(0, prov_ruler["gold"] - upkeep)
                # Boost province levies pool directly based on upgrade level (+10 base, +5 per level)
                prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + recruits)

        # Army upkeep cost (1 gold per 100 Crown Demesne troops; Feudal Vassal Levies are FREE!)
        player_crown_field = sum(getattr(a, "crown_troops", 0) for a in self.armies if a.owner == self.player_id)
        upkeep = player_crown_field // 100
        self.player["gold"] = max(0, self.player["gold"] - upkeep)

        enemy_crown_field = sum(getattr(a, "crown_troops", 0) for a in self.armies if a.owner == self.enemy_id)
        enemy_upkeep = enemy_crown_field // 100
        self.enemy["gold"] = max(0, self.enemy["gold"] - enemy_upkeep)

        self.player["prestige"] += 1
        self.player["piety"] += 1
        self.enemy["prestige"] += 1

        # Vassal autonomous build request chance: ONLY IF Vassal has sufficient Gold AND owns a fief with free tiles!
        if not self.vassal_build_requests:
            player_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.player_id]
            if player_provs and random.random() < 0.35:
                eligible_petitions = []
                for pid in player_provs:
                    v_list = self.vassals.get(pid, [])
                    for v in v_list:
                        v_gold = v.get("gold", 0)
                        if v_gold >= 600:
                            v_fiefs = [f for f in self.fiefs.values() if f.get("province") == pid and (f.get("holder") == v["name"] or f.get("vassal_id") == v.get("id"))]
                            for f in v_fiefs:
                                free_tiles = [t for t in f.get("tiles", []) if t not in self.settlements]
                                if not free_tiles:
                                    continue
                                
                                # Try 2-tile fort if vassal has >= 1000g
                                pair = None
                                if v_gold >= 1000 and len(free_tiles) >= 2:
                                    free_set = set(free_tiles)
                                    for (c, r) in free_tiles:
                                        if (c + 1, r) in free_set:
                                            pair = [(c, r), (c + 1, r)]
                                            break
                                        elif (c, r + 1) in free_set:
                                            pair = [(c, r), (c, r + 1)]
                                            break
                                
                                if pair and v_gold >= 1000:
                                    eligible_petitions.append({
                                        "vassal": v["name"],
                                        "vassal_ref": v,
                                        "province_id": pid,
                                        "province_name": PROVINCES[pid]["name"],
                                        "fief_id": f["id"],
                                        "fief_name": f["name"],
                                        "build_tiles": pair,
                                        "build_type": "fort",
                                        "cost": 1000
                                    })
                                else:
                                    # 1-tile city petition
                                    eligible_petitions.append({
                                        "vassal": v["name"],
                                        "vassal_ref": v,
                                        "province_id": pid,
                                        "province_name": PROVINCES[pid]["name"],
                                        "fief_id": f["id"],
                                        "fief_name": f["name"],
                                        "build_tiles": [free_tiles[0]],
                                        "build_type": "city",
                                        "cost": 600
                                    })

                if eligible_petitions:
                    req_choice = random.choice(eligible_petitions)
                    self.vassal_build_requests.append(req_choice)
                    b_title = "Fort (1,000g)" if req_choice["build_type"] == "fort" else "City (600g)"
                    self.logs.append(f"Charter Petition: {req_choice['vassal']} petitions to build {b_title} inside {req_choice['fief_name']} ({req_choice['province_name']})!")

    def yearly_tick(self):
        self.player["age"] += 1
        self.enemy["age"] += 1
        self.logs.append(f"AD {self.year}: War rages across the lands of Britain.")

    def update_armies(self):
        # Sanity check: Clear in_battle flag for any army that has no enemy in its province
        for a in self.armies:
            opponents = [o for o in self.armies if o.province == a.province and o.owner != a.owner]
            if not opponents:
                a.in_battle = False

        # 1. Update movement
        for a in list(self.armies):
            if a.in_battle:
                # Armies locked in battle cannot move or show path arrows
                if a.path:
                    a.path = []
                    a.move_progress = 0.0
                continue

            if a.is_moving:
                a.move_progress += a.move_speed
                if a.move_progress >= 100.0:
                    a.province = a.path.pop(0)
                    a.move_progress = 0.0

                    # INTERCEPTION CHECK: if enemy is in this province, stop and fight
                    enemy_owner = self.enemy_id if a.owner == self.player_id else self.player_id
                    blockers = [e for e in self.armies
                                if e.province == a.province and e.owner == enemy_owner]
                    if blockers:
                        a.path = []
                        a.move_progress = 0.0
                        if a.is_demobilizing:
                            a.is_demobilizing = False
                            self.logs.append(f"Ambush! {a.name} was attacked while returning home!")
                        for b in blockers:
                            b.path = []
                            b.move_progress = 0.0
                            b.is_sieging = False

                    # If reached final destination with no blocker:
                    elif not a.path:
                        if a.is_demobilizing and a.province == a.flag_origin:
                            prov = PROVINCES.get(a.flag_origin)
                            if prov:
                                prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + a.troops)
                            self.logs.append(f"{a.name} arrived safely home in {prov['name']}. {a.troops:,} men demobilized to garrison.")
                            if a.id == self.selected_army_id:
                                self.selected_army_id = None
                            if a in self.armies:
                                self.armies.remove(a)
                        elif not a.is_demobilizing:
                            self.merge_armies_in_province(a.province, a.owner)

        # 2. Check Battles (Opposing armies in same province)
        for pid in list(PROVINCES.keys()):
            self.merge_armies_in_province(pid, self.player_id)
            self.merge_armies_in_province(pid, self.enemy_id)

            armies_in_prov = [a for a in self.armies if a.province == pid]
            p1_list = [a for a in armies_in_prov if a.owner == self.player_id]
            p2_list = [a for a in armies_in_prov if a.owner == self.enemy_id]

            if not (p1_list and p2_list):
                for a in armies_in_prov:
                    a.in_battle = False
                continue

            a1 = p1_list[0]
            a2 = p2_list[0]
            
            # Lock both hosts in combat and halt all marching, sieging, or demobilizing
            for a in p1_list + p2_list:
                a.in_battle = True
                a.path = []
                a.move_progress = 0.0
                a.is_sieging = False
                a.is_demobilizing = False
                a.courier_en_route = False
                a.is_mustering = False

            # One combat round per game-tick
            alfred_martial  = self.player["stats"]["martial"]
            halfdan_martial = self.enemy["stats"]["martial"]

            dmg_to_a2 = max(1, int(a1.troops * 0.08 * (1 + alfred_martial * 0.02))  + random.randint(10, 50))
            dmg_to_a1 = max(1, int(a2.troops * 0.08 * (1 + halfdan_martial * 0.02)) + random.randint(10, 50))

            a1.troops = max(0, a1.troops - dmg_to_a1)
            a2.troops = max(0, a2.troops - dmg_to_a2)
            if a1.troops > 0:
                a1.crown_troops = min(getattr(a1, "crown_troops", 0), a1.troops)
                a1.vassal_levies = a1.troops - a1.crown_troops
            if a2.troops > 0:
                a2.crown_troops = min(getattr(a2, "crown_troops", 0), a2.troops)
                a2.vassal_levies = a2.troops - a2.crown_troops

            if a1.troops <= 0 and a2.troops <= 0:
                self.logs.append(f"Both armies annihilated at {PROVINCES[pid]['name']}!")
                if a1 in self.armies: self.armies.remove(a1)
                if a2 in self.armies: self.armies.remove(a2)
            elif a1.troops <= 0:
                self.logs.append(f"Defeat! {a1.name} was wiped out at {PROVINCES[pid]['name']}!")
                if a1 in self.armies: self.armies.remove(a1)
                a2.in_battle = False
                a2.path = []
                a2.move_progress = 0.0
            elif a2.troops <= 0:
                self.logs.append(f"Glorious Victory! Destroyed the Viking host at {PROVINCES[pid]['name']}!")
                if a2 in self.armies: self.armies.remove(a2)
                a1.in_battle = False
                a1.path = []
                a1.move_progress = 0.0

        # 3. Check Sieges (City-by-City Siege in Enemy or Contested Province)
        for a in list(self.armies):
            if a not in self.armies:
                continue
            if a.is_moving or a.in_battle or a.is_mustering or a.courier_en_route or a.is_demobilizing:
                continue

            prov = PROVINCES[a.province]
            defenders = [enemy for enemy in self.armies if enemy.province == a.province and enemy.owner != a.owner]
            if defenders:
                a.is_sieging = False
                continue

            siegeable = get_siegeable_holdings(self, a.province, a.owner)
            is_enemy_prov = (prov["owner"] != a.owner)

            if siegeable:
                # Find current target or set to first available holding
                h_target_name, h_tiles = siegeable[0]
                a.is_sieging = True
                a.siege_target_name = h_target_name
                a.target_city = h_tiles[0]

                # Siege rate scaled by troops
                rate = max(4, int(a.troops / 250))
                a.siege_progress += rate

                if a.siege_progress >= 100:
                    a.siege_progress = 0
                    if is_enemy_prov:
                        # Occupy this holding!
                        for t in h_tiles:
                            self.settlements[t]["occupied_by"] = a.owner
                        
                        remaining = get_siegeable_holdings(self, a.province, a.owner)
                        if remaining:
                            self.logs.append(f"Holding Fallen! {a.name} captured {h_target_name}. {prov['name']} is now contested!")
                            a.target_city = remaining[0][1][0]
                            a.siege_target_name = remaining[0][0]
                        else:
                            # ALL holdings captured! Whole province flips!
                            prov["owner"] = a.owner
                            prov["color"] = list(PROVINCE_FACTION_COLORS.get(a.owner, {}).get(a.province, COLOR_WESSEX if a.owner == self.player_id else COLOR_DANELAW))
                            a.is_sieging = False
                            a.target_city = None
                            a.siege_target_name = None
                            for t in [coord for coord, s in self.settlements.items() if s.get("province") == a.province]:
                                self.settlements[t]["occupied_by"] = None
                            
                            if a.owner == self.player_id:
                                self.player["prestige"] += 100
                                self.logs.append(f"TOTAL VICTORY! All boroughs in {prov['name']} have fallen! Province conquered by Wessex!")
                            else:
                                self.enemy["prestige"] += 100
                                self.logs.append(f"DISASTER! All boroughs in {prov['name']} have fallen to the Danelaw!")
                    else:
                        # Friendly liberation of occupied holding!
                        for t in h_tiles:
                            self.settlements[t]["occupied_by"] = None
                        self.logs.append(f"Liberated! {a.name} reclaimed {h_target_name} for {prov['name']}!")
                        remaining = get_siegeable_holdings(self, a.province, a.owner)
                        if remaining:
                            a.target_city = remaining[0][1][0]
                            a.siege_target_name = remaining[0][0]
                        else:
                            a.is_sieging = False
                            a.target_city = None
                            a.siege_target_name = None
                            self.logs.append(f"Order Restored! {prov['name']} is fully liberated and no longer contested.")
            elif is_enemy_prov:
                # Enemy province with NO settlements: direct capture
                a.is_sieging = True
                rate = max(4, int(a.troops / 250))
                a.siege_progress += rate
                if a.siege_progress >= 100:
                    prov["owner"] = a.owner
                    prov["color"] = list(PROVINCE_FACTION_COLORS.get(a.owner, {}).get(a.province, COLOR_WESSEX if a.owner == self.player_id else COLOR_DANELAW))
                    a.is_sieging = False
                    a.siege_progress = 0
                    if a.owner == self.player_id:
                        self.player["prestige"] += 100
                        self.logs.append(f"Victory! {prov['name']} has been conquered by Wessex!")
                    else:
                        self.enemy["prestige"] += 100
                        self.logs.append(f"Disaster! {prov['name']} has fallen to the Danelaw!")
            else:
                a.is_sieging = False
                a.siege_progress = 0

    # ---------------------------------------------------------
    # AI (Halfdan Ragnarsson) - Intelligent Border Awareness, Mobilization & Retaliation
    # ---------------------------------------------------------
    def ai_routine(self):
        danelaw_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.enemy_id]
        if not danelaw_provs:
            return

        # 1. STANDARDIZE AI REALM LAWS
        # Automatically enforce uniform AI feudal taxes and levies (80% levy, 20% tax)
        standardize_enemy_ai_laws(self)

        # ---------------------------------------------------------
        # 2. RADAR & THREAT RECOGNITION
        # Senses both direct territorial incursions (inside Danelaw)
        # and border concentrations (in adjacent Saxon lands before entering).
        # ---------------------------------------------------------
        player_armies = [a for a in self.armies if a.owner == self.player_id and a.troops > 0]
        
        invading_threats = {}    # Danelaw pid -> list of invading player armies
        threatened_borders = {}  # Danelaw pid -> list of bordering player armies
        all_threat_armies = []
        
        for pa in player_armies:
            pa_locations = [pa.province]
            if pa.is_moving and pa.path:
                pa_locations.append(pa.path[-1])
            
            for loc in pa_locations:
                if loc in danelaw_provs:
                    invading_threats.setdefault(loc, []).append(pa)
                    if pa not in all_threat_armies:
                        all_threat_armies.append(pa)
                else:
                    for dp in danelaw_provs:
                        if loc in ADJACENCY.get(dp, []):
                            threatened_borders.setdefault(dp, []).append(pa)
                            if pa not in all_threat_armies:
                                all_threat_armies.append(pa)

        danelaw_armies = [a for a in self.armies if a.owner == self.enemy_id]
        total_viking_field = sum(a.troops for a in danelaw_armies)
        total_threat_troops = sum(pa.troops for pa in all_threat_armies)
        unraised_enemy_levies = sum(PROVINCES[pid].get("levies_current", 0) for pid in danelaw_provs)
        
        has_invasion = len(invading_threats) > 0
        has_border_threat = len(threatened_borders) > 0

        # ---------------------------------------------------------
        # 3. WAR MOBILIZATION (ALL-IN LEVY SUMMONS)
        # ---------------------------------------------------------
        should_mobilize = False
        if (has_invasion or has_border_threat) and unraised_enemy_levies > 0:
            should_mobilize = True
        elif len(danelaw_armies) == 0 and unraised_enemy_levies > 0:
            should_mobilize = True
        elif unraised_enemy_levies >= 150:
            should_mobilize = True
        elif total_viking_field < sum(pa.troops for pa in player_armies) * 0.8 and unraised_enemy_levies >= 60:
            should_mobilize = True

        if should_mobilize:
            count, men = self.raise_all_enemy_levies(is_emergency=(has_invasion or has_border_threat))
            if count > 0:
                if has_invasion:
                    inv_names = ", ".join([PROVINCES[dp]['name'].split()[0] for dp in invading_threats.keys()])
                    self.logs.append(f"⚔ INVASION ALERT! Saxon armies inside {inv_names}! Danelaw sounds ALL-IN war horns (+{men:,} men in {count} hosts)!")
                elif has_border_threat:
                    t_names = ", ".join([PROVINCES[dp]['name'].split()[0] for dp in threatened_borders.keys()])
                    self.logs.append(f"⚔ Raven Warning! Saxon armies massing near {t_names}! Danelaw sounds ALL-IN war horns (+{men:,} men in {count} hosts)!")
                else:
                    self.logs.append(f"Ravens squawk! The Danelaw has summoned ALL realm warbands (+{men:,} men in {count} hosts)!")

        # ---------------------------------------------------------
        # 4. IDENTIFY PRIMARY STRATEGIC RALLY POINT
        # ---------------------------------------------------------
        if has_invasion:
            # Emergency: Converge directly on invaded province to liberate/defend
            safe_rally = list(invading_threats.keys())[0]
        elif has_border_threat:
            # Border threat: Gather at the frontier to meet the enemy
            safe_rally = list(threatened_borders.keys())[0]
        else:
            # Standard rally: Jorvik capital
            safe_rally = "jorvik" if "jorvik" in danelaw_provs else danelaw_provs[0]

        # ---------------------------------------------------------
        # 5. RALLY & MARCH TO CONCENTRATE FORCES
        # ---------------------------------------------------------
        active_viking_armies = [a for a in self.armies if a.owner == self.enemy_id and not a.in_battle]
        for a in active_viking_armies:
            if a.is_mustering or a.courier_en_route:
                continue
            if a.province != safe_rally and not a.is_moving:
                path = find_shortest_path(a.province, safe_rally)
                if path and len(path) > 1:
                    a.path = path[1:]
                    a.move_progress = 0.0

        # Automatically merge ready Viking hosts in all Danelaw provinces
        for dp in danelaw_provs:
            self.merge_armies_in_province(dp, self.enemy_id)

        # ---------------------------------------------------------
        # 6. RETALIATION, SALLY-OUT & OFFENSIVE CAMPAIGN
        # ---------------------------------------------------------
        ready_hosts = [a for a in self.armies if a.owner == self.enemy_id and not a.is_mustering and not a.courier_en_route and not a.in_battle and not a.is_moving]
        if ready_hosts:
            ready_hosts.sort(key=lambda x: x.troops, reverse=True)
            main_host = ready_hosts[0]

            # SITUATION 1: Invaders are inside Danelaw territory!
            if has_invasion:
                target_inv_prov = list(invading_threats.keys())[0]
                if main_host.province != target_inv_prov:
                    path = find_shortest_path(main_host.province, target_inv_prov)
                    if path and len(path) > 1:
                        main_host.path = path[1:]
                        main_host.move_progress = 0.0
                        self.logs.append(f"⚔ Halfdan marches his Great Host ({main_host.troops:,} men) into {PROVINCES[target_inv_prov]['name']} to repel Saxon invaders!")

            # SITUATION 2: Enemy armies massing along the border!
            elif has_border_threat:
                target_border = list(threatened_borders.keys())[0]
                opposing_armies = threatened_borders.get(target_border, [])
                opp_troops = sum(oa.troops for oa in opposing_armies)

                if main_host.province != target_border:
                    # Advance to the border fortress to defend
                    path = find_shortest_path(main_host.province, target_border)
                    if path and len(path) > 1:
                        main_host.path = path[1:]
                        main_host.move_progress = 0.0
                        self.logs.append(f"⚔ Halfdan advances his Great Host ({main_host.troops:,} men) to {PROVINCES[target_border]['name']} to block Saxon invasion!")
                else:
                    # Main host is AT the border! Halfdan launches a FEROCIOUS RETALIATION (Serangan Balik)!
                    # He does not wait passively to be sieged. If he has capable warriors, he strikes!
                    if opposing_armies and main_host.troops >= 200 and (main_host.troops >= opp_troops * 0.50 or main_host.troops >= 600):
                        target_enemy_prov = opposing_armies[0].province
                        path = find_shortest_path(target_border, target_enemy_prov)
                        if path and len(path) > 1:
                            main_host.path = path[1:]
                            main_host.move_progress = 0.0
                            self.logs.append(f"⚔ RETALIATION! Halfdan sallies out from {PROVINCES[target_border]['name']} to counter-attack the Saxon army in {PROVINCES[target_enemy_prov]['name']}!")

            # SITUATION 3: Offensive Invasion into Saxon England!
            else:
                # If no immediate threat, Halfdan leads his Great Viking Army south into England!
                if main_host.troops >= 350:
                    player_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.player_id]
                    if player_provs:
                        border_targets = [p for p in player_provs if any(p in ADJACENCY.get(dp, []) for dp in danelaw_provs)]
                        target = random.choice(border_targets) if border_targets else random.choice(player_provs)
                        path = find_shortest_path(main_host.province, target)
                        if path and len(path) > 1:
                            main_host.path = path[1:]
                            main_host.move_progress = 0.0
                            self.logs.append(f"⚔ The Great Viking Army! Halfdan marches south into {PROVINCES[target]['name']} ({main_host.troops:,} warriors)!")

# -------------------------------------------------------------
# Main Game Loop
# -------------------------------------------------------------
def run_game():
    global screen
    if screen is None:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
    maximize_window()
    clock = pygame.time.Clock()

    reset_global_world_data()
    state = GameState()

    # Map Viewport & Base Tile Setup
    raw_grid = MAP_DATA["raw_grid"]
    BASE_TILE_W = 34
    BASE_TILE_H = 32
    VIEWPORT_CENTER_X = 575
    VIEWPORT_CENTER_Y = 385
    map_viewport = pygame.Rect(290, 53, 570, WINDOW_HEIGHT - 53)

    # Pre-map coordinate to 12 provinces
    cell_to_prov = {}
    for r, row in enumerate(raw_grid):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            prov_id = None
            if ch == "H": prov_id = "highlands"
            elif ch == "S": prov_id = "strathclyde"
            elif ch in ("T", "L"): prov_id = "lothian"
            elif ch == "B": prov_id = "bernicia"
            elif ch == "D": prov_id = "deira"
            elif ch == "Y": prov_id = "jorvik"
            elif ch == "M": prov_id = "mercia"
            elif ch == "E": prov_id = "east_anglia"
            elif ch == "W":
                prov_id = "wales" if r <= 17 else "wessex"
            elif ch == "K": prov_id = "kent_essex"
            elif ch == "C": prov_id = "cornwall"
            else: prov_id = "wessex"
            cell_to_prov[(c, r)] = prov_id

    # Compute TRUE province centroids in GRID units (scale & pan independent)
    prov_grid_sum = {}   # pid -> [sum_c, sum_r, count]
    for (c, r), pid in cell_to_prov.items():
        if pid not in prov_grid_sum:
            prov_grid_sum[pid] = [0, 0, 0]
        prov_grid_sum[pid][0] += c
        prov_grid_sum[pid][1] += r
        prov_grid_sum[pid][2] += 1

    prov_grid_centroids = {}
    for pid, (sc, sr, count) in prov_grid_sum.items():
        prov_grid_centroids[pid] = (sc / count, sr / count)

    # Dynamically update ADJACENCY from map tile grid for 100% map-agnostic pathfinding
    dyn_adj = build_dynamic_province_adjacency(cell_to_prov)
    ADJACENCY.clear()
    ADJACENCY.update(dyn_adj)

    # Precompute border grid midpoints between touching/neighboring provinces
    border_grid_sums = {}
    for (c, r), pid_a in cell_to_prov.items():
        for dc in range(-2, 3):
            for dr in range(-2, 3):
                if (dc == 0 and dr == 0) or (abs(dc) + abs(dr) > 2):
                    continue
                pid_b = cell_to_prov.get((c + dc, r + dr))
                if pid_b and pid_b != pid_a and pid_b in ADJACENCY.get(pid_a, []):
                    pair_key = (pid_a, pid_b)
                    if pair_key not in border_grid_sums:
                        border_grid_sums[pair_key] = [0.0, 0.0, 0]
                    border_grid_sums[pair_key][0] += (c + (c + dc)) / 2.0
                    border_grid_sums[pair_key][1] += (r + (r + dr)) / 2.0
                    border_grid_sums[pair_key][2] += 1

    border_grid_centroids = {}
    for pair_key, (sc, sr, count) in border_grid_sums.items():
        border_grid_centroids[pair_key] = (sc / count, sr / count)

    # Initialize 1:1 STARTER FIEFS AND CITIES FOR EVERY VASSAL IN THE PROVINCE!
    prov_tile_list = {}
    for (c, r), pid in cell_to_prov.items():
        prov_tile_list.setdefault(pid, []).append((c, r))

    def setup_province_starter_cities(target_state):
        target_state.settlements = {}
        target_state.fiefs = {}
        fief_counter = 1
        settlement_counter = 1
        used_tiles_by_prov = {pid: set() for pid in prov_tile_list.keys()}

        # -------------------------------------------------------------
        # 1. RULER PERSONAL DEMESNE
        # Penguasa starter default: 1 City (1 tile), 1 Fort (2 tiles), 1 Barracks (1 tile) = 4 tiles
        # -------------------------------------------------------------
        ruler_specs = [
            # King Alfred (Wessex)
            {
                "owner": target_state.player_id,
                "lord": target_state.player["name"],
                "province": "wessex",
                "holdings": [
                    {"type": "city", "name": "Royal City of Winchester", "fief": "Crown Demesne of Winchester", "tiles": 1},
                    {"type": "fort", "name": "Royal Citadel of Wilton", "fief": "Crown Demesne of Wilton", "tiles": 2},
                    {"type": "barrack", "name": "King's Saxon Barracks", "fief": "Crown Demesne of Aldhelm's", "tiles": 1, "level": 0}
                ]
            },
            # Jarl Halfdan (Jorvik)
            {
                "owner": target_state.enemy_id,
                "lord": target_state.enemy["name"],
                "province": "jorvik",
                "holdings": [
                    {"type": "fort", "name": "Great Hall Citadel of Eoforwic", "fief": "Crown Demesne of Eoforwic", "tiles": 2},
                    {"type": "barrack", "name": "Halfdan's War Camp Barracks", "fief": "Crown Demesne of the Raven", "tiles": 1, "level": 0}
                ]
            }
        ]

        for r_spec in ruler_specs:
            pid = r_spec["province"]
            tiles = prov_tile_list.get(pid, [])
            tile_set = set(tiles)
            used = used_tiles_by_prov[pid]

            for h_spec in r_spec["holdings"]:
                h_type = h_spec["type"]
                needed = h_spec["tiles"]
                allocated = []

                if needed == 2:
                    for (c, r) in tiles:
                        if (c, r) not in used and (c + 1, r) in tile_set and (c + 1, r) not in used:
                            allocated = [(c, r), (c + 1, r)]
                            break
                    if not allocated:
                        for (c, r) in tiles:
                            if (c, r) not in used and (c, r + 1) in tile_set and (c, r + 1) not in used:
                                allocated = [(c, r), (c, r + 1)]
                                break
                else:
                    for (c, r) in tiles:
                        if (c, r) not in used:
                            allocated = [(c, r)]
                            break

                if allocated:
                    s_id = f"settlement_{settlement_counter}"
                    settlement_counter += 1
                    for t in allocated:
                        used.add(t)
                        target_state.settlements[t] = {
                            "id": s_id,
                            "province": pid,
                            "type": h_type,
                            "name": h_spec["name"],
                            "lord": f"{r_spec['lord']} (Crown Demesne)",
                            "vassal_id": None,
                            "is_crown_demesne": True,
                            "is_crown_fief": True,
                            "level": h_spec.get("level", 0)
                        }
                    fid = f"fief_{fief_counter}"
                    fief_counter += 1
                    target_state.fiefs[fid] = {
                        "id": fid,
                        "province": pid,
                        "tiles": list(allocated),
                        "name": h_spec["fief"],
                        "holder": r_spec["lord"],
                        "vassal_id": None,
                        "is_crown_demesne": True
                    }

        # -------------------------------------------------------------
        # 2. VASSAL STARTER HOLDINGS & FIEFS
        # Every vassal is randomized: gets 1 City (1 tile) OR 1 Fort (2 tiles)
        # -------------------------------------------------------------
        for pid, tiles in prov_tile_list.items():
            v_list = target_state.vassals.get(pid, [])
            tile_set = set(tiles)
            used = used_tiles_by_prov[pid]

            for idx, v in enumerate(v_list):
                b_type = random.choice(["city", "fort"])
                allocated = []

                if b_type == "fort":
                    for (c, r) in tiles:
                        if (c, r) not in used and (c + 1, r) in tile_set and (c + 1, r) not in used:
                            allocated = [(c, r), (c + 1, r)]
                            break
                    if not allocated:
                        for (c, r) in tiles:
                            if (c, r) not in used and (c, r + 1) in tile_set and (c, r + 1) not in used:
                                allocated = [(c, r), (c, r + 1)]
                                break
                    if not allocated:
                        b_type = "city"

                if b_type == "city" and not allocated:
                    for (c, r) in tiles:
                        if (c, r) not in used:
                            allocated = [(c, r)]
                            break

                if allocated:
                    s_id = f"settlement_{settlement_counter}"
                    settlement_counter += 1
                    v_name_parts = v["name"].split()
                    v_label = v_name_parts[1] if len(v_name_parts) > 1 else v["name"]

                    if b_type == "city":
                        holding_name = f"{v_label}'s {random.choice(['Borough', 'Burgh', 'Town', 'Market'])}"
                    else:
                        holding_name = f"{v_label}'s {random.choice(['Keep', 'Castle', 'Fortress', 'Stronghold'])}"

                    for t in allocated:
                        used.add(t)
                        target_state.settlements[t] = {
                            "id": s_id,
                            "province": pid,
                            "type": b_type,
                            "name": holding_name,
                            "lord": v["name"],
                            "vassal_id": v["id"],
                            "is_crown_demesne": False,
                            "is_crown_fief": False,
                            "level": 0
                        }
                    v["city_name"] = holding_name
                    v["tiles"] = list(allocated)
                    fid = f"fief_{fief_counter}"
                    fief_counter += 1
                    target_state.fiefs[fid] = {
                        "id": fid,
                        "province": pid,
                        "tiles": list(allocated),
                        "name": f"Barony of {v_label}",
                        "holder": v["name"],
                        "vassal_id": v["id"],
                        "is_crown_demesne": False
                    }
                else:
                    v["city_name"] = None
                    v["tiles"] = []

        # Synchronize target_state's counter so newly carved fiefs never collide with starter fiefs!
        target_state.fief_id_counter = max(target_state.fief_id_counter, fief_counter + 10)
        target_state.settlement_id_counter = max(target_state.settlement_id_counter, settlement_counter + 10)

        # Synchronize province garrison and tax strictly to physical holdings on map!
        sync_province_holdings_stats(target_state, is_init=True)

        # Synchronize all vassals' initial levy and tax contributions strictly according to landed status
        for pid in PROVINCES:
            for v in target_state.vassals.get(pid, []):
                st = get_vassal_landed_status(target_state, v, pid)
                v["tax_contribution"] = st["tax_paid"]
                v["levy_contribution"] = st["levy_contribution"]

        # Standardize enemy AI laws uniformly across all Danelaw vassals
        standardize_enemy_ai_laws(target_state)

    # Setup starter cities and fiefs matching each vassal exactly
    setup_province_starter_cities(state)

    def carve_new_fief(target_state, province_id):
        p_tiles = [coord for coord, pid in cell_to_prov.items() if pid == province_id]
        claimed_tiles = set()
        for f in target_state.fiefs.values():
            if f.get("province") == province_id:
                for t in f.get("tiles", []):
                    claimed_tiles.add(t)

        free_tiles = [t for t in p_tiles if t not in claimed_tiles]

        if len(free_tiles) < 1:
            pname = PROVINCES[province_id]["name"]
            target_state.logs.append(f"Cannot carve fief: No unclaimed tiles left in {pname}. Dissolve an existing fief first.")
            return None

        target_state.fief_id_counter += 1
        fid = f"fief_{target_state.fief_id_counter}"
        pname = PROVINCES[province_id]["name"].split()[0]
        cur_prov_fief_count = sum(1 for f in target_state.fiefs.values() if f.get("province") == province_id)
        target_state.fiefs[fid] = {
            "id": fid,
            "province": province_id,
            "tiles": [],
            "holder": None,
            "name": f"{pname} Fief #{cur_prov_fief_count + 1}",
            "vassal_id": None,
            "is_crown_demesne": False,
            "is_newly_carved": True
        }
        target_state.selected_fief_id = fid
        target_state.editing_fief_id = fid
        target_state.selected_settlement = None
        target_state.logs.append(f"Partition Mode: Click green unclaimed tiles on map for '{target_state.fiefs[fid]['name']}', then click DONE.")
        return fid

    # Build reverse lookup: pixel -> province (for accurate click detection)
    # cell_to_prov already handles this via tile grid

    running = True
    # Box-selection state (separate from drag_start on GameState for clarity)
    box_start = None   # (x,y) where drag started
    box_end   = None   # (x,y) current mouse position while dragging

    while running:
        dt = clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False
        right_clicked = False

        # Compute dynamic frame camera transform
        curr_tile_w = max(18, int(BASE_TILE_W * state.zoom))
        curr_tile_h = max(16, int(BASE_TILE_H * state.zoom))
        default_ox = VIEWPORT_CENTER_X - int(10 * curr_tile_w)
        default_oy = VIEWPORT_CENTER_Y - int(13 * curr_tile_h)
        origin_x = default_ox + state.cam_pan_x
        origin_y = default_oy + state.cam_pan_y

        def get_prov_anchor(pid):
            if pid not in prov_grid_centroids:
                return (0, 0)
            gc, gr = prov_grid_centroids[pid]
            return (int(origin_x + gc * curr_tile_w + curr_tile_w / 2),
                    int(origin_y + gr * curr_tile_h + curr_tile_h / 2))

        def get_border_midpoint(pid_a, pid_b):
            pair_key = (pid_a, pid_b)
            if pair_key in border_grid_centroids:
                gc, gr = border_grid_centroids[pair_key]
                return (int(origin_x + gc * curr_tile_w + curr_tile_w / 2),
                        int(origin_y + gr * curr_tile_h + curr_tile_h / 2))
            pair_rev = (pid_b, pid_a)
            if pair_rev in border_grid_centroids:
                gc, gr = border_grid_centroids[pair_rev]
                return (int(origin_x + gc * curr_tile_w + curr_tile_w / 2),
                        int(origin_y + gr * curr_tile_h + curr_tile_h / 2))
            return None

        province_anchors = {pid: get_prov_anchor(pid) for pid in prov_grid_centroids}

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEWHEEL:
                r_panel_rect = pygame.Rect(860, 62, 330, WINDOW_HEIGHT - 72)
                l_panel_rect = pygame.Rect(10, 62, 290, WINDOW_HEIGHT - 72)
                if r_panel_rect.collidepoint(mouse_pos) and state.right_tab == "fiefs":
                    if event.y > 0:
                        state.fief_page = max(0, state.fief_page - 1)
                    elif event.y < 0:
                        state.fief_page += 1
                elif l_panel_rect.collidepoint(mouse_pos) and state.left_tab == "vassals":
                    if event.y > 0:
                        state.vassal_page = max(0, state.vassal_page - 1)
                    elif event.y < 0:
                        state.vassal_page += 1
                elif l_panel_rect.collidepoint(mouse_pos) and state.left_tab == "demesne":
                    if event.y > 0:
                        state.demesne_page = max(0, state.demesne_page - 1)
                    elif event.y < 0:
                        state.demesne_page += 1
                elif l_panel_rect.collidepoint(mouse_pos) and state.left_tab == "laws":
                    if event.y > 0:
                        state.laws_page = max(0, state.laws_page - 1)
                    elif event.y < 0:
                        state.laws_page += 1
                elif l_panel_rect.collidepoint(mouse_pos) and state.left_tab == "economy":
                    if event.y > 0:
                        state.economy_vassal_page = max(0, state.economy_vassal_page - 1)
                    elif event.y < 0:
                        state.economy_vassal_page += 1
                elif map_viewport.collidepoint(mouse_pos):
                    old_zoom = state.zoom
                    zoom_delta = 0.12 * event.y
                    new_zoom = max(state.min_zoom, min(state.max_zoom, round(state.zoom + zoom_delta, 2)))
                    if new_zoom != old_zoom:
                        old_tw = max(18, int(BASE_TILE_W * old_zoom))
                        old_th = max(16, int(BASE_TILE_H * old_zoom))
                        old_ox = (VIEWPORT_CENTER_X - int(10 * old_tw)) + state.cam_pan_x
                        old_oy = (VIEWPORT_CENTER_Y - int(13 * old_th)) + state.cam_pan_y
                        
                        mx, my = mouse_pos
                        gc = (mx - old_ox) / old_tw
                        gr = (my - old_oy) / old_th
                        
                        new_tw = max(18, int(BASE_TILE_W * new_zoom))
                        new_th = max(16, int(BASE_TILE_H * new_zoom))
                        new_def_x = VIEWPORT_CENTER_X - int(10 * new_tw)
                        new_def_y = VIEWPORT_CENTER_Y - int(13 * new_th)
                        
                        new_ox = mx - gc * new_tw
                        new_oy = my - gr * new_th
                        state.cam_pan_x = int(new_ox - new_def_x)
                        state.cam_pan_y = int(new_oy - new_def_y)
                        state.zoom = new_zoom

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
                    box_start = event.pos
                    box_end   = event.pos
                elif event.button == 2:
                    # Middle-click drag to pan camera
                    state.is_panning = True
                    state.pan_start_mouse = event.pos
                    state.pan_start_cam = (state.cam_pan_x, state.cam_pan_y)
                elif event.button == 3:
                    right_clicked = True

            elif event.type == pygame.MOUSEMOTION:
                if box_start:
                    box_end = event.pos
                if state.is_panning:
                    dx = event.pos[0] - state.pan_start_mouse[0]
                    dy = event.pos[1] - state.pan_start_mouse[1]
                    state.cam_pan_x = state.pan_start_cam[0] + dx
                    state.cam_pan_y = state.pan_start_cam[1] + dy

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    state.is_panning = False
                if event.button == 1 and box_start:
                    # Build selection rect
                    x1, y1 = box_start
                    x2, y2 = box_end
                    sel_rect = pygame.Rect(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
                    # Only treat as drag if moved >5 px (avoid accidental click-select)
                    if sel_rect.width > 5 or sel_rect.height > 5:
                        state.selected_army_ids = []
                        for a in state.armies:
                            if a.owner == state.player_id:
                                ax, ay = province_anchors.get(a.province, (0, 0))
                                # Interpolate badge pos if moving
                                if a.is_moving and a.next_province:
                                    nxt = province_anchors.get(a.next_province, (ax, ay))
                                    pct = a.move_progress / 100.0
                                    ax = int(ax + (nxt[0] - ax) * pct)
                                    ay = int(ay + (nxt[1] - ay) * pct)
                                badge_rect = pygame.Rect(ax - curr_tile_w, ay - curr_tile_h, curr_tile_w * 2, int(curr_tile_h * 1.5))
                                if sel_rect.colliderect(badge_rect):
                                    state.selected_army_ids.append(a.id)
                        if state.selected_army_ids:
                            state.selected_army_id = state.selected_army_ids[0]
                    box_start = None
                    box_end   = None

            elif event.type == pygame.KEYDOWN:
                is_popup_open = bool(state.vassal_build_requests or state.granting_fief_id or state.inspecting_vassal or state.inspecting_ruler or state.vassal_build_confirm)
                if is_popup_open:
                    if event.key == pygame.K_ESCAPE:
                        if state.inspecting_ruler:
                            state.inspecting_ruler = None
                        elif state.inspecting_vassal:
                            state.inspecting_vassal = None
                        elif state.granting_fief_id:
                            state.granting_fief_id = None
                        elif state.vassal_build_confirm:
                            state.vassal_build_confirm = None
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                        # Queue intended speed to resume when popup is closed
                        state.pre_popup_speed = int(event.unicode)
                else:
                    if event.key == pygame.K_SPACE:
                        state.speed = 0 if state.speed > 0 else 3
                    elif event.key == pygame.K_1:
                        state.speed = 1
                    elif event.key == pygame.K_2:
                        state.speed = 2
                    elif event.key == pygame.K_3:
                        state.speed = 3
                    elif event.key == pygame.K_4:
                        state.speed = 4
                    elif event.key == pygame.K_5:
                        state.speed = 5
                    elif event.key == pygame.K_r:
                        state.raise_all_levies()
                    elif event.key == pygame.K_m:
                        if state.selected_province:
                            state.rally_all_armies_to(state.selected_province)
                    elif event.key == pygame.K_b:
                        # Toggle Build Mode
                        state.build_mode = not state.build_mode
                    elif event.key == pygame.K_t:
                        # Rotate building orientation
                        state.build_orientation = "V" if state.build_orientation == "H" else "H"
                    elif event.key == pygame.K_ESCAPE:
                        if state.build_mode:
                            state.build_mode = False
                        else:
                            # Clear selection
                            state.selected_army_ids = []
                            state.selected_army_id  = None
                    elif event.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()

            elif event.type == pygame.VIDEORESIZE:
                pass

        # -------------------------------------------------------------
        # POPUP MODAL AUTO-PAUSE & AUTO-RESUME SYSTEM
        # -------------------------------------------------------------
        is_popup_active = bool(state.vassal_build_requests or state.granting_fief_id or state.inspecting_vassal or state.inspecting_ruler or state.vassal_build_confirm)
        if is_popup_active:
            if not state.popup_was_active:
                if state.speed > 0:
                    state.pre_popup_speed = state.speed
                    state.speed = 0
                    state.logs.append("⏸ Royal Council: Game paused for royal decision.")
                state.popup_was_active = True
        else:
            if state.popup_was_active:
                if state.pre_popup_speed is not None and state.pre_popup_speed > 0:
                    state.speed = state.pre_popup_speed
                    state.logs.append(f"▶ Resumed game speed ({state.speed}x).")
                    state.pre_popup_speed = None
                state.popup_was_active = False

        # Inhibit background dragging/ordering/clicking when modal popup is open
        modal_mouse_clicked = mouse_clicked
        if is_popup_active:
            mouse_clicked = False
            box_start = None
            box_end = None
            right_clicked = False
        game_mouse_clicked = mouse_clicked

        # Smooth keyboard pan navigation (Arrows / WASD)
        keys = pygame.key.get_pressed()
        pan_step = int(12 / max(0.5, state.zoom))
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            state.cam_pan_x += pan_step
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            state.cam_pan_x -= pan_step
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            state.cam_pan_y += pan_step
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            state.cam_pan_y -= pan_step

        # Right-click march orders for selected armies (box-select or single selected army)
        if right_clicked:
            armies_to_order = []
            if state.selected_army_ids:
                armies_to_order = [a for a in state.armies if a.id in state.selected_army_ids and a.owner == state.player_id]
            elif state.selected_army_id:
                sel_single = next((a for a in state.armies if a.id == state.selected_army_id and a.owner == state.player_id), None)
                if sel_single:
                    armies_to_order = [sel_single]

            if armies_to_order:
                # Accurate province detection: reverse-lookup tile under cursor
                mx, my = mouse_pos
                col_idx = int((mx - origin_x) // curr_tile_w)
                row_idx = int((my - origin_y) // curr_tile_h)
                target_province = cell_to_prov.get((col_idx, row_idx))
                if target_province:
                    for army_obj in armies_to_order:
                        state.order_army_march(army_obj, target_province)
        # Time advancement
        if state.speed > 0:
            state.tick_timer += dt
            tick_interval = state.speed_factors.get(state.speed, 500)
            if state.tick_timer >= tick_interval:
                state.advance_day()
                state.tick_timer = 0


        # Background
        screen.fill(COLOR_BG)

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
            reset_global_world_data()
            state = GameState()
            setup_province_starter_cities(state)
            state.logs.append("Game reset to 1 January 867 AD! Vassals & cities synchronized.")

        # ---------------------------------------------------------
        # 2. LEFT PANEL: PLAYER RULER & ACTIVE FORCES
        # ---------------------------------------------------------
        left_panel = pygame.Rect(10, 62, 290, WINDOW_HEIGHT - 72)
        pygame.draw.rect(screen, COLOR_PANEL_BG, left_panel, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, left_panel, 2, border_radius=6)

        # Portrait & Wessex Shield (Clickable Ruler Card)
        r_card_p = pygame.Rect(20, 70, 270, 96)
        is_rcp_hov = r_card_p.collidepoint(mouse_pos)
        if is_rcp_hov:
            pygame.draw.rect(screen, (45, 55, 75), r_card_p, border_radius=6)
            pygame.draw.rect(screen, COLOR_GOLD, r_card_p, 1, border_radius=6)

        p_img = portrait_cache.get(state.player_id)
        if p_img:
            screen.blit(p_img, (25, 75))
            pygame.draw.rect(screen, COLOR_GOLD, (25, 75, 64, 64), 1)
        c_img = coa_cache.get(state.player_id)
        if c_img:
            screen.blit(c_img, (88, 125))

        # Ruler Info
        name_surf = font_md.render(state.player["name"], True, COLOR_GOLD if is_rcp_hov else COLOR_TEXT_WHITE)
        title_surf = font_sm.render(state.player["realm"], True, COLOR_GOLD)
        dynasty_surf = font_sm.render(f"Martial Skill: {state.player['stats']['martial']}", True, COLOR_TEXT_RED)
        age_surf = font_sm.render(f"Age: {state.player['age']} • Gold: {state.player['gold']}", True, COLOR_TEXT_MUTED)

        screen.blit(name_surf, (115, 75))
        screen.blit(title_surf, (115, 96))
        screen.blit(dynasty_surf, (115, 116))
        screen.blit(age_surf, (115, 134))

        if mouse_clicked and is_rcp_hov:
            state.inspecting_ruler = state.player_id
            state.logs.append(f"Inspecting Sovereign Dossier for {state.player['name']}.")

        # Realm Mobilization Buttons
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 172), (285, 172), 1)
        
        # Raise All Button
        btn_raise_all = pygame.Rect(25, 185, 125, 36)
        b_hover = btn_raise_all.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (40, 110, 60) if b_hover else (30, 80, 45), btn_raise_all, border_radius=4)
        pygame.draw.rect(screen, COLOR_TEXT_GREEN, btn_raise_all, 1, border_radius=4)
        screen.blit(font_sm.render("RAISE ALL (R)", True, COLOR_TEXT_WHITE), (35, 193))
        if mouse_clicked and b_hover:
            state.raise_all_levies()

        # Disband All Button
        btn_disband_all = pygame.Rect(160, 185, 125, 36)
        b_hover_d = btn_disband_all.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (100, 40, 40) if b_hover_d else (75, 30, 30), btn_disband_all, border_radius=4)
        pygame.draw.rect(screen, COLOR_TEXT_RED, btn_disband_all, 1, border_radius=4)
        screen.blit(font_sm.render("DISBAND ALL", True, COLOR_TEXT_WHITE), (175, 193))
        if mouse_clicked and b_hover_d:
            for a in list(state.armies):
                if a.owner == state.player_id:
                    state.disband_army(a)

        # ---------------------------------------------------------
        # Left Panel Sub-Tabs: [ ⚔ Armies ]  [ ♟ Vassals ]  [ ♚ Demesne ]
        #                      [ ⚖ Realm Laws ]     [ ◆ In/Expense ]
        # ---------------------------------------------------------
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 233), (285, 233), 1)
        tab_y = 236
        tab_armies = pygame.Rect(25, tab_y, 84, 25)
        tab_vassals = pygame.Rect(113, tab_y, 84, 25)
        tab_demesne = pygame.Rect(201, tab_y, 84, 25)
        tab_laws = pygame.Rect(25, tab_y + 29, 127, 25)
        tab_economy = pygame.Rect(156, tab_y + 29, 129, 25)
        
        is_hov_ta = tab_armies.collidepoint(mouse_pos)
        is_hov_tv = tab_vassals.collidepoint(mouse_pos)
        is_hov_td = tab_demesne.collidepoint(mouse_pos)
        is_hov_tl = tab_laws.collidepoint(mouse_pos)
        is_hov_te = tab_economy.collidepoint(mouse_pos)
        
        is_a_active = (state.left_tab == "armies")
        is_v_active = (state.left_tab == "vassals")
        is_d_active = (state.left_tab == "demesne")
        is_l_active = (state.left_tab == "laws")
        is_e_active = (state.left_tab == "economy")
        
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
            if (f.get("vassal_id") is None and
                PROVINCES.get(f.get("province"), {}).get("owner") == state.player_id and
                (f.get("holder") == state.player["name"] or f.get("is_crown_demesne"))):
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
            if PROVINCES.get(pid, {}).get("owner") == state.player_id and (sdata.get("is_crown_demesne") or sdata.get("vassal_id") is None):
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

        if mouse_clicked and is_hov_ta:
            state.left_tab = "armies"
        elif mouse_clicked and is_hov_tv:
            state.left_tab = "vassals"
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
                    a_rect = pygame.Rect(25, ay, 260, 44)
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
                key=lambda p: (0 if p == "wessex" else 1, PROVINCES.get(p, {}).get("name", p))
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

                    p_card = pygame.Rect(25, fy, 260, 50)
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
                btn_prev = pygame.Rect(25, py_btn, 80, 26)
                btn_next = pygame.Rect(205, py_btn, 80, 26)
                is_prev_hov = btn_prev.collidepoint(mouse_pos)
                is_next_hov = btn_next.collidepoint(mouse_pos)

                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
                screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.demesne_page > 0 else COLOR_TEXT_MUTED), (42, py_btn + 5))

                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
                screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.demesne_page < max_pages - 1 else COLOR_TEXT_MUTED), (222, py_btn + 5))

                page_str = f"Page {state.demesne_page + 1}/{max_pages}"
                p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
                screen.blit(p_lbl, (115 + (80 - p_lbl.get_width()) // 2, py_btn + 5))

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
                    f_rect = pygame.Rect(25, fy, 260, 50)
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
                btn_prev = pygame.Rect(25, py_btn, 80, 26)
                btn_next = pygame.Rect(205, py_btn, 80, 26)

                is_prev_hov = btn_prev.collidepoint(mouse_pos)
                is_next_hov = btn_next.collidepoint(mouse_pos)

                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
                screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.demesne_page > 0 else COLOR_TEXT_MUTED), (42, py_btn + 5))

                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
                screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.demesne_page < max_pages - 1 else COLOR_TEXT_MUTED), (222, py_btn + 5))

                page_str = f"Page {state.demesne_page + 1}/{max_pages}"
                p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
                screen.blit(p_lbl, (115 + (80 - p_lbl.get_width()) // 2, py_btn + 5))

                if mouse_clicked and is_prev_hov and state.demesne_page > 0:
                    state.demesne_page -= 1
                elif mouse_clicked and is_next_hov and state.demesne_page < max_pages - 1:
                    state.demesne_page += 1

        elif state.left_tab == "vassals":
            # Realm Vassals Directory (All vassals across Kingdom of Wessex)
            realm_vassals = []
            for pid, prov in PROVINCES.items():
                if prov["owner"] == state.player_id:
                    for v in state.vassals.get(pid, []):
                        realm_vassals.append((pid, v))
            
            total_v = len(realm_vassals)
            header_lbl = font_md.render(f"Realm Vassals ({total_v} Lords)", True, COLOR_GOLD)
            screen.blit(header_lbl, (25, 302))
            
            per_page = 5
            max_pages = max(1, (total_v + per_page - 1) // per_page)
            state.vassal_page = max(0, min(getattr(state, "vassal_page", 0), max_pages - 1))
            
            start_i = state.vassal_page * per_page
            cur_page_vassals = realm_vassals[start_i:start_i + per_page]
            
            vy = 328
            for v_pid, v_data in cur_page_vassals:
                v_card = pygame.Rect(25, vy, 260, 50)
                is_vc_hov = v_card.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (50, 60, 78) if is_vc_hov else (34, 40, 52), v_card, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if is_vc_hov else COLOR_PANEL_BORDER, v_card, 1, border_radius=4)
                
                prov_short = PROVINCES[v_pid]["name"].split()[0]
                screen.blit(font_xs.render(f"♟ {v_data['name']}", True, COLOR_GOLD), (32, vy + 4))
                p_tag = font_xs.render(f"[{prov_short}]", True, (140, 200, 255))
                screen.blit(p_tag, (280 - p_tag.get_width(), vy + 4))
                
                st = get_vassal_landed_status(state, v_data, v_pid)
                h_name = v_data.get("city_name") if st["is_landed"] else "Landless Noble (Unlanded)"
                screen.blit(font_xs.render(f"Fief: {h_name}", True, (210, 220, 235)), (32, vy + 17))
                
                levy_txt = f"+{st['levy_contribution']}" if st["is_landed"] else "0"
                tax_txt = f"+{st['tax_paid']}g/m" if st["is_landed"] else "0g/m"
                screen.blit(font_xs.render(f"Gold: {v_data['gold']}g  •  Levy: {levy_txt}  •  Tax: {tax_txt}", True, COLOR_TEXT_MUTED), (32, vy + 30))
                
                if mouse_clicked and is_vc_hov:
                    state.selected_province = v_pid
                    state.inspecting_vassal = {"province": v_pid, "vassal": v_data}
                    if v_data.get("tiles"):
                        state.selected_settlement = v_data["tiles"][0]
                    state.logs.append(f"Opened royal dossier for vassal {v_data['name']}.")
                
                vy += 54
                
            # Pagination Controls at bottom
            py_btn = 645
            btn_prev = pygame.Rect(25, py_btn, 80, 26)
            btn_next = pygame.Rect(205, py_btn, 80, 26)
            
            is_prev_hov = btn_prev.collidepoint(mouse_pos)
            is_next_hov = btn_next.collidepoint(mouse_pos)
            
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
            screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.vassal_page > 0 else COLOR_TEXT_MUTED), (42, py_btn + 5))
            
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
            screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.vassal_page < max_pages - 1 else COLOR_TEXT_MUTED), (222, py_btn + 5))
            
            page_str = f"Page {state.vassal_page + 1}/{max_pages}"
            p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
            screen.blit(p_lbl, (115 + (80 - p_lbl.get_width()) // 2, py_btn + 5))
            
            if mouse_clicked and is_prev_hov and state.vassal_page > 0:
                state.vassal_page -= 1
            elif mouse_clicked and is_next_hov and state.vassal_page < max_pages - 1:
                state.vassal_page += 1

        elif state.left_tab == "laws":
            # Feudal Realm Laws View (Customizable per-vassal tax and levy rates 0% - 90%)
            if not hasattr(state, "laws_subtab") or state.laws_subtab not in ("tax", "levy"):
                state.laws_subtab = "tax"

            tab_tax_law = pygame.Rect(25, 298, 126, 24)
            tab_levy_law = pygame.Rect(154, 298, 126, 24)
            is_hov_tax_law = tab_tax_law.collidepoint(mouse_pos)
            is_hov_levy_law = tab_levy_law.collidepoint(mouse_pos)

            is_tax_active = (state.laws_subtab == "tax")
            is_levy_active = (state.laws_subtab == "levy")

            # Draw Tax Sub-tab
            pygame.draw.rect(screen, (60, 48, 20) if is_tax_active else (COLOR_BUTTON_HOVER if is_hov_tax_law else (35, 40, 52)), tab_tax_law, border_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD if is_tax_active else (80, 110, 150), tab_tax_law, 1, border_radius=4)
            t_tax_lbl = font_xs.render("◆ TAX LAWS", True, COLOR_GOLD if is_tax_active else (200, 220, 245))
            screen.blit(t_tax_lbl, (tab_tax_law.x + (tab_tax_law.w - t_tax_lbl.get_width()) // 2, tab_tax_law.y + 4))

            # Draw Levy Sub-tab
            pygame.draw.rect(screen, (60, 48, 20) if is_levy_active else (COLOR_BUTTON_HOVER if is_hov_levy_law else (35, 40, 52)), tab_levy_law, border_radius=4)
            pygame.draw.rect(screen, COLOR_GOLD if is_levy_active else (80, 110, 150), tab_levy_law, 1, border_radius=4)
            t_levy_lbl = font_xs.render("⚔ LEVY LAWS", True, COLOR_GOLD if is_levy_active else (200, 220, 245))
            screen.blit(t_levy_lbl, (tab_levy_law.x + (tab_levy_law.w - t_levy_lbl.get_width()) // 2, tab_levy_law.y + 4))

            if mouse_clicked and is_hov_tax_law and not is_tax_active:
                state.laws_subtab = "tax"
                state.laws_page = 0
            elif mouse_clicked and is_hov_levy_law and not is_levy_active:
                state.laws_subtab = "levy"
                state.laws_page = 0

            # -------------------------------------------------------------
            # Universal Realm Law Enactment Bar ("SAMARATAKAN SEMUA")
            # -------------------------------------------------------------
            uni_target = getattr(state, "universal_tax_target", 10) if is_tax_active else getattr(state, "universal_levy_target", 20)
            
            uni_rect = pygame.Rect(25, 326, 260, 30)
            pygame.draw.rect(screen, (32, 38, 50), uni_rect, border_radius=4)
            pygame.draw.rect(screen, (70, 95, 130), uni_rect, 1, border_radius=4)

            screen.blit(font_xs.render("ALL:", True, COLOR_GOLD), (31, 334))
            
            btn_uni_dec = pygame.Rect(58, 331, 18, 20)
            box_uni_rate = pygame.Rect(78, 331, 38, 20)
            btn_uni_inc = pygame.Rect(118, 331, 18, 20)
            btn_uni_apply = pygame.Rect(140, 331, 140, 20)

            hov_uni_dec = btn_uni_dec.collidepoint(mouse_pos)
            hov_uni_inc = btn_uni_inc.collidepoint(mouse_pos)
            hov_uni_apply = btn_uni_apply.collidepoint(mouse_pos)

            # [-] button
            pygame.draw.rect(screen, (60, 70, 90) if hov_uni_dec else (42, 48, 62), btn_uni_dec, border_radius=3)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_uni_dec, 1, border_radius=3)
            screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE if hov_uni_dec else (200, 210, 230)), (64, 333))

            # Target Box
            pygame.draw.rect(screen, (24, 30, 42), box_uni_rate, border_radius=3)
            pygame.draw.rect(screen, (80, 120, 180), box_uni_rate, 1, border_radius=3)
            u_lbl = font_xs.render(f"{uni_target}%", True, COLOR_GOLD)
            screen.blit(u_lbl, (box_uni_rate.x + (box_uni_rate.w - u_lbl.get_width()) // 2, 333))

            # [+] button
            pygame.draw.rect(screen, (60, 70, 90) if hov_uni_inc else (42, 48, 62), btn_uni_inc, border_radius=3)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_uni_inc, 1, border_radius=3)
            screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE if hov_uni_inc else (200, 210, 230)), (123, 333))

            # [ ⚡ SAMARATAKAN ] button
            pygame.draw.rect(screen, (35, 95, 52) if hov_uni_apply else (25, 72, 40), btn_uni_apply, border_radius=3)
            pygame.draw.rect(screen, COLOR_TEXT_GREEN, btn_uni_apply, 1, border_radius=3)
            apply_txt = font_xs.render("⚡ SAMARATAKAN", True, COLOR_TEXT_WHITE)
            screen.blit(apply_txt, (btn_uni_apply.x + (btn_uni_apply.w - apply_txt.get_width()) // 2, 334))

            if mouse_clicked:
                if hov_uni_dec:
                    if is_tax_active:
                        state.universal_tax_target = max(0, uni_target - 5)
                    else:
                        state.universal_levy_target = max(0, uni_target - 5)
                elif hov_uni_inc:
                    if is_tax_active:
                        state.universal_tax_target = min(90, uni_target + 5)
                    else:
                        state.universal_levy_target = min(90, uni_target + 5)
                elif hov_uni_apply:
                    app_count = 0
                    lock_count = 0
                    for r_pid, r_prov in PROVINCES.items():
                        if r_prov["owner"] == state.player_id:
                            for v_item in state.vassals.get(r_pid, []):
                                v_is_locked = v_item.get("tax_locked", False) if is_tax_active else v_item.get("levy_locked", False)
                                if v_is_locked:
                                    lock_count += 1
                                else:
                                    if is_tax_active:
                                        v_item["tax_rate"] = uni_target
                                        st_v = get_vassal_landed_status(state, v_item, r_pid)
                                        v_item["tax_contribution"] = st_v["tax_paid"]
                                    else:
                                        v_item["levy_rate"] = uni_target
                                        st_v = get_vassal_landed_status(state, v_item, r_pid)
                                        v_item["levy_contribution"] = st_v["levy_contribution"]
                                    sync_province_holdings_stats(state, r_pid)
                                    app_count += 1
                    law_name = "Tax" if is_tax_active else "Levy"
                    state.logs.append(f"Samaratakan Hukum: {law_name} diset ke {uni_target}% untuk {app_count} vassal! ({lock_count} vassal terkunci tetap aman).")

            # -------------------------------------------------------------
            # Vassals List with Individual Settings & LOCK Toggles
            # -------------------------------------------------------------
            realm_vassals = []
            for pid, prov in PROVINCES.items():
                if prov["owner"] == state.player_id:
                    for v in state.vassals.get(pid, []):
                        realm_vassals.append((pid, v))

            total_v = len(realm_vassals)
            header_text = f"Tax Laws ({total_v} Lords)" if is_tax_active else f"Levy Laws ({total_v} Lords)"
            header_lbl = font_md.render(header_text, True, COLOR_GOLD)
            screen.blit(header_lbl, (25, 362))

            per_page = 4
            max_pages = max(1, (total_v + per_page - 1) // per_page)
            state.laws_page = max(0, min(getattr(state, "laws_page", 0), max_pages - 1))

            # Header Top Pagination Controls (< 1/5 >)
            top_btn_prev = pygame.Rect(216, 362, 18, 18)
            top_btn_next = pygame.Rect(268, 362, 18, 18)
            is_top_prev_hov = top_btn_prev.collidepoint(mouse_pos)
            is_top_next_hov = top_btn_next.collidepoint(mouse_pos)

            p_top_prev_col = COLOR_TEXT_WHITE if (state.laws_page > 0 and not is_top_prev_hov) else (COLOR_GOLD if is_top_prev_hov else (70, 75, 85))
            p_top_next_col = COLOR_TEXT_WHITE if (state.laws_page < max_pages - 1 and not is_top_next_hov) else (COLOR_GOLD if is_top_next_hov else (70, 75, 85))
            screen.blit(font_xs.render("<", True, p_top_prev_col), (221, 364))
            p_top_str = f"{state.laws_page + 1}/{max_pages}"
            p_top_lbl = font_xs.render(p_top_str, True, COLOR_TEXT_MUTED)
            screen.blit(p_top_lbl, (244 - p_top_lbl.get_width() // 2, 364))
            screen.blit(font_xs.render(">", True, p_top_next_col), (273, 364))

            if mouse_clicked and is_top_prev_hov and state.laws_page > 0:
                state.laws_page -= 1
            elif mouse_clicked and is_top_next_hov and state.laws_page < max_pages - 1:
                state.laws_page += 1

            start_i = state.laws_page * per_page
            cur_page_vassals = realm_vassals[start_i:start_i + per_page]

            vy = 384
            for v_pid, v_data in cur_page_vassals:
                v_card = pygame.Rect(25, vy, 260, 52)
                is_vc_hov = v_card.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (48, 56, 72) if is_vc_hov else (32, 38, 50), v_card, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if is_vc_hov else COLOR_PANEL_BORDER, v_card, 1, border_radius=4)

                prov_short = PROVINCES[v_pid]["name"].split()[0]
                screen.blit(font_xs.render(f"♟ {v_data['name']}", True, COLOR_GOLD), (32, vy + 3))
                p_tag = font_xs.render(f"[{prov_short}]", True, (140, 200, 255))
                screen.blit(p_tag, (280 - p_tag.get_width(), vy + 3))

                st = get_vassal_landed_status(state, v_data, v_pid)
                h_name = v_data.get("city_name") if st["is_landed"] else "Landless Noble"
                screen.blit(font_xs.render(f"Fief: {h_name}", True, (200, 215, 230)), (32, vy + 16))

                # Row 3: [-] [Rate%] [+] [Info] [Lock Button]
                btn_dec = pygame.Rect(30, vy + 31, 18, 17)
                rate_box = pygame.Rect(50, vy + 31, 36, 17)
                btn_inc = pygame.Rect(88, vy + 31, 18, 17)
                btn_lock = pygame.Rect(196, vy + 31, 84, 17)

                hov_dec = btn_dec.collidepoint(mouse_pos)
                hov_rate = rate_box.collidepoint(mouse_pos)
                hov_inc = btn_inc.collidepoint(mouse_pos)
                hov_lock = btn_lock.collidepoint(mouse_pos)

                # Dec
                pygame.draw.rect(screen, (70, 80, 100) if hov_dec else (42, 48, 62), btn_dec, border_radius=3)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_dec, 1, border_radius=3)
                screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE), (36, vy + 31))

                # Inc
                pygame.draw.rect(screen, (70, 80, 100) if hov_inc else (42, 48, 62), btn_inc, border_radius=3)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_inc, 1, border_radius=3)
                screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE), (93, vy + 31))

                if is_tax_active:
                    cur_rate = v_data.get("tax_rate", 10)
                    is_locked = v_data.get("tax_locked", False)
                    
                    # Rate Box
                    pygame.draw.rect(screen, (28, 34, 46), rate_box, border_radius=3)
                    pygame.draw.rect(screen, (90, 140, 210) if hov_rate else COLOR_PANEL_BORDER, rate_box, 1, border_radius=3)
                    r_lbl = font_xs.render(f"{cur_rate}%", True, COLOR_GOLD)
                    screen.blit(r_lbl, (rate_box.x + (rate_box.w - r_lbl.get_width()) // 2, vy + 31))

                    # Tax Info
                    info_txt = f"+{st['tax_paid']}g/m" if st["is_landed"] else "0g"
                    screen.blit(font_xs.render(info_txt, True, COLOR_TEXT_GREEN if st['tax_paid'] > 0 else COLOR_TEXT_MUTED), (110, vy + 32))

                    # Lock Button
                    lock_bg = (65, 50, 20) if is_locked else ((45, 52, 68) if hov_lock else (28, 34, 46))
                    lock_bd = COLOR_GOLD if is_locked else ((120, 160, 210) if hov_lock else (70, 80, 95))
                    pygame.draw.rect(screen, lock_bg, btn_lock, border_radius=3)
                    pygame.draw.rect(screen, lock_bd, btn_lock, 1, border_radius=3)
                    l_txt = "◈ LOCKED" if is_locked else "◇ UNLOCK"
                    l_col = COLOR_GOLD if is_locked else COLOR_TEXT_MUTED
                    l_lbl = font_xs.render(l_txt, True, l_col)
                    screen.blit(l_lbl, (btn_lock.x + (btn_lock.w - l_lbl.get_width()) // 2, vy + 31))

                    if mouse_clicked:
                        if hov_lock:
                            v_data["tax_locked"] = not is_locked
                            st_str = "LOCKED (exempt from realm changes)" if v_data["tax_locked"] else "UNLOCKED"
                            state.logs.append(f"Feudal Law: {v_data['name']}'s tax rate is now {st_str}.")
                        elif hov_dec:
                            new_rate = max(0, cur_rate - 5)
                            v_data["tax_rate"] = new_rate
                            st_new = get_vassal_landed_status(state, v_data, v_pid)
                            v_data["tax_contribution"] = st_new["tax_paid"]
                            sync_province_holdings_stats(state, v_pid)
                            state.logs.append(f"Decreased {v_data['name']}'s tax obligation to {new_rate}%.")
                        elif hov_inc:
                            new_rate = min(90, cur_rate + 5)
                            v_data["tax_rate"] = new_rate
                            st_new = get_vassal_landed_status(state, v_data, v_pid)
                            v_data["tax_contribution"] = st_new["tax_paid"]
                            sync_province_holdings_stats(state, v_pid)
                            state.logs.append(f"Increased {v_data['name']}'s tax obligation to {new_rate}%.")
                        elif hov_rate:
                            cycle = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
                            next_i = (cycle.index(cur_rate) + 1) % len(cycle) if cur_rate in cycle else 1
                            new_rate = cycle[next_i]
                            v_data["tax_rate"] = new_rate
                            st_new = get_vassal_landed_status(state, v_data, v_pid)
                            v_data["tax_contribution"] = st_new["tax_paid"]
                            sync_province_holdings_stats(state, v_pid)
                            state.logs.append(f"Adjusted {v_data['name']}'s tax rate to {new_rate}%.")
                        elif is_vc_hov:
                            state.selected_province = v_pid
                            state.inspecting_vassal = {"province": v_pid, "vassal": v_data}
                            if v_data.get("tiles"):
                                state.selected_settlement = v_data["tiles"][0]
                            state.logs.append(f"Inspecting feudal dossier for {v_data['name']}.")

                else:  # Levy Laws
                    cur_rate = v_data.get("levy_rate", 20)
                    is_locked = v_data.get("levy_locked", False)
                    
                    # Rate Box
                    pygame.draw.rect(screen, (28, 34, 46), rate_box, border_radius=3)
                    pygame.draw.rect(screen, (90, 140, 210) if hov_rate else COLOR_PANEL_BORDER, rate_box, 1, border_radius=3)
                    r_lbl = font_xs.render(f"{cur_rate}%", True, COLOR_GOLD)
                    screen.blit(r_lbl, (rate_box.x + (rate_box.w - r_lbl.get_width()) // 2, vy + 31))

                    # Levy Info
                    info_txt = f"+{st['levy_contribution']}m" if st["is_landed"] else "0m"
                    screen.blit(font_xs.render(info_txt, True, COLOR_TEXT_GREEN if st['levy_contribution'] > 0 else COLOR_TEXT_MUTED), (110, vy + 32))

                    # Lock Button
                    lock_bg = (65, 50, 20) if is_locked else ((45, 52, 68) if hov_lock else (28, 34, 46))
                    lock_bd = COLOR_GOLD if is_locked else ((120, 160, 210) if hov_lock else (70, 80, 95))
                    pygame.draw.rect(screen, lock_bg, btn_lock, border_radius=3)
                    pygame.draw.rect(screen, lock_bd, btn_lock, 1, border_radius=3)
                    l_txt = "◈ LOCKED" if is_locked else "◇ UNLOCK"
                    l_col = COLOR_GOLD if is_locked else COLOR_TEXT_MUTED
                    l_lbl = font_xs.render(l_txt, True, l_col)
                    screen.blit(l_lbl, (btn_lock.x + (btn_lock.w - l_lbl.get_width()) // 2, vy + 31))

                    if mouse_clicked:
                        if hov_lock:
                            v_data["levy_locked"] = not is_locked
                            st_str = "LOCKED (exempt from realm changes)" if v_data["levy_locked"] else "UNLOCKED"
                            state.logs.append(f"Feudal Law: {v_data['name']}'s levy rate is now {st_str}.")
                        elif hov_dec:
                            new_rate = max(0, cur_rate - 5)
                            v_data["levy_rate"] = new_rate
                            st_new = get_vassal_landed_status(state, v_data, v_pid)
                            v_data["levy_contribution"] = st_new["levy_contribution"]
                            sync_province_holdings_stats(state, v_pid)
                            state.logs.append(f"Decreased {v_data['name']}'s levy obligation to {new_rate}%.")
                        elif hov_inc:
                            new_rate = min(90, cur_rate + 5)
                            v_data["levy_rate"] = new_rate
                            st_new = get_vassal_landed_status(state, v_data, v_pid)
                            v_data["levy_contribution"] = st_new["levy_contribution"]
                            sync_province_holdings_stats(state, v_pid)
                            state.logs.append(f"Increased {v_data['name']}'s levy obligation to {new_rate}%.")
                        elif hov_rate:
                            cycle = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
                            next_i = (cycle.index(cur_rate) + 1) % len(cycle) if cur_rate in cycle else 2
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

                vy += 56

            # Bottom Pagination Controls (py_btn = 618)
            py_btn = 618
            btn_prev = pygame.Rect(25, py_btn, 80, 26)
            btn_next = pygame.Rect(205, py_btn, 80, 26)

            is_prev_hov = btn_prev.collidepoint(mouse_pos)
            is_next_hov = btn_next.collidepoint(mouse_pos)

            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_prev_hov else COLOR_BUTTON_NORMAL, btn_prev, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_prev, 1, border_radius=4)
            screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.laws_page > 0 else COLOR_TEXT_MUTED), (42, py_btn + 5))

            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if is_next_hov else COLOR_BUTTON_NORMAL, btn_next, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_next, 1, border_radius=4)
            screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.laws_page < max_pages - 1 else COLOR_TEXT_MUTED), (222, py_btn + 5))

            page_str = f"Page {state.laws_page + 1}/{max_pages}"
            p_lbl = font_xs.render(page_str, True, COLOR_TEXT_MUTED)
            screen.blit(p_lbl, (115 + (80 - p_lbl.get_width()) // 2, py_btn + 5))

            if mouse_clicked and is_prev_hov and state.laws_page > 0:
                state.laws_page -= 1
            elif mouse_clicked and is_next_hov and state.laws_page < max_pages - 1:
                state.laws_page += 1

        elif state.left_tab == "economy":
            # Royal Financial Ledger & Budget View (Income & Expenses Breakdown)
            fin = get_realm_finances(state, state.player_id)

            # 1. Summary Treasury Card (y = 298 to 364)
            sum_card = pygame.Rect(25, 298, 260, 66)
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

            tab_inc = pygame.Rect(25, 370, 128, 24)
            tab_exp = pygame.Rect(157, 370, 128, 24)

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
                card_p = pygame.Rect(25, 400, 260, 92)
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
                card_v = pygame.Rect(25, 498, 260, 118)
                pygame.draw.rect(screen, (32, 38, 50), card_v, border_radius=5)
                pygame.draw.rect(screen, (80, 110, 150), card_v, 1, border_radius=5)

                screen.blit(font_xs.render("♚ Feudal Vassal Tithes", True, COLOR_GOLD), (32, 502))
                v_tot_lbl = font_xs.render(f"+{fin['total_vassal_tax']}g/m", True, COLOR_TEXT_GREEN)
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
                        screen.blit(font_xs.render(f"{v_item['tax_rate']}% -> +{v_item['tax_paid']}g/m", True, COLOR_TEXT_GREEN), (170, vy_item))
                        vy_item += 18
                else:
                    screen.blit(font_xs.render("• No landed vassals paying tithes yet", True, COLOR_TEXT_MUTED), (34, 545))

                screen.blit(font_xs.render("Adjust individual rates under [ ⚖ LAWS ] tab", True, COLOR_GOLD), (34, 596))

                # 3. Direct Crown Demesne Revenue Card (y = 622, h = 54)
                card_c = pygame.Rect(25, 622, 260, 54)
                pygame.draw.rect(screen, (32, 38, 50), card_c, border_radius=5)
                pygame.draw.rect(screen, (80, 110, 150), card_c, 1, border_radius=5)

                screen.blit(font_xs.render("[Fort] Crown Demesne Rents", True, COLOR_GOLD), (32, 626))
                c_tot_lbl = font_xs.render(f"+{fin['total_crown_income']}g/m", True, COLOR_TEXT_GREEN)
                screen.blit(c_tot_lbl, (275 - c_tot_lbl.get_width(), 626))

                screen.blit(font_xs.render("Direct rents from King Alfred's royal seats:", True, COLOR_TEXT_MUTED), (32, 642))
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
                card_a = pygame.Rect(25, 400, 260, 112)
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

                # 2. Military Facilities & Barracks Upkeep Card (y = 518, h = 82)
                card_b = pygame.Rect(25, 518, 260, 82)
                pygame.draw.rect(screen, (42, 34, 38), card_b, border_radius=5)
                pygame.draw.rect(screen, (150, 80, 80), card_b, 1, border_radius=5)

                screen.blit(font_xs.render("⚔ Forts & Barracks Maintenance", True, COLOR_GOLD), (32, 522))
                b_tot_lbl = font_xs.render(f"-{fin['total_facility_upkeep']}g/m", True, COLOR_TEXT_RED)
                screen.blit(b_tot_lbl, (275 - b_tot_lbl.get_width(), 522))

                screen.blit(font_xs.render("Drillmasters & garrison maintenance (1+Lv gold):", True, COLOR_TEXT_MUTED), (32, 538))

                if fin['barrack_expenses']:
                    by_item = 558
                    for b_exp in fin['barrack_expenses'][:2]:
                        screen.blit(font_xs.render(f"• {b_exp['name']} ({b_exp['prov']}):", True, (230, 215, 215)), (34, by_item))
                        screen.blit(font_xs.render(f"-{b_exp['cost']}g/m", True, COLOR_TEXT_RED), (225, by_item))
                        by_item += 18
                else:
                    screen.blit(font_xs.render("• Standard wooden palisades (0g additional upkeep)", True, COLOR_TEXT_MUTED), (34, 558))

                # 3. Monthly Financial Statement Card (y = 606, h = 70)
                card_s = pygame.Rect(25, 606, 260, 70)
                pygame.draw.rect(screen, (32, 40, 52), card_s, border_radius=5)
                pygame.draw.rect(screen, COLOR_GOLD, card_s, 1, border_radius=5)

                screen.blit(font_xs.render("⚖ Monthly Financial Bottom Line", True, COLOR_GOLD), (32, 610))
                screen.blit(font_xs.render(f"Gross Inflow: +{fin['total_income']}g / month", True, (160, 225, 180)), (34, 626))
                screen.blit(font_xs.render(f"Gross Outflow: -{fin['total_expense']}g / month", True, (255, 140, 140)), (34, 642))

                net_st_lbl = font_xs.render(f"Net Cash Flow: {net_sign}{fin['net_monthly']}g / month", True, net_col)
                screen.blit(net_st_lbl, (34, 658))

        # ---------------------------------------------------------
        # 3. CENTER: TERRITORY BALANCE & MAP
        # ---------------------------------------------------------
        map_bg_rect = pygame.Rect(292, 54, 566, WINDOW_HEIGHT - 60)
        pygame.draw.rect(screen, COLOR_OCEAN, map_bg_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, map_bg_rect, 2, border_radius=6)

        # Territory Control Bar (Wessex vs Danelaw)
        wessex_count = state.get_provinces_count(state.player_id)
        danelaw_count = state.get_provinces_count(state.enemy_id)
        total_provs = 12

        bar_x = 310
        bar_y = 66
        bar_w = 490
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
        hud_rect = pygame.Rect(816, 62, 34, 118)

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

        # Province Name Labels (Medieval Plaque / Banner)
        for pid, (lx, ly) in province_anchors.items():
            p_data = PROVINCES.get(pid)
            if p_data:
                short_name = p_data["name"].split()[0]
                is_sel = (pid == state.selected_province)
                is_hov = (pid == state.hovered_province)
                
                txt_col = (255, 220, 60) if is_sel else ((225, 235, 255) if is_hov else (240, 244, 250))
                txt_surf = font_xs.render(short_name, True, txt_col)
                bw = txt_surf.get_width() + 14
                bh = 18
                bx = lx - bw // 2
                by = ly - bh // 2
                
                plaque_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
                plaque_surf.fill((16, 20, 30, 215))
                screen.blit(plaque_surf, (bx, by))
                
                border_c = (255, 215, 60) if is_sel else ((160, 180, 210) if is_hov else (55, 70, 95))
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

        def border_midpoint(pid_a, pid_b):
            return get_border_midpoint(pid_a, pid_b)

        for army in state.armies:
            if not army.is_moving or army.in_battle:
                continue
            is_player_army = (army.owner == state.player_id)
            arrow_col = (240, 180, 50) if is_player_army else (80, 130, 220)

            # Build waypoints: centroid -> border midpoint -> centroid -> ...
            path_steps = [army.province] + army.path
            waypoints = [province_anchors.get(path_steps[0])]
            for i in range(len(path_steps) - 1):
                bp = border_midpoint(path_steps[i], path_steps[i + 1])
                if bp:
                    waypoints.append(bp)
                dst = province_anchors.get(path_steps[i + 1])
                if dst:
                    waypoints.append(dst)

            # Draw path segments with arrowhead on each leg
            for i in range(len(waypoints) - 1):
                src = waypoints[i]
                dst = waypoints[i + 1]
                if src and dst:
                    fade = max(80, 220 - i * 30)
                    col = (arrow_col[0], arrow_col[1], arrow_col[2])
                    # Dashed line for far steps
                    if i % 2 == 0:
                        draw_arrow(screen, col, src, dst, width=2, head_size=8)
                    else:
                        pygame.draw.line(screen, col, src, dst, 2)

        # ---------------------------------------------------------
        # DRAW ARMIES ON MAP (Waving War Banners & Troop Standard)
        # ---------------------------------------------------------
        anim_ticks = pygame.time.get_ticks()

        for army in state.armies:
            base_pos = province_anchors.get(army.province)
            if not base_pos:
                continue

            cx, cy = base_pos[0], base_pos[1]

            # If moving, interpolate position smoothly along route
            if army.is_moving and army.next_province and not army.in_battle:
                next_pos = province_anchors.get(army.next_province, base_pos)
                pct = army.move_progress / 100.0
                cx = int(cx + (next_pos[0] - base_pos[0]) * pct)
                cy = int(cy + (next_pos[1] - base_pos[1]) * pct)

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
                t_str = army.siege_target_name.split()[0] if army.siege_target_name else "City"
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
        hud_x, hud_y = 816, 62
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

        # ---------------------------------------------------------
        # 4. RIGHT PANEL: SELECTED PROVINCE & ARMY COMMANDS
        # ---------------------------------------------------------
        right_panel = pygame.Rect(860, 62, 330, WINDOW_HEIGHT - 72)
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
            screen.blit(c_head, (880, 80))
            
            p_cap = s_data['province'].replace("_", " ").title()
            if h_type == "city":
                sub_c = font_sm.render(f"Holding Type: [City] Commercial City ({p_cap})", True, COLOR_TEXT_WHITE)
            elif h_type == "fort":
                sub_c = font_sm.render(f"Holding Type: [Fort] Stone Fortress ({p_cap})", True, COLOR_TEXT_WHITE)
            else:
                lvl = s_data.get("level", 0)
                sub_c = font_sm.render(f"Holding Type: ⚔ Military Barracks Lvl {lvl} ({p_cap})", True, COLOR_TEXT_WHITE)
            screen.blit(sub_c, (880, 110))
            
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 135), (1170, 135), 1)
            screen.blit(font_md.render("Holding Overview", True, COLOR_GOLD), (880, 145))
            h_matching_tiles = [coord for coord, s in state.settlements.items() if s.get("name") == s_data["name"] and s.get("province") == s_data["province"]]
            t_loc_str = ", ".join(f"({c},{r})" for c, r in h_matching_tiles)
            screen.blit(font_sm.render(f"Location: {t_loc_str} ({len(h_matching_tiles)} Tiles)", True, COLOR_TEXT_MUTED), (880, 172))
            lord_str = s_data.get('lord', 'Crown Demesne').replace("Royal Demesne", "Crown Demesne")
            screen.blit(font_sm.render(f"Ruling Lord: {lord_str}", True, COLOR_GOLD), (880, 194))

            cur_y = 216
            if h_type == "city":
                screen.blit(font_sm.render("Economic Income: +3 Gold / month", True, COLOR_TEXT_GREEN), (880, cur_y))
                screen.blit(font_sm.render("Recruitment Rate: +10 Men / month", True, COLOR_TEXT_GREEN), (880, cur_y + 22))
                screen.blit(font_sm.render("Local Garrison: 100 Defenders", True, COLOR_TEXT_WHITE), (880, cur_y + 44))
                screen.blit(font_xs.render("• Generates gold and recruits to supply and replenish realm fyrd.", True, COLOR_TEXT_MUTED), (880, cur_y + 66))
                cur_y += 90

            elif h_type == "fort":
                screen.blit(font_sm.render("Economic Income: +1 Gold / month (Tolls)", True, COLOR_TEXT_GREEN), (880, cur_y))
                screen.blit(font_sm.render("Recruitment Rate: +10 Men / month", True, COLOR_TEXT_GREEN), (880, cur_y + 22))
                screen.blit(font_sm.render("Local Garrison: 300 Defenders", True, COLOR_TEXT_WHITE), (880, cur_y + 44))
                screen.blit(font_sm.render("Fortification: High Defense (Twin Turrets)", True, (160, 210, 255)), (880, cur_y + 66))
                screen.blit(font_xs.render("• Shields the province and trains +10 garrison defenders monthly.", True, COLOR_TEXT_MUTED), (880, cur_y + 88))
                cur_y += 112

            else: # Barracks
                lvl = s_data.get("level", 0)
                bstats = get_barrack_stats(lvl)
                screen.blit(font_sm.render(f"Recruitment Rate: +{bstats['recruits']} Men / month", True, COLOR_TEXT_GREEN), (880, cur_y))
                screen.blit(font_sm.render(f"Holding Upkeep: -{bstats['upkeep']} Gold / month", True, (255, 120, 120)), (880, cur_y + 22))
                screen.blit(font_sm.render(f"Garrison Capacity: {bstats['garrison']} / 500 Men", True, COLOR_TEXT_WHITE), (880, cur_y + 44))
                cur_y += 70

                # Upgrade & Downgrade buttons for Barracks
                is_crown_barrack = s_data.get("is_crown_demesne", False)
                if is_crown_barrack and p_parent and p_parent["owner"] == state.player_id:
                    # Upgrade button
                    if lvl < 5:
                        up_cost = BARRACK_UPGRADE_COSTS.get(lvl, 500)
                        can_afford = state.player["gold"] >= up_cost
                        up_btn = pygame.Rect(880, cur_y, 290, 32)
                        up_hov = up_btn.collidepoint(mouse_pos)
                        pygame.draw.rect(screen, (35, 95, 50) if (up_hov and can_afford) else ((25, 65, 35) if can_afford else (45, 45, 50)), up_btn, border_radius=4)
                        pygame.draw.rect(screen, COLOR_TEXT_GREEN if can_afford else (90, 90, 95), up_btn, 1, border_radius=4)
                        up_txt = font_xs.render(f"▲ UPGRADE TO LEVEL {lvl+1} ({up_cost}g  •  +5 Recruits/m)", True, COLOR_TEXT_WHITE if can_afford else COLOR_TEXT_MUTED)
                        screen.blit(up_txt, (892, cur_y + 8))
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
                        down_btn = pygame.Rect(880, cur_y, 290, 30)
                        down_hov = down_btn.collidepoint(mouse_pos)
                        pygame.draw.rect(screen, (90, 45, 30) if down_hov else (65, 32, 22), down_btn, border_radius=4)
                        pygame.draw.rect(screen, (220, 110, 60), down_btn, 1, border_radius=4)
                        down_txt = font_xs.render(f"▼ DEMOBILIZE / DOWNGRADE (Save 1g/m Upkeep)", True, (255, 210, 190))
                        screen.blit(down_txt, (890, cur_y + 7))
                        if mouse_clicked and down_hov:
                            new_lvl = lvl - 1
                            for tc in h_matching_tiles:
                                state.settlements[tc]["level"] = new_lvl
                            sync_province_holdings_stats(state, s_data["province"])
                            state.logs.append(f"Downgraded {s_data['name']} to Level {new_lvl}. Saved 1 Gold/month upkeep.")
                        cur_y += 36
            
            if s_data.get("vassal_id"):
                v_btn = pygame.Rect(880, cur_y + 8, 290, 34)
                b_v_hov = v_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 75, 110) if b_v_hov else (30, 55, 85), v_btn, border_radius=6)
                pygame.draw.rect(screen, (100, 180, 255), v_btn, 1, border_radius=6)
                screen.blit(font_xs.render("♚ VIEW VASSAL PROFILE & DOSSIER", True, COLOR_TEXT_WHITE), (915, cur_y + 16))
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
            cls_btn = pygame.Rect(880, cls_y, 290, 34)
            b_c_hov = cls_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if b_c_hov else COLOR_BUTTON_NORMAL, cls_btn, border_radius=6)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, cls_btn, 1, border_radius=6)
            screen.blit(font_sm.render("← Back to Province View", True, COLOR_TEXT_WHITE), (940, cls_y + 8))
            if mouse_clicked and b_c_hov:
                state.selected_settlement = None
                state.selected_vassal_idx = None

        # If an army is selected, show Army Command Card!
        elif sel_army and sel_army.owner == state.player_id:
            # Header
            a_title = font_lg.render(sel_army.name, True, COLOR_GOLD)
            screen.blit(a_title, (880, 80))
            
            sub_title = font_sm.render(f"Strength: {sel_army.troops:,} Men  •  Owner: Wessex", True, COLOR_TEXT_WHITE)
            screen.blit(sub_title, (880, 110))

            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 135), (1170, 135), 1)

            # Location & Status
            screen.blit(font_md.render("Host Status", True, COLOR_GOLD), (880, 145))
            screen.blit(font_sm.render(f"Current Location: {PROVINCES[sel_army.province]['name']}", True, COLOR_TEXT_WHITE), (880, 175))
            
            if sel_army.in_battle:
                screen.blit(font_md.render("STATUS: ⚔ IN PITCHED BATTLE!", True, COLOR_TEXT_RED), (880, 202))
            elif sel_army.courier_en_route:
                screen.blit(font_md.render(f"STATUS: ROYAL COURIER EN ROUTE ({sel_army.courier_days_left}d left)", True, (255, 215, 80)), (880, 202))
                dest_p = PROVINCES[sel_army.province]["name"].split()[0]
                cap_p = "Winchester" if sel_army.owner == state.player_id else "Jorvik"
                screen.blit(font_xs.render(f"Decree riding from {cap_p} to {dest_p}.", True, COLOR_TEXT_WHITE), (880, 222))
            elif sel_army.is_mustering:
                screen.blit(font_md.render(f"STATUS: MUSTERING ({sel_army.muster_days}d left)", True, COLOR_GOLD), (880, 202))
            elif sel_army.is_demobilizing:
                home_p = PROVINCES[sel_army.flag_origin]["name"].split()[0]
                screen.blit(font_md.render(f"STATUS: ◆ Returning Home to {home_p}", True, (140, 200, 255)), (880, 202))
            elif sel_army.is_sieging:
                t_lbl = sel_army.siege_target_name or 'Holding'
                screen.blit(font_md.render(f"STATUS: [Fort] Besieging {t_lbl} ({sel_army.siege_progress}%)", True, COLOR_GOLD), (880, 202))
            elif sel_army.is_moving:
                screen.blit(font_sm.render(f"Marching to: {PROVINCES[sel_army.next_province]['name']} ({int(sel_army.move_progress)}%)", True, COLOR_TEXT_WHITE), (880, 202))
            else:
                screen.blit(font_sm.render("Status: Standing Ready", True, COLOR_TEXT_GREEN), (880, 202))

            # March Instruction Box
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 235), (1170, 235), 1)
            screen.blit(font_md.render("March Orders", True, COLOR_GOLD), (880, 245))
            screen.blit(font_sm.render("Click any province on the map to", True, COLOR_TEXT_MUTED), (880, 275))
            screen.blit(font_sm.render("order this army to march there!", True, COLOR_TEXT_MUTED), (880, 295))
            screen.blit(font_xs.render("• March into enemy land to begin SIEGE.", True, COLOR_GOLD), (880, 320))
            screen.blit(font_xs.render("• March into Viking army to CLASH.", True, COLOR_TEXT_RED), (880, 340))

            # Action Buttons for Army
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 365), (1170, 365), 1)
            
            # Merge button if other armies in same province
            other_armies = [a for a in state.armies if a.province == sel_army.province and a.owner == state.player_id and a.id != sel_army.id]
            if other_armies:
                merge_btn = pygame.Rect(880, 385, 290, 40)
                b_m_hover = merge_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 90, 140) if b_m_hover else (30, 65, 105), merge_btn, border_radius=6)
                pygame.draw.rect(screen, (80, 160, 240), merge_btn, 1, border_radius=6)
                screen.blit(font_md.render("MERGE WITH OTHER HOSTS", True, COLOR_TEXT_WHITE), (910, 394))
                if mouse_clicked and b_m_hover:
                    state.merge_armies_in_province(sel_army.province, state.player_id)

            # Disband / Cancel Muster / Cancel Summons Button
            if sel_army.is_mustering or sel_army.courier_en_route:
                dis_btn = pygame.Rect(880, 435, 290, 40)
                b_d_hover = dis_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (90, 40, 40) if b_d_hover else (70, 30, 30), dis_btn, border_radius=6)
                pygame.draw.rect(screen, (240, 90, 90), dis_btn, 1, border_radius=6)
                btn_txt = "CANCEL SUMMONS (Recall Courier)" if sel_army.courier_en_route else "CANCEL MUSTER (Refund Men)"
                b_lbl = font_md.render(btn_txt, True, (255, 220, 220))
                screen.blit(b_lbl, (880 + (290 - b_lbl.get_width()) // 2, 444))
                if mouse_clicked and b_d_hover:
                    state.disband_army(sel_army)
            elif sel_army.is_demobilizing:
                dis_btn = pygame.Rect(880, 435, 290, 40)
                b_d_hover = dis_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 90, 140) if b_d_hover else (30, 65, 105), dis_btn, border_radius=6)
                pygame.draw.rect(screen, (80, 160, 240), dis_btn, 1, border_radius=6)
                screen.blit(font_md.render("CANCEL DISBAND (Resume War)", True, COLOR_TEXT_WHITE), (905, 444))
                if mouse_clicked and b_d_hover:
                    sel_army.is_demobilizing = False
                    sel_army.path = []
                    state.logs.append(f"{sel_army.name} cancelled return march and is standing ready.")
            else:
                dis_btn = pygame.Rect(880, 435, 290, 40)
                b_d_hover = dis_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (80, 35, 35) if b_d_hover else (60, 28, 28), dis_btn, border_radius=6)
                pygame.draw.rect(screen, COLOR_TEXT_RED, dis_btn, 1, border_radius=6)
                screen.blit(font_md.render("ORDER DISBAND (Return Home)", True, (255, 220, 220)), (905, 444))
                if mouse_clicked and b_d_hover:
                    state.disband_army(sel_army)

            # Deselect Army Button
            desel_btn = pygame.Rect(880, 485, 290, 36)
            b_ds_hover = desel_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if b_ds_hover else COLOR_BUTTON_NORMAL, desel_btn, border_radius=6)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, desel_btn, 1, border_radius=6)
            screen.blit(font_sm.render("Deselect Army (View Province)", True, COLOR_TEXT_MUTED), (925, 493))
            if mouse_clicked and b_ds_hover:
                state.selected_army_id = None

        elif sel_prov:
            owner_char = CHARACTERS.get(sel_prov["owner"], CHARACTERS["char_alfred"])
            is_player_owned = (sel_prov["owner"] == state.player_id)

            # Province Header
            p_title = font_lg.render(sel_prov["name"], True, COLOR_GOLD)
            screen.blit(p_title, (880, 75))
            sub_title = font_xs.render(f"Culture: {sel_prov['culture']}  •  Faith: {sel_prov['religion']}", True, COLOR_TEXT_MUTED)
            screen.blit(sub_title, (880, 102))

            # CLEAN TAB NAVIGATION BAR (Province Overview | Buildings | Vassals | Fiefs)
            tabs = [("overview", "Overview"), ("buildings", "Buildings"), ("vassals", "Vassals"), ("fiefs", "Fiefs")]
            tab_w = 70
            for t_i, (t_key, t_label) in enumerate(tabs):
                t_rect = pygame.Rect(880 + t_i * 72, 122, tab_w, 28)
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

            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 150), (1170, 150), 2)

            # -------------------------------------------------------------
            # TAB 1: OVERVIEW
            # -------------------------------------------------------------
            if state.right_tab == "overview":
                # Owner Info (Clickable Sovereign Ruler Card)
                r_card = pygame.Rect(876, 156, 298, 58)
                is_rc_hov = r_card.collidepoint(mouse_pos)
                if is_rc_hov:
                    pygame.draw.rect(screen, (48, 55, 75) if is_player_owned else (65, 36, 40), r_card, border_radius=6)
                    pygame.draw.rect(screen, COLOR_GOLD if is_player_owned else (240, 100, 100), r_card, 1, border_radius=6)

                owner_p = portrait_cache.get(sel_prov["owner"])
                if owner_p:
                    mini_p = pygame.transform.smoothscale(owner_p, (46, 46))
                    screen.blit(mini_p, (882, 162))
                    pygame.draw.rect(screen, COLOR_GOLD if is_player_owned else (220, 80, 80), (882, 162, 46, 46), 1)
                owner_c = coa_cache.get(sel_prov["owner"])
                if owner_c:
                    screen.blit(owner_c, (934, 162))

                screen.blit(font_md.render(owner_char["name"], True, COLOR_GOLD if is_player_owned else COLOR_TEXT_RED), (975, 162))
                screen.blit(font_xs.render(owner_char["title"], True, COLOR_TEXT_WHITE), (975, 182))
                
                # Click to inspect hint
                hint_str = "♚ Click to Inspect Sovereign Dossier"
                hint_col = (255, 220, 130) if is_player_owned else (255, 180, 180)
                screen.blit(font_xs.render(hint_str, True, hint_col), (975, 198))

                if mouse_clicked and is_rc_hov:
                    state.inspecting_ruler = sel_prov["owner"]
                    state.logs.append(f"Opened royal dossier for Sovereign {owner_char['name']}.")

                # Province Stats Box
                s_box = pygame.Rect(880, 220, 290, 80)
                pygame.draw.rect(screen, (35, 40, 54), s_box, border_radius=6)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, s_box, 1, border_radius=6)
                screen.blit(icon_gold, (890, 230))
                screen.blit(font_sm.render(f"Monthly Tax Revenue: +{sel_prov['tax']} Gold", True, COLOR_TEXT_WHITE), (925, 233))
                screen.blit(icon_troops, (890, 265))
                screen.blit(font_sm.render(f"Levies Available: {sel_prov['levies_current']} / {sel_prov['levies_max']}", True, COLOR_TEXT_WHITE), (925, 268))

                if is_player_owned:
                    # Military Orders
                    screen.blit(font_md.render("Military Orders", True, COLOR_GOLD), (880, 320))
                    raise_btn = pygame.Rect(880, 345, 290, 40)
                    b_r_hov = raise_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (35, 95, 50) if b_r_hov else (25, 70, 38), raise_btn, border_radius=6)
                    pygame.draw.rect(screen, COLOR_TEXT_GREEN, raise_btn, 1, border_radius=6)
                    screen.blit(font_md.render(f"RAISE LOCAL LEVY ({sel_prov['levies_current']} Men)", True, COLOR_TEXT_WHITE), (905, 354))
                    if mouse_clicked and b_r_hov:
                        state.raise_province_levy(state.selected_province)

                    rally_btn = pygame.Rect(880, 395, 290, 40)
                    b_rl_hov = rally_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (35, 65, 110) if b_rl_hov else (25, 48, 85), rally_btn, border_radius=6)
                    pygame.draw.rect(screen, (70, 130, 220), rally_btn, 1, border_radius=6)
                    screen.blit(font_md.render("RALLY ALL ARMIES HERE (M)", True, COLOR_TEXT_WHITE), (895, 404))
                    if mouse_clicked and b_rl_hov:
                        state.rally_all_armies_to(state.selected_province)
                else:
                    screen.blit(font_md.render("Enemy Held Territory", True, COLOR_TEXT_RED), (880, 320))
                    screen.blit(font_xs.render("• Right click your armies to march and conquer.", True, COLOR_TEXT_MUTED), (880, 350))

            # -------------------------------------------------------------
            # TAB 2: BUILDINGS
            # -------------------------------------------------------------
            elif state.right_tab == "buildings":
                screen.blit(font_md.render("Constructed Province Holdings", True, COLOR_GOLD), (880, 160))
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
                    c_box = pygame.Rect(880, cy, 290, 42)
                    is_c_hov = c_box.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (45, 52, 68) if is_c_hov else (32, 38, 50), c_box, border_radius=4)
                    pygame.draw.rect(screen, COLOR_PANEL_BORDER, c_box, 1, border_radius=4)

                    htype = h_info["type"]
                    if htype == "town":
                        htype = "city"
                    h_icon = "[City]" if htype == "city" else ("[Fort]" if htype == "fort" else "⚔")
                    screen.blit(font_xs.render(f"{h_icon} {h_info['name']}", True, COLOR_GOLD), (888, cy + 5))

                    if htype == "city":
                        stat_sub = f"Lord: {h_info['lord']}  •  +3g  •  +10 Rec/m  •  100 Gar"
                    elif htype == "fort":
                        stat_sub = f"Lord: {h_info['lord']}  •  +1g  •  +10 Rec/m  •  300 Gar"
                    else:
                        bstats = get_barrack_stats(h_info['level'])
                        stat_sub = f"Lord: {h_info['lord']}  •  -{bstats['upkeep']}g Upk  •  +{bstats['recruits']} Rec/m"
                    screen.blit(font_xs.render(stat_sub, True, COLOR_TEXT_MUTED), (888, cy + 22))

                    if mouse_clicked and is_c_hov:
                        state.selected_settlement = h_info["tile"]
                    cy += 48

                if is_player_owned:
                    pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, cy + 6), (1170, cy + 6), 1)
                    screen.blit(font_md.render("Construct New Holding", True, COLOR_GOLD), (880, cy + 14))

                    menu_specs = [
                        ("city", "[City] CITY (1 Tile - 600g)", "+100 Gar  •  +10 Recruits/m  •  +3 Gold/m", 600),
                        ("fort", "[Fort] FORT (2 Tiles - 1,000g)", "+300 Gar  •  +10 Recruits/m  •  +1 Gold/m  [T: Rotate]", 1000),
                        ("barrack", "⚔ BARRACKS (1 Tile - 800g)", "+100 Gar  •  +10 Recruits/m (Upgr)  •  -1g Upkeep", 800)
                    ]

                    btn_y = cy + 36
                    for b_type_key, b_title, b_sub, b_cost in menu_specs:
                        b_rect = pygame.Rect(880, btn_y, 290, 36)
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
                        screen.blit(font_xs.render(b_title, True, title_col), (888, btn_y + 4))
                        screen.blit(font_xs.render(b_sub, True, (240, 220, 170) if is_active else COLOR_TEXT_MUTED), (888, btn_y + 19))

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
                        screen.blit(hint1, (880, btn_y + 6))
                        if cur_spec["tiles"] > 1:
                            hint2 = font_xs.render("• Press 'T' to rotate (Horiz / Vert)", True, COLOR_GOLD)
                        else:
                            hint2 = font_xs.render("• Hover 1 free tile in this province", True, COLOR_TEXT_WHITE)
                        hint3 = font_xs.render("• Click to establish holding  •  ESC to cancel", True, COLOR_TEXT_GREEN)
                        screen.blit(hint2, (880, btn_y + 22))
                        screen.blit(hint3, (880, btn_y + 38))

            # -------------------------------------------------------------
            # TAB 3: VASSALS (Detailed Realm & Province Vassals)
            # -------------------------------------------------------------
            elif state.right_tab == "vassals":
                screen.blit(font_md.render("Provincial Vassals List", True, COLOR_GOLD), (880, 160))
                v_list = state.vassals.get(state.selected_province, [])
                vy = 190
                for v_idx, v in enumerate(v_list[:5]):
                    v_box = pygame.Rect(880, vy, 290, 44)
                    is_v_hov = v_box.collidepoint(mouse_pos)
                    is_v_sel = (state.selected_vassal_idx == v_idx)
                    v_bg = (55, 65, 85) if is_v_sel else ((42, 48, 62) if is_v_hov else (32, 36, 48))
                    pygame.draw.rect(screen, v_bg, v_box, border_radius=4)
                    pygame.draw.rect(screen, (100, 255, 120) if is_v_sel else COLOR_PANEL_BORDER, v_box, 1, border_radius=4)

                    screen.blit(font_xs.render(f"♚ {v['name']}", True, COLOR_GOLD if is_v_sel else COLOR_TEXT_WHITE), (888, vy + 4))
                    st = get_vassal_landed_status(state, v, state.selected_province)
                    c_info = v.get('city_name') if st["is_landed"] else 'Landless Noble (Unlanded)'
                    screen.blit(font_xs.render(f"Fief: {c_info}", True, (200, 230, 255)), (888, vy + 17))
                    levy_txt = f"+{st['levy_contribution']}" if st["is_landed"] else "0"
                    tax_txt = f"+{st['tax_paid']}g/m" if st["is_landed"] else "0g/m"
                    screen.blit(font_xs.render(f"Gold: {v['gold']}g  •  Levies: {levy_txt}  •  Tax: {tax_txt}", True, COLOR_TEXT_MUTED), (888, vy + 29))

                    if mouse_clicked and is_v_hov:
                        state.selected_vassal_idx = v_idx
                        state.inspecting_vassal = {"province": state.selected_province, "vassal": v}
                        if v.get("tiles"):
                            state.selected_settlement = v["tiles"][0]
                        state.logs.append(f"Opened royal dossier for vassal {v['name']}.")

                    vy += 50

            # -------------------------------------------------------------
            # TAB 4: FIEFS (Fiefs Management, Redrawing, Granting, Revoking)
            # -------------------------------------------------------------
            elif state.right_tab == "fiefs":
                prov_fiefs = [f for f in state.fiefs.values() if f.get("province") == state.selected_province]
                total_fiefs = len(prov_fiefs)
                per_page = 5 if not state.editing_fief_id else 4
                total_pages = max(1, (total_fiefs + per_page - 1) // per_page)
                state.fief_page = max(0, min(getattr(state, "fief_page", 0), total_pages - 1))

                screen.blit(font_md.render(f"Provincial Fiefs & Baronies ({total_fiefs})", True, COLOR_GOLD), (880, 155))

                if total_pages > 1:
                    # Quick Top Pagination buttons: < Page X/Y >
                    h_prev_btn = pygame.Rect(1072, 152, 22, 22)
                    h_next_btn = pygame.Rect(1146, 152, 22, 22)
                    hp_hov = h_prev_btn.collidepoint(mouse_pos)
                    hn_hov = h_next_btn.collidepoint(mouse_pos)

                    pygame.draw.rect(screen, (50, 62, 85) if hp_hov else (32, 38, 52), h_prev_btn, border_radius=3)
                    pygame.draw.rect(screen, COLOR_GOLD if hp_hov else COLOR_PANEL_BORDER, h_prev_btn, 1, border_radius=3)
                    screen.blit(font_xs.render("<", True, COLOR_TEXT_WHITE if state.fief_page > 0 else COLOR_TEXT_MUTED), (1079, 155))

                    pygame.draw.rect(screen, (50, 62, 85) if hn_hov else (32, 38, 52), h_next_btn, border_radius=3)
                    pygame.draw.rect(screen, COLOR_GOLD if hn_hov else COLOR_PANEL_BORDER, h_next_btn, 1, border_radius=3)
                    screen.blit(font_xs.render(">", True, COLOR_TEXT_WHITE if state.fief_page < total_pages - 1 else COLOR_TEXT_MUTED), (1153, 155))

                    h_pg_txt = font_xs.render(f"{state.fief_page + 1}/{total_pages}", True, COLOR_GOLD)
                    screen.blit(h_pg_txt, (1096 + (48 - h_pg_txt.get_width()) // 2, 156))

                    if mouse_clicked and hp_hov and state.fief_page > 0:
                        state.fief_page -= 1
                    elif mouse_clicked and hn_hov and state.fief_page < total_pages - 1:
                        state.fief_page += 1

                # Header action: Edit banner or Carve New Fief button
                if state.editing_fief_id:
                    edit_f = state.fiefs.get(state.editing_fief_id)
                    f_name = edit_f["name"] if edit_f else "Fief"
                    num_tiles = len(edit_f.get("tiles", [])) if edit_f else 0
                    eb_rect = pygame.Rect(880, 180, 290, 46)
                    pygame.draw.rect(screen, (70, 50, 15), eb_rect, border_radius=4)
                    pygame.draw.rect(screen, COLOR_GOLD, eb_rect, 2, border_radius=4)
                    screen.blit(font_xs.render(f"✎ CARVING: {f_name} ({num_tiles} tiles)", True, COLOR_GOLD), (886, 184))
                    screen.blit(font_xs.render("Click green tiles on map (Min 1)", True, (240, 240, 240)), (886, 202))
                    
                    # DONE button
                    done_btn = pygame.Rect(1028, 186, 68, 28)
                    d_hov = done_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (35, 100, 50) if d_hov else (25, 75, 40), done_btn, border_radius=4)
                    pygame.draw.rect(screen, COLOR_TEXT_GREEN, done_btn, 1, border_radius=4)
                    screen.blit(font_xs.render("DONE ✓", True, COLOR_TEXT_WHITE), (1038, 193))

                    # CANCEL button
                    can_btn = pygame.Rect(1100, 186, 65, 28)
                    can_hov = can_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (100, 35, 35) if can_hov else (75, 25, 25), can_btn, border_radius=4)
                    pygame.draw.rect(screen, COLOR_TEXT_RED, can_btn, 1, border_radius=4)
                    screen.blit(font_xs.render("CANCEL", True, COLOR_TEXT_WHITE), (1108, 193))

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
                    carve_btn = pygame.Rect(880, 182, 290, 28)
                    c_hov = carve_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (40, 75, 110) if c_hov else (30, 55, 85), carve_btn, border_radius=4)
                    pygame.draw.rect(screen, (100, 180, 255), carve_btn, 1, border_radius=4)
                    screen.blit(font_xs.render("+ CARVE NEW FIEF (Partition Land)", True, COLOR_TEXT_WHITE), (935, 188))
                    if mouse_clicked and c_hov:
                        carve_new_fief(state, state.selected_province)
                    fy = 216

                # Pagination slice
                start_i = state.fief_page * per_page
                page_fiefs = prov_fiefs[start_i:start_i + per_page]

                for f_data in page_fiefs:
                    f_box = pygame.Rect(880, fy, 290, 64)
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

                    screen.blit(font_xs.render(f"⚔ {f_data['name']} ({len(f_data['tiles'])} Tiles)", True, COLOR_GOLD), (888, fy + 4))
                    screen.blit(font_xs.render(holder_str, True, h_col), (888, fy + 18))

                    # Action buttons on fief card
                    e_hov = False
                    g_hov = False
                    d_hov = False
                    r_hov = False

                    # 1. Edit Tiles Button
                    b_edit = pygame.Rect(888, fy + 36, 75, 20)
                    e_hov = b_edit.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (80, 70, 30) if e_hov else (50, 45, 25), b_edit, border_radius=3)
                    pygame.draw.rect(screen, COLOR_GOLD, b_edit, 1, border_radius=3)
                    screen.blit(font_xs.render("EDIT ✎" if not is_f_editing else "STOP ✕", True, COLOR_GOLD), (902, fy + 38))
                    if mouse_clicked and e_hov:
                        state.editing_fief_id = None if is_f_editing else f_data["id"]
                        state.selected_fief_id = f_data["id"]
                        if state.editing_fief_id:
                            state.selected_settlement = None

                    # 2. Grant / Revoke Buttons
                    if is_ungranted or is_crown_owned:
                        # Grant Fief Button (Opens Vassal Selection Modal)
                        b_grant = pygame.Rect(970, fy + 36, 120, 20)
                        g_hov = b_grant.collidepoint(mouse_pos)
                        pygame.draw.rect(screen, (40, 110, 60) if g_hov else (30, 80, 45), b_grant, border_radius=3)
                        pygame.draw.rect(screen, COLOR_TEXT_GREEN, b_grant, 1, border_radius=3)
                        screen.blit(font_xs.render("GRANT TO VASSAL", True, COLOR_TEXT_WHITE), (982, fy + 38))
                        if mouse_clicked and g_hov:
                            state.granting_fief_id = f_data["id"]
                            state.grant_page = 0

                        # 3. Dissolve Button
                        b_del = pygame.Rect(1096, fy + 36, 68, 20)
                        d_hov = b_del.collidepoint(mouse_pos)
                        pygame.draw.rect(screen, (85, 30, 30) if d_hov else (60, 25, 25), b_del, border_radius=3)
                        pygame.draw.rect(screen, (220, 80, 80), b_del, 1, border_radius=3)
                        screen.blit(font_xs.render("DISSOLVE", True, (255, 200, 200)), (1104, fy + 38))
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
                        b_revoke = pygame.Rect(970, fy + 36, 194, 20)
                        r_hov = b_revoke.collidepoint(mouse_pos)
                        pygame.draw.rect(screen, (100, 45, 45) if r_hov else (70, 30, 30), b_revoke, border_radius=3)
                        pygame.draw.rect(screen, (240, 100, 100), b_revoke, 1, border_radius=3)
                        screen.blit(font_xs.render("REVOKE FIEF (♚ Return to Crown)", True, COLOR_TEXT_WHITE), (980, fy + 38))
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
                    prev_btn = pygame.Rect(880, py_bar, 85, 26)
                    next_btn = pygame.Rect(1085, py_bar, 85, 26)
                    p_hov = prev_btn.collidepoint(mouse_pos)
                    n_hov = next_btn.collidepoint(mouse_pos)

                    pygame.draw.rect(screen, COLOR_BUTTON_HOVER if p_hov else COLOR_BUTTON_NORMAL, prev_btn, border_radius=4)
                    pygame.draw.rect(screen, COLOR_GOLD if p_hov else COLOR_PANEL_BORDER, prev_btn, 1, border_radius=4)
                    screen.blit(font_xs.render("< PREV", True, COLOR_TEXT_WHITE if state.fief_page > 0 else COLOR_TEXT_MUTED), (898, py_bar + 5))

                    pygame.draw.rect(screen, COLOR_BUTTON_HOVER if n_hov else COLOR_BUTTON_NORMAL, next_btn, border_radius=4)
                    pygame.draw.rect(screen, COLOR_GOLD if n_hov else COLOR_PANEL_BORDER, next_btn, 1, border_radius=4)
                    screen.blit(font_xs.render("NEXT >", True, COLOR_TEXT_WHITE if state.fief_page < total_pages - 1 else COLOR_TEXT_MUTED), (1108, py_bar + 5))

                    pg_lbl = font_xs.render(f"Page {state.fief_page + 1}/{total_pages} ({total_fiefs} Fiefs)", True, COLOR_GOLD)
                    screen.blit(pg_lbl, (970 + (110 - pg_lbl.get_width()) // 2, py_bar + 5))

                    if mouse_clicked and p_hov and state.fief_page > 0:
                        state.fief_page -= 1
                    elif mouse_clicked and n_hov and state.fief_page < total_pages - 1:
                        state.fief_page += 1
            else:
                # Enemy Province Instructions
                screen.blit(font_md.render("Viking Controlled Territory", True, COLOR_TEXT_RED), (880, 415))
                screen.blit(font_sm.render("To conquer this province:", True, COLOR_TEXT_MUTED), (880, 445))
                screen.blit(font_xs.render("1. Raise levies from your provinces.", True, COLOR_TEXT_WHITE), (880, 470))
                screen.blit(font_xs.render("2. Rally & merge your hosts into an army.", True, COLOR_TEXT_WHITE), (880, 490))
                screen.blit(font_xs.render("3. Select your army and click here to march!", True, COLOR_GOLD), (880, 510))

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
            req_cost = req.get("cost", 600 if req_type == "city" else 1000)
            req_name = "Commercial City" if req_type == "city" else "Fortress Keep"

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

            pop_w, pop_h = 680, 530
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
            p_full = prov_data.get("name", "Wessex")
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
            screen.blit(font_md.render(f"♚ {v_obj['name']}", True, (255, 120, 120) if is_enemy else COLOR_GOLD), (pop_x + 90, pop_y + 74))
            v_religion = "Norse Pagan" if p_owner == state.enemy_id else prov_data.get("faith", "Catholic")
            v_culture = "Norse" if p_owner == state.enemy_id else prov_data.get("culture", "Anglo-Saxon")
            rank_str = f"Feudal Rank: {v_obj.get('title', 'Thane')} of {p_full.split()[0]}  •  Religion: {v_religion} ({v_culture})"
            screen.blit(font_xs.render(rank_str, True, COLOR_TEXT_WHITE), (pop_x + 90, pop_y + 98))
            seat_str = f"Seat of Power: {v_obj.get('city_name')}" if is_landed and v_obj.get('city_name') else "Seat of Power: Landless Subject (Awaiting Royal Charter)"
            screen.blit(font_xs.render(seat_str, True, (140, 205, 255)), (pop_x + 90, pop_y + 114))

            # Feudal Attributes Grid (Martial, Stewardship, Diplomacy, Feudal Oath)
            oath_val = f"100% ({liege_char['name'].split()[1]})" if is_enemy else "100%"
            oath_sub = "(Enemy Vassal)" if is_enemy else "(Faithful Subject)"
            stats_list = [
                ("⚔ Martial", f"{10 + (levies_contrib // 30)}" if is_landed else "8", "(Commands Fyrd)"),
                ("◆ Stewardship", f"{11 + (tax_paid * 2)}" if is_landed else "9", "(Manages Estates)"),
                ("◆ Diplomacy", "11" if is_enemy else "13", "(Foreign Court)" if is_enemy else "(Royal Harmony)"),
                ("⚔ Feudal Oath", oath_val, oath_sub)
            ]
            for s_i, (s_name, s_val, s_sub) in enumerate(stats_list):
                bx = pop_x + 25 + s_i * 158
                by = pop_y + 138
                b_rect = pygame.Rect(bx, by, 150, 44)
                pygame.draw.rect(screen, (34, 40, 54), b_rect, border_radius=4)
                pygame.draw.rect(screen, (160, 60, 60) if is_enemy else COLOR_PANEL_BORDER, b_rect, 1, border_radius=4)
                screen.blit(font_xs.render(s_name, True, COLOR_TEXT_MUTED), (bx + 8, by + 4))
                screen.blit(font_md.render(s_val, True, (255, 120, 120) if is_enemy else COLOR_GOLD), (bx + 8, by + 18))
                screen.blit(font_xs.render(s_sub, True, (120, 160, 200)), (bx + 48, by + 22))

            # Two Main Columns: Economy & Treasury (Left), Military & Fiefs (Right)
            col_w = 305
            col_y = pop_y + 194

            # LEFT COLUMN: ECONOMY & INCOME ("income etc seluruhnya")
            left_rect = pygame.Rect(pop_x + 25, col_y, col_w, 245)
            pygame.draw.rect(screen, (30, 36, 48), left_rect, border_radius=6)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, left_rect, 1, border_radius=6)
            
            screen.blit(font_md.render("◆ Vassal Finances & Revenue", True, COLOR_GOLD), (pop_x + 35, col_y + 10))
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 35, col_y + 32), (pop_x + 35 + col_w - 20, col_y + 32), 1)

            screen.blit(font_sm.render(f"Treasury: {v_obj['gold']} Gold", True, COLOR_GOLD), (pop_x + 40, col_y + 40))
            
            # Breakdown of monthly finances
            if is_landed:
                screen.blit(font_xs.render(f"• Gross Domain Income: +{monthly_gross}g / month", True, (160, 220, 180)), (pop_x + 40, col_y + 68))
                screen.blit(font_xs.render("  (From tenant rents, tolls & agricultural yield)", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 84))
                screen.blit(font_xs.render(f"• Feudal Royal Tax ({tax_rate}%): -{tax_paid}g / month", True, COLOR_TEXT_RED), (pop_x + 40, col_y + 104))
                
                # Interactive Tax Controls in Dossier (Player only)
                if not is_enemy:
                    d_t_dec = pygame.Rect(pop_x + 214, col_y + 102, 16, 16)
                    d_t_inc = pygame.Rect(pop_x + 232, col_y + 102, 16, 16)
                    d_t_lock = pygame.Rect(pop_x + 250, col_y + 102, 68, 16)

                    h_t_dec = d_t_dec.collidepoint(mouse_pos)
                    h_t_inc = d_t_inc.collidepoint(mouse_pos)
                    h_t_lock = d_t_lock.collidepoint(mouse_pos)

                    is_t_locked = v_obj.get("tax_locked", False)
                    pygame.draw.rect(screen, (70, 80, 100) if h_t_dec else (42, 48, 62), d_t_dec, border_radius=3)
                    pygame.draw.rect(screen, COLOR_PANEL_BORDER, d_t_dec, 1, border_radius=3)
                    screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE), (pop_x + 219, col_y + 101))

                    pygame.draw.rect(screen, (70, 80, 100) if h_t_inc else (42, 48, 62), d_t_inc, border_radius=3)
                    pygame.draw.rect(screen, COLOR_PANEL_BORDER, d_t_inc, 1, border_radius=3)
                    screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE), (pop_x + 236, col_y + 101))

                    l_t_bg = (65, 50, 20) if is_t_locked else ((45, 52, 68) if h_t_lock else (28, 34, 46))
                    l_t_bd = COLOR_GOLD if is_t_locked else ((120, 160, 210) if h_t_lock else (70, 80, 95))
                    pygame.draw.rect(screen, l_t_bg, d_t_lock, border_radius=3)
                    pygame.draw.rect(screen, l_t_bd, d_t_lock, 1, border_radius=3)
                    l_t_txt = "◈ LOCKED" if is_t_locked else "◇ UNLOCK"
                    l_t_col = COLOR_GOLD if is_t_locked else COLOR_TEXT_MUTED
                    l_t_lbl = font_xs.render(l_t_txt, True, l_t_col)
                    screen.blit(l_t_lbl, (d_t_lock.x + (d_t_lock.w - l_t_lbl.get_width()) // 2, col_y + 102))

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

                screen.blit(font_xs.render(f"  (Directly enriches {liege_char['name']}'s treasury)", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 120))
                screen.blit(font_xs.render(f"• Net Monthly Savings: +{net_profit}g / month", True, COLOR_TEXT_GREEN), (pop_x + 40, col_y + 140))
            else:
                screen.blit(font_xs.render("• Gross Domain Income: 0g / month", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 68))
                screen.blit(font_xs.render("  (Landless noble holds no estates or tolls)", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 84))
                screen.blit(font_xs.render(f"• Feudal Royal Tax ({tax_rate}%): 0g / month", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 104))
                screen.blit(font_xs.render(f"  (No domain revenue subject to royal taxation)", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 120))
                screen.blit(font_xs.render("• Net Monthly Savings: 0g / month", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 140))
            
            # Autonomous Charter Status Bar
            screen.blit(font_xs.render("• Charter Fund (1,000g needed to build town):", True, COLOR_GOLD), (pop_x + 40, col_y + 168))
            bar_w = col_w - 30
            bar_h = 16
            bx = pop_x + 40
            by = col_y + 188
            pygame.draw.rect(screen, (20, 24, 32), (bx, by, bar_w, bar_h), border_radius=3)
            fill_pct = min(1.0, max(0.0, v_obj['gold'] / 1000.0))
            if fill_pct > 0:
                pygame.draw.rect(screen, COLOR_GOLD if fill_pct >= 1.0 else (80, 150, 240), (bx, by, int(bar_w * fill_pct), bar_h), border_radius=3)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, (bx, by, bar_w, bar_h), 1, border_radius=3)
            p_text = f"{v_obj['gold']} / 1,000g ({int(fill_pct * 100)}%)"
            p_lbl = font_xs.render(p_text, True, COLOR_TEXT_WHITE)
            screen.blit(p_lbl, (bx + (bar_w - p_lbl.get_width()) // 2, by + 1))

            status_str = "Eligible to petition charter!" if v_obj['gold'] >= 1000 else f"Needs {1000 - v_obj['gold']}g more to petition build"
            screen.blit(font_xs.render(status_str, True, COLOR_GOLD if v_obj['gold'] >= 1000 else (180, 190, 205)), (pop_x + 40, col_y + 212))

            # RIGHT COLUMN: MILITARY & DOMAIN ("keseluruhan kekuasaan dia")
            right_rect = pygame.Rect(pop_x + 350, col_y, col_w, 245)
            pygame.draw.rect(screen, (30, 36, 48), right_rect, border_radius=6)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, right_rect, 1, border_radius=6)

            screen.blit(font_md.render("⚔ Military Duty & Fiefdoms", True, COLOR_GOLD), (pop_x + 360, col_y + 10))
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 360, col_y + 32), (pop_x + 360 + col_w - 20, col_y + 32), 1)

            if is_landed:
                screen.blit(font_sm.render(f"Fyrd Levies ({levy_rate}%): +{levies_contrib} Soldiers", True, COLOR_TEXT_GREEN), (pop_x + 365, col_y + 40))

                # Interactive Levy Controls in Dossier (Player only)
                if not is_enemy:
                    d_l_dec = pygame.Rect(pop_x + 538, col_y + 40, 16, 16)
                    d_l_inc = pygame.Rect(pop_x + 556, col_y + 40, 16, 16)
                    d_l_lock = pygame.Rect(pop_x + 574, col_y + 40, 68, 16)

                    h_l_dec = d_l_dec.collidepoint(mouse_pos)
                    h_l_inc = d_l_inc.collidepoint(mouse_pos)
                    h_l_lock = d_l_lock.collidepoint(mouse_pos)

                    is_l_locked = v_obj.get("levy_locked", False)
                    pygame.draw.rect(screen, (70, 80, 100) if h_l_dec else (42, 48, 62), d_l_dec, border_radius=3)
                    pygame.draw.rect(screen, COLOR_PANEL_BORDER, d_l_dec, 1, border_radius=3)
                    screen.blit(font_xs.render("-", True, COLOR_TEXT_WHITE), (pop_x + 543, col_y + 39))

                    pygame.draw.rect(screen, (70, 80, 100) if h_l_inc else (42, 48, 62), d_l_inc, border_radius=3)
                    pygame.draw.rect(screen, COLOR_PANEL_BORDER, d_l_inc, 1, border_radius=3)
                    screen.blit(font_xs.render("+", True, COLOR_TEXT_WHITE), (pop_x + 560, col_y + 39))

                    l_l_bg = (65, 50, 20) if is_l_locked else ((45, 52, 68) if h_l_lock else (28, 34, 46))
                    l_l_bd = COLOR_GOLD if is_l_locked else ((120, 160, 210) if h_l_lock else (70, 80, 95))
                    pygame.draw.rect(screen, l_l_bg, d_l_lock, border_radius=3)
                    pygame.draw.rect(screen, l_l_bd, d_l_lock, 1, border_radius=3)
                    l_l_txt = "◈ LOCKED" if is_l_locked else "◇ UNLOCK"
                    l_l_col = COLOR_GOLD if is_l_locked else COLOR_TEXT_MUTED
                    l_l_lbl = font_xs.render(l_l_txt, True, l_l_col)
                    screen.blit(l_l_lbl, (d_l_lock.x + (d_l_lock.w - l_l_lbl.get_width()) // 2, col_y + 40))

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

                screen.blit(font_xs.render(f"• Household Guards (Kept): {household_guard} Men", True, COLOR_TEXT_WHITE), (pop_x + 365, col_y + 66))
                screen.blit(font_xs.render(f"• Total Domain Force: {total_garrison} Men", True, (170, 200, 230)), (pop_x + 365, col_y + 82))
                service_text = f"• Feudal Service: Pledged to {liege_char['name'].split()[1]}'s banner" if is_enemy else "• Feudal Service: Ready to march on King's call"
                screen.blit(font_xs.render(service_text, True, COLOR_TEXT_MUTED), (pop_x + 365, col_y + 98))
                screen.blit(font_xs.render(f"• Fiefdoms Controlled: {len(held_fiefs)} Fief(s) ({total_held_tiles} Tiles)", True, (150, 215, 255)), (pop_x + 365, col_y + 114))
            else:
                screen.blit(font_sm.render(f"Fyrd Levies ({levy_rate}%): 0 Soldiers", True, COLOR_TEXT_MUTED), (pop_x + 365, col_y + 40))
                screen.blit(font_xs.render("• Household Guards: None (Unlanded)", True, COLOR_TEXT_MUTED), (pop_x + 365, col_y + 66))
                screen.blit(font_xs.render("• Total Domain Force: 0 Men", True, COLOR_TEXT_MUTED), (pop_x + 365, col_y + 82))
                screen.blit(font_xs.render("• Feudal Service: Awaiting royal fief or title", True, COLOR_TEXT_MUTED), (pop_x + 365, col_y + 98))
                screen.blit(font_xs.render("• Fiefdoms Controlled: 0 Fiefs (0 Tiles)", True, COLOR_TEXT_MUTED), (pop_x + 365, col_y + 114))
            
            # List held fiefs
            fy_item = col_y + 132
            if not held_fiefs:
                screen.blit(font_xs.render("• No fiefdoms granted yet (Unlanded)", True, COLOR_TEXT_MUTED), (pop_x + 365, fy_item))
            else:
                for h_f in held_fiefs[:4]:
                    f_prov = PROVINCES.get(h_f["province"], {}).get("name", "").split()[0]
                    f_sub = f"  - {h_f['name']} ({len(h_f['tiles'])}t in {f_prov})"
                    screen.blit(font_xs.render(f_sub, True, COLOR_GOLD), (pop_x + 365, fy_item))
                    fy_item += 19

            # Action Buttons at Bottom
            btn_w, btn_h = 280, 38
            
            # Button 1: Locate on Map (pans camera to vassal seat)
            loc_btn = pygame.Rect(pop_x + 40, pop_y + pop_h - 60, btn_w, btn_h)
            loc_hov = loc_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (40, 85, 130) if loc_hov else (28, 60, 95), loc_btn, border_radius=6)
            pygame.draw.rect(screen, (100, 180, 255), loc_btn, 1, border_radius=6)
            screen.blit(font_sm.render("▶ LOCATE SEAT ON MAP", True, COLOR_TEXT_WHITE), (pop_x + 95, pop_y + pop_h - 50))
            if modal_mouse_clicked and loc_hov:
                state.selected_province = v_pid
                if v_obj.get("tiles"):
                    tc, tr = v_obj["tiles"][0]
                    state.selected_settlement = (tc, tr)
                    # Pan camera to focus on this holding
                    state.cam_pan_x = VIEWPORT_CENTER_X - (tc * curr_tile_w + curr_tile_w // 2)
                    state.cam_pan_y = VIEWPORT_CENTER_Y - (tr * curr_tile_h + curr_tile_h // 2)
                state.inspecting_vassal = None
                state.logs.append(f"Centering camera on {v_obj['name']}'s seat in {p_full}.")

            # Button 2: Close Dossier (ESC)
            close_btn = pygame.Rect(pop_x + pop_w - 40 - btn_w, pop_y + pop_h - 60, btn_w, btn_h)
            c_hov = close_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (75, 35, 35) if c_hov else (55, 25, 25), close_btn, border_radius=6)
            pygame.draw.rect(screen, (220, 80, 80), close_btn, 1, border_radius=6)
            screen.blit(font_sm.render("CLOSE DOSSIER (ESC)", True, (255, 220, 220)), (pop_x + pop_w - 40 - btn_w + 70, pop_y + pop_h - 50))
            if modal_mouse_clicked and c_hov:
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

            pop_w, pop_h = 680, 500
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
            col_w = 305
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

            screen.blit(font_md.render("⚔ Military Might & Feudal Roster", True, COLOR_GOLD), (pop_x + 360, col_y + 10))
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 360, col_y + 32), (pop_x + 360 + col_w - 20, col_y + 32), 1)

            screen.blit(font_sm.render(f"Available Levies: {total_garrison:,} Men", True, COLOR_TEXT_GREEN), (pop_x + 365, col_y + 40))
            screen.blit(font_xs.render(f"• Active Armies in Field: {total_armies_count} Hosts ({total_field:,} Men)", True, (255, 200, 120)), (pop_x + 365, col_y + 66))
            screen.blit(font_xs.render(f"• Sworn Feudal Lords: {len(r_vassals)} Vassals", True, COLOR_TEXT_WHITE), (pop_x + 365, col_y + 88))
            screen.blit(font_xs.render(f"• Capital Province: {'Jorvik (York)' if is_ruler_enemy else 'Wessex (Winchester)'}", True, (150, 215, 255)), (pop_x + 365, col_y + 110))
            
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
            cap_name = "JORVIK" if is_ruler_enemy else "WESSEX"
            screen.blit(font_sm.render(f"▶ LOCATE CAPITAL ({cap_name})", True, COLOR_TEXT_WHITE), (pop_x + 75, pop_y + pop_h - 45))
            if modal_mouse_clicked and loc_hov:
                cap_prov = "jorvik" if is_ruler_enemy else "wessex"
                state.selected_province = cap_prov
                cap_coord = (14, 12) if is_ruler_enemy else (4, 18)
                curr_tw = max(18, int(BASE_TILE_W * state.zoom))
                curr_th = max(16, int(BASE_TILE_H * state.zoom))
                state.cam_pan_x = VIEWPORT_CENTER_X - (cap_coord[0] * curr_tw + curr_tw // 2)
                state.cam_pan_y = VIEWPORT_CENTER_Y - (cap_coord[1] * curr_th + curr_th // 2)
                state.inspecting_ruler = None
                state.logs.append(f"Focusing camera on {r_char['name']}'s seat in {cap_prov.title()}.")

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
            t5 = font_xs.render(f"• Royal Treasury: -{b_cost:,} Gold  |  Constructs {b_spec['name']} ({b_spec['desc']}).", True, COLOR_GOLD)

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

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_game()
