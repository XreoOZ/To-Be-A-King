"""
Asset Loading, Heraldry Generation, and Waving War Banners
"""
import os
import math
import pygame
from game.config import ASSETS_DIR, COLOR_GOLD
from game.data.characters import CHARACTERS, get_color

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

def make_default_portrait(color, size=(80, 80)):
    """Generated portrait placeholder tinted with the ruler's faction color."""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    surf.fill((34, 30, 28))
    pygame.draw.circle(surf, tuple(color), (w // 2, int(h * 0.38)), int(w * 0.22))
    pygame.draw.ellipse(surf, tuple(color), (int(w * 0.16), int(h * 0.60), int(w * 0.68), int(h * 0.50)))
    pygame.draw.rect(surf, COLOR_GOLD, (0, 0, w, h), 1, border_radius=3)
    return surf

def init_asset_caches():
    """Initializes all image caches after pygame display is set."""
    global prov_flag_cache, portrait_cache, coa_cache
    from game.data.provinces import PROVINCES
    prov_flag_cache.clear()
    portrait_cache.clear()
    coa_cache.clear()
    _cloth_scaled_cache.clear()
    for cid, char in CHARACTERS.items():
        color = get_color(cid)
        pfile = char.get("portrait")
        if pfile and os.path.exists(os.path.join(ASSETS_DIR, "portraits", pfile)):
            portrait_cache[cid] = load_image(os.path.join("portraits", pfile), (80, 80))
        else:
            portrait_cache[cid] = make_default_portrait(color, (80, 80))

        cfile = char.get("coa")
        if cfile and os.path.exists(os.path.join(ASSETS_DIR, "heraldry", cfile)):
            coa_cache[cid] = load_image(os.path.join("heraldry", cfile), (36, 42))
        else:
            coa_cache[cid] = pygame.transform.smoothscale(make_heraldic_shield(color), (36, 42))

    for pid, pdata in PROVINCES.items():
        pcol = tuple(pdata.get("color", (120, 120, 120)))
        prov_flag_cache[pid] = make_heraldic_shield(pcol)

def make_banner_cloth(pid, width, height, is_large=True):
    from game.data.provinces import PROVINCES
    if pid in PROVINCES:
        pdata = PROVINCES.get(pid, {})
        bg = tuple(pdata.get("color", (120, 30, 30)))
        is_vassal = False
    else:
        # Distinctive Vassal Heraldry Palette
        vassal_hues = [
            (35, 75, 140),   # Royal Azure
            (90, 40, 110),   # Imperial Purple
            (40, 95, 55),    # Emerald Forest
            (145, 45, 45),   # Crimson
            (150, 105, 30),  # Amber Gold
            (45, 95, 120),   # Teal
            (125, 70, 40),   # Bronze
            (65, 80, 105),   # Steel Navy
        ]
        h_idx = abs(hash(str(pid))) % len(vassal_hues)
        bg = vassal_hues[h_idx]
        is_vassal = True

    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill(bg)

    emblem = prov_flag_cache.get(pid)
    if emblem:
        ew = int(width * 0.65)
        eh = int(height * 0.78)
        scaled_emblem = pygame.transform.smoothscale(emblem, (ew, eh))
        surf.blit(scaled_emblem, (2, (height - eh) // 2))
    elif is_vassal:
        # Draw feudal charge / bend / cross on vassal banner
        v_idx = abs(hash(str(pid))) % 4
        chg_col = (255, 225, 100) if v_idx % 2 == 0 else (240, 240, 245)
        if v_idx == 0:
            # Pale / Vertical band
            pygame.draw.rect(surf, chg_col, (int(width * 0.35), 0, max(2, int(width * 0.25)), height))
        elif v_idx == 1:
            # Fess / Horizontal band
            pygame.draw.rect(surf, chg_col, (0, int(height * 0.35), width, max(2, int(height * 0.30))))
        elif v_idx == 2:
            # Cross
            pygame.draw.rect(surf, chg_col, (int(width * 0.35), 0, max(2, int(width * 0.22)), height))
            pygame.draw.rect(surf, chg_col, (0, int(height * 0.38), width, max(2, int(height * 0.25))))
        else:
            # Saltire / Chevron
            pygame.draw.line(surf, chg_col, (0, 0), (width, height), 2)
            pygame.draw.line(surf, chg_col, (0, height), (width, 0), 2)

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
