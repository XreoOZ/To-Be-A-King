"""
CK2-Lite Asset Generator
Generates mock/dummy blocky retro assets:
- UI Icons (Gold, Prestige, Piety, Troops, Speed, etc.)
- Heraldry / Shields (Coats of Arms)
- Character Portraits (Blocky medieval portraits)
- Britain Province Grid & Map Preview
"""

import os
import json
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
HERALDRY_DIR = os.path.join(ASSETS_DIR, "heraldry")
PORTRAITS_DIR = os.path.join(ASSETS_DIR, "portraits")
MAP_DIR = os.path.join(ASSETS_DIR, "map")
DATA_DIR = os.path.join(BASE_DIR, "data")

for d in [ICONS_DIR, HERALDRY_DIR, PORTRAITS_DIR, MAP_DIR, DATA_DIR]:
    os.makedirs(d, exist_ok=True)

# -------------------------------------------------------------
# 1. GENERATE ICONS (32x32 pixel blocky style)
# -------------------------------------------------------------
def make_icon_gold():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Gold coin outer
    d.ellipse([4, 4, 27, 27], fill=(218, 165, 32), outline=(139, 101, 8), width=2)
    # Inner rim
    d.ellipse([7, 7, 24, 24], outline=(255, 215, 0), width=1)
    # Coin detail ($ / cross / gem)
    d.rectangle([13, 10, 18, 21], fill=(255, 235, 100))
    d.rectangle([10, 13, 21, 18], fill=(255, 235, 100))
    img.save(os.path.join(ICONS_DIR, "gold.png"))

def make_icon_prestige():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Blue ribbon / shield background
    d.polygon([(16, 2), (28, 7), (24, 26), (16, 30), (8, 26), (4, 7)], fill=(30, 80, 160), outline=(20, 50, 110), width=1)
    # Golden Crown
    d.polygon([(8, 20), (8, 14), (12, 16), (16, 11), (20, 16), (24, 14), (24, 20)], fill=(255, 215, 0), outline=(180, 140, 0))
    d.rectangle([9, 21, 23, 23], fill=(218, 165, 32))
    # Red gem in crown
    d.point([(16, 17)], fill=(220, 30, 30))
    img.save(os.path.join(ICONS_DIR, "prestige.png"))

def make_icon_piety():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Halo glow
    d.ellipse([4, 4, 27, 27], fill=(255, 250, 200, 100))
    # Holy Cross
    d.rectangle([13, 6, 18, 26], fill=(240, 240, 255), outline=(160, 160, 200))
    d.rectangle([8, 11, 23, 16], fill=(240, 240, 255), outline=(160, 160, 200))
    d.rectangle([14, 12, 17, 15], fill=(255, 215, 0))
    img.save(os.path.join(ICONS_DIR, "piety.png"))

def make_icon_troops():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Crossed swords
    # Sword 1 (top-left to bottom-right)
    d.line([(6, 6), (25, 25)], fill=(200, 210, 220), width=3)
    d.line([(5, 5), (7, 7)], fill=(255, 255, 255), width=2)
    d.line([(22, 26), (26, 22)], fill=(139, 69, 19), width=2)
    # Sword 2 (top-right to bottom-left)
    d.line([(25, 6), (6, 25)], fill=(200, 210, 220), width=3)
    d.line([(24, 5), (26, 7)], fill=(255, 255, 255), width=2)
    d.line([(6, 22), (10, 26)], fill=(139, 69, 19), width=2)
    # Center shield mini
    d.polygon([(16, 10), (22, 13), (20, 22), (16, 25), (12, 22), (10, 13)], fill=(180, 40, 40), outline=(80, 20, 20))
    img.save(os.path.join(ICONS_DIR, "troops.png"))

