import heapq
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

def find_shortest_tile_path(start_tile, goal_tile, owner=None):
    """
    Finds the optimal path between start_tile and goal_tile.
    If owner is provided (e.g. army.owner):
      - If destination is within owner's realm: STRICTLY paths only through tiles belonging
        to owner, ensuring zero border intrusions into foreign lands.
      - If destination is in foreign territory: paths through owner's land and crosses directly
        into target realm, while strictly avoiding third-party neutral realms.
    """
    if start_tile == goal_tile:
        return [start_tile]
    if start_tile not in TILE_ADJACENCY or goal_tile not in TILE_ADJACENCY:
        return None

    from game.data.provinces import PROVINCES

    start_prov = CELL_TO_PROV.get(start_tile)
    goal_prov = CELL_TO_PROV.get(goal_tile)
    start_owner = PROVINCES.get(start_prov, {}).get("owner")
    goal_owner = PROVINCES.get(goal_prov, {}).get("owner")

    if owner is None:
        owner = start_owner

    # Determine allowed realms / owners
    if goal_owner == owner and start_owner == owner:
        # STRICT domestic: only tiles belonging to owner are allowed!
        allowed_set = {owner}
    else:
        # User clicked foreign land, or army is in foreign land moving home/elsewhere
        allowed_set = {owner, goal_owner}
        if start_owner:
            allowed_set.add(start_owner)

    def heuristic(a, b):
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy) + 0.414 * min(dx, dy)

    def get_tile_cost(tile):
        p_id = CELL_TO_PROV.get(tile)
        t_owner = PROVINCES.get(p_id, {}).get("owner")
        if t_owner not in allowed_set:
            return None  # Strictly forbidden
        if t_owner == owner:
            return 1.0   # Domestic territory: lowest cost
        if t_owner == goal_owner:
            return 2.5   # Target foreign territory: allowed when target is foreign
        return 5.0       # Current location foreign territory: allowed to escape

    def run_astar(check_costs=True):
        open_set = []
        heapq.heappush(open_set, (0.0, 0, start_tile, [start_tile]))
        g_scores = {start_tile: 0.0}
        counter = 0

        while open_set:
            f, _, current, path = heapq.heappop(open_set)

            if current == goal_tile:
                return path

            if g_scores.get(current, float('inf')) < f - heuristic(current, goal_tile):
                continue

            for neighbor in TILE_ADJACENCY.get(current, []):
                if check_costs:
                    cost = get_tile_cost(neighbor)
                    if cost is None:
                        continue
                else:
                    cost = 1.0

                step_dist = 1.414 if (neighbor[0] != current[0] and neighbor[1] != current[1]) else 1.0
                tentative_g = g_scores[current] + (cost * step_dist)

                if tentative_g < g_scores.get(neighbor, float('inf')):
                    g_scores[neighbor] = tentative_g
                    h = heuristic(neighbor, goal_tile)
                    counter += 1
                    heapq.heappush(open_set, (tentative_g + h, counter, neighbor, path + [neighbor]))
        return None

    path = run_astar(check_costs=True)
    if not path:
        # Fallback to unrestricted only if terrain connectivity demands it
        path = run_astar(check_costs=False)

    return path
