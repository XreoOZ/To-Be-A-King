"""Procedural map and ruler generation for new campaigns."""
import colorsys
import math
import random
import secrets
from collections import deque

from game.config import BASE_TILE_H, BASE_TILE_W, MAP_VIEWPORT_W, PANEL_H

PROVINCE_GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
FIRST_NAMES = [
    "Aldric", "Alina", "Baldwin", "Beren", "Cerys", "Cedric", "Darian",
    "Elowen", "Edrin", "Fiora", "Gareth", "Isolde", "Kael", "Liora",
    "Maeron", "Mira", "Nerys", "Orrin", "Rowan", "Soren", "Talia", "Theron",
    "Valen", "Wynne", "Yorick", "Zephra",
]
EPITHETS = [
    "the Bold", "the Wise", "the Stern", "the Just", "the Red", "the Patient",
    "the Stalwart", "the Fox", "the Radiant", "the Wanderer", "the Strong",
    "the Quiet", "the Great", "the Unbroken", "the Fair",
]
REALM_WORDS = [
    "Ashenvale", "Brightwater", "Dunmere", "Everwold", "Frostmarch",
    "Goldhaven", "Hollowmere", "Ironwood", "Kingsfall", "Mistvale",
    "Northreach", "Ravenmoor", "Silverkeep", "Stormwatch", "Thornfield",
    "Westreach", "Winterhold", "Cinderfall", "Dawnspire", "Greyhaven",
]
CULTURES = [
    ("Aethel", "Old Gods"), ("Dunfolk", "Ancestor Faith"),
    ("Mereborn", "River Saints"), ("Northmen", "The Hearth"),
    ("Sylvan", "World Tree"), ("Highland", "Church of Light"),
    ("Coastlander", "Tide Faith"), ("Ironborn", "Forge Ancestors"),
]
TRAITS = [
    "Brave", "Cautious", "Ambitious", "Just", "Patient", "Generous",
    "Proud", "Cunning", "Diligent", "Stubborn", "Temperate", "Charismatic",
]


class _MapGenerationError(Exception):
    pass


def _neighbors(tile, cols, rows):
    x, y = tile
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        neighbor = (x + dx, y + dy)
        if 1 <= neighbor[0] < cols - 1 and 1 <= neighbor[1] < rows - 1:
            yield neighbor