def make_icon_speed():
    # Pause
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 29, 29], fill=(45, 50, 60), outline=(80, 90, 105), width=2)
    d.rectangle([9, 8, 13, 23], fill=(220, 220, 220))
    d.rectangle([18, 8, 22, 23], fill=(220, 220, 220))
    img.save(os.path.join(ICONS_DIR, "speed_pause.png"))

    # Play (Speed 1)
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 29, 29], fill=(45, 50, 60), outline=(80, 90, 105), width=2)
    d.polygon([(11, 8), (24, 16), (11, 24)], fill=(100, 220, 120))
    img.save(os.path.join(ICONS_DIR, "speed_play.png"))

    # Fast (Speed 2)
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 29, 29], fill=(45, 50, 60), outline=(80, 90, 105), width=2)
    d.polygon([(8, 8), (17, 16), (8, 24)], fill=(240, 200, 80))
    d.polygon([(16, 8), (25, 16), (16, 24)], fill=(240, 200, 80))
    img.save(os.path.join(ICONS_DIR, "speed_fast.png"))

# -------------------------------------------------------------
# 2. GENERATE HERALDRY / SHIELDS (48x56 pixel medieval shields)
# -------------------------------------------------------------
REALM_COLORS = {
    "wessex": {
        "name": "Wessex",
        "bg": (180, 30, 30),         # Saxon Red
        "outline": (100, 15, 15),
        "symbol": "dragon",
        "sym_color": (255, 215, 0)    # Golden Dragon/Cross
    },
    "mercia": {
        "name": "Mercia",
        "bg": (25, 55, 135),          # Mercian Royal Blue
        "outline": (15, 30, 80),
        "symbol": "saltire",          # St. Alban's Cross
        "sym_color": (255, 215, 0)
    },
    "northumbria": {
        "name": "Northumbria",
        "bg": (150, 25, 25),          # Vertical red & gold
        "outline": (80, 15, 15),
        "symbol": "stripes",
        "sym_color": (255, 200, 50)
    },
    "east_anglia": {
        "name": "East Anglia",
        "bg": (30, 85, 150),
        "outline": (15, 45, 90),
        "symbol": "crowns",           # Three golden crowns
        "sym_color": (255, 215, 0)
    },
    "danelaw": {
        "name": "Danelaw",
        "bg": (45, 45, 50),           # Norse Raven Dark
        "outline": (160, 30, 30),
        "symbol": "raven",
        "sym_color": (200, 30, 30)
    },
    "wales": {
        "name": "Wales",
        "bg": (35, 130, 60),          # Welsh Green
        "outline": (15, 65, 30),
        "symbol": "dragon",
        "sym_color": (220, 40, 40)
    },
    "scotland": {
        "name": "Scotland",
        "bg": (20, 60, 140),          # Royal Azure
        "outline": (10, 30, 80),
        "symbol": "saltire",          # White St. Andrew's
        "sym_color": (245, 245, 255)
    },
    "ireland": {
        "name": "Ireland",
        "bg": (30, 115, 70),          # Emerald Green
        "outline": (15, 60, 35),
        "symbol": "harp",
        "sym_color": (255, 215, 0)
    }
}

def draw_shield(realm_key, info):
    w, h = 48, 56
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Medieval shield polygon
    pts = [
        (4, 4), (43, 4),
        (43, 34),
        (24, 51),
        (4, 34)
    ]
    # Background fill
    d.polygon(pts, fill=info["bg"])

    # Symbols
    sym = info["symbol"]
    col = info["sym_color"]

    if sym == "saltire":
        # Diagonal cross
        d.line([(8, 8), (39, 39)], fill=col, width=5)
        d.line([(39, 8), (8, 39)], fill=col, width=5)
    elif sym == "stripes":
        d.rectangle([11, 4, 17, 42], fill=col)
        d.rectangle([30, 4, 36, 42], fill=col)
    elif sym == "dragon":
        # Blocky wyvern/dragon silhouette
        d.rectangle([18, 16, 29, 28], fill=col)
        d.rectangle([25, 11, 33, 17], fill=col) # head
        d.polygon([(14, 12), (18, 19), (11, 23)], fill=col) # wing
        d.polygon([(24, 28), (20, 37), (27, 34)], fill=col) # tail
    elif sym == "crowns":
        # 3 crowns
        for cx, cy in [(24, 14), (16, 27), (31, 27)]:
            d.polygon([(cx-5, cy+3), (cx-5, cy-2), (cx-2, cy), (cx, cy-3), (cx+2, cy), (cx+5, cy-2), (cx+5, cy+3)], fill=col)
    elif sym == "raven":
        # Viking raven wings
        d.polygon([(24, 15), (14, 22), (20, 27), (24, 34), (27, 27), (33, 22)], fill=col)
        d.rectangle([22, 11, 25, 16], fill=col) # head
    elif sym == "harp":
        d.line([(16, 12), (16, 36)], fill=col, width=3)
        d.arc([16, 12, 32, 34], 270, 90, fill=col, width=3)
        d.line([(19, 16), (25, 16)], fill=col, width=1)
        d.line([(19, 22), (28, 22)], fill=col, width=1)
        d.line([(19, 28), (27, 28)], fill=col, width=1)

    # Border outline & bevel
    d.polygon(pts, outline=info["outline"], width=3)
    # Highlight on top/left
    d.line([(5, 5), (42, 5)], fill=(255, 255, 255, 90), width=2)
    d.line([(5, 5), (5, 33)], fill=(255, 255, 255, 90), width=2)

    img.save(os.path.join(HERALDRY_DIR, f"coa_{realm_key}.png"))

