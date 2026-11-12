"""
Master GameState Engine and Simulation Loop
"""
import random
import math
import copy

from game.config import DAYS_PER_TILE, DAYS_PER_KOTAK, LEVY_RAISE_COOLDOWN_DAYS
from game.data.scenario import get_scenario, get_start_date
from game.data.characters import (
    CHARACTERS, INITIAL_CHARACTERS, get_capital_province, get_color,
    get_display_name, get_honorific, get_personal_name, get_short_name,
    get_naming, get_realm_name, get_title, strip_honorific,
    set_character_honorific, set_character_title, set_character_realm,
)
from game.data.provinces import (
    PROVINCES, INITIAL_PROVINCES, PROVINCE_FACTION_COLORS, ADJACENCY,
    find_shortest_path, reset_global_world_data, refresh_province_faction_colors,
    get_province_color,
)
from game.data.buildings import BUILDING_SPECS, get_barrack_stats, BARRACK_UPGRADE_COSTS
from game.core.map import CELL_TO_PROV, PROV_TO_TILES, PROV_CAPITAL_TILES, get_province_capital_tile, find_shortest_tile_path, TILE_ADJACENCY
from game.core.army import Army, SupplyWagon
from game.core.titles import Title, get_tier_prefix
from game.systems.economy import (
    sync_province_holdings_stats,
    get_vassal_landed_status,
    get_province_holdings,
    get_all_settlement_holdings
)
from game.systems.military import get_siegeable_holdings, is_province_contested
from game.systems.ai import standardize_enemy_ai_laws, standardize_all_ai_laws, run_viking_ai, run_realm_ai

