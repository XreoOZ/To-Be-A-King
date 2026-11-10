"""
Map Grid Parsing, Provincial Boundaries, Tile Adjacency, and BFS Pathfinding
"""
import os
import json
from collections import deque
from game.config import ASSETS_DIR

# Load Britain Map specification
with open(os.path.join(ASSETS_DIR, "map", "britain_map.json"), "r", encoding="utf-8") as f:
    MAP_DATA = json.load(f)

RAW_GRID = MAP_DATA["raw_grid"]

CELL_TO_PROV = {}
PROV_TO_TILES = {}

for r, row in enumerate(RAW_GRID):
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
        CELL_TO_PROV[(c, r)] = prov_id
        PROV_TO_TILES.setdefault(prov_id, []).append((c, r))

# Precompute Capital / Centroid Tile for each of the 12 provinces
PROV_CAPITAL_TILES = {
    "bernicia": (14, 9),
    "cornwall": (6, 20),
    "deira": (16, 11),
    "east_anglia": (17, 16),
    "highlands": (9, 3),
    "jorvik": (14, 11),
    "kent_essex": (14, 19),
    "lothian": (12, 7),
    "mercia": (14, 15),
    "strathclyde": (8, 7),
    "wales": (9, 15),
    "wessex": (11, 20),
}

def get_province_capital_tile(pid):
    return PROV_CAPITAL_TILES.get(pid, (11, 20))

# Compute province centroids in grid units
prov_grid_sum = {}
for (c, r), pid in CELL_TO_PROV.items():
    if pid not in prov_grid_sum:
        prov_grid_sum[pid] = [0, 0, 0]
    prov_grid_sum[pid][0] += c
    prov_grid_sum[pid][1] += r
    prov_grid_sum[pid][2] += 1

prov_grid_centroids = {}
for pid, (sc, sr, count) in prov_grid_sum.items():
    prov_grid_centroids[pid] = (sc / count, sr / count)

border_grid_sums = {}
for (c, r), pid_a in CELL_TO_PROV.items():
    for dc in range(-2, 3):
        for dr in range(-2, 3):
            if (dc == 0 and dr == 0) or (abs(dc) + abs(dr) > 2):
                continue
            pid_b = CELL_TO_PROV.get((c + dc, r + dr))
            if pid_b and pid_b != pid_a:
                pair_key = (pid_a, pid_b)
                if pair_key not in border_grid_sums:
                    border_grid_sums[pair_key] = [0.0, 0.0, 0]
                border_grid_sums[pair_key][0] += (c + (c + dc)) / 2.0
                border_grid_sums[pair_key][1] += (r + (r + dr)) / 2.0
                border_grid_sums[pair_key][2] += 1

border_grid_centroids = {}
for pair_key, (sc, sr, count) in border_grid_sums.items():
    border_grid_centroids[pair_key] = (sc / count, sr / count)

# Build Seamless 8-Way Tile Adjacency with Historical Water Strait Crossings
TILE_ADJACENCY = {t: set() for t in CELL_TO_PROV}
for (c, r) in CELL_TO_PROV:
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == 0 and dr == 0:
                continue
            nt = (c + dc, r + dr)
            if nt in CELL_TO_PROV:
                TILE_ADJACENCY[(c, r)].add(nt)

# Bridges / Fords across narrow straits (Tamar for Cornwall, Severn for Wales)
for t1 in CELL_TO_PROV:
    p1 = CELL_TO_PROV[t1]
    for t2 in CELL_TO_PROV:
        p2 = CELL_TO_PROV[t2]
        if p1 != p2:
            d = max(abs(t1[0] - t2[0]), abs(t1[1] - t2[1]))
            if d <= 2 and (
                (p1 == "cornwall" and p2 == "wessex") or (p1 == "wessex" and p2 == "cornwall") or
                (p1 == "wales" and p2 in ("mercia", "wessex")) or (p1 in ("mercia", "wessex") and p2 == "wales")
            ):
                TILE_ADJACENCY[t1].add(t2)
                TILE_ADJACENCY[t2].add(t1)

def find_shortest_tile_path(start_tile, goal_tile):
    if start_tile == goal_tile:
        return [start_tile]
    if start_tile not in TILE_ADJACENCY or goal_tile not in TILE_ADJACENCY:
        return None
    queue = deque([[start_tile]])
    visited = {start_tile}
    while queue:
        path = queue.popleft()
        node = path[-1]
        neighbors = sorted(TILE_ADJACENCY[node], key=lambda t: (t[0]-goal_tile[0])**2 + (t[1]-goal_tile[1])**2)
        for neighbor in neighbors:
            if neighbor == goal_tile:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None