# -------------------------------------------------------------
# 3. GENERATE DUMMY RETRO PORTRAITS (64x64 pixel character cards)
# -------------------------------------------------------------
PORTRAIT_DATA = [
    {
        "id": "portrait_alfred",
        "name": "King Alfred",
        "crown": True,
        "hair_color": (160, 110, 50),
        "tunic_color": (180, 30, 30),
        "beard": True,
        "frame_col": (218, 165, 32)
    },
    {
        "id": "portrait_burgred",
        "name": "King Burgred",
        "crown": True,
        "hair_color": (70, 50, 35),
        "tunic_color": (25, 55, 135),
        "beard": True,
        "frame_col": (190, 190, 210)
    },
    {
        "id": "portrait_halfden",
        "name": "Halfdan Ragnarsson",
        "crown": False,
        "helmet": True,
        "hair_color": (200, 160, 70),
        "tunic_color": (45, 45, 50),
        "beard": True,
        "frame_col": (160, 40, 40)
    },
    {
        "id": "portrait_rhodri",
        "name": "King Rhodri Mawr",
        "crown": True,
        "hair_color": (50, 40, 35),
        "tunic_color": (35, 130, 60),
        "beard": True,
        "frame_col": (218, 165, 32)
    },
    {
        "id": "portrait_constantine",
        "name": "King Causantin",
        "crown": True,
        "hair_color": (120, 60, 30),
        "tunic_color": (20, 60, 140),
        "beard": True,
        "frame_col": (200, 200, 200)
    },
    {
        "id": "portrait_default",
        "name": "Noble Courtier",
        "crown": False,
        "hair_color": (90, 70, 50),
        "tunic_color": (100, 90, 80),
        "beard": False,
        "frame_col": (110, 100, 90)
    }
]

