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
import pygame

# Initialize Pygame
pygame.init()
pygame.font.init()

# Game Window Dimensions
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 720
FPS = 60

# Set display mode immediately
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("CK2-Lite: The War for Britain (Army Raising & Rally Edition)")

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

# Fonts
font_xs = pygame.font.SysFont("segoeui", 12, bold=True)
font_sm = pygame.font.SysFont("segoeui", 14)
font_md = pygame.font.SysFont("segoeui", 17, bold=True)
font_lg = pygame.font.SysFont("segoeui", 22, bold=True)
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

def reset_global_world_data():
    """Restores PROVINCES and CHARACTERS dictionaries to pristine AD 867 state."""
    CHARACTERS.clear()
    CHARACTERS.update(copy.deepcopy(INITIAL_CHARACTERS))
    PROVINCES.clear()
    PROVINCES.update(copy.deepcopy(INITIAL_PROVINCES))

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

def draw_waving_banner(surface, cloth_surf, pole_x, pole_y, pole_h, ticks, amp=3.0, freq=0.25, is_main=False):
    # Wooden flagpole
    top_y = pole_y - pole_h
    pygame.draw.line(surface, (45, 30, 20), (pole_x, top_y), (pole_x, pole_y), 2 if is_main else 1)
    pygame.draw.line(surface, (95, 70, 48), (pole_x - 1, top_y), (pole_x - 1, pole_y), 1)

    # Golden Spearhead Finial on top
    finial_h = 7 if is_main else 4
    finial_w = 4 if is_main else 2
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
    cloth_top = top_y + (4 if is_main else 2)
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
    "wessex": ["cornwall", "mercia", "kent_essex", "wales"],
    "kent_essex": ["wessex", "mercia", "east_anglia"],
    "mercia": ["wessex", "kent_essex", "east_anglia", "wales", "deira", "jorvik"],
    "wales": ["wessex", "mercia", "deira"],
    "east_anglia": ["kent_essex", "mercia", "jorvik"],
    "jorvik": ["mercia", "east_anglia", "deira", "bernicia"],
    "deira": ["mercia", "wales", "jorvik", "bernicia"],
    "bernicia": ["deira", "jorvik", "strathclyde", "lothian"],
    "strathclyde": ["bernicia", "lothian", "highlands"],
    "lothian": ["bernicia", "strathclyde", "highlands"],
    "highlands": ["strathclyde", "lothian"]
}

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
        
        # Mobilization & Demobilization
        self.is_mustering = False
        self.muster_days = 0
        self.is_demobilizing = False

    @property
    def is_moving(self):
        return len(self.path) > 0

    @property
    def next_province(self):
        return self.path[0] if self.path else None

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
        
        # City Building Mode State
        self.build_mode = False          # True when building a settlement
        self.build_type = "town"         # "town" (2 tiles) or "castle" (1 tile)
        self.build_orientation = "H"     # "H" (Horizontal) or "V" (Vertical) for 2-tile
        self.settlements = {}            # (c, r) -> {"province": pid, "type": "town", "name": str}
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
        self.pre_popup_speed = None      # Saved game speed before a popup paused the game
        self.popup_was_active = False    # Track whether a popup was active on previous frame
        
        # Left Panel Sub-Tab System ('armies', 'vassals', or 'demesne')
        self.left_tab = "armies"
        self.vassal_page = 0
        self.fief_page = 0
        
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
            count = random.randint(1, 5)
            is_norse = (pdata["owner"] == self.enemy_id)
            v_list = []
            for i in range(count):
                fn = random.choice(viking_first_names if is_norse else saxon_first_names)
                ep = random.choice(viking_epithets if is_norse else saxon_epithets)
                title = random.choice(["Jarl", "Hersir", "Gothi"] if is_norse else ["Thane", "Baron", "Ealdorman"])
                v_list.append({
                    "id": f"{pid}_vassal_{i}",
                    "name": f"{title} {fn} '{ep}'",
                    "levy_contribution": random.randint(80, 260),
                    "tax_contribution": random.randint(3, 8),
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
        is_royal = (province_id == "wessex")
        new_army = Army(army_id, self.player_id, province_id, available, army_name,
                        flag_origin=province_id, rank=3 if is_royal else 1)
        new_army.is_mustering = True
        new_army.muster_days = 30
        self.armies.append(new_army)
        
        prov["levies_current"] = 0
        self.selected_army_id = army_id
        self.logs.append(f"Summoned {available:,} men in {prov['name']}! Mustering troops (30 days)...")

    def raise_all_levies(self):
        raised_count = 0
        total_men = 0
        for pid, prov in PROVINCES.items():
            if prov["owner"] == self.player_id and prov["levies_current"] > 0:
                available = prov["levies_current"]
                army_id = f"army_{self.army_id_counter}"
                self.army_id_counter += 1
                army_name = f"{prov['name'].split()[0]} Fyrd"
                is_royal = (pid == "wessex")
                new_army = Army(army_id, self.player_id, pid, available, army_name,
                                flag_origin=pid, rank=3 if is_royal else 1)
                new_army.is_mustering = True
                new_army.muster_days = 30
                self.armies.append(new_army)
                prov["levies_current"] = 0
                raised_count += 1
                total_men += available
        
        if raised_count > 0:
            self.logs.append(f"Mobilized all realm levies: {total_men:,} men in {raised_count} hosts! (Mustering for 30 days)")
        else:
            self.logs.append("All available levies are already raised.")

    def rally_all_armies_to(self, target_province_id):
        player_armies = [a for a in self.armies if a.owner == self.player_id]
        if not player_armies:
            self.logs.append("No active armies to rally! Raise levies first.")
            return

        rallied = 0
        for a in player_armies:
            if a.province != target_province_id:
                path = find_shortest_path(a.province, target_province_id)
                if path and len(path) > 1:
                    a.path = path[1:]
                    a.move_progress = 0.0
                    a.is_sieging = False
                    rallied += 1
        
        target_name = PROVINCES[target_province_id]["name"]
        self.logs.append(f"Rally orders issued! {len(player_armies)} hosts marching to {target_name}.")

    def merge_armies_in_province(self, province_id, owner_id):
        armies_here = [a for a in self.armies if a.province == province_id and a.owner == owner_id and not a.is_moving and not a.is_demobilizing and not a.is_mustering]
        if len(armies_here) <= 1:
            return

        total_troops = sum(a.troops for a in armies_here)
        # Sort by rank descending, then troops descending to find dominant host
        armies_here.sort(key=lambda x: (x.rank, x.troops), reverse=True)
        dominant_army = armies_here[0]
        dominant_army.troops = total_troops
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

        # If mustering, cancel muster and refund troops immediately
        if army.is_mustering:
            prov = PROVINCES.get(army.flag_origin)
            if prov:
                prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + army.troops)
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

        # Update Muster Preparation Days
        for a in list(self.armies):
            if a.is_mustering:
                a.muster_days -= 1
                if a.muster_days <= 0:
                    a.is_mustering = False
                    self.logs.append(f"🎺 {a.name} is fully assembled and battle-ready!")

        # Update Army Movements & Combat
        self.update_armies()

        # AI Behavior
        self.ai_timer -= 1
        if self.ai_timer <= 0:
            self.ai_timer = random.randint(35, 55)
            self.ai_routine()

    def monthly_tick(self):
        # Tax collection and levy reinforcement
        for pid, prov in PROVINCES.items():
            owner = CHARACTERS.get(prov["owner"])
            if owner:
                owner["gold"] += prov["tax"]
                # Reinforce unraised garrison slowly
                if prov["levies_current"] < prov["levies_max"]:
                    prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + 50)
                # Vassal tax contribution & economy
                for v in self.vassals.get(pid, []):
                    owner["gold"] += v.get("tax_contribution", 3)
                    v["gold"] = v.get("gold", 150) + random.randint(15, 35)
        
        # Army upkeep cost (1 gold per 500 men)
        player_troops = self.get_field_troops(self.player_id)
        upkeep = player_troops // 500
        self.player["gold"] = max(0, self.player["gold"] - upkeep)

        self.player["prestige"] += 1
        self.player["piety"] += 1
        self.enemy["prestige"] += 1

        # Vassal autonomous build request chance: ONLY IF Vassal has at least 1,000 Gold AND owns a fief with free unbuilt tiles!
        if not self.vassal_build_requests:
            player_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.player_id]
            if player_provs and random.random() < 0.35:
                eligible_petitions = []
                for pid in player_provs:
                    v_list = self.vassals.get(pid, [])
                    for v in v_list:
                        if v.get("gold", 0) >= 1000:
                            # Vassal MUST own a fief in this province
                            v_fiefs = [f for f in self.fiefs.values() if f.get("province") == pid and (f.get("holder") == v["name"] or f.get("vassal_id") == v.get("id"))]
                            for f in v_fiefs:
                                # Fief must have at least one tile without an existing settlement
                                free_tiles = [t for t in f.get("tiles", []) if t not in self.settlements]
                                if free_tiles:
                                    free_set = set(free_tiles)
                                    pair = None
                                    for (c, r) in free_tiles:
                                        if (c + 1, r) in free_set:
                                            pair = [(c, r), (c + 1, r)]
                                            break
                                        elif (c, r + 1) in free_set:
                                            pair = [(c, r), (c, r + 1)]
                                            break
                                    if not pair:
                                        pair = [free_tiles[0]]
                                    
                                    eligible_petitions.append({
                                        "vassal": v["name"],
                                        "vassal_ref": v,
                                        "province_id": pid,
                                        "province_name": PROVINCES[pid]["name"],
                                        "fief_id": f["id"],
                                        "fief_name": f["name"],
                                        "build_tiles": pair,
                                        "cost": 1000
                                    })
                if eligible_petitions:
                    req_choice = random.choice(eligible_petitions)
                    self.vassal_build_requests.append(req_choice)
                    self.logs.append(f"Charter Petition: {req_choice['vassal']} (1,000g) petitions to build inside {req_choice['fief_name']} ({req_choice['province_name']})!")

    def yearly_tick(self):
        self.player["age"] += 1
        self.enemy["age"] += 1
        self.logs.append(f"AD {self.year}: War rages across the lands of Britain.")

    def update_armies(self):
        # 1. Update movement
        for a in list(self.armies):
            if a.is_moving and not a.in_battle:
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

            p1_list = [a for a in self.armies if a.province == pid and a.owner == self.player_id and not a.is_moving]
            p2_list = [a for a in self.armies if a.province == pid and a.owner == self.enemy_id and not a.is_moving]

            if not (p1_list and p2_list):
                for a in p1_list + p2_list:
                    a.in_battle = False
                continue

            a1 = p1_list[0]
            a2 = p2_list[0]
            a1.in_battle = True
            a2.in_battle  = True
            a1.is_sieging = False
            a2.is_sieging = False
            a1.is_demobilizing = False
            a2.is_demobilizing = False

            # One combat round per game-tick
            alfred_martial  = self.player["stats"]["martial"]
            halfdan_martial = self.enemy["stats"]["martial"]

            dmg_to_a2 = max(1, int(a1.troops * 0.08 * (1 + alfred_martial * 0.02))  + random.randint(10, 50))
            dmg_to_a1 = max(1, int(a2.troops * 0.08 * (1 + halfdan_martial * 0.02)) + random.randint(10, 50))

            a1.troops = max(0, a1.troops - dmg_to_a1)
            a2.troops = max(0, a2.troops - dmg_to_a2)

            if a1.troops <= 0 and a2.troops <= 0:
                self.logs.append(f"Both armies annihilated at {PROVINCES[pid]['name']}!")
                if a1 in self.armies: self.armies.remove(a1)
                if a2 in self.armies: self.armies.remove(a2)
            elif a1.troops <= 0:
                self.logs.append(f"Defeat! {a1.name} was wiped out at {PROVINCES[pid]['name']}!")
                if a1 in self.armies: self.armies.remove(a1)
                a2.in_battle = False
            elif a2.troops <= 0:
                self.logs.append(f"Glorious Victory! Destroyed the Viking host at {PROVINCES[pid]['name']}!")
                if a2 in self.armies: self.armies.remove(a2)
                a1.in_battle = False

        # 3. Check Sieges (City-by-City Siege in Enemy or Contested Province)
        for a in list(self.armies):
            if a not in self.armies:
                continue
            if a.is_moving or a.in_battle or a.is_mustering or a.is_demobilizing:
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
                            prov["color"] = list(COLOR_WESSEX if a.owner == self.player_id else COLOR_DANELAW)
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
                    prov["color"] = list(COLOR_WESSEX if a.owner == self.player_id else COLOR_DANELAW)
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
    # AI (Halfdan Ragnarsson)
    # ---------------------------------------------------------
    def ai_routine(self):
        danelaw_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.enemy_id]
        if not danelaw_provs:
            return

        danelaw_armies = [a for a in self.armies if a.owner == self.enemy_id and not a.is_mustering]
        
        # 1. Raise Levies if none active
        if not danelaw_armies and not any(a.owner == self.enemy_id for a in self.armies):
            for pid in danelaw_provs:
                p = PROVINCES[pid]
                if p["levies_current"] > 500:
                    army_id = f"army_{self.army_id_counter}"
                    self.army_id_counter += 1
                    host = Army(army_id, self.enemy_id, pid, p["levies_current"], "Viking Warband")
                    host.is_mustering = True
                    host.muster_days = 20
                    self.armies.append(host)
                    p["levies_current"] = 0
            self.logs.append("Ravens squawk! The Danelaw has summoned their Viking hosts (Mustering)!")
            return

        # 2. Rally Viking armies into Jorvik or a border province
        rally_point = "jorvik" if "jorvik" in danelaw_provs else random.choice(danelaw_provs)
        for a in danelaw_armies:
            if a.province != rally_point and not a.is_moving:
                path = find_shortest_path(a.province, rally_point)
                if path and len(path) > 1:
                    a.path = path[1:]
                    a.move_progress = 0.0

        # 3. If armies gathered in rally point, march to attack player border province!
        gathered = [a for a in danelaw_armies if a.province == rally_point and not a.is_moving]
        if gathered:
            self.merge_armies_in_province(rally_point, self.enemy_id)
            main_host = [a for a in self.armies if a.province == rally_point and a.owner == self.enemy_id]
            if main_host and main_host[0].troops >= 2000:
                player_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.player_id]
                if player_provs:
                    target = random.choice(player_provs)
                    path = find_shortest_path(rally_point, target)
                    if path and len(path) > 1:
                        main_host[0].path = path[1:]
                        main_host[0].move_progress = 0.0
                        self.logs.append(f"Alarm! Halfdan's Great Host marches towards {PROVINCES[target]['name']}!")

