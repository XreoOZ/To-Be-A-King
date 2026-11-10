"""
Character and Dynasty Data
"""
import os
import json
import copy
from game.config import DATA_DIR

with open(os.path.join(DATA_DIR, "characters.json"), "r", encoding="utf-8") as f:
    INITIAL_CHARACTERS = json.load(f)

CHARACTERS = copy.deepcopy(INITIAL_CHARACTERS)

def get_character(char_id):
    return CHARACTERS.get(char_id)
