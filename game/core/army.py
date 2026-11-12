"""
Army Class and Troop Movement State
"""
from game.config import DAYS_PER_KOTAK
from game.core.map import get_province_capital_tile, CELL_TO_PROV, find_shortest_tile_path

class Army:
    def __init__(self, army_id, owner_id, province_id, troops, name="Levy Host", flag_origin=None, rank=1, tile=None):
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
        self.vassal_id = None
        self.allow_reinforcements = True  # If False, receives rations (anti-starve) but 0 recruits
        self.sub_units = [
            {
                "id": f"{army_id}_sub_1",
                "name": f"{name} Levy",
                "troops": troops,
                "vassal_id": None,
                "flag": flag_origin or province_id
            }
        ] if troops > 0 else []
        
        # Tile Grid coordinates
        self.tile = tile or get_province_capital_tile(province_id)
        self.tile_path = []         # list of (col, row) coordinates to march through
        self.move_progress = 0.0    # 0 to 100%
        self.move_speed = 100.0 / DAYS_PER_KOTAK  # % per day (1 day per tile)
        
        # Combat & Siege (15-Day Preparation & Decamp Cycle)
        self.is_sieging = False
        self.siege_progress = 0     # 0 to 100%
        self.in_battle = False
        self.target_city = None
        self.siege_target_name = None
        self.siege_intent = False          # True only when explicitly ordered to siege
        self.siege_prep_days = 0           # 15 days required to build siege camp before progress ticks
        self.siege_packup_days = 0         # 15 days required to dismantle camp before free movement
        self.pending_march_target = None   # Target tile queued while dismantling siege works
        self.siege_target_tile = None      # Tile of the specific holding being besieged
        
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
        
        # Logistics & Expeditionary Campaign System
        self.is_expeditionary = False      # Outside sovereign/vassal territory
        self.is_starving = False           # Suffers daily -5 troop starvation when severed
        self.days_without_supply = 0       # Days since last supply delivery or domestic presence
        self.supply_line_cut = False       # True if enemy blocks supply corridor

    @property
    def is_moving(self):
        return len(self.tile_path) > 0

    @property
    def next_tile(self):
        return self.tile_path[0] if self.tile_path else None

    @property
    def next_province(self):
        if not self.tile_path:
            return None
        return CELL_TO_PROV.get(self.tile_path[0], self.province)

    @property
    def path(self):
        """Returns the remaining unique province IDs along the army's tile path."""
        p_list = []
        cur_p = self.province
        for t in self.tile_path:
            p = CELL_TO_PROV.get(t, cur_p)
            if p != cur_p:
                if not p_list or p_list[-1] != p:
                    p_list.append(p)
                cur_p = p
        return p_list

    @path.setter
    def path(self, new_val):
        if not new_val:
            self.tile_path = []
            return
        if isinstance(new_val, list) and new_val and isinstance(new_val[0], tuple):
            self.tile_path = list(new_val)
        elif isinstance(new_val, list) and new_val and isinstance(new_val[0], str):
            target_prov = new_val[-1]
            target_tile = get_province_capital_tile(target_prov)
            route = find_shortest_tile_path(self.tile, target_tile, owner=self.owner)
            if route and len(route) > 1:
                self.tile_path = route[1:]
            else:
                self.tile_path = []



    def recalc_troops(self):
        """Recalculates total troop strength from constituent sub-units."""
        if self.sub_units:
            self.troops = sum(u.get("troops", 0) for u in self.sub_units)
            self.vassal_levies = sum(u.get("troops", 0) for u in self.sub_units if u.get("vassal_id") or u.get("source_type") != "crown")
            self.crown_troops = sum(u.get("troops", 0) for u in self.sub_units if not u.get("vassal_id") and u.get("source_type") == "crown")
        return self.troops

    def merge_army(self, other_army):
        """Merges another army into this host, integrating its sub-units and flags."""
        if not other_army or other_army == self:
            return False
        if not getattr(other_army, "sub_units", None):
            other_army.sub_units = [{
                "id": f"{other_army.id}_sub_1",
                "name": other_army.name,
                "troops": other_army.troops,
                "vassal_id": getattr(other_army, "vassal_id", None),
                "flag": other_army.flag_origin
            }]
        self.sub_units.extend(other_army.sub_units)
        if other_army.flag_origin and other_army.flag_origin not in self.sub_flags and other_army.flag_origin != self.flag_origin:
            self.sub_flags.append(other_army.flag_origin)
        for sf in getattr(other_army, "sub_flags", []):
            if sf not in self.sub_flags and sf != self.flag_origin:
                self.sub_flags.append(sf)
        self.recalc_troops()
        return True

    def split_sub_units(self, unit_ids):
        """Detaches the specified sub-units from this host and returns them."""
        detached = [u for u in self.sub_units if u.get("id") in unit_ids]
        self.sub_units = [u for u in self.sub_units if u.get("id") not in unit_ids]
        self.recalc_troops()
        return detached

class SupplyWagon:
    def __init__(self, wagon_id, owner_id, target_army_id, origin_tile, origin_prov, reinforcements=0, supplies=30):
        self.id = wagon_id
        self.owner = owner_id
        self.target_army_id = target_army_id
        self.origin_tile = origin_tile
        self.origin_prov = origin_prov
        self.tile = origin_tile
        self.tile_path = []
        self.move_progress = 0.0
        self.move_speed = 100.0 / DAYS_PER_KOTAK  # 1 tile per day
        self.reinforcements = reinforcements
        self.supplies = supplies
        self.is_ambushed = False

    @property
    def is_moving(self):
        return len(self.tile_path) > 0

    @property
    def next_tile(self):
        return self.tile_path[0] if self.tile_path else None
