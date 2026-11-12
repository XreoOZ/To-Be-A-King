"""
Crusader Kings 2 (CK2) Style Dynamic Feudal Titles System
Separates Titles from Characters so titles can be granted, revoked,
transferred, and held simultaneously by rulers (Kings, Dukes, Counts, Barons).
"""

class Title:
    def __init__(self, title_id, name, tier, holder_id, province_id=None, de_jure_liege_id=None, tiles=None, holding_id=None, holding_type=None):
        self.id = title_id
        self.title_id = title_id
        self.name = name
        self.tier = tier          # "empire", "kingdom", "duchy", "county", "barony"
        self.rank = {
            "empire": 5,
            "kingdom": 4,
            "duchy": 3,
            "county": 2,
            "barony": 1
        }.get(tier, 1)
        self.holder_id = holder_id
        self.province_id = province_id
        self.de_jure_liege_id = de_jure_liege_id
        self.tiles = list(tiles or [])
        self.holding_id = holding_id
        self.holding_type = holding_type  # "city", "fort", "barrack"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "tier": self.tier,
            "rank": self.rank,
            "holder_id": self.holder_id,
            "province_id": self.province_id,
            "de_jure_liege_id": self.de_jure_liege_id,
            "tiles": self.tiles,
            "holding_id": self.holding_id,
            "holding_type": self.holding_type
        }

def get_tier_prefix(tier, culture="human", is_female=False):
    """Dynamically returns noble honorific based on title tier, culture, and gender."""
    if tier == "kingdom":
        return "Queen" if is_female else "King"
    elif tier == "duchy":
        if "Dwarf" in culture:
            return "Grand Thane"
        elif "Elf" in culture:
            return "Archon" if not is_female else "Duchess"
        return "Duchess" if is_female else "Duke"
    elif tier == "county":
        if "Dwarf" in culture:
            return "Thane"
        elif "Elf" in culture:
            return "Warden"
        return "Countess" if is_female else "Count"
    elif tier == "barony":
        if "Dwarf" in culture:
            return "Hearth-Warden"
        elif "Elf" in culture:
            return "Elder"
        return "Baroness" if is_female else "Baron"
    return "Lord"
