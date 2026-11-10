"""
Province Data, Faction Coloring, and Adjacency Graphs for Fantasy Realm
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
    # Holy Kingdom of Solaris (Humans) - Crimson & Gold
    "char_human": {
        pid: (200, 42, 45) for pid in PROVINCES
    },
    # Ironpeak Dominion (Dwarves) - Slate Steel & Bronze
    "char_ironpeak": {
        pid: (52, 72, 95) for pid in PROVINCES
    },
    # Sylvandell Sovereignty (Elves) - Deep Emerald & Jade
    "char_sylvan": {
        pid: (32, 100, 52) for pid in PROVINCES
    }
}

# Apply harmonic colors to initial provinces
for pid, p in PROVINCES.items():
    if "color" in p:
        p["color"] = list(p["color"])
    else:
        owner = p.get("owner", "char_human")
        if owner in PROVINCE_FACTION_COLORS and pid in PROVINCE_FACTION_COLORS[owner]:
            p["color"] = list(PROVINCE_FACTION_COLORS[owner][pid])

# Province Adjacency Graph from JSON neighbors
ADJACENCY = {pid: list(p.get("neighbors", [])) for pid, p in PROVINCES.items()}

def reset_global_world_data():
    """Restores PROVINCES and CHARACTERS dictionaries to pristine fantasy state."""
    CHARACTERS.clear()
    CHARACTERS.update(copy.deepcopy(INITIAL_CHARACTERS))
    PROVINCES.clear()
    PROVINCES.update(copy.deepcopy(INITIAL_PROVINCES))
    for pid, p in PROVINCES.items():
        if "color" in p:
            p["color"] = list(p["color"])
        else:
            owner = p.get("owner", "char_human")
            if owner in PROVINCE_FACTION_COLORS and pid in PROVINCE_FACTION_COLORS[owner]:
                p["color"] = list(PROVINCE_FACTION_COLORS[owner][pid])

def build_dynamic_province_adjacency(cell_to_prov, max_reach=2, extra_connections=None):
    """
    Dynamically generates the adjacency graph of provinces from the tile map grid.
    """
    adj = {p: set() for p in PROVINCES.keys()}
    for (c, r), p_src in cell_to_prov.items():
        for dc in range(-max_reach, max_reach + 1):
            for dr in range(-max_reach, max_reach + 1):
                if dc == 0 and dr == 0:
                    continue
                neighbor_coord = (c + dc, r + dr)
                if neighbor_coord in cell_to_prov:
                    p_dst = cell_to_prov[neighbor_coord]
                    if p_dst != p_src:
                        adj[p_src].add(p_dst)
                        adj[p_dst].add(p_src)

    if extra_connections:
        for p1, p2 in extra_connections:
            if p1 in adj and p2 in adj:
                adj[p1].add(p2)
                adj[p2].add(p1)

    return {p: sorted(list(neighbors)) for p, neighbors in adj.items()}

def find_shortest_path(start_prov, goal_prov):
    """Finds the shortest province sequence between two provinces using BFS."""
    if start_prov == goal_prov:
        return [start_prov]
    if start_prov not in ADJACENCY or goal_prov not in ADJACENCY:
        return None

    visited = {start_prov}
    queue = deque([[start_prov]])

    while queue:
        path = queue.popleft()
        node = path[-1]

        for neighbor in ADJACENCY.get(node, []):
            if neighbor == goal_prov:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return None
