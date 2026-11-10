"""
Master GameState Engine and Simulation Loop
"""
import random
import math
import copy

from game.config import DAYS_PER_TILE, DAYS_PER_KOTAK, LEVY_RAISE_COOLDOWN_DAYS, COLOR_WESSEX, COLOR_DANELAW
from game.data.characters import CHARACTERS, INITIAL_CHARACTERS
from game.data.provinces import PROVINCES, INITIAL_PROVINCES, PROVINCE_FACTION_COLORS, ADJACENCY, find_shortest_path, reset_global_world_data
from game.data.buildings import BUILDING_SPECS, get_barrack_stats
from game.core.map import CELL_TO_PROV, PROV_TO_TILES, PROV_CAPITAL_TILES, get_province_capital_tile, find_shortest_tile_path, TILE_ADJACENCY
from game.core.army import Army
from game.systems.economy import (
    sync_province_holdings_stats,
    get_vassal_landed_status,
    get_province_holdings,
    get_all_settlement_holdings
)
from game.systems.military import get_siegeable_holdings, is_province_contested
from game.systems.ai import standardize_enemy_ai_laws, run_viking_ai, run_realm_ai

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
        self.player_raise_cooldown = 0   # in days (3 months / 90 days cooldown)
        self.enemy_raise_cooldown = 0    # in days (3 months / 90 days cooldown)
        
        # Royal Capital & Realm Seats
        self.player_capital = "wessex"
        self.player_primary_capital = "wessex"
        self.player_capital_was_lost = False
        
        self.enemy_capital = "jorvik"
        self.enemy_primary_capital = "jorvik"
        self.enemy_capital_was_lost = False

        # Feudal Suzerainty & Dynamic Vassalage (No hard Defeat / Win!)
        self.player_liege = None         # "char_halfdan" if Alfred is vassalized
        self.enemy_liege = None          # "char_alfred" if Halfdan is vassalized
        self.war_status = "war"          # "war" or "vassalage"
        self.subjugation_event = None    # Feudal treaty story modal event
        
        # AI decision timer
        self.ai_timer = 1
        
        # Chronicle Logs
        self.logs = [
            "AD 867: Britain stands divided between Saxons and Vikings.",
            "Raise your levies from the provinces, assemble your army, and march!"
        ]
        
        # Generate random 1-5 vassals for all provinces
        self.generate_province_vassals()

    def reset(self):
        """Reinitialize entire game state and 1:1 starter cities matching vassals in-place."""
        reset_global_world_data()
        self.__init__()
        setup_province_starter_cities(self)
        self.logs.append("Game reset to 1 January 867 AD! Vassals & cities synchronized.")

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
                    "gold": random.randint(20, 50),
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

    def get_realm_capital(self, owner_id):
        """
        Returns the active capital province ID for the given realm owner.
        Handles emergency capital relocation if capital is captured,
        and restoration when liberated.
        """
        if owner_id == self.player_id:
            pri = self.player_primary_capital
            if PROVINCES.get(pri, {}).get("owner") == self.player_id:
                if self.player_capital_was_lost:
                    self.player_capital_was_lost = False
                    self.player_capital = pri
                    if self.player_id in CHARACTERS:
                        CHARACTERS[self.player_id]["province"] = pri
                    p_name = PROVINCES[pri]["name"]
                    self.logs.append(f"Royal Triumph! The Royal Seat has been restored to {p_name}!")
                return pri

            owned = [pid for pid, p in PROVINCES.items() if p.get("owner") == self.player_id]
            if not owned:
                return pri

            if self.player_capital in owned and self.player_capital != pri:
                return self.player_capital

            sorted_owned = sorted(owned, key=lambda p: (PROVINCES[p].get("levies_max", 0), len(PROVINCES[p].get("tiles", []))), reverse=True)
            new_cap = sorted_owned[0]
            self.player_capital = new_cap
            if self.player_id in CHARACTERS:
                CHARACTERS[self.player_id]["province"] = new_cap
            if not self.player_capital_was_lost:
                self.player_capital_was_lost = True
                p_old = PROVINCES.get(pri, {}).get("name", pri.capitalize())
                p_new = PROVINCES[new_cap]["name"]
                self.logs.append(f"Catastrophe! {p_old} has fallen! King Alfred flees and establishes emergency royal capital in {p_new}!")
            return new_cap

        elif owner_id == self.enemy_id:
            pri = self.enemy_primary_capital
            if PROVINCES.get(pri, {}).get("owner") == self.enemy_id:
                if self.enemy_capital_was_lost:
                    self.enemy_capital_was_lost = False
                    self.enemy_capital = pri
                    if self.enemy_id in CHARACTERS:
                        CHARACTERS[self.enemy_id]["province"] = pri
                    p_name = PROVINCES[pri]["name"]
                    self.logs.append(f"Seat of Power Restored! Jarl Halfdan has returned the Danelaw Royal Seat to {p_name}!")
                return pri

            owned = [pid for pid, p in PROVINCES.items() if p.get("owner") == self.enemy_id]
            if not owned:
                return pri

            if self.enemy_capital in owned and self.enemy_capital != pri:
                return self.enemy_capital

            sorted_owned = sorted(owned, key=lambda p: (PROVINCES[p].get("levies_max", 0), len(PROVINCES[p].get("tiles", []))), reverse=True)
            new_cap = sorted_owned[0]
            self.enemy_capital = new_cap
            if self.enemy_id in CHARACTERS:
                CHARACTERS[self.enemy_id]["province"] = new_cap
            if not self.enemy_capital_was_lost:
                self.enemy_capital_was_lost = True
                p_old = PROVINCES.get(pri, {}).get("name", pri.capitalize())
                p_new = PROVINCES[new_cap]["name"]
                self.logs.append(f"War Emergency! {p_old} has fallen! Jarl Halfdan establishes emergency war capital in {p_new}! War summons depart from here.")
            return new_cap

        return "wessex"

    def set_player_capital(self, province_id):
        """Allows the player to move their Royal Capital to any owned province."""
        if province_id not in PROVINCES:
            return False
        if PROVINCES[province_id].get("owner") != self.player_id:
            self.logs.append(f"Cannot relocate capital: {PROVINCES[province_id]['name']} is not under your control!")
            return False
        curr_cap = self.get_realm_capital(self.player_id)
        if province_id == curr_cap:
            self.logs.append(f"{PROVINCES[province_id]['name']} is already your royal capital.")
            return False

        self.player_primary_capital = province_id
        self.player_capital = province_id
        self.player_capital_was_lost = False
        if self.player_id in CHARACTERS:
            CHARACTERS[self.player_id]["province"] = province_id
        p_name = PROVINCES[province_id]["name"]
        self.logs.append(f"Royal Decree: King Alfred relocates the Realm Capital to {p_name}! Royal couriers and war summons will now depart from {p_name}.")
        return True

    # ---------------------------------------------------------
    # Feudal Subjugation & Dynamic Vassalage System
    # (No hard defeat / win conditions; living feudal hierarchy)
    # ---------------------------------------------------------
    def check_subjugation_and_vassalage(self):
        """
        Evaluates territorial control for feudal submission:
        - If Wessex loses all provinces: Alfred bends the knee as Duke of Wessex under High King Halfdan.
        - If Danelaw loses all provinces: Halfdan bends the knee as Jarl of Jorvik under High King Alfred.
        """
        player_provs = [pid for pid, p in PROVINCES.items() if p.get("owner") == self.player_id]
        enemy_provs = [pid for pid, p in PROVINCES.items() if p.get("owner") == self.enemy_id]

        if len(player_provs) == 0 and self.player_liege is None:
            self.trigger_player_subjugation_to_danelaw()
        elif len(enemy_provs) == 0 and self.enemy_liege is None:
            self.trigger_danelaw_subjugation_to_player()

    def trigger_player_subjugation_to_danelaw(self):
        """King Alfred yields to Halfdan and bends the knee, becoming Duke of Wessex."""
        self.player_liege = self.enemy_id
        self.enemy_liege = None
        self.war_status = "vassalage"

        CHARACTERS[self.player_id]["realm"] = "Duchy of Wessex (Vassal to Danelaw)"
        CHARACTERS[self.player_id]["title"] = "Duke of Wessex & Vassal of York"
        CHARACTERS[self.enemy_id]["realm"] = "The Danelaw (High Kingdom of Britain)"
        CHARACTERS[self.enemy_id]["title"] = "High King of the Danelaw & All Britain"

        # Restore ancestral seat of Wessex as Alfred's hereditary vassal duchy
        PROVINCES["wessex"]["owner"] = self.player_id
        PROVINCES["wessex"]["color"] = list(PROVINCE_FACTION_COLORS.get(self.player_id, {}).get("wessex", COLOR_WESSEX))
        PROVINCES["wessex"]["levies_current"] = min(PROVINCES["wessex"].get("levies_max", 500), 250)
        self.player_capital = "wessex"
        self.player_primary_capital = "wessex"
        self.player_capital_was_lost = False

        # Clear enemy occupation in Wessex
        for t, s in self.settlements.items():
            if s.get("province") == "wessex":
                s["occupied_by"] = None

        # Stand down wartime offensive armies
        for a in list(self.armies):
            if a.owner == self.player_id:
                self.disband_army(a)
            elif a.owner == self.enemy_id and (a.province == "wessex" or a.is_sieging):
                self.disband_army(a)

        self.subjugation_event = {
            "type": "player_vassalized",
            "title": "TREATY OF SUBMISSION: BENDING THE KNEE",
            "liege_name": "High King Halfdan Ragnarsson",
            "vassal_name": "Duke Alfred of Wessex",
            "text_lines": [
                "All Saxon resistance across Britain has broken before the Great Heathen Army.",
                "Yet King Alfred survives! Meeting High King Halfdan at the Stone of Fealty,",
                "Alfred places his hands between Halfdan's and swears the ancient Oath of Vassalage.",
                "",
                "Halfdan confirms Wessex as your hereditary vassal duchy. You must pay 20% feudal",
                "tax to York every month, but your court, your laws, and your dynasty endure.",
                "",
                "Bide your time, enrich your baronies, muster a secret host, and when",
                "the Vikings are vulnerable—DECLARE REBELLION and reclaim the High Crown!"
            ],
            "button_text": "ACCEPT VASSALAGE & BIDE TIME"
        }
        self.logs.append("FEUDAL SUBMISSION: King Alfred has bent the knee to High King Halfdan. Wessex is now a vassal duchy under the Danelaw.")

    def trigger_danelaw_subjugation_to_player(self):
        """Halfdan yields to Alfred and bends the knee, becoming Jarl of Jorvik."""
        self.enemy_liege = self.player_id
        self.player_liege = None
        self.war_status = "vassalage"

        CHARACTERS[self.player_id]["realm"] = "High Kingdom of All Britain"
        CHARACTERS[self.player_id]["title"] = "High King Alfred 'the Great' (Bretwalda)"
        CHARACTERS[self.enemy_id]["realm"] = "Jarlhood of Jorvik (Vassal of Wessex)"
        CHARACTERS[self.enemy_id]["title"] = "Jarl of Jorvik & Northern Marcher Lord"

        # Restore Jorvik as Halfdan's hereditary vassal fiefdom
        PROVINCES["jorvik"]["owner"] = self.enemy_id
        PROVINCES["jorvik"]["color"] = list(PROVINCE_FACTION_COLORS.get(self.enemy_id, {}).get("jorvik", COLOR_DANELAW))
        PROVINCES["jorvik"]["levies_current"] = min(PROVINCES["jorvik"].get("levies_max", 500), 250)
        self.enemy_capital = "jorvik"
        self.enemy_primary_capital = "jorvik"
        self.enemy_capital_was_lost = False

        # Clear enemy occupation in Jorvik
        for t, s in self.settlements.items():
            if s.get("province") == "jorvik":
                s["occupied_by"] = None

        # Stand down enemy armies
        for a in list(self.armies):
            if a.owner == self.enemy_id:
                self.disband_army(a)

        self.subjugation_event = {
            "type": "enemy_vassalized",
            "title": "TREATY OF WEDMORE: DANELAW SUBMISSION",
            "liege_name": "High King Alfred 'the Great'",
            "vassal_name": "Jarl Halfdan Ragnarsson",
            "text_lines": [
                "The Viking conquerors have been utterly crushed across the length of Britain!",
                "Jarl Halfdan Ragnarsson surrenders his raven war banner and kneels before Alfred.",
                "",
                "Under the historic Treaty of Wedmore, Halfdan accepts Christian baptism and swears",
                "solemn fealty to the Saxon Crown as your vassal Jarl in Jorvik.",
                "",
                "All 12 shires of Britain now acknowledge King Alfred as High King (Bretwalda)!",
                "Halfdan now pays 20% feudal tribute to Winchester and his warriors stand ready",
                "to serve as Viking auxilia in your royal host."
            ],
            "button_text": "RULE THE UNITED REALM"
        }
        self.logs.append("DANELAW SUBMISSION: Halfdan has bent the knee! Danelaw has accepted Saxon suzerainty. Alfred is High King of All Britain!")

    def declare_independence(self):
        """Duke Alfred casts off the Viking yoke and declares War of Independence!"""
        if self.player_liege != self.enemy_id:
            return
        self.player_liege = None
        self.war_status = "war"
        CHARACTERS[self.player_id]["realm"] = "Kingdom of Wessex"
        CHARACTERS[self.player_id]["title"] = "King of Wessex & the Anglo-Saxons"
        self.ai_timer = 0
        self.logs.append("⚔ WAR OF INDEPENDENCE! Duke Alfred casts off the Viking yoke and declares Sovereign Independence! Saxon war horns sound across Wessex!")

    # ---------------------------------------------------------
    # Army Operations
    # ---------------------------------------------------------
    def is_province_levy_in_field(self, province_id, owner_id=None):
        """Checks if a province's levies are currently deployed in the field (active host or sub-flag)."""
        if owner_id is None:
            prov = PROVINCES.get(province_id)
            if not prov:
                return False
            owner_id = prov.get("owner")
        for a in self.armies:
            if a.owner == owner_id and a.troops > 0:
                if a.flag_origin == province_id or (getattr(a, "sub_flags", None) and province_id in a.sub_flags):
                    return True
        return False

    def raise_province_levy(self, province_id):
        prov = PROVINCES.get(province_id)
        if not prov or prov["owner"] != self.player_id:
            return
        
        # Anti-exploit: Feudal vassal levies cannot be re-raised while already active in the field!
        if self.is_province_levy_in_field(province_id, prov["owner"]):
            p_short = prov["name"].split()[0]
            self.logs.append(f"Cannot muster {p_short}! Levies already deployed in the field. Disband active host first.")
            return

        # 3-Month Cooldown Check
        cd = prov.get("raise_cooldown_days", 0)
        if cd > 0:
            m_left = (cd + 29) // 30
            self.logs.append(f"Muster Cooldown! {prov['name']} cannot raise levies for {cd}d (~{m_left}m)!")
            return

        available = prov["levies_current"]
        if available <= 0:
            self.logs.append(f"No levies available to raise in {prov['name']}.")
            return

        army_id = f"army_{self.army_id_counter}"
        self.army_id_counter += 1
        
        army_name = f"{prov['name'].split()[0]} Fyrd"
        capital_pid = self.get_realm_capital(self.player_id)
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
                cap_short = PROVINCES[capital_pid]["name"].split()[0]
                self.logs.append(f"Royal Courier dispatched from {cap_short} to {p_short} ({hops} shires away, {total_days}d ride)! 30d muster begins upon arrival.")
            else:
                new_army.is_mustering = True
                new_army.muster_days = 30
                new_army.courier_en_route = False
                self.logs.append(f"Summoned {available:,} men in {prov['name']}! Mustering troops (30 days)...")

        self.armies.append(new_army)
        prov["levies_current"] = 0
        prov["raise_cooldown_days"] = LEVY_RAISE_COOLDOWN_DAYS
        self.player_raise_cooldown = max(self.player_raise_cooldown, LEVY_RAISE_COOLDOWN_DAYS)
        self.selected_army_id = army_id

    def raise_all_levies(self):
        if self.player_raise_cooldown > 0:
            m_left = (self.player_raise_cooldown + 29) // 30
            self.logs.append(f"Realm Muster Cooldown! Must wait {self.player_raise_cooldown}d (~{m_left}m) before raising all levies again!")
            return

        raised_count = 0
        total_men = 0
        capital_pid = self.get_realm_capital(self.player_id)
        courier_count = 0
        for pid, prov in PROVINCES.items():
            if prov["owner"] == self.player_id and prov["levies_current"] > 0 and prov.get("raise_cooldown_days", 0) <= 0:
                if self.is_province_levy_in_field(pid, self.player_id):
                    continue
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
                prov["raise_cooldown_days"] = LEVY_RAISE_COOLDOWN_DAYS
                raised_count += 1
                total_men += available
        
        if raised_count > 0:
            self.player_raise_cooldown = LEVY_RAISE_COOLDOWN_DAYS
            cap_short = PROVINCES[capital_pid]["name"].split()[0]
            if courier_count > 0:
                self.logs.append(f"Royal Couriers dispatched from {cap_short} to {courier_count} shires! ({total_men:,} total men summoned, 30d muster begins as couriers arrive)")
            else:
                self.logs.append(f"Mobilized royal capital levies: {total_men:,} men! (Mustering for 30 days)")
        else:
            in_field = any(self.is_province_levy_in_field(pid, self.player_id) for pid, p in PROVINCES.items() if p["owner"] == self.player_id)
            if in_field:
                self.logs.append("All provincial levies are already deployed in the field! Disband active armies first.")
            else:
                self.logs.append("All available levies are already raised or recovering.")

    def raise_all_realm_levies(self, ruler_id, is_emergency=False):
        """Mobilizes ALL available levies across 100% of a ruler's realm provinces."""
        if ruler_id == self.enemy_id and self.enemy_raise_cooldown > 0:
            return 0, 0

        raised_count = 0
        total_men = 0
        capital_pid = self.get_realm_capital(ruler_id)
        realm_provs = [pid for pid, p in PROVINCES.items() if p["owner"] == ruler_id]
        has_field = any(a.owner == ruler_id for a in self.armies)
        min_to_raise = 25 if (is_emergency or not has_field) else 50

        ruler = CHARACTERS.get(ruler_id, {})
        r_name = ruler.get("name", "Ruler").split()[0]
        realm_name = ruler.get("realm", "the realm")

        for pid in realm_provs:
            prov = PROVINCES[pid]
            if prov.get("raise_cooldown_days", 0) > 0:
                continue
            if self.is_province_levy_in_field(pid, ruler_id):
                continue
            available = prov.get("levies_current", 0)
            if available >= min_to_raise:
                army_id = f"army_{self.army_id_counter}"
                self.army_id_counter += 1
                p_short = prov["name"].split()[0]
                army_name = f"{p_short} Host"
                is_royal = (pid == capital_pid)
                new_army = Army(army_id, ruler_id, pid, available, army_name,
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
                
                m_days = 15 if is_emergency else 30
                if is_royal:
                    new_army.is_mustering = True
                    new_army.muster_days = m_days
                    new_army.courier_en_route = False
                else:
                    full_route = find_shortest_path(capital_pid, pid)
                    if full_route and len(full_route) > 1:
                        hops = len(full_route) - 1
                        total_days = max(1, hops * 2) if is_emergency else (hops * DAYS_PER_TILE)
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
                prov["raise_cooldown_days"] = LEVY_RAISE_COOLDOWN_DAYS
                raised_count += 1
                total_men += available
        if raised_count > 0:
            if ruler_id == self.enemy_id:
                self.enemy_raise_cooldown = LEVY_RAISE_COOLDOWN_DAYS
            cap_short = PROVINCES[capital_pid]["name"].split()[0] if capital_pid in PROVINCES else "Capital"
            self.logs.append(f"War Summons! {r_name} mobilizes {total_men:,} warriors across {realm_name} (Couriers dispatch from {cap_short})!")
        return raised_count, total_men

    def raise_all_enemy_levies(self, is_emergency=False):
        return self.raise_all_realm_levies(self.enemy_id, is_emergency=is_emergency)

    def rally_all_armies_to(self, target_province_id):
        player_armies = [a for a in self.armies if a.owner == self.player_id]
        if not player_armies:
            self.logs.append("No active armies to rally! Raise levies first.")
            return

        target_tile = get_province_capital_tile(target_province_id)
        rallied = 0
        for a in player_armies:
            if getattr(a, "tile", None) != target_tile and not a.in_battle and not a.is_mustering and not a.courier_en_route:
                self.order_army_march_to_tile(a, target_tile)
                rallied += 1
        
        target_name = PROVINCES[target_province_id]["name"]
        self.logs.append(f"Rally orders issued! {len(player_armies)} hosts marching to {target_name} ({target_tile}).")

    def merge_armies_on_tile(self, tile, owner_id):
        armies_here = [a for a in self.armies if getattr(a, "tile", None) == tile and a.owner == owner_id and not a.is_moving and not a.is_demobilizing and not a.is_mustering and not a.courier_en_route]
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
        prov_id = dominant_army.province
        prov_name = PROVINCES.get(prov_id, {}).get("name", "Realm").split()[0]
        dominant_army.name = f"Royal Host of {prov_name}"
        
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
            if a.id in self.selected_army_ids:
                self.selected_army_ids.remove(a.id)
                if dominant_army.id not in self.selected_army_ids:
                    self.selected_army_ids.append(dominant_army.id)
            if a in self.armies:
                self.armies.remove(a)
            
        self.logs.append(f"Combined {len(armies_here)} hosts on tile {tile} under banner of {dominant_army.name} ({total_troops:,} men)!")

    def merge_armies_in_province(self, province_id, owner_id):
        prov_tiles = set(getattr(a, "tile", None) for a in self.armies if a.province == province_id and a.owner == owner_id)
        for t in prov_tiles:
            if t is not None:
                self.merge_armies_on_tile(t, owner_id)

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
                sf_host = Army(new_id, army.owner, army.province, share, f"{p_short} Fyrd", flag_origin=sf, tile=army.tile)
                self.armies.append(sf_host)
                contingents_to_disband.append(sf_host)
                
            army.sub_flags = []
            army.name = f"{PROVINCES[army.flag_origin]['name'].split()[0]} Fyrd"
        
        contingents_to_disband.append(army)

        for host in contingents_to_disband:
            home_cap_tile = get_province_capital_tile(host.flag_origin)
            if host.province == host.flag_origin and getattr(host, "tile", None) == home_cap_tile:
                # Already at home province & capital: instant disband
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
                tile_route = find_shortest_tile_path(host.tile, home_cap_tile)
                if tile_route and len(tile_route) > 1:
                    host.tile_path = tile_route[1:]
                    host.move_progress = 0.0
                    self.logs.append(f"{host.name} demobilizing! ({host.troops:,} men marching home to {PROVINCES[host.flag_origin]['name']}...)")
                else:
                    prov = PROVINCES.get(host.flag_origin)
                    if prov:
                        prov["levies_current"] = min(prov["levies_max"], prov["levies_current"] + host.troops)
                    self.logs.append(f"{host.name} demobilized into garrison of {PROVINCES[host.flag_origin]['name']}.")
                    if host in self.armies:
                        self.armies.remove(host)

    def order_army_march_to_tile(self, army, target_tile):
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
        if getattr(army, "tile", None) == target_tile:
            return
        
        path = find_shortest_tile_path(army.tile, target_tile)
        if path and len(path) > 1:
            army.tile_path = path[1:] # steps to traverse
            army.move_progress = 0.0
            army.is_sieging = False
            t_prov = CELL_TO_PROV.get(target_tile, army.province)
            t_name = PROVINCES.get(t_prov, {}).get("name", "the realm")
            self.logs.append(f"{army.name} marching to tile {target_tile} in {t_name}...")
        else:
            self.logs.append(f"No valid march route from {army.tile} to {target_tile}!")

    def order_army_march(self, army, target_province_id):
        target_tile = get_province_capital_tile(target_province_id)
        self.order_army_march_to_tile(army, target_tile)

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

        # Update Muster Cooldown Timers (3 months / 90 days cooldown)
        self.player_raise_cooldown = max(0, self.player_raise_cooldown - 1)
        self.enemy_raise_cooldown = max(0, self.enemy_raise_cooldown - 1)
        for p in PROVINCES.values():
            if p.get("raise_cooldown_days", 0) > 0:
                p["raise_cooldown_days"] = max(0, p["raise_cooldown_days"] - 1)

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

        # Dynamic Feudal Subjugation check (No game over / defeat screen)
        self.check_subjugation_and_vassalage()

        # AI Behavior (Responsive 2-day tactical cycle)
        self.ai_timer -= 1
        if self.ai_timer <= 0:
            self.ai_timer = 2
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
                        owner["gold"] = round(owner["gold"] + st["tax_paid"], 1)
                        v["gold"] = round(v.get("gold", 25) + st["net_savings"], 1)
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

        # Feudal Suzerainty & Vassalage Tributes
        if getattr(self, "player_liege", None) == self.enemy_id:
            # Player is vassal to Halfdan: pays 20% feudal tribute
            w_tax = PROVINCES.get("wessex", {}).get("tax", 4)
            trib = round(max(1.0, w_tax * 0.20 + 1.5), 1)
            self.player["gold"] = max(0.0, round(self.player["gold"] - trib, 1))
            self.enemy["gold"] = round(self.enemy.get("gold", 100) + trib, 1)
            self.logs.append(f"Paid -{trib}g feudal tribute to Liege High King Halfdan.")
        elif getattr(self, "enemy_liege", None) == self.player_id:
            # Halfdan is vassal to Player: pays 20% feudal tribute
            j_tax = PROVINCES.get("jorvik", {}).get("tax", 4)
            trib = round(max(1.0, j_tax * 0.20 + 1.5), 1)
            self.enemy["gold"] = max(0.0, round(self.enemy.get("gold", 100) - trib, 1))
            self.player["gold"] = round(self.player["gold"] + trib, 1)
            self.logs.append(f"Received +{trib}g feudal tribute from Vassal Jarl Halfdan of Jorvik.")

        # Vassal Feudal Autonomy: Vassals autonomously build whatever they want on their fiefs!
        # If they have enough gold and free tiles in their territory, they erect Cities (600g), Barracks (800g), or Forts (1000g)!
        for pid in PROVINCES:
            v_list = self.vassals.get(pid, [])
            for v in v_list:
                v_gold = v.get("gold", 0)
                city_cost = BUILDING_SPECS["city"]["cost"]       # 600
                barrack_cost = BUILDING_SPECS["barrack"]["cost"] # 800
                fort_cost = BUILDING_SPECS["fort"]["cost"]       # 1000

                if v_gold < city_cost:
                    continue

                v_fiefs = [f for f in self.fiefs.values() if f.get("province") == pid and (f.get("holder") == v["name"] or f.get("vassal_id") == v.get("id"))]
                if not v_fiefs:
                    continue

                # Find all available choices for this vassal
                possible_builds = []
                for f in v_fiefs:
                    free_tiles = [t for t in f.get("tiles", []) if t not in self.settlements]
                    if not free_tiles:
                        continue

                    # 1. Fort option (2 adjacent tiles, 1000g)
                    if v_gold >= fort_cost and len(free_tiles) >= 2:
                        free_set = set(free_tiles)
                        pair = None
                        for (c, r) in free_tiles:
                            if (c + 1, r) in free_set:
                                pair = [(c, r), (c + 1, r)]
                                break
                            elif (c, r + 1) in free_set:
                                pair = [(c, r), (c, r + 1)]
                                break
                        if pair:
                            possible_builds.append(("fort", fort_cost, pair, f))

                    # 2. Barracks option (1 tile, 800g)
                    if v_gold >= barrack_cost:
                        possible_builds.append(("barrack", barrack_cost, [free_tiles[0]], f))

                    # 3. Commercial City option (1 tile, 600g)
                    if v_gold >= city_cost:
                        possible_builds.append(("city", city_cost, [free_tiles[0]], f))

                if not possible_builds:
                    continue

                # Autonomous Decision:
                # If vassal has no city in this fief yet, they strongly prefer building a City to generate wealth!
                has_city = any(self.settlements.get(t, {}).get("type") in ("city", "town") for f in v_fiefs for t in f.get("tiles", []))
                if not has_city:
                    city_choices = [b for b in possible_builds if b[0] == "city"]
                    choice = city_choices[0] if city_choices else random.choice(possible_builds)
                else:
                    choice = random.choice(possible_builds)

                b_type, b_cost, chosen_tiles, chosen_fief = choice
                v["gold"] = round(v["gold"] - b_cost, 1)

                self.settlement_id_counter += 1
                s_id = f"settlement_{self.settlement_id_counter}"
                v_first = v["name"].split()[1] if len(v["name"].split()) > 1 else v["name"]
                if b_type == "city":
                    s_name = f"{v_first}'s Borough"
                elif b_type == "fort":
                    s_name = f"{v_first}'s Stronghold"
                else:
                    s_name = f"{v_first}'s Barracks"

                for t in chosen_tiles:
                    self.settlements[t] = {
                        "id": s_id,
                        "province": pid,
                        "type": b_type,
                        "name": s_name,
                        "lord": v["name"],
                        "vassal_id": v["id"],
                        "is_crown_demesne": False,
                        "is_crown_fief": False,
                        "level": 0
                    }
                    if t not in v.get("tiles", []):
                        v.setdefault("tiles", []).append(t)

                if not v.get("city_name"):
                    v["city_name"] = s_name

                # Synchronize province stats and vassal stats immediately
                sync_province_holdings_stats(self, pid)
                st_v = get_vassal_landed_status(self, v, pid)
                v["tax_contribution"] = st_v["tax_paid"]
                v["levy_contribution"] = st_v["levy_contribution"]

                b_spec = BUILDING_SPECS[b_type]
                self.logs.append(f"Feudal Autonomy: {v['name']} has autonomously constructed a {b_spec['name']} ({b_cost}g) in {chosen_fief['name']} ({PROVINCES[pid]['name']})!")

    def yearly_tick(self):
        self.player["age"] += 1
        self.enemy["age"] += 1
        self.logs.append(f"AD {self.year}: War rages across the lands of Britain.")

    def update_armies(self):
        # Sanity check: Clear in_battle flag for any army that has no enemy on its tile
        for a in self.armies:
            opponents = [o for o in self.armies if getattr(o, "tile", None) == getattr(a, "tile", None) and o.owner != a.owner]
            if not opponents:
                a.in_battle = False

        # 1. Update movement
        for a in list(self.armies):
            if a.in_battle:
                # Armies locked in battle cannot move or show path arrows
                if a.tile_path:
                    a.tile_path = []
                    a.move_progress = 0.0
                continue

            if a.is_moving:
                a.move_progress += a.move_speed
                if a.move_progress >= 100.0:
                    a.tile = a.tile_path.pop(0)
                    a.province = CELL_TO_PROV.get(a.tile, a.province)
                    a.move_progress = 0.0

                    # INTERCEPTION CHECK: if enemy is on this tile, stop and fight
                    enemy_owner = self.enemy_id if a.owner == self.player_id else self.player_id
                    blockers = [e for e in self.armies
                                if getattr(e, "tile", None) == a.tile and e.owner == enemy_owner]
                    if blockers:
                        a.tile_path = []
                        a.move_progress = 0.0
                        if a.is_demobilizing:
                            a.is_demobilizing = False
                            self.logs.append(f"Ambush! {a.name} was attacked while returning home!")
                        for b in blockers:
                            b.tile_path = []
                            b.move_progress = 0.0
                            b.is_sieging = False

                    # If reached final destination with no blocker:
                    elif not a.is_moving:
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
                            self.merge_armies_on_tile(a.tile, a.owner)

        # 2. Check Battles (Opposing armies on same tile)
        all_army_tiles = set(getattr(a, "tile", None) for a in self.armies if getattr(a, "tile", None) is not None)
        for tile in all_army_tiles:
            self.merge_armies_on_tile(tile, self.player_id)
            self.merge_armies_on_tile(tile, self.enemy_id)

            armies_on_tile = [a for a in self.armies if getattr(a, "tile", None) == tile]
            p1_list = [a for a in armies_on_tile if a.owner == self.player_id]
            p2_list = [a for a in armies_on_tile if a.owner == self.enemy_id]

            if not (p1_list and p2_list):
                for a in armies_on_tile:
                    a.in_battle = False
                continue

            a1 = p1_list[0]
            a2 = p2_list[0]
            
            # Lock both hosts in combat and halt all marching, sieging, or demobilizing
            for a in p1_list + p2_list:
                a.in_battle = True
                a.tile_path = []
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

            p_name = PROVINCES.get(a1.province, {}).get("name", "the realm")
            if a1.troops <= 0 and a2.troops <= 0:
                self.logs.append(f"Both armies annihilated at tile {tile} in {p_name}!")
                if a1 in self.armies: self.armies.remove(a1)
                if a2 in self.armies: self.armies.remove(a2)
            elif a1.troops <= 0:
                self.logs.append(f"Defeat! {a1.name} was wiped out at tile {tile} in {p_name}!")
                if a1 in self.armies: self.armies.remove(a1)
                a2.in_battle = False
                a2.tile_path = []
                a2.move_progress = 0.0
            elif a2.troops <= 0:
                self.logs.append(f"Glorious Victory! Destroyed the Viking host at tile {tile} in {p_name}!")
                if a2 in self.armies: self.armies.remove(a2)
                a1.in_battle = False
                a1.tile_path = []
                a1.move_progress = 0.0

        # 3. Check Sieges (City-by-City Siege in Enemy or Contested Province)
        for a in list(self.armies):
            if a not in self.armies:
                continue
            if a.is_moving or a.in_battle or a.is_mustering or a.courier_en_route or a.is_demobilizing:
                continue

            prov = PROVINCES.get(a.province)
            if not prov:
                a.is_sieging = False
                a.siege_progress = 0
                continue

            defenders = [enemy for enemy in self.armies if getattr(enemy, "tile", None) == a.tile and enemy.owner != a.owner]
            if defenders:
                a.is_sieging = False
                continue

            is_enemy_prov = (prov["owner"] != a.owner)

            # Strict Tile-Based Siege: Army must stand directly on the settlement tile
            cur_settlement = self.settlements.get(a.tile)

            if cur_settlement:
                s_id = cur_settlement.get("id")
                # Group all tiles of this holding (e.g. 2-tile fort)
                h_tiles = [coord for coord, s in self.settlements.items() if (s.get("id") and s.get("id") == s_id) or coord == a.tile]
                h_name = cur_settlement.get("name", "Holding")
                occ = cur_settlement.get("occupied_by")

                needs_siege = False
                is_liberation = False

                if is_enemy_prov:
                    # Enemy province: need to siege if not yet occupied by a.owner
                    if occ != a.owner:
                        needs_siege = True
                        is_liberation = False
                else:
                    # Friendly province: need to liberate if occupied by enemy
                    if occ is not None and occ != a.owner:
                        needs_siege = True
                        is_liberation = True

                if needs_siege:
                    a.is_sieging = True
                    a.siege_target_name = h_name
                    a.target_city = a.tile

                    # Siege rate scaled by troops
                    rate = max(4, int(a.troops / 250))
                    a.siege_progress += rate

                    if a.siege_progress >= 100:
                        a.siege_progress = 0
                        a.is_sieging = False
                        a.target_city = None
                        a.siege_target_name = None

                        if not is_liberation:
                            # Occupy this holding!
                            for t in h_tiles:
                                self.settlements[t]["occupied_by"] = a.owner

                            remaining = get_siegeable_holdings(self, a.province, a.owner)
                            if remaining:
                                self.logs.append(f"Holding Fallen! {a.name} captured {h_name}. {prov['name']} is now contested ({len(remaining)} holding(s) remain)!")
                            else:
                                # ALL holdings captured! Whole province flips!
                                prov["owner"] = a.owner
                                prov["color"] = list(PROVINCE_FACTION_COLORS.get(a.owner, {}).get(a.province, COLOR_WESSEX if a.owner == self.player_id else COLOR_DANELAW))
                                for t in [coord for coord, s in self.settlements.items() if s.get("province") == a.province]:
                                    self.settlements[t]["occupied_by"] = None

                                if a.owner == self.player_id:
                                    self.player["prestige"] += 100
                                    self.logs.append(f"TOTAL VICTORY! All boroughs in {prov['name']} have fallen! Province conquered by Wessex!")
                                else:
                                    self.enemy["prestige"] += 100
                                    self.logs.append(f"DISASTER! All boroughs in {prov['name']} have fallen to the Danelaw!")

                                # Automatically relocate or restore capitals if needed
                                self.get_realm_capital(self.player_id)
                                self.get_realm_capital(self.enemy_id)
                        else:
                            # Friendly liberation of occupied holding!
                            for t in h_tiles:
                                self.settlements[t]["occupied_by"] = None
                            self.logs.append(f"Liberated! {a.name} reclaimed {h_name} for {prov['name']}!")

                            remaining = get_siegeable_holdings(self, a.province, a.owner)
                            if not remaining:
                                self.logs.append(f"Order Restored! {prov['name']} is fully liberated and no longer contested.")
                else:
                    # Settlement already friendly or already occupied by this army's owner: no siege
                    a.is_sieging = False
                    a.siege_progress = 0
                    a.target_city = None
                    a.siege_target_name = None

            else:
                # Army is standing on an EMPTY tile: CANNOT SIEGE ANY HOLDINGS!
                # Only if the province has literally 0 settlements total (empty wilderness) can it cap on capital tile
                prov_has_settlements = any(s.get("province") == a.province for s in self.settlements.values())
                if not prov_has_settlements and is_enemy_prov:
                    cap_tile = get_province_capital_tile(a.province)
                    if getattr(a, "tile", None) == cap_tile:
                        a.is_sieging = True
                        a.siege_target_name = f"Wilds of {prov['name']}"
                        a.target_city = a.tile
                        rate = max(4, int(a.troops / 250))
                        a.siege_progress += rate
                        if a.siege_progress >= 100:
                            prov["owner"] = a.owner
                            prov["color"] = list(PROVINCE_FACTION_COLORS.get(a.owner, {}).get(a.province, COLOR_WESSEX if a.owner == self.player_id else COLOR_DANELAW))
                            a.is_sieging = False
                            a.siege_progress = 0
                            a.target_city = None
                            a.siege_target_name = None
                            if a.owner == self.player_id:
                                self.player["prestige"] += 100
                                self.logs.append(f"Victory! {prov['name']} has been conquered by Wessex!")
                            else:
                                self.enemy["prestige"] += 100
                                self.logs.append(f"Disaster! {prov['name']} has fallen to the Danelaw!")
                            self.get_realm_capital(self.player_id)
                            self.get_realm_capital(self.enemy_id)
                    else:
                        a.is_sieging = False
                        a.siege_progress = 0
                        a.target_city = None
                        a.siege_target_name = None
                else:
                    # Regular empty tile: no siege
                    a.is_sieging = False
                    a.siege_progress = 0
                    a.target_city = None
                    a.siege_target_name = None

    # ---------------------------------------------------------
    # AI (Halfdan Ragnarsson) - Intelligent Border Awareness, Mobilization & Retaliation
    # ---------------------------------------------------------
    def ai_routine(self):
        """Dispatches to modular strategic AI system for all active non-player AI realm rulers."""
        ai_rulers = [cid for cid in CHARACTERS if cid != self.player_id and CHARACTERS[cid].get("alive", True)]
        for r_id in ai_rulers:
            run_realm_ai(self, r_id)

    # ---------------------------------------------------------
prov_tile_list = {}
for (c, r), pid in CELL_TO_PROV.items():
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



def carve_new_fief(target_state, province_id):
    p_tiles = [coord for coord, pid in CELL_TO_PROV.items() if pid == province_id]
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

