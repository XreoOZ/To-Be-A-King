"""
Province Data, Faction Coloring, and Adjacency Graphs
"""
import os
import json
import copy
from collections import deque
from game.config import DATA_DIR
from game.data.characters import CHARACTERS, INITIAL_CHARACTERS

with open(os.path.join(DATA_DIR, "provinces.json"), "r", encoding="utf-8") as f:
    INITIAL_PROVINCES = json.load(f)

PROVINCES = copy.deepcopy(INITIAL_PROVINCES)

# Harmonic Provincial Color Palettes per Faction
PROVINCE_FACTION_COLORS = {
    # If owned by Wessex (Kingdom of Wessex / Saxons - rich crimson/burgundy/terracotta palette)
    "char_alfred": {
        "wessex": (196, 38, 42),       # Wessex Royal Red
        "kent_essex": (170, 32, 50),   # Kent Burgundy
        "mercia": (185, 60, 36),       # Mercia Terracotta Crimson
        "east_anglia": (205, 52, 36),  # East Anglia Vermilion
        "cornwall": (175, 42, 60),     # Cornwall Celtic Crimson
        "wales": (155, 26, 38),        # Wales Dark Dragon Red
        "jorvik": (168, 46, 46),       # Jorvik Northern Red
        "deira": (180, 52, 44),        # Deira Northumbrian Red
        "bernicia": (160, 38, 50),     # Bernicia Coastal Crimson
        "strathclyde": (172, 48, 55),  # Strathclyde Red
        "lothian": (184, 55, 48),      # Lothian Red
        "highlands": (150, 30, 42),    # Highlands Red
    },
    # If owned by Danelaw (Vikings - navy/slate/cobalt/storm palette)
    "char_halfdan": {
        "jorvik": (44, 68, 98),        # Jorvik Viking Navy
        "deira": (58, 84, 114),        # Deira Northumbrian Slate Blue
        "bernicia": (38, 60, 88),      # Bernicia North Sea Cobalt
        "strathclyde": (52, 76, 104),  # Strathclyde Storm Blue
        "lothian": (46, 72, 98),       # Lothian Midnight Teal
        "highlands": (35, 54, 78),     # Scottish Highlands Deep Pine
        "mercia": (50, 72, 96),        # Mercia Conquered Slate
        "east_anglia": (62, 86, 112),  # East Anglia Conquered Blue
        "wessex": (42, 64, 92),        # Wessex Conquered Navy
        "kent_essex": (48, 70, 96),    # Kent Conquered Navy
        "cornwall": (40, 58, 84),      # Cornwall Conquered Navy
        "wales": (36, 56, 82),         # Wales Conquered Blue
    }
}

# Apply harmonic colors to initial provinces
for pid, p in PROVINCES.items():
    owner = p.get("owner", "char_alfred")
    if owner in PROVINCE_FACTION_COLORS and pid in PROVINCE_FACTION_COLORS[owner]:
        p["color"] = list(PROVINCE_FACTION_COLORS[owner][pid])

# Province Adjacency Graph for Movement & Pathfinding
ADJACENCY = {
    "cornwall": ["wessex"],
    "wessex": ["cornwall", "kent_essex", "mercia", "wales"],
    "kent_essex": ["east_anglia", "mercia", "wessex"],
    "mercia": ["deira", "east_anglia", "jorvik", "kent_essex", "wales", "wessex"],
    "wales": ["mercia", "wessex"],
    "east_anglia": ["kent_essex", "mercia"],
    "jorvik": ["bernicia", "deira", "mercia"],
    "deira": ["bernicia", "jorvik", "mercia"],
    "bernicia": ["deira", "jorvik", "lothian"],
    "strathclyde": ["highlands", "lothian"],
    "lothian": ["bernicia", "highlands", "strathclyde"],
    "highlands": ["lothian", "strathclyde"]
}

def reset_global_world_data():
    """Restores PROVINCES and CHARACTERS dictionaries to pristine AD 867 state."""
    CHARACTERS.clear()
    CHARACTERS.update(copy.deepcopy(INITIAL_CHARACTERS))
    PROVINCES.clear()
    PROVINCES.update(copy.deepcopy(INITIAL_PROVINCES))
    for pid, p in PROVINCES.items():
        owner = p.get("owner", "char_alfred")
        if owner in PROVINCE_FACTION_COLORS and pid in PROVINCE_FACTION_COLORS[owner]:
            p["color"] = list(PROVINCE_FACTION_COLORS[owner][pid])

def build_dynamic_province_adjacency(cell_to_prov, max_reach=2, extra_connections=None):
    """
    Dynamically generates the adjacency graph of provinces from the tile map grid.
    """
    adj = {pid: set() for pid in set(cell_to_prov.values()) if pid}
    for (c, r), p_a in cell_to_prov.items():
        if not p_a:
            continue
        for dc in range(-max_reach, max_reach + 1):
            for dr in range(-max_reach, max_reach + 1):
                if dc == 0 and dr == 0:
                    continue
                if abs(dc) + abs(dr) > max_reach:
                    continue
                p_b = cell_to_prov.get((c + dc, r + dr))
                if p_b and p_b != p_a:
                    adj[p_a].add(p_b)
                    adj[p_b].add(p_a)
                    
    if extra_connections:
        for p1, p2 in extra_connections:
            if p1 in adj and p2 in adj:
                adj[p1].add(p2)
                adj[p2].add(p1)
                
    return {p: sorted(list(neighbors)) for p, neighbors in adj.items()}

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
    return [start]