# -------------------------------------------------------------
# Main Game Loop
# -------------------------------------------------------------
def run_game():
    global screen
    if screen is None:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
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

    # Precompute border grid midpoints between touching provinces
    border_grid_sums = {}
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    for (c, r), pid_a in cell_to_prov.items():
        for dc, dr in dirs:
            pid_b = cell_to_prov.get((c + dc, r + dr))
            if pid_b and pid_b != pid_a:
                pair_key = (pid_a, pid_b)
                if pair_key not in border_grid_sums:
                    border_grid_sums[pair_key] = [0, 0, 0]
                border_grid_sums[pair_key][0] += c
                border_grid_sums[pair_key][1] += r
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
        # 1. RULER PERSONAL DEMESNE (3 Personal Crown Cities for King & Jarl)
        # -------------------------------------------------------------
        royal_demesnes = [
            # King Alfred's 3 Personal Royal Cities
            {"owner": target_state.player_id, "lord": target_state.player["name"], "province": "wessex", "city": "Royal Citadel of Winchester", "fief": "Crown Demesne of Winchester"},
            {"owner": target_state.player_id, "lord": target_state.player["name"], "province": "wessex", "city": "Royal Borough of Wilton", "fief": "Crown Demesne of Wilton"},
            {"owner": target_state.player_id, "lord": target_state.player["name"], "province": "kent_essex", "city": "Royal Castle of London", "fief": "Crown Demesne of London"},
            
            # Jarl Halfdan's 3 Personal Viking Strongholds
            {"owner": target_state.enemy_id, "lord": target_state.enemy["name"], "province": "jorvik", "city": "Great Hall of Jorvik", "fief": "Royal Demesne of Jorvik"},
            {"owner": target_state.enemy_id, "lord": target_state.enemy["name"], "province": "jorvik", "city": "Citadel of Eoforwic", "fief": "Royal Demesne of Eoforwic"},
            {"owner": target_state.enemy_id, "lord": target_state.enemy["name"], "province": "deira", "city": "Viking Stronghold of Deira", "fief": "Royal Demesne of Deira"},
        ]

        for spec in royal_demesnes:
            pid = spec["province"]
            tiles = prov_tile_list.get(pid, [])
            tile_set = set(tiles)
            used = used_tiles_by_prov[pid]
            pair = None
            for (c, r) in tiles:
                if (c, r) not in used and (c + 1, r) in tile_set and (c + 1, r) not in used:
                    pair = [(c, r), (c + 1, r)]
                    break
            if not pair:
                for (c, r) in tiles:
                    if (c, r) not in used and (c, r + 1) in tile_set and (c, r + 1) not in used:
                        pair = [(c, r), (c, r + 1)]
                        break
            if not pair:
                for (c, r) in tiles:
                    if (c, r) not in used:
                        pair = [(c, r)]
                        break
            if pair:
                s_id = f"settlement_{settlement_counter}"
                settlement_counter += 1
                for t in pair:
                    used.add(t)
                    target_state.settlements[t] = {
                        "id": s_id,
                        "province": pid,
                        "type": "town",
                        "name": spec["city"],
                        "lord": f"{spec['lord']} (Royal Demesne)",
                        "vassal_id": None,
                        "is_crown_demesne": True
                    }
                fid = f"fief_{fief_counter}"
                fief_counter += 1
                target_state.fiefs[fid] = {
                    "id": fid,
                    "province": pid,
                    "tiles": pair,
                    "name": spec["fief"],
                    "holder": spec["lord"],
                    "vassal_id": None,
                    "is_crown_demesne": True
                }

        # -------------------------------------------------------------
        # 2. VASSAL STARTER HOLDINGS & FIEFS (Remaining tiles)
        # -------------------------------------------------------------
        for pid, tiles in prov_tile_list.items():
            v_list = target_state.vassals.get(pid, [])
            tile_set = set(tiles)
            pname = PROVINCES[pid]["name"].split()[0]
            used = used_tiles_by_prov[pid]
            
            for idx, v in enumerate(v_list):
                city_name = f"{v['name'].split()[1]}'s {random.choice(['Keep', 'Burgh', 'Castle', 'Borough'])}"
                pair = None
                for (c, r) in tiles:
                    if (c, r) not in used and (c + 1, r) in tile_set and (c + 1, r) not in used:
                        pair = [(c, r), (c + 1, r)]
                        break
                if not pair:
                    for (c, r) in tiles:
                        if (c, r) not in used and (c, r + 1) in tile_set and (c, r + 1) not in used:
                            pair = [(c, r), (c, r + 1)]
                            break
                if not pair:
                    for (c, r) in tiles:
                        if (c, r) not in used:
                            pair = [(c, r)]
                            break

                if pair:
                    s_id = f"settlement_{settlement_counter}"
                    settlement_counter += 1
                    for t in pair:
                        used.add(t)
                        target_state.settlements[t] = {
                            "id": s_id,
                            "province": pid,
                            "type": "town",
                            "name": city_name,
                            "lord": v["name"],
                            "vassal_id": v["id"],
                            "is_crown_demesne": False
                        }
                    v["city_name"] = city_name
                    v["tiles"] = pair
                    fid = f"fief_{fief_counter}"
                    fief_counter += 1
                    target_state.fiefs[fid] = {
                        "id": fid,
                        "province": pid,
                        "tiles": pair,
                        "name": f"Barony of {v['name'].split()[1]}",
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
        
        if len(free_tiles) < 2:
            pname = PROVINCES[province_id]["name"]
            target_state.logs.append(f"Cannot carve fief: Only {len(free_tiles)} unclaimed tile(s) left in {pname} (Min 2 required). Dissolve an existing fief first.")
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
            "is_newly_carved": True
        }
        target_state.selected_fief_id = fid
        target_state.editing_fief_id = fid
        target_state.selected_settlement = None
        target_state.logs.append(f"Partition Mode: Click at least 2 green unclaimed tiles on map for '{target_state.fiefs[fid]['name']}', then click DONE.")
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
                                badge_rect = pygame.Rect(ax - 42, ay - 25, 84, 24)
                                if sel_rect.colliderect(badge_rect):
                                    state.selected_army_ids.append(a.id)
                        if state.selected_army_ids:
                            state.selected_army_id = state.selected_army_ids[0]
                    box_start = None
                    box_end   = None

            elif event.type == pygame.KEYDOWN:
                is_popup_open = bool(state.vassal_build_requests or state.granting_fief_id or state.inspecting_vassal)
                if is_popup_open:
                    if event.key == pygame.K_ESCAPE:
                        if state.inspecting_vassal:
                            state.inspecting_vassal = None
                        elif state.granting_fief_id:
                            state.granting_fief_id = None
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

        # -------------------------------------------------------------
        # POPUP MODAL AUTO-PAUSE & AUTO-RESUME SYSTEM
        # -------------------------------------------------------------
        is_popup_active = bool(state.vassal_build_requests or state.granting_fief_id or state.inspecting_vassal)
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

        # Portrait & Wessex Shield
        p_img = portrait_cache.get(state.player_id)
        if p_img:
            screen.blit(p_img, (25, 75))
        c_img = coa_cache.get(state.player_id)
        if c_img:
            screen.blit(c_img, (88, 125))

        # Ruler Info
        name_surf = font_md.render(state.player["name"], True, COLOR_TEXT_WHITE)
        title_surf = font_sm.render(state.player["realm"], True, COLOR_GOLD)
        dynasty_surf = font_sm.render(f"Martial Skill: {state.player['stats']['martial']}", True, COLOR_TEXT_RED)
        age_surf = font_sm.render(f"Age: {state.player['age']} • Gold: {state.player['gold']}", True, COLOR_TEXT_MUTED)

        screen.blit(name_surf, (115, 75))
        screen.blit(title_surf, (115, 96))
        screen.blit(dynasty_surf, (115, 116))
        screen.blit(age_surf, (115, 134))

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
        # Left Panel Sub-Tabs: [ ⚔ Active Armies ]  [ 👥 Realm Vassals ]
        #                      [ 👑 Royal Demesne (Crown Fiefs) ]
        # ---------------------------------------------------------
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 233), (285, 233), 1)
        tab_y = 238
        tab_armies = pygame.Rect(25, tab_y, 125, 25)
        tab_vassals = pygame.Rect(158, tab_y, 127, 25)
        tab_demesne = pygame.Rect(25, tab_y + 29, 260, 25)
        
        is_hov_ta = tab_armies.collidepoint(mouse_pos)
        is_hov_tv = tab_vassals.collidepoint(mouse_pos)
        is_hov_td = tab_demesne.collidepoint(mouse_pos)
        
        is_a_active = (state.left_tab == "armies")
        is_v_active = (state.left_tab == "vassals")
        is_d_active = (state.left_tab == "demesne")
        
        # Row 1 Tabs
        pygame.draw.rect(screen, COLOR_BUTTON_ACTIVE if is_a_active else (COLOR_BUTTON_HOVER if is_hov_ta else COLOR_BUTTON_NORMAL), tab_armies, border_radius=4)
        pygame.draw.rect(screen, COLOR_GOLD if is_a_active else COLOR_PANEL_BORDER, tab_armies, 1, border_radius=4)
        screen.blit(font_xs.render("⚔ ACTIVE ARMIES", True, COLOR_TEXT_WHITE if not is_a_active else COLOR_GOLD), (32, tab_y + 5))
        
        pygame.draw.rect(screen, COLOR_BUTTON_ACTIVE if is_v_active else (COLOR_BUTTON_HOVER if is_hov_tv else COLOR_BUTTON_NORMAL), tab_vassals, border_radius=4)
        pygame.draw.rect(screen, COLOR_GOLD if is_v_active else COLOR_PANEL_BORDER, tab_vassals, 1, border_radius=4)
        screen.blit(font_xs.render("👥 REALM VASSALS", True, COLOR_TEXT_WHITE if not is_v_active else COLOR_GOLD), (164, tab_y + 5))

        # Row 2 Tab: Royal Demesne
        player_crown_fiefs = [f for f in state.fiefs.values() if f.get("holder") == state.player["name"]]
        d_title = f"👑 ROYAL DEMESNE ({len(player_crown_fiefs)} Crown Fiefs)"
        pygame.draw.rect(screen, (60, 48, 20) if is_d_active else (COLOR_BUTTON_HOVER if is_hov_td else (35, 40, 52)), tab_demesne, border_radius=4)
        pygame.draw.rect(screen, COLOR_GOLD if is_d_active else (90, 140, 210), tab_demesne, 1, border_radius=4)
        d_lbl = font_xs.render(d_title, True, COLOR_GOLD if is_d_active else (210, 230, 255))
        screen.blit(d_lbl, (tab_demesne.x + (tab_demesne.w - d_lbl.get_width()) // 2, tab_y + 34))

        if mouse_clicked and is_hov_ta:
            state.left_tab = "armies"
        elif mouse_clicked and is_hov_tv:
            state.left_tab = "vassals"
        elif mouse_clicked and is_hov_td:
            state.left_tab = "demesne"

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
                    elif a.is_mustering: status_str = f"⏳ Mustering ({a.muster_days}d)"
                    elif a.is_demobilizing: status_str = f"🏠 Returning to {PROVINCES[a.flag_origin]['name'].split()[0]}"
                    elif a.is_sieging: status_str = f"Besieging {a.siege_target_name or 'Holding'} ({a.siege_progress}%)"
                    elif a.is_moving: status_str = f"Marching to {PROVINCES[a.next_province]['name'].split()[0]}"
                    else: status_str = f"Stationed in {PROVINCES[a.province]['name'].split()[0]}"

                    st_color = COLOR_GOLD if a.in_battle else ((255, 180, 50) if a.is_mustering else ((150, 200, 255) if a.is_demobilizing else COLOR_TEXT_MUTED))
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
            # Royal Demesne View (Personal Crown Fiefs & Cities)
            screen.blit(font_md.render(f"Royal Crown Demesne ({len(player_crown_fiefs)} Fiefs)", True, COLOR_GOLD), (25, 302))
            screen.blit(font_xs.render("King Alfred's Personal Holdings & Cities:", True, COLOR_TEXT_MUTED), (25, 324))

            fy = 345
            for f in player_crown_fiefs[:3]:
                f_rect = pygame.Rect(25, fy, 260, 46)
                is_sel = (f["id"] == state.selected_fief_id)
                b_hover_f = f_rect.collidepoint(mouse_pos)
                
                bg_col = (70, 55, 20) if is_sel else ((50, 60, 78) if b_hover_f else (34, 40, 52))
                pygame.draw.rect(screen, bg_col, f_rect, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if is_sel else (80, 140, 220), f_rect, 1, border_radius=4)

                screen.blit(font_sm.render(f"🏰 {f['name']}", True, COLOR_GOLD), (34, fy + 4))
                p_short = PROVINCES[f['province']]['name'].split()[0]
                status_str = f"Province: {p_short}  •  {len(f['tiles'])} Tiles (+6g/m)"
                screen.blit(font_xs.render(status_str, True, (210, 230, 255)), (34, fy + 24))

                if mouse_clicked and b_hover_f:
                    state.selected_fief_id = f["id"]
                    state.selected_province = f["province"]
                    if f.get("tiles"):
                        state.selected_settlement = f["tiles"][0]
                    state.selected_army_id = None

                fy += 50

            if not player_crown_fiefs:
                screen.blit(font_sm.render("No crown fiefs held directly.", True, COLOR_TEXT_MUTED), (25, 350))
                screen.blit(font_xs.render("Revoke fiefs to expand royal land.", True, COLOR_TEXT_MUTED), (25, 370))

            # Chronicle of Britain
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 505), (285, 505), 1)
            screen.blit(font_md.render("Chronicle of Britain", True, COLOR_GOLD), (25, 515))

            log_y = 545
            for log_msg in state.logs[-6:]:
                disp = log_msg[:34] + "..." if len(log_msg) > 37 else log_msg
                lm_surf = font_sm.render(f"• {disp}", True, COLOR_TEXT_MUTED)
                screen.blit(lm_surf, (25, log_y))
                log_y += 24

        else:
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
            state.vassal_page = max(0, min(state.vassal_page, max_pages - 1))
            
            start_i = state.vassal_page * per_page
            cur_page_vassals = realm_vassals[start_i:start_i + per_page]
            
            vy = 328
            for v_pid, v_data in cur_page_vassals:
                v_card = pygame.Rect(25, vy, 260, 50)
                is_vc_hov = v_card.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (50, 60, 78) if is_vc_hov else (34, 40, 52), v_card, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if is_vc_hov else COLOR_PANEL_BORDER, v_card, 1, border_radius=4)
                
                prov_short = PROVINCES[v_pid]["name"].split()[0]
                screen.blit(font_xs.render(f"👑 {v_data['name']}", True, COLOR_GOLD), (32, vy + 4))
                p_tag = font_xs.render(f"[{prov_short}]", True, (140, 200, 255))
                screen.blit(p_tag, (280 - p_tag.get_width(), vy + 4))
                
                h_name = v_data.get("city_name") or "Landless Noble"
                screen.blit(font_xs.render(f"Fief: {h_name}", True, (210, 220, 235)), (32, vy + 17))
                screen.blit(font_xs.render(f"Gold: {v_data['gold']}g  •  Levy: +{v_data['levy_contribution']}  •  Tax: +{v_data['tax_contribution']}g/m", True, COLOR_TEXT_MUTED), (32, vy + 30))
                
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
        # -----------------------------------------------------------
        fief_palette = [(120, 200, 255), (255, 175, 90), (190, 130, 255), (90, 255, 190), (255, 120, 150), (240, 220, 90)]
        for f_idx, (fid, fdata) in enumerate(state.fiefs.items()):
            f_color = fief_palette[f_idx % len(fief_palette)]
            is_f_sel = (state.selected_fief_id == fid)
            is_f_edit = (state.editing_fief_id == fid)
            is_cur_prov = (fdata.get("province") == state.selected_province)
            f_tiles_set = set(fdata["tiles"])
            
            for (fc, fr) in fdata["tiles"]:
                fx = origin_x + (fc * curr_tile_w)
                fy = origin_y + (fr * curr_tile_h)
                
                # Fief fill tint:
                # - When editing: vivid golden glow
                # - When selected: vibrant green glow
                # - When in selected province: visible distinct color tint so EVERY fief is identifiable at a glance!
                if is_f_edit:
                    f_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                    f_surf.fill((255, 220, 50, 105))
                    screen.blit(f_surf, (fx, fy))
                elif is_f_sel:
                    f_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                    f_surf.fill((100, 255, 120, 85))
                    screen.blit(f_surf, (fx, fy))
                elif is_cur_prov:
                    f_surf = pygame.Surface((curr_tile_w, curr_tile_h), pygame.SRCALPHA)
                    fill_col = (*f_color, 45) if fdata.get("holder") else (235, 195, 100, 45)
                    f_surf.fill(fill_col)
                    screen.blit(f_surf, (fx, fy))
                
                # Draw fief border ONLY on outer boundary edges (no internal seam line between tiles of same fief!)
                # Every fief gets a bold, distinct border: editing = gold (3px), selected = green (2px), regular = distinct palette color (2px)
                edge_col = (255, 225, 60) if is_f_edit else ((100, 255, 120) if is_f_sel else f_color)
                edge_w = 3 if is_f_edit else 2
                
                # Right edge
                if (fc + 1, fr) not in f_tiles_set:
                    pygame.draw.line(screen, edge_col, (fx + curr_tile_w - 1, fy), (fx + curr_tile_w - 1, fy + curr_tile_h - 1), edge_w)
                # Left edge
                if (fc - 1, fr) not in f_tiles_set:
                    pygame.draw.line(screen, edge_col, (fx, fy), (fx, fy + curr_tile_h - 1), edge_w)
                # Bottom edge
                if (fc, fr + 1) not in f_tiles_set:
                    pygame.draw.line(screen, edge_col, (fx, fy + curr_tile_h - 1), (fx + curr_tile_w - 1, fy + curr_tile_h - 1), edge_w)
                # Top edge
                if (fc, fr - 1) not in f_tiles_set:
                    pygame.draw.line(screen, edge_col, (fx, fy), (fx + curr_tile_w - 1, fy), edge_w)

        # -----------------------------------------------------------
        # PASS 2.5: Draw Outer Province Boundaries Framing All Land
        #           (Drawn on top of fiefs so province perimeter is solid & crisp!)
        # -----------------------------------------------------------
        BORDER_COL   = (0, 0, 0)      # black line between provinces
        def get_prov(col_i, row_i):
            """Return province id for tile, or None if ocean."""
            return cell_to_prov.get((col_i, row_i))

        for r, row in enumerate(raw_grid):
            for c, ch in enumerate(row):
                if ch == ".":
                    continue
                cell_x = origin_x + (c * curr_tile_w)
                cell_y = origin_y + (r * curr_tile_h)
                prov_id    = get_prov(c, r)
                is_selected = (prov_id == state.selected_province)
                border_col = COLOR_GOLD if is_selected else BORDER_COL
                border_w = 3 if is_selected else 2

                # Right edge — draw if neighbor is different province (or ocean)
                if get_prov(c + 1, r) != prov_id:
                    ex = cell_x + curr_tile_w - 1
                    pygame.draw.line(screen, border_col,
                                     (ex, cell_y), (ex, cell_y + curr_tile_h - 1), border_w)
                # Bottom edge
                if get_prov(c, r + 1) != prov_id:
                    ey = cell_y + curr_tile_h - 1
                    pygame.draw.line(screen, border_col,
                                     (cell_x, ey), (cell_x + curr_tile_w - 1, ey), border_w)
                # Left edge
                if get_prov(c - 1, r) != prov_id:
                    pygame.draw.line(screen, border_col,
                                     (cell_x, cell_y), (cell_x, cell_y + curr_tile_h - 1), border_w)
                # Top edge
                if get_prov(c, r - 1) != prov_id:
                    pygame.draw.line(screen, border_col,
                                     (cell_x, cell_y), (cell_x + curr_tile_w - 1, cell_y), border_w)

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
                
                # Central Great Keep (stands high and proud in center)
                keep_w = max(6, int(tw * 0.32))
                keep_x = tx + (tw - keep_w) // 2
                pygame.draw.rect(screen, (100, 112, 134), (keep_x, ty, keep_w, th))
                # Central Grand Crown Battlements
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
                # Mid battlements
                pygame.draw.rect(screen, COLOR_GOLD, (tx, ty + up_h, tow_w, 2))
                # Lower Bailey & Gatehouse
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
        # PASS 4: Build Mode Hover & Placement Ghost (Unified Preview)
        # -----------------------------------------------------------
        if state.build_mode and state.selected_province:
            # Determine tile hovered
            mx, my = mouse_pos
            hc = int((mx - origin_x) // curr_tile_w)
            hr = int((my - origin_y) // curr_tile_h)

            target_tiles = []
            if state.build_orientation == "H":
                target_tiles = [(hc, hr), (hc + 1, hr)]
            else:
                target_tiles = [(hc, hr), (hc, hr + 1)]

            # Check validity
            prov_obj = PROVINCES.get(state.selected_province)
            is_valid = True
            if prov_obj["owner"] != state.player_id:
                is_valid = False
            elif state.player["gold"] < 1000:
                is_valid = False
            else:
                for tc, tr in target_tiles:
                    if cell_to_prov.get((tc, tr)) != state.selected_province:
                        is_valid = False
                        break
                    if (tc, tr) in state.settlements:
                        is_valid = False
                        break

            # Draw Ghost Box (Continuous 2-tile preview)
            ghost_col = (50, 220, 80, 140) if is_valid else (220, 50, 50, 140)
            border_c = (80, 255, 110) if is_valid else (255, 80, 80)
            min_gc = min(tc for tc, tr in target_tiles)
            max_gc = max(tc for tc, tr in target_tiles)
            min_gr = min(tr for tc, tr in target_tiles)
            max_gr = max(tr for tc, tr in target_tiles)
            gx = origin_x + (min_gc * curr_tile_w)
            gy = origin_y + (min_gr * curr_tile_h)
            gw = (max_gc - min_gc + 1) * curr_tile_w
            gh = (max_gr - min_gr + 1) * curr_tile_h
            
            # Preview centered ghost
            pad_x = max(5, int(gw * 0.14))
            pad_y = max(3, int(gh * 0.16))
            cw = gw - 2 * pad_x
            ch = gh - 2 * pad_y
            cx = gx + pad_x
            cy = gy + pad_y

            gsurf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            gsurf.fill(ghost_col)
            screen.blit(gsurf, (cx, cy))
            pygame.draw.rect(screen, border_c, (cx, cy, cw, ch), 2, border_radius=3)

            # Left click to place
            if mouse_clicked and is_valid:
                state.player["gold"] -= 1000
                prov_obj["tax"] += 10
                prov_obj["levies_max"] += 500
                prov_obj["levies_current"] += 500
                state.settlement_id_counter += 1
                s_id = f"settlement_{state.settlement_id_counter}"
                for tc, tr in target_tiles:
                    state.settlements[(tc, tr)] = {
                        "id": s_id,
                        "province": state.selected_province,
                        "type": "town",
                        "name": f"{prov_obj['name'].split()[0]} Burgh",
                        "lord": f"{state.player['name']} (Crown Demesne)",
                        "vassal_id": None,
                        "is_crown_demesne": True
                    }
                # Ensure these tiles belong to a Crown Fief if not already claimed
                claimed_f = any((tc, tr) in f.get("tiles", []) for f in state.fiefs.values())
                if not claimed_f:
                    state.fief_id_counter += 1
                    fid = f"fief_{state.fief_id_counter}"
                    p_short = prov_obj['name'].split()[0]
                    state.fiefs[fid] = {
                        "id": fid,
                        "province": state.selected_province,
                        "tiles": list(target_tiles),
                        "name": f"Crown Fief of {p_short}",
                        "holder": state.player["name"],
                        "vassal_id": None,
                        "is_crown_demesne": True
                    }
                state.logs.append(f"Founded Grand City in {prov_obj['name']} (-1000g, +10 Tax, +500 Levies)!")
                state.build_mode = False

        # Province Name Labels
        for pid, (lx, ly) in province_anchors.items():
            p_data = PROVINCES.get(pid)
            if p_data:
                short_name = p_data["name"].split()[0]
                lbl_surf = font_sm.render(short_name, True, (245, 245, 245))
                sh_surf = font_sm.render(short_name, True, (10, 15, 25))
                screen.blit(sh_surf, (lx - lbl_surf.get_width() // 2 + 1, ly + 1))
                screen.blit(lbl_surf, (lx - lbl_surf.get_width() // 2, ly))

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
            if not army.is_moving:
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
            if army.is_moving and army.next_province:
                next_pos = province_anchors.get(army.next_province, base_pos)
                pct = army.move_progress / 100.0
                cx = int(cx + (next_pos[0] - base_pos[0]) * pct)
                cy = int(cy + (next_pos[1] - base_pos[1]) * pct)

            is_player = (army.owner == state.player_id)
            is_sel_army = (army.id == state.selected_army_id or army.id in state.selected_army_ids)

            # RTS Golden Ground Selection Ring
            if is_sel_army:
                sel_surf = pygame.Surface((46, 14), pygame.SRCALPHA)
                pygame.draw.ellipse(sel_surf, (240, 195, 50, 180), (0, 0, 46, 14), 2)
                screen.blit(sel_surf, (cx - 23, cy - 7))

            # -------------------------------------------------------------
            # WAVING BANNER HIERARCHY:
            # 1 Grand Central Standard (Large, Waving)
            # + All Contingent Standards (Small, Waving, Encircling the Grand Banner)
            # -------------------------------------------------------------
            banner_draw_queue = []
            # Grand standard in center (dy = 0)
            banner_draw_queue.append((0, True, army.flag_origin, cx, cy, 0))

            # All secondary contingents encircling the grand standard
            for idx, sf in enumerate(army.sub_flags):
                dx, dy = SUB_FLAG_OFFSETS[idx % len(SUB_FLAG_OFFSETS)]
                mult = 1.0 + (idx // len(SUB_FLAG_OFFSETS)) * 0.25
                cur_dx = int(dx * mult)
                cur_dy = int(dy * mult)
                banner_draw_queue.append((cur_dy, False, sf, cx + cur_dx, cy + cur_dy, (idx + 1) * 750))

            # Sort by depth so background banners render behind foreground banners
            banner_draw_queue.sort(key=lambda b: b[0])

            for dy, is_main, f_id, px, py, t_off in banner_draw_queue:
                if is_main:
                    c_surf = banner_cloth_large.get(f_id, banner_cloth_large.get("wessex"))
                    draw_waving_banner(screen, c_surf, px, py, pole_h=42, ticks=anim_ticks, amp=3.2, freq=0.25, is_main=True)
                else:
                    c_surf = banner_cloth_small.get(f_id, banner_cloth_small.get("wessex"))
                    draw_waving_banner(screen, c_surf, px, py, pole_h=26, ticks=anim_ticks + t_off, amp=2.0, freq=0.30, is_main=False)

            # -------------------------------------------------------------
            # Sleek Troop Count Pill Under Standard Base (No Clunky Red Box)
            # -------------------------------------------------------------
            txt_badge = f"{army.troops:,}"
            if army.in_battle:
                txt_badge = f"⚔ {army.troops:,}"
                p_bg = (185, 35, 35)
                p_border = (255, 220, 50)
            elif army.is_mustering:
                txt_badge = f"⏳ {army.muster_days}d ({army.troops:,})"
                p_bg = (65, 52, 20)
                p_border = COLOR_GOLD
            elif army.is_demobilizing:
                txt_badge = f"🏠 HOME ({army.troops:,})"
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
            pw = max(42, tw + 12)
            ph = 16
            px_pill = cx - pw // 2
            py_pill = cy + 4

            pill_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
            pill_surf.fill((*p_bg, 225))
            pygame.draw.rect(pill_surf, p_border, (0, 0, pw, ph), 2 if is_sel_army else 1, border_radius=4)
            screen.blit(pill_surf, (px_pill, py_pill))
            screen.blit(lbl, (px_pill + (pw - tw) // 2, py_pill + 1))

            # Hitbox covering all banners + pill for natural mouse selection
            all_x = [cx, cx + 34, px_pill, px_pill + pw]
            for idx, sf in enumerate(army.sub_flags):
                dx, dy = SUB_FLAG_OFFSETS[idx % len(SUB_FLAG_OFFSETS)]
                all_x.extend([cx + dx - 2, cx + dx + 20])
            min_x = min(all_x) - 4
            max_x = max(all_x) + 4
            hit_rect = pygame.Rect(min_x, cy - 48, max_x - min_x, (py_pill + ph + 4) - (cy - 48))

            is_badge_hover = hit_rect.collidepoint(mouse_pos)

            # Click banner or count pill to select army
            if mouse_clicked and is_badge_hover:
                state.selected_army_id = army.id
                state.selected_province = army.province

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

        # If a city is specifically selected, display City Holding Inspector Card!
        if state.selected_settlement and state.selected_settlement in state.settlements:
            s_coord = state.selected_settlement
            s_data = state.settlements[s_coord]
            p_parent = PROVINCES.get(s_data["province"])
            
            c_head = font_lg.render(s_data["name"], True, COLOR_GOLD)
            screen.blit(c_head, (880, 80))
            sub_c = font_sm.render(f"Holding Type: Fortified Town ({s_data['province'].title()})", True, COLOR_TEXT_WHITE)
            screen.blit(sub_c, (880, 110))
            
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 135), (1170, 135), 1)
            screen.blit(font_md.render("Holding Overview", True, COLOR_GOLD), (880, 145))
            h_matching_tiles = [coord for coord, s in state.settlements.items() if s.get("name") == s_data["name"] and s.get("province") == s_data["province"]]
            t_loc_str = ", ".join(f"({c},{r})" for c, r in h_matching_tiles)
            screen.blit(font_sm.render(f"Location: {t_loc_str} ({len(h_matching_tiles)} Tiles)", True, COLOR_TEXT_MUTED), (880, 175))
            screen.blit(font_sm.render(f"Ruling Lord: {s_data.get('lord', 'Crown Fief')}", True, COLOR_GOLD), (880, 200))
            screen.blit(font_sm.render("Fortification Level: II (Stone Walls)", True, COLOR_TEXT_WHITE), (880, 225))
            screen.blit(font_sm.render("Economic Income: +6 Gold / month", True, COLOR_TEXT_GREEN), (880, 250))
            screen.blit(font_sm.render("Local Garrison: 300 Defenders", True, COLOR_TEXT_WHITE), (880, 275))
            
            if s_data.get("vassal_id"):
                v_btn = pygame.Rect(880, 310, 290, 34)
                b_v_hov = v_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (40, 75, 110) if b_v_hov else (30, 55, 85), v_btn, border_radius=6)
                pygame.draw.rect(screen, (100, 180, 255), v_btn, 1, border_radius=6)
                screen.blit(font_xs.render("👑 VIEW VASSAL PROFILE & DOSSIER", True, COLOR_TEXT_WHITE), (915, 318))
                if mouse_clicked and b_v_hov:
                    v_list = state.vassals.get(s_data["province"], [])
                    matching_v = next((v for v in v_list if v.get("id") == s_data["vassal_id"] or v.get("name") == s_data["lord"]), None)
                    if matching_v:
                        state.inspecting_vassal = {"province": s_data["province"], "vassal": matching_v}
                        state.logs.append(f"Opened royal dossier for vassal {matching_v['name']}.")
                cls_y = 352
            else:
                cls_y = 315

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
            elif sel_army.is_mustering:
                screen.blit(font_md.render(f"STATUS: ⏳ MUSTERING ({sel_army.muster_days}d left)", True, COLOR_GOLD), (880, 202))
            elif sel_army.is_demobilizing:
                home_p = PROVINCES[sel_army.flag_origin]["name"].split()[0]
                screen.blit(font_md.render(f"STATUS: 🏠 Returning Home to {home_p}", True, (140, 200, 255)), (880, 202))
            elif sel_army.is_sieging:
                t_lbl = sel_army.siege_target_name or 'Holding'
                screen.blit(font_md.render(f"STATUS: 🏰 Besieging {t_lbl} ({sel_army.siege_progress}%)", True, COLOR_GOLD), (880, 202))
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

            # Disband / Cancel Muster / Cancel Return Button
            if sel_army.is_mustering:
                dis_btn = pygame.Rect(880, 435, 290, 40)
                b_d_hover = dis_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (90, 40, 40) if b_d_hover else (70, 30, 30), dis_btn, border_radius=6)
                pygame.draw.rect(screen, (240, 90, 90), dis_btn, 1, border_radius=6)
                screen.blit(font_md.render("CANCEL MUSTER (Refund Men)", True, (255, 220, 220)), (915, 444))
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
                # Owner Info
                owner_p = portrait_cache.get(sel_prov["owner"])
                if owner_p:
                    mini_p = pygame.transform.smoothscale(owner_p, (46, 46))
                    screen.blit(mini_p, (880, 162))
                owner_c = coa_cache.get(sel_prov["owner"])
                if owner_c:
                    screen.blit(owner_c, (932, 162))

                screen.blit(font_md.render(owner_char["name"], True, COLOR_GOLD if is_player_owned else COLOR_TEXT_RED), (975, 162))
                screen.blit(font_xs.render(owner_char["title"], True, COLOR_TEXT_WHITE), (975, 185))

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
                # List all cities in this province
                prov_cities = {}
                for coord, sdata in state.settlements.items():
                    if sdata["province"] == state.selected_province:
                        c_name = sdata["name"]
                        if c_name not in prov_cities:
                            prov_cities[c_name] = {"lord": sdata.get("lord", "None"), "tile": coord}

                cy = 190
                for c_name, c_info in list(prov_cities.items())[:7]:
                    c_box = pygame.Rect(880, cy, 290, 42)
                    is_c_hov = c_box.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (45, 52, 68) if is_c_hov else (32, 38, 50), c_box, border_radius=4)
                    pygame.draw.rect(screen, COLOR_PANEL_BORDER, c_box, 1, border_radius=4)
                    screen.blit(font_xs.render(f"🏰 {c_name}", True, COLOR_GOLD), (888, cy + 5))
                    screen.blit(font_xs.render(f"Lord: {c_info['lord']}  •  +6 Gold/m", True, COLOR_TEXT_MUTED), (888, cy + 22))
                    if mouse_clicked and is_c_hov:
                        state.selected_settlement = c_info["tile"]
                    cy += 48

                if is_player_owned:
                    # Found New City Button
                    pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, cy + 10), (1170, cy + 10), 1)
                    bld_btn = pygame.Rect(880, cy + 25, 290, 42)
                    b_bld_hov = bld_btn.collidepoint(mouse_pos)
                    b_bld_active = state.build_mode
                    pygame.draw.rect(screen, (150, 75, 15) if b_bld_active else ((75, 45, 15) if b_bld_hov else (55, 32, 10)), bld_btn, border_radius=6)
                    pygame.draw.rect(screen, COLOR_GOLD if b_bld_active else (210, 150, 40), bld_btn, 2 if b_bld_active else 1, border_radius=6)
                    b_lbl = "CANCEL PLACEMENT (ESC)" if b_bld_active else "FOUND NEW CITY (2 TILES - 1,000g)"
                    screen.blit(font_xs.render(b_lbl, True, COLOR_GOLD if b_bld_active else COLOR_TEXT_WHITE), (895, cy + 38))
                    if mouse_clicked and b_bld_hov:
                        state.build_mode = not state.build_mode

                    if state.build_mode:
                        hint1 = font_xs.render("• Hover 2 adjacent tiles inside this province.", True, COLOR_TEXT_WHITE)
                        hint2 = font_xs.render("• Press 'T' to rotate orientation (Horiz / Vert).", True, COLOR_GOLD)
                        hint3 = font_xs.render("• Click to establish new city holding.", True, COLOR_TEXT_GREEN)
                        screen.blit(hint1, (880, cy + 75))
                        screen.blit(hint2, (880, cy + 93))
                        screen.blit(hint3, (880, cy + 111))

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

                    screen.blit(font_xs.render(f"👑 {v['name']}", True, COLOR_GOLD if is_v_sel else COLOR_TEXT_WHITE), (888, vy + 4))
                    c_info = v.get('city_name') or 'No Assigned Holding'
                    screen.blit(font_xs.render(f"Fief: {c_info}", True, (200, 230, 255)), (888, vy + 17))
                    screen.blit(font_xs.render(f"Gold: {v['gold']}g  •  Levies: +{v['levy_contribution']}  •  Tax: +{v['tax_contribution']}g/m", True, COLOR_TEXT_MUTED), (888, vy + 29))

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
                screen.blit(font_md.render(f"Provincial Fiefs & Baronies ({total_fiefs})", True, COLOR_GOLD), (880, 155))

                # Header action: Edit banner or Carve New Fief button
                if state.editing_fief_id:
                    edit_f = state.fiefs.get(state.editing_fief_id)
                    f_name = edit_f["name"] if edit_f else "Fief"
                    num_tiles = len(edit_f.get("tiles", [])) if edit_f else 0
                    eb_rect = pygame.Rect(880, 180, 290, 46)
                    pygame.draw.rect(screen, (70, 50, 15), eb_rect, border_radius=4)
                    pygame.draw.rect(screen, COLOR_GOLD, eb_rect, 2, border_radius=4)
                    screen.blit(font_xs.render(f"🖌 CARVING: {f_name} ({num_tiles} tiles)", True, COLOR_GOLD), (886, 184))
                    screen.blit(font_xs.render("Click green tiles on map (Min 2)", True, (240, 240, 240)), (886, 202))
                    
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
                        if edit_f and len(edit_f.get("tiles", [])) < 2:
                            if len(edit_f.get("tiles", [])) == 0:
                                del state.fiefs[state.editing_fief_id]
                                state.editing_fief_id = None
                                state.logs.append(f"Cancelled carving {f_name}: No tiles were selected.")
                            else:
                                state.logs.append(f"Fief requires at least 2 tiles (currently has {len(edit_f['tiles'])}). Click more green tiles or click CANCEL.")
                        else:
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

                # Pagination setup (5 fiefs per page, or 4 when editing)
                per_page = 5 if not state.editing_fief_id else 4
                total_pages = max(1, (total_fiefs + per_page - 1) // per_page)
                state.fief_page = max(0, min(getattr(state, "fief_page", 0), total_pages - 1))

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

                    is_crown_owned = (f_data["holder"] is None or f_data["holder"] == state.player["name"] or f_data.get("is_crown_demesne"))
                    
                    if f_data["holder"] == state.player["name"] or f_data.get("is_crown_demesne"):
                        holder_str = f"Lord: {state.player['name']} (Crown Demesne)"
                        h_col = COLOR_GOLD
                    elif f_data["holder"] is None:
                        holder_str = "Status: UNASSIGNED CROWN FIEF"
                        h_col = (255, 180, 80)
                    else:
                        holder_str = f"Lord: {f_data['holder']}"
                        h_col = (180, 255, 180)

                    screen.blit(font_xs.render(f"🛡 {f_data['name']} ({len(f_data['tiles'])} Tiles)", True, COLOR_GOLD), (888, fy + 4))
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
                    screen.blit(font_xs.render("EDIT 🖌" if not is_f_editing else "STOP ✕", True, COLOR_GOLD), (902, fy + 38))
                    if mouse_clicked and e_hov:
                        state.editing_fief_id = None if is_f_editing else f_data["id"]
                        state.selected_fief_id = f_data["id"]
                        if state.editing_fief_id:
                            state.selected_settlement = None

                    # 2. Grant / Revoke Buttons
                    if is_crown_owned:
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
                            del state.fiefs[f_data["id"]]
                            if state.selected_fief_id == f_data["id"]:
                                state.selected_fief_id = None
                            if state.editing_fief_id == f_data["id"]:
                                state.editing_fief_id = None
                            state.logs.append(f"Dissolved {f_data['name']}. Land returned to province.")
                            break
                    else:
                        # Revoke Fief Button (Transfers vassal ownership to Crown Demesne)
                        b_revoke = pygame.Rect(970, fy + 36, 194, 20)
                        r_hov = b_revoke.collidepoint(mouse_pos)
                        pygame.draw.rect(screen, (100, 45, 45) if r_hov else (70, 30, 30), b_revoke, border_radius=3)
                        pygame.draw.rect(screen, (240, 100, 100), b_revoke, 1, border_radius=3)
                        screen.blit(font_xs.render("REVOKE FIEF (👑 Return to Crown)", True, COLOR_TEXT_WHITE), (980, fy + 38))
                        if mouse_clicked and r_hov:
                            v_prev = f_data["holder"]
                            v_prev_id = f_data.get("vassal_id")
                            f_data["holder"] = state.player["name"]
                            f_data["vassal_id"] = None
                            f_data["is_crown_demesne"] = True
                            p_short = PROVINCES[f_data['province']]['name'].split()[0]
                            f_data["name"] = f"Crown Fief of {p_short}"

                            # 1. Transfer all settlements on this fief directly to the King (Crown Demesne)
                            for t in f_data["tiles"]:
                                if t in state.settlements:
                                    state.settlements[t]["lord"] = f"{state.player['name']} (Crown Demesne)"
                                    state.settlements[t]["vassal_id"] = None
                                    state.settlements[t]["is_crown_demesne"] = True
                                    state.settlements[t]["is_crown_fief"] = True

                            # 2. Update former vassal's held tiles
                            for pid, v_list in state.vassals.items():
                                for v in v_list:
                                    if v["name"] == v_prev or v["id"] == v_prev_id:
                                        v["tiles"] = [t for t in v.get("tiles", []) if t not in f_data["tiles"]]
                                        if not v["tiles"]:
                                            v["city_name"] = None

                            state.logs.append(f"Revoked {f_data['name']} from {v_prev}! Transferred to Crown Demesne (King Alfred).")

                    if mouse_clicked and is_f_hov and not (e_hov or g_hov or d_hov or r_hov):
                        state.selected_fief_id = f_data["id"]

                    fy += 68

                # Pagination Controls for Fiefs list
                if total_pages > 1:
                    py_bar = 700
                    prev_btn = pygame.Rect(880, py_bar, 80, 26)
                    next_btn = pygame.Rect(1090, py_bar, 80, 26)
                    p_hov = prev_btn.collidepoint(mouse_pos)
                    n_hov = next_btn.collidepoint(mouse_pos)

                    pygame.draw.rect(screen, COLOR_BUTTON_HOVER if p_hov else COLOR_BUTTON_NORMAL, prev_btn, border_radius=4)
                    pygame.draw.rect(screen, COLOR_PANEL_BORDER, prev_btn, 1, border_radius=4)
                    screen.blit(font_xs.render("◄ PREV", True, COLOR_TEXT_WHITE if state.fief_page > 0 else COLOR_TEXT_MUTED), (898, py_bar + 5))

                    pygame.draw.rect(screen, COLOR_BUTTON_HOVER if n_hov else COLOR_BUTTON_NORMAL, next_btn, border_radius=4)
                    pygame.draw.rect(screen, COLOR_PANEL_BORDER, next_btn, 1, border_radius=4)
                    screen.blit(font_xs.render("NEXT ►", True, COLOR_TEXT_WHITE if state.fief_page < total_pages - 1 else COLOR_TEXT_MUTED), (1108, py_bar + 5))

                    pg_lbl = font_xs.render(f"Page {state.fief_page + 1}/{total_pages} ({total_fiefs} Fiefs)", True, COLOR_TEXT_MUTED)
                    screen.blit(pg_lbl, (965 + (120 - pg_lbl.get_width()) // 2, py_bar + 5))

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

            t1 = font_sm.render(f"My Liege, {req['vassal']} humbly requests your royal charter", True, COLOR_TEXT_WHITE)
            t2 = font_sm.render(f"to construct a fortified market town inside {fief_label}.", True, COLOR_TEXT_WHITE)
            t3 = font_xs.render("• Granting Charter: Vassal pays 1,000g, +5 Province Tax, +250 Levies.", True, COLOR_TEXT_GREEN)
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
                    p_obj["tax"] += 5
                    p_obj["levies_max"] += 250
                    p_obj["levies_current"] += 250
                    req["vassal_ref"]["gold"] = max(0, req["vassal_ref"]["gold"] - 1000)
                    
                    # Construct town strictly on free tiles within this vassal's owned fief!
                    b_tiles = req.get("build_tiles", [])
                    city_title = f"{req['vassal'].split()[1]}'s {random.choice(['Borough', 'Castle', 'Burgh', 'Keep'])}"
                    state.settlement_id_counter += 1
                    s_id = f"settlement_{state.settlement_id_counter}"
                    for t in b_tiles:
                        state.settlements[t] = {
                            "id": s_id,
                            "province": pid,
                            "type": "town",
                            "name": city_title,
                            "lord": req["vassal"],
                            "vassal_id": req["vassal_ref"]["id"],
                            "is_crown_demesne": False
                        }
                        if "tiles" not in req["vassal_ref"]:
                            req["vassal_ref"]["tiles"] = []
                        if t not in req["vassal_ref"]["tiles"]:
                            req["vassal_ref"]["tiles"].append(t)
                    
                    if not req["vassal_ref"].get("city_name"):
                        req["vassal_ref"]["city_name"] = city_title

                    state.logs.append(f"Granted charter! {req['vassal']} established {city_title} inside {fief_label}.")
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
                    v_title_str = f"👑 {c_v['name']}"
                    screen.blit(font_md.render(v_title_str, True, COLOR_GOLD), (pop_x + 40, vy + 10))
                    
                    # Locality & holdings
                    loc_str = f"Home: {PROVINCES[c_pid]['name'].split()[0]}" + (" (Local Vassal)" if is_loc else " (Realm Lord)")
                    n_held_fiefs = sum(1 for f in state.fiefs.values() if f.get("holder") == c_v["name"])
                    status_str = f"{loc_str}  •  Holds {n_held_fiefs} Fief(s)"
                    screen.blit(font_xs.render(status_str, True, (150, 210, 255) if is_loc else COLOR_TEXT_MUTED), (pop_x + 40, vy + 34))

                    econ_str = f"Treasury: {c_v.get('gold', 150)}g  •  Levy Support: +{c_v.get('levy_contribution', 120)} soldiers"
                    screen.blit(font_xs.render(econ_str, True, COLOR_TEXT_GREEN), (pop_x + 40, vy + 56))

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
                        f_target["name"] = f"Barony of {c_v['name'].split()[1]}"

                        # Update all city settlements located on this fief to the chosen vassal!
                        for t in f_target["tiles"]:
                            if t in state.settlements:
                                state.settlements[t]["lord"] = c_v["name"]
                                state.settlements[t]["vassal_id"] = c_v["id"]
                                state.settlements[t]["is_crown_fief"] = False
                        
                        # Update Vassal details
                        if "tiles" not in c_v:
                            c_v["tiles"] = []
                        for t in f_target["tiles"]:
                            if t not in c_v["tiles"]:
                                c_v["tiles"].append(t)
                        c_v["gold"] = c_v.get("gold", 150) + 100
                        
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

            # Header Title
            screen.blit(font_lg.render("FEUDAL VASSAL DOSSIER", True, COLOR_GOLD), (pop_x + 25, pop_y + 16))
            p_full = PROVINCES.get(v_pid, {}).get("name", "Wessex")
            screen.blit(font_xs.render(f"Feudal Subject of King Alfred • Province of {p_full}", True, COLOR_TEXT_MUTED), (pop_x + 25, pop_y + 44))
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 25, pop_y + 64), (pop_x + pop_w - 25, pop_y + 64), 1)

            # Top Character Banner Section
            # Crest / Heraldic Flag
            emblem = prov_flag_cache.get(v_pid)
            if emblem:
                screen.blit(pygame.transform.smoothscale(emblem, (44, 50)), (pop_x + 30, pop_y + 74))
            else:
                pygame.draw.rect(screen, (50, 60, 80), (pop_x + 30, pop_y + 74, 44, 50), border_radius=4)

            # Name and Titles
            screen.blit(font_md.render(f"👑 {v_obj['name']}", True, COLOR_GOLD), (pop_x + 90, pop_y + 74))
            rank_str = f"Feudal Rank: {v_obj.get('title', 'Thane')} of {p_full.split()[0]}  •  Religion: Catholic"
            screen.blit(font_xs.render(rank_str, True, COLOR_TEXT_WHITE), (pop_x + 90, pop_y + 98))
            seat_str = f"Seat of Power: {v_obj.get('city_name') or 'Landless Subject (Awaiting Royal Charter)'}"
            screen.blit(font_xs.render(seat_str, True, (140, 205, 255)), (pop_x + 90, pop_y + 114))

            # Feudal Attributes Grid (Martial, Stewardship, Diplomacy, Feudal Oath)
            stats_list = [
                ("⚔ Martial", f"{10 + (v_obj['levy_contribution'] // 30)}", "(Commands Fyrd)"),
                ("💰 Stewardship", f"{11 + (v_obj['tax_contribution'] * 2)}", "(Manages Estates)"),
                ("🤝 Diplomacy", "13", "(Royal Harmony)"),
                ("🛡 Feudal Oath", "100%", "(Faithful Subject)")
            ]
            for s_i, (s_name, s_val, s_sub) in enumerate(stats_list):
                bx = pop_x + 25 + s_i * 158
                by = pop_y + 138
                b_rect = pygame.Rect(bx, by, 150, 44)
                pygame.draw.rect(screen, (34, 40, 54), b_rect, border_radius=4)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, b_rect, 1, border_radius=4)
                screen.blit(font_xs.render(s_name, True, COLOR_TEXT_MUTED), (bx + 8, by + 4))
                screen.blit(font_md.render(s_val, True, COLOR_GOLD), (bx + 8, by + 18))
                screen.blit(font_xs.render(s_sub, True, (120, 160, 200)), (bx + 48, by + 22))

            # Compute vassal's overall fiefdoms and holdings
            held_fiefs = [f for f in state.fiefs.values() if f.get("holder") == v_obj["name"] or f.get("vassal_id") == v_obj.get("id")]
            total_held_tiles = sum(len(f.get("tiles", [])) for f in held_fiefs)

            # Two Main Columns: Economy & Treasury (Left), Military & Fiefs (Right)
            col_w = 305
            col_y = pop_y + 194

            # LEFT COLUMN: ECONOMY & INCOME ("income etc seluruhnya")
            left_rect = pygame.Rect(pop_x + 25, col_y, col_w, 245)
            pygame.draw.rect(screen, (30, 36, 48), left_rect, border_radius=6)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, left_rect, 1, border_radius=6)
            
            screen.blit(font_md.render("💰 Vassal Finances & Revenue", True, COLOR_GOLD), (pop_x + 35, col_y + 10))
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (pop_x + 35, col_y + 32), (pop_x + 35 + col_w - 20, col_y + 32), 1)

            screen.blit(font_sm.render(f"Treasury: {v_obj['gold']} Gold", True, COLOR_GOLD), (pop_x + 40, col_y + 40))
            
            # Breakdown of monthly finances
            tax_paid = v_obj.get("tax_contribution", 4)
            monthly_gross = tax_paid + 24
            net_profit = 24
            
            screen.blit(font_xs.render(f"• Gross Domain Income: +{monthly_gross}g / month", True, (160, 220, 180)), (pop_x + 40, col_y + 68))
            screen.blit(font_xs.render("  (From tenant rents, tolls & agricultural yield)", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 84))
            screen.blit(font_xs.render(f"• Feudal Royal Tax to Liege: -{tax_paid}g / month", True, COLOR_TEXT_RED), (pop_x + 40, col_y + 104))
            screen.blit(font_xs.render("  (Directly enriches King Alfred's treasury)", True, COLOR_TEXT_MUTED), (pop_x + 40, col_y + 120))
            screen.blit(font_xs.render(f"• Net Monthly Savings: +{net_profit}g / month", True, COLOR_TEXT_GREEN), (pop_x + 40, col_y + 140))
            
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

            screen.blit(font_sm.render(f"Fyrd Levies: +{v_obj['levy_contribution']} Soldiers", True, COLOR_TEXT_GREEN), (pop_x + 365, col_y + 40))
            screen.blit(font_xs.render(f"• Household Guards / Garrison: {v_obj['levy_contribution'] * 2} Men", True, COLOR_TEXT_WHITE), (pop_x + 365, col_y + 68))
            screen.blit(font_xs.render(f"• Feudal Service: Ready to march on King's call", True, COLOR_TEXT_MUTED), (pop_x + 365, col_y + 86))
            screen.blit(font_xs.render(f"• Fiefdoms Controlled: {len(held_fiefs)} Fief(s) ({total_held_tiles} Tiles)", True, (150, 215, 255)), (pop_x + 365, col_y + 110))
            
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
            screen.blit(font_sm.render("🔍 LOCATE SEAT ON MAP", True, COLOR_TEXT_WHITE), (pop_x + 95, pop_y + pop_h - 50))
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

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_game()
