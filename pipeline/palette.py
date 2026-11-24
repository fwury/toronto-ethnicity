"""Colour palette: each broad category is a hue band, subcategories are spread
across the band (OKLCH) with alternating lightness so neighbours separate.

Tuned for a light, print-style basemap but legible on dark ones too.
"""
import math

from origin_groups import BROAD_ORDER, GROUPS

# broad: (hue_from, hue_to, chroma, light_lo, light_hi)
BANDS = {
    "Indigenous North American": (28, 48, 0.11, 0.42, 0.58),
    "Non-Indigenous North American": (100, 122, 0.08, 0.44, 0.62),
    "European": (230, 276, 0.15, 0.44, 0.68),
    "Middle Eastern and North African": (76, 98, 0.14, 0.56, 0.74),
    "African and Black Diaspora": (132, 165, 0.15, 0.44, 0.66),
    "Caribbean": (176, 198, 0.12, 0.50, 0.68),
    "Latin American": (306, 330, 0.15, 0.44, 0.66),
    "East Asian": (12, 26, 0.19, 0.48, 0.66),
    "Southeast Asian": (342, 360, 0.18, 0.50, 0.70),
    "South Asian": (48, 70, 0.17, 0.58, 0.76),
    "Oceanian": (60, 70, 0.03, 0.36, 0.52),
    "Jewish and Israeli": (290, 290, 0.17, 0.52, 0.52),
    "Other": (0, 0, 0.0, 0.58, 0.58),
}


def oklch_to_srgb(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    return rgb


def in_gamut(rgb):
    return all(-1e-4 <= c <= 1 + 1e-4 for c in rgb)


def to_hex(L, C, h):
    while C > 0 and not in_gamut(oklch_to_srgb(L, C, h)):
        C -= 0.005
    out = []
    for c in oklch_to_srgb(L, max(C, 0), h):
        c = min(max(c, 0), 1)
        c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
        out.append(round(c * 255))
    return "#%02x%02x%02x" % tuple(out)


def palette():
    """Returns {broad: hex}, {(broad, sub): hex}."""
    broad_col, sub_col = {}, {}
    for broad in BROAD_ORDER:
        h0, h1, C, lo, hi = BANDS[broad]
        subs = [s for b, s in GROUPS if b == broad]
        n = len(subs)
        broad_col[broad] = to_hex((lo + hi) / 2, C, (h0 + h1) / 2)
        for i, sub in enumerate(subs):
            t = i / (n - 1) if n > 1 else 0.5
            h = h0 + (h1 - h0) * t
            # alternate light/dark, with a gentle ramp so long bands don't repeat
            L = (hi if i % 2 else lo) + (0.04 * (t - 0.5) if n > 4 else 0)
            sub_col[(broad, sub)] = to_hex(L, C, h)
    return broad_col, sub_col


if __name__ == "__main__":
    bc, sc = palette()
    for (b, s), c in sc.items():
        print(f"{c}  {b:34} {s}")
