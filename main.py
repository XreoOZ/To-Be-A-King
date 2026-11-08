"""
CK2-Lite: Britain AD 867 (Simplified 2-Kingdom Campaign)
Kingdom of Wessex (Saxons) vs The Danelaw (Vikings)

Features:
- Single continuous Britain island landmass
- Exactly 2 Rival Kingdoms: King Alfred vs Jarl Halfdan
- Territory Control Bar (e.g. 6 vs 6 provinces)
- Real-time conquest war and siege mechanics
- No annoying pop-up event interruptions
- Standalone Windows .exe ready
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

# Set display mode immediately
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("CK2-Lite: Britain AD 867 - Wessex vs Danelaw")

# Palette
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
# Game State
# -------------------------------------------------------------
class GameState:
    def __init__(self):
        self.player_id = "char_alfred"
        self.enemy_id = "char_halfdan"
        self.selected_province = "wessex"
        self.hovered_province = None
        
        # Calendar: Start 1 January 867 AD
        self.year = 867
        self.month = 1
        self.day = 1
        self.months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        self.month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Speed: 0 = Pause, 1 = Normal (1 day/sec), 2 = Fast, 3 = Super Fast
        self.speed = 1
        self.tick_timer = 0
        
        # Active War List: {"attacker": char_id, "defender": char_id, "target_prov": prov_id, "siege_progress": int}
        self.active_wars = []
        
        # AI decision timer (in days)
        self.ai_timer = 45
        
        # Silent Chronicle Log (No popups)
        self.logs = [
            "AD 867: King Alfred stands against the Great Heathen Army.",
            "Objective: Conquer all 12 provinces to unite Britain!"
        ]

    @property
    def player(self):
        return CHARACTERS[self.player_id]

    @property
    def enemy(self):
        return CHARACTERS[self.enemy_id]

    def get_provinces_count(self, char_id):
        return sum(1 for p in PROVINCES.values() if p["owner"] == char_id)

    def get_total_troops(self, char_id):
        return sum(p["levies_current"] for p in PROVINCES.values() if p["owner"] == char_id)

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

        # Update Wars / Sieges
        self.update_wars()

        # AI Behavior
        self.ai_timer -= 1
        if self.ai_timer <= 0:
            self.ai_timer = random.randint(40, 70)
            self.ai_take_action()

    def monthly_tick(self):
        # Tax collection and levy reinforcements for both sides
        for prov in PROVINCES.values():
            owner = CHARACTERS.get(prov["owner"])
            if owner:
                owner["gold"] += prov["tax"]
                if prov["levies_current"] < prov["levies_max"]:
                    prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + 60)
        
        self.player["prestige"] += 1
        self.player["piety"] += 1
        self.enemy["prestige"] += 1

    def yearly_tick(self):
        self.player["age"] += 1
        self.enemy["age"] += 1
        self.logs.append(f"AD {self.year}: The fierce war for Britain continues.")

    def declare_war(self, target_prov_id):
        prov = PROVINCES[target_prov_id]
        if prov["owner"] == self.player_id:
            return
        
        # Check if already besieging this province
        for war in self.active_wars:
            if war["target_prov"] == target_prov_id:
                return

        war = {
            "attacker": self.player_id,
            "defender": self.enemy_id,
            "target_prov": target_prov_id,
            "siege_progress": 0,
            "days_elapsed": 0
        }
        self.active_wars.append(war)
        self.logs.append(f"Wessex launched siege on {prov['name']}!")

    def ai_take_action(self):
        # If already in a war, don't start another
        ai_wars = [w for w in self.active_wars if w["attacker"] == self.enemy_id]
        if ai_wars:
            return

        # Target a random player province
        player_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == self.player_id]
        if player_provs and random.random() < 0.6:
            target = random.choice(player_provs)
            war = {
                "attacker": self.enemy_id,
                "defender": self.player_id,
                "target_prov": target,
                "siege_progress": 0,
                "days_elapsed": 0
            }
            self.active_wars.append(war)
            self.logs.append(f"Warning! Halfdan has launched an attack on {PROVINCES[target]['name']}!")

    def update_wars(self):
        completed_wars = []
        for war in self.active_wars:
            war["days_elapsed"] += 1
            prov = PROVINCES[war["target_prov"]]
            atk_char = CHARACTERS[war["attacker"]]
            def_char = CHARACTERS[war["defender"]]

            atk_martial = atk_char["stats"]["martial"]
            def_martial = def_char["stats"]["martial"]

            # Advance siege progress every 3 days
            if war["days_elapsed"] % 3 == 0:
                roll = random.randint(1, 10) + (atk_martial - def_martial) // 3
                if roll > 3:
                    war["siege_progress"] += 14
                    prov["levies_current"] = max(0, prov["levies_current"] - 140)
                else:
                    war["siege_progress"] += 6

            if war["siege_progress"] >= 100 or prov["levies_current"] <= 0:
                # Victory for attacker
                prov["owner"] = war["attacker"]
                prov["color"] = list(COLOR_WESSEX if war["attacker"] == self.player_id else COLOR_DANELAW)
                atk_char["prestige"] += 80
                
                if war["attacker"] == self.player_id:
                    self.logs.append(f"Victory! {prov['name']} has been conquered for Wessex!")
                else:
                    self.logs.append(f"Loss! {prov['name']} has fallen to the Danelaw!")

                completed_wars.append(war)

        for w in completed_wars:
            self.active_wars.remove(w)

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

    # Province name labels on map
    label_positions = {
        "highlands": (map_origin_x + 185, map_origin_y + 80),
        "strathclyde": (map_origin_x + 175, map_origin_y + 195),
        "lothian": (map_origin_x + 245, map_origin_y + 195),
        "bernicia": (map_origin_x + 255, map_origin_y + 245),
        "deira": (map_origin_x + 265, map_origin_y + 295),
        "jorvik": (map_origin_x + 250, map_origin_y + 325),
        "wales": (map_origin_x + 180, map_origin_y + 395),
        "mercia": (map_origin_x + 270, map_origin_y + 395),
        "east_anglia": (map_origin_x + 360, map_origin_y + 440),
        "wessex": (map_origin_x + 225, map_origin_y + 515),
        "kent_essex": (map_origin_x + 330, map_origin_y + 500),
        "cornwall": (map_origin_x + 130, map_origin_y + 535)
    }

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

        # Time advancement (Smooth, no popup interruptions)
        if state.speed > 0:
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

        # Title / Campaign Name
        t_surf = font_lg.render("CK2: THE WAR FOR BRITAIN", True, COLOR_GOLD)
        screen.blit(t_surf, (20, 12))

        # Calendar Date
        date_str = f"{state.day:02d} {state.months[state.month - 1]} {state.year} AD"
        d_surf = font_md.render(date_str, True, COLOR_TEXT_WHITE)
        screen.blit(d_surf, (350, 15))

        # Speed Controls
        speeds = [(0, icon_speed_pause), (1, icon_speed_play), (2, icon_speed_fast)]
        for i, (sp, icon) in enumerate(speeds):
            btn_x = 485 + (i * 36)
            btn_rect = pygame.Rect(btn_x, 10, 32, 32)
            is_active = (state.speed == sp)
            b_col = COLOR_BUTTON_ACTIVE if is_active else (COLOR_BUTTON_HOVER if btn_rect.collidepoint(mouse_pos) else COLOR_BUTTON_NORMAL)
            pygame.draw.rect(screen, b_col, btn_rect, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, btn_rect, 1, border_radius=4)
            screen.blit(icon, (btn_x + 4, 14))
            if mouse_clicked and btn_rect.collidepoint(mouse_pos):
                state.speed = sp

        # Player Stats (Gold, Prestige, Piety, Total Levies)
        stats_x = 640
        stats = [
            (icon_gold, str(state.player["gold"]), COLOR_GOLD),
            (icon_prestige, str(state.player["prestige"]), COLOR_PRESTIGE),
            (icon_piety, str(state.player["piety"]), COLOR_PIETY),
            (icon_troops, f"{state.get_total_troops(state.player_id):,}", COLOR_TEXT_WHITE)
        ]
        for icon, val_str, col in stats:
            screen.blit(icon, (stats_x, 14))
            v_surf = font_md.render(val_str, True, col)
            screen.blit(v_surf, (stats_x + 28, 15))
            stats_x += 120

        # ---------------------------------------------------------
        # 2. LEFT PANEL: PLAYER RULER (ALFRED THE GREAT)
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
        dynasty_surf = font_sm.render(f"Dynasty: {state.player['dynasty']}", True, COLOR_TEXT_MUTED)
        age_surf = font_sm.render(f"Age: {state.player['age']} years old", True, COLOR_TEXT_MUTED)

        screen.blit(name_surf, (115, 75))
        screen.blit(title_surf, (115, 96))
        screen.blit(dynasty_surf, (115, 116))
        screen.blit(age_surf, (115, 134))

        # Attributes Table
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 172), (285, 172), 1)
        st_title = font_md.render("Royal Attributes", True, COLOR_GOLD)
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

            # Stat Bar
            pygame.draw.rect(screen, (40, 45, 58), (145, row_y + 4, 130, 8), border_radius=3)
            fill_w = min(130, int((val / 20) * 130))
            pygame.draw.rect(screen, bar_col, (145, row_y + 4, fill_w, 8), border_radius=3)

        # Traits
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 345), (285, 345), 1)
        tr_title = font_md.render("Traits", True, COLOR_GOLD)
        screen.blit(tr_title, (25, 355))

        for tidx, trait in enumerate(state.player["traits"]):
            tx = 25 + ((tidx % 2) * 135)
            ty = 380 + ((tidx // 2) * 28)
            t_box = pygame.Rect(tx, ty, 125, 24)
            pygame.draw.rect(screen, COLOR_BUTTON_NORMAL, t_box, border_radius=4)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, t_box, 1, border_radius=4)
            tt_surf = font_sm.render(trait, True, COLOR_TEXT_WHITE)
            screen.blit(tt_surf, (t_box.x + 8, t_box.y + 3))

        # Chronicle Logs (Uninterrupted)
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (25, 450), (285, 450), 1)
        log_title = font_md.render("Chronicle of Britain", True, COLOR_GOLD)
        screen.blit(log_title, (25, 460))

        log_y = 490
        for log_msg in state.logs[-7:]:
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
        
        # Draw balance bar
        pygame.draw.rect(screen, (25, 30, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        wessex_pixel_w = int((wessex_count / total_provs) * bar_w)
        pygame.draw.rect(screen, COLOR_WESSEX, (bar_x, bar_y, wessex_pixel_w, bar_h), border_radius=4)
        pygame.draw.rect(screen, COLOR_DANELAW, (bar_x + wessex_pixel_w, bar_y, bar_w - wessex_pixel_w, bar_h), border_radius=4)
        pygame.draw.rect(screen, COLOR_PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)

        # Bar Labels
        w_lbl = font_sm.render(f"WESSEX: {wessex_count}", True, (255, 230, 230))
        d_lbl = font_sm.render(f"DANELAW: {danelaw_count}", True, (230, 240, 255))
        screen.blit(w_lbl, (bar_x + 10, bar_y + 3))
        screen.blit(d_lbl, (bar_x + bar_w - d_lbl.get_width() - 10, bar_y + 3))

        state.hovered_province = None

        # Draw mainland Britain tiles
        for r, row in enumerate(raw_grid):
            for c, ch in enumerate(row):
                cell_x = map_origin_x + (c * tile_w)
                cell_y = map_origin_y + 45 + (r * tile_h)
                cell_rect = pygame.Rect(cell_x, cell_y, tile_w, tile_h)

                if ch == ".":
                    if (r + c) % 7 == 0:
                        pygame.draw.line(screen, (28, 48, 76), (cell_x + 4, cell_y + 12), (cell_x + 12, cell_y + 12))
                else:
                    prov_id = cell_to_prov.get((c, r))
                    prov_info = PROVINCES.get(prov_id)
                    col = prov_info["color"] if prov_info else (150, 150, 150)

                    is_hovered = cell_rect.collidepoint(mouse_pos)
                    is_selected = (prov_id == state.selected_province)

                    if is_hovered:
                        state.hovered_province = prov_id
                        col = (min(255, col[0] + 45), min(255, col[1] + 45), min(255, col[2] + 45))

                    pygame.draw.rect(screen, col, (cell_x, cell_y, tile_w - 1, tile_h - 1))

                    if is_selected:
                        pygame.draw.rect(screen, COLOR_GOLD, (cell_x - 1, cell_y - 1, tile_w + 1, tile_h + 1), 2)
                    else:
                        pygame.draw.line(screen, (min(255, col[0] + 25), min(255, col[1] + 25), min(255, col[2] + 25)), (cell_x, cell_y), (cell_x + tile_w - 2, cell_y))
                        pygame.draw.line(screen, (max(0, col[0] - 25), max(0, col[1] - 25), max(0, col[2] - 25)), (cell_x, cell_y + tile_h - 2), (cell_x + tile_w - 2, cell_y + tile_h - 2))

                    if mouse_clicked and is_hovered:
                        state.selected_province = prov_id

        # Province Name Labels
        for pid, (lx, ly) in label_positions.items():
            p_data = PROVINCES.get(pid)
            if p_data:
                short_name = p_data["name"].split()[0]
                lbl_surf = font_sm.render(short_name, True, (245, 245, 245))
                sh_surf = font_sm.render(short_name, True, (10, 15, 25))
                screen.blit(sh_surf, (lx + 1, ly + 1))
                screen.blit(lbl_surf, (lx, ly))

        # Victory / Defeat Check
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
        # 4. RIGHT PANEL: SELECTED PROVINCE & CAMPAIGN ACTIONS
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
            screen.blit(font_md.render("Controlled by:", True, COLOR_TEXT_WHITE), (880, 145))
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
            screen.blit(font_md.render("Province Resources", True, COLOR_GOLD), (880, 252))

            screen.blit(icon_gold, (880, 285))
            screen.blit(font_sm.render(f"Monthly Tax Revenue: +{sel_prov['tax']} Gold", True, COLOR_TEXT_WHITE), (915, 288))

            screen.blit(icon_troops, (880, 320))
            screen.blit(font_sm.render(f"Levies / Garrison: {sel_prov['levies_current']} / {sel_prov['levies_max']}", True, COLOR_TEXT_WHITE), (915, 323))

            # Actions
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 365), (1170, 365), 1)
            screen.blit(font_md.render("Command Orders", True, COLOR_GOLD), (880, 375))

            if is_player_owned:
                # Develop Lands Button
                imp_btn = pygame.Rect(880, 415, 290, 42)
                b_hover = imp_btn.collidepoint(mouse_pos)
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if b_hover else COLOR_BUTTON_NORMAL, imp_btn, border_radius=6)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, imp_btn, 1, border_radius=6)
                
                ib_text = font_md.render("Develop Lands (-50 Gold, +4 Tax)", True, COLOR_GOLD)
                screen.blit(ib_text, (895, 426))

                if mouse_clicked and b_hover:
                    if state.player["gold"] >= 50:
                        state.player["gold"] -= 50
                        sel_prov["tax"] += 4
                        sel_prov["levies_max"] += 250
                        state.logs.append(f"Developed lands in {sel_prov['name']}!")
                    else:
                        state.logs.append("Need 50 Gold to develop lands!")
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
                    pygame.draw.rect(screen, (170, 40, 40) if b_hover else (130, 30, 30), war_btn, border_radius=6)
                    pygame.draw.rect(screen, (230, 70, 70), war_btn, 1, border_radius=6)
                    
                    wb_text = font_md.render("DECLARE CONQUEST SIEGE", True, (255, 240, 240))
                    screen.blit(wb_text, (910, 426))

                    if mouse_clicked and b_hover:
                        state.declare_war(state.selected_province)

            # Active Sieges List
            if state.active_wars:
                pygame.draw.line(screen, COLOR_PANEL_BORDER, (880, 480), (1170, 480), 1)
                screen.blit(font_md.render("Active Campaigns", True, COLOR_TEXT_RED), (880, 492))
                
                for widx, w in enumerate(state.active_wars):
                    w_box_y = 525 + (widx * 55)
                    pygame.draw.rect(screen, (40, 20, 25), (880, w_box_y, 290, 48), border_radius=4)
                    pygame.draw.rect(screen, (140, 40, 50), (880, w_box_y, 290, 48), 1, border_radius=4)

                    wp_name = PROVINCES[w["target_prov"]]["name"].split()[0]
                    atk_name = "Wessex" if w["attacker"] == state.player_id else "Danelaw"
                    w_title = font_sm.render(f"{atk_name} Siege of {wp_name}: {w['siege_progress']}%", True, COLOR_TEXT_WHITE)
                    screen.blit(w_title, (890, w_box_y + 6))

                    # Siege Bar
                    pygame.draw.rect(screen, (20, 20, 20), (890, w_box_y + 28, 270, 10), border_radius=4)
                    pw = int((w["siege_progress"] / 100) * 270)
                    pygame.draw.rect(screen, COLOR_TEXT_RED if w["attacker"] == state.player_id else (80, 120, 180), (890, w_box_y + 28, pw, 10), border_radius=4)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_game()