def _grow_world_once(province_sizes, rng):
    total_tiles = sum(province_sizes)
    inner_cols = max(18, math.ceil(math.sqrt(total_tiles * 1.2)))
    cols = inner_cols + 6
    rows = math.ceil(total_tiles / inner_cols * 1.1) + 6
    center = (cols // 2, rows // 2)

    land = set()
    province_tiles = []
    province_seeds = []
    all_frontier = set()

    for index, target_size in enumerate(province_sizes):
        if index == 0:
            seed = center
        else:
            if not all_frontier:
                raise _MapGenerationError("Unable to expand the generated continent.")
            seed = max(
                all_frontier,
                key=lambda tile: (
                    min((tile[0] - sx) ** 2 + (tile[1] - sy) ** 2
                        for sx, sy in province_seeds) + rng.random() * 8
                ),
            )
            all_frontier.remove(seed)

        region = {seed}
        frontier = set(_neighbors(seed, cols, rows)) - land
        while len(region) < target_size:
            frontier.difference_update(land)
            if not frontier:
                raise _MapGenerationError("Unable to finish a generated province.")

            def growth_score(tile):
                same_neighbors = sum(neighbor in region for neighbor in _neighbors(tile, cols, rows))
                dx = tile[0] - seed[0]
                dy = tile[1] - seed[1]
                return same_neighbors * 1.5 - (dx * dx + dy * dy) * 0.015 + rng.random()

            tile = max(frontier, key=growth_score)
            frontier.remove(tile)
            region.add(tile)
            for neighbor in _neighbors(tile, cols, rows):
                if neighbor not in land and neighbor not in region:
                    frontier.add(neighbor)

        land.update(region)
        province_tiles.append(region)
        province_seeds.append(seed)
        for tile in region:
            all_frontier.update(_neighbors(tile, cols, rows))
        all_frontier.difference_update(land)

    raw_grid = [["." for _ in range(cols)] for _ in range(rows)]
    for index, tiles in enumerate(province_tiles):
        glyph = PROVINCE_GLYPHS[index]
        for x, y in tiles:
            raw_grid[y][x] = glyph
    return ["".join(row) for row in raw_grid], province_tiles, province_seeds


def _grow_world(province_sizes, rng):
    for _ in range(40):
        try:
            return _grow_world_once(province_sizes, rng)
        except _MapGenerationError:
            continue
    raise RuntimeError("Unable to generate a connected map with the selected province sizes.")


def generate_world(province_count, seed=None):
    """Creates a connected land map with 30-80 tiles per province and new rulers."""
    if province_count not in (10, 20, 30):
        raise ValueError("province_count must be one of 10, 20, or 30")

    seed = secrets.randbits(64) if seed is None else int(seed)
    rng = random.Random(seed)
    province_sizes = [rng.randint(30, 80) for _ in range(province_count)]
    raw_grid, province_tiles, province_seeds = _grow_world(province_sizes, rng)
    world_tag = f"{seed:016x}"

    province_ids = [f"province_{world_tag}_{i + 1:02d}" for i in range(province_count)]
    ruler_count = rng.randint(6, min(10, province_count))
    ruler_ids = [f"ruler_{world_tag}_{i + 1:02d}" for i in range(ruler_count)]
    color_order = list(range(ruler_count))
    rng.shuffle(color_order)
    colors = {}
    for i, color_index in enumerate(color_order):
        hue = (color_index * 0.618033988749895 + rng.random() * 0.08) % 1.0
        saturation = rng.uniform(0.58, 0.82)
        value = rng.uniform(0.68, 0.92)
        colors[ruler_ids[i]] = tuple(
            round(channel * 255) for channel in colorsys.hsv_to_rgb(hue, saturation, value)
        )

    char_to_prov = {
        PROVINCE_GLYPHS[i]: province_ids[i] for i in range(province_count)
    }
    cell_to_prov = {}
    provinces = {}
    centroids = {}
    for index, tiles in enumerate(province_tiles):
        pid = province_ids[index]
        tile_list = sorted(tiles)
        for tile in tile_list:
            cell_to_prov[tile] = pid
        capital_tile = sorted(
            tile_list,
            key=lambda tile: (
                (tile[0] - province_seeds[index][0]) ** 2
                + (tile[1] - province_seeds[index][1]) ** 2
            ),
        )[len(tile_list) // 2]
        centroids[pid] = (
            sum(tile[0] for tile in tile_list) / len(tile_list),
            sum(tile[1] for tile in tile_list) / len(tile_list),
        )
        provinces[pid] = {
            "id": pid,
            "name": "",
            "owner": None,
            "tax": rng.randint(10, 24),
            "culture": "",
            "faith": "",
            "color": [130, 130, 130],
            "neighbors": [],
            "coords": [list(tile) for tile in tile_list],
            "capital_tile": list(capital_tile),
            "tiles": [],
        }

    for tile, pid in cell_to_prov.items():
        for neighbor in _neighbors(tile, len(raw_grid[0]), len(raw_grid)):
            other_pid = cell_to_prov.get(neighbor)
            if other_pid and other_pid != pid and other_pid not in provinces[pid]["neighbors"]:
                provinces[pid]["neighbors"].append(other_pid)
    for province in provinces.values():
        province["neighbors"].sort()

    selected_capitals = [0]
    while len(selected_capitals) < ruler_count:
        next_index = max(
            (i for i in range(province_count) if i not in selected_capitals),
            key=lambda i: min(
                (centroids[province_ids[i]][0] - centroids[province_ids[j]][0]) ** 2
                + (centroids[province_ids[i]][1] - centroids[province_ids[j]][1]) ** 2
                for j in selected_capitals
            ),
        )
        selected_capitals.append(next_index)
    rng.shuffle(selected_capitals)

    owner_by_province = {}
    queue = deque()
    for ruler_id, province_index in zip(ruler_ids, selected_capitals):
        capital_id = province_ids[province_index]
        owner_by_province[capital_id] = ruler_id
        queue.append(capital_id)
    while queue:
        current = queue.popleft()
        for neighbor_id in provinces[current]["neighbors"]:
            if neighbor_id not in owner_by_province:
                owner_by_province[neighbor_id] = owner_by_province[current]
                queue.append(neighbor_id)

    characters = {}
    realm_words = rng.sample(REALM_WORDS, ruler_count)
    ruler_first_names = rng.sample(FIRST_NAMES, ruler_count)
    for index, ruler_id in enumerate(ruler_ids):
        first_name = ruler_first_names[index]
        epithet = rng.choice(EPITHETS)
        realm_word = realm_words[index]
        gender = rng.choice(("male", "female"))
        honorific = "King" if gender == "male" else "Queen"
        culture, faith = rng.choice(CULTURES)
        province_index = selected_capitals[index]
        capital_id = province_ids[province_index]
        color = colors[ruler_id]
        character = {
            "id": ruler_id,
            "name": f"{honorific} {first_name} '{epithet}'",
            "personal_name": f"{first_name} '{epithet}'",
            "honorific": honorific,
            "short_name": realm_word,
            "title": f"{honorific} of {realm_word}",
            "dynasty": f"House {realm_word}",
            "realm": f"Kingdom of {realm_word}",
            "duchy_title": f"Duchy of {realm_word}",
            "culture": culture,
            "faith": faith,
            "gender": gender,
            "province": capital_id,
            "capital_province": capital_id,
            "martial": rng.randint(6, 18),
            "stewardship": rng.randint(6, 18),
            "diplomacy": rng.randint(6, 18),
            "learning": rng.randint(6, 18),
            "intrigue": rng.randint(6, 18),
            "gold": rng.randint(180, 320),
            "prestige": rng.randint(80, 260),
            "piety": rng.randint(40, 220),
            "alive": True,
            "age": rng.randint(18, 68),
            "color": list(color),
            "traits": rng.sample(TRAITS, 3),
            "naming": {
                "count_title": "Count" if gender == "male" else "Countess",
                "baron_title": "Baron" if gender == "male" else "Baroness",
                "first_names": rng.sample(FIRST_NAMES, 10),
                "epithets": rng.sample(EPITHETS, 8),
            },
        }
        character["stats"] = {
            stat: character[stat]
            for stat in ("diplomacy", "martial", "stewardship", "intrigue", "learning")
        }
        characters[ruler_id] = character

    ruler_by_id = {ruler_id: characters[ruler_id] for ruler_id in ruler_ids}
    for index, pid in enumerate(province_ids):
        owner_id = owner_by_province[pid]
        ruler = ruler_by_id[owner_id]
        province = provinces[pid]
        province["owner"] = owner_id
        province["name"] = f"{ruler['short_name']} {('March', 'Vale', 'Reach', 'Coast')[index % 4]}"
        province["culture"] = ruler["culture"]
        province["faith"] = ruler["faith"]
        province["color"] = list(ruler["color"])

    map_data = {
        "grid_size": {
            "cols": len(raw_grid[0]),
            "rows": len(raw_grid),
            "tile_size": 24,
        },
        "raw_grid": raw_grid,
        "char_to_prov": char_to_prov,
    }
    zoom = min(
        0.85,
        MAP_VIEWPORT_W / (len(raw_grid[0]) * BASE_TILE_W),
        PANEL_H / (len(raw_grid) * BASE_TILE_H),
    )
    return {
        "seed": seed,
        "map_data": map_data,
        "provinces": provinces,
        "characters": characters,
        "player_id": ruler_ids[0],
        "ai_rulers": ruler_ids[1:],
        "zoom": max(0.25, zoom),
        "province_count": province_count,
    }


def install_generated_world(world):
    """Applies a generated world to the live game data and scenario."""
    from game.data.characters import CHARACTERS
    from game.data.provinces import PROVINCES, refresh_province_faction_colors
    from game.data.scenario import get_scenario
    from game.core.map import apply_map_data

    CHARACTERS.clear()
    CHARACTERS.update(world["characters"])
    PROVINCES.clear()
    PROVINCES.update(world["provinces"])
    apply_map_data(world["map_data"])
    refresh_province_faction_colors()

    scenario = get_scenario()
    scenario.update({
        "id": f"generated_{world['seed']:016x}",
        "title": "CK2-Lite: New World",
        "window_title": "CK2-Lite: New World",
        "subtitle": f"A New Realm of {world['province_count']} Provinces",
        "campaign_label": "New World Campaign",
        "region_name": "the New Realm",
        "chronicle_heading": "Chronicle of the New Realm",
        "map_file": "generated",
        "player_id": world["player_id"],
        "ai_rulers": list(world["ai_rulers"]),
        "zoom": world["zoom"],
        "min_zoom": min(0.65, world["zoom"] * 0.7),
        "intro_logs": [
            f"A new realm takes shape across {world['province_count']} provinces.",
            f"{len(world['characters'])} rulers begin their struggle for power.",
        ],
    })
