"""
CK2-Lite: Britain AD 867
A Grand Strategy Prototype in Python / Pygame.
Features:
- Interactive Blocky Britain Province Map
- Rulers, Dynasties, Levies, and Tax Incomes
- Character Sheets (Alfred the Great, Halfdan Ragnarsson, Burgred, etc.)
- Speed Controls (Pause, Normal, Fast) with Real-Time Date Ticks
- War & Conquest Mechanic (Declare War, Siege & Conquer Provinces)
- Pop-up Decision Events (CK2-style intrigue and choices)
- Ready for packaging to standalone Windows .exe via PyInstaller
"""

import sys
import os
import json
import random
import pygame

# Initialize Pygame
pygame.init()
pygame.font.init()

# Game Window Dimensions
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 720
FPS = 60

# Set display mode immediately so convert_alpha() and textures can initialize
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("CK2-Lite: Britain AD 867 (Desktop Prototype)")

# Palette
COLOR_BG = (22, 26, 34)
COLOR_PANEL_BG = (32, 36, 46)
COLOR_PANEL_BORDER = (55, 62, 78)
COLOR_GOLD = (235, 185, 50)
COLOR_PRESTIGE = (80, 160, 240)
COLOR_PIETY = (240, 240, 255)
COLOR_TEXT_WHITE = (230, 235, 245)
COLOR_TEXT_MUTED = (150, 160, 175)
COLOR_TEXT_RED = (235, 75, 75)
COLOR_TEXT_GREEN = (75, 215, 110)
COLOR_BUTTON_NORMAL = (45, 52, 68)
COLOR_BUTTON_HOVER = (65, 75, 98)
COLOR_BUTTON_ACTIVE = (90, 105, 135)
COLOR_OCEAN = (20, 38, 62)

if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Fonts
font_sm = pygame.font.SysFont("segoeui", 14)
font_md = pygame.font.SysFont("segoeui", 17, bold=True)
font_lg = pygame.font.SysFont("segoeui", 22, bold=True)
font_title = pygame.font.SysFont("georgia", 26, bold=True)

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
    # Return placeholder surface if not found
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

# Load Portraits & Heraldry cache
portrait_cache = {}
coa_cache = {}

for cid, char in CHARACTERS.items():
    pfile = char.get("portrait", "portrait_default.png")
    portrait_cache[cid] = load_image(os.path.join("portraits", pfile), (80, 80))
    cfile = char.get("coa", "coa_wessex.png")
    coa_cache[cid] = load_image(os.path.join("heraldry", cfile), (36, 42))