def make_portrait(p):
    w, h = 64, 64
    img = Image.new("RGBA", (w, h), (30, 32, 40, 255))
    d = ImageDraw.Draw(img)

    # Gradient background wall
    for y in range(h):
        shade = int(35 + y * 0.4)
        d.line([(0, y), (w, y)], fill=(shade, shade + 5, shade + 15))

    # Shoulders / Tunic
    tc = p["tunic_color"]
    d.polygon([(12, 60), (22, 44), (42, 44), (52, 60)], fill=tc, outline=(tc[0]//2, tc[1]//2, tc[2]//2))
    # Cloak clasp / collar
    d.rectangle([27, 44, 37, 50], fill=(218, 165, 32))

    # Neck
    skin = (235, 195, 160)
    d.rectangle([28, 38, 36, 44], fill=(215, 175, 140))

    # Face base
    d.rectangle([22, 22, 42, 39], fill=skin)
    d.polygon([(22, 38), (32, 43), (42, 38)], fill=skin)

    # Hair
    hc = p["hair_color"]
    d.rectangle([20, 16, 44, 23], fill=hc)
    d.rectangle([19, 21, 23, 33], fill=hc)
    d.rectangle([41, 21, 45, 33], fill=hc)

    # Eyes & Eyebrows
    d.rectangle([25, 27, 28, 29], fill=(40, 35, 30))
    d.rectangle([36, 27, 39, 29], fill=(40, 35, 30))
    d.line([(24, 25), (29, 25)], fill=(30, 25, 20), width=1)
    d.line([(35, 25), (40, 25)], fill=(30, 25, 20), width=1)

    # Nose
    d.line([(32, 29), (32, 33)], fill=(200, 150, 120), width=2)

    # Mouth / Beard
    if p.get("beard"):
        d.rectangle([25, 35, 39, 42], fill=hc)
        d.polygon([(26, 41), (32, 45), (38, 41)], fill=hc)
    else:
        d.line([(29, 36), (35, 36)], fill=(180, 110, 100), width=1)

    # Helmet or Crown
    if p.get("helmet"):
        # Viking/Saxon Spangenhelm
        d.polygon([(19, 19), (32, 10), (45, 19)], fill=(160, 165, 175))
        d.rectangle([20, 18, 44, 22], fill=(180, 185, 195))
        d.line([(32, 10), (32, 26)], fill=(218, 165, 32), width=2) # Nasal guard
    elif p.get("crown"):
        # Golden crown
        d.polygon([
            (21, 18), (21, 13), (25, 15), (32, 10), (39, 15), (43, 13), (43, 18)
        ], fill=(255, 215, 0), outline=(180, 140, 0))
        d.rectangle([21, 18, 43, 20], fill=(218, 165, 32))
        # Jewels
        d.point([(26, 17), (32, 14), (38, 17)], fill=(220, 30, 30))

    # Ornate Card Frame
    fc = p["frame_col"]
    d.rectangle([0, 0, w-1, h-1], outline=fc, width=3)
    d.rectangle([2, 2, w-3, h-3], outline=(20, 20, 20), width=1)
    # Corner studs
    for cx, cy in [(2, 2), (w-4, 2), (2, h-4), (w-4, h-4)]:
        d.rectangle([cx, cy, cx+1, cy+1], fill=(255, 235, 150))

    img.save(os.path.join(PORTRAITS_DIR, f"{p['id']}.png"))

# -------------------------------------------------------------
# 4. BRITAIN MAP & PROVINCES (Grid-based Mock Layout)
# -------------------------------------------------------------
# We define a 20 columns x 26 rows blocky grid of Britain & Ireland.
# Each cell is either ocean ("..") or a Province ID code.
#
MAP_GRID = [
    # 01234567890123456789
    "........HH..........", # 0 Highlands (Scotland)
    ".......HHHHH........", # 1
    "......HHHHHHHH......", # 2
    "......AAAHHHH.......", # 3 Alba
    ".....AAAAAAAH.......", # 4
    "....U.AAAAAAA.......", # 5 Ulster / Alba
    "...UUU..STT.LL......", # 6 Strathclyde / Lothian
    "..UUUU..SST.LLL.....", # 7
    "..C.UU..S...NBBN....", # 8 Connacht / Bernicia
    ".CCC.........NBBBN..", # 9
    ".CCC..M......NNBBN..", # 10 Isle of Man / Deira
    ".CC.MMM.......YYDD..", # 11 Jorvik / York
    "..L.MMM..WW...YYDD..", # 12 Leinster / Gwynedd
    "..LLMMM.WWW...MMMM..", # 13 Mercia
    "..LL....WWPP.MMMMM..", # 14 Powys
    "...LL..PPP...MMMEE..", # 15 East Anglia
    "....L..DDD..MMMEEEE.", # 16 Deheubarth
    "........DD..MMMEEEE.", # 17
    "............KKK..SS.", # 18 Essex
    "......CC.WWWWKKKK...", # 19 Wessex / Kent
    ".....CCC.WWWWWW.....", # 20
    "....CCCC.WWWWWW.....", # 21 Cornwall
    ".....C....WWWW......", # 22
    "....................", # 23
    "....................", # 24
    "...................."  # 25
]

PROVINCE_DEFS = {
    "H": {
        "id": "highlands",
        "name": "Scottish Highlands",
        "realm": "scotland",
        "color": (40, 80, 160),
        "tax": 5,
        "levies": 600,
        "owner_id": "char_constantine"
    },
    "A": {
        "id": "alba",
        "name": "Kingdom of Alba",
        "realm": "scotland",
        "color": (25, 65, 145),
        "tax": 10,
        "levies": 1200,
        "owner_id": "char_constantine"
    },
    "L": {
        "id": "lothian",
        "name": "Lothian",
        "realm": "scotland",
        "color": (60, 100, 175),
        "tax": 8,
        "levies": 900,
        "owner_id": "char_constantine"
    },
    "S": {
        "id": "strathclyde",
        "name": "Strathclyde",
        "realm": "scotland",
        "color": (75, 115, 190),
        "tax": 6,
        "levies": 750,
        "owner_id": "char_constantine"
    },
    "B": {
        "id": "bernicia",
        "name": "Bernicia (Northumbria)",
        "realm": "northumbria",
        "color": (160, 45, 45),
        "tax": 8,
        "levies": 1000,
        "owner_id": "char_halfden"
    },
    "N": {
        "id": "deira",
        "name": "Deira",
        "realm": "northumbria",
        "color": (180, 60, 50),
        "tax": 9,
        "levies": 1100,
        "owner_id": "char_halfden"
    },
    "Y": {
        "id": "jorvik",
        "name": "Jorvik (Danelaw)",
        "realm": "danelaw",
        "color": (70, 70, 75),
        "tax": 14,
        "levies": 1800,
        "owner_id": "char_halfden"
    },
    "M": {
        "id": "mercia",
        "name": "Kingdom of Mercia",
        "realm": "mercia",
        "color": (210, 170, 40),
        "tax": 12,
        "levies": 1500,
        "owner_id": "char_burgred"
    },
    "E": {
        "id": "east_anglia",
        "name": "East Anglia",
        "realm": "east_anglia",
        "color": (220, 120, 40),
        "tax": 10,
        "levies": 1200,
        "owner_id": "char_burgred"
    },
    "W": {
        "id": "gwynedd",
        "name": "Gwynedd (North Wales)",
        "realm": "wales",
        "color": (35, 140, 65),
        "tax": 7,
        "levies": 800,
        "owner_id": "char_rhodri"
    },
    "P": {
        "id": "powys",
        "name": "Powys (Mid Wales)",
        "realm": "wales",
        "color": (50, 160, 80),
        "tax": 6,
        "levies": 700,
        "owner_id": "char_rhodri"
    },
    "D": {
        "id": "deheubarth",
        "name": "Deheubarth (South Wales)",
        "realm": "wales",
        "color": (65, 175, 95),
        "tax": 7,
        "levies": 850,
        "owner_id": "char_rhodri"
    },
    "W": {
        "id": "wessex",
        "name": "Kingdom of Wessex",
        "realm": "wessex",
        "color": (195, 30, 30),
        "tax": 15,
        "levies": 2000,
        "owner_id": "char_alfred"
    },
    "K": {
        "id": "kent_essex",
        "name": "Kent & Essex",
        "realm": "wessex",
        "color": (215, 60, 60),
        "tax": 11,
        "levies": 1300,
        "owner_id": "char_alfred"
    },
    "C": {
        "id": "cornwall",
        "name": "Cornwall",
        "realm": "wessex",
        "color": (175, 50, 70),
        "tax": 6,
        "levies": 700,
        "owner_id": "char_alfred"
    },
    "U": {
        "id": "ulster",
        "name": "Ulster (Ireland)",
        "realm": "ireland",
        "color": (30, 120, 75),
        "tax": 6,
        "levies": 750,
        "owner_id": "char_default"
    }
}

# Resolve cell codes properly
CODE_MAP = {
    "H": "highlands",
    "A": "alba",
    "T": "lothian",
    "S": "strathclyde",
    "B": "bernicia",
    "N": "deira",
    "Y": "jorvik",
    "M": "mercia",
    "E": "east_anglia",
    "W": "gwynedd",
    "P": "powys",
    "D": "deheubarth",
    "W": "wessex",
    "K": "kent_essex",
    "C": "cornwall",
    "U": "ulster"
}

def generate_map_assets():
    # Tile size in preview
    tile_w, tile_h = 24, 24
    rows = len(MAP_GRID)
    cols = len(MAP_GRID[0])

    img = Image.new("RGBA", (cols * tile_w, rows * tile_h), (25, 45, 75, 255)) # Ocean deep blue
    d = ImageDraw.Draw(img)

    province_tiles = {}

    for r, row in enumerate(MAP_GRID):
        for c, ch in enumerate(row):
            x1 = c * tile_w
            y1 = r * tile_h
            x2 = x1 + tile_w
            y2 = y1 + tile_h

            if ch == ".":
                # Ocean waves mock detail
                if (r + c) % 5 == 0:
                    d.line([(x1 + 4, y1 + 12), (x1 + 12, y1 + 12)], fill=(35, 60, 95))
            else:
                prov_id = None
                # Custom character resolution
                if ch == "H": prov_id = "highlands"
                elif ch == "A": prov_id = "alba"
                elif ch == "T": prov_id = "lothian"
                elif ch == "S" and r < 10: prov_id = "strathclyde"
                elif ch == "B": prov_id = "bernicia"
                elif ch == "N": prov_id = "deira"
                elif ch == "Y": prov_id = "jorvik"
                elif ch == "M" and c > 10: prov_id = "mercia"
                elif ch == "E": prov_id = "east_anglia"
                elif ch == "W" and r < 15: prov_id = "gwynedd"
                elif ch == "P": prov_id = "powys"
                elif ch == "D" and r > 14: prov_id = "deheubarth"
                elif ch == "W" and r >= 19: prov_id = "wessex"
                elif ch == "K": prov_id = "kent_essex"
                elif ch == "C" and c > 5: prov_id = "cornwall"
                elif ch == "U": prov_id = "ulster"
                elif ch == "C" and c <= 5: prov_id = "connacht"
                elif ch == "L" and c <= 5: prov_id = "leinster"
                elif ch == "M" and c <= 5: prov_id = "munster"
                else: prov_id = "wessex"

                if prov_id not in province_tiles:
                    province_tiles[prov_id] = []
                province_tiles[prov_id].append({"x": c, "y": r})

                # Determine color
                pinfo = PROVINCE_DEFS.get(ch, {"color": (160, 160, 160)})
                col = pinfo["color"]

                # Draw block tile with subtle 3D border
                d.rectangle([x1, y1, x2 - 1, y2 - 1], fill=col)
                d.line([(x1, y1), (x2 - 1, y1)], fill=(col[0] + 30, col[1] + 30, col[2] + 30))
                d.line([(x1, y1), (x1, y2 - 1)], fill=(col[0] + 30, col[1] + 30, col[2] + 30))
                d.line([(x1, y2 - 1), (x2 - 1, y2 - 1)], fill=(max(0, col[0] - 40), max(0, col[1] - 40), max(0, col[2] - 40)))
                d.line([(x2 - 1, y1), (x2 - 1, y2 - 1)], fill=(max(0, col[0] - 40), max(0, col[1] - 40), max(0, col[2] - 40)))

    # Save map preview image
    img.save(os.path.join(MAP_DIR, "britain_map_preview.png"))

    # Save map JSON data
    map_data = {
        "grid_size": {"cols": cols, "rows": rows, "tile_size": tile_w},
        "raw_grid": MAP_GRID,
        "provinces": province_tiles
    }
    with open(os.path.join(MAP_DIR, "britain_map.json"), "w", encoding="utf-8") as f:
        json.dump(map_data, f, indent=2)

# -------------------------------------------------------------
# 5. INITIAL GAME DATABASE (Provinces & Characters)
# -------------------------------------------------------------
def generate_game_data():
    characters = {
        "char_alfred": {
            "id": "char_alfred",
            "name": "Alfred 'the Great'",
            "title": "King of Wessex",
            "dynasty": "House of Wessex",
            "realm": "wessex",
            "portrait": "portrait_alfred.png",
            "coa": "coa_wessex.png",
            "age": 22,
            "alive": True,
            "stats": {"diplomacy": 14, "martial": 16, "stewardship": 15, "intrigue": 11, "learning": 18},
            "gold": 120,
            "prestige": 250,
            "piety": 180,
            "traits": ["Brave", "Just", "Scholar"]
        },
        "char_burgred": {
            "id": "char_burgred",
            "name": "Burgred",
            "title": "King of Mercia",
            "dynasty": "House of Mercia",
            "realm": "mercia",
            "portrait": "portrait_burgred.png",
            "coa": "coa_mercia.png",
            "age": 41,
            "alive": True,
            "stats": {"diplomacy": 11, "martial": 9, "stewardship": 12, "intrigue": 8, "learning": 9},
            "gold": 80,
            "prestige": 140,
            "piety": 90,
            "traits": ["Craven", "Content"]
        },
        "char_halfden": {
            "id": "char_halfden",
            "name": "Halfdan Ragnarsson",
            "title": "Jarl of Jorvik & Northumbria",
            "dynasty": "Ragnarsson",
            "realm": "danelaw",
            "portrait": "portrait_halfden.png",
            "coa": "coa_danelaw.png",
            "age": 35,
            "alive": True,
            "stats": {"diplomacy": 8, "martial": 19, "stewardship": 10, "intrigue": 14, "learning": 6},
            "gold": 210,
            "prestige": 400,
            "piety": 50,
            "traits": ["Viking", "Fierce", "Ambitious"]
        },
        "char_rhodri": {
            "id": "char_rhodri",
            "name": "Rhodri the Great",
            "title": "King of Gwynedd & Powys",
            "dynasty": "Aberffraw",
            "realm": "wales",
            "portrait": "portrait_rhodri.png",
            "coa": "coa_wales.png",
            "age": 48,
            "alive": True,
            "stats": {"diplomacy": 13, "martial": 15, "stewardship": 12, "intrigue": 10, "learning": 12},
            "gold": 90,
            "prestige": 210,
            "piety": 130,
            "traits": ["Proud", "Diligent"]
        },
        "char_constantine": {
            "id": "char_constantine",
            "name": "Causantín mac Cináeda",
            "title": "King of the Picts & Alba",
            "dynasty": "Alpin",
            "realm": "scotland",
            "portrait": "portrait_constantine.png",
            "coa": "coa_scotland.png",
            "age": 31,
            "alive": True,
            "stats": {"diplomacy": 10, "martial": 14, "stewardship": 11, "intrigue": 12, "learning": 10},
            "gold": 110,
            "prestige": 190,
            "piety": 110,
            "traits": ["Stubborn", "Hunter"]
        }
    }

    provinces = {
        "wessex": {
            "id": "wessex",
            "name": "Wessex",
            "owner": "char_alfred",
            "culture": "Anglo-Saxon",
            "religion": "Catholic",
            "tax": 16,
            "levies_max": 2200,
            "levies_current": 2200,
            "color": [195, 30, 30]
        },
        "kent_essex": {
            "id": "kent_essex",
            "name": "Kent & Essex",
            "owner": "char_alfred",
            "culture": "Anglo-Saxon",
            "religion": "Catholic",
            "tax": 12,
            "levies_max": 1400,
            "levies_current": 1400,
            "color": [215, 60, 60]
        },
        "cornwall": {
            "id": "cornwall",
            "name": "Cornwall",
            "owner": "char_alfred",
            "culture": "Cornish",
            "religion": "Catholic",
            "tax": 7,
            "levies_max": 800,
            "levies_current": 800,
            "color": [175, 50, 70]
        },
        "mercia": {
            "id": "mercia",
            "name": "Mercia",
            "owner": "char_burgred",
            "culture": "Anglo-Saxon",
            "religion": "Catholic",
            "tax": 13,
            "levies_max": 1600,
            "levies_current": 1600,
            "color": [210, 170, 40]
        },
        "east_anglia": {
            "id": "east_anglia",
            "name": "East Anglia",
            "owner": "char_burgred",
            "culture": "Anglo-Saxon",
            "religion": "Catholic",
            "tax": 10,
            "levies_max": 1200,
            "levies_current": 1200,
            "color": [220, 120, 40]
        },
        "jorvik": {
            "id": "jorvik",
            "name": "Jorvik",
            "owner": "char_halfden",
            "culture": "Norse",
            "religion": "Norse Pagan",
            "tax": 15,
            "levies_max": 2000,
            "levies_current": 2000,
            "color": [70, 70, 75]
        },
        "bernicia": {
            "id": "bernicia",
            "name": "Bernicia",
            "owner": "char_halfden",
            "culture": "Anglo-Saxon",
            "religion": "Catholic",
            "tax": 9,
            "levies_max": 1100,
            "levies_current": 1100,
            "color": [160, 45, 45]
        },
        "gwynedd": {
            "id": "gwynedd",
            "name": "Gwynedd",
            "owner": "char_rhodri",
            "culture": "Welsh",
            "religion": "Catholic",
            "tax": 8,
            "levies_max": 900,
            "levies_current": 900,
            "color": [35, 140, 65]
        },
        "powys": {
            "id": "powys",
            "name": "Powys",
            "owner": "char_rhodri",
            "culture": "Welsh",
            "religion": "Catholic",
            "tax": 7,
            "levies_max": 800,
            "levies_current": 800,
            "color": [50, 160, 80]
        },
        "deheubarth": {
            "id": "deheubarth",
            "name": "Deheubarth",
            "owner": "char_rhodri",
            "culture": "Welsh",
            "religion": "Catholic",
            "tax": 7,
            "levies_max": 850,
            "levies_current": 850,
            "color": [65, 175, 95]
        },
        "alba": {
            "id": "alba",
            "name": "Alba",
            "owner": "char_constantine",
            "culture": "Goidelic",
            "religion": "Catholic",
            "tax": 11,
            "levies_max": 1300,
            "levies_current": 1300,
            "color": [25, 65, 145]
        },
        "highlands": {
            "id": "highlands",
            "name": "Highlands",
            "owner": "char_constantine",
            "culture": "Pictish",
            "religion": "Catholic",
            "tax": 5,
            "levies_max": 700,
            "levies_current": 700,
            "color": [40, 80, 160]
        },
        "lothian": {
            "id": "lothian",
            "name": "Lothian",
            "owner": "char_constantine",
            "culture": "Goidelic",
            "religion": "Catholic",
            "tax": 8,
            "levies_max": 950,
            "levies_current": 950,
            "color": [60, 100, 175]
        },
        "strathclyde": {
            "id": "strathclyde",
            "name": "Strathclyde",
            "owner": "char_constantine",
            "culture": "Cumbric",
            "religion": "Catholic",
            "tax": 7,
            "levies_max": 800,
            "levies_current": 800,
            "color": [75, 115, 190]
        }
    }

    with open(os.path.join(DATA_DIR, "characters.json"), "w", encoding="utf-8") as f:
        json.dump(characters, f, indent=2)

    with open(os.path.join(DATA_DIR, "provinces.json"), "w", encoding="utf-8") as f:
        json.dump(provinces, f, indent=2)

if __name__ == "__main__":
    print("Generating UI Icons...")
    make_icon_gold()
    make_icon_prestige()
    make_icon_piety()
    make_icon_troops()
    make_icon_speed()

    print("Generating Heraldry Shields...")
    for key, info in REALM_COLORS.items():
        draw_shield(key, info)

    print("Generating Character Portraits...")
    for p in PORTRAIT_DATA:
        make_portrait(p)

    print("Generating Britain Map Grid & Preview...")
    generate_map_assets()

    print("Generating Database (characters.json, provinces.json)...")
    generate_game_data()

    print("All mock assets and game data generated successfully!")