class GameState:
    def __init__(self):
        self.scenario = get_scenario()
        scenario = self.scenario
        alive_ids = [cid for cid, c in CHARACTERS.items() if c.get("alive", True)] or list(CHARACTERS)

        # The scenario chooses the player; every other living ruler is AI.
        # This is the single switch that makes any character playable.
        scenario_player = scenario.get("player_id")
        if scenario_player not in alive_ids:
            scenario_player = alive_ids[0] if alive_ids else next(iter(CHARACTERS), None)
        self.player_id = scenario_player

        scenario_ai = [cid for cid in scenario.get("ai_rulers", []) if cid in alive_ids and cid != self.player_id]
        self.ai_rulers = scenario_ai + [cid for cid in alive_ids if cid != self.player_id and cid not in scenario_ai]
        self.enemy_id = self.ai_rulers[0] if self.ai_rulers else self.player_id

        self.selected_province = None
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
        self.vassal_selected_province = None
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
        self.zoom = float(scenario.get("zoom", 0.85))
        self.min_zoom = 0.65
        self.max_zoom = 2.40
        self.cam_pan_x = 0
        self.cam_pan_y = 0
        self.is_panning = False
        self.pan_start_mouse = (0, 0)
        self.pan_start_cam = (0, 0)
        
        # Calendar from the active scenario.
        start_year, start_month, start_day = get_start_date()
        self.year = start_year
        self.month = start_month
        self.day = start_day
        self.months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        self.month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Speed: 0 = Pause, 1 = Very Slow, 2 = Slow, 3 = Normal, 4 = Fast, 5 = Very Fast
        self.speed = 3  # start at Normal
        self.speed_factors = {1:2000, 2:1000, 3:500, 4:250, 5:125}
        self.tick_timer = 0
        
        # Army management
        self.armies = []
        self.army_id_counter = 1
        self.raise_cooldowns = {cid: 0 for cid in CHARACTERS}
        self.supply_wagons = []
        self.wagon_id_counter = 1

        # Royal Capital & Realm Seats (per ruler, fully data-driven)
        self.primary_capitals = {}
        for cid, cdata in CHARACTERS.items():
            cap = get_capital_province(cid)
            if not cap or cap not in PROVINCES:
                owned = [pid for pid, p in PROVINCES.items() if p.get("owner") == cid]
                cap = owned[0] if owned else next(iter(PROVINCES), None)
            self.primary_capitals[cid] = cap
        self.capitals = dict(self.primary_capitals)
        self.capital_was_lost = {cid: False for cid in CHARACTERS}
        self.selected_province = self.primary_capitals.get(self.player_id) or next(iter(PROVINCES), None)

        # Feudal Suzerainty & Dynamic Vassalage (No hard Defeat / Win!)
        self.liege_of = {}
        for cid, cdata in CHARACTERS.items():
            liege = cdata.get("liege")
            self.liege_of[cid] = liege if liege in CHARACTERS and liege != cid else None
        self.war_status = "peace"          # Default is PEACE across the continent!
        self.active_wars = set()           # Set of frozenset({char1, char2})
        self.active_diplomacy_target = self.enemy_id
        self.tribute_rate = float(scenario.get("tribute_rate", 0.20))
        self.default_vassal_tax_rate = int(scenario.get("default_vassal_tax_rate", 10))
        self.default_vassal_levy_rate = int(scenario.get("default_vassal_levy_rate", 20))
        self.ai_vassal_tax_rate = int(scenario.get("ai_vassal_tax_rate", 20))
        self.ai_vassal_levy_rate = int(scenario.get("ai_vassal_levy_rate", 20))
        self.ai_standoff_days = {}         # frozenset({ai_1, ai_2}) -> days facing each other
        self.ai_standoff_cooldown = {}     # frozenset({ai_1, ai_2}) -> cooldown days before re-escalating
        self.ai_border_vigilance = {}      # ruler_id -> remaining vigilance countdown days (e.g. 20)
        self.ai_vigilance_provs = {}       # ruler_id -> set of border provinces being guarded
        self.vassal_limit = int(scenario.get("vassal_limit", 5))
        self.vassal_inspecting_liege_id = None  # Drill-down into a Count's direct sub-vassals
        self.vassal_subordinate_target_id = None  # Vassal currently being subordinated to another liege
        self.hovered_vassal_tiles = set()        # Tiles to highlight on map when hovering a vassal card
        self.subjugation_event = None    # Feudal treaty story modal event
        
        # AI decision timer
        self.ai_timer = 1
        
        # Chronicle Logs come from the scenario; generate neutral fallbacks.
        self.logs = list(scenario.get("intro_logs") or [])
        if not self.logs:
            title = scenario.get("title", "The campaign")
            region = scenario.get("region_name", "the realm")
            self.logs = [f"{title}: the chronicle of {region} begins."]
        
        # Generate random 1-5 vassals for all provinces
        self.generate_province_vassals()
        self.init_feudal_titles()
        setup_province_starter_cities(self)
        self.sync_conquered_rulers()
        self.siege_context_menu = None   # Floating context menu for 'SIEGE THE CASTLE'

    def are_hostile(self, char1, char2):
        """
        Returns True if char1 and char2 are actively at war.
        During peacetime ('peace' or 'vassalage'), characters are NOT hostile!
        """
        if not char1 or not char2 or char1 == char2:
            return False

        # Check explicit bilateral wars
        if hasattr(self, "active_wars") and frozenset({char1, char2}) in self.active_wars:
            return True

        ws = getattr(self, "war_status", "peace")
        if ws == "peace":
            return False

        if ws == "war":
            if not getattr(self, "active_wars", None):
                return {char1, char2} == {self.player_id, self.enemy_id}
            return frozenset({char1, char2}) in self.active_wars

        if ws == "vassalage":
            if self.get_liege(char2) == char1 or self.get_liege(char1) == char2:
                return False
        return False

    def declare_war(self, initiator_id=None, target_id=None, reason="Formal Declaration"):
        """Declares war between two realms, initiating active hostility."""
        if initiator_id is None:
            initiator_id = self.player_id
        if target_id is None:
            target_id = getattr(self, "active_diplomacy_target", self.enemy_id)

        if not hasattr(self, "active_wars"):
            self.active_wars = set()

        war_pair = frozenset({initiator_id, target_id})
        if war_pair in self.active_wars:
            return 0, 0

        self.active_wars.add(war_pair)
        self.war_status = "war"
        p_char = CHARACTERS.get(initiator_id, {})
        t_char = CHARACTERS.get(target_id, {})
        p_name = p_char.get("name", initiator_id)
        t_name = t_char.get("name", target_id)
        self.logs.append(f"⚔ WAR DECLARED! {p_name} has declared war on {t_name}! ({reason})")

    def offer_peace(self, initiator_id=None, target_id=None):
        """Signs a truce / peace agreement between two realms, ending hostilities."""
        if initiator_id is None:
            initiator_id = self.player_id
        if target_id is None:
            target_id = getattr(self, "active_diplomacy_target", self.enemy_id)

        if not hasattr(self, "active_wars"):
            self.active_wars = set()

        war_pair = frozenset({initiator_id, target_id})
        self.active_wars.discard(war_pair)
        if len(self.active_wars) == 0:
            self.war_status = "peace"

        p_char = CHARACTERS.get(initiator_id, {})
        t_char = CHARACTERS.get(target_id, {})
        p_name = p_char.get("name", initiator_id)
        t_name = t_char.get("name", target_id)
        self.logs.append(f"🕊 PEACE CONCLUDED: A truce has been established between {p_name} and {t_name}.")

    def reset(self):
        """Reinitialize entire game state and 1:1 starter cities matching vassals in-place."""
        reset_global_world_data()
        self.__init__()
        setup_province_starter_cities(self)
        self.logs.append(f"Campaign reset to {self.day} {self.months[self.month - 1]} {self.year} AD. Vassals and cities synchronized.")

    # ---------------------------------------------------------
    # CK2-STYLE FEUDAL TITLES SYSTEM (Revoke & Grant Titles)
    # ---------------------------------------------------------
    def get_noble_prefix(self, ruler_id, tier, is_female=None):
        """Resolves a culture-appropriate honorific from character metadata."""
        ruler = CHARACTERS.get(ruler_id, {})
        if is_female is None:
            is_female = str(ruler.get("gender", "")).lower() == "female"
        naming = get_naming(ruler_id)
        title_key = {
            "kingdom": "kingdom_title",
            "duchy": "duke_title",
            "county": "count_title",
            "barony": "baron_title",
        }.get(tier)
        if title_key and naming.get(title_key):
            return str(naming[title_key])
        return get_tier_prefix(tier, ruler.get("culture", "human"), is_female)

    def init_feudal_titles(self):
        """Initializes de jure and de facto landed titles for every living ruler."""
        self.titles = {}

        # 1. Sovereign titles and personal duchies for every ruler in data.
        for cid in CHARACTERS:
            if not CHARACTERS[cid].get("alive", True):
                continue
            cap = self.primary_capitals.get(cid) or get_capital_province(cid)
            if not cap:
                continue
            short = get_short_name(cid)
            kingdom_id = f"k_{cid}"
            duchy_id = f"d_{cid}"
            realm = get_realm_name(cid, f"Realm of {short}")
            duchy_title = CHARACTERS[cid].get("duchy_title") or f"Duchy of {short}"
            self.titles[kingdom_id] = Title(kingdom_id, realm, "kingdom", cid, cap)
            self.titles[duchy_id] = Title(duchy_id, duchy_title, "duchy", cid, cap, kingdom_id)
            self.titles[f"b_{cid}_capital"] = Title(
                f"b_{cid}_capital", f"Barony of {short}", "barony", cid, cap, duchy_id
            )

        # 2. County & Barony titles from the vassal hierarchy.
        for pid, v_list in self.vassals.items():
            owner = PROVINCES.get(pid, {}).get("owner")
            duchy_id = f"d_{owner}" if owner in CHARACTERS else f"d_{pid}"
            for v in v_list:
                v_id = v.get("id")
                v_rank = v.get("rank", "baron")
                clean_n = self.get_character_clean_name(v.get("name", "Noble"))

                if v_rank in ("duke", "count"):
                    t_id = f"c_{v_id}"
                    t_name = f"County of {clean_n}"
                    self.titles[t_id] = Title(t_id, t_name, "county", v_id, pid, de_jure_liege_id=duchy_id, tiles=v.get("tiles", []))
                else:
                    t_id = f"b_{v_id}"
                    t_name = f"Barony of {clean_n}"
                    liege_t_id = f"c_{v.get('liege_id')}"
                    self.titles[t_id] = Title(t_id, t_name, "barony", v_id, pid, de_jure_liege_id=liege_t_id, tiles=v.get("tiles", []))

    def get_character_clean_name(self, raw_name):
        """Strips known noble honorifics from a name to prevent repeated prefixes."""
        return strip_honorific(raw_name)

    def get_duchy_for_province(self, pid):
        """Resolves the regional Duchy Title for a given province ID."""
        owner = PROVINCES.get(pid, {}).get("owner")
        for duchy_id in (f"d_{owner}", f"d_{pid}"):
            if duchy_id in self.titles:
                return self.titles[duchy_id]
        for t in self.titles.values():
            if t.tier == "duchy" and t.province_id == pid:
                return t
        return None

    def get_held_titles(self, char_id):
        """Returns all unique Title entities held by a character, sorted by rank descending."""
        seen = set()
        result = []
        for t in self.titles.values():
            if t.holder_id == char_id and t.id not in seen:
                seen.add(t.id)
                result.append(t)
        return sorted(result, key=lambda t: t.rank, reverse=True)

    def get_primary_title(self, char_id):
        """Returns the highest rank title held by a character."""
        held = self.get_held_titles(char_id)
        if not held:
            return None
        return max(held, key=lambda t: t.rank)

    def get_grantable_titles(self, ruler_id=None):
        """Returns titles held by ruler_id that can be granted to vassals (Duchies, Counties, Baronies)."""
        if ruler_id is None:
            ruler_id = self.player_id
        held = self.get_held_titles(ruler_id)
        # Cannot grant sovereign primary Kingdom title, only Duchies and below!
        return [t for t in held if t.tier in ("duchy", "county", "barony")]

    def update_character_rank_from_titles(self, char_or_vassal_id):
        """
        Dynamically computes a noble's rank strictly from their highest held Title (CK2 style).
        - Holds Kingdom title -> King / Queen (rank 4)
        - Holds Duchy title -> Duke / Duchess (rank 3)
        - Holds County title -> Count / Countess (rank 2)
        - Holds Barony title -> Baron / Baroness (rank 1)
        - Holds NO titles -> Courtier / Unlanded Noble (rank 0)
        """
        all_v = [v for plist in self.vassals.values() for v in plist]
        v = next((x for x in all_v if x.get("id") == char_or_vassal_id or x.get("char_id") == char_or_vassal_id), None)
        if not v:
            return

        held = self.get_held_titles(char_or_vassal_id)
        clean_n = self.get_character_clean_name(v.get("name", "Noble"))

        if not held:
            v["rank"] = "courtier"
            v["rank_num"] = 0
            v["title"] = "Courtier"
            v["name"] = f"Lord {clean_n}"
            v["is_direct_vassal"] = False
            return

        primary = max(held, key=lambda t: t.rank)
        v["rank_num"] = primary.rank
        if primary.tier == "kingdom":
            v["rank"] = "king"
        elif primary.tier == "duchy":
            v["rank"] = "duke"
        elif primary.tier == "county":
            v["rank"] = "count"
        else:
            v["rank"] = "baron"

        pid = v.get("province")
        owner = PROVINCES.get(pid, {}).get("owner")
        ruler_id = owner if owner in CHARACTERS else self.player_id
        pfx = self.get_noble_prefix(ruler_id, primary.tier)
        v["title"] = pfx
        v["name"] = f"{pfx} {clean_n}"
        if v["rank"] in ("duke", "count") and v.get("liege_id") in CHARACTERS:
            v["is_direct_vassal"] = True

    def grant_title(self, title_id, target_char_id):
        """
        Grants a title currently held by the King/Ruler to a target character.
        Dynamically elevates target's rank, updates primary title, transfers physical fief tiles,
        and establishes de jure feudal vassalage.
        """
        title = self.titles.get(title_id)
        if not title:
            return False

        old_holder_id = title.holder_id
        title.holder_id = target_char_id

        all_v = [v for plist in self.vassals.values() for v in plist]
        target_v = next((v for v in all_v if v.get("id") == target_char_id or v.get("char_id") == target_char_id), None)
        old_v = next((v for v in all_v if v.get("id") == old_holder_id or v.get("char_id") == old_holder_id), None)

        # Transfer physical tiles and settlements
        if title.tiles:
            if target_v:
                for t in title.tiles:
                    if t not in target_v.setdefault("tiles", []):
                        target_v["tiles"].append(t)
            if old_v and old_v.get("tiles"):
                old_v["tiles"] = [t for t in old_v["tiles"] if t not in title.tiles]
            for t in title.tiles:
                if t in self.settlements:
                    self.settlements[t]["lord"] = target_v["name"] if target_v else "Noble"
                    self.settlements[t]["vassal_id"] = target_char_id
                    if target_char_id != self.player_id:
                        self.settlements[t]["is_crown_demesne"] = False

        if target_v:
            target_v["liege_id"] = old_holder_id if old_holder_id in CHARACTERS else self.player_id
            target_v["is_direct_vassal"] = True

        # Sync rank dynamically from held titles
        self.update_character_rank_from_titles(target_char_id)
        if old_holder_id != self.player_id:
            self.update_character_rank_from_titles(old_holder_id)

        disp_n = target_v["name"] if target_v else target_char_id
        lord_n = get_display_name(old_holder_id, self.player_id)
        self.logs.append(f"🎁 Feudal Investiture: {lord_n} bestowed the {title.name} upon {disp_n}!")
        return True

    def revoke_title(self, title_id, revoker_char_id=None):
        """
        Revokes a landed title (Duchy, County, or Barony) directly into the revoker's (King's) demesne.
        Physical tiles transfer to the Crown. Former holder drops rank according to their remaining titles.
        """
        if revoker_char_id is None:
            revoker_char_id = self.player_id

        title = self.titles.get(title_id)
        if not title:
            return False

        old_holder_id = title.holder_id
        title.holder_id = revoker_char_id

        all_v = [v for plist in self.vassals.values() for v in plist]
        old_v = next((v for v in all_v if v.get("id") == old_holder_id or v.get("char_id") == old_holder_id), None)

        # Transfer physical tiles and settlements to the Crown Demesne
        if title.tiles:
            if old_v and old_v.get("tiles"):
                old_v["tiles"] = [t for t in old_v["tiles"] if t not in title.tiles]
            for t in title.tiles:
                if t in self.settlements:
                    self.settlements[t]["lord"] = get_display_name(revoker_char_id)
                    self.settlements[t]["vassal_id"] = revoker_char_id
                    self.settlements[t]["is_crown_demesne"] = True

        # Recalculate former holder's rank from their remaining titles
        if old_v:
            self.update_character_rank_from_titles(old_holder_id)

        disp_n = old_v["name"] if old_v else "Noble"
        r_name = get_display_name(revoker_char_id)
        self.logs.append(f"👑 Royal Decree: {r_name} revoked the {title.name} from {disp_n} into the Crown Demesne!")
        return True

    def sync_conquered_rulers(self):
        """
        Landless rulers are inducted into the feudal hierarchy as dukes
        holding a seat under whoever controls their former primary capital.
        Works for any number of characters and any scenario province layout.
        """
        for r_id in list(CHARACTERS.keys()):
            r_char = CHARACTERS.get(r_id)
            if not r_char or not r_char.get("alive", True):
                continue
            owned = [pid for pid, p in PROVINCES.items() if p.get("owner") == r_id]
            if owned:
                continue

            seat = self.primary_capitals.get(r_id) or get_capital_province(r_id)
            prov = PROVINCES.get(seat)
            if not prov:
                continue
            current_owner = prov.get("owner")
            if not current_owner or current_owner == r_id:
                continue

            liege_id = self.get_liege(r_id) or current_owner
            if liege_id not in CHARACTERS or liege_id == r_id:
                continue
            self.set_liege(r_id, liege_id)

            seat_short = prov["name"].split()[0]
            is_female = str(r_char.get("gender", "")).lower() == "female"
            ducal_prefix = self.get_noble_prefix(liege_id, "duchy", is_female)
            ducal_name = f"{ducal_prefix} {get_personal_name(r_id)}"
            d_title_id = f"d_{r_id}"

            if hasattr(self, "titles"):
                if d_title_id not in self.titles:
                    self.titles[d_title_id] = Title(
                        d_title_id, f"Duchy of {seat_short}", "duchy", r_id, seat, f"k_{liege_id}"
                    )
                d_title = self.titles[d_title_id]
                if d_title.holder_id not in (current_owner,):
                    d_title.holder_id = f"duke_{r_id}"

            p_vassals = self.vassals.setdefault(seat, [])
            duke_entry = next((v for v in p_vassals if v.get("char_id") == r_id or v.get("id") == f"duke_{r_id}"), None)

            crown_tiles = []
            for coord, sdata in self.settlements.items():
                if sdata.get("province") == seat:
                    if sdata.get("is_crown_demesne") or sdata.get("vassal_id") == f"duke_{r_id}":
                        crown_tiles.append(coord)
            if not crown_tiles:
                cap_tile = PROV_CAPITAL_TILES.get(seat)
                if cap_tile and cap_tile in self.settlements:
                    crown_tiles.append(cap_tile)

            prov_counts = [v for v in p_vassals if v.get("rank") in ("count", "duke") and v.get("id") != f"duke_{r_id}"]
            count_ids = [c["id"] for c in prov_counts]

            if not duke_entry:
                duke_entry = {
                    "id": f"duke_{r_id}",
                    "char_id": r_id,
                    "name": ducal_name,
                    "rank": "duke",
                    "title": ducal_prefix,
                    "province": seat,
                    "liege_id": liege_id,
                    "is_direct_vassal": True,
                    "tiles": crown_tiles,
                    "city_name": f"Ducal Palace of {seat_short}",
                    "sub_vassals": list(count_ids),
                    "gold": max(50.0, float(r_char.get("gold", 100.0))),
                    "tax_rate": self.ai_vassal_tax_rate if liege_id != self.player_id else self.default_vassal_tax_rate,
                    "levy_rate": self.ai_vassal_levy_rate if liege_id != self.player_id else self.default_vassal_levy_rate,
                    "loyalty": 85
                }
                p_vassals.insert(0, duke_entry)
                for cv in prov_counts:
                    cv["liege_id"] = duke_entry["id"]
                    cv["is_direct_vassal"] = False
                self.logs.append(f"⚜ Feudal Treaty: {ducal_name} takes their seat as {ducal_prefix} of {seat_short} under {get_display_name(liege_id)}!")
            else:
                duke_entry.update({
                    "rank": "duke",
                    "title": ducal_prefix,
                    "name": ducal_name,
                    "liege_id": liege_id,
                })
                if not duke_entry.get("tiles"):
                    duke_entry["tiles"] = crown_tiles

            for t in crown_tiles:
                if t in self.settlements:
                    self.settlements[t]["lord"] = ducal_name
                    self.settlements[t]["owner"] = r_id
                    self.settlements[t]["is_crown_demesne"] = True
                    self.settlements[t]["vassal_id"] = None

            for f in self.fiefs.values():
                if f.get("province") == seat and (f.get("holder") == ducal_name or "Crown Demesne" in f.get("name", "")):
                    f["holder"] = ducal_name
                    f["owner"] = r_id
                    f["is_crown_demesne"] = True
                    f["vassal_id"] = None

            set_character_honorific(r_id, ducal_prefix)
            set_character_title(r_id, f"{ducal_prefix} of {seat_short}")
            set_character_realm(r_id, f"Duchy of {seat_short} (Vassal of {get_short_name(liege_id)})")
            r_char["liege"] = liege_id

    def retract_to_direct_vassal(self, vassal_id):
        """
        Pulls a subordinate vassal (Count or Baron) to become a Direct Vassal under the King.
        Removes them from their previous liege's sub_vassals list.
        """
        all_v = [v for plist in self.vassals.values() for v in plist]
        target_v = next((v for v in all_v if v.get("id") == vassal_id), None)
        if not target_v:
            return False

        # Remove from previous liege's sub_vassals
        for v in all_v:
            if vassal_id in v.get("sub_vassals", []):
                v["sub_vassals"].remove(vassal_id)

        target_v["liege_id"] = self.player_id
        target_v["is_direct_vassal"] = True

        rk_title = target_v.get("rank", "vassal").capitalize()
        p_name = self.player.get("name", "Ruler")
        self.logs.append(f"👑 Royal Retraction: {target_v['name']} is now a Direct {rk_title} under {p_name}!")
        return True

    def transfer_vassal_to_liege(self, vassal_id, new_liege_id):
        """
        Transfers a vassal (Count or Baron) to swear fealty to a new liege (Duke, Count, or King).
        - If new_liege_id == self.player_id: becomes Direct Vassal to the King.
        - If Count under Duke: becomes subordinate Count under that Duke.
        - If Baron under Count/Duke: becomes subordinate Baron under that liege.
        """
        all_v = [v for plist in self.vassals.values() for v in plist]
        target_v = next((v for v in all_v if v.get("id") == vassal_id), None)
        if not target_v:
            return False

        # Remove from previous liege's sub_vassals
        for v in all_v:
            if vassal_id in v.get("sub_vassals", []):
                v["sub_vassals"].remove(vassal_id)

        if new_liege_id == self.player_id:
            return self.retract_to_direct_vassal(vassal_id)

        new_liege = next((v for v in all_v if v.get("id") == new_liege_id), None)
        if not new_liege:
            return False

        target_v["liege_id"] = new_liege["id"]
        target_v["is_direct_vassal"] = False
        if target_v["id"] not in new_liege.setdefault("sub_vassals", []):
            new_liege["sub_vassals"].append(target_v["id"])

        self.logs.append(f"⚜ Feudal Charter: {target_v['name']} sworn as direct vassal under {new_liege['name']}!")
        return True

    def promote_vassal(self, vassal_id):
        """Nobility ranks can only be elevated by granting a landed Title (CK2 style)."""
        self.logs.append("⚠️ Nobility ranks cannot be created out of thin air! Grant a held Duchy or County title from your Crown Demesne.")
        return False

    def demote_vassal(self, vassal_id):
        """Demotes a vassal by revoking their highest held landed title into the Royal Demesne."""
        held = self.get_held_titles(vassal_id)
        if held:
            return self.revoke_title(held[0].id)
        self.logs.append("⚠️ Vassal holds no landed titles to revoke.")
        return False

    def grant_duchy_title(self, vassal_id):
        """Elevates a direct Count to Duke."""
        return self.promote_vassal(vassal_id)

    def demote_and_assign_vassal(self, vassal_id, new_liege_id):
        """Demotes/transfers a vassal under a liege."""
        return self.transfer_vassal_to_liege(vassal_id, new_liege_id)

    def demote_to_baron(self, vassal_id):
        """Demotes Count to Baron."""
        return self.demote_vassal(vassal_id)

    def promote_to_direct_vassal(self, vassal_id):
        """Promotes Baron to Count or retracts to direct vassal."""
        all_v = [v for plist in self.vassals.values() for v in plist]
        target_v = next((v for v in all_v if v.get("id") == vassal_id), None)
        if target_v and target_v.get("rank") == "baron":
            self.promote_vassal(vassal_id)
        return self.retract_to_direct_vassal(vassal_id)

    def generate_province_vassals(self):
        """
        Generates a feudal hierarchy for every province using each ruler's
        data-defined naming pools and cultural titles. Works with any number
        of realms/provinces, including custom scenarios.
        """
        random.seed(self.year)
        self.vassals = {}

        for pid, pdata in PROVINCES.items():
            owner = pdata.get("owner", self.player_id)
            is_ai = owner != self.player_id
            naming = get_naming(owner)
            f_pool = list(naming.get("first_names") or ["Aldric", "Bertram", "Cedric", "Daria"])
            ep_pool = list(naming.get("epithets") or ["the Bold", "the Wise", "the Pious"])
            c_title = str(naming.get("count_title", "Count"))
            b_title = str(naming.get("baron_title", "Baron"))
            tax_rate = self.ai_vassal_tax_rate if is_ai else self.default_vassal_tax_rate
            levy_rate = self.ai_vassal_levy_rate if is_ai else self.default_vassal_levy_rate

            c1_id = f"{pid}_count_1"
            c2_id = f"{pid}_count_2"
            b1_id = f"{pid}_baron_1"
            b2_id = f"{pid}_baron_2"

            def make_vassal(v_id, rank, liege_id, title, gold_range, sub_ids=None):
                fn = random.choice(f_pool)
                ep = random.choice(ep_pool)
                return {
                    "id": v_id,
                    "name": f"{title} {fn} '{ep}'",
                    "rank": rank,
                    "title": title,
                    "province": pid,
                    "is_direct_vassal": rank in ("duke", "count"),
                    "liege_id": liege_id,
                    "sub_vassals": list(sub_ids or []),
                    "levy_contribution": 0,
                    "tax_contribution": 0,
                    "tax_rate": tax_rate,
                    "levy_rate": levy_rate,
                    "tax_locked": is_ai,
                    "levy_locked": is_ai,
                    "gold": random.randint(*gold_range),
                    "city_name": None,
                    "tiles": []
                }

            count_1 = make_vassal(c1_id, "count", owner, c_title, (60, 95), [b1_id])
            count_2 = make_vassal(c2_id, "count", owner, c_title, (60, 95), [b2_id])
            baron_1 = make_vassal(b1_id, "baron", c1_id, b_title, (40, 70))
            baron_2 = make_vassal(b2_id, "baron", c2_id, b_title, (40, 70))
            self.vassals[pid] = [count_1, count_2, baron_1, baron_2]

    @property
    def player(self):
        return CHARACTERS[self.player_id]

    @property
    def enemy(self):
        return CHARACTERS.get(self.enemy_id, CHARACTERS.get(self.player_id, {}))

    # ---------------------------------------------------------
    # Generic ruler / liege / capital / cooldown accessors
    # ---------------------------------------------------------
    def get_active_rulers(self, include_player=True, alive_only=True):
        """All playable sovereign rulers in the scenario."""
        result = []
        for cid, cdata in CHARACTERS.items():
            if alive_only and not cdata.get("alive", True):
                continue
            if not include_player and cid == self.player_id:
                continue
            result.append(cid)
        return result

    def get_ai_rulers(self):
        return [cid for cid in self.ai_rulers if cid in CHARACTERS and CHARACTERS[cid].get("alive", True)]

    def get_rival_rulers(self, ruler_id=None):
        if ruler_id is None:
            ruler_id = self.player_id
        return [cid for cid in self.get_active_rulers(include_player=True) if cid != ruler_id]

    def get_liege(self, char_id):
        if not char_id:
            return None
        liege = self.liege_of.get(char_id)
        if liege not in CHARACTERS:
            char = CHARACTERS.get(char_id, {})
            liege = char.get("liege")
            if liege not in CHARACTERS:
                liege = None
            self.liege_of[char_id] = liege
        return liege

    def set_liege(self, vassal_id, liege_id):
        """Sets (or clears) a ruler's feudal overlord consistently across state and data."""
        if not vassal_id or vassal_id == liege_id:
            return False
        if vassal_id not in CHARACTERS:
            return False
        if liege_id is not None and liege_id not in CHARACTERS:
            return False
        self.liege_of[vassal_id] = liege_id
        CHARACTERS[vassal_id]["liege"] = liege_id
        return True

    def get_primary_capital(self, char_id):
        cap = self.primary_capitals.get(char_id)
        if cap in PROVINCES:
            return cap
        cap = get_capital_province(char_id)
        if cap in PROVINCES:
            self.primary_capitals[char_id] = cap
            return cap
        owned = [pid for pid, p in PROVINCES.items() if p.get("owner") == char_id]
        cap = owned[0] if owned else next(iter(PROVINCES), None)
        self.primary_capitals[char_id] = cap
        return cap

    def get_raise_cooldown(self, ruler_id):
        return int(self.raise_cooldowns.get(ruler_id, 0))

    def set_raise_cooldown(self, ruler_id, days):
        self.raise_cooldowns[ruler_id] = max(0, int(days))

    @property
    def player_capital(self):
        return self.capitals.get(self.player_id) or self.get_primary_capital(self.player_id)

    @player_capital.setter
    def player_capital(self, province_id):
        self.capitals[self.player_id] = province_id

    @property
    def player_primary_capital(self):
        return self.primary_capitals.get(self.player_id)

    @player_primary_capital.setter
    def player_primary_capital(self, province_id):
        self.primary_capitals[self.player_id] = province_id

    @property
    def player_capital_was_lost(self):
        return bool(self.capital_was_lost.get(self.player_id, False))

    @player_capital_was_lost.setter
    def player_capital_was_lost(self, value):
        self.capital_was_lost[self.player_id] = bool(value)

    @property
    def enemy_capital(self):
        return self.capitals.get(self.enemy_id) or self.get_primary_capital(self.enemy_id)

    @enemy_capital.setter
    def enemy_capital(self, province_id):
        self.capitals[self.enemy_id] = province_id

    @property
    def enemy_primary_capital(self):
        return self.primary_capitals.get(self.enemy_id)

    @enemy_primary_capital.setter
    def enemy_primary_capital(self, province_id):
        self.primary_capitals[self.enemy_id] = province_id

    @property
    def enemy_capital_was_lost(self):
        return bool(self.capital_was_lost.get(self.enemy_id, False))

    @enemy_capital_was_lost.setter
    def enemy_capital_was_lost(self, value):
        self.capital_was_lost[self.enemy_id] = bool(value)

    @property
    def player_liege(self):
        return self.get_liege(self.player_id)

    @player_liege.setter
    def player_liege(self, liege_id):
        self.set_liege(self.player_id, liege_id)

    @property
    def enemy_liege(self):
        return self.get_liege(self.enemy_id)

    @enemy_liege.setter
    def enemy_liege(self, liege_id):
        self.set_liege(self.enemy_id, liege_id)

    @property
    def player_raise_cooldown(self):
        return self.get_raise_cooldown(self.player_id)

    @player_raise_cooldown.setter
    def player_raise_cooldown(self, days):
        self.set_raise_cooldown(self.player_id, days)

    @property
    def enemy_raise_cooldown(self):
        return self.get_raise_cooldown(self.enemy_id)

    @enemy_raise_cooldown.setter
    def enemy_raise_cooldown(self, days):
        self.set_raise_cooldown(self.enemy_id, days)

    def get_provinces_count(self, char_id):
        return sum(1 for p in PROVINCES.values() if p["owner"] == char_id)

    def get_sub_unit_home_province(self, sub_unit):
        """Returns the authoritative home province for an army sub-unit or contingent."""
        if not sub_unit:
            return self.player_capital
        flag = sub_unit.get("flag")
        if flag in PROVINCES:
            return flag
        vid = sub_unit.get("vassal_id")
        for p_k, v_list in self.vassals.items():
            if any(v.get("id") in (flag, vid) for v in v_list if isinstance(v, dict)):
                return p_k
        return self.player_capital

    def get_sub_unit_home_tile(self, sub_unit):
        """Finds the fief tile where a contingent was raised."""
        if not sub_unit:
            return get_province_capital_tile(self.player_capital)
        flag = sub_unit.get("flag")
        if flag in PROVINCES:
            return get_province_capital_tile(flag)

        vassal_id = sub_unit.get("vassal_id") or flag
        for v_list in self.vassals.values():
            vassal = next((v for v in v_list if v.get("id") == vassal_id), None)
            if vassal:
                tiles = vassal.get("tiles") or []
                if tiles:
                    return tuple(tiles[0])
                break

        for fief in self.fiefs.values():
            if fief.get("vassal_id") == vassal_id and fief.get("tiles"):
                return tuple(fief["tiles"][0])

        home_province = self.get_sub_unit_home_province(sub_unit)
        return get_province_capital_tile(home_province)

    def get_army_home_province(self, army_or_flag):
        """Finds the authoritative home province for an army or vassal flag."""
        flag = getattr(army_or_flag, "flag_origin", army_or_flag)
        if flag in PROVINCES:
            return flag
        for p_k, v_list in self.vassals.items():
            if any(v.get("id") == flag for v in v_list if isinstance(v, dict)):
                return p_k
        army_prov = getattr(army_or_flag, "province", None)
        if army_prov in PROVINCES:
            return army_prov
        owner = getattr(army_or_flag, "owner", self.player_id)
        return self.get_realm_capital(owner)

    def get_field_troops_for_province(self, province_id):
        """Returns the total number of troops currently deployed in the field originating from this province."""
        prov_vassal_ids = {v.get("id") for v in self.vassals.get(province_id, []) if isinstance(v, dict)}
        total = 0
        for a in self.armies:
            if a.troops <= 0:
                continue
            if getattr(a, "sub_units", None):
                sub_total = sum(u.get("troops", 0) for u in a.sub_units)
                ratio = (a.troops / float(sub_total)) if sub_total > 0 else 1.0
                for u in a.sub_units:
                    u_flag = u.get("flag")
                    u_vid = u.get("vassal_id")
                    if u_flag == province_id or u_vid in prov_vassal_ids or (not u_flag and not u_vid and a.province == province_id):
                        total += int(round(u.get("troops", 0) * ratio))
            else:
                if a.flag_origin == province_id or a.flag_origin in prov_vassal_ids or (getattr(a, "sub_flags", None) and province_id in a.sub_flags):
                    total += a.troops
                elif a.province == province_id and not a.flag_origin:
                    total += a.troops
        return total

    def return_troops_to_province_garrison(self, province_id, troops):
        """Returns troops to the province garrison, strictly clamped to physical maximum capacity."""
        prov = PROVINCES.get(province_id)
        if not prov:
            return
        p_max = prov.get("crown_levies_max", 0) + prov.get("vassal_levies_max", 0)
        if p_max <= 0:
            p_max = prov.get("levies_max", 780)
        prov["levies_max"] = p_max
        prov["levies_current"] = min(p_max, max(0, prov.get("levies_current", 0) + troops))

    def get_unraised_levies(self, char_id):
        return sum(min(p.get("levies_max", 100), p.get("levies_current", p.get("levies_max", 100))) for p in PROVINCES.values() if p.get("owner") == char_id)

    def get_field_troops(self, char_id):
        return sum(a.troops for a in self.armies if a.owner == char_id)

    def get_selected_army(self):
        for a in self.armies:
            if a.id == self.selected_army_id:
                return a
        return None

    def get_realm_capital(self, owner_id):
        """
        Returns the active capital province for any ruler. Handles emergency
        relocation and restoration generically for player and AI alike.
        """
        pri = self.get_primary_capital(owner_id)
        owned = [pid for pid, p in PROVINCES.items() if p.get("owner") == owner_id]
        if not owned:
            return pri

        was_lost = self.capital_was_lost.get(owner_id, False)
        if pri in owned:
            if was_lost:
                self.capital_was_lost[owner_id] = False
                self.capitals[owner_id] = pri
                if owner_id in CHARACTERS:
                    CHARACTERS[owner_id]["province"] = pri
                if owner_id == self.player_id:
                    self.logs.append(f"Royal Triumph! The seat of {get_display_name(owner_id)} has been restored to {PROVINCES[pri]['name']}!")
            else:
                self.capitals[owner_id] = pri
            return pri

        sorted_owned = sorted(
            owned,
            key=lambda p: (PROVINCES[p].get("levies_max", 0), len(PROVINCES[p].get("tiles", []))),
            reverse=True
        )
        new_cap = sorted_owned[0]
        if not was_lost:
            self.capital_was_lost[owner_id] = True
            if owner_id == self.player_id:
                p_old = PROVINCES.get(pri, {}).get("name", str(pri))
                p_new = PROVINCES[new_cap]["name"]
                self.logs.append(f"Catastrophe! {p_old} has fallen! {get_display_name(owner_id)} establishes an emergency capital in {p_new}!")
        self.capitals[owner_id] = new_cap
        if owner_id in CHARACTERS:
            CHARACTERS[owner_id]["province"] = new_cap
        return new_cap

    def set_realm_capital(self, owner_id, province_id):
        """Moves any ruler's primary capital to an owned province."""
        if province_id not in PROVINCES:
            return False
        if PROVINCES[province_id].get("owner") != owner_id:
            if owner_id == self.player_id:
                self.logs.append(f"Cannot relocate capital: {PROVINCES[province_id]['name']} is not under your control!")
            return False
        curr_cap = self.get_realm_capital(owner_id)
        if province_id == curr_cap:
            if owner_id == self.player_id:
                self.logs.append(f"{PROVINCES[province_id]['name']} is already the realm capital.")
            return False

        self.primary_capitals[owner_id] = province_id
        self.capitals[owner_id] = province_id
        self.capital_was_lost[owner_id] = False
        if owner_id in CHARACTERS:
            CHARACTERS[owner_id]["province"] = province_id
        if owner_id == self.player_id:
            p_name = PROVINCES[province_id]["name"]
            self.logs.append(f"Royal Decree: {get_display_name(owner_id)} relocates the Realm Capital to {p_name}! Couriers and war summons will depart from {p_name}.")
        return True

    def set_player_capital(self, province_id):
        """Backwards-compatible wrapper for moving the player's capital."""
        return self.set_realm_capital(self.player_id, province_id)

    # ---------------------------------------------------------
    # Feudal Subjugation & Dynamic Vassalage System
    # (No hard defeat / win conditions; living feudal hierarchy)
    # ---------------------------------------------------------
    def check_subjugation_and_vassalage(self):
        """
        Evaluates territorial control for every ruler: a landless sovereign
        bends the knee to whoever controls their former primary capital.
        """
        for r_id in self.get_active_rulers(include_player=True):
            owned = [pid for pid, p in PROVINCES.items() if p.get("owner") == r_id]
            if owned:
                continue
            if self.get_liege(r_id) is not None:
                continue
            seat = self.get_primary_capital(r_id)
            conqueror = PROVINCES.get(seat, {}).get("owner")
            if conqueror in CHARACTERS and conqueror != r_id:
                self.subjugate(r_id, conqueror)

    def subjugate(self, vassal_id, liege_id):
        """
        Generic feudal submission: any ruler can become the vassal of any
        other ruler. Updates metadata, titles, armies, and the story event.
        """
        if vassal_id == liege_id or vassal_id not in CHARACTERS or liege_id not in CHARACTERS:
            return False
        if self.get_liege(vassal_id) == liege_id:
            return False

        v_char = CHARACTERS[vassal_id]
        l_char = CHARACTERS[liege_id]
        self.set_liege(vassal_id, liege_id)
        self.war_status = "vassalage"

        seat = self.get_primary_capital(vassal_id)
        seat_short = PROVINCES.get(seat, {}).get("name", get_short_name(vassal_id)).split()[0]
        is_female = str(v_char.get("gender", "")).lower() == "female"
        ducal_prefix = self.get_noble_prefix(liege_id, "duchy", is_female)
        set_character_honorific(vassal_id, ducal_prefix)
        set_character_title(vassal_id, f"{ducal_prefix} of {seat_short}")
        set_character_realm(vassal_id, f"Duchy of {seat_short} (Vassal of {get_short_name(liege_id)})")
        v_char["liege"] = liege_id

        d_title_id = f"d_{vassal_id}"
        if hasattr(self, "titles") and d_title_id in self.titles:
            self.titles[d_title_id].holder_id = f"duke_{vassal_id}"

        # Only the submitting ruler's armies stand down; other realms continue.
        for a in list(self.armies):
            if a.owner != vassal_id:
                continue
            a.is_sieging = False
            a.target_city = None
            a.siege_progress = 0
            a.tile_path = []
            a.siege_intent = False
            a.siege_prep_days = 0
            a.siege_packup_days = 0
            h_prov = self.get_army_home_province(a)
            self.return_troops_to_province_garrison(h_prov, a.troops)
            if a in self.armies:
                self.armies.remove(a)

        liege_name = get_display_name(liege_id)
        vassal_name = get_display_name(vassal_id)
        rate_pct = int(round(self.tribute_rate * 100))
        if vassal_id == self.player_id:
            etype = "player_vassalized"
            title = "TREATY OF SUBMISSION: BENDING THE KNEE"
            text_lines = [
                f"All resistance has broken before {liege_name}.",
                f"{vassal_name} survives and meets the overlord at the Stone of Fealty.",
                f"{vassal_name} places hands between {liege_name}'s and swears fealty.",
                "",
                f"{liege_name} confirms the ancestral demesne under suzerainty. {rate_pct}% feudal",
                "tribute is owed every month, but the court, laws, and dynasty endure.",
                "",
                "Bide your time and enrich your holdings under the peace of the realm."
            ]
            button = "ACCEPT VASSALAGE & BIDE TIME"
        elif liege_id == self.player_id:
            etype = "enemy_vassalized"
            title = "TREATY OF SUBMISSION: VICTORY FEALTY"
            text_lines = [
                "The opposing armies have been crushed across the realm!",
                f"{vassal_name} surrenders their war banner and kneels before {liege_name}.",
                "",
                f"Under the terms of submission, {vassal_name} swears fealty to {liege_name}.",
                "",
                f"All lands now acknowledge {liege_name} as overlord.",
                f"{vassal_name} now pays {rate_pct}% feudal tribute and their warriors stand ready."
            ]
            button = "RULE THE UNITED REALM"
        else:
            etype = "vassalized"
            title = "TREATY OF SUBMISSION"
            text_lines = [
                f"{vassal_name} has been defeated by {liege_name}.",
                f"{vassal_name} kneels and swears fealty as a ducal vassal.",
                "",
                f"The realm now pays {rate_pct}% tribute to {liege_name}."
            ]
            button = "ACKNOWLEDGE FEALTY"

        self.subjugation_event = {
            "type": etype,
            "title": title,
            "liege_id": liege_id,
            "vassal_id": vassal_id,
            "liege_name": liege_name,
            "vassal_name": vassal_name,
            "text_lines": text_lines,
            "button_text": button,
        }
        self.logs.append(f"FEUDAL SUBMISSION: {vassal_name} has bent the knee to {liege_name}.")
        self.sync_conquered_rulers()
        return True

    # Submission between any two rulers goes through subjugate(vassal_id, liege_id).

    # ---------------------------------------------------------
    # Army Operations
    # ---------------------------------------------------------
    def is_province_levy_in_field(self, province_id, owner_id=None):
        """Checks if any active army originating from this province is currently in the field."""
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

    def is_province_vassal_levy_in_field(self, province_id, owner_id=None):
        """Checks if a province's FREE vassal levies are currently deployed in the field (1x Raise limit)."""
        if owner_id is None:
            prov = PROVINCES.get(province_id)
            if not prov:
                return False
            owner_id = prov.get("owner")
        for a in self.armies:
            if a.owner == owner_id and a.troops > 0 and getattr(a, "vassal_levies", 0) > 0:
                if a.flag_origin == province_id or (getattr(a, "sub_flags", None) and province_id in a.sub_flags):
                    return True
        return False

    def get_available_province_levies(self, province_id, owner_id=None):
        """
        Calculates available levies to muster (total_available, crown_portion, vassal_portion):
        - Personal / Royal Army (Crown Demesne): CAN ALWAYS be raised as they replenish (King pays upkeep).
        - Feudal Vassal Levies (FREE): Strictly limited to 1x deployment; blocked while active in field!
        """
        prov = PROVINCES.get(province_id)
        if not prov:
            return 0, 0, 0
        if owner_id is None:
            owner_id = prov.get("owner")

        current_men = prov.get("levies_current", 0)
        if current_men <= 0:
            return 0, 0, 0

        c_max = prov.get("crown_levies_max", 0)
        v_max = prov.get("vassal_levies_max", 0)
        t_max = prov.get("levies_max", c_max + v_max)
        if t_max <= 0:
            t_max = current_men

        vassal_in_field = self.is_province_vassal_levy_in_field(province_id, owner_id)
        if vassal_in_field:
            # Vassal fyrd already fighting in field: ALL available garrison troops up to c_max can be mobilized as Crown Troops!
            c_avail = min(current_men, c_max)
            v_avail = 0
        else:
            # Both Crown and Vassals at home: normal proportional split
            if c_max > 0 and t_max > 0:
                c_avail = min(current_men, int(round(current_men * (c_max / float(t_max)))))
            else:
                c_avail = 0
            v_avail = max(0, current_men - c_avail)

        total_avail = c_avail + v_avail
        return total_avail, c_avail, v_avail

    def raise_province_levy(self, province_id, ruler_id=None, is_emergency=False):
        """Raises available troops from a province and always returns (host_count, troops)."""
        if ruler_id is None:
            ruler_id = self.player_id
        prov = PROVINCES.get(province_id)
        if not prov:
            return 0, 0
        
        is_my_prov = (prov["owner"] == ruler_id)
        if not is_my_prov and self.get_liege(ruler_id) is not None:
            has_demesne = any(
                s.get("province") == province_id
                and s.get("is_crown_demesne")
                and not s.get("vassal_id")
                and s.get("owner", prov.get("owner")) == ruler_id
                for s in self.settlements.values()
            )
            if has_demesne or province_id == self.get_realm_capital(ruler_id):
                is_my_prov = True
        
        if not is_my_prov:
            return 0, 0

        # 3-Month Cooldown Check
        cd = prov.get("raise_cooldown_days", 0)
        if cd > 0 and not is_emergency:
            m_left = (cd + 29) // 30
            self.logs.append(f"Muster Cooldown! {prov['name']} cannot raise levies for {cd}d (~{m_left}m)!")
            return 0, 0

        tot_avail, c_troops, v_troops = self.get_available_province_levies(province_id, ruler_id)
        vassal_in_field = self.is_province_vassal_levy_in_field(province_id, ruler_id)

        if tot_avail <= 0:
            p_short = prov["name"].split()[0]
            if vassal_in_field:
                self.logs.append(f"Cannot muster {p_short}! Vassal fyrd already deployed in the field and no Crown troops available.")
            else:
                self.logs.append(f"No levies available to raise in {prov['name']}.")
            return 0, 0

        p_short = prov['name'].split()[0]
        capital_pid = self.get_realm_capital(ruler_id)
        cap_tile = PROV_CAPITAL_TILES.get(capital_pid, get_province_capital_tile(capital_pid))
        prov_cap_tile = PROV_CAPITAL_TILES.get(province_id, cap_tile)
        is_royal = (province_id == capital_pid)
        army_count = 0

        # 1. Crown Troops (Muster at Capital / Province Citadel)
        if c_troops > 0:
            self.army_id_counter += 1
            army_id = f"army_{self.army_id_counter}"
            c_name = f"{p_short} Royal Guard" if is_royal else f"{p_short} Crown Retinue"
            c_army = Army(army_id, ruler_id, province_id, c_troops, c_name,
                          flag_origin=province_id, rank=3 if is_royal else 2, tile=prov_cap_tile)
            c_army.crown_troops = c_troops
            c_army.vassal_levies = 0
            c_army.sub_units = [{
                "id": f"{army_id}_sub_crown",
                "name": c_name,
                "troops": c_troops,
                "source_type": "crown",
                "vassal_id": None,
                "flag": province_id
            }]
            if is_royal:
                # Royal Guard at King's Capital Citadel: Standing household retinue ready immediately (NO 30-day delay!)
                c_army.is_mustering = False
                c_army.muster_days = 0
                c_army.courier_en_route = False
                self.logs.append(f"Royal Guard standing ready! {c_troops:,} elite household guards mobilized at {prov['name']}.")
            else:
                c_army.is_mustering = True
                c_army.muster_days = 30
                c_army.courier_en_route = False
            self.armies.append(c_army)
            if ruler_id == self.player_id:
                self.selected_army_id = army_id
            army_count += 1

        # 2. Vassal Levies (Summon couriers to each landed vassal's primary fief tile)
        if v_troops > 0:
            prov_vassals = [v for v in self.vassals.get(province_id, []) if v.get("tiles")]
            if prov_vassals:
                total_v_contrib = sum(max(1, v.get("levy_contribution", 10)) for v in prov_vassals)
                rem_v = v_troops
                for idx, v in enumerate(prov_vassals):
                    if idx == len(prov_vassals) - 1:
                        share = rem_v
                    else:
                        share = max(1, int(round(v_troops * (v.get("levy_contribution", 10) / total_v_contrib))))
                        rem_v = max(0, rem_v - share)
                    
                    if share <= 0:
                        continue
                    
                    self.army_id_counter += 1
                    army_id = f"army_{self.army_id_counter}"
                    clean_n = self.get_character_clean_name(v.get("name", "Vassal"))
                    fief_tile = v["tiles"][0] if v.get("tiles") else prov_cap_tile
                    v_name = f"{clean_n}'s Levy"
                    
                    v_army = Army(army_id, ruler_id, province_id, share, v_name,
                                  flag_origin=v["id"], rank=1, tile=fief_tile)
                    v_army.vassal_id = v["id"]
                    v_army.crown_troops = 0
                    v_army.vassal_levies = share
                    v_army.sub_units = [{
                        "id": f"{army_id}_sub_vassal",
                        "name": v_name,
                        "troops": share,
                        "source_type": "vassal",
                        "vassal_id": v["id"],
                        "flag": v["id"]
                    }]
                    
                    # Dispatch courier to fief tile if distant from royal capital
                    if fief_tile != cap_tile:
                        c_path = find_shortest_tile_path(cap_tile, fief_tile, owner=ruler_id)
                        if c_path and len(c_path) > 1:
                            v_army.courier_en_route = True
                            v_army.courier_tile_path = list(c_path[1:])
                            v_army.courier_current_prov = capital_pid
                            v_army.courier_next_prov = province_id
                            total_courier_days = (len(c_path) - 1) * DAYS_PER_TILE
                            v_army.courier_days_left = max(1, total_courier_days)
                            v_army.is_mustering = False
                            v_army.muster_days = 30
                        else:
                            v_army.courier_en_route = False
                            v_army.is_mustering = True
                            v_army.muster_days = 30
                    else:
                        v_army.courier_en_route = False
                        v_army.is_mustering = True
                        v_army.muster_days = 30
                    
                    self.armies.append(v_army)
                    if ruler_id == self.player_id and not self.selected_army_id:
                        self.selected_army_id = army_id
                    army_count += 1
            else:
                self.army_id_counter += 1
                army_id = f"army_{self.army_id_counter}"
                v_army = Army(army_id, ruler_id, province_id, v_troops, f"{p_short} Fyrd",
                              flag_origin=province_id, rank=1, tile=prov_cap_tile)
                v_army.sub_units = [{
                    "id": f"{army_id}_sub_1",
                    "name": f"{p_short} Fyrd",
                    "troops": v_troops,
                    "source_type": "vassal",
                    "vassal_id": None,
                    "flag": province_id
                }]
                v_army.is_mustering = True
                v_army.muster_days = 30
                self.armies.append(v_army)
                army_count += 1

        prov["levies_current"] = max(0, prov["levies_current"] - tot_avail)
        prov["raise_cooldown_days"] = LEVY_RAISE_COOLDOWN_DAYS
        self.set_raise_cooldown(ruler_id, max(self.get_raise_cooldown(ruler_id), LEVY_RAISE_COOLDOWN_DAYS))
        self.logs.append(f"⚔ Feudal Summons: {get_display_name(ruler_id)} summons {tot_avail:,} men across {army_count} fief divisions in {prov['name']}!")
        return army_count, tot_avail

    def raise_all_levies(self, ruler_id=None):
        """Raises every available levy using the same fief summons for every ruler."""
        if ruler_id is None:
            ruler_id = self.player_id
        return self.raise_all_realm_levies(ruler_id)

    def raise_all_realm_levies(self, ruler_id, is_emergency=False):
        """Raises levies by fief and dispatches couriers for both player and AI."""
        if not is_emergency and self.get_raise_cooldown(ruler_id) > 0:
            return 0, 0

        raised_count = 0
        total_men = 0
        capital_pid = self.get_realm_capital(ruler_id)
        realm_provs = []
        for pid, prov in PROVINCES.items():
            if prov.get("owner") == ruler_id:
                realm_provs.append(pid)
            elif self.get_liege(ruler_id) is not None:
                has_demesne = any(
                    s.get("province") == pid
                    and (s.get("owner") == ruler_id or s.get("vassal_id") == ruler_id)
                    for s in self.settlements.values()
                )
                if has_demesne:
                    realm_provs.append(pid)

        for pid in realm_provs:
            count, men = self.raise_province_levy(pid, ruler_id, is_emergency=is_emergency)
            raised_count += count
            total_men += men

        if raised_count:
            self.set_raise_cooldown(
                ruler_id,
                max(self.get_raise_cooldown(ruler_id), LEVY_RAISE_COOLDOWN_DAYS)
            )
            cap_short = PROVINCES[capital_pid]["name"].split()[0] if capital_pid in PROVINCES else "the capital"
            r_name = get_display_name(ruler_id, "Ruler")
            realm_name = get_realm_name(ruler_id)
            self.logs.append(
                f"War Summons! {r_name} mobilizes {total_men:,} warriors across {realm_name} "
                f"(Couriers dispatch from {cap_short})!"
            )
        return raised_count, total_men

    def raise_all_enemy_levies(self, is_emergency=False):
        return self.raise_all_realm_levies(self.enemy_id, is_emergency=is_emergency)

    def rally_all_armies_to(self, target_province_id, ruler_id=None):
        if ruler_id is None:
            ruler_id = self.player_id
        player_armies = [a for a in self.armies if a.owner == ruler_id]
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
        
        # Aggregate sub_units from all joining hosts so each contingent preserves its home fief and origin
        merged_sub_units = []
        for a in armies_here:
            if getattr(a, "sub_units", None):
                merged_sub_units.extend(a.sub_units)
            else:
                merged_sub_units.append({
                    "id": f"{a.id}_sub",
                    "name": a.name,
                    "troops": a.troops,
                    "source_type": "crown" if getattr(a, "crown_troops", 0) > 0 else "vassal",
                    "vassal_id": getattr(a, "vassal_id", None),
                    "flag": a.flag_origin
                })
        dominant_army.sub_units = merged_sub_units
        
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
        if getattr(army, "is_demobilizing", False):
            return

        # If mustering or courier en route, cancel summons and refund troops directly to each contingent's home province!
        if army.is_mustering or army.courier_en_route:
            if getattr(army, "sub_units", None):
                for u in army.sub_units:
                    u_prov = self.get_sub_unit_home_province(u)
                    self.return_troops_to_province_garrison(u_prov, u.get("troops", 0))
            else:
                h_prov = self.get_army_home_province(army)
                self.return_troops_to_province_garrison(h_prov, army.troops)
            if army.courier_en_route:
                self.logs.append(f"Summons recalled for {army.name}. Royal courier stopped; {army.troops:,} men remain in garrison.")
            else:
                self.logs.append(f"Muster cancelled for {army.name}. {army.troops:,} men returned to garrison.")
            if army.id == self.selected_army_id:
                self.selected_army_id = None
            if army in self.armies:
                self.armies.remove(army)
            if army.owner == self.player_id:
                self.check_reset_player_raise_cooldown()
            return

        # Multi-Province / Multi-Fief Disband: Group contingents by their true home province!
        prov_contingents = {}
        if getattr(army, "sub_units", None):
            for u in army.sub_units:
                p_home = self.get_sub_unit_home_province(u)
                home_tile = self.get_sub_unit_home_tile(u)
                prov_contingents.setdefault((p_home, home_tile), []).append(u)
        else:
            p_home = self.get_army_home_province(army)
            home_tile = get_province_capital_tile(p_home)
            prov_contingents[(p_home, home_tile)] = [{
                "id": f"{army.id}_sub",
                "name": army.name,
                "troops": army.troops,
                "source_type": "crown" if getattr(army, "crown_troops", 0) > 0 else "vassal",
                "vassal_id": getattr(army, "vassal_id", None),
                "flag": army.flag_origin
            }]

        # Remove source army from field
        if army in self.armies:
            self.armies.remove(army)
        if army.id == self.selected_army_id:
            self.selected_army_id = None

        # Each provincial group disbands or marches back to its OWN home province
        for (p_home, home_tile), u_list in prov_contingents.items():
            p_troops = sum(u.get("troops", 0) for u in u_list)
            if p_troops <= 0:
                continue
            prov = PROVINCES.get(p_home)
            prov_name = prov["name"] if prov else "Homeland"
            
            at_home = getattr(army, "tile", None) == home_tile
            if at_home:
                self.return_troops_to_province_garrison(p_home, p_troops)
                p_short = prov_name.split()[0]
                self.logs.append(f"{p_short} contingents ({p_troops:,} men) returned to their fief and disbanded in {prov_name}.")
            else:
                self.army_id_counter += 1
                new_id = f"army_{self.army_id_counter}"
                p_short = prov_name.split()[0]
                c_crown = sum(u.get("troops", 0) for u in u_list if u.get("source_type") == "crown")
                c_vassal = p_troops - c_crown
                h_name = f"{p_short} Returning Fyrd"
                demob_host = Army(new_id, army.owner, army.province, p_troops, h_name, flag_origin=p_home, tile=army.tile)
                demob_host.crown_troops = c_crown
                demob_host.vassal_levies = c_vassal
                demob_host.sub_units = u_list
                demob_host.is_demobilizing = True
                demob_host.is_sieging = False
                demob_host.is_mustering = False
                demob_host.return_tile = home_tile
                
                tile_route = find_shortest_tile_path(army.tile, home_tile, owner=army.owner)
                if tile_route and len(tile_route) > 1:
                    demob_host.tile_path = list(tile_route[1:])
                    demob_host.move_progress = 0.0
                    self.armies.append(demob_host)
                    self.logs.append(f"{h_name} demobilizing! ({p_troops:,} men marching back to their fief in {prov_name}...)")
                elif getattr(army, "tile", None) == home_tile:
                    self.return_troops_to_province_garrison(p_home, p_troops)
                    self.logs.append(f"{h_name} returned to its fief and disbanded in {prov_name}.")
                else:
                    self.armies.append(demob_host)
                    self.logs.append(f"Cannot find a route for {h_name} to return to its fief in {prov_name}; the host remains deployed.")
        if army.owner == self.player_id:
            self.check_reset_player_raise_cooldown()

    def check_reset_player_raise_cooldown(self, ruler_id=None):
        """Resets a ruler's raise cooldown when no armies of that ruler remain."""
        if ruler_id is None:
            ruler_id = self.player_id
        has_army = any(a.owner == ruler_id for a in self.armies)
        if not has_army:
            cooldown_active = (self.get_raise_cooldown(ruler_id) > 0)
            self.set_raise_cooldown(ruler_id, 0)
            for p in PROVINCES.values():
                if p.get("owner") == ruler_id:
                    p["raise_cooldown_days"] = 0
            if cooldown_active and ruler_id == self.player_id:
                self.logs.append("All royal hosts stood down. Mobilization cooldown reset to 0.")

    def disband_all_armies(self, ruler_id=None):
        """Orders all armies belonging to ruler_id to disband or demobilize."""
        if ruler_id is None:
            ruler_id = self.player_id
        for a in list(self.armies):
            if a.owner == ruler_id:
                self.disband_army(a)
        self.check_reset_player_raise_cooldown(ruler_id)

    def cancel_army_siege(self, army, target_tile=None):
        if not army:
            return
        if not getattr(army, "is_sieging", False) and getattr(army, "siege_prep_days", 0) <= 0:
            return
        army.is_sieging = False
        army.siege_prep_days = 0
        army.siege_intent = False
        army.siege_packup_days = 15
        army.pending_march_target = target_tile
        army.tile_path = []
        army.move_progress = 0.0
        h_name = getattr(army, "siege_target_name", "the stronghold") or "the stronghold"
        self.logs.append(f"⛺ Siege Cancelled: {army.name} begins dismantling siege works around {h_name} (15 days to pack up before moving).")

    def order_army_siege_holding(self, army, target_tile=None):
        if not army:
            return
        if army.in_battle:
            self.logs.append(f"{army.name} is locked in combat and cannot organize siege works!")
            return
        if army.courier_en_route or army.is_mustering:
            self.logs.append(f"{army.name} is not fully assembled!")
            return
        if getattr(army, "siege_packup_days", 0) > 0:
            self.logs.append(f"{army.name} is currently dismantling camp ({army.siege_packup_days}d left) and cannot start a new siege yet!")
            return

        t = target_tile or army.tile
        cur_settlement = self.settlements.get(t)
        if not cur_settlement:
            self.logs.append(f"No fortification or borough at {t} to besiege!")
            return

        target_prov_id = CELL_TO_PROV.get(t) or army.province
        prov = PROVINCES.get(target_prov_id)
        if not prov:
            return

        occ = cur_settlement.get("occupied_by")
        if prov.get("owner") != army.owner and not self.are_hostile(army.owner, prov.get("owner")):
            self.declare_war(army.owner, prov["owner"], reason="Unprovoked Siege")
        is_enemy_prov = self.are_hostile(army.owner, prov["owner"])

        needs_siege = False
        if is_enemy_prov:
            if occ != army.owner:
                needs_siege = True
        else:
            if occ is not None and self.are_hostile(occ, prov["owner"]):
                needs_siege = True

        if not needs_siege:
            self.logs.append(f"{cur_settlement.get('name', 'Holding')} is already under friendly control. No siege required!")
            return

        h_name = cur_settlement.get("name", "Holding")
        army.siege_intent = True
        army.siege_prep_days = 15
        army.siege_packup_days = 0
        army.is_sieging = False
        army.siege_progress = 0
        army.target_city = t
        army.siege_target_tile = t
        army.siege_target_name = h_name
        army.tile_path = []
        army.move_progress = 0.0
        self.logs.append(f"⛺ Siege Order: {army.name} begins 15 days of siege preparation around {h_name}!")

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

        # 15-Day Decamp Rule: If sieging or in prep, must pack up for 15 days before departure!
        if getattr(army, "is_sieging", False) or getattr(army, "siege_prep_days", 0) > 0:
            self.cancel_army_siege(army, target_tile=target_tile)
            return

        if getattr(army, "siege_packup_days", 0) > 0:
            army.pending_march_target = target_tile
            self.logs.append(f"{army.name} is dismantling siege equipment ({army.siege_packup_days}d left). Will march to {target_tile} upon completion.")
            return

        if getattr(army, "tile", None) == target_tile:
            return
        
        path = find_shortest_tile_path(army.tile, target_tile, owner=army.owner)
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
    def update_ai_border_standoffs(self):
        """
        Monitors border standoff (SIAGA) between neutral AI realms.
        If two AI hosts face each other at the frontier for 20 days without escalation:
        AI A proposes 'DE-ESCALATE?', AI B agrees 'OK', and both simultaneously disband!
        """
        if not hasattr(self, "ai_standoff_days"):
            self.ai_standoff_days = {}
        if not hasattr(self, "ai_standoff_cooldown"):
            self.ai_standoff_cooldown = {}

        # Decrement cooldowns
        for pair in list(self.ai_standoff_cooldown.keys()):
            self.ai_standoff_cooldown[pair] -= 1
            if self.ai_standoff_cooldown[pair] <= 0:
                del self.ai_standoff_cooldown[pair]

        ai_list = [cid for cid in getattr(self, "ai_rulers", []) if cid in CHARACTERS and CHARACTERS[cid].get("alive", True)]
        if len(ai_list) < 2:
            return

        for i in range(len(ai_list)):
            for j in range(i + 1, len(ai_list)):
                r1 = ai_list[i]
                r2 = ai_list[j]
                pair_key = frozenset({r1, r2})

                if self.are_hostile(r1, r2):
                    self.ai_standoff_days[pair_key] = 0
                    continue

                if pair_key in self.ai_standoff_cooldown:
                    self.ai_standoff_days[pair_key] = 0
                    continue

                r1_provs = set(p for p, pdata in PROVINCES.items() if pdata.get("owner") == r1)
                r2_provs = set(p for p, pdata in PROVINCES.items() if pdata.get("owner") == r2)

                r1_border_armies = []
                for a in self.armies:
                    if a.owner == r1 and a.troops > 0 and not a.is_demobilizing:
                        if any(adj_p in r2_provs for adj_p in ADJACENCY.get(a.province, [])):
                            r1_border_armies.append(a)

                r2_border_armies = []
                for a in self.armies:
                    if a.owner == r2 and a.troops > 0 and not a.is_demobilizing:
                        if any(adj_p in r1_provs for adj_p in ADJACENCY.get(a.province, [])):
                            r2_border_armies.append(a)

                # Check if either AI realm is facing a player threat within 30 tiles / 30 days
                # If threatened by player, NEVER de-escalate or cancel forces!
                has_player_threat_r1 = False
                has_player_threat_r2 = False
                r1_tiles = [t for rp in r1_provs for t in PROV_TO_TILES.get(rp, [])]
                r2_tiles = [t for rp in r2_provs for t in PROV_TO_TILES.get(rp, [])]

                for pa in self.armies:
                    if pa.owner == self.player_id and pa.troops > 0 and not getattr(pa, "is_demobilizing", False):
                        pa_tile = getattr(pa, "tile", None) or get_province_capital_tile(pa.province)
                        if pa_tile:
                            if r1_tiles and min(max(abs(pa_tile[0] - t[0]), abs(pa_tile[1] - t[1])) for t in r1_tiles) <= 30:
                                has_player_threat_r1 = True
                            if r2_tiles and min(max(abs(pa_tile[0] - t[0]), abs(pa_tile[1] - t[1])) for t in r2_tiles) <= 30:
                                has_player_threat_r2 = True

                if has_player_threat_r1 or has_player_threat_r2:
                    self.ai_standoff_days[pair_key] = 0
                    continue

                if r1_border_armies and r2_border_armies:
                    curr_days = self.ai_standoff_days.get(pair_key, 0) + 1
                    self.ai_standoff_days[pair_key] = curr_days

                    if curr_days >= 20:
                        char1 = CHARACTERS.get(r1, {})
                        char2 = CHARACTERS.get(r2, {})
                        short1 = get_personal_name(r1)
                        short2 = get_personal_name(r2)
                        realm1 = char1.get("realm", "Dominion")
                        realm2 = char2.get("realm", "Sovereignty")

                        self.logs.append(f"📜 Frontier Diplomacy (Day 20): {short1} sends envoy to {short2}: 'DE-ESCALATE?' -> {short2} responds: 'OK'.")
                        self.logs.append(f"🕊 Treaty of De-escalation: {realm1} and {realm2} simultaneously stand down border hosts!")

                        # Both AIs simultaneously disband border armies facing each other
                        for a in list(r1_border_armies + r2_border_armies):
                            if a in self.armies and not getattr(a, "is_demobilizing", False) and not a.in_battle:
                                self.disband_army(a)

                        # Auto-cancel any couriers/messengers and mustering hosts for both AIs
                        for r in (r1, r2):
                            r_provs = set(p for p, pdata in PROVINCES.items() if pdata.get("owner") == r)
                            r_tiles = [t for rp in r_provs for t in PROV_TO_TILES.get(rp, [])]
                            
                            has_player_threat = False
                            for pa in self.armies:
                                if pa.owner == self.player_id and pa.troops > 0 and not getattr(pa, "is_demobilizing", False):
                                    pa_tile = getattr(pa, "tile", None) or get_province_capital_tile(pa.province)
                                    if pa_tile and r_tiles:
                                        d = min(max(abs(pa_tile[0] - t[0]), abs(pa_tile[1] - t[1])) for t in r_tiles)
                                        if d <= 30:
                                            has_player_threat = True
                                            break
                            
                            # If no direct player threat within 30 tiles/days, cancel all messengers and muster
                            if not has_player_threat:
                                for a in list(self.armies):
                                    if a.owner == r and (a.courier_en_route or a.is_mustering):
                                        self.disband_army(a)
                                if hasattr(self, "ai_border_vigilance") and r in self.ai_border_vigilance:
                                    self.ai_border_vigilance[r] = 0
                                if hasattr(self, "ai_vigilance_provs") and r in self.ai_vigilance_provs:
                                    self.ai_vigilance_provs.pop(r, None)

                        self.ai_standoff_days[pair_key] = 0
                        self.ai_standoff_cooldown[pair_key] = 30
                else:
                    self.ai_standoff_days[pair_key] = 0

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

        # Update AI frontier standoff & mutual de-escalation protocol (20-day limit)
        self.update_ai_border_standoffs()

        # Update Muster Cooldown Timers for all rulers.
        for r_id in list(self.raise_cooldowns.keys()):
            self.raise_cooldowns[r_id] = max(0, self.get_raise_cooldown(r_id) - 1)
        for p in PROVINCES.values():
            if p.get("raise_cooldown_days", 0) > 0:
                p["raise_cooldown_days"] = max(0, p["raise_cooldown_days"] - 1)

        # If no armies remain for any realm, ensure their raise cooldown resets to 0
        for r_id in self.get_active_rulers(include_player=True):
            if not any(a.owner == r_id for a in self.armies):
                if self.get_raise_cooldown(r_id) > 0:
                    self.set_raise_cooldown(r_id, 0)
                for p in PROVINCES.values():
                    if p.get("owner") == r_id:
                        p["raise_cooldown_days"] = 0

        arrived_courier_ids = set()

        # 1. Update Royal Couriers En Route
        for a in list(self.armies):
            if a.courier_en_route:
                a.courier_progress += (100.0 / DAYS_PER_TILE)
                if a.courier_progress >= 100.0:
                    a.courier_progress = 0.0
                    if getattr(a, "courier_tile_path", None):
                        a.courier_tile = a.courier_tile_path.pop(0)
                        if not a.courier_tile_path:
                            a.courier_en_route = False
                            a.is_mustering = True
                            a.courier_days_left = 0
                            arrived_courier_ids.add(a.id)
                            self.logs.append(f"✉ Royal Courier reached {a.name}'s seat! {a.troops:,} soldiers begin muster.")
                    elif getattr(a, "courier_path", None):
                        a.courier_current_prov = a.courier_path.pop(0)
                        if a.courier_path:
                            a.courier_next_prov = a.courier_path[0]
                        else:
                            a.courier_next_prov = None
                            a.courier_en_route = False
                            a.is_mustering = True
                            a.courier_days_left = 0
                            arrived_courier_ids.add(a.id)
                            p_short = PROVINCES.get(a.province, {}).get("name", "homeland").split()[0]
                            self.logs.append(f"✉ War summons reached {p_short}! {a.troops:,} {a.name} begins muster.")

                # Keep courier_days_left strictly synchronized with remaining tile travel
                if a.courier_en_route:
                    if getattr(a, "courier_tile_path", None):
                        rem_tiles = len(a.courier_tile_path)
                        a.courier_days_left = max(1, rem_tiles * DAYS_PER_TILE - int(a.courier_progress * DAYS_PER_TILE / 100.0))
                    elif getattr(a, "courier_path", None):
                        rem_hops = len(a.courier_path)
                        a.courier_days_left = max(1, rem_hops * DAYS_PER_TILE - int(a.courier_progress * DAYS_PER_TILE / 100.0))
                    else:
                        a.courier_days_left = max(0, a.courier_days_left - 1)

        # 2. Update Muster Preparation Days (only for armies where courier has already arrived)
        for a in list(self.armies):
            if a.is_mustering and not a.courier_en_route and a.id not in arrived_courier_ids:
                a.muster_days -= 1
                if a.muster_days <= 0:
                    a.is_mustering = False
                    self.logs.append(f"⚔ {a.name} is fully assembled and battle-ready!")

        # Update Siege Preparation & Decamp Timers (15-Day Cycles)
        for a in list(self.armies):
            if getattr(a, "siege_prep_days", 0) > 0 and not a.in_battle:
                a.siege_prep_days -= 1
                if a.siege_prep_days <= 0:
                    a.is_sieging = True
                    a.siege_progress = 0
                    h_name = getattr(a, "siege_target_name", "the stronghold")
                    self.logs.append(f"⚔ Siege Works Complete! {a.name} has launched the active siege against {h_name}!")

            elif getattr(a, "siege_packup_days", 0) > 0 and not a.in_battle:
                a.siege_packup_days -= 1
                if a.siege_packup_days <= 0:
                    self.logs.append(f"⛺ Camp Dismantled! {a.name} has finished breaking siege camp and is free to move.")
                    dest = getattr(a, "pending_march_target", None)
                    a.pending_march_target = None
                    if dest and dest != getattr(a, "tile", None):
                        self.order_army_march_to_tile(a, dest)

        # Update Army Movements & Combat
        self.update_armies()

        # Update Supply Wagons & Logistics
        self.update_supply_wagons()

        # Update Expeditionary Status & Starvation Attrition
        self.update_expeditionary_and_starvation()

        # Dynamic Feudal Subjugation check (No game over / defeat screen)
        self.check_subjugation_and_vassalage()
        self.sync_conquered_rulers()

        # AI Behavior (Responsive 2-day tactical cycle)
        self.ai_timer -= 1
        if self.ai_timer <= 0:
            self.ai_timer = 2
            self.ai_routine()

    def monthly_tick(self):
        # 1. Vassal net savings for autonomy fund
        for pid, prov in PROVINCES.items():
            for v in self.vassals.get(pid, []):
                st = get_vassal_landed_status(self, v, pid)
                if st["is_landed"]:
                    v["gold"] = round(v.get("gold", 25) + st["net_savings"], 1)
                    v["tax_contribution"] = st["tax_paid"]
                    v["levy_contribution"] = st["levy_contribution"]
                else:
                    v["tax_contribution"] = 0
                    v["levy_contribution"] = 0

        # Maintain standardized AI feudal laws uniformly across every AI realm.
        standardize_all_ai_laws(self)

        # 2. Holdings Recruitment Tick (City, Fort, Barracks contribute recruits to levy pool)
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

            # Manpower ceiling: Garrison can only replenish up to (max_capacity - field_troops_already_raised)
            p_max = prov.get("crown_levies_max", 0) + prov.get("vassal_levies_max", 0)
            if p_max <= 0:
                p_max = prov.get("levies_max", 780)
            field_troops = self.get_field_troops_for_province(pid)
            garrison_cap = max(0, p_max - field_troops)

            if prov.get("levies_current", 0) < garrison_cap:
                if htype == "city":
                    prov["levies_current"] = min(garrison_cap, prov.get("levies_current", 0) + 3)
                elif htype == "fort":
                    prov["levies_current"] = min(garrison_cap, prov.get("levies_current", 0) + 3)
                elif htype == "barrack":
                    lvl = sdata.get("level", 0)
                    bstats = get_barrack_stats(lvl)
                    prov["levies_current"] = min(garrison_cap, prov.get("levies_current", 0) + bstats["recruits"])

        # 3. Synchronize realm economy for every ruler (player and AI identically).
        from game.systems.economy import get_realm_finances
        finances = {}
        for cid in self.get_active_rulers(include_player=True):
            fin = get_realm_finances(self, cid)
            finances[cid] = fin
            CHARACTERS[cid]["gold"] = max(0.0, round(CHARACTERS[cid].get("gold", 0) + fin["net_monthly"], 1))
            CHARACTERS[cid]["prestige"] = CHARACTERS[cid].get("prestige", 0) + 1
            CHARACTERS[cid]["piety"] = CHARACTERS[cid].get("piety", 0) + 1

        # Feudal Suzerainty & Vassalage Tributes for every vassal ruler.
        for cid, fin in finances.items():
            liege_id = self.get_liege(cid)
            if not liege_id or liege_id not in CHARACTERS:
                continue
            trib = fin.get("total_tribute", 0)
            if trib <= 0:
                continue
            CHARACTERS[liege_id]["gold"] = round(CHARACTERS[liege_id].get("gold", 0) + trib, 1)
            if cid == self.player_id or liege_id == self.player_id:
                liege_n = get_display_name(liege_id)
                vassal_n = get_display_name(cid)
                self.logs.append(f"Feudal tribute: {vassal_n} pays {trib}g to {liege_n}.")

        # Vassal Feudal Autonomy: Vassals autonomously build whatever they want on their fiefs!
        # If they have enough gold and free tiles in their territory, they erect Cities (600g), Barracks (800g), or Forts (1000g)!
        for pid in PROVINCES:
            v_list = self.vassals.get(pid, [])
            for v in v_list:
                v_gold = v.get("gold", 0)
                city_cost = BUILDING_SPECS["city"]["cost"]       # 600
                barrack_cost = BUILDING_SPECS["barrack"]["cost"] # 800
                fort_cost = BUILDING_SPECS["fort"]["cost"]       # 1000

                if v_gold < min(city_cost, 400):
                    continue

                # Check ALL fiefs held by this vassal anywhere across the realm!
                v_fiefs = [f for f in self.fiefs.values() if (f.get("holder") == v["name"] or f.get("vassal_id") == v.get("id"))]

                # Also include un-fiefed tiles held directly by this vassal if any
                direct_tiles = [t for t in v.get("tiles", []) if t not in self.settlements]
                if direct_tiles:
                    tiles_by_prov = {}
                    for dt in direct_tiles:
                        p_dt = CELL_TO_PROV.get(dt, pid)
                        tiles_by_prov.setdefault(p_dt, []).append(dt)
                    for p_dt, dt_list in tiles_by_prov.items():
                        v_fiefs.append({
                            "name": f"Domain of {self.get_character_clean_name(v['name']).split()[0]}",
                            "province": p_dt,
                            "tiles": dt_list
                        })

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

                # 4. Check Barracks Upgrade Option for existing barracks
                all_v_tiles = list(v.get("tiles", []))
                for f in v_fiefs:
                    for t in f.get("tiles", []):
                        if t not in all_v_tiles:
                            all_v_tiles.append(t)

                for t in all_v_tiles:
                    s_cur = self.settlements.get(t)
                    if s_cur and s_cur.get("type") == "barrack" and (s_cur.get("vassal_id") == v.get("id") or s_cur.get("lord") == v["name"]):
                        cur_lvl = s_cur.get("level", 1) or 1
                        if cur_lvl < 5:
                            next_lvl = cur_lvl + 1
                            up_cost = BARRACK_UPGRADE_COSTS.get(next_lvl, 400)
                            if v_gold >= up_cost:
                                f_dummy = {"province": s_cur.get("province", pid), "name": s_cur.get("name", "Barracks")}
                                possible_builds.append(("upgrade_barrack", up_cost, [t], f_dummy))

                if not possible_builds:
                    continue

                # Autonomous Decision:
                # If vassal has no city in their fiefs yet, they strongly prefer building a City to generate wealth!
                has_city = any(self.settlements.get(t, {}).get("type") in ("city", "town") for f in v_fiefs for t in f.get("tiles", []))
                if not has_city:
                    city_choices = [b for b in possible_builds if b[0] == "city"]
                    choice = city_choices[0] if city_choices else random.choice(possible_builds)
                else:
                    # Prefer higher-tier investments if wealthy
                    if v_gold >= fort_cost and any(b[0] == "fort" for b in possible_builds):
                        fort_choices = [b for b in possible_builds if b[0] == "fort"]
                        choice = fort_choices[0]
                    else:
                        choice = random.choice(possible_builds)

                b_type, b_cost, chosen_tiles, chosen_fief = choice
                f_pid = chosen_fief.get("province", pid)

                if b_type == "upgrade_barrack":
                    t = chosen_tiles[0]
                    s_cur = self.settlements[t]
                    new_vlvl = (s_cur.get("level", 1) or 1) + 1
                    s_cur["level"] = new_vlvl
                    s_cur["max_unlocked_level"] = max(s_cur.get("max_unlocked_level", 0), new_vlvl)
                    v["gold"] = round(v["gold"] - b_cost, 1)
                    sync_province_holdings_stats(self, f_pid)
                    st_v = get_vassal_landed_status(self, v, pid)
                    v["tax_contribution"] = st_v["tax_paid"]
                    v["levy_contribution"] = st_v["levy_contribution"]
                    self.logs.append(f"Feudal Autonomy: {v['name']} has upgraded {s_cur['name']} to Level {s_cur['level']} ({b_cost}g) in {PROVINCES.get(f_pid, {}).get('name', 'the realm')}!")
                    continue

                v["gold"] = round(v["gold"] - b_cost, 1)

                self.settlement_id_counter += 1
                s_id = f"settlement_{self.settlement_id_counter}"
                v_first = self.get_character_clean_name(v["name"]).split()[0]
                if b_type == "city":
                    s_name = f"{v_first}'s Borough"
                elif b_type == "fort":
                    s_name = f"{v_first}'s Stronghold"
                else:
                    s_name = f"{v_first}'s Barracks"

                for t in chosen_tiles:
                    self.settlements[t] = {
                        "id": s_id,
                        "province": f_pid,
                        "type": b_type,
                        "name": s_name,
                        "lord": v["name"],
                        "vassal_id": v["id"],
                        "is_crown_demesne": False,
                        "is_crown_fief": False,
                        "level": 0,
                        "max_unlocked_level": 0
                    }
                    if t not in v.get("tiles", []):
                        v.setdefault("tiles", []).append(t)

                if not v.get("city_name"):
                    v["city_name"] = s_name

                # Synchronize province stats and vassal stats immediately
                sync_province_holdings_stats(self, f_pid)
                if f_pid != pid:
                    sync_province_holdings_stats(self, pid)
                st_v = get_vassal_landed_status(self, v, pid)
                v["tax_contribution"] = st_v["tax_paid"]
                v["levy_contribution"] = st_v["levy_contribution"]

                b_spec = BUILDING_SPECS[b_type]
                self.logs.append(f"Feudal Autonomy: {v['name']} has autonomously constructed a {b_spec['name']} ({b_cost}g) in {chosen_fief['name']} ({PROVINCES.get(f_pid, {}).get('name', 'the realm')})!")

        # 4. Monthly Logistics & Supply Wagons (Deliver Supplies & Reinforcements directly to Armies)
        for a in list(self.armies):
            self.rebalance_army_sub_units(a)
            if a.troops > 0 and not getattr(a, "is_demobilizing", False) and not getattr(a, "is_mustering", False):
                has_active_wagon = any(w.target_army_id == a.id for w in self.supply_wagons)
                if not has_active_wagon:
                    self.dispatch_supply_wagon(a)


    # ---------------------------------------------------------
    # FEUDAL ARMY COMPOSITION, MERGE & SPLIT (CK2-Style)
    # ---------------------------------------------------------
    def merge_armies_at_tile(self, tile, owner_id):
        """Merges all friendly armies on the specified tile into one dominant host."""
        armies_here = [
            a for a in self.armies 
            if getattr(a, "tile", None) == tile and a.owner == owner_id 
            and not a.in_battle and not a.is_demobilizing and not getattr(a, "courier_en_route", False)
            and not getattr(a, "is_mustering", False)
        ]
        if len(armies_here) < 2:
            return None
        
        dominant = max(armies_here, key=lambda a: (a.rank, a.troops))
        merged_names = []
        for a in list(armies_here):
            if a != dominant:
                dominant.merge_army(a)
                merged_names.append(a.name)
                if a in self.armies:
                    self.armies.remove(a)
        
        self.selected_army_id = dominant.id
        self.logs.append(f"⚔ Feudal Union: Merged {len(merged_names)+1} forces at {tile}! {dominant.name} now marshals {dominant.troops:,} men ({len(dominant.sub_units)} contingents).")
        return dominant

    def split_army(self, source_army_id, unit_ids_to_split, new_name=None):
        """Detaches selected sub-units from source army into a new independent host on the same tile."""
        src = next((a for a in self.armies if a.id == source_army_id), None)
        if not src or not unit_ids_to_split:
            return None

        # If source only has 1 sub-unit, delegate to split_army_in_half
        if len(getattr(src, "sub_units", [])) <= 1:
            return self.split_army_in_half(source_army_id)
        
        detached = src.split_sub_units(unit_ids_to_split)
        if not detached:
            return None
        
        self.army_id_counter += 1
        new_id = f"army_{self.army_id_counter}"
        det_troops = sum(u.get("troops", 0) for u in detached)
        
        first_u = detached[0]
        n_name = new_name or f"{first_u.get('name', 'Detached')} Host"
        flag = first_u.get("flag", src.flag_origin)
        
        new_host = Army(new_id, src.owner, src.province, det_troops, n_name, flag_origin=flag, rank=1, tile=src.tile)
        new_host.sub_units = detached
        new_host.vassal_id = first_u.get("vassal_id")
        new_host.recalc_troops()
        
        # Dynamically recalculate heraldic sub_flags for both hosts
        src.sub_flags = list({u.get("flag") for u in src.sub_units if u.get("flag") and u.get("flag") != src.flag_origin})
        new_host.sub_flags = list({u.get("flag") for u in new_host.sub_units if u.get("flag") and u.get("flag") != new_host.flag_origin})

        self.armies.append(new_host)
        self.selected_army_id = new_host.id
        self.selected_army_ids = [new_host.id]
        self.selected_province = new_host.province
        self.selected_settlement = None
        self.logs.append(f"➦ Split Host: Detached {det_troops:,} men from {src.name} into '{new_host.name}'.")
        return new_host

    def split_army_in_half(self, source_army_id):
        """Splits an army exactly in half (50/50), whether it has 1 or multiple sub-units."""
        src = next((a for a in self.armies if a.id == source_army_id), None)
        if not src or src.troops < 2:
            self.logs.append("⚠️ Host too small to divide (minimum 2 men).")
            return None
        
        sub_u = getattr(src, "sub_units", [])
        if len(sub_u) > 1:
            half_target = src.troops // 2
            acc = 0
            det_ids = []
            for u in sub_u:
                acc += u.get("troops", 0)
                det_ids.append(u.get("id"))
                if acc >= half_target and len(det_ids) < len(sub_u):
                    break
            if not det_ids or len(det_ids) == len(sub_u):
                det_ids = [sub_u[0]["id"]]
            return self.split_army(src.id, det_ids)
        else:
            # Single sub-unit: divide troops in half!
            u = sub_u[0] if sub_u else None
            half = src.troops // 2
            rem = src.troops - half
            if u:
                u["troops"] = rem
            src.troops = rem
            if getattr(src, "vassal_levies", 0) > 0:
                src.vassal_levies = rem
            else:
                src.crown_troops = rem
            
            self.army_id_counter += 1
            new_id = f"army_{self.army_id_counter}"
            n_name = f"{src.name} II"
            new_u = {
                "id": f"{new_id}_sub_1",
                "name": f"{u.get('name', src.name) if u else src.name} (Detached)",
                "troops": half,
                "vassal_id": getattr(src, "vassal_id", None),
                "source_type": u.get("source_type", "feudal") if u else "feudal",
                "flag": getattr(src, "flag_origin", None)
            }
            new_host = Army(new_id, src.owner, src.province, half, n_name, flag_origin=src.flag_origin, rank=src.rank, tile=src.tile)
            new_host.sub_units = [new_u]
            new_host.vassal_id = getattr(src, "vassal_id", None)
            new_host.recalc_troops()
            self.armies.append(new_host)
            self.selected_army_id = new_host.id
            self.selected_army_ids = [new_host.id]
            self.selected_province = new_host.province
            self.selected_settlement = None
            self.logs.append(f"⚡ Split in Half: {src.name} halved! New host '{new_host.name}' ({half:,} men) ready at {src.tile}.")
            return new_host

    def make_army_from_garrison(self, tile=None, troops=None, name=None, ruler_id=None):
        """Forms a new standing army host directly from unraised realm garrison."""
        if ruler_id is None:
            ruler_id = self.player_id
        capital_pid = self.get_realm_capital(ruler_id)
        if tile is None:
            tile = PROV_CAPITAL_TILES.get(capital_pid, get_province_capital_tile(capital_pid))
        
        total_avail = sum(p.get("levies_current", 0) for p in PROVINCES.values() if p.get("owner") == ruler_id)
        if total_avail <= 0:
            self.logs.append("Cannot create army: No unraised garrison recruits currently available in the realm.")
            return None
        
        summon_troops = min(total_avail, troops) if troops else total_avail
        
        # Deduct from provinces
        rem = summon_troops
        for p in PROVINCES.values():
            if p.get("owner") == ruler_id and p.get("levies_current", 0) > 0:
                d = min(p["levies_current"], rem)
                p["levies_current"] -= d
                rem -= d
                if rem <= 0:
                    break
        
        self.army_id_counter += 1
        new_id = f"army_{self.army_id_counter}"
        a_name = name or f"Royal Army {self.army_id_counter}"
        new_host = Army(new_id, ruler_id, capital_pid, summon_troops, a_name, flag_origin=capital_pid, rank=2, tile=tile)
        new_host.crown_troops = summon_troops
        new_host.vassal_levies = 0
        new_host.sub_units = [{
            "id": f"{new_id}_reg_1",
            "name": f"{a_name} Regulars",
            "troops": summon_troops,
            "source_type": "crown",
            "vassal_id": None,
            "flag": capital_pid
        }]
        self.armies.append(new_host)
        self.selected_army_id = new_host.id
        self.logs.append(f"⚔ Formed new host: '{new_host.name}' ({summon_troops:,} men) assembled at {tile}!")
        return new_host

    # ---------------------------------------------------------
    # UNIVERSAL RENAMING SYSTEM (Characters, Titles, Fiefs, Armies)
    # ---------------------------------------------------------
    def open_rename_modal(self, entity_type, entity_id, current_name=None):
        """Opens universal rename modal for character, title, settlement, or army."""
        if not current_name:
            if entity_type == "character":
                current_name = CHARACTERS.get(entity_id, {}).get("name", "Noble")
            elif entity_type == "title":
                current_name = self.titles[entity_id].name if entity_id in getattr(self, "titles", {}) else "Title"
            elif entity_type == "settlement":
                current_name = self.settlements.get(entity_id, {}).get("name", "Holding")
            elif entity_type == "army":
                a = next((arm for arm in self.armies if arm.id == entity_id), None)
                current_name = a.name if a else "Army"
            else:
                current_name = ""
        self.rename_modal = {
            "active": True,
            "type": entity_type,
            "id": entity_id,
            "text": str(current_name)
        }

    def commit_rename(self):
        """Saves new name for the active rename target."""
        if not getattr(self, "rename_modal", None) or not self.rename_modal.get("active"):
            return
        m = self.rename_modal
        new_n = m.get("text", "").strip()
        if not new_n:
            self.rename_modal = None
            return
        
        etype = m.get("type")
        eid = m.get("id")

        if etype == "character":
            if eid in CHARACTERS:
                char = CHARACTERS[eid]
                honorific = get_honorific(eid)
                if honorific and new_n.startswith(honorific + " "):
                    set_character_honorific(
                        eid, honorific, new_n[len(honorific) + 1:].strip()
                    )
                else:
                    char["honorific"] = ""
                    char["personal_name"] = new_n
                    char["name"] = new_n
            for vlist in self.vassals.values():
                for v in vlist:
                    if v.get("id") == eid or v.get("char_id") == eid:
                        v["name"] = new_n
            if eid == self.player_id:
                self.player["name"] = new_n
            elif eid == self.enemy_id:
                self.enemy["name"] = new_n
            self.logs.append(f"✎ Renamed character to '{new_n}'.")

        elif etype == "title":
            if hasattr(self, "titles") and eid in self.titles:
                self.titles[eid].name = new_n
                self.logs.append(f"✎ Renamed landed title to '{new_n}'.")

        elif etype == "settlement":
            if eid in self.settlements:
                self.settlements[eid]["name"] = new_n
                self.logs.append(f"✎ Renamed holding to '{new_n}'.")

        elif etype == "army":
            for a in self.armies:
                if a.id == eid:
                    a.name = new_n
                    self.logs.append(f"✎ Renamed host to '{new_n}'.")
                    break

        self.rename_modal = None

    def yearly_tick(self):
        for cid in self.get_active_rulers(include_player=True):
            char = CHARACTERS.get(cid)
            if char:
                char["age"] = char.get("age", 0) + 1
        region = (self.scenario or {}).get("region_name", "the realm")
        self.logs.append(f"AD {self.year}: The chronicle of {region} continues.")

    def update_armies(self):
        # 0. Co-location & Territorial Incursion Check (Multi-Realm Sovereign Borders)
        for a in self.armies:
            if not getattr(a, "is_demobilizing", False) and a.troops > 0:
                # 0a. Check territory breach (foreign sovereign province)
                p_id = getattr(a, "province", None)
                p_owner = PROVINCES.get(p_id, {}).get("owner")
                if p_owner and p_owner != a.owner and not self.are_hostile(a.owner, p_owner):
                    self.declare_war(a.owner, p_owner, reason="Border Incursion")

                # 0b. Check co-located hostile/neutral armies on same tile
                if getattr(a, "tile", None) is not None:
                    opponents = [o for o in self.armies if getattr(o, "tile", None) == a.tile and o.owner != a.owner and o.troops > 0]
                    for o in opponents:
                        if not self.are_hostile(a.owner, o.owner):
                            self.declare_war(a.owner, o.owner, reason="Troop Clash")

        # Sanity check: Clear in_battle flag for any army that has no enemy on its tile
        for a in self.armies:
            opponents = [o for o in self.armies if getattr(o, "tile", None) == getattr(a, "tile", None) and self.are_hostile(a.owner, o.owner) and o.troops > 0]
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
                    new_prov = CELL_TO_PROV.get(a.tile, a.province)
                    if new_prov != a.province:
                        a.province = new_prov
                        prov_owner = PROVINCES.get(new_prov, {}).get("owner")
                        if prov_owner and prov_owner != a.owner and not getattr(a, "is_demobilizing", False):
                            if not self.are_hostile(a.owner, prov_owner):
                                self.declare_war(a.owner, prov_owner, reason="Border Incursion")
                    a.move_progress = 0.0

                    # Check peace-break if stepping onto a foreign army's tile
                    if not getattr(a, "is_demobilizing", False):
                        other_armies = [e for e in self.armies if getattr(e, "tile", None) == a.tile and e.owner != a.owner and e.troops > 0]
                        for other in other_armies:
                            if not self.are_hostile(a.owner, other.owner):
                                self.declare_war(a.owner, other.owner, reason="Troop Clash")

                    # INTERCEPTION CHECK: if enemy is on this tile, stop and fight
                    blockers = [e for e in self.armies
                                if getattr(e, "tile", None) == a.tile and self.are_hostile(a.owner, e.owner) and e.troops > 0]
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
                        if a.is_demobilizing:
                            h_prov = self.get_army_home_province(a)
                            self.return_troops_to_province_garrison(h_prov, a.troops)
                            prov = PROVINCES.get(h_prov)
                            p_name = prov['name'] if prov else "homeland"
                            self.logs.append(f"{a.name} returned to its fief in {p_name}. {a.troops:,} men disbanded into the garrison.")
                            if a.id == self.selected_army_id:
                                self.selected_army_id = None
                            if a in self.armies:
                                self.armies.remove(a)
                            if a.owner == self.player_id:
                                self.check_reset_player_raise_cooldown()
                        elif not a.is_demobilizing:
                            pass  # Merging is strictly manual (CK2 style: player must click MERGE)

        # 2. Check Battles (Opposing armies on same tile)
        all_army_tiles = set(getattr(a, "tile", None) for a in self.armies if getattr(a, "tile", None) is not None)
        for tile in all_army_tiles:
            # Merging is strictly manual via UI/ContextMenu (never auto-merge on tick)
            armies_on_tile = [a for a in self.armies if getattr(a, "tile", None) == tile and a.troops > 0]
            if len(armies_on_tile) < 2:
                for a in armies_on_tile:
                    a.in_battle = False
                continue

            # Ensure any co-located armies from different owners declare war
            for i, a1_cand in enumerate(armies_on_tile):
                for a2_cand in armies_on_tile[i+1:]:
                    if a1_cand.owner != a2_cand.owner and not self.are_hostile(a1_cand.owner, a2_cand.owner):
                        self.declare_war(a1_cand.owner, a2_cand.owner, reason="Troop Clash")

            # Find hostile pair
            hostile_pair = None
            for i, a1_cand in enumerate(armies_on_tile):
                for a2_cand in armies_on_tile[i+1:]:
                    if a1_cand.owner != a2_cand.owner and self.are_hostile(a1_cand.owner, a2_cand.owner):
                        hostile_pair = (a1_cand, a2_cand)
                        break
                if hostile_pair:
                    break

            if not hostile_pair:
                for a in armies_on_tile:
                    a.in_battle = False
                continue

            a1, a2 = hostile_pair
            # CK2 Rule: All friendly armies on this tile fight together as one unified force in combat!
            p1_list = [a for a in armies_on_tile if a.owner == a1.owner and a.troops > 0]
            p2_list = [a for a in armies_on_tile if a.owner == a2.owner and a.troops > 0]

            # Lock ALL participating hosts in combat and halt movement/siege
            for a in p1_list + p2_list:
                a.in_battle = True
                a.tile_path = []
                a.move_progress = 0.0
                a.is_sieging = False
                a.is_demobilizing = False
                a.courier_en_route = False
                a.is_mustering = False

            # Pool total strength and best general martial for each side
            total_t1 = sum(a.troops for a in p1_list)
            total_t2 = sum(a.troops for a in p2_list)

            martial_1 = max(CHARACTERS.get(a.owner, {}).get("stats", {}).get("martial", 10) for a in p1_list)
            martial_2 = max(CHARACTERS.get(a.owner, {}).get("stats", {}).get("martial", 10) for a in p2_list)

            # Combined attack damage: Side 1 strikes Side 2 with full combined power, and vice versa!
            dmg_to_p2 = max(1, int(total_t1 * 0.08 * (1 + martial_1 * 0.02)) + random.randint(10, 50))
            dmg_to_p1 = max(1, int(total_t2 * 0.08 * (1 + martial_2 * 0.02)) + random.randint(10, 50))

            # Helper to distribute casualties proportionally across hosts and their sub-units
            def apply_side_damage(army_list, total_side_troops, total_dmg):
                if total_side_troops <= 0:
                    return
                for a in army_list:
                    a_share = int(round(total_dmg * (a.troops / float(total_side_troops)))) if total_side_troops > 0 else 0
                    actual_loss = min(a.troops, max(1 if total_dmg > 0 and a.troops > 0 else 0, a_share))
                    prev_t = a.troops
                    prev_c = min(prev_t, getattr(a, "crown_troops", 0))
                    c_loss = int(round(actual_loss * (prev_c / float(prev_t)))) if prev_t > 0 else 0
                    c_loss = min(prev_c, c_loss)
                    v_loss = actual_loss - c_loss

                    a.troops = max(0, prev_t - actual_loss)
                    a.crown_troops = max(0, prev_c - c_loss)
                    a.vassal_levies = max(0, a.troops - a.crown_troops)

                    # Distribute casualties across constituent sub-units
                    sub_u = getattr(a, "sub_units", [])
                    if sub_u and prev_t > 0:
                        rem = actual_loss
                        for u in sub_u:
                            u_tr = u.get("troops", 0)
                            u_l = int(round(actual_loss * (u_tr / float(prev_t))))
                            u_l = min(u_tr, min(rem, u_l))
                            u["troops"] = max(0, u_tr - u_l)
                            rem -= u_l
                        if rem > 0:
                            for u in sub_u:
                                d = min(u.get("troops", 0), rem)
                                u["troops"] -= d
                                rem -= d
                                if rem <= 0:
                                    break
                    a.recalc_troops()

            apply_side_damage(p1_list, total_t1, dmg_to_p1)
            apply_side_damage(p2_list, total_t2, dmg_to_p2)

            # Check for destroyed hosts
            wiped_1 = [a for a in p1_list if a.troops <= 0]
            wiped_2 = [a for a in p2_list if a.troops <= 0]

            for a in wiped_1 + wiped_2:
                if a in self.armies:
                    self.armies.remove(a)
                if a.id == self.selected_army_id:
                    self.selected_army_id = None

            survivors_1 = [a for a in p1_list if a.troops > 0]
            survivors_2 = [a for a in p2_list if a.troops > 0]

            p_name = PROVINCES.get(a1.province, {}).get("name", "the realm")
            name1 = CHARACTERS.get(a1.owner, {}).get("name", a1.owner).split()[0]
            name2 = CHARACTERS.get(a2.owner, {}).get("name", a2.owner).split()[0]

            if not survivors_1 and not survivors_2:
                self.logs.append(f"Mutual Annihilation! All forces perished in battle at tile {tile} in {p_name}!")
                self.check_reset_player_raise_cooldown()
            elif not survivors_1:
                # Side 2 wins! Side 2 hosts REMAIN SEPARATE (CK2 style!)
                if a1.owner == self.player_id:
                    self.logs.append(f"Defeat! Player hosts crushed by {name2}'s forces at tile {tile} in {p_name}!")
                    self.check_reset_player_raise_cooldown()
                else:
                    self.logs.append(f"Victory! {name2}'s forces broke {name1}'s lines at tile {tile} in {p_name}!")
                
                cur_set = self.settlements.get(tile)
                for a in survivors_2:
                    a.in_battle = False
                    a.tile_path = []
                    a.move_progress = 0.0
                    if cur_set and getattr(a, "siege_intent", False) and getattr(a, "siege_prep_days", 0) <= 0:
                        a.is_sieging = True
            elif not survivors_2:
                # Side 1 wins! Side 1 hosts REMAIN SEPARATE (CK2 style!)
                if a1.owner == self.player_id:
                    self.logs.append(f"Glorious Victory! Combined royal hosts shattered the enemy army at tile {tile} in {p_name}!")
                else:
                    self.logs.append(f"Battle report: {name1}'s hosts crushed {name2}'s forces at tile {tile} in {p_name}!")
                if a2.owner == self.player_id:
                    self.check_reset_player_raise_cooldown()

                cur_set = self.settlements.get(tile)
                for a in survivors_1:
                    a.in_battle = False
                    a.tile_path = []
                    a.move_progress = 0.0
                    if cur_set and getattr(a, "siege_intent", False) and getattr(a, "siege_prep_days", 0) <= 0:
                        a.is_sieging = True

        # 3. Check Sieges (City-by-City Siege in Enemy or Contested Province)
        for a in list(self.armies):
            if a not in self.armies:
                continue
            if a.is_moving or a.in_battle or a.is_mustering or a.courier_en_route or a.is_demobilizing or getattr(a, "siege_prep_days", 0) > 0 or getattr(a, "siege_packup_days", 0) > 0:
                continue

            prov = PROVINCES.get(a.province)
            if not prov:
                a.is_sieging = False
                a.siege_progress = 0
                continue

            defenders = [enemy for enemy in self.armies if getattr(enemy, "tile", None) == a.tile and self.are_hostile(a.owner, enemy.owner)]
            if defenders:
                a.is_sieging = False
                continue

            is_enemy_prov = self.are_hostile(a.owner, prov["owner"])

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
                    # Friendly / Vassal province: liberate only if occupied by a hostile power
                    if occ is not None and self.are_hostile(occ, prov["owner"]):
                        needs_siege = True
                        is_liberation = True

                # Only siege if explicitly ordered (siege_intent == True) and prep is finished
                if needs_siege and getattr(a, "siege_intent", False) and getattr(a, "siege_prep_days", 0) <= 0:
                    a.is_sieging = True
                    a.siege_target_name = h_name
                    a.target_city = a.tile

                    # Siege rate scaled by troops
                    rate = max(4, int(a.troops / 250))
                    a.siege_progress += rate

                    if a.siege_progress >= 100:
                        a.siege_progress = 0
                        a.is_sieging = False
                        a.siege_intent = False
                        a.siege_prep_days = 0
                        a.siege_packup_days = 0
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
                                prov["color"] = list(PROVINCE_FACTION_COLORS.get(a.owner, {}).get(a.province, CHARACTERS.get(a.owner, {}).get("color", [100, 100, 100])))
                                for t in [coord for coord, s in self.settlements.items() if s.get("province") == a.province]:
                                    self.settlements[t]["occupied_by"] = None

                                if a.owner == self.player_id:
                                    CHARACTERS[a.owner]["prestige"] = CHARACTERS.get(a.owner, {}).get("prestige", 0) + 100
                                    conq_r = get_realm_name(a.owner, "the Realm"); self.logs.append(f"TOTAL VICTORY! All strongholds in {prov['name']} have fallen! Conquered by {conq_r}!")
                                else:
                                    r_char = CHARACTERS.get(a.owner)
                                    if r_char: r_char["prestige"] = r_char.get("prestige", 100) + 100
                                    conq_r = get_realm_name(a.owner, "the Realm"); self.logs.append(f"TERRITORY LOST! All strongholds in {prov['name']} have fallen to {conq_r}!")

                                # Automatically relocate or restore capitals if needed
                                for cid in self.get_active_rulers(include_player=True):
                                    self.get_realm_capital(cid)
                                self.sync_conquered_rulers()
                        else:
                            # Friendly liberation of occupied holding!
                            for t in h_tiles:
                                self.settlements[t]["occupied_by"] = None
                            self.logs.append(f"Liberated! {a.name} reclaimed {h_name} for {prov['name']}!")

                            remaining = get_siegeable_holdings(self, a.province, a.owner)
                            if not remaining:
                                self.logs.append(f"Order Restored! {prov['name']} is fully liberated and no longer contested.")
                elif not needs_siege:
                    # Settlement already friendly or already occupied: siege fulfilled!
                    a.is_sieging = False
                    a.siege_progress = 0
                    a.siege_intent = False
                    a.target_city = None
                    a.siege_target_name = None
                elif not getattr(a, "siege_intent", False):
                    # Army has no intention to siege (just standing/passing)
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
                            prov["color"] = list(PROVINCE_FACTION_COLORS.get(a.owner, {}).get(a.province, CHARACTERS.get(a.owner, {}).get("color", [100, 100, 100])))
                            a.is_sieging = False
                            a.siege_progress = 0
                            a.target_city = None
                            a.siege_target_name = None
                            if a.owner == self.player_id:
                                CHARACTERS[a.owner]["prestige"] = CHARACTERS.get(a.owner, {}).get("prestige", 0) + 100
                                conq_r = get_realm_name(a.owner, "the Realm"); self.logs.append(f"Victory! {prov['name']} has been conquered by {conq_r}!")
                            else:
                                if a.owner in CHARACTERS:
                                    CHARACTERS[a.owner]["prestige"] = CHARACTERS[a.owner].get("prestige", 0) + 100
                                conq_r = get_realm_name(a.owner, "the Realm"); self.logs.append(f"Territory Lost! {prov['name']} has fallen to {conq_r}!")
                            for cid in self.get_active_rulers(include_player=True):
                                self.get_realm_capital(cid)
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
    # SUPPLY WAGON LOGISTICS & EXPEDITIONARY ATTRITION
    # ---------------------------------------------------------
    def get_friendly_provinces(self, ruler_id):
        """Returns set of province IDs belonging to ruler_id or their loyal vassals / allies."""
        friendly = set()
        for pid, p in PROVINCES.items():
            o = p.get("owner")
            if o == ruler_id:
                friendly.add(pid)
            elif o and not self.are_hostile(ruler_id, o):
                # Friendly when one is the other's liege, or a direct vassal.
                if self.get_liege(o) == ruler_id or self.get_liege(ruler_id) == o:
                    friendly.add(pid)
                elif any(
                    v.get("id") == o or v.get("char_id") == o
                    for v_list in self.vassals.values() for v in v_list
                ):
                    friendly.add(pid)
        return friendly

    def get_friendly_tiles(self, ruler_id):
        """Returns list of all grid coordinates belonging to ruler_id or their vassals."""
        f_provs = self.get_friendly_provinces(ruler_id)
        tiles = []
        for pid in f_provs:
            tiles.extend(PROV_TO_TILES.get(pid, []))
        return tiles

    def get_next_supply_days(self, owner_id):
        """Returns the number of days until the next supply wagon arrives or is dispatched."""
        active_wagons = [w for w in getattr(self, "supply_wagons", []) if w.owner == owner_id]
        if active_wagons:
            min_hops = min(len(w.tile_path) for w in active_wagons)
            return max(1, min_hops)
        max_d = self.month_days[self.month - 1]
        return max(1, max_d - self.day + 1)

    def check_army_supply_line(self, army):
        """
        Determines whether an expeditionary army maintains an intact supply line corridor
        from friendly territory to its current tile.
        Returns: (is_connected: bool, nearest_friendly_tile: tuple)
        """
        if not army or getattr(army, "tile", None) is None:
            return False, None

        friendly_tiles = self.get_friendly_tiles(army.owner)
        if not friendly_tiles:
            return False, None

        if army.tile in friendly_tiles:
            return True, army.tile

        ax, ay = army.tile
        sorted_friendly = sorted(friendly_tiles, key=lambda t: (t[0] - ax)**2 + (t[1] - ay)**2)
        closest_friendly = None
        path = None
        for ft in sorted_friendly:
            p = find_shortest_tile_path(ft, army.tile, owner=army.owner)
            if p:
                closest_friendly = ft
                path = p
                break

        if not path:
            return False, (sorted_friendly[0] if sorted_friendly else None)

        # Check if hostile armies occupy tiles along the corridor
        hostile_army_tiles = {
            getattr(ha, "tile", None) for ha in self.armies
            if self.are_hostile(army.owner, ha.owner) and ha.troops > 0 and ha != army
        }

        # Any hostile army standing directly on the corridor severs the line!
        corridor = path[:-1]  # Exclude target army's own tile
        for step in corridor:
            if step in hostile_army_tiles:
                return False, closest_friendly

        return True, closest_friendly

    def rebalance_army_sub_units(self, target_army):
        """
        Rebalances sub-unit troop distribution if previous bug concentrated
        reinforcements onto a single sub-unit (e.g. sub_units[0]).
        Preserves 100% of the total troop count.
        """
        if not target_army:
            return
        sub_u = getattr(target_army, "sub_units", None)
        if not sub_u or len(sub_u) <= 1 or target_army.troops <= 0:
            return

        u0_troops = sub_u[0].get("troops", 0)
        tot = target_army.troops
        # Check if first sub-unit holds >50% of total troops while other units are starved (<10%)
        if len(sub_u) >= 2 and u0_troops > 0.50 * tot and any(u.get("troops", 0) < 0.10 * tot for u in sub_u[1:]):
            from game.systems.economy import get_vassal_landed_status
            from game.data.provinces import PROVINCES
            weights = []
            for u in sub_u:
                v_id = u.get("vassal_id")
                s_type = u.get("source_type")
                if v_id:
                    matching_v = None
                    v_prov = target_army.province
                    for pid, v_list in self.vassals.items():
                        for v in v_list:
                            if v.get("id") == v_id or v.get("name") == u.get("name", "").replace("'s Levy", "").strip():
                                matching_v = v
                                v_prov = pid
                                break
                        if matching_v:
                            break
                    if matching_v:
                        status = get_vassal_landed_status(self, matching_v, v_prov)
                        w = max(10, status.get("levy_contribution", 50))
                    else:
                        w = 50
                elif s_type == "crown" or not v_id:
                    prov = PROVINCES.get(target_army.province, {})
                    w = max(20, prov.get("crown_levies_max", 200))
                else:
                    w = 30
                weights.append(w)

            total_w = sum(weights)
            rem = tot
            for idx, u in enumerate(sub_u):
                if idx == len(sub_u) - 1:
                    u["troops"] = rem
                else:
                    share = int(round(tot * (weights[idx] / float(total_w))))
                    share = min(rem, max(1, share))
                    u["troops"] = share
                    rem -= share

            target_army.recalc_troops()
            self.logs.append(f"⚖ Rebalanced {target_army.name} ({tot:,} men): Fairly distributed reinforcement pool across all participating fiefs & crown guard.")

    def apply_reinforcements_to_army(self, target_army, reinforcements):
        """
        Integrates incoming reinforcements proportionally across all participating
        constituent sub-units (Crown Demesne Royal Guard and all participating Vassal Fiefs).
        """
        if not target_army or reinforcements <= 0:
            return

        self.rebalance_army_sub_units(target_army)

        sub_u = getattr(target_army, "sub_units", None)
        if not sub_u:
            target_army.troops += reinforcements
            target_army.vassal_levies += reinforcements
            return

        from game.systems.economy import get_vassal_landed_status
        from game.data.provinces import PROVINCES

        weights = []
        for u in sub_u:
            v_id = u.get("vassal_id")
            s_type = u.get("source_type")
            if v_id:
                matching_v = None
                v_prov = target_army.province
                for pid, v_list in self.vassals.items():
                    for v in v_list:
                        if v.get("id") == v_id or v.get("name") == u.get("name", "").replace("'s Levy", "").strip():
                            matching_v = v
                            v_prov = pid
                            break
                    if matching_v:
                        break
                if matching_v:
                    st = get_vassal_landed_status(self, matching_v, v_prov)
                    w = max(10, st.get("levy_contribution", 50))
                else:
                    w = 50
            elif s_type == "crown" or not v_id:
                prov = PROVINCES.get(target_army.province, {})
                w = max(20, prov.get("crown_levies_max", 200))
            else:
                w = 30
            weights.append(w)

        total_w = sum(weights)
        if total_w <= 0:
            total_w = len(sub_u)
            weights = [1] * len(sub_u)

        target_army.troops += reinforcements
        rem = reinforcements
        for idx, u in enumerate(sub_u):
            if idx == len(sub_u) - 1:
                share = rem
            else:
                share = int(round(reinforcements * (weights[idx] / float(total_w))))
                share = min(rem, share)
            u["troops"] = u.get("troops", 0) + share
            rem -= share

        if rem > 0:
            sub_u[0]["troops"] = sub_u[0].get("troops", 0) + rem

        target_army.recalc_troops()

    def dispatch_supply_wagon(self, target_army, reinforcements=0):
        """
        Dispatches a Supply Wagon loaded with rations and available recruits
        from the nearest friendly base to an expeditionary army.
        """
        if not target_army or getattr(target_army, "tile", None) is None:
            return None

        friendly_tiles = self.get_friendly_tiles(target_army.owner)
        if not friendly_tiles:
            return None

        # Check if wagon already heading to this army
        existing = [w for w in self.supply_wagons if w.target_army_id == target_army.id]
        if existing:
            return existing[0]

        ax, ay = target_army.tile
        sorted_friendly = sorted(friendly_tiles, key=lambda t: (t[0] - ax)**2 + (t[1] - ay)**2)
        closest_friendly = None
        path = None
        for ft in sorted_friendly:
            p = find_shortest_tile_path(ft, target_army.tile, owner=target_army.owner)
            if p:
                closest_friendly = ft
                path = p
                break

        if not path:
            return None
        origin_prov = CELL_TO_PROV.get(closest_friendly) or target_army.province

        # If army has reinforcements disabled by player/commander, deliver rations only (0 recruits)
        if not getattr(target_army, "allow_reinforcements", True):
            reinforcements = 0

        # Collect available recruits from garrison pool (All-in matching available garrison)
        elif reinforcements == 0:
            total_garrison = sum(p.get("levies_current", 0) for p in PROVINCES.values() if p.get("owner") == target_army.owner)
            
            field_armies = [
                a for a in self.armies
                if a.owner == target_army.owner and a.troops > 0
                and not getattr(a, "is_demobilizing", False) and not getattr(a, "is_mustering", False)
                and not any(w.target_army_id == a.id for w in self.supply_wagons)
            ]
            armies_count = max(1, len(field_armies))
            
            # If 1 army, take 100% of available garrison (all-in). If multiple, take equal share.
            take = total_garrison // armies_count if armies_count > 1 else total_garrison
            
            if take > 0:
                rem_take = take
                # Deduct from origin province first if owned by ruler
                prov = PROVINCES.get(origin_prov)
                if prov and prov.get("owner") == target_army.owner and prov.get("levies_current", 0) > 0:
                    d = min(prov["levies_current"], rem_take)
                    prov["levies_current"] -= d
                    rem_take -= d
                
                # Deduct from realm capital next
                if rem_take > 0:
                    cap_pid = self.get_realm_capital(target_army.owner)
                    cap_prov = PROVINCES.get(cap_pid)
                    if cap_prov and cap_prov.get("owner") == target_army.owner and cap_prov.get("levies_current", 0) > 0:
                        d = min(cap_prov["levies_current"], rem_take)
                        cap_prov["levies_current"] -= d
                        rem_take -= d
                
                # Deduct remainder from any other owned provinces
                if rem_take > 0:
                    for pid, p in PROVINCES.items():
                        if p.get("owner") == target_army.owner and p.get("levies_current", 0) > 0:
                            d = min(p["levies_current"], rem_take)
                            p["levies_current"] -= d
                            rem_take -= d
                            if rem_take <= 0:
                                break
                
                reinforcements = take - rem_take
            else:
                reinforcements = 0

        wagon_id = f"wagon_{self.wagon_id_counter}"
        self.wagon_id_counter += 1
        wagon = SupplyWagon(wagon_id, target_army.owner, target_army.id, closest_friendly, origin_prov, reinforcements=reinforcements)
        if len(path) > 1:
            wagon.tile_path = list(path[1:])
            self.supply_wagons.append(wagon)
            o_name = PROVINCES.get(origin_prov, {}).get("name", "homeland").split()[0]
            self.logs.append(f"📦 Supply Wagon dispatched from {o_name} to {target_army.name} (+{reinforcements} recruits & rations)!")
        else:
            # Immediate local delivery if army is already at the holding
            wagon.tile_path = []
            target_army.is_starving = False
            target_army.days_without_supply = 0
            target_army.supply_line_cut = False
            if reinforcements > 0:
                self.apply_reinforcements_to_army(target_army, reinforcements)
            self.logs.append(f"📦 Local Supplies Delivered! {target_army.name} reinforced with +{reinforcements} fresh recruits across all participating fiefs & crown.")

        return wagon

    def update_supply_wagons(self):
        """Advances supply wagons, handles ambushes, and delivers provisions & recruits."""
        for wagon in list(self.supply_wagons):
            target = next((a for a in self.armies if a.id == wagon.target_army_id and a.troops > 0), None)
            if not target:
                if wagon in self.supply_wagons:
                    self.supply_wagons.remove(wagon)
                continue

            # If target army has moved, recalculate tile_path towards target.tile
            if not wagon.tile_path or wagon.tile_path[-1] != target.tile:
                if wagon.tile != target.tile:
                    new_path = find_shortest_tile_path(wagon.tile, target.tile, owner=wagon.owner)
                    if new_path and len(new_path) > 1:
                        wagon.tile_path = list(new_path[1:])
                    else:
                        wagon.tile_path = []

            # Check Ambush before movement (hostiles on wagon tile)
            hostile_here = [
                ha for ha in self.armies
                if self.are_hostile(wagon.owner, ha.owner) and ha.troops > 0 and getattr(ha, "tile", None) == wagon.tile
            ]
            if hostile_here:
                wagon.is_ambushed = True
                ambusher = hostile_here[0]
                a_name = CHARACTERS.get(ambusher.owner, {}).get("name", "Hostile force").split()[0]
                self.logs.append(f"⚔ AMBUSH! {a_name}'s {ambusher.name} intercepted a Supply Wagon bound for {target.name} at {wagon.tile}! Supplies plundered & +{wagon.reinforcements} reinforcements dispersed!")
                target.supply_line_cut = True
                if target.days_without_supply >= 35:
                    target.is_starving = True
                if wagon in self.supply_wagons:
                    self.supply_wagons.remove(wagon)
                continue

            # Move along path
            if wagon.tile_path:
                wagon.move_progress += wagon.move_speed
                if wagon.move_progress >= 100.0:
                    wagon.move_progress = 0.0
                    wagon.tile = wagon.tile_path.pop(0)

            # Check Ambush after movement (stepped onto hostile tile)
            hostile_here = [
                ha for ha in self.armies
                if self.are_hostile(wagon.owner, ha.owner) and ha.troops > 0 and getattr(ha, "tile", None) == wagon.tile
            ]
            if hostile_here:
                wagon.is_ambushed = True
                ambusher = hostile_here[0]
                a_name = CHARACTERS.get(ambusher.owner, {}).get("name", "Hostile force").split()[0]
                self.logs.append(f"⚔ AMBUSH! {a_name}'s {ambusher.name} intercepted a Supply Wagon bound for {target.name} at {wagon.tile}! Supplies plundered & +{wagon.reinforcements} reinforcements dispersed!")
                target.supply_line_cut = True
                if target.days_without_supply >= 35:
                    target.is_starving = True
                if wagon in self.supply_wagons:
                    self.supply_wagons.remove(wagon)
                continue

            # Check Delivery Arrival
            if wagon.tile == target.tile:
                target.is_starving = False
                target.days_without_supply = 0
                target.supply_line_cut = False
                if wagon.reinforcements > 0:
                    self.apply_reinforcements_to_army(target, wagon.reinforcements)
                self.logs.append(f"📦 Supplies Delivered! Supply Wagon reached {target.name}! Rations restocked & +{wagon.reinforcements} reinforcements integrated across all participating fiefs & crown.")
                if wagon in self.supply_wagons:
                    self.supply_wagons.remove(wagon)

    def update_expeditionary_and_starvation(self):
        """
        Evaluates expeditionary status, supply line connectivity, and inflicts
        -5 soldiers/day starvation attrition on severed hosts.
        """
        friendly_cache = {}
        for a in list(self.armies):
            if a.troops <= 0 or a.is_demobilizing or a.is_mustering:
                continue

            owner = a.owner
            if owner not in friendly_cache:
                friendly_cache[owner] = self.get_friendly_provinces(owner)
            friendly_provs = friendly_cache[owner]

            # Expeditionary Status: Outside friendly realm provinces
            if a.province not in friendly_provs:
                a.is_expeditionary = True
                connected, _ = self.check_army_supply_line(a)
                a.supply_line_cut = not connected
                # Troops carry 35 days of rations when supplied.
                # Starvation ONLY occurs when rations run out completely (>= 35 days without supply).
                if a.days_without_supply >= 35:
                    a.is_starving = True
                else:
                    a.is_starving = False
            else:
                a.is_expeditionary = False
                a.is_starving = False
                a.supply_line_cut = False
                a.days_without_supply = 0

            # Daily Starvation Attrition: EXACT USER SPECIFICATION: "-5 prajurit setiap hari"
            if a.is_starving:
                loss = min(5, a.troops)
                a.troops -= loss
                if getattr(a, "vassal_levies", 0) >= loss:
                    a.vassal_levies -= loss
                elif getattr(a, "crown_troops", 0) >= loss:
                    a.crown_troops -= loss

                # Synchronize constituent sub-units with attrition loss
                if getattr(a, "sub_units", None):
                    rem_loss = loss
                    for u in a.sub_units:
                        if u.get("troops", 0) >= rem_loss:
                            u["troops"] -= rem_loss
                            rem_loss = 0
                            break
                        else:
                            rem_loss -= u.get("troops", 0)
                            u["troops"] = 0
                    a.recalc_troops()

                a.days_without_supply += 1
                if a.troops <= 1:
                    self.logs.append(f"☠ Host Disintegrated: {a.name} succumbed to starvation (-{loss}/d) and completely dissolved in foreign lands!")
                    self.disband_army(a)
                elif a.days_without_supply % 10 == 1 or a.days_without_supply == 1:
                    self.logs.append(f"☠ Starvation (-5/day): {a.name} is cut off from supplies! {a.troops:,} soldiers remain.")
            elif a.is_expeditionary:
                a.days_without_supply += 1

    # ---------------------------------------------------------
    # AI ROUTINE - Intelligent Border Awareness, Mobilization & Retaliation
    # ---------------------------------------------------------
    def ai_routine(self):
        """Dispatches to modular strategic AI system for all active non-player AI realm rulers."""
        for r_id in self.get_ai_rulers():
            run_realm_ai(self, r_id)

    # ---------------------------------------------------------
