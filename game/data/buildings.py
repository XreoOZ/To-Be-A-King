"""
Modular Building Specifications and Upgrade Curves
"""

BUILDING_SPECS = {
    "city": {
        "name": "City",
        "title": "Commercial Town",
        "desc": "+3g Income, +100 Garrison, +10 Recruits/mo",
        "tiles": 1,
        "cost": 600,
        "income": 3,
        "upkeep": 0,
        "garrison": 100,
        "recruits": 10,
        "icon": "[City]"
    },
    "fort": {
        "name": "Fort",
        "title": "Stone Fortress",
        "desc": "+1g Income, +300 Garrison, +10 Recruits/mo",
        "tiles": 2,
        "cost": 1000,
        "income": 1,
        "upkeep": 0,
        "garrison": 300,
        "recruits": 10,
        "icon": "[Fort]"
    },
    "barrack": {
        "name": "Barracks",
        "title": "Military Barracks",
        "desc": "+100 Garrison slot, +10 Recruits/mo",
        "tiles": 1,
        "cost": 800,
        "income": 0,
        "upkeep": 1,
        "garrison": 100,
        "recruits": 10,
        "icon": "⚔"
    }
}

BARRACK_UPGRADE_COSTS = {
    0: 300,   # Level 0 -> 1
    1: 450,   # Level 1 -> 2
    2: 600,   # Level 2 -> 3
    3: 750,   # Level 3 -> 4
    4: 1000   # Level 4 -> 5
}

def get_barrack_stats(level):
    lvl = max(0, min(5, int(level)))
    garrison = 100 + min(400, lvl * 100)
    recruits = 10 + lvl * 5
    upkeep = 1 + lvl
    return {"level": lvl, "garrison": garrison, "recruits": recruits, "upkeep": upkeep}