# -------------------------------------------------------------
# Game State
# -------------------------------------------------------------
class GameState:
    def __init__(self):
        self.player_id = "char_alfred"
        self.selected_province = "wessex"
        self.hovered_province = None
        
        # Calendar: Start 1 January 867
        self.year = 867
        self.month = 1
        self.day = 1
        self.months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        self.month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Speed: 0 = Pause, 1 = Normal (1 day/sec), 2 = Fast (5 days/sec)
        self.speed = 1
        self.tick_timer = 0
        
        # Active War List: {"attacker": char_id, "defender": char_id, "target_prov": prov_id}
        self.active_wars = []
        
        # Active Event Modal: None or dict
        self.active_event = None
        self.event_cooldown = 15 # days before checking new event
        
        # Combat Notification Log
        self.logs = ["Year 867: The Great Heathen Army marches upon Britain."]
        
        # Compute starting troops & levies
        self.raised_levies = False

    @property
    def player(self):
        return CHARACTERS[self.player_id]

    def get_player_total_troops(self):
        total = 0
        for pid, prov in PROVINCES.items():
            if prov["owner"] == self.player_id:
                total += prov["levies_current"]
        return total

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

        # Update Wars
        self.update_wars()

        # Random Event Check
        self.event_cooldown -= 1
        if self.event_cooldown <= 0 and not self.active_event:
            self.maybe_trigger_event()
            self.event_cooldown = random.randint(25, 45)

    def monthly_tick(self):
        # Collect taxes & reinforce levies
        for pid, prov in PROVINCES.items():
            owner = CHARACTERS.get(prov["owner"])
            if owner:
                owner["gold"] += prov["tax"]
                if prov["levies_current"] < prov["levies_max"]:
                    prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + 50)
        
        # Monthly prestige/piety
        self.player["prestige"] += 1
        self.player["piety"] += 1

    def yearly_tick(self):
        # Character aging
        for char in CHARACTERS.values():
            if char["alive"]:
                char["age"] += 1
                if char["age"] > 60 and random.random() < 0.15:
                    self.logs.append(f"{char['name']} has passed away of old age.")

    def declare_war(self, target_prov_id):
        prov = PROVINCES[target_prov_id]
        defender_id = prov["owner"]
        if defender_id == self.player_id:
            return
        
        # Check if already at war
        for war in self.active_wars:
            if war["target_prov"] == target_prov_id:
                return

        defender = CHARACTERS[defender_id]
        self.player["prestige"] = max(0, self.player["prestige"] - 50)
        
        war = {
            "attacker": self.player_id,
            "defender": defender_id,
            "target_prov": target_prov_id,
            "siege_progress": 0,
            "days_elapsed": 0
        }
        self.active_wars.append(war)
        self.logs.append(f"War declared on {defender['name']} for {prov['name']}!")

    def update_wars(self):
        completed_wars = []
        for war in self.active_wars:
            war["days_elapsed"] += 1
            prov = PROVINCES[war["target_prov"]]
            atk_char = CHARACTERS[war["attacker"]]
            def_char = CHARACTERS[war["defender"]]

            atk_martial = atk_char["stats"]["martial"]
            def_martial = def_char["stats"]["martial"]

            # Advance siege every 5 days
            if war["days_elapsed"] % 3 == 0:
                roll = random.randint(1, 10) + (atk_martial - def_martial) // 2
                if roll > 4:
                    war["siege_progress"] += 15
                    prov["levies_current"] = max(0, prov["levies_current"] - 120)
                else:
                    war["siege_progress"] += 5

            if war["siege_progress"] >= 100 or prov["levies_current"] <= 0:
                # Victory!
                prov["owner"] = war["attacker"]
                prov["color"] = [195, 30, 30] # Player red
                atk_char["prestige"] += 100
                self.logs.append(f"Victory! {prov['name']} has been conquered by {atk_char['name']}!")
                completed_wars.append(war)

        for w in completed_wars:
            self.active_wars.remove(w)

    def maybe_trigger_event(self):
        events = [
            {
                "title": "A Viking Raid on the Coast",
                "desc": "Norse longships have been spotted near the shores. Peasants flee into the churches praying for salvation.",
                "options": [
                    {
                        "text": "Send the Fyrd to drive them into the sea! (-200 Troops, +40 Prestige)",
                        "effect": lambda: self.event_raid_fight()
                    },
                    {
                        "text": "Pay Danegeld bribe to spare the villages (-40 Gold, +10 Piety)",
                        "effect": lambda: self.event_raid_pay()
                    }
                ]
            },
            {
                "title": "Papal Envoy Arrives",
                "desc": "A holy bishop from Rome brings blessings and seeks a generous donation to rebuild an ancient abbey.",
                "options": [
                    {
                        "text": "Donate generously (-50 Gold, +60 Piety)",
                        "effect": lambda: self.event_papal_donate()
                    },
                    {
                        "text": "We need our coin for our own soldiers (-15 Piety)",
                        "effect": lambda: self.event_papal_refuse()
                    }
                ]
            },
            {
                "title": "A Feud in the Witan",
                "desc": "Two powerful Saxon nobles argue fiercely over hunting borders. They demand the King pass judgment.",
                "options": [
                    {
                        "text": "Rule fairly according to ancient Saxon law (+20 Prestige)",
                        "effect": lambda: self.event_noble_fair()
                    },
                    {
                        "text": "Tax them both for wasting the King's time (+35 Gold)",
                        "effect": lambda: self.event_noble_tax()
                    }
                ]
            }
        ]
        self.active_event = random.choice(events)

    def event_raid_fight(self):
        prov = PROVINCES.get(self.selected_province, PROVINCES["wessex"])
        prov["levies_current"] = max(0, prov["levies_current"] - 200)
        self.player["prestige"] += 40
        self.logs.append("Viking raiders repelled with heavy clash of shields!")

    def event_raid_pay(self):
        self.player["gold"] = max(0, self.player["gold"] - 40)
        self.player["piety"] += 10
        self.logs.append("Danegeld paid. The raiders sail back to their lands.")

    def event_papal_donate(self):
        self.player["gold"] = max(0, self.player["gold"] - 50)
        self.player["piety"] += 60
        self.logs.append("The Pope praises the piety of Wessex!")

    def event_papal_refuse(self):
        self.player["piety"] = max(0, self.player["piety"] - 15)
        self.logs.append("The papal envoy departs in dismay.")

    def event_noble_fair(self):
        self.player["prestige"] += 20
        self.logs.append("The King's wisdom is celebrated across the realm.")

    def event_noble_tax(self):
        self.player["gold"] += 35
        self.logs.append("Fined both nobles and filled the treasury.")

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
    grid_rows = len(raw_grid)
    grid_cols = len(raw_grid[0])
    
    # Calculate map render area in center-left
    map_origin_x = 320
    map_origin_y = 70
    tile_w = 26
    tile_h = 24

    # Pre-map coordinate to province id
    cell_to_prov = {}
    for r, row in enumerate(raw_grid):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            prov_id = None
            if ch == "H": prov_id = "highlands"
            elif ch == "A": prov_id = "alba"
            elif ch == "T": prov_id = "lothian"
            elif ch == "S" and r < 10: prov_id = "strathclyde"
            elif ch == "B": prov_id = "bernicia"
            elif ch == "N": prov_id = "deira"
            elif ch == "Y": prov_id = "jorvik"
            elif ch == "M" and c > 10: prov_id = "mercia"
            elif ch == "E": prov_id = "east_anglia"
            elif ch == "W" and r < 15: prov_id = "gwynedd"
            elif ch == "P": prov_id = "powys"
            elif ch == "D" and r > 14: prov_id = "deheubarth"
            elif ch == "W" and r >= 19: prov_id = "wessex"
            elif ch == "K": prov_id = "kent_essex"
            elif ch == "C" and c > 5: prov_id = "cornwall"
            elif ch == "U": prov_id = "ulster"
            elif ch == "C" and c <= 5: prov_id = "connacht"
            elif ch == "L" and c <= 5: prov_id = "leinster"
            elif ch == "M" and c <= 5: prov_id = "munster"
            else: prov_id = "wessex"
            cell_to_prov[(c, r)] = prov_id

    running = True
    while running:
        dt = clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    state.speed = 0 if state.speed > 0 else 1
                elif event.key == pygame.K_1:
                    state.speed = 1
                elif event.key == pygame.K_2:
                    state.speed = 2
                elif event.key == pygame.K_3:
                    state.speed = 3

        # Tick logic
        if state.speed > 0 and not state.active_event:
            state.tick_timer += dt
            tick_interval = 1000 // (state.speed * 2) # Speed 1: ~500ms, Speed 2: ~250ms, Speed 3: ~166ms
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

        # Title / Era
        t_surf = font_lg.render("CRUSADER KINGS II - LITE", True, COLOR_GOLD)
        screen.blit(t_surf, (20, 12))

        # Date & Speed
        date_str = f"{state.day:02d} {state.months[state.month - 1]} {state.year} AD"
        d_surf = font_md.render(date_str, True, COLOR_TEXT_WHITE)
        screen.blit(d_surf, (370, 15))

        # Speed buttons
        speeds = [(0, icon_speed_pause), (1, icon_speed_play), (2, icon_speed_fast)]
        for i, (sp, icon) in enumerate(speeds):
            btn_x = 510 + (i * 36)
            btn_rect = pygame.Rect(btn_x, 10, 32, 32)
            is_active = (state.speed == sp)
            b_col = COLOR_BUTTON_ACTIVE if is_active else (COLOR_BUTTON_HOVER if btn_rect.collidepoint(mouse_pos) else COLOR_BUTTON_NORMAL)
            pygame.draw.rect(screen, b_col, btn_rect, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_rect, 1, border_radius=4)
            screen.blit(icon, (btn_x + 4, 14))
            if mouse_clicked and btn_rect.collidepoint(mouse_pos) and not state.active_event:
                state.speed = sp

        # Player Stats (Gold, Prestige, Piety, Total Levies)
        stats_x = 660
        stats = [
            (icon_gold, str(state.player["gold"]), COLOR_GOLD),
            (icon_prestige, str(state.player["prestige"]), COLOR_PRESTIGE),
            (icon_piety, str(state.player["piety"]), COLOR_PIETY),
            (icon_troops, f"{state.get_player_total_troops():,}", COLOR_TEXT_WHITE)
        ]
        for icon, val_str, col in stats:
            screen.blit(icon, (stats_x, 14))
            v_surf = font_md.render(val_str, True, col)
            screen.blit(v_surf, (stats_x + 28, 15))
            stats_x += 115

        # ---------------------------------------------------------
        # 2. LEFT PANEL: PLAYER RULER & DYNASTY
        # ---------------------------------------------------------
        left_panel = pygame.Rect(10, 62, 290, WINDOW_HEIGHT - 72)
        pygame.draw.rect(screen, COLOR_PANEL_BG, left_panel, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, left_panel, 2, border_radius=6)

        # Portrait & Shield
        p_img = portrait_cache.get(state.player_id)
        if p_img:
            screen.blit(p_img, (25, 75))
        c_img = coa_cache.get(state.player_id)
        if c_img:
            screen.blit(c_img, (88, 125))

        # Ruler Info
        name_surf = font_md.render(state.player["name"], True, COLOR_TEXT_WHITE)
        title_surf = font_sm.render(state.player["title"], True, COLOR_GOLD)
        dynasty_surf = font_sm.render(f"Dynasty: {state.player['dynasty']}", True, COLOR_TEXT_MUTED)
        age_surf = font_sm.render(f"Age: {state.player['age']} years", True, COLOR_TEXT_MUTED)

        screen.blit(name_surf, (115, 75))
        screen.blit(title_surf, (115, 96))
        screen.blit(dynasty_surf, (115, 116))
        screen.blit(age_surf, (115, 134))

        # Stats Table
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 172), (285, 172), 1)
        st_title = font_md.render("Attributes", True, COLOR_GOLD)
        screen.blit(st_title, (25, 180))

        attr_keys = [
            ("Diplomacy", state.player["stats"]["diplomacy"], (100, 180, 255)),
            ("Martial", state.player["stats"]["martial"], (240, 100, 100)),
            ("Stewardship", state.player["stats"]["stewardship"], (120, 220, 140)),
            ("Intrigue", state.player["stats"]["intrigue"], (190, 120, 240)),
            ("Learning", state.player["stats"]["learning"], (255, 220, 120))
        ]
        for idx, (label, val, bar_col) in enumerate(attr_keys):
            row_y = 208 + (idx * 26)
            l_surf = font_sm.render(label, True, COLOR_TEXT_WHITE)
            v_surf = font_sm.render(str(val), True, COLOR_GOLD)
            screen.blit(l_surf, (25, row_y))
            screen.blit(v_surf, (115, row_y))

            # Progress bar
            pygame.draw.rect(screen, (40, 45, 58), (145, row_y + 4, 130, 8), border_radius=3)
            fill_w = min(130, int((val / 20) * 130))
            pygame.draw.rect(screen, bar_col, (145, row_y + 4, fill_w, 8), border_radius=3)

        # Traits
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 345), (285, 345), 1)
        tr_title = font_md.render("Traits", True, COLOR_GOLD)
        screen.blit(tr_title, (25, 355))

        for tidx, trait in enumerate(state.player["traits"]):
            t_box = pygame.Rect(25 + (tidx * 85), 382, 80, 24)
            pygame.draw.rect(screen, COLOR_BUTTON_NORMAL, t_box, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, t_box, 1, border_radius=4)
            tt_surf = font_sm.render(trait, True, COLOR_TEXT_WHITE)
            screen.blit(tt_surf, (t_box.x + 8, t_box.y + 3))

        # Chronicle Logs
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 420), (285, 420), 1)
        log_title = font_md.render("Chronicle of the Realm", True, COLOR_GOLD)
        screen.blit(log_title, (25, 430))

        log_y = 458
        for log_msg in state.logs[-7:]:
            # Wrap or truncate
            if len(log_msg) > 36:
                display_msg = log_msg[:33] + "..."
            else:
                display_msg = log_msg
            lm_surf = font_sm.render(f"• {display_msg}", True, COLOR_TEXT_MUTED)
            screen.blit(lm_surf, (25, log_y))
            log_y += 24

        # ---------------------------------------------------------
        # 3. CENTER: INTERACTIVE BLOCKY BRITAIN MAP
        # ---------------------------------------------------------
        map_bg_rect = pygame.Rect(310, 62, 540, WINDOW_HEIGHT - 72)
        pygame.draw.rect(screen, COLOR_OCEAN, map_bg_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, map_bg_rect, 2, border_radius=6)

        # Map Header
        map_title = font_sm.render("MAP OF BRITAIN & IRELAND (AD 867)", True, (130, 160, 200))
        screen.blit(map_title, (325, 75))

        state.hovered_province = None

        # Draw grid cells
        for r, row in enumerate(raw_grid):
            for c, ch in enumerate(row):
                cell_x = map_origin_x + (c * tile_w)
                cell_y = map_origin_y + 30 + (r * tile_h)
                cell_rect = pygame.Rect(cell_x, cell_y, tile_w, tile_h)

                if ch == ".":
                    # Ocean waves detail
                    if (r + c) % 6 == 0:
                        pygame.draw.line(screen, (32, 55, 88), (cell_x + 4, cell_y + 12), (cell_x + 12, cell_y + 12))
                else:
                    prov_id = cell_to_prov.get((c, r))
                    prov_info = PROVINCES.get(prov_id)
                    col = prov_info["color"] if prov_info else (160, 160, 160)

                    # Highlight if hovered or selected
                    is_hovered = cell_rect.collidepoint(mouse_pos)
                    is_selected = (prov_id == state.selected_province)

                    if is_hovered:
                        state.hovered_province = prov_id
                        # Lighten color
                        col = (min(255, col[0] + 50), min(255, col[1] + 50), min(255, col[2] + 50))
                    
                    # Fill tile
                    pygame.draw.rect(screen, col, (cell_x, cell_y, tile_w - 1, tile_h - 1))
                    
                    # Border highlights for selected province
                    if is_selected:
                        pygame.draw.rect(screen, COLOR_GOLD, (cell_x - 1, cell_y - 1, tile_w + 1, tile_h + 1), 2)
                    else:
                        # Subtle 3D border
                        pygame.draw.line(screen, (min(255, col[0] + 25), min(255, col[1] + 25), min(255, col[2] + 25)), (cell_x, cell_y), (cell_x + tile_w - 2, cell_y))
                        pygame.draw.line(screen, (max(0, col[0] - 30), max(0, col[1] - 30), max(0, col[2] - 30)), (cell_x, cell_y + tile_h - 2), (cell_x + tile_w - 2, cell_y + tile_h - 2))

                    if mouse_clicked and is_hovered and not state.active_event:
                        state.selected_province = prov_id

        # Province labels overlay
        label_positions = {
            "highlands": (map_origin_x + 175, map_origin_y + 60),
            "alba": (map_origin_x + 160, map_origin_y + 115),
            "strathclyde": (map_origin_x + 140, map_origin_y + 195),
            "lothian": (map_origin_x + 225, map_origin_y + 195),
            "bernicia": (map_origin_x + 235, map_origin_y + 245),
            "deira": (map_origin_x + 245, map_origin_y + 295),
            "jorvik": (map_origin_x + 230, map_origin_y + 335),
            "mercia": (map_origin_x + 220, map_origin_y + 400),
            "east_anglia": (map_origin_x + 315, map_origin_y + 425),
            "gwynedd": (map_origin_x + 130, map_origin_y + 355),
            "powys": (map_origin_x + 135, map_origin_y + 415),
            "deheubarth": (map_origin_x + 115, map_origin_y + 455),
            "wessex": (map_origin_x + 175, map_origin_y + 510),
            "kent_essex": (map_origin_x + 275, map_origin_y + 490),
            "cornwall": (map_origin_x + 95, map_origin_y + 540)
        }
        for pid, (lx, ly) in label_positions.items():
            p_data = PROVINCES.get(pid)
            if p_data:
                short_name = p_data["name"].split()[0]
                lbl_surf = font_sm.render(short_name, True, (245, 245, 245))
                # Shadow
                sh_surf = font_sm.render(short_name, True, (10, 15, 25))
                screen.blit(sh_surf, (lx + 1, ly + 1))
                screen.blit(lbl_surf, (lx, ly))

        # ---------------------------------------------------------
        # 4. RIGHT PANEL: SELECTED PROVINCE & ACTIONS
        # ---------------------------------------------------------
        right_panel = pygame.Rect(860, 62, 330, WINDOW_HEIGHT - 72)
        pygame.draw.rect(screen, COLOR_PANEL_BG, right_panel, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, right_panel, 2, border_radius=6)

        sel_prov = PROVINCES.get(state.selected_province)
        if sel_prov:
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

            screen.blit(font_md.render(owner_char["name"], True, COLOR_GOLD), (980, 175))
            screen.blit(font_sm.render(owner_char["title"], True, COLOR_TEXT_WHITE), (980, 198))

            # Economic & Military stats
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 240), (1170, 240), 1)
            screen.blit(font_md.render("Province Details", True, COLOR_GOLD), (880, 252))

            screen.blit(icon_gold, (880, 285))
            screen.blit(font_sm.render(f"Monthly Tax Income: +{sel_prov['tax']} Gold", True, COLOR_TEXT_WHITE), (915, 288))

            screen.blit(icon_troops, (880, 320))
            screen.blit(font_sm.render(f"Garrison & Levies: {sel_prov['levies_current']} / {sel_prov['levies_max']}", True, COLOR_TEXT_WHITE), (915, 323))

            # Action Buttons
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 365), (1170, 365), 1)
            screen.blit(font_md.render("Diplomacy & Warfare", True, COLOR_GOLD), (880, 375))

            if is_player_owned:
                # Improve Province Button
                imp_btn = pygame.Rect(880, 415, 290, 42)
                b_hover = imp_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if b_hover else COLOR_BUTTON_NORMAL, imp_btn, border_radius=6)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, imp_btn, 1, border_radius=6)
                
                ib_text = font_md.render("Develop Lands (-50 Gold, +4 Tax)", True, COLOR_GOLD)
                screen.blit(ib_text, (895, 426))

                if mouse_clicked and b_hover and not state.active_event:
                    if state.player["gold"] >= 50:
                        state.player["gold"] -= 50
                        sel_prov["tax"] += 4
                        sel_prov["levies_max"] += 200
                        state.logs.append(f"Developed infrastructure in {sel_prov['name']}!")
                    else:
                        state.logs.append("Not enough gold to develop province!")
            else:
                # Declare War Button
                war_btn = pygame.Rect(880, 415, 290, 44)
                is_at_war = any(w["target_prov"] == state.selected_province for w in state.active_wars)
                
                if is_at_war:
                    pygame.draw.rect(screen, (90, 30, 30), war_btn, border_radius=6)
                    pygame.draw.rect(screen, COLOR_TEXT_RED, war_btn, 1, border_radius=6)
                    wb_text = font_md.render("Besieging Province...", True, COLOR_TEXT_WHITE)
                    screen.blit(wb_text, (940, 427))
                else:
                    b_hover = war_btn.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (160, 40, 40) if b_hover else (120, 30, 30), war_btn, border_radius=6)
                    pygame.draw.rect(screen, (220, 60, 60), war_btn, 1, border_radius=6)
                    
                    wb_text = font_md.render("DECLARE CONQUEST WAR", True, (255, 240, 240))
                    screen.blit(wb_text, (915, 426))

                    if mouse_clicked and b_hover and not state.active_event:
                        state.declare_war(state.selected_province)

            # Active War Tracker Box
            if state.active_wars:
                pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 480), (1170, 480), 1)
                screen.blit(font_md.render("Current Campaigns", True, COLOR_TEXT_RED), (880, 492))
                
                for widx, w in enumerate(state.active_wars):
                    w_box_y = 525 + (widx * 55)
                    pygame.draw.rect(screen, (40, 20, 25), (880, w_box_y, 290, 48), border_radius=4)
                    pygame.draw.rect(screen, (140, 40, 50), (880, w_box_y, 290, 48), 1, border_radius=4)

                    wp_name = PROVINCES[w["target_prov"]]["name"]
                    w_title = font_sm.render(f"Siege of {wp_name}: {w['siege_progress']}%", True, COLOR_TEXT_WHITE)
                    screen.blit(w_title, (890, w_box_y + 6))

                    # Siege Progress bar
                    pygame.draw.rect(screen, (20, 20, 20), (890, w_box_y + 28, 270, 10), border_radius=4)
                    pw = int((w["siege_progress"] / 100) * 270)
                    pygame.draw.rect(screen, COLOR_TEXT_RED, (890, w_box_y + 28, pw, 10), border_radius=4)

        # ---------------------------------------------------------
        # 5. POP-UP EVENT DIALOG (CK2 DRAMA MODAL)
        # ---------------------------------------------------------
        if state.active_event:
            # Dim background
            dim_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            dim_surf.fill((0, 0, 0, 175))
            screen.blit(dim_surf, (0, 0))

            # Modal Window
            modal_rect = pygame.Rect((WINDOW_WIDTH - 540) // 2, (WINDOW_HEIGHT - 340) // 2, 540, 320)
            pygame.draw.rect(screen, COLOR_PANEL_BG, modal_rect, border_radius=8)
            pygame.draw.rect(screen, COLOR_GOLD, modal_rect, 2, border_radius=8)

            # Title
            ev_title = font_title.render(state.active_event["title"], True, COLOR_GOLD)
            screen.blit(ev_title, (modal_rect.x + 25, modal_rect.y + 22))

            pygame.draw.line(screen, COLOR_PANEL_BORDER, (modal_rect.x + 25, modal_rect.y + 62), (modal_rect.x + modal_rect.width - 25, modal_rect.y + 62), 1)

            # Description (Multi-line)
            desc_text = state.active_event["desc"]
            ev_desc = font_md.render(desc_text, True, COLOR_TEXT_WHITE)
            screen.blit(ev_desc, (modal_rect.x + 25, modal_rect.y + 80))

            # Option Buttons
            for opt_idx, opt in enumerate(state.active_event["options"]):
                btn_y = modal_rect.y + 160 + (opt_idx * 65)
                btn_rect = pygame.Rect(modal_rect.x + 25, btn_y, modal_rect.width - 50, 48)
                b_hover = btn_rect.collidepoint(mouse_pos)

                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if b_hover else COLOR_BUTTON_NORMAL, btn_rect, border_radius=6)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_rect, 1, border_radius=6)

                opt_surf = font_sm.render(opt["text"], True, COLOR_GOLD if b_hover else COLOR_TEXT_WHITE)
                screen.blit(opt_surf, (btn_rect.x + 15, btn_rect.y + 14))

                if mouse_clicked and b_hover:
                    # Execute option effect
                    opt["effect"]()
                    state.active_event = None
                    break

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_game()