prov_tile_list = {}
for (c, r), pid in CELL_TO_PROV.items():
    prov_tile_list.setdefault(pid, []).append((c, r))

def cluster_30_tiles(tiles, cap_tile):
    """Partitions province tiles into crown/count/baron clusters.

    The layout targets 10 crown / 6 count1 / 4 baron1 / 6 count2 / 4 baron2
    tiles, but scales gracefully for province sizes that are not exactly 30.
    """
    rem_tiles = list(tiles or [])
    if not rem_tiles:
        return [], [], [], [], []
    rem_tiles.sort(key=lambda t: (t[0]-cap_tile[0])**2 + (t[1]-cap_tile[1])**2)
    n = len(rem_tiles)
    crown_n = min(10, max(1, n // 3)) if n >= 5 else n
    crown_tiles = rem_tiles[:crown_n]
    rem_20 = rem_tiles[crown_n:]
    rem_20.sort(key=lambda t: (t[0] + t[1]))
    # Split the remainder evenly into two vassal groups.
    half = (len(rem_20) + 1) // 2
    grp_1 = rem_20[:half]
    grp_2 = rem_20[half:]
    def split_group(group):
        if not group:
            return [], []
        cut = (len(group) * 3 + 4) // 5  # ~60% count / 40% baron
        cut = max(1, min(len(group) - 1, cut)) if len(group) > 1 else len(group)
        return group[:cut], group[cut:]
    c1_tiles, b1_tiles = split_group(grp_1)
    c2_tiles, b2_tiles = split_group(grp_2)
    return crown_tiles, c1_tiles, b1_tiles, c2_tiles, b2_tiles

def setup_province_starter_cities(target_state):
    """
    Partitions all 30 tiles of every realm province into complete feudal fiefdoms:
    1 Province = 1 Complete Kingdom (30 tiles total, 100% sliced into fiefs):
    - Crown Demesne (10 tiles): Royal City (Lvl 0), Royal Citadel (Lvl 0), Royal Barracks (Lvl 0)
    - Direct Vassal Count 1 (6 tiles): Fort (Lvl 0), Starter City (Lvl 0), Barracks (Lvl 0)
    - Sub-Vassal Baron 1 (4 tiles): Burgh/Town (Lvl 0)
    - Direct Vassal Count 2 (6 tiles): Fort (Lvl 0), Starter City (Lvl 0), Barracks (Lvl 0)
    - Sub-Vassal Baron 2 (4 tiles): Keep (Lvl 0)
    Total = 10 + 6 + 4 + 6 + 4 = 30 tiles!
    """
    target_state.settlements = {}
    target_state.fiefs = {}
    fief_counter = 1
    settlement_counter = 1

    for pid in list(PROVINCES.keys()):
        p_name = PROVINCES[pid]["name"].split()[0]
        p_owner = PROVINCES[pid].get("owner", target_state.player_id)
        ruler_char = CHARACTERS.get(p_owner, target_state.player)
        p_tiles = list(PROV_TO_TILES.get(pid, []))
        cap_tile = PROV_CAPITAL_TILES.get(pid, p_tiles[0] if p_tiles else (0, 0))

        crown_tiles, c1_tiles, b1_tiles, c2_tiles, b2_tiles = cluster_30_tiles(p_tiles, cap_tile)

        # 1. CROWN DEMESNE FIEF (10 TILES) - Held by the Sovereign Ruler
        fid_crown = f"fief_{fief_counter}"
        fief_counter += 1
        target_state.fiefs[fid_crown] = {
            "id": fid_crown,
            "province": pid,
            "tiles": crown_tiles,
            "name": f"Crown Demesne of {p_name}",
            "holder": ruler_char["name"],
            "owner": p_owner,
            "vassal_id": None,
            "is_crown_demesne": True
        }

        # Crown City (1 tile, Level 0) at Capital Tile
        sb_city = f"settlement_{settlement_counter}"
        settlement_counter += 1
        target_state.settlements[cap_tile] = {
            "id": sb_city,
            "province": pid,
            "type": "city",
            "name": f"Royal City of {p_name}",
            "lord": ruler_char["name"],
            "owner": p_owner,
            "vassal_id": None,
            "is_crown_demesne": True,
            "is_crown_fief": True,
            "level": 0,
            "max_unlocked_level": 0
        }

        # Crown Citadel (1 tile, Level 0)
        free_crown = [t for t in crown_tiles if t != cap_tile]
        cit_tile = free_crown.pop(0) if free_crown else cap_tile
        sb_cit = f"settlement_{settlement_counter}"
        settlement_counter += 1
        target_state.settlements[cit_tile] = {
            "id": sb_cit,
            "province": pid,
            "type": "fort",
            "name": f"Citadel of {p_name}",
            "lord": ruler_char["name"],
            "owner": p_owner,
            "vassal_id": None,
            "is_crown_demesne": True,
            "is_crown_fief": True,
            "level": 0,
            "max_unlocked_level": 0
        }

        # Crown Barracks (1 tile, Level 0)
        barr_tile = free_crown.pop(0) if free_crown else cap_tile
        sb_barr = f"settlement_{settlement_counter}"
        settlement_counter += 1
        target_state.settlements[barr_tile] = {
            "id": sb_barr,
            "province": pid,
            "type": "barrack",
            "name": f"Royal {p_name} Barracks",
            "lord": ruler_char["name"],
            "owner": p_owner,
            "vassal_id": None,
            "is_crown_demesne": True,
            "is_crown_fief": True,
            "level": 0,
            "max_unlocked_level": 0
        }

        v_list = target_state.vassals.get(pid, [])
        c1 = v_list[0] if len(v_list) > 0 else None
        c2 = v_list[1] if len(v_list) > 1 else None
        b1 = v_list[2] if len(v_list) > 2 else None
        b2 = v_list[3] if len(v_list) > 3 else None

        # 2. DIRECT VASSAL 1 (COUNT 1, 6 TILES)
        if c1:
            fid_c1 = f"fief_{fief_counter}"
            fief_counter += 1
            c1_lbl = target_state.get_character_clean_name(c1["name"]).split()[0]
            c1_fief_name = f"County of {c1_lbl}"
            target_state.fiefs[fid_c1] = {
                "id": fid_c1,
                "province": pid,
                "tiles": c1_tiles,
                "name": c1_fief_name,
                "holder": c1["name"],
                "owner": p_owner,
                "vassal_id": c1["id"],
                "is_crown_demesne": False
            }
            c1_free = list(c1_tiles)
            random.shuffle(c1_free)

            t_fort = c1_free.pop(0)
            c1_seat_name = f"{c1_lbl}'s Fortress"
            sb_c1_f = f"settlement_{settlement_counter}"
            settlement_counter += 1
            target_state.settlements[t_fort] = {
                "id": sb_c1_f, "province": pid, "type": "fort", "name": c1_seat_name,
                "lord": c1["name"], "owner": p_owner, "vassal_id": c1["id"],
                "is_crown_demesne": False, "is_crown_fief": False, "level": 0, "max_unlocked_level": 0
            }
            c1["city_name"] = c1_seat_name
            c1["tiles"] = c1_tiles

            t_city = c1_free.pop(0)
            sb_c1_c = f"settlement_{settlement_counter}"
            settlement_counter += 1
            target_state.settlements[t_city] = {
                "id": sb_c1_c, "province": pid, "type": "city", "name": f"{c1_lbl}'s City",
                "lord": c1["name"], "owner": p_owner, "vassal_id": c1["id"],
                "is_crown_demesne": False, "is_crown_fief": False, "level": 0, "max_unlocked_level": 0
            }

            t_barr = c1_free.pop(0)
            sb_c1_b = f"settlement_{settlement_counter}"
            settlement_counter += 1
            target_state.settlements[t_barr] = {
                "id": sb_c1_b, "province": pid, "type": "barrack", "name": f"{c1_lbl}'s Barracks",
                "lord": c1["name"], "owner": p_owner, "vassal_id": c1["id"],
                "is_crown_demesne": False, "is_crown_fief": False, "level": 0, "max_unlocked_level": 0
            }

        # 3. SUB-VASSAL 1 (BARON 1 under Count 1, 4 TILES)
        if b1:
            fid_b1 = f"fief_{fief_counter}"
            fief_counter += 1
            b1_lbl = target_state.get_character_clean_name(b1["name"]).split()[0]
            b1_fief_name = f"Barony of {b1_lbl}"
            target_state.fiefs[fid_b1] = {
                "id": fid_b1,
                "province": pid,
                "tiles": b1_tiles,
                "name": b1_fief_name,
                "holder": b1["name"],
                "owner": p_owner,
                "vassal_id": b1["id"],
                "is_crown_demesne": False
            }
            b1_t_pick = random.choice(b1_tiles)
            b1_seat = f"{b1_lbl}'s Burgh"
            sb_b1 = f"settlement_{settlement_counter}"
            settlement_counter += 1
            target_state.settlements[b1_t_pick] = {
                "id": sb_b1, "province": pid, "type": "city", "name": b1_seat,
                "lord": b1["name"], "owner": p_owner, "vassal_id": b1["id"],
                "is_crown_demesne": False, "is_crown_fief": False, "level": 0, "max_unlocked_level": 0
            }
            b1["city_name"] = b1_seat
            b1["tiles"] = b1_tiles

        # 4. DIRECT VASSAL 2 (COUNT 2, 6 TILES)
        if c2:
            fid_c2 = f"fief_{fief_counter}"
            fief_counter += 1
            c2_lbl = target_state.get_character_clean_name(c2["name"]).split()[0]
            c2_fief_name = f"County of {c2_lbl}"
            target_state.fiefs[fid_c2] = {
                "id": fid_c2,
                "province": pid,
                "tiles": c2_tiles,
                "name": c2_fief_name,
                "holder": c2["name"],
                "owner": p_owner,
                "vassal_id": c2["id"],
                "is_crown_demesne": False
            }
            c2_free = list(c2_tiles)
            random.shuffle(c2_free)

            t_fort2 = c2_free.pop(0)
            c2_seat_name = f"{c2_lbl}'s Keep"
            sb_c2_f = f"settlement_{settlement_counter}"
            settlement_counter += 1
            target_state.settlements[t_fort2] = {
                "id": sb_c2_f, "province": pid, "type": "fort", "name": c2_seat_name,
                "lord": c2["name"], "owner": p_owner, "vassal_id": c2["id"],
                "is_crown_demesne": False, "is_crown_fief": False, "level": 0, "max_unlocked_level": 0
            }
            c2["city_name"] = c2_seat_name
            c2["tiles"] = c2_tiles

            t_city2 = c2_free.pop(0)
            sb_c2_c = f"settlement_{settlement_counter}"
            settlement_counter += 1
            target_state.settlements[t_city2] = {
                "id": sb_c2_c, "province": pid, "type": "city", "name": f"{c2_lbl}'s Town",
                "lord": c2["name"], "owner": p_owner, "vassal_id": c2["id"],
                "is_crown_demesne": False, "is_crown_fief": False, "level": 0, "max_unlocked_level": 0
            }

            t_barr2 = c2_free.pop(0)
            sb_c2_b = f"settlement_{settlement_counter}"
            settlement_counter += 1
            target_state.settlements[t_barr2] = {
                "id": sb_c2_b, "province": pid, "type": "barrack", "name": f"{c2_lbl}'s Barracks",
                "lord": c2["name"], "owner": p_owner, "vassal_id": c2["id"],
                "is_crown_demesne": False, "is_crown_fief": False, "level": 0, "max_unlocked_level": 0
            }

        # 5. SUB-VASSAL 2 (BARON 2 under Count 2, 4 TILES)
        if b2:
            fid_b2 = f"fief_{fief_counter}"
            fief_counter += 1
            b2_lbl = target_state.get_character_clean_name(b2["name"]).split()[0]
            b2_fief_name = f"Barony of {b2_lbl}"
            target_state.fiefs[fid_b2] = {
                "id": fid_b2,
                "province": pid,
                "tiles": b2_tiles,
                "name": b2_fief_name,
                "holder": b2["name"],
                "owner": p_owner,
                "vassal_id": b2["id"],
                "is_crown_demesne": False
            }
            b2_t_pick = random.choice(b2_tiles)
            b2_seat = f"{b2_lbl}'s Castle"
            sb_b2 = f"settlement_{settlement_counter}"
            settlement_counter += 1
            target_state.settlements[b2_t_pick] = {
                "id": sb_b2, "province": pid, "type": "fort", "name": b2_seat,
                "lord": b2["name"], "owner": p_owner, "vassal_id": b2["id"],
                "is_crown_demesne": False, "is_crown_fief": False, "level": 0, "max_unlocked_level": 0
            }
            b2["city_name"] = b2_seat
            b2["tiles"] = b2_tiles

    target_state.fief_id_counter = fief_counter + 100
    target_state.settlement_id_counter = settlement_counter + 100

    for plist in target_state.vassals.values():
        for v in plist:
            pid = v.get("province")
            st = get_vassal_landed_status(target_state, v, pid)
            v["tax_contribution"] = st["tax_paid"]
            v["levy_contribution"] = st["levy_contribution"]

    from game.systems.economy import sync_province_holdings_stats
    sync_province_holdings_stats(target_state, is_init=True)
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

