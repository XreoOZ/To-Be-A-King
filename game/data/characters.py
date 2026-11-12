"""
Character, Dynasty, and Ruler Metadata
Scenario-agnostic helpers compose display names, titles, colors and
vassal naming pools from data instead of hardcoded campaign strings.
"""
import os
import json
import copy
import re
from game.config import DATA_DIR

with open(os.path.join(DATA_DIR, "characters.json"), "r", encoding="utf-8") as f:
    INITIAL_CHARACTERS = json.load(f)

CHARACTERS = copy.deepcopy(INITIAL_CHARACTERS)

# Generic honorifics used only as a fallback when legacy data has no
# explicit `honorific` / `personal_name` metadata.
FALLBACK_HONORIFICS = [
    "High King", "High Queen", "King", "Queen", "High Duke", "Grand Duke",
    "Grand Thane", "High Thane", "High Archon", "Archon", "Duke", "Duchess",
    "Count", "Countess", "Thane", "Warden", "Baron", "Baroness",
    "Hearth-Warden", "Elder", "Lord", "Lady", "Jarl", "Emir", "Sultan",
]

DEFAULT_NAMING = {
    "count_title": "Count",
    "baron_title": "Baron",
    "first_names": ["Aldric", "Bertram", "Cedric", "Daria", "Edwin", "Fiona"],
    "epithets": ["the Bold", "the Wise", "the Pious", "the Stalwart"],
}


def get_character(char_id):
    return CHARACTERS.get(char_id)


def get_character_ids(alive_only=True):
    """Returns all character IDs, optionally excluding the deceased."""
    result = []
    for cid, char in CHARACTERS.items():
        if alive_only and not char.get("alive", True):
            continue
        result.append(cid)
    return result


def get_ruler_ids(alive_only=True):
    """Returns characters that actually own at least one province."""
    try:
        from game.data.provinces import PROVINCES
    except Exception:
        return get_character_ids(alive_only)
    rulers = []
    for cid in CHARACTERS:
        if alive_only and not CHARACTERS[cid].get("alive", True):
            continue
        if any(p.get("owner") == cid for p in PROVINCES.values()):
            rulers.append(cid)
    return rulers


def strip_honorific(raw_name, extra_prefixes=None):
    """Strips any known noble prefix from a name, repeatedly."""
    if not raw_name:
        return "Noble"
    clean = str(raw_name).strip()
    prefixes = list(FALLBACK_HONORIFICS)
    for c in CHARACTERS.values():
        h = c.get("honorific")
        if h:
            prefixes.append(str(h))
        naming = c.get("naming") or {}
        for key in ("count_title", "baron_title"):
            if naming.get(key):
                prefixes.append(str(naming[key]))
    if extra_prefixes:
        prefixes.extend(str(p) for p in extra_prefixes if p)
    prefixes = sorted(set(prefixes), key=len, reverse=True)

    changed = True
    while changed:
        changed = False
        for pfx in prefixes:
            if clean.startswith(pfx + " "):
                clean = clean[len(pfx) + 1:].strip()
                changed = True
                break
    return clean or "Noble"


def get_personal_name(char_id):
    """Returns the character's personal name (without honorific)."""
    char = CHARACTERS.get(char_id, {})
    personal = char.get("personal_name")
    if personal:
        return str(personal)
    name = char.get("name", "")
    honorific = char.get("honorific")
    if honorific and name.startswith(str(honorific) + " "):
        return name[len(str(honorific)) + 1:].strip()
    return strip_honorific(name)


def get_honorific(char_id, default=""):
    char = CHARACTERS.get(char_id, {})
    honorific = char.get("honorific")
    if honorific:
        return str(honorific)
    name = str(char.get("name", "")).strip()
    for pfx in sorted(FALLBACK_HONORIFICS, key=len, reverse=True):
        if name.startswith(pfx + " "):
            return pfx
    return default


def get_display_name(char_id, default=""):
    char = CHARACTERS.get(char_id, {})
    personal_name = char.get("personal_name")
    if personal_name:
        return compose_display_name(char.get("honorific"), personal_name)
    return str(char.get("name") or default or char_id or "Unknown")


def compose_display_name(honorific, personal_name):
    honorific = str(honorific or "").strip()
    personal_name = str(personal_name or "").strip()
    if honorific and personal_name:
        return f"{honorific} {personal_name}"
    return personal_name or honorific or "Noble"


def _normalize_character_names(characters):
    for char in characters.values():
        personal_name = char.get("personal_name")
        if personal_name:
            char["name"] = compose_display_name(char.get("honorific"), personal_name)


_normalize_character_names(INITIAL_CHARACTERS)
_normalize_character_names(CHARACTERS)


def get_short_name(char_id):
    """A compact realm/character label for dense UI (territory bar, pills)."""
    char = CHARACTERS.get(char_id, {})
    short = char.get("short_name")
    if short:
        return str(short)
    realm = str(char.get("realm", "") or "")
    if realm:
        words = [w for w in re.split(r"\s+", realm) if w]
        stop = {"the", "of", "holy", "kingdom", "duchy", "grand", "high", "sovereignty", "dominion", "realm"}
        for w in words:
            if w.lower() not in stop:
                return w
    return get_personal_name(char_id)


def get_color(char_id, default=(150, 150, 150)):
    char = CHARACTERS.get(char_id, {})
    color = char.get("color", default)
    try:
        return tuple(int(v) for v in color[:3])
    except Exception:
        return default


def get_naming(char_id):
    naming = copy.deepcopy(DEFAULT_NAMING)
    naming.update(CHARACTERS.get(char_id, {}).get("naming") or {})
    return naming


def get_capital_province(char_id):
    char = CHARACTERS.get(char_id, {})
    return char.get("capital_province") or char.get("province")


def get_realm_name(char_id, default=None):
    char = CHARACTERS.get(char_id, {})
    return char.get("realm") or default or f"Realm of {get_short_name(char_id)}"


def get_title(char_id, default=""):
    char = CHARACTERS.get(char_id, {})
    return char.get("title") or default


def set_character_honorific(char_id, honorific, personal_name=None):
    """Updates honorific and rebuilds the display name from metadata."""
    char = CHARACTERS.get(char_id)
    if not char:
        return False
    pn = personal_name if personal_name is not None else get_personal_name(char_id)
    char["honorific"] = str(honorific or "").strip()
    char["personal_name"] = str(pn or "").strip()
    char["name"] = compose_display_name(char["honorific"], char["personal_name"])
    return True


def set_character_title(char_id, title):
    char = CHARACTERS.setdefault(char_id, {})
    char["title"] = str(title or "")
    return True


def set_character_realm(char_id, realm):
    char = CHARACTERS.setdefault(char_id, {})
    char["realm"] = str(realm or "")
    return True


def character_exists(char_id):
    return char_id in CHARACTERS


def reset_characters():
    CHARACTERS.clear()
    CHARACTERS.update(copy.deepcopy(INITIAL_CHARACTERS))
    _normalize_character_names(CHARACTERS)
