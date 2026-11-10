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
        
        # Tile Grid coordinates
        self.tile = tile or get_province_capital_tile(province_id)
        self.tile_path = []         # list of (col, row) coordinates to march through
        self.move_progress = 0.0    # 0 to 100%
        self.move_speed = 100.0 / DAYS_PER_KOTAK  # % per day (1 day per tile)
        
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
            route = find_shortest_tile_path(self.tile, target_tile)
            if route and len(route) > 1:
                self.tile_path = route[1:]
            else:
                self.tile_path = []
