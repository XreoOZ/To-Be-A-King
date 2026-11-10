"""
Map Grid Parsing, Provincial Boundaries, Tile Adjacency, and BFS Pathfinding
"""
import os
import json
from collections import deque
from game.config import ASSETS_DIR

# Load Fantasy Continent Map specification
map_path = os.path.join(ASSETS_DIR, "map", "fantasy_map.json")
if not os.path.exists(map_path):
    map_path = os.path.join(ASSETS_DIR, "map", "britain_map.json")

with open(map_path, "r", encoding="utf-8") as f:
    MAP_DATA = json.load(f)

RAW_GRID = MAP_DATA["raw_grid"]
char_to_prov = MAP_DATA.get("char_to_prov", {})

CELL_TO_PROV = {}
PROV_TO_TILES = {}

for r, row in enumerate(RAW_GRID):
    for c, ch in enumerate(row):
        if ch == ".":
            continue
        if char_to_prov and ch in char_to_prov:
            prov_id = char_to_prov[ch]
        else:
            # Fallback legacy Britain letters
            if ch == "H": prov_id = "highlands"
            elif ch == "S": prov_id = "strathclyde"
            elif ch in ("T", "L"): prov_id = "lothian"
            elif ch == "B": prov_id = "bernicia"
            elif ch == "D": prov_id = "deira"
            elif ch == "Y": prov_id = "jorvik"
            elif ch == "M": prov_id = "mercia"
            elif ch == "E": prov_id = "east_anglia"
            elif ch == "W": prov_id = "wales" if r <= 17 else "wessex"
            elif ch == "K": prov_id = "kent_essex"
            elif ch == "C": prov_id = "cornwall"
            else: prov_id = "wessex"
            
        CELL_TO_PROV[(c, r)] = prov_id
        PROV_TO_TILES.setdefault(prov_id, []).append((c, r))

# Precompute Capital Tile for each province
PROV_CAPITAL_TILES = {}
for pid, tiles in PROV_TO_TILES.items():
    t_sorted = sorted(tiles)
    PROV_CAPITAL_TILES[pid] = t_sorted[len(t_sorted) // 2]

def get_province_capital_tile(pid):
    if pid in PROV_CAPITAL_TILES:
        return PROV_CAPITAL_TILES[pid]
    if pid in PROV_TO_TILES and PROV_TO_TILES[pid]:
        return sorted(PROV_TO_TILES[pid])[0]
    return (11, 10)

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

# Build Seamless 8-Way Tile Adjacency across pure continental landmass
TILE_ADJACENCY = {t: set() for t in CELL_TO_PROV}
for (c, r) in CELL_TO_PROV:
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == 0 and dr == 0:
                continue
            nt = (c + dc, r + dr)
            if nt in CELL_TO_PROV:
                TILE_ADJACENCY[(c, r)].add(nt)

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
