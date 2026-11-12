"""Focused tests for data-driven character display names."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.data.characters import CHARACTERS, get_display_name
from game.core.state import GameState


class DynamicCharacterNameTests(unittest.TestCase):
    def test_display_name_uses_personal_name_and_honorific_metadata(self):
        char_id = next(iter(CHARACTERS))
        original = copy.deepcopy(CHARACTERS[char_id])
        try:
            CHARACTERS[char_id]["personal_name"] = "Andrus"
            CHARACTERS[char_id]["honorific"] = "King"
            CHARACTERS[char_id]["name"] = "King Oldname"

            self.assertEqual(get_display_name(char_id), "King Andrus")
        finally:
            CHARACTERS[char_id].clear()
            CHARACTERS[char_id].update(original)

    def test_renaming_character_updates_personal_name_metadata(self):
        char_id = next(iter(CHARACTERS))
        original = copy.deepcopy(CHARACTERS[char_id])
        try:
            state = GameState.__new__(GameState)
            state.rename_modal = {
                "active": True,
                "type": "character",
                "id": char_id,
                "text": "King Andrus",
            }
            state.vassals = {}
            state.player_id = char_id
            state.enemy_id = None
            state.logs = []

            state.commit_rename()

            self.assertEqual(get_display_name(char_id), "King Andrus")
            self.assertEqual(CHARACTERS[char_id]["personal_name"], "Andrus")
        finally:
            CHARACTERS[char_id].clear()
            CHARACTERS[char_id].update(original)


if __name__ == "__main__":
    unittest.main()
