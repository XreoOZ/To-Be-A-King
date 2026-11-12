"""
Scenario Definition Loader
Single source of truth for campaign identity, start date, playable ruler,
map selection, and realm-wide default rules. Game logic and UI should read
from this module instead of hardcoding campaign-specific strings.
"""
import os
import json
import copy
from game.config import DATA_DIR

SCENARIO_FILE = os.path.join(DATA_DIR, "scenario.json")

DEFAULT_SCENARIO = {
    "id": "default",
    "title": "CK2-Lite",
    "window_title": "CK2-Lite",
    "subtitle": "",
    "campaign_label": "",
    "region_name": "the realm",
    "chronicle_heading": "Chronicle",
    "map_file": "fantasy_map.json",
    "start_date": {"year": 1000, "month": 1, "day": 1},
    "player_id": None,
    "ai_rulers": [],
    "vassal_limit": 5,
    "tribute_rate": 0.20,
    "default_vassal_tax_rate": 10,
    "default_vassal_levy_rate": 20,
    "ai_vassal_tax_rate": 20,
    "ai_vassal_levy_rate": 20,
    "zoom": 0.85,
    "intro_logs": [],
}


def _merge_defaults(defaults, override):
    """Recursively merge override values on top of defaults."""
    result = copy.deepcopy(defaults)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_defaults(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _load_initial():
    if not os.path.exists(SCENARIO_FILE):
        return copy.deepcopy(DEFAULT_SCENARIO)
    with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return _merge_defaults(DEFAULT_SCENARIO, raw)


INITIAL_SCENARIO = _load_initial()
SCENARIO = copy.deepcopy(INITIAL_SCENARIO)


def get_scenario():
    """Returns the active scenario dictionary."""
    return SCENARIO


def reset_scenario():
    """Restores the scenario dictionary to its pristine on-disk state."""
    SCENARIO.clear()
    SCENARIO.update(copy.deepcopy(INITIAL_SCENARIO))
    return SCENARIO


def get_scenario_value(key, default=None):
    return SCENARIO.get(key, default)


def get_start_date():
    sd = SCENARIO.get("start_date", {})
    return int(sd.get("year", 1000)), int(sd.get("month", 1)), int(sd.get("day", 1))
