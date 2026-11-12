# CK2-Lite

A lightweight, data-driven grand strategy prototype inspired by **Crusader Kings II**. Built in Python with Pygame and packaged for Windows.

The default campaign data lives in JSON files in `data/`. The main menu's New World flow procedurally generates a fresh map, rulers, and AI roster at runtime.

---

## Features

- **Data-driven Campaign**:
  - `data/scenario.json` sets the title, map, start date, playable ruler and AI roster.
  - `data/characters.json` holds rulers, dynasties, cultures, traits, colors and capitals.
  - `data/provinces.json` and `assets/map/*.json` describe the map and its holdings.
- **Ruler & Dynasty Mechanics**:
  - Swap the player by editing `player_id` — every other living ruler becomes AI automatically.
  - Per-ruler income, aging, levy cooldowns, capitals and titles.
  - 5 core attributes: Diplomacy, Martial, Stewardship, Intrigue, and Learning.
  - Traits, cultural titles, prestige, and piety tracking.
- **Economy & Levies**:
  - Monthly tax collection and garrison recovery for every ruler, not just the player.
  - Land development system to increase tax base and levy size.
  - Tribute flows from vassals to their direct liege.
- **Warfare & Conquest**:
  - Real-time siege progression based on martial attributes.
  - Province annexation, subjugation and vassalage handled by one generic engine.
- **Decision Pop-up Events**:
  - Periodic CK2-style dilemma events.
- **Procedural New Worlds**:
  - Start from the main menu and choose a 10, 20, or 30 province world.
  - Each new campaign generates connected provinces with 30-80 tiles each, fresh rulers, realm ownership, and AI rivals.
  - Character customization is currently a visual mockup; ruler and NPC details are randomized when the campaign starts.

---

## Controls

| Key / Action | Function |
| :--- | :--- |
| **Left Click** | Select province / Click UI buttons |
| **Spacebar** | Pause / Resume game time |
| **1 / 2 / 3** | Set game speed (Normal, Fast, Very Fast) |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Pygame (`pip install pygame`)
- Pillow (`pip install pillow`)

### Running the Game

```bash
# Run directly with Python
python main.py

# Or run via batch file on Windows
run_game.bat
```

Choose **Play** from the main menu, select a world size, then start the campaign to generate a new map and ruler roster.

### Generated Campaigns

Choose **Play**, select 10, 20, or 30 provinces, and start the campaign. The game generates 6-10 sovereigns and assigns one as the player; all other generated sovereigns are AI. The character-maker screen is a placeholder for now.

The JSON `player_id` and `ai_rulers` settings continue to describe the default scenario data, but the New World flow creates its own roster and does not use those IDs.


### Building Standalone Executable (.exe)

```bash
# Install PyInstaller
pip install pyinstaller

# Run the build script
build_exe.bat
```
The compiled executable will be located at `dist/CK2Lite/CK2Lite.exe`.

---

## Development

Headless smoke test (runs every ruler as the player, ticks a year, renders all
tabs, then exercises generic subjugation):

```bash
python tests/smoke_dynamic.py
```

Procedural generator tests:

```bash
python tests/test_world_generator.py
```

`generate_assets.py` regenerates demo icons, heraldry, portraits and the map
preview. It intentionally never touches the hand-authored JSON in `data/`.

---

## License

MIT License.
