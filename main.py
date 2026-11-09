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
    def __init__(self, army_id, owner_id, province_id, troops, name="Levy Host"):
        self.id = army_id
        self.owner = owner_id
        self.province = province_id
        self.troops = troops
        self.name = name
        
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
        new_army = Army(army_id, self.player_id, province_id, available, army_name)
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
                new_army = Army(army_id, self.player_id, pid, available, army_name)
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
        leader_army = armies_here[0]
        leader_army.troops = total_troops
        leader_army.name = f"Royal Host of {PROVINCES[province_id]['name'].split()[0]}"
        
        for a in armies_here[1:]:
            if a.id == self.selected_army_id:
                self.selected_army_id = leader_army.id
            self.armies.remove(a)
            
        self.logs.append(f"Combined {len(armies_here)} hosts into a grand army of {total_troops:,} men!")

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
        for prov in PROVINCES.values():
            owner = CHARACTERS.get(prov["owner"])
            if owner:
                owner["gold"] += prov["tax"]
                # Reinforce unraised garrison slowly
                if prov["levies_current"] < prov["levies_max"]:
                    prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + 50)
        
        # Army upkeep cost (1 gold per 500 men)
        player_troops = self.get_field_troops(self.player_id)
        upkeep = player_troops // 500
        self.player["gold"] = max(0, self.player["gold"] - upkeep)

        self.player["prestige"] += 1
        self.player["piety"] += 1
        self.enemy["prestige"] += 1

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

        # Right-click march orders for box-selected armies
        if right_clicked and state.selected_army_ids:
            # Accurate province detection: reverse-lookup tile under cursor
            mx, my = mouse_pos
            target_province = None
            # Convert screen pos -> grid cell -> province
            col_idx = (mx - map_origin_x) // tile_w
            row_idx = (my - (map_origin_y + 45)) // tile_h
            target_province = cell_to_prov.get((col_idx, row_idx))
            if target_province:
                for aid in state.selected_army_ids:
                    army_obj = next((a for a in state.armies if a.id == aid), None)
                    if army_obj:
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
        stats_x = 610
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
            stats_x += 140

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
                        curr_army = state.get_selected_army()
                        if curr_army and curr_army.owner == state.player_id and prov_id != curr_army.province:
                            state.order_army_march(curr_army, prov_id)
                        state.selected_province = prov_id

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
        # PASS 3: Draw Built Settlements / Cities
        # -----------------------------------------------------------
        for (sc, sr), sdata in state.settlements.items():
            sx = map_origin_x + (sc * tile_w)
            sy = map_origin_y + 45 + (sr * tile_h)
            # Small settlement foundation icon
            pygame.draw.rect(screen, (40, 45, 55), (sx + 3, sy + 3, tile_w - 6, tile_h - 6), border_radius=3)
            pygame.draw.rect(screen, COLOR_GOLD, (sx + 3, sy + 3, tile_w - 6, tile_h - 6), 1, border_radius=3)
            # City Icon / Letter
            c_txt = font_xs.render("🏰", True, COLOR_GOLD)
            screen.blit(c_txt, (sx + 6, sy + 4))

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
            elif state.player["gold"] < 100:
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
            ghost_col = (50, 220, 80, 120) if is_valid else (220, 50, 50, 120)
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
                state.player["gold"] -= 100
                prov_obj["tax"] += 6
                prov_obj["levies_max"] += 300
                prov_obj["levies_current"] += 300
                for tc, tr in target_tiles:
                    state.settlements[(tc, tr)] = {
                        "province": state.selected_province,
                        "type": "town",
                        "name": f"{prov_obj['name'].split()[0]} Burgh"
                    }
                state.logs.append(f"Constructed new Town Burgh in {prov_obj['name']}! (+6 Tax, +300 Levies)")
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
        # DRAW ARMIES ON MAP (Badges with Troop Counts)
        # ---------------------------------------------------------
        for army in state.armies:
            base_pos = province_anchors.get(army.province)
            if not base_pos:
                continue

            bx, by = base_pos[0] - 15, base_pos[1] - 25

            # If moving, interpolate slightly towards next province
            if army.is_moving and army.next_province:
                next_pos = province_anchors.get(army.next_province, base_pos)
                pct = army.move_progress / 100.0
                bx = int(bx + (next_pos[0] - base_pos[0]) * pct)
                by = int(by + (next_pos[1] - base_pos[1]) * pct)

            badge_w = 84
            badge_h = 24
            badge_rect = pygame.Rect(bx, by, badge_w, badge_h)

            is_player = (army.owner == state.player_id)
            is_sel_army = (army.id == state.selected_army_id)
            is_badge_hover = badge_rect.collidepoint(mouse_pos)

            # Badge Styling
            if army.in_battle:
                b_color = (190, 40, 40)
                border_col = (255, 220, 50)
                txt_badge = f"⚔ {army.troops:,}"
            elif army.is_sieging:
                b_color = (160, 90, 30)
                border_col = COLOR_GOLD
                txt_badge = f"🏰 {army.troops:,}"
            elif is_player:
                b_color = (170, 30, 30) if not is_sel_army else (210, 45, 45)
                border_col = COLOR_GOLD if is_sel_army else (240, 180, 180)
                txt_badge = f"🛡 {army.troops:,}"
            else:
                b_color = (40, 60, 90)
                border_col = (120, 160, 220)
                txt_badge = f"⚔ {army.troops:,}"

            pygame.draw.rect(screen, b_color, badge_rect, border_radius=4)
            pygame.draw.rect(screen, border_col, badge_rect, 2 if is_sel_army else 1, border_radius=4)

            badge_surf = font_xs.render(txt_badge, True, COLOR_TEXT_WHITE)
            screen.blit(badge_surf, (bx + 6, by + 4))

            # Click badge to select army
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

        # If an army is selected, show Army Command Card first!
        if sel_army and sel_army.owner == state.player_id:
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
            screen.blit(p_title, (880, 80))

            sub_title = font_sm.render(f"Culture: {sel_prov['culture']}  •  Faith: {sel_prov['religion']}", True, COLOR_TEXT_MUTED)
            screen.blit(sub_title, (880, 110))

            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 135), (1170, 135), 1)

            # Owner Badge
            screen.blit(font_md.render("Held by:", True, COLOR_TEXT_WHITE), (880, 145))
            owner_p = portrait_cache.get(sel_prov["owner"])
            if owner_p:
                mini_p = pygame.transform.smoothscale(owner_p, (50, 50))
                screen.blit(mini_p, (880, 175))
            owner_c = coa_cache.get(sel_prov["owner"])
            if owner_c:
                screen.blit(owner_c, (935, 175))

            screen.blit(font_md.render(owner_char["name"], True, COLOR_GOLD if is_player_owned else COLOR_TEXT_RED), (980, 175))
            screen.blit(font_sm.render(owner_char["title"], True, COLOR_TEXT_WHITE), (980, 198))

            # Details
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 240), (1170, 240), 1)
            screen.blit(font_md.render("Province Details", True, COLOR_GOLD), (880, 252))

            screen.blit(icon_gold, (880, 285))
            screen.blit(font_sm.render(f"Monthly Tax Revenue: +{sel_prov['tax']} Gold", True, COLOR_TEXT_WHITE), (915, 288))

            screen.blit(icon_troops, (880, 320))
            screen.blit(font_sm.render(f"Levies Available: {sel_prov['levies_current']} / {sel_prov['levies_max']}", True, COLOR_TEXT_WHITE), (915, 323))

            # Actions
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 365), (1170, 365), 1)
            screen.blit(font_md.render("Military Orders", True, COLOR_GOLD), (880, 375))

            if is_player_owned:
                # 1. Raise Local Levy Button
                raise_btn = pygame.Rect(880, 405, 290, 42)
                b_r_hover = raise_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (35, 95, 50) if b_r_hover else (25, 70, 38), raise_btn, border_radius=6)
                pygame.draw.rect(screen, COLOR_TEXT_GREEN, raise_btn, 1, border_radius=6)
                screen.blit(font_md.render(f"RAISE LEVY ({sel_prov['levies_current']} Men)", True, COLOR_TEXT_WHITE), (915, 415))
                if mouse_clicked and b_r_hover:
                    state.raise_province_levy(state.selected_province)

                # 2. Rally All Armies Here Button
                rally_btn = pygame.Rect(880, 455, 290, 40)
                b_rl_hover = rally_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (35, 65, 110) if b_rl_hover else (25, 48, 85), rally_btn, border_radius=6)
                pygame.draw.rect(screen, (70, 130, 220), rally_btn, 1, border_radius=6)
                screen.blit(font_md.render("RALLY ALL ARMIES HERE (M)", True, COLOR_TEXT_WHITE), (895, 464))
                if mouse_clicked and b_rl_hover:
                    state.rally_all_armies_to(state.selected_province)

                # 3. Develop Lands Button
                dev_btn = pygame.Rect(880, 505, 290, 36)
                b_dv_hover = dev_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if b_dv_hover else COLOR_BUTTON_NORMAL, dev_btn, border_radius=6)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, dev_btn, 1, border_radius=6)
                screen.blit(font_sm.render("Develop Lands (-50 Gold, +4 Tax, +250 Levies)", True, COLOR_GOLD), (888, 513))
                if mouse_clicked and b_dv_hover:
                    if state.player["gold"] >= 50:
                        state.player["gold"] -= 50
                        sel_prov["tax"] += 4
                        sel_prov["levies_max"] += 250
                        state.logs.append(f"Developed lands in {sel_prov['name']}!")
                    else:
                        state.logs.append("Need 50 Gold to develop lands!")

                # 4. BUILD SETTLEMENT BUTTON (2 Tiles, Rotatable with T)
                bld_btn = pygame.Rect(880, 550, 290, 42)
                b_bld_hover = bld_btn.collidepoint(mouse_pos)
                b_bld_active = state.build_mode
                bld_bg = (140, 80, 20) if b_bld_active else ((85, 50, 15) if b_bld_hover else (60, 35, 10))
                pygame.draw.rect(screen, bld_bg, bld_btn, border_radius=6)
                pygame.draw.rect(screen, COLOR_GOLD if b_bld_active else (200, 140, 40), bld_btn, 2 if b_bld_active else 1, border_radius=6)
                
                bld_lbl = "CANCEL BUILD MODE (ESC)" if b_bld_active else "BUILD CITY (2 TILES - 100g)"
                screen.blit(font_md.render(bld_lbl, True, COLOR_GOLD if b_bld_active else COLOR_TEXT_WHITE), (895, 559))
                if mouse_clicked and b_bld_hover:
                    state.build_mode = not state.build_mode

                if state.build_mode:
                    hint1 = font_xs.render("• Hover mouse over 2 adjacent tiles inside province.", True, COLOR_TEXT_WHITE)
                    hint2 = font_xs.render("• Press 'T' to rotate orientation (Horiz / Vert).", True, COLOR_GOLD)
                    hint3 = font_xs.render("• Click to place settlement when green.", True, COLOR_TEXT_GREEN)
                    screen.blit(hint1, (880, 600))
                    screen.blit(hint2, (880, 618))
                    screen.blit(hint3, (880, 636))
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
                # Outline matches badge size exactly (84×24)
                pygame.draw.rect(screen, (100, 255, 120),
                                 pygame.Rect(bx - 2, by - 2, 88, 28), 2, border_radius=5)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_game()
