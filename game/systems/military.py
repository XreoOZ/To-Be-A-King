"""
Military Mechanics: Sieges, Contested Provinces, and Combat Helpers
"""
from game.data.provinces import PROVINCES
from game.systems.economy import get_province_holdings

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
        display_name = s_data.get("name") or h_name
        if is_enemy_prov:
            if occ != army_owner:
                siegeable.append((display_name, tiles))
        else:
            if occ is not None and occ != army_owner:
                siegeable.append((display_name, tiles))
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
