#!/usr/bin/env python3
"""The built skin as it looks in use, one image per theme, with a preset loaded: the curve the engine reports drawn
from the column filmstrip, the band switches lit, and MPC's live text filled in at its size.

    python3 tools/preview_demo.py <mpc-vst-plugins checkout> <run_engine harness> out_dir [preset name]

Offline approximation: MPC draws its own text (Titillium Web) and knob positions; this stands in for them.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

MV, HARNESS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
PRESET = sys.argv[4] if len(sys.argv) > 4 else "Vocal Clarity"
sys.path.insert(0, os.path.join(MV, "tools"))
from PIL import Image, ImageDraw, ImageFont   # noqa: E402
import studio                                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_skin_art as A                       # noqa: E402

VST = A.VST                                     # SHAPEY_BANDS=5: the 5-band version (vst5/)
SKIN = os.path.join(VST, "build", "skin", "3DTHC - VST - %s" % json.load(open(os.path.join(VST, "vst.json")))["name"], "Plugin Skins")
FONT = os.path.join(MV, "tools", "html_art", "fonts")
EM = 1 / 1.53   # MPC font heights are ascent + descent; Titillium's letters are about 1/1.53 of that
f = lambda size, w="SemiBold": ImageFont.truetype(os.path.join(FONT, "TitilliumWeb-%s.ttf" % w), size)
ImageFont.load_default = lambda size=10: f(max(1, round(size * EM)))
orig_rect = ImageDraw.ImageDraw.rectangle
ImageDraw.ImageDraw.rectangle = lambda self, xy, *a, **k: None if k.get("outline") == (70, 110, 160) else orig_rect(self, xy, *a, **k)

preset = next(p for p in json.load(open(os.path.join(VST, "presets.json")))["presets"] if p["name"] == PRESET)
vals = preset["values"]
with tempfile.TemporaryDirectory() as tmp:
    import numpy as np
    music = os.path.join(tmp, "in.f32")                              # stand-in audio for the analyzer: pink-ish noise
    w = np.random.default_rng(3).normal(0, 1, 2 * 44100)
    pink = np.real(np.fft.irfft(np.fft.rfft(w) / np.sqrt(np.maximum(np.arange(len(w) // 2 + 1), 1))))
    (0.25 * pink / np.max(np.abs(pink))).astype(np.float32).tofile(music)
    out = subprocess.run([HARNESS, music, os.path.join(tmp, "o.s16"), "analyzer=1"] + ["%s=%s" % kv for kv in vals.items()],
                         check=True, capture_output=True, text=True).stdout.split("\n")
    cols = [int(v) for v in out[1].split()]
    bars = [int(v) for v in out[2].split()]
    import shutil
    skin = os.path.join(tmp, "skin")
    shutil.copytree(SKIN, skin)
    import numpy as np
    # studio draws every when= part at its parameter's first option: blank the live ones (the curve, Low Cut shown as
    # selected) -- they are drawn below from the engine's values instead
    first_sel = [np.asarray(Image.open(os.path.join(VST, "images", n)).convert("RGBA")) for n in ("ring_1.png", "pill_1_sel.png")]
    for m in os.listdir(skin):
        path = os.path.join(skin, m)
        if m.startswith("sh_meter_") or m.startswith("sh_slider_h"):
            Image.new("RGBA", Image.open(path).size).save(path)
        elif m.startswith("sh_btn_") and m.endswith(".png"):
            a = np.asarray(Image.open(path).convert("RGBA"))
            if any(a.shape == b.shape and np.abs(a.astype(int) - b).max() < 8 for b in first_sel):
                Image.new("RGBA", Image.open(path).size).save(path)
    names = [p["key"] for p in json.load(open(os.path.join(VST, "params.json")))["params"]]
    tag = "_mode%d-" % names.index("theme")
    # studio draws a page for every option of every when= parameter (hundreds here: dots, marker, touch): only the
    # base page and the theme pages are needed, so its page list is filtered before drawing
    import inspect, re as _re
    src = inspect.getsource(studio.preview).replace(
        "    for out, tab, state, note in pages:",
        "    pages = [pg for pg in pages if '_mode' not in pg[0] or %r in pg[0]]\n    pages = [pg for pg in pages if '_open' not in pg[0]]\n"
        "    for out, tab, state, note in pages:" % tag, 1)
    assert "_open' not in" in src
    exec(compile(src, studio.__file__, "exec"), studio.__dict__)
    pages = [p for p, _ in studio.preview(skin, os.path.join(tmp, "p_%d.png")) if "_open" not in p]
    pages = [pages[0]] + sorted(p for p in pages[1:] if tag in p)
    strip = Image.open(os.path.join(VST, "images", "curve_col.png")).convert("RGBA")
    os.makedirs(OUT, exist_ok=True)
    for (slug, name, t), page in zip(A.THEMES, pages):
        im = Image.open(page).convert("RGBA")
        d = ImageDraw.Draw(im)

        def text(cx, cy, s, size, colour, weight="SemiBold", anchor="mm"):
            d.text((cx, cy), s, font=f(size, weight), fill="#" + colour.lstrip("#"), anchor=anchor)

        sel = len(A.BANDS) // 2 - 1 if A.NB == 8 else 2             # a middle bell selected: its column glows, its marker shows
        selx = A.band_x(sel) + A.COL_PITCH // 2
        ring = Image.open(os.path.join(VST, "images", "ring_%d.png" % (sel + 1))).convert("RGBA")
        im.alpha_composite(ring, (A.band_x(sel) + 1, A.COLS_Y - 2))
        lane_w = A.NCOL * A.COL_W
        for i in range(len(A.BANDS)):                               # the numbered dots, then the handles' rings
            if vals.get("b%d_on" % (i + 1)):
                k = int(A.NDOT * min(vals["b%d_freq" % (i + 1)], 999.9) / 1000)
                dot = Image.open(os.path.join(VST, "images", "dot_%d.png" % (i + 1))).convert("RGBA")
                im.alpha_composite(dot, (A.PLOT_X + k * (lane_w // A.NDOT) + lane_w // A.NDOT // 2 - A.DOT // 2, A.lane_cy(i) - A.DOT // 2))
        lane = Image.open(os.path.join(VST, "images", "lane.png")).convert("RGBA")
        for i in (range(len(A.BANDS)) if A.NLANES > 1 else [sel]):
            fr = round(vals["b%d_freq" % (i + 1)] / 1000 * (A.LANE_FRAMES - 1))
            im.alpha_composite(lane.crop((0, fr * A.LANE_H, lane_w, (fr + 1) * A.LANE_H)), (A.PLOT_X, A.lane_cy(i) - A.LANE_H // 2))
        bar = Image.open(os.path.join(VST, "images", "bar.png")).convert("RGBA")
        bw = A.NCOL * A.COL_W // A.NBAR
        for k, v in enumerate(bars):
            im.alpha_composite(bar.crop((0, v * A.PLOT_H, bw, (v + 1) * A.PLOT_H)), (A.PLOT_X + k * bw, A.PLOT_Y))
        ax, ay, aw, ah = A.ANALYZER
        im.alpha_composite(Image.open(os.path.join(VST, "images", "analyzer_on.png")).convert("RGBA"), (ax - aw // 2, ay - ah // 2))
        mcol = int(72 * vals["b%d_freq" % (sel + 1)] / 1000)
        im.alpha_composite(Image.open(os.path.join(VST, "images", "marker.png")).convert("RGBA"), (A.PLOT_X + mcol * A.COL_W, A.PLOT_Y))
        for c, v in enumerate(cols):
            fr = strip.crop((0, v * A.PLOT_H, A.COL_W, (v + 1) * A.PLOT_H))
            im.alpha_composite(fr, (A.PLOT_X + c * A.COL_W, A.PLOT_Y))
        for i, (bname, kind, col) in enumerate(A.BANDS):
            x0 = A.band_x(i) + (A.COL_PITCH - A.BAND_BTN[0]) // 2
            if vals.get("b%d_on" % (i + 1)):
                im.alpha_composite(Image.open(os.path.join(VST, "images", "power_%d_on.png" % (i + 1))).convert("RGBA"), (x0, A.COLS_Y + A.COL_PAD))
            if i == sel:
                im.alpha_composite(Image.open(os.path.join(VST, "images", "pill_%d_sel.png" % (i + 1))).convert("RGBA"),
                                   (x0 + A.BAND_BTN[0] - A.PILL_W, A.COLS_Y + A.COL_PAD))
            hz = 20 * 1000 ** (vals["b%d_freq" % (i + 1)] / 1000)
            q = 0.1 * 100 ** (vals["b%d_q" % (i + 1)] / 100)
            cx = A.band_x(i) + A.COL_PITCH // 2
            top = A.COLS_Y + A.COL_PAD + A.BAND_BTN[1] + 4
            ftxt = "%.1f kHz" % (hz / 1000) if hz >= 10000 else "%.2f kHz" % (hz / 1000) if hz >= 1000 else "%d Hz" % round(hz)
            if A.KNOB_ROW:
                cx, row2 = cx + 78, top
                text(cx - 156, row2 + A.knob_box(A.SMALL_R, A.SMALL_NS, A.SMALL_VS) - round(A.SMALL_VS * 1.2) // 2 - 4, ftxt, round(A.SMALL_VS * EM), t["knob_value"])
            else:
                text(cx, top + A.knob_box(A.FREQ_R, A.FREQ_NS, A.FREQ_VS) - round(A.FREQ_VS * 1.2) // 2 - 4, ftxt, round(A.FREQ_VS * EM), t["knob_value"])
                row2 = top + A.knob_box(A.FREQ_R, A.FREQ_NS, A.FREQ_VS) + 2
            ty = A.TYPES[vals["b%d_type" % (i + 1)]]
            x = vals["b%d_x" % (i + 1)]
            second = (["6 dB", "12 dB", "24 dB", "48 dB"][min(3, x // 120)] if "Cut" in ty else
                      "-" if ty in ("Notch", "Band Pass") else "%+.1f dB" % ((x - 240) / 10))
            text(x0 + A.BAND_BTN[0] - A.PILL_W // 2, A.COLS_Y + A.COL_PAD + A.BAND_BTN[1] // 2, ty, round(A.TYPE_TEXT * EM), "eef1f4")
            for s, dx in (((second, -78), ("%.2f" % q, 0)) if A.KNOB_ROW else ((second, -38), ("%.2f" % q, 38))):
                text(cx + dx, row2 + A.knob_box(A.SMALL_R, A.SMALL_NS, A.SMALL_VS) - round(A.SMALL_VS * 1.2) // 2 - 4, s, round(A.SMALL_VS * EM), t["knob_value"])
        x, w = A.THEME_SEL
        text(x + w // 2, A.SEL_Y + A.SEL_H // 2, name, round(A.FIELD_TEXT * EM), "eef1f4")
        mx, my = A.MASTER
        text(mx + 30, my, "%+.1f dB" % vals.get("master", 0), round((34 if A.NB == 8 else 30) * EM), t["ink"])
        path = os.path.join(OUT, "shapey_%s.png" % slug)
        im.convert("RGB").save(path)
        print(path)
