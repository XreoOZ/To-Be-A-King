# CK2-Lite: Britain AD 867

A lightweight grand strategy prototype inspired by **Crusader Kings II**, focused on the British Isles during the Viking Age (AD 867). Built in Python with Pygame and packaged for Windows.

---

## Features

- **Interactive Blocky Britain Map**:
  - Provinces across Anglo-Saxon England, Danelaw, Wales, Scotland, and Ireland.
  - Hover highlights and click selection with realm borders.
- **Ruler & Dynasty Mechanics**:
  - Play as **Alfred the Great (King of Wessex)** against rivals like Halfdan Ragnarsson (Danelaw/Jorvik) and Burgred (Mercia).
  - 5 core attributes: Diplomacy, Martial, Stewardship, Intrigue, and Learning.
  - Traits, titles, prestige, and piety tracking.
- **Economy & Levies**:
  - Monthly tax collection and garrison recovery.
  - Land development system to increase tax base and levy size.
- **Warfare & Conquest**:
  - Real-time siege progression based on martial attributes.
  - Province annexation on successful conquest.
- **Decision Pop-up Events**:
  - Periodic CK2-style dilemma events (Viking raids, papal envoys, noble disputes).

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

### Building Standalone Executable (.exe)

```bash
# Install PyInstaller
pip install pyinstaller

# Run the build script
build_exe.bat
```
The compiled executable will be located in `dist/CK2Lite/CK2Lite.exe`.

---

## License

MIT License.
