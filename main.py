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

# Load Data
with open(os.path.join(DATA_DIR, "characters.json"), "r", encoding="utf-8") as f:
    CHARACTERS = json.load(f)

with open(os.path.join(DATA_DIR, "provinces.json"), "r", encoding="utf-8") as f:
    PROVINCES = json.load(f)

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

    @property
    def is_moving(self):
        return len(self.path) > 0

    @property
    def next_province(self):
        return self.path[0] if self.path else None

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
        self.armies.append(new_army)
        
        prov["levies_current"] = 0
        self.selected_army_id = army_id
        self.logs.append(f"Raised {available:,} men in {prov['name']}!")

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
                self.armies.append(new_army)
                prov["levies_current"] = 0
                raised_count += 1
                total_men += available
        
        if raised_count > 0:
            self.logs.append(f"Mobilized all realm levies: {total_men:,} men in {raised_count} hosts!")
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
        armies_here = [a for a in self.armies if a.province == province_id and a.owner == owner_id and not a.is_moving]
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
        prov = PROVINCES.get(army.province)
        if prov and prov["owner"] == army.owner:
            # Return surviving men to province
            prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + army.troops)
            self.logs.append(f"Disbanded {army.name}. {army.troops:,} men returned home.")
            if army.id == self.selected_army_id:
                self.selected_army_id = None
            self.armies.remove(army)
        else:
            self.logs.append("Cannot disband an army while inside enemy territory!")

    def order_army_march(self, army, target_province_id):
        if not army:
            return
        if army.in_battle:
            self.logs.append(f"{army.name} is locked in combat and cannot retreat!")
            return
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

        # Vassal autonomous build request chance: ONLY IF Vassal has at least 1,000 Gold!
        if not self.vassal_build_requests:
            player_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.player_id]
            if player_provs and random.random() < 0.35:
                target_pid = random.choice(player_provs)
                v_list = self.vassals.get(target_pid, [])
                wealthy_vassals = [v for v in v_list if v.get("gold", 0) >= 1000]
                if wealthy_vassals:
                    v_requester = random.choice(wealthy_vassals)
                    self.vassal_build_requests.append({
                        "vassal": v_requester["name"],
                        "vassal_ref": v_requester,
                        "province_id": target_pid,
                        "province_name": PROVINCES[target_pid]["name"],
                        "cost": 1000
                    })
                    self.logs.append(f"Charter Petition: {v_requester['name']} has accumulated 1,000g and requests royal charter to build a new borough in {PROVINCES[target_pid]['name']}!")

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
                        # Stop marching — battle logic picks it up next tick
                        a.path = []
                        a.move_progress = 0.0

                    # If reached final destination with no blocker, auto-merge
                    elif not a.path:
                        self.merge_armies_in_province(a.province, a.owner)

        # 2. Check Battles (Opposing armies in same province)
        for pid in list(PROVINCES.keys()):
            # Merge both sides first, THEN get fresh references
            self.merge_armies_in_province(pid, self.player_id)
            self.merge_armies_in_province(pid, self.enemy_id)

            p1_list = [a for a in self.armies if a.province == pid and a.owner == self.player_id and not a.is_moving]
            p2_list = [a for a in self.armies if a.province == pid and a.owner == self.enemy_id and not a.is_moving]

            if not (p1_list and p2_list):
                # No clash – make sure in_battle is cleared for any lone survivors
                for a in p1_list + p2_list:
                    a.in_battle = False
                continue

            a1 = p1_list[0]
            a2 = p2_list[0]
            a1.in_battle = True
            a2.in_battle  = True
            a1.is_sieging = False
            a2.is_sieging = False

            # One combat round per game-tick
            alfred_martial  = self.player["stats"]["martial"]
            halfdan_martial = self.enemy["stats"]["martial"]

            dmg_to_a2 = max(1, int(a1.troops * 0.08 * (1 + alfred_martial * 0.02))  + random.randint(10, 50))
            dmg_to_a1 = max(1, int(a2.troops * 0.08 * (1 + halfdan_martial * 0.02)) + random.randint(10, 50))

            a1.troops = max(0, a1.troops - dmg_to_a1)
            a2.troops = max(0, a2.troops - dmg_to_a2)

            if a1.troops <= 0 and a2.troops <= 0:
                # Mutual annihilation
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
            # else: both alive → battle continues next tick (in_battle stays True, blocks movement)

        # 3. Check Sieges (Army in enemy province with no defending army)
        for a in list(self.armies):
            if a not in self.armies:
                continue
            prov = PROVINCES[a.province]
            if prov["owner"] != a.owner and not a.is_moving and not a.in_battle:
                # Check if there is an opposing army defending
                defenders = [enemy for enemy in self.armies if enemy.province == a.province and enemy.owner != a.owner]
                if not defenders:
                    a.is_sieging = True
                    # Siege progress speed based on troop size
                    rate = max(4, int(a.troops / 250))
                    a.siege_progress += rate
                    
                    if a.siege_progress >= 100:
                        # Province conquered!
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

    # ---------------------------------------------------------
    # AI (Halfdan Ragnarsson)
    # ---------------------------------------------------------
    def ai_routine(self):
        danelaw_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.enemy_id]
        if not danelaw_provs:
            return

        danelaw_armies = [a for a in self.armies if a.owner == self.enemy_id]
        
        # 1. Raise Levies if none active
        if not danelaw_armies:
            for pid in danelaw_provs:
                p = PROVINCES[pid]
                if p["levies_current"] > 500:
                    army_id = f"army_{self.army_id_counter}"
                    self.army_id_counter += 1
                    host = Army(army_id, self.enemy_id, pid, p["levies_current"], "Viking Warband")
                    self.armies.append(host)
                    p["levies_current"] = 0
            self.logs.append("Ravens squawk! The Danelaw has summoned their Viking hosts!")
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

    state = GameState()

    # Map Rendering Setup
    raw_grid = MAP_DATA["raw_grid"]
    map_origin_x = 320
    map_origin_y = 65
    tile_w = 26
    tile_h = 24

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

    # Compute TRUE province centroids from tile grid (guaranteed on land)
    prov_tile_sum = {}   # pid -> [sum_x, sum_y, count]
    for (c, r), pid in cell_to_prov.items():
        cx = map_origin_x + c * tile_w + tile_w // 2
        cy = map_origin_y + 45 + r * tile_h + tile_h // 2
        if pid not in prov_tile_sum:
            prov_tile_sum[pid] = [0, 0, 0]
        prov_tile_sum[pid][0] += cx
        prov_tile_sum[pid][1] += cy
        prov_tile_sum[pid][2] += 1

    province_anchors = {}
    for pid, (sx, sy, count) in prov_tile_sum.items():
        province_anchors[pid] = (sx // count, sy // count)

    # Initialize 1:1 STARTER FIEFS AND CITIES FOR EVERY VASSAL IN THE PROVINCE!
    prov_tile_list = {}
    for (c, r), pid in cell_to_prov.items():
        prov_tile_list.setdefault(pid, []).append((c, r))

    def setup_province_starter_cities(target_state):
        target_state.settlements = {}
        target_state.fiefs = {}
        fief_counter = 1
        
        for pid, tiles in prov_tile_list.items():
            v_list = target_state.vassals.get(pid, [])
            tile_set = set(tiles)
            pname = PROVINCES[pid]["name"].split()[0]
            used_tiles = set()
            
            # Step 1: Assign each vassal their starter 2-tile Fief and City
            for idx, v in enumerate(v_list):
                city_name = f"{v['name'].split()[1]}'s {random.choice(['Keep', 'Burgh', 'Castle', 'Borough'])}"
                placed_pair = None
                # Scan for free horizontal pair
                for (c, r) in tiles:
                    if (c, r) not in used_tiles and (c + 1, r) in tile_set and (c + 1, r) not in used_tiles:
                        placed_pair = [(c, r), (c + 1, r)]
                        break
                # Scan for free vertical pair if horizontal not found
                if not placed_pair:
                    for (c, r) in tiles:
                        if (c, r) not in used_tiles and (c, r + 1) in tile_set and (c, r + 1) not in used_tiles:
                            placed_pair = [(c, r), (c, r + 1)]
                            break
                
                if placed_pair:
                    for t in placed_pair:
                        used_tiles.add(t)
                        target_state.settlements[t] = {"province": pid, "type": "town", "name": city_name, "lord": v["name"], "vassal_id": v["id"]}
                    v["city_name"] = city_name
                    v["tiles"] = placed_pair
                    # Register Fief
                    fid = f"fief_{fief_counter}"
                    fief_counter += 1
                    target_state.fiefs[fid] = {
                        "id": fid,
                        "province": pid,
                        "tiles": placed_pair,
                        "name": f"Barony of {v['name'].split()[1]}",
                        "holder": v["name"],
                        "vassal_id": v["id"]
                    }
                else:
                    # Single tile fallback
                    for (c, r) in tiles:
                        if (c, r) not in used_tiles:
                            used_tiles.add((c, r))
                            target_state.settlements[(c, r)] = {"province": pid, "type": "town", "name": city_name, "lord": v["name"], "vassal_id": v["id"]}
                            v["city_name"] = city_name
                            v["tiles"] = [(c, r)]
                            fid = f"fief_{fief_counter}"
                            fief_counter += 1
                            target_state.fiefs[fid] = {
                                "id": fid,
                                "province": pid,
                                "tiles": [(c, r)],
                                "name": f"Barony of {v['name'].split()[1]}",
                                "holder": v["name"],
                                "vassal_id": v["id"]
                            }
                            break
            
            # Step 2: Group any remaining tiles into UNCLAIMED FIEFS (2 tiles min each)!
            remaining_tiles = [t for t in tiles if t not in used_tiles]
            rem_set = set(remaining_tiles)
            f_unclaimed_idx = 1
            for (c, r) in remaining_tiles:
                if (c, r) in used_tiles:
                    continue
                pair = None
                if (c + 1, r) in rem_set and (c + 1, r) not in used_tiles:
                    pair = [(c, r), (c + 1, r)]
                elif (c, r + 1) in rem_set and (c, r + 1) not in used_tiles:
                    pair = [(c, r), (c, r + 1)]
                
                if pair:
                    for t in pair:
                        used_tiles.add(t)
                    fid = f"fief_{fief_counter}"
                    fief_counter += 1
                    target_state.fiefs[fid] = {
                        "id": fid,
                        "province": pid,
                        "tiles": pair,
                        "name": f"{pname} Fief #{f_unclaimed_idx}",
                        "holder": None,  # UNASSIGNED / EMPTY FIEF READY TO BE GRANTED!
                        "vassal_id": None
                    }
                    f_unclaimed_idx += 1

    # Setup starter cities and fiefs matching each vassal exactly
    setup_province_starter_cities(state)

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

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
                    box_start = event.pos
                    box_end   = event.pos
                elif event.button == 3:
                    right_clicked = True

            elif event.type == pygame.MOUSEMOTION:
                if box_start:
                    box_end = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
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
                col_idx = (mx - map_origin_x) // tile_w
                row_idx = (my - (map_origin_y + 45)) // tile_h
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

        # Active Armies Roster
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 235), (285, 235), 1)
        screen.blit(font_md.render("Active Saxon Armies", True, COLOR_GOLD), (25, 245))

        player_armies = [a for a in state.armies if a.owner == state.player_id]
        if not player_armies:
            screen.blit(font_sm.render("No armies raised yet.", True, COLOR_TEXT_MUTED), (25, 275))
            screen.blit(font_sm.render("Click 'RAISE ALL' or select", True, COLOR_TEXT_MUTED), (25, 295))
            screen.blit(font_sm.render("a province to raise local fyrd.", True, COLOR_TEXT_MUTED), (25, 315))
        else:
            ay = 275
            for a in player_armies[:4]:
                a_rect = pygame.Rect(25, ay, 260, 46)
                is_sel = (a.id == state.selected_army_id)
                b_hover_a = a_rect.collidepoint(mouse_pos)
                
                bg_col = COLOR_BUTTON_ACTIVE if is_sel else ((55, 65, 82) if b_hover_a else (38, 44, 58))
                pygame.draw.rect(screen, bg_col, a_rect, border_radius=4)
                pygame.draw.rect(screen, COLOR_GOLD if is_sel else COLOR_PANEL_BORDER, a_rect, 1, border_radius=4)

                # Army info
                screen.blit(font_sm.render(f"{a.name} ({a.troops:,} men)", True, COLOR_TEXT_WHITE), (35, ay + 5))
                
                status_str = "Idle"
                if a.in_battle: status_str = "⚔ IN BATTLE!"
                elif a.is_sieging: status_str = f"Besieging ({a.siege_progress}%)"
                elif a.is_moving: status_str = f"Marching to {PROVINCES[a.next_province]['name'].split()[0]}"
                else: status_str = f"Stationed in {PROVINCES[a.province]['name'].split()[0]}"

                screen.blit(font_xs.render(status_str, True, COLOR_GOLD if a.in_battle else COLOR_TEXT_MUTED), (35, ay + 25))

                if mouse_clicked and b_hover_a:
                    state.selected_army_id = a.id
                    state.selected_province = a.province

                ay += 52

        # Chronicle of Britain
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 495), (285, 495), 1)
        screen.blit(font_md.render("Chronicle of Britain", True, COLOR_GOLD), (25, 505))

        log_y = 535
        for log_msg in state.logs[-6:]:
            disp = log_msg[:34] + "..." if len(log_msg) > 37 else log_msg
            lm_surf = font_sm.render(f"• {disp}", True, COLOR_TEXT_MUTED)
            screen.blit(lm_surf, (25, log_y))
            log_y += 24

        # ---------------------------------------------------------
        # 3. CENTER: TERRITORY BALANCE & MAP
        # ---------------------------------------------------------
        map_bg_rect = pygame.Rect(310, 62, 540, WINDOW_HEIGHT - 72)
        pygame.draw.rect(screen, COLOR_OCEAN, map_bg_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, map_bg_rect, 2, border_radius=6)

        # Territory Control Bar (Wessex vs Danelaw)
        wessex_count = state.get_provinces_count(state.player_id)
        danelaw_count = state.get_provinces_count(state.enemy_id)
        total_provs = 12

        bar_x = 330
        bar_y = 75
        bar_w = 500
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

        state.hovered_province = None

        # -----------------------------------------------------------
        # PASS 1: Fill all land tiles (full tile, no gap = seamless)
        # -----------------------------------------------------------
        for r, row in enumerate(raw_grid):
            for c, ch in enumerate(row):
                cell_x = map_origin_x + (c * tile_w)
                cell_y = map_origin_y + 45 + (r * tile_h)
                cell_rect = pygame.Rect(cell_x, cell_y, tile_w, tile_h)

                if ch == ".":
                    # Ocean dashes
                    if (r + c) % 7 == 0:
                        pygame.draw.line(screen, (28, 48, 76),
                                         (cell_x + 4, cell_y + 12), (cell_x + 12, cell_y + 12))
                    continue

                prov_id  = cell_to_prov.get((c, r))
                prov_info = PROVINCES.get(prov_id)
                col = tuple(prov_info["color"]) if prov_info else (150, 150, 150)

                is_hovered  = cell_rect.collidepoint(mouse_pos)
                is_selected = (prov_id == state.selected_province)

                if is_hovered:
                    state.hovered_province = prov_id
                    col = (min(255, col[0] + 45), min(255, col[1] + 45), min(255, col[2] + 45))

                # Draw full tile (no 1-px gap → seamless within province)
                pygame.draw.rect(screen, col, (cell_x, cell_y, tile_w, tile_h))

                # Subtle inner highlight (top/left edges only within same province)
                pygame.draw.line(screen,
                    (min(255, col[0]+18), min(255, col[1]+18), min(255, col[2]+18)),
                    (cell_x, cell_y), (cell_x + tile_w - 1, cell_y))
                pygame.draw.line(screen,
                    (min(255, col[0]+18), min(255, col[1]+18), min(255, col[2]+18)),
                    (cell_x, cell_y), (cell_x, cell_y + tile_h - 1))

                if mouse_clicked and is_hovered:
                    if not state.build_mode:
                        # CK2 style: Left-clicking a province inspects that province and unselects armies!
                        state.selected_province = prov_id
                        state.selected_army_id = None
                        state.selected_army_ids = []
                        state.selected_settlement = None
                        state.selected_vassal_idx = None

        # -----------------------------------------------------------
        # PASS 2: Draw borders ONLY on edges between different PROVINCES
        #         (tiles of same province = seamless; different province = border)
        # -----------------------------------------------------------
        BORDER_COL   = (0, 0, 0)      # black line between provinces
        BORDER_W     = 2

        def get_prov(col_i, row_i):
            """Return province id for tile, or None if ocean."""
            return cell_to_prov.get((col_i, row_i))

        for r, row in enumerate(raw_grid):
            for c, ch in enumerate(row):
                if ch == ".":
                    continue
                cell_x = map_origin_x + (c * tile_w)
                cell_y = map_origin_y + 45 + (r * tile_h)
                prov_id    = get_prov(c, r)
                is_selected = (prov_id == state.selected_province)
                border_col = COLOR_GOLD if is_selected else BORDER_COL

                # Right edge — draw if neighbor is different province (or ocean)
                if get_prov(c + 1, r) != prov_id:
                    ex = cell_x + tile_w - 1
                    pygame.draw.line(screen, border_col,
                                     (ex, cell_y), (ex, cell_y + tile_h - 1), BORDER_W)
                # Bottom edge
                if get_prov(c, r + 1) != prov_id:
                    ey = cell_y + tile_h - 1
                    pygame.draw.line(screen, border_col,
                                     (cell_x, ey), (cell_x + tile_w - 1, ey), BORDER_W)
                # Left edge
                if get_prov(c - 1, r) != prov_id:
                    pygame.draw.line(screen, border_col,
                                     (cell_x, cell_y), (cell_x, cell_y + tile_h - 1), BORDER_W)
                # Top edge
                if get_prov(c, r - 1) != prov_id:
                    pygame.draw.line(screen, border_col,
                                     (cell_x, cell_y), (cell_x + tile_w - 1, cell_y), BORDER_W)

                # Golden highlight on selected province (reinforcing border)
                if is_selected:
                    pygame.draw.rect(screen, COLOR_GOLD,
                                     (cell_x, cell_y, tile_w, tile_h), 1)

        # -----------------------------------------------------------
        # PASS 2.5: Draw Fiefdom Sub-divisions & Borders
        # -----------------------------------------------------------
        fief_palette = [(120, 200, 255), (255, 175, 90), (190, 130, 255), (90, 255, 190), (255, 120, 150), (240, 220, 90)]
        for f_idx, (fid, fdata) in enumerate(state.fiefs.items()):
            f_color = fief_palette[f_idx % len(fief_palette)]
            is_f_sel = (state.selected_fief_id == fid)
            
            for (fc, fr) in fdata["tiles"]:
                fx = map_origin_x + (fc * tile_w)
                fy = map_origin_y + 45 + (fr * tile_h)
                
                # Fief border / outline
                if is_f_sel:
                    f_surf = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
                    f_surf.fill((100, 255, 120, 75))
                    screen.blit(f_surf, (fx, fy))
                    pygame.draw.rect(screen, (100, 255, 120), (fx, fy, tile_w, tile_h), 2)
                elif fdata["holder"] is None:
                    # Unclaimed / empty fief: dashed subtle pattern
                    pygame.draw.rect(screen, (170, 180, 200), (fx + 1, fy + 1, tile_w - 2, tile_h - 2), 1)
                else:
                    # Claimed barony fief: delicate sub-border
                    pygame.draw.rect(screen, (*f_color,), (fx + 1, fy + 1, tile_w - 2, tile_h - 2), 1)

        # -----------------------------------------------------------
        # PASS 3: Draw Built Settlements / Cities
        # -----------------------------------------------------------
        for (sc, sr), sdata in state.settlements.items():
            sx = map_origin_x + (sc * tile_w)
            sy = map_origin_y + 45 + (sr * tile_h)
            
            # City Foundation Block with Stone Walls
            base_rect = pygame.Rect(sx + 2, sy + 2, tile_w - 4, tile_h - 4)
            is_city_hover = base_rect.collidepoint(mouse_pos)
            is_city_sel = (state.selected_settlement == (sc, sr))
            
            pygame.draw.rect(screen, (55, 60, 75) if is_city_hover else (38, 42, 54), base_rect, border_radius=4)
            border_city_col = (100, 255, 120) if is_city_sel else COLOR_GOLD
            pygame.draw.rect(screen, border_city_col, base_rect, 2 if is_city_sel else 1, border_radius=4)
            
            # Castle Tower graphic drawn using geometric shapes (Clear & sharp, no broken font glyphs)
            tw, th = tile_w - 8, tile_h - 8
            tx, ty = sx + 4, sy + 4
            # Keep wall
            pygame.draw.rect(screen, (85, 95, 115), (tx + 2, ty + 4, tw - 4, th - 4))
            # Left turret
            pygame.draw.rect(screen, COLOR_GOLD, (tx + 1, ty + 1, 4, 6))
            # Right turret
            pygame.draw.rect(screen, COLOR_GOLD, (tx + tw - 5, ty + 1, 4, 6))
            # Center battlements
            pygame.draw.rect(screen, COLOR_GOLD, (tx + tw // 2 - 2, ty + 2, 4, 3))
            # Arch gate
            pygame.draw.rect(screen, (20, 24, 32), (tx + tw // 2 - 2, ty + th - 5, 4, 5))

            # Click city to inspect settlement details!
            if mouse_clicked and is_city_hover and not state.build_mode:
                state.selected_settlement = (sc, sr)
                state.selected_province = sdata["province"]
                state.selected_army_id = None

        # -----------------------------------------------------------
        # PASS 4: Build Mode Hover & Placement Ghost
        # -----------------------------------------------------------
        if state.build_mode and state.selected_province:
            # Determine tile hovered
            mx, my = mouse_pos
            hc = (mx - map_origin_x) // tile_w
            hr = (my - (map_origin_y + 45)) // tile_h

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

            # Draw Ghost Tiles
            ghost_col = (50, 220, 80, 140) if is_valid else (220, 50, 50, 140)
            border_c = (80, 255, 110) if is_valid else (255, 80, 80)
            for tc, tr in target_tiles:
                gx = map_origin_x + (tc * tile_w)
                gy = map_origin_y + 45 + (tr * tile_h)
                gsurf = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
                gsurf.fill(ghost_col)
                screen.blit(gsurf, (gx, gy))
                pygame.draw.rect(screen, border_c, (gx, gy, tile_w, tile_h), 2)

            # Left click to place
            if mouse_clicked and is_valid:
                state.player["gold"] -= 1000
                prov_obj["tax"] += 10
                prov_obj["levies_max"] += 500
                prov_obj["levies_current"] += 500
                for tc, tr in target_tiles:
                    state.settlements[(tc, tr)] = {
                        "province": state.selected_province,
                        "type": "town",
                        "name": f"{prov_obj['name'].split()[0]} Burgh"
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
                screen.blit(sh_surf, (lx + 1, ly + 1))
                screen.blit(lbl_surf, (lx, ly))

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

        # Find the pixel centroid of tiles that border between two adjacent provinces
        def border_midpoint(pid_a, pid_b):
            """Return pixel midpoint of tiles where pid_a and pid_b touch."""
            border_pixels = []
            dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            for (c, r), pid in cell_to_prov.items():
                if pid != pid_a:
                    continue
                for dc, dr in dirs:
                    if cell_to_prov.get((c + dc, r + dr)) == pid_b:
                        # This tile is on the border
                        cx = map_origin_x + c * tile_w + tile_w // 2
                        cy = map_origin_y + 45 + r * tile_h + tile_h // 2
                        border_pixels.append((cx, cy))
                        break
            if not border_pixels:
                return None
            bx = sum(p[0] for p in border_pixels) // len(border_pixels)
            by = sum(p[1] for p in border_pixels) // len(border_pixels)
            return (bx, by)

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
            is_sel_army = (army.id == state.selected_army_id)

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
            if army.in_battle:
                txt_badge = f"⚔ {army.troops:,}"
                p_bg = (185, 35, 35)
                p_border = (255, 220, 50)
            elif army.is_sieging:
                txt_badge = f"⚑ {army.troops:,}"
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
            screen.blit(font_sm.render(f"Location Tile: ({s_coord[0]}, {s_coord[1]})", True, COLOR_TEXT_MUTED), (880, 175))
            screen.blit(font_sm.render(f"Ruling Lord: {s_data.get('lord', 'Crown Fief')}", True, COLOR_GOLD), (880, 200))
            screen.blit(font_sm.render("Fortification Level: II (Stone Walls)", True, COLOR_TEXT_WHITE), (880, 225))
            screen.blit(font_sm.render("Economic Income: +6 Gold / month", True, COLOR_TEXT_GREEN), (880, 250))
            screen.blit(font_sm.render("Local Garrison: 300 Defenders", True, COLOR_TEXT_WHITE), (880, 275))
            
            # Close/Back button
            cls_btn = pygame.Rect(880, 315, 290, 36)
            b_c_hov = cls_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, COLOR_BUTTON_HOVER if b_c_hov else COLOR_BUTTON_NORMAL, cls_btn, border_radius=6)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, cls_btn, 1, border_radius=6)
            screen.blit(font_sm.render("← Back to Province View", True, COLOR_TEXT_WHITE), (940, 323))
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
            elif sel_army.is_sieging:
                screen.blit(font_md.render(f"STATUS: 🏰 Besieging ({sel_army.siege_progress}%)", True, COLOR_GOLD), (880, 202))
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

            # Disband Button
            dis_btn = pygame.Rect(880, 435, 290, 40)
            b_d_hover = dis_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (80, 35, 35) if b_d_hover else (60, 28, 28), dis_btn, border_radius=6)
            pygame.draw.rect(screen, COLOR_TEXT_RED, dis_btn, 1, border_radius=6)
            screen.blit(font_md.render("DISBAND THIS HOST", True, (255, 220, 220)), (930, 444))
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
                for c_name, c_info in list(prov_cities.items())[:4]:
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
                        if v.get("tiles"):
                            state.selected_settlement = v["tiles"][0]

                    vy += 50

            # -------------------------------------------------------------
            # TAB 4: FIEFS (Fiefs Management & Granting)
            # -------------------------------------------------------------
            elif state.right_tab == "fiefs":
                screen.blit(font_md.render("Provincial Fiefs & Baronies", True, COLOR_GOLD), (880, 160))
                prov_fiefs = [f for f in state.fiefs.values() if f["province"] == state.selected_province]
                fy = 190
                for f_data in prov_fiefs[:4]:
                    f_box = pygame.Rect(880, fy, 290, 52)
                    is_f_hov = f_box.collidepoint(mouse_pos)
                    is_f_sel = (state.selected_fief_id == f_data["id"])
                    pygame.draw.rect(screen, (55, 65, 85) if is_f_sel else ((42, 48, 62) if is_f_hov else (32, 36, 48)), f_box, border_radius=4)
                    pygame.draw.rect(screen, (100, 255, 120) if is_f_sel else COLOR_PANEL_BORDER, f_box, 1, border_radius=4)

                    holder_str = f"Holder: {f_data['holder']}" if f_data["holder"] else "Status: UNASSIGNED FIEF"
                    h_col = (180, 255, 180) if f_data["holder"] else (255, 170, 70)
                    screen.blit(font_xs.render(f"🛡 {f_data['name']} ({len(f_data['tiles'])} Tiles)", True, COLOR_GOLD), (888, fy + 4))
                    screen.blit(font_xs.render(holder_str, True, h_col), (888, fy + 18))

                    # Grant Fief Button for Unassigned Fiefs
                    if f_data["holder"] is None and is_player_owned:
                        g_btn = pygame.Rect(888, fy + 32, 270, 16)
                        g_hov = g_btn.collidepoint(mouse_pos)
                        pygame.draw.rect(screen, (40, 110, 60) if g_hov else (30, 80, 45), g_btn, border_radius=3)
                        screen.blit(font_xs.render("GRANT FIEF TO VASSAL", True, COLOR_TEXT_WHITE), (960, fy + 32))
                        if mouse_clicked and g_hov:
                            v_list = state.vassals.get(state.selected_province, [])
                            if v_list:
                                chosen_v = random.choice(v_list)
                                f_data["holder"] = chosen_v["name"]
                                f_data["vassal_id"] = chosen_v["id"]
                                chosen_v["gold"] += 100
                                state.logs.append(f"Granted {f_data['name']} to {chosen_v['name']}!")
                    else:
                        screen.blit(font_xs.render("Tiles physically partitioned on map", True, COLOR_TEXT_MUTED), (888, fy + 33))

                    if mouse_clicked and is_f_hov:
                        state.selected_fief_id = f_data["id"]

                    fy += 58
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

        # Highlight selected army badges with green ring — EXACT same pos calc as badge draw
        for aid in state.selected_army_ids:
            sel_a = next((a for a in state.armies if a.id == aid), None)
            if sel_a:
                base_pos = province_anchors.get(sel_a.province)
                if not base_pos:
                    continue
                bx, by = base_pos[0] - 15, base_pos[1] - 25
                if sel_a.is_moving and sel_a.next_province:
                    next_pos = province_anchors.get(sel_a.next_province, base_pos)
                    pct = sel_a.move_progress / 100.0
                    bx = int(bx + (next_pos[0] - base_pos[0]) * pct)
                    by = int(by + (next_pos[1] - base_pos[1]) * pct)
                # Outline matches badge size exactly (104×28)
                pygame.draw.rect(screen, (100, 255, 120),
                                 pygame.Rect(bx - 2, by - 2, 108, 32), 2, border_radius=5)

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

            t1 = font_sm.render(f"My Liege, {req['vassal']} humbly requests your royal charter", True, COLOR_TEXT_WHITE)
            t2 = font_sm.render(f"to construct a fortified market town in {req['province_name']}.", True, COLOR_TEXT_WHITE)
            t3 = font_xs.render("• Granting Charter: Vassal pays cost, +15 Vassal Opinion, +5 Tax, +250 Levies.", True, COLOR_TEXT_GREEN)
            t4 = font_xs.render("• Denying Charter: -15 Vassal Opinion.", True, COLOR_TEXT_RED)

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

            if mouse_clicked and app_hov:
                pid = req["province_id"]
                p_obj = PROVINCES.get(pid)
                if p_obj:
                    p_obj["tax"] += 5
                    p_obj["levies_max"] += 250
                    p_obj["levies_current"] += 250
                    req["vassal_ref"]["opinion"] = min(100, req["vassal_ref"]["opinion"] + 15)
                    req["vassal_ref"]["gold"] = max(0, req["vassal_ref"]["gold"] - 100)
                    
                    # Find free 2 tiles in this province to establish the new town!
                    tiles = prov_tile_list.get(pid, [])
                    tile_set = set(tiles)
                    placed = False
                    for (c, r) in tiles:
                        if (c, r) not in state.settlements:
                            if (c + 1, r) in tile_set and (c + 1, r) not in state.settlements:
                                state.settlements[(c, r)] = {"province": pid, "type": "town", "name": f"{req['vassal'].split()[0]}'s Borough"}
                                state.settlements[(c + 1, r)] = {"province": pid, "type": "town", "name": f"{req['vassal'].split()[0]}'s Borough"}
                                placed = True
                                break
                            elif (c, r + 1) in tile_set and (c, r + 1) not in state.settlements:
                                state.settlements[(c, r)] = {"province": pid, "type": "town", "name": f"{req['vassal'].split()[0]}'s Borough"}
                                state.settlements[(c, r + 1)] = {"province": pid, "type": "town", "name": f"{req['vassal'].split()[0]}'s Borough"}
                                placed = True
                                break
                    state.logs.append(f"Granted charter! {req['vassal']} established a thriving new borough in {p_obj['name']}.")
                state.vassal_build_requests.pop(0)

            elif mouse_clicked and den_hov:
                req["vassal_ref"]["opinion"] = max(0, req["vassal_ref"]["opinion"] - 15)
                state.logs.append(f"Denied charter to {req['vassal']}. Their loyalty wavers (-15 Opinion).")
                state.vassal_build_requests.pop(0)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_game()
