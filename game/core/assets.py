"""
Asset Loading, Heraldry Generation, and Waving War Banners
"""
import os
import math
import pygame
from game.config import ASSETS_DIR, COLOR_GOLD
from game.data.characters import CHARACTERS

def load_image(subpath, size=None):
    full_path = os.path.join(ASSETS_DIR, subpath)
    if os.path.exists(full_path):
        img = pygame.image.load(full_path)
        if pygame.display.get_surface() is not None:
            img = img.convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    surf = pygame.Surface(size or (32, 32), pygame.SRCALPHA)
    surf.fill((120, 120, 120, 180))
    return surf

def make_heraldic_shield(bg_color, is_cornwall=False, is_kent=False):
    s = pygame.Surface((24, 28), pygame.SRCALPHA)
    s.fill(bg_color)
    if is_cornwall:
        pygame.draw.line(s, (255, 255, 255), (0, 14), (24, 14), 4)
        pygame.draw.line(s, (255, 255, 255), (8, 0), (8, 28), 4)
    elif is_kent:
        pygame.draw.line(s, (255, 255, 255), (0, 14), (24, 14), 3)
        pygame.draw.line(s, (255, 255, 255), (8, 0), (8, 28), 3)
        pygame.draw.polygon(s, (255, 255, 255), [(13, 6), (19, 10), (13, 14)])
    pygame.draw.rect(s, COLOR_GOLD, (0, 0, 24, 28), 1, border_radius=3)
    return s

# Cache dictionaries
prov_flag_cache = {}
portrait_cache = {}
coa_cache = {}

def init_asset_caches():
    """Initializes all image caches after pygame display is set."""
    global prov_flag_cache, portrait_cache, coa_cache
    for cid, char in CHARACTERS.items():
        pfile = char.get("portrait", "portrait_default.png")
        portrait_cache[cid] = load_image(os.path.join("portraits", pfile), (80, 80))
        cfile = char.get("coa", "coa_wessex.png")
        coa_cache[cid] = load_image(os.path.join("heraldry", cfile), (36, 42))

    prov_flag_cache.update({
        "wessex": load_image(os.path.join("heraldry", "coa_wessex.png"), (24, 28)),
        "mercia": load_image(os.path.join("heraldry", "coa_mercia.png"), (24, 28)),
        "east_anglia": load_image(os.path.join("heraldry", "coa_east_anglia.png"), (24, 28)),
        "kent_essex": make_heraldic_shield((175, 25, 45), is_kent=True),
        "cornwall": make_heraldic_shield((24, 24, 28), is_cornwall=True),
        "wales": load_image(os.path.join("heraldry", "coa_wales.png"), (24, 28)),
        "jorvik": load_image(os.path.join("heraldry", "coa_danelaw.png"), (24, 28)),
        "deira": load_image(os.path.join("heraldry", "coa_northumbria.png"), (24, 28)),
        "bernicia": load_image(os.path.join("heraldry", "coa_northumbria.png"), (24, 28)),
        "strathclyde": load_image(os.path.join("heraldry", "coa_scotland.png"), (24, 28)),
        "lothian": load_image(os.path.join("heraldry", "coa_scotland.png"), (24, 28)),
        "highlands": load_image(os.path.join("heraldry", "coa_scotland.png"), (24, 28)),
    })

