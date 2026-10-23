"""Recolour sv-ttk's accent sprites to markerlite's logo blue (#2F4C8F).

sv-ttk draws its accent controls (the primary button, checked boxes,
radio buttons, switches, the progress bar, an entry's focus line) from
sprite images in one spritesheet per theme, so the accent is not a colour
option. This writes a copy of each spritesheet with those sprites
recoloured; the app copies the recoloured sprites over the theme's own
images after loading it (markerlite_gui.App._apply_accent). Copying keeps
each pixel's alpha, which works in Tk 8.6 as well as 9.

Each pixel of an accent sprite is a blend of the accent with white or
with black (anti-aliasing, hover and pressed shades, the glyph inside a
control). It keeps its blend factor and takes the new accent. In the dark
theme the glyph inside an accent control is black on light blue; on the
darker logo blue it becomes white. Pixels that are not such a blend
(greys of the disabled state, the page background) are left alone.

Rerun when the pinned sv-ttk version changes:

    python tools/recolour_sprites.py
"""

from __future__ import annotations

import pathlib
import re

import sv_ttk
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "sv-ttk"
TARGET = (0x2F, 0x4C, 0x8F)
SOURCE = {"light": (0, 95, 184), "dark": (87, 200, 255)}
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
RESIDUAL_MAX = 20.0
RESIDUAL_BLACK_MAX = 6.0
# Sprites drawn in the accent colour (the unselected, off and disabled
# variants are grey and are not listed).
ACCENT_SPRITES = re.compile(
    r"^(button-accent-(?!dis)|check-(?!unsel|dis|tri-dis)|radio-(?!unsel|dis)"
    r"|switch-(?!off|dis)|progressbar-bar|slider-thumb-(?!dis)|textbox-focus)"
)


def sprite_table(theme: str) -> dict[str, tuple[int, int, int, int]]:
    tcl = pathlib.Path(sv_ttk.__file__).with_name("theme") / f"sprites_{theme}.tcl"
    found = re.findall(r"(\S+) (\d+) (\d+) (\d+) (\d+)", tcl.read_text())
    return {name: tuple(map(int, rest)) for name, *rest in found}


def _project(p, a, g):
    """Blend factor t of p on the segment g->a, and the distance from it."""
    d = [a[i] - g[i] for i in range(3)]
    n2 = sum(x * x for x in d) or 1
    t = sum((p[i] - g[i]) * d[i] for i in range(3)) / n2
    t = min(1.0, max(0.0, t))
    q = [g[i] + t * d[i] for i in range(3)]
    return t, sum((p[i] - q[i]) ** 2 for i in range(3)) ** 0.5


def recolour_pixel(p, theme: str):
    a = SOURCE[theme]
    best = min(((g,) + _project(p, a, g) for g in (WHITE, BLACK)), key=lambda r: r[2])
    g, t, residual = best
    # A blend with black must be close: the dark page background (28, 28,
    # 28) lies near the black-to-accent line and is not part of a control.
    if residual > (RESIDUAL_BLACK_MAX if g == BLACK else RESIDUAL_MAX):
        return None
    if theme == "dark" and g == BLACK:
        g = WHITE  # the glyph inside a control: white on the darker blue
    return tuple(round(g[i] + t * (TARGET[i] - g[i])) for i in range(3))


def recolour(theme: str) -> Image.Image:
    sheet = (
        pathlib.Path(sv_ttk.__file__).with_name("theme") / f"spritesheet_{theme}.png"
    )
    im = Image.open(sheet).convert("RGBA")
    px = im.load()
    for name, (x, y, w, h) in sprite_table(theme).items():
        if not ACCENT_SPRITES.match(name):
            continue
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                r, g, b, alpha = px[xx, yy]
                if not alpha:
                    continue
                new = recolour_pixel((r, g, b), theme)
                if new is not None:
                    px[xx, yy] = new + (alpha,)
    return im


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        recolour(theme).save(OUT / f"spritesheet_{theme}.png", optimize=True)
        print(f"wrote {OUT / f'spritesheet_{theme}.png'}")


if __name__ == "__main__":
    main()
