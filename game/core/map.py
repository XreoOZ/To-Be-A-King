import heapq
"""
Map Grid Parsing, Provincial Boundaries, Tile Adjacency, and BFS Pathfinding
"""
import os
import json
from collections import deque
from game.config import ASSETS_DIR
from game.data.scenario import get_scenario

# Load the map selected by the active scenario definition.
_map_file = get_scenario().get("map_file") or "fantasy_map.json"
map_path = os.path.join(ASSETS_DIR, "map", _map_file)
if not os.path.exists(map_path):
    raise FileNotFoundError(
        f"Scenario map '{_map_file}' was not found at '{map_path}'. "
        "Check the map_file value in data/scenario.json."
    )

with open(map_path, "r", encoding="utf-8") as f:
    MAP_DATA = json.load(f)

RAW_GRID = list(MAP_DATA["raw_grid"])
char_to_prov = dict(MAP_DATA.get("char_to_prov", {}))
CELL_TO_PROV = {}
PROV_TO_TILES = {}
PROV_CAPITAL_TILES = {}
prov_grid_centroids = {}
border_grid_centroids = {}
TILE_ADJACENCY = {}


def apply_map_data(map_data):
    """Rebuilds all map indexes while preserving references imported by game modules."""
    global char_to_prov

    new_map_data = dict(map_data)
    new_raw_grid = list(new_map_data["raw_grid"])
    MAP_DATA.clear()
    MAP_DATA.update(new_map_data)
    RAW_GRID[:] = new_raw_grid
    char_to_prov = dict(new_map_data.get("char_to_prov", {}))

    cell_to_prov = {}
    prov_to_tiles = {}
    for r, row in enumerate(RAW_GRID):
        for c, ch in enumerate(row):
            prov_id = char_to_prov.get(ch)
            if ch == "." or prov_id is None:
                continue
            cell_to_prov[(c, r)] = prov_id
            prov_to_tiles.setdefault(prov_id, []).append((c, r))

    CELL_TO_PROV.clear()
    CELL_TO_PROV.update(cell_to_prov)
    PROV_TO_TILES.clear()
    PROV_TO_TILES.update(prov_to_tiles)

    from game.data.provinces import PROVINCES, ADJACENCY, build_dynamic_province_adjacency

    capitals = {}
    for pid, tiles in PROV_TO_TILES.items():
        declared = (PROVINCES.get(pid) or {}).get("capital_tile")
        if declared and tuple(declared) in tiles:
            capitals[pid] = tuple(declared)
        else:
            capitals[pid] = sorted(tiles)[len(tiles) // 2]
    PROV_CAPITAL_TILES.clear()
    PROV_CAPITAL_TILES.update(capitals)

    centroids = {}
    for (c, r), pid in CELL_TO_PROV.items():
        sx, sy, count = centroids.get(pid, (0, 0, 0))
        centroids[pid] = (sx + c, sy + r, count + 1)
    prov_grid_centroids.clear()
    prov_grid_centroids.update({
        pid: (sx / count, sy / count)
        for pid, (sx, sy, count) in centroids.items()
    })

    border_sums = {}
    for (c, r), pid_a in CELL_TO_PROV.items():
        for dc in range(-2, 3):
            for dr in range(-2, 3):
                if (dc == 0 and dr == 0) or (abs(dc) + abs(dr) > 2):
                    continue
                pid_b = CELL_TO_PROV.get((c + dc, r + dr))
                if pid_b and pid_b != pid_a:
                    pair = (pid_a, pid_b)
                    sx, sy, count = border_sums.get(pair, (0.0, 0.0, 0))
                    border_sums[pair] = (
                        sx + (c + (c + dc)) / 2.0,
                        sy + (r + (r + dr)) / 2.0,
                        count + 1,
                    )
    border_grid_centroids.clear()
    border_grid_centroids.update({
        pair: (sx / count, sy / count)
        for pair, (sx, sy, count) in border_sums.items()
    })

    tile_adjacency = {tile: set() for tile in CELL_TO_PROV}
    for c, r in CELL_TO_PROV:
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if (dc or dr) and (c + dc, r + dr) in CELL_TO_PROV:
                    tile_adjacency[(c, r)].add((c + dc, r + dr))
    TILE_ADJACENCY.clear()
    TILE_ADJACENCY.update(tile_adjacency)

    adjacency = build_dynamic_province_adjacency(CELL_TO_PROV, max_reach=1)
    ADJACENCY.clear()
    ADJACENCY.update(adjacency)

def get_province_capital_tile(pid):
    if pid in PROV_CAPITAL_TILES:
        return PROV_CAPITAL_TILES[pid]
    if pid in PROV_TO_TILES and PROV_TO_TILES[pid]:
        return sorted(PROV_TO_TILES[pid])[0]
    return (0, 0)

apply_map_data(MAP_DATA)

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
