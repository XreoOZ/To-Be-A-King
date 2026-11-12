"""
Province Data, Faction Coloring, and Adjacency Graphs for Fantasy Realm
"""
import os
import json
import copy
import math
import heapq
from collections import deque
from game.config import DATA_DIR
from game.data.characters import CHARACTERS, INITIAL_CHARACTERS, get_color

with open(os.path.join(DATA_DIR, "provinces.json"), "r", encoding="utf-8") as f:
    INITIAL_PROVINCES = json.load(f)

PROVINCES = copy.deepcopy(INITIAL_PROVINCES)
INITIAL_PROVINCE_COLORS = {
    pid: list(p.get("color", (150, 150, 150))) for pid, p in INITIAL_PROVINCES.items()
}

# Faction color lookup is generated from CHARACTERS metadata, so adding a new
# ruler to data/characters.json automatically gives them a map color.
def build_province_faction_colors():
    return {
        cid: {pid: get_color(cid) for pid in PROVINCES}
        for cid in CHARACTERS
    }

PROVINCE_FACTION_COLORS = build_province_faction_colors()

def get_province_color(pid, default=(150, 150, 150)):
    p = PROVINCES.get(pid, {})
    owner = p.get("owner")
    if owner in CHARACTERS and CHARACTERS[owner].get("color"):
        return get_color(owner, default)
    color = p.get("color", INITIAL_PROVINCE_COLORS.get(pid, default))
    try:
        return tuple(int(v) for v in color[:3])
    except Exception:
        return default

def apply_faction_colors():
    """Recolors all provinces according to their current owner's data color."""
    for pid, p in PROVINCES.items():
        owner = p.get("owner")
        if owner in CHARACTERS:
            p["color"] = list(get_province_color(pid))
        elif "color" in p:
            p["color"] = list(p["color"])
        else:
            p["color"] = list(INITIAL_PROVINCE_COLORS.get(pid, (150, 150, 150)))

def refresh_province_faction_colors():
    PROVINCE_FACTION_COLORS.clear()
    PROVINCE_FACTION_COLORS.update(build_province_faction_colors())
    apply_faction_colors()
    return PROVINCE_FACTION_COLORS

# Province Adjacency Graph from JSON neighbors
ADJACENCY = {pid: list(p.get("neighbors", [])) for pid, p in PROVINCES.items()}

apply_faction_colors()

def reset_global_world_data():
    """Restores PROVINCES and CHARACTERS dictionaries to pristine scenario state."""
    CHARACTERS.clear()
    CHARACTERS.update(copy.deepcopy(INITIAL_CHARACTERS))
    PROVINCES.clear()
    PROVINCES.update(copy.deepcopy(INITIAL_PROVINCES))
    refresh_province_faction_colors()

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

def find_shortest_path(start_prov, goal_prov, owner=None):
    """
    Finds the optimal province sequence between start_prov and goal_prov using A* pathfinding
    based on true Euclidean distance between provincial capitals/centroids.
    This guarantees messengers and AI take the geometrically shortest, fastest, and most direct route.
    """
    if start_prov == goal_prov:
        return [start_prov]
    if start_prov not in ADJACENCY or goal_prov not in ADJACENCY:
        return None

    def get_coords(pid):
        p = PROVINCES.get(pid, {})
        if "capital_tile" in p and p["capital_tile"]:
            return float(p["capital_tile"][0]), float(p["capital_tile"][1])
        coords = p.get("coords", [])
        if coords:
            return float(sum(c[0] for c in coords) / len(coords)), float(sum(c[1] for c in coords) / len(coords))
        return (0.0, 0.0)

    goal_c = get_coords(goal_prov)

    def heuristic(pid):
        c = get_coords(pid)
        return math.hypot(c[0] - goal_c[0], c[1] - goal_c[1])

    open_set = []
    # (f_score, g_score, counter, current_node, path)
    heapq.heappush(open_set, (heuristic(start_prov), 0.0, 0, start_prov, [start_prov]))
    g_scores = {start_prov: 0.0}
    counter = 0

    while open_set:
        f, g, _, current, path = heapq.heappop(open_set)

        if current == goal_prov:
            return path

        if g > g_scores.get(current, float('inf')):
            continue

        for neighbor in ADJACENCY.get(current, []):
            c_curr = get_coords(current)
            c_next = get_coords(neighbor)
            base_dist = math.hypot(c_next[0] - c_curr[0], c_next[1] - c_curr[1])

            multiplier = 1.0
            if owner is not None:
                n_owner = PROVINCES.get(neighbor, {}).get("owner")
                if n_owner != owner:
                    multiplier = 1.15

            step_cost = max(1.0, base_dist) * multiplier
            tentative_g = g + step_cost

            if tentative_g < g_scores.get(neighbor, float('inf')):
                g_scores[neighbor] = tentative_g
                h = heuristic(neighbor)
                counter += 1
                heapq.heappush(open_set, (tentative_g + h, tentative_g, counter, neighbor, path + [neighbor]))

    return None