def make_banner_cloth(pid, width, height, is_large=True):
    bg_palette = {
        "wessex": (190, 30, 30),
        "mercia": (22, 50, 130),
        "east_anglia": (30, 80, 160),
        "kent_essex": (170, 25, 45),
        "cornwall": (24, 24, 28),
        "wales": (28, 110, 50),
        "jorvik": (35, 40, 50),
        "deira": (135, 38, 42),
        "bernicia": (30, 42, 85),
        "strathclyde": (20, 55, 135),
        "lothian": (20, 55, 135),
        "highlands": (20, 55, 135),
    }
    bg = bg_palette.get(pid, (120, 30, 30))
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill(bg)

    emblem = prov_flag_cache.get(pid)
    if emblem:
        ew = int(width * 0.65)
        eh = int(height * 0.78)
        scaled_emblem = pygame.transform.smoothscale(emblem, (ew, eh))
        surf.blit(scaled_emblem, (2, (height - eh) // 2))

    pygame.draw.line(surf, COLOR_GOLD, (0, 0), (width, 0), 1)
    pygame.draw.line(surf, COLOR_GOLD, (0, height - 1), (width, height - 1), 1)

    if is_large and width >= 26:
        cut_w = 6
        pts = [(width - cut_w, height // 2), (width + 1, 0), (width + 1, height)]
        cut_mask = pygame.Surface((width, height), pygame.SRCALPHA)
        cut_mask.fill((255, 255, 255, 255))
        pygame.draw.polygon(cut_mask, (0, 0, 0, 0), pts)
        surf.blit(cut_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.line(surf, COLOR_GOLD, (width - 1, 0), (width - cut_w, height // 2), 1)
        pygame.draw.line(surf, COLOR_GOLD, (width - cut_w, height // 2), (width - 1, height - 1), 1)
    else:
        pygame.draw.line(surf, COLOR_GOLD, (width - 1, 0), (width - 1, height - 1), 1)

    return surf

_cloth_scaled_cache = {}

def get_scaled_banner_cloth(pid, width, height, is_large=True):
    width = max(8, width)
    height = max(6, height)
    key = (pid, width, height, is_large)
    if key in _cloth_scaled_cache:
        return _cloth_scaled_cache[key]
    cloth = make_banner_cloth(pid, width, height, is_large=is_large)
    _cloth_scaled_cache[key] = cloth
    return cloth

def draw_waving_banner(surface, cloth_surf, pole_x, pole_y, pole_h, ticks, amp=3.0, freq=0.25, is_main=False):
    top_y = pole_y - pole_h
    pygame.draw.line(surface, (45, 30, 20), (pole_x, top_y), (pole_x, pole_y), 2 if is_main else 1)
    pygame.draw.line(surface, (95, 70, 48), (pole_x - 1, top_y), (pole_x - 1, pole_y), 1)

    finial_h = max(3, int(pole_h * 0.18)) if is_main else max(2, int(pole_h * 0.14))
    finial_w = max(2, int(pole_h * 0.10)) if is_main else max(1, int(pole_h * 0.08))
    pygame.draw.polygon(surface, COLOR_GOLD, [
        (pole_x, top_y - finial_h),
        (pole_x - finial_w, top_y),
        (pole_x + finial_w, top_y)
    ])
    if is_main:
        pygame.draw.line(surface, (255, 235, 120), (pole_x - finial_w, top_y), (pole_x + finial_w, top_y), 1)

    cw, ch = cloth_surf.get_size()
    strip_w = 2
    cloth_top = top_y + max(2, int(pole_h * 0.10))
    time_val = ticks * 0.0055

    for sx in range(0, cw, strip_w):
        cur_w = min(strip_w, cw - sx)
        progress = sx / max(1, cw - 1)
        cur_amp = amp * progress
        wave_y = int(math.sin(time_val + sx * freq) * cur_amp)
        
        draw_x = pole_x + 1 + sx
        draw_y = cloth_top + wave_y
        surface.blit(cloth_surf, (draw_x, draw_y), (sx, 0, cur_w, ch))

        shade = int(math.cos(time_val + sx * freq) * (18 if is_main else 12))
        if shade != 0:
            s_surf = pygame.Surface((cur_w, ch), pygame.SRCALPHA)
            if shade > 0:
                s_surf.fill((255, 255, 255, min(45, shade * 2)))
            else:
                s_surf.fill((0, 0, 0, min(65, -shade * 2)))
            surface.blit(s_surf, (draw_x, draw_y))

SUB_FLAG_OFFSETS = [
    (-22,  3),   # 0: left flank forward
    (+24,  3),   # 1: right flank forward
    (-36, -5),   # 2: left flank rear
    (+38, -5),   # 3: right flank rear
    (-50,  2),   # 4: far-left flank
    (+52,  2),   # 5: far-right flank
    (-14, -12),  # 6: center-left rear
    (+14, -12),  # 7: center-right rear
    (-64, -3),   # 8: extra far left
    (+66, -3),   # 9: extra far right
    (-28, -14),  # 10: far rear left
    (+28, -14),  # 11: far rear right
]
