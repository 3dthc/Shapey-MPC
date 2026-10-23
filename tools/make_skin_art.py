#!/usr/bin/env python3
"""Draws Shapey EQ's skin in its four themes and writes the layout that places the live controls on top.

    python3 tools/make_skin_art.py          # needs: pip install playwright && playwright install chromium

Writes vst/artwork/bg_<theme>.svg, vst/images/*.png (knob filmstrips, band switches, the curve column filmstrip,
arrows, bypass) and vst/layout.conf. All of it is committed, so a normal build does not run this.
Coordinates are the skin's (1280 x 628); layout.conf's are the same plus 86 on y.
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VST = os.path.join(HERE, "..", "vst")
# Titillium Web from the toolchain checkout next to this repo (as in ~/mpc-vst-plugins)
FONT = os.environ.get("SHAPEY_FONTS") or os.path.join(HERE, "..", "..", "mpc-vst-plugins", "tools", "html_art", "fonts")
Y = 86   # layout y = skin y + 86
# ---------------------------------------------------------------- themes
# f0/f1: gradient stops. nat/sharp: (face0, face1, stroke, ink) for a lit and an unlit key. led_*: the lit key's bar.
BASE = dict(amber=("#f2a33a", "#ffc76e", "#1d1407"))
THEMES = [
    ("grey", "Grey", dict(
        bg=("#2c2f34", "#1b1d21"), hdr=("#383c42", "#272a2f"), panel=("#373b41", "#25282c"), line="#4b5159",
        ink="#eef1f4", dim="#9aa3ad", sub="#9d5cff", hint="#7a838d", accent="#9d5cff", accent_hi="#c9a3ff",
        field="#191b1f", field_line="#4b5159", arrow="#9d5cff",
        bezel=("#3a3e44", "#1c1e22"), disc=("#55309a", "#2d1a57", "#150c2b"), ring="#9d5cff", glow=.55,
        tick="#4b5159", tick_major="#727b85", tick_zero="#c9a3ff", tick_label="#9aa3ad",
        note="f7f2ff", cents="c9a3ff", knob_name="eef1f4", knob_value="c9a3ff",
        kface=("#40454c", "#1d2024"), ktrack="#4b5159", karc="#9d5cff", kpointer="#c9a3ff",
        nat_on=("#f6f8fa", "#c8ced5", "#8d959e", "#1b1e22"), nat_off=("#4a4f57", "#3b3f46", "#41464d", "#7f8791"),
        sharp_on=("#2d3137", "#16181b", "#565c64", "#eef1f4"), sharp_off=("#202327", "#17191c", "#2f3338", "#5b626a"),
        led_nat="#9d5cff", led_sharp="#9d5cff", byp_off=("#191b1f", "#4b5159", "#aab3bd"), byp_on=BASE["amber"])),
    ("classic", "Classic", dict(                                                   # MPC-style: grey, black, white and red
        bg=("#4a4d52", "#33363a"), hdr=("#55595e", "#3e4146"), panel=("#1c1d1f", "#101113"), line="#5c6066",
        ink="#ffffff", dim="#b4b8bd", sub="#e3242b", hint="#8e9399", accent="#e3242b", accent_hi="#ff4d52",
        field="#0e0f10", field_line="#26282b", arrow="#e3242b",
        bezel=("#5a5e63", "#2a2c2f"), disc=("#26282b", "#141516", "#09090a"), ring="#e3242b", glow=.45,
        tick="#55595e", tick_major="#c9cdd2", tick_zero="#ff4d52", tick_label="#c9cdd2",
        note="ffffff", cents="ff6a6e", knob_name="ffffff", knob_value="ff6a6e",
        kface=("#2c2e31", "#0b0c0d"), ktrack="#3a3d41", karc="#e3242b", kpointer="#ffffff",
        nat_on=("#ffffff", "#dfe2e5", "#9ba0a6", "#111214"), nat_off=("#55595e", "#45484d", "#4c5055", "#8e9399"),
        sharp_on=("#2a2c2f", "#0b0c0d", "#4a4d52", "#ffffff"), sharp_off=("#1a1b1d", "#111213", "#2a2c2f", "#5f6368"),
        led_nat="#e3242b", led_sharp="#ff4d52", byp_off=("#0e0f10", "#26282b", "#c9cdd2"), byp_on=("#e3242b", "#ff6a6e", "#ffffff"))),
    ("white", "White", dict(                                                       # white, grey and black with orange
        bg=("#eef0f3", "#dde1e5"), hdr=("#fbfcfd", "#e7eaee"), panel=("#f8f9fb", "#e2e6ea"), line="#b9c0c8",
        ink="#121417", dim="#5f6873", sub="#f26b1d", hint="#7f8893", accent="#f26b1d", accent_hi="#ff8a3d",
        field="#15171a", field_line="#15171a", arrow="#ff8a3d",
        bezel=("#d5dae0", "#aab2bb"), disc=("#2b2f34", "#17191c", "#0b0c0e"), ring="#f26b1d", glow=.35,
        tick="#a1a9b2", tick_major="#4a525b", tick_zero="#f26b1d", tick_label="#4a525b",
        note="ffffff", cents="ff8a3d", knob_name="121417", knob_value="d9560f",
        kface=("#2e3237", "#0f1113"), ktrack="#c3c9d0", karc="#f26b1d", kpointer="#ffffff",
        nat_on=("#ffffff", "#e9ecef", "#9aa2ab", "#121417"), nat_off=("#cdd2d8", "#b9bfc6", "#a8afb7", "#7d858f"),
        sharp_on=("#2e3237", "#0f1113", "#0f1113", "#ffffff"), sharp_off=("#90979f", "#7d848c", "#757c84", "#50575f"),
        led_nat="#f26b1d", led_sharp="#ff8a3d", byp_off=("#ffffff", "#b9c0c8", "#121417"), byp_on=("#f26b1d", "#ff8a3d", "#ffffff"))),
    ("silver", "Silver", dict(
        bg=("#cdd2d8", "#9ea6ae"), hdr=("#e3e7eb", "#bcc2c9"), panel=("#dde1e6", "#b5bcc4"), line="#8b939c",
        ink="#14181d", dim="#48505a", sub="#0a6fb0", hint="#5c646e", accent="#0a6fb0", accent_hi="#0a6fb0",
        field="#1b1f24", field_line="#5f6770", arrow="#6fd8ff",
        bezel=("#e4e8ec", "#8e969f"), disc=("#2b5d85", "#173650", "#0c1b29"), ring="#0a6fb0", glow=.35,
        tick="#7a828b", tick_major="#2f363e", tick_zero="#0a6fb0", tick_label="#3a424b",
        note="f2f8ff", cents="9fdcff", knob_name="14181d", knob_value="0a4f80",
        kface=("#3a3e44", "#14171a"), ktrack="#9aa2ab", karc="#0a6fb0", kpointer="#ffffff",
        nat_on=("#ffffff", "#e3e7eb", "#8b939c", "#14181d"), nat_off=("#aeb5bd", "#99a0a8", "#8b939c", "#5f6873"),
        sharp_on=("#2e3237", "#101215", "#101215", "#e9ecef"), sharp_off=("#6f767e", "#5e646b", "#565c63", "#3c4249"),
        led_nat="#0a6fb0", led_sharp="#3fb0ff", byp_off=("#1b1f24", "#5f6770", "#cfd6dd"), byp_on=BASE["amber"])),
]


def _font_css():
    """Titillium Web as embedded @font-face rules: the SVG is drawn as a separate image, which can't load fonts from
    files, so the background and the pictures carry the font themselves."""
    import base64
    rules = []
    for w, f in ((400, "TitilliumWeb-Regular.ttf"), (600, "TitilliumWeb-SemiBold.ttf"), (700, "TitilliumWeb-Bold.ttf")):
        p = os.path.join(FONT, f)
        if not os.path.exists(p):
            raise SystemExit("make_skin_art: %s not found (set TUNEY_FONTS to the Titillium Web folder)" % p)
        rules.append('@font-face{font-family:"Titillium Web";font-weight:%d;src:url(data:font/ttf;base64,%s)}'
                     % (w, base64.b64encode(open(p, "rb").read()).decode()))
    return "".join(rules)


FONT_CSS = _font_css()
TF = "font-family:'Titillium Web',sans-serif"


def grad(id_, stops, vertical=True):
    return '<linearGradient id="%s" x2="%d" y2="%d">%s</linearGradient>' % (
        id_, 0 if vertical else 1, 1 if vertical else 0,
        "".join('<stop offset="%g" stop-color="%s"/>' % (i / max(1, len(stops) - 1), c) for i, c in enumerate(stops)))


# ---------------------------------------------------------------- finish (shared by every theme)
# grain: fine noise over the plate; brushed: horizontal brushed-metal streaks; gloss: strength of the top sheen
FINISH = {"grey": dict(grain=.07, brushed=0, gloss=.09), "classic": dict(grain=.08, brushed=0, gloss=.09),
          "white": dict(grain=.035, brushed=0, gloss=.45), "silver": dict(grain=.02, brushed=.20, gloss=.35)}
def common_defs():
    return ('<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" '
            'numOctaves="2" seed="7"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .9 -.35"/></filter>'
            '<filter id="brushed" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".004 .9" '
            'numOctaves="3" seed="3"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1.4 -.55"/></filter>'
            '<filter id="drop" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="4" stdDeviation="6" flood-opacity=".45"/></filter>'
            '<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3.5"/></filter>'
            '<filter id="blur8" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter>'
            '<linearGradient id="bevel" x2="0" y2="1"><stop stop-color="#fff" stop-opacity=".22"/><stop offset=".12" stop-color="#fff" stop-opacity="0"/>'
            '<stop offset=".88" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".35"/></linearGradient>'
            '<linearGradient id="chrome" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff" stop-opacity=".55"/>'
            '<stop offset=".45" stop-color="#fff" stop-opacity=".05"/><stop offset=".55" stop-color="#000" stop-opacity=".1"/>'
            '<stop offset="1" stop-color="#000" stop-opacity=".5"/></linearGradient>'
            '<linearGradient id="inset" x2="0" y2="1"><stop stop-color="#000" stop-opacity=".55"/><stop offset=".35" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#fff" stop-opacity=".06"/></linearGradient>'
            '<radialGradient id="vignette" cx=".5" cy=".45" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#000" stop-opacity=".35"/></radialGradient>'
            '<linearGradient id="glass" x2="0" y2="1"><stop stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')


def gloss_grad(g):
    return ('<linearGradient id="gloss" x2="0" y2="1"><stop stop-color="#fff" stop-opacity="%g"/>'
            '<stop offset=".45" stop-color="#fff" stop-opacity="%g"/><stop offset=".46" stop-color="#fff" stop-opacity="0"/></linearGradient>' % (g, g * .35))


def panel(path, t, fin):
    """A raised panel: soft shadow, fill, top sheen, bevelled edge."""
    return ('<path d="%s" fill="url(#pnl)" filter="url(#drop)"/>'
            '<path d="%s" fill="url(#gloss)" opacity=".6"/>'
            '<path d="%s" fill="none" stroke="url(#bevel)" stroke-width="2"/>'
            '<path d="%s" fill="none" stroke="%s"/>' % (path, path, path, path, t["line"]))


def bypass_svg(slug, t, on):
    _, _, w, h = BYPASS
    fill, stroke, ink = t["byp_on" if on else "byp_off"]
    rr = (h - 4) // 2
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs>%s<filter id="gl" x="-20%%" y="-50%%" width="140%%" height="200%%">'
            '<feGaussianBlur stdDeviation="3"/></filter></defs>'
            '%s<rect x="2" y="2" width="%d" height="%d" rx="%d" fill="%s"/><rect x="2" y="2" width="%d" height="%d" rx="%d" fill="url(#gloss)"/>'
            '<rect x="2.5" y="2.5" width="%d" height="%d" rx="%d" fill="none" stroke="%s" stroke-width="1.5"/>'
            '<text x="%g" y="%g" text-anchor="middle" dominant-baseline="central" style="%s;font-weight:700;font-size:18px;letter-spacing:3px" fill="%s">BYPASS</text></svg>') % (
        w, h, gloss_grad(.35 if on else .12),
        ('<rect x="4" y="4" width="%d" height="%d" rx="%d" fill="%s" filter="url(#gl)" opacity=".8"/>' % (w - 8, h - 8, rr, fill)) if on else "",
        w - 4, h - 4, rr, fill, w - 4, h - 4, rr, w - 5, h - 5, rr, stroke, w / 2, h / 2 + 1, TF, ink)


def arrow_svg(t, side, pressed):
    """A ◀ or ▶ for an arrows selector, on a transparent square (the field is in the background)."""
    w, h = ARROW_W, SEL_H
    cx, cy = w / 2, h / 2
    d = -1 if side == "prev" else 1
    col = t["arrow"]
    back = ('<rect x="3" y="3" width="%d" height="%d" rx="7" fill="#fff" opacity=".10"/>' % (w - 6, h - 6)) if pressed else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">%s<path d="M%g %gL%g %gL%g %gZ" fill="%s"/></svg>' % (
        w, h, back, cx + 8 * d, cy, cx - 7 * d, cy - 11, cx - 7 * d, cy + 11, col))


FRAMES = 128


def knob_strip_svg(slug, t, r):
    """128 knob positions stacked top to bottom, each in a (2r+8)-pixel square (the renderer's knob box): value arc with a
    soft glow, a bevelled rim, a domed face lit from above, and a pointer. The light stays put while the pointer turns."""
    s = 2 * r + 8
    sw = max(2.5, r / 11)
    R = r + 4 - sw / 2 - 1.5
    fr = r - sw - 2.5                                   # rim radius
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (s, s * FRAMES, s, s * FRAMES),
         '<defs><radialGradient id="kf" cx=".42" cy=".3" r=".85"><stop stop-color="%s"/><stop offset="1" stop-color="%s"/></radialGradient>' % t["kface"],
         '<linearGradient id="rim" x2="0" y2="1"><stop stop-color="#fff" stop-opacity=".45"/><stop offset=".5" stop-color="#fff" stop-opacity=".05"/>'
         '<stop offset="1" stop-color="#000" stop-opacity=".5"/></linearGradient>',
         '<radialGradient id="spec" cx=".5" cy=".5" r=".5"><stop stop-color="#fff" stop-opacity=".38"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>',
         '<filter id="sh" x="-30%%" y="-30%%" width="160%%" height="170%%"><feDropShadow dx="0" dy="%g" stdDeviation="%g" flood-opacity=".6"/></filter>' % (max(1.5, r / 20), max(1.5, r / 18)),
         '<filter id="ag" x="-30%%" y="-30%%" width="160%%" height="160%%"><feGaussianBlur stdDeviation="%g"/></filter></defs>' % max(1.2, r / 22)]
    pt = lambda cx, cy, a, rad: (cx + rad * math.sin(math.radians(a)), cy - rad * math.cos(math.radians(a)))
    for k in range(FRAMES):
        cx, cy = s / 2, s / 2 + k * s
        a1 = -135 + 270 * k / (FRAMES - 1)
        sx, sy = pt(cx, cy, -135, R)
        ex, ey = pt(cx, cy, 135, R)
        o.append('<path d="M%.2f %.2fA%g %g 0 1 1 %.2f %.2f" fill="none" stroke="%s" stroke-width="%g" stroke-linecap="round"/>' % (
            sx, sy, R, R, ex, ey, t["ktrack"], sw))
        if k:
            vx, vy = pt(cx, cy, a1, R)
            arc = 'd="M%.2f %.2fA%g %g 0 %d 1 %.2f %.2f" fill="none" stroke="%s" stroke-linecap="round"' % (
                sx, sy, R, R, 1 if a1 + 135 > 180 else 0, vx, vy, t["karc"])
            o.append('<path %s stroke-width="%g" opacity=".55" filter="url(#ag)"/>' % (arc, sw * 1.8))
            o.append('<path %s stroke-width="%g"/>' % (arc, sw))
        o.append('<circle cx="%g" cy="%g" r="%g" fill="url(#kf)" filter="url(#sh)"/>' % (cx, cy, fr))
        o.append('<circle cx="%g" cy="%g" r="%g" fill="none" stroke="url(#rim)" stroke-width="%g"/>' % (cx, cy, fr - max(1, r / 40), max(1.2, r / 28)))
        o.append('<circle cx="%g" cy="%g" r="%g" fill="url(#kf)"/>' % (cx, cy, fr * .78))
        o.append('<ellipse cx="%g" cy="%g" rx="%g" ry="%g" fill="url(#spec)"/>' % (cx - fr * .18, cy - fr * .38, fr * .55, fr * .32))
        p0, p1 = pt(cx, cy, a1, fr * .30), pt(cx, cy, a1, fr * .86)
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="%g" stroke-linecap="round"/>' % (
            p0[0], p0[1], p1[0], p1[1], t["kpointer"], max(2, r / 10)))
    o.append("</svg>")
    return "\n".join(o), s, s * FRAMES


def render_pngs(items):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        for path, svg, w, h in items:
            pg.set_viewport_size({"width": w, "height": min(h, 16384)})
            pg.set_content("<html><head><style>%s html,body{margin:0;background:transparent}</style></head><body>%s</body></html>" % (FONT_CSS, svg))
            pg.wait_for_timeout(50)
            pg.screenshot(path=path, omit_background=True, full_page=True)
        b.close()


# ---------------------------------------------------------------- geometry (skin coordinates)
HDR_H = 80
TITLE_W = 152
SEL_Y, SEL_H = 24, 50
ARROW_W = 64
THEME_SEL = (884, 228)                                   # x, w of the THEME selector
BYPASS = (1196, 49, 136, 50)                             # cx, cy, w, h
MASTER = (640, 49)                                       # the master knob (knob at the left, value at its right)
ANALYZER = (362, 49, 170, 50)                            # the analyzer switch: cx, cy, w, h
NBAR, BAR_STEPS = 72, 24                                 # analyzer: a soft haze behind the curve, 72 columns, 0..24 (-60..0 dBFS)
FIELD_TEXT = 34

GRAPH = (16, 88, 1248, 198)                              # the display panel: x, y, w, h
NCOL, COL_W = 72, 16
PLOT_X, PLOT_Y, PLOT_H = 72, 97, 130                     # the curve area: 72 columns of 16 px from x 72, 130 px tall
LANE_Y, LANE_H = 229, 36                                 # under it, the lane with each band's numbered dot (top, height)
NDOT = 48                                                # places a dot can sit (24 px apart)
DOT = 34                                                 # a dot's size
CURVE_DB, CURVE_STEPS = 18, 60                           # -18 .. +18 dB in 60 steps (frame 30 = 0 dB)
F_LO, F_HI = 20.0, 20000.0

BANDS = [("LOW CUT", "cut", "#ff5a5f"), ("LOW SHELF", "shelf", "#ff9f40"), ("BELL 1", "bell", "#ffd84a"),
         ("BELL 2", "bell", "#5ee08a"), ("BELL 3", "bell", "#4ad6e8"), ("BELL 4", "bell", "#5b8cff"),
         ("HIGH SHELF", "shelf", "#b47cff"), ("HIGH CUT", "cut", "#ff6fc6")]
COLS_X0, COLS_Y, COL_PITCH, COLS_H = 16, 294, 156, 323   # the band columns under the graph
COL_PAD = 6                                              # space above a column's header row
BAND_BTN = (140, 38)                                     # a band's header row: w, h
POWER_W, PILL_W = 38, 100                                # in it: the on/off switch, then the TYPE field (tap: pick the type)
PICK_BOX = (COL_PITCH - 8, COLS_H - COL_PAD - BAND_BTN[1])   # a column's tap-to-select area, under its header
TYPE_TEXT = 22                                           # the TYPE field's text (MPC font height; vst/skin_post.py sets it)
TYPE_CELL = 118                                          # an option's width in the TYPE list (two columns)
TYPES = ["Bell", "Low Shelf", "High Shelf", "Low Cut", "High Cut", "Notch", "Band Pass"]
FREQ_R, SMALL_R = 28, 22
FREQ_NS, FREQ_VS, SMALL_NS, SMALL_VS = 28, 32, 28, 28   # knob name / value text heights (MPC font heights)


def knob_box(r, ns, vs):
    """height of a knob's touch box (picture, name, value) as the skin builder lays it out"""
    return 2 * r + 15 + round(1.2 * (ns + vs))
SCREEN = ("#0b0e13", "#151a22")                          # the graph is a dark display in every theme
CURVE = "#eaf4ff"


def plot_x(hz):
    return PLOT_X + NCOL * COL_W * math.log(hz / F_LO) / math.log(F_HI / F_LO)


def plot_y(db):
    return PLOT_Y + 2.5 + (PLOT_H - 5) * (CURVE_DB - db) / (2 * CURVE_DB)


def band_x(i):
    return COLS_X0 + i * COL_PITCH


# ---------------------------------------------------------------- background
def background(slug, t):
    fin = FINISH[slug]
    gx, gy, gw, gh = GRAPH
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="628" viewBox="0 0 1280 628">', "<defs>",
         grad("bg", t["bg"]), grad("hdr", t["hdr"]), grad("pnl", t["panel"]), grad("scr", SCREEN), gloss_grad(fin["gloss"]),
         common_defs(), "<style>%s</style>" % FONT_CSS, "</defs>",
         '<rect width="1280" height="628" fill="url(#bg)"/>']
    if fin["brushed"]:
        o.append('<rect width="1280" height="628" filter="url(#brushed)" opacity="%g"/>' % fin["brushed"])
    if fin["grain"]:
        o.append('<rect width="1280" height="628" filter="url(#grain)" opacity="%g"/>' % fin["grain"])
    o.append('<rect width="1280" height="628" fill="url(#vignette)"/>')

    # header
    o.append('<rect width="1280" height="%d" fill="url(#hdr)" filter="url(#drop)"/>' % HDR_H)
    o.append('<rect width="1280" height="%d" fill="url(#gloss)" opacity=".7"/>' % (HDR_H * 34 // 80))
    o.append('<path d="M0 .5H1280" stroke="#fff" stroke-opacity=".18"/><path d="M0 %gH1280" stroke="#000" stroke-opacity=".45"/>' % (HDR_H - .5))
    mx, my = MASTER
    if NB == 5:   # one row: title, then the labels beside their controls
        o.append('<text x="24" y="%d" dominant-baseline="central" style="%s;font-weight:700;font-size:30px" fill="%s">SHAPEY</text>' % (HDR_H // 2, TF, t["ink"]))
        o.append('<text x="150" y="%d" dominant-baseline="central" style="%s;font-weight:600;font-size:15px;letter-spacing:2px" fill="%s">%s</text>' % (HDR_H // 2 + 1, TF, t["sub"], TITLE_SUB))
        for label, x in (("MASTER", mx - 96 - 82), ("THEME", THEME_SEL[0] - 62)):
            o.append('<text x="%d" y="%d" dominant-baseline="central" style="%s;font-weight:600;font-size:15px;letter-spacing:2px" fill="%s">%s</text>' % (x, HDR_H // 2 + 1, TF, t["dim"], label))
    else:
        o.append('<text x="30" y="44" textLength="%d" lengthAdjust="spacing" style="%s;font-weight:700;font-size:36px" fill="%s">SHAPEY</text>' % (TITLE_W, TF, t["ink"]))
        o.append('<text x="31" y="66" textLength="%d" lengthAdjust="spacing" style="%s;font-weight:600;font-size:14px" fill="%s">%s</text>' % (TITLE_W - 1, TF, t["sub"], TITLE_SUB))
        # master: the knob and its value, no field
        o.append('<text x="%d" y="%d" style="%s;font-weight:600;font-size:15px;letter-spacing:2px" fill="%s">MASTER</text>' % (mx - 98, SEL_Y - 7, TF, t["dim"]))
        for label, x, w in (("THEME", THEME_SEL[0], THEME_SEL[1]),):
            o.append('<text x="%d" y="%d" style="%s;font-weight:600;font-size:15px;letter-spacing:2px" fill="%s">%s</text>' % (x + 2, SEL_Y - 7, TF, t["dim"], label))
    for x, w in (THEME_SEL,):                           # (the master knob and its value sit on the header itself)
        o.append('<rect x="%g" y="%g" width="%d" height="%d" rx="8" fill="%s"/>' % (x, SEL_Y, w, SEL_H, t["field"]))
        o.append('<rect x="%g" y="%g" width="%d" height="%d" rx="8" fill="url(#inset)"/>' % (x, SEL_Y, w, SEL_H))
        o.append('<rect x="%g" y="%g" width="%d" height="%d" rx="8" fill="none" stroke="%s"/>' % (x + .5, SEL_Y + .5, w - 1, SEL_H - 1, t["field_line"]))
    x, w = THEME_SEL
    for dx in (x + ARROW_W, x + w - ARROW_W):
        o.append('<path d="M%g %gV%g" stroke="#fff" stroke-opacity=".08"/>' % (dx, SEL_Y + 7, SEL_Y + SEL_H - 7))

    # the display: a dark screen in every theme, with a frame from the theme
    o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="12" fill="url(#pnl)" filter="url(#drop)"/>' % (gx, gy, gw, gh))
    o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="12" fill="none" stroke="url(#bevel)" stroke-width="2"/>' % (gx, gy, gw, gh))
    o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="url(#scr)"/>' % (gx + 6, gy + 6, gw - 12, gh - 12))
    o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="url(#inset)"/>' % (gx + 6, gy + 6, gw - 12, gh - 12))
    x0, x1 = PLOT_X, PLOT_X + NCOL * COL_W
    for db in range(-18, 19, 6):
        y = plot_y(db)
        o.append('<path d="M%d %.1fH%d" stroke="#fff" stroke-opacity="%g"/>' % (x0, y, x1, .28 if db == 0 else .08))
        o.append('<text x="%d" y="%.1f" text-anchor="end" dominant-baseline="central" style="%s;font-weight:600;font-size:14px" fill="#8793a3">%s</text>' % (
            x0 - 8, y, TF, ("%+d" % db) if db else "0"))
    for hz, lab in ((20, "20"), (50, "50"), (100, "100"), (200, "200"), (500, "500"), (1000, "1k"), (2000, "2k"),
                    (5000, "5k"), (10000, "10k"), (20000, "20k")):
        x = plot_x(hz)
        o.append('<path d="M%.1f %dV%d" stroke="#fff" stroke-opacity="%g"/>' % (x, PLOT_Y, PLOT_Y + PLOT_H, .12 if lab in ("100", "1k", "10k") else .06))
        o.append('<text x="%.1f" y="%d" text-anchor="middle" style="%s;font-weight:600;font-size:14px" fill="#8793a3">%s</text>' % (
            x, LANE_Y + NLANES * LANE_H + 12 + (4 if NLANES > 1 else 0), TF, lab))
    for hz in (30, 40, 60, 70, 80, 90, 300, 400, 600, 700, 800, 900, 3000, 4000, 6000, 7000, 8000, 9000):
        x = plot_x(hz)
        o.append('<path d="M%.1f %dV%d" stroke="#fff" stroke-opacity=".03"/>' % (x, PLOT_Y, PLOT_Y + PLOT_H))
    if NLANES == 1:   # the dots' lane: a slightly lighter groove
        o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="#ffffff" opacity=".035"/>' % (x0 - 4, LANE_Y, x1 - x0 + 8, LANE_H, LANE_H // 2))
        o.append('<path d="M%d %gH%d" stroke="#ffffff" stroke-opacity=".10" stroke-dasharray="2 6"/>' % (x0, LANE_Y + LANE_H / 2, x1))
    else:             # a lane per band, tinted in its colour and numbered
        for i, (name, kind, col) in enumerate(BANDS):
            y = LANE_Y + i * LANE_H
            o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" opacity=".08"/>' % (x0 - 4, y + 2, x1 - x0 + 8, LANE_H - 4, (LANE_H - 4) // 2, col))
            o.append('<path d="M%d %gH%d" stroke="%s" stroke-opacity=".28" stroke-dasharray="2 6"/>' % (x0, y + LANE_H / 2, x1, col))
            o.append('<text x="%d" y="%g" text-anchor="end" dominant-baseline="central" style="%s;font-weight:700;font-size:14px" fill="%s">%d</text>' % (
                x0 - 10, y + LANE_H / 2, TF, col, i + 1))
    # glass sheen over the screen
    o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="url(#glass)" opacity=".35"/>' % (gx + 6, gy + 6, gw - 12, (gh - 12) // 2))

    # band columns
    for i, (name, kind, col) in enumerate(BANDS):
        x = band_x(i)
        p = "M%g %dH%gA8 8 0 0 1 %g %dV%dA8 8 0 0 1 %g %dH%gA8 8 0 0 1 %g %dV%dA8 8 0 0 1 %g %dZ" % (
            x + 10, COLS_Y, x + COL_PITCH - 12, x + COL_PITCH - 4, COLS_Y + 8, COLS_Y + COLS_H - 8, x + COL_PITCH - 12, COLS_Y + COLS_H,
            x + 10, x + 2, COLS_Y + COLS_H - 8, COLS_Y + 8, x + 10, COLS_Y)
        o.append(panel(p, t, fin))
        o.append('<path d="M%g %dH%g" stroke="%s" stroke-width="3" stroke-linecap="round" opacity=".9"/>' % (x + 16, COLS_Y + 1.5, x + COL_PITCH - 18, col))
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- pictures
def power_svg(colour, on):
    """a band's on/off switch: a round button with a power symbol, glowing in the band's colour when on"""
    w = h = POWER_W
    c = w / 2
    ink = colour if on else "#5d6570"
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs>'
            '<filter id="g" x="-50%%" y="-50%%" width="200%%" height="200%%"><feGaussianBlur stdDeviation="2.2"/></filter>'
            '<linearGradient id="f" x2="0" y2="1"><stop stop-color="#262b33"/><stop offset="1" stop-color="#11141a"/></linearGradient></defs>'
            '<circle cx="%g" cy="%g" r="%g" fill="url(#f)" stroke="%s" stroke-opacity="%g" stroke-width="1.5"/>'
            '<g fill="none" stroke="%s" stroke-width="2.4" stroke-linecap="round" %s>'
            '<path d="M%g %g A7 7 0 1 0 %g %g"/><path d="M%g %gV%g"/></g>'
            '<g fill="none" stroke="%s" stroke-width="2.4" stroke-linecap="round">'
            '<path d="M%g %g A7 7 0 1 0 %g %g"/><path d="M%g %gV%g"/></g></svg>') % (
        w, h, c, c, c - 1.5, ink, .9 if on else .25,
        colour, 'filter="url(#g)" opacity="%g"' % (.9 if on else 0),
        c - 4.6, c - 4.4, c + 4.6, c - 4.4, c, c - 9, c - 1,
        ink, c - 4.6, c - 4.4, c + 4.6, c - 4.4, c, c - 9, c - 1)


def pill_svg(name, colour, selected):
    """a band's TYPE field (MPC writes the type in it): outlined in the band's colour, lit when the band is selected"""
    w, h = PILL_W, BAND_BTN[1]
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs>'
            '<filter id="g" x="-20%%" y="-50%%" width="140%%" height="200%%"><feGaussianBlur stdDeviation="2.5"/></filter>'
            '<linearGradient id="f" x2="0" y2="1"><stop stop-color="%s"/><stop offset="1" stop-color="#11141a"/></linearGradient></defs>'
            '%s<rect x="1.5" y="1.5" width="%d" height="%d" rx="9" fill="url(#f)" stroke="%s" stroke-opacity="%g" stroke-width="%g"/>'
            '<text x="%g" y="%g" text-anchor="middle" dominant-baseline="central" style="%s;font-weight:700;font-size:14px;letter-spacing:.5px" fill="%s">%s</text></svg>') % (
        w, h, "#2a2f38" if selected else "#20252d",
        ('<rect x="2" y="2" width="%d" height="%d" rx="9" fill="none" stroke="%s" stroke-width="3" filter="url(#g)"/>' % (w - 4, h - 4, colour)) if selected else "",
        w - 3, h - 3, colour, 1 if selected else .35, 2 if selected else 1,
        w / 2, h / 2 + 1, TF, "#ffffff" if selected else "#aab3bd", name)


def column_ring_svg(colour):
    """around the selected band's column"""
    w, h = COL_PITCH - 2, COLS_H + 4
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs><filter id="g" x="-10%%" y="-10%%" width="120%%" height="120%%">'
            '<feGaussianBlur stdDeviation="2.5"/></filter></defs>'
            '<rect x="3" y="3" width="%d" height="%d" rx="10" fill="none" stroke="%s" stroke-width="3" opacity=".75" filter="url(#g)"/>'
            '<rect x="2.5" y="2.5" width="%d" height="%d" rx="10" fill="none" stroke="%s" stroke-width="1.5"/></svg>') % (
        w, h, w - 6, h - 6, colour, w - 5, h - 5, colour)


def bar_strip_svg():
    """an analyzer column: BAR_STEPS + 1 frames (frame 0: nothing), a soft haze: no edge, fading in over its top 14 px and
    out towards the bottom. Each frame fills its column's full width, so side by side they read as one glow, not stripes"""
    w, h = NCOL * COL_W // NBAR, PLOT_H
    n = BAR_STEPS + 1
    c = "#8fb8ff"
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">' % (w, h * n)]
    for k in range(1, n):
        top = k * h + 3 + (h - 6) * (1 - k / BAR_STEPS)
        bottom = (k + 1) * h - 2
        y0 = max(k * h, top - 14)                    # the fade-in stays inside this frame
        span = bottom - y0
        edge = min(.5, max(.02, (top - y0) / span))
        o.append('<defs><linearGradient id="g%d" x2="0" y2="1"><stop stop-color="%s" stop-opacity="0"/>'
                 '<stop offset="%.3f" stop-color="%s" stop-opacity=".30"/><stop offset="1" stop-color="%s" stop-opacity=".05"/></linearGradient></defs>'
                 % (k, c, edge, c, c))
        o.append('<rect x="0" y="%.1f" width="%d" height="%.1f" fill="url(#g%d)"/>' % (y0, w, span, k))
    o.append("</svg>")
    return "".join(o), w, h * n


def analyzer_svg(on):
    """the analyzer switch: a dark pill with a little spectrum, lit when on"""
    _, _, w, h = ANALYZER
    ink = "#bcd6ff" if on else "#6d7682"
    bars = "".join('<rect x="%g" y="%g" width="4" height="%g" rx="1" fill="%s"/>' % (16 + 6 * i, h / 2 + 9 - v, v, ink)
                   for i, v in enumerate((6, 12, 17, 10, 14, 7)))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs>'
            '<filter id="g" x="-20%%" y="-50%%" width="140%%" height="200%%"><feGaussianBlur stdDeviation="2.5"/></filter>'
            '<linearGradient id="f" x2="0" y2="1"><stop stop-color="%s"/><stop offset="1" stop-color="#0f1217"/></linearGradient></defs>'
            '%s<rect x="1.5" y="1.5" width="%d" height="%d" rx="9" fill="url(#f)" stroke="%s" stroke-opacity="%g" stroke-width="1.5"/>%s'
            '<text x="%g" y="%g" text-anchor="middle" dominant-baseline="central" style="%s;font-weight:700;font-size:16px;letter-spacing:2px" fill="%s">ANALYZER</text></svg>') % (
        w, h, "#262c35" if on else "#1b1f26",
        ('<rect x="3" y="3" width="%d" height="%d" rx="9" fill="none" stroke="#9fc4ff" stroke-width="3" filter="url(#g)" opacity=".7"/>' % (w - 6, h - 6)) if on else "",
        w - 3, h - 3, "#9fc4ff" if on else "#ffffff", .8 if on else .14, bars, w / 2 + 22, h / 2 + 1, TF, "#eef4ff" if on else "#8b949e")


def dot_svg(n, colour):
    """a band's numbered dot: a filled circle in the band's colour with its number"""
    c = DOT / 2
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs><filter id="g" x="-50%%" y="-50%%" width="200%%" height="200%%">'
            '<feGaussianBlur stdDeviation="1.8"/></filter></defs>'
            '<circle cx="%g" cy="%g" r="%g" fill="%s" opacity=".55" filter="url(#g)"/>'
            '<circle cx="%g" cy="%g" r="%g" fill="%s" stroke="#0b0e13" stroke-width="2"/>'
            '<text x="%g" y="%g" text-anchor="middle" dominant-baseline="central" style="%s;font-weight:700;font-size:19px" fill="#0b0e13">%d</text></svg>') % (
        DOT, DOT, c, c, c - 1, colour, c, c, c - 2.5, colour, c, c + .5, TF, n)


LANE_FRAMES = 128


def lane_strip_svg():
    """the selected band's handle on the lane: a white ring that follows its frequency (a horizontal slider's filmstrip:
    frame k = the ring at k / 127 of the way across). Drawn over the coloured dot, it marks which band a drag moves"""
    w, h = NCOL * COL_W, LANE_H
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs><filter id="g" x="-50%%" y="-50%%" width="200%%" height="200%%">'
         '<feGaussianBlur stdDeviation="2"/></filter></defs>' % (w, h * LANE_FRAMES)]
    r = LANE_H / 2 - 1.5
    for k in range(LANE_FRAMES):
        cx = min(max(w * k / (LANE_FRAMES - 1), r + 1), w - r - 1)
        cy = k * h + h / 2
        o.append('<circle cx="%.1f" cy="%g" r="%g" fill="none" stroke="#ffffff" stroke-width="3" opacity=".6" filter="url(#g)"/>'
                 '<circle cx="%.1f" cy="%g" r="%g" fill="none" stroke="#ffffff" stroke-width="2"/>' % (cx, cy, r, cx, cy, r))
    o.append("</svg>")
    return "".join(o), w, h * LANE_FRAMES


TOUCH_W = 64                                             # the touch glow's width (wider than a column, centred on it)


def touch_glow_svg():
    """the graph column under the finger: a soft column of light, brightest along the middle, with a bright core line"""
    w, h = TOUCH_W, PLOT_H
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs>'
            '<linearGradient id="hz"><stop stop-color="#ffffff" stop-opacity="0"/><stop offset=".5" stop-color="#ffffff" stop-opacity=".26"/>'
            '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>'
            '<linearGradient id="v" x2="0" y2="1"><stop stop-color="#000" stop-opacity=".55"/><stop offset=".5" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#000" stop-opacity=".55"/></linearGradient>'
            '<mask id="m"><rect width="%d" height="%d" fill="#fff"/><rect width="%d" height="%d" fill="url(#v)"/></mask></defs>'
            '<g mask="url(#m)"><rect width="%d" height="%d" fill="url(#hz)"/><rect x="%g" width="2" height="%d" fill="#ffffff" opacity=".7"/></g></svg>') % (
        w, h, w, h, w, h, w, h, w / 2 - 1, h)


HALO = (76, 36)


def halo_svg():
    """around the selected band's dot while it's being moved: a bright glow"""
    w, h = HALO
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs><radialGradient id="r" cx=".5" cy=".5" r=".5">'
            '<stop offset=".35" stop-color="#ffffff" stop-opacity=".85"/><stop offset=".7" stop-color="#ffffff" stop-opacity=".30"/>'
            '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>'
            '<ellipse cx="%g" cy="%g" rx="%g" ry="%g" fill="url(#r)"/></svg>') % (w, h, w / 2, h / 2, w / 2, h / 2)


def marker_svg():
    """the selected band's frequency on the graph: a thin dashed line (under the curve)"""
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><path d="M%g 0V%d" stroke="#ffffff" stroke-width="1.5" '
            'stroke-dasharray="5 4" opacity=".55"/></svg>') % (COL_W, PLOT_H, COL_W / 2, PLOT_H)


def column_strip_svg():
    """the curve, one column: CURVE_STEPS + 1 frames, each the column's level as a bright cap over a soft fill from 0 dB"""
    w, h = COL_W, PLOT_H
    n = CURVE_STEPS + 1
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><defs>'
         '<linearGradient id="up" x2="0" y2="1"><stop stop-color="%s" stop-opacity=".34"/><stop offset="1" stop-color="%s" stop-opacity=".06"/></linearGradient>'
         '<linearGradient id="dn" x2="0" y2="1"><stop stop-color="%s" stop-opacity=".06"/><stop offset="1" stop-color="%s" stop-opacity=".34"/></linearGradient>'
         '<filter id="g" x="-50%%" y="-200%%" width="200%%" height="500%%"><feGaussianBlur stdDeviation="2"/></filter></defs>' % (
             w, h * n, CURVE, CURVE, CURVE, CURVE)]
    y0 = h / 2
    for k in range(n):
        top = k * h
        y = top + 2.5 + (h - 5) * (1 - k / CURVE_STEPS)       # frame k: -18 dB at the bottom .. +18 at the top (inside its frame)
        a, b = sorted((top + y0, y))
        if b - a > .5:
            o.append('<rect x="0" y="%.2f" width="%d" height="%.2f" fill="url(#%s)"/>' % (a, w, b - a, "up" if y < top + y0 else "dn"))
        o.append('<rect x="-1" y="%.2f" width="%d" height="4" fill="%s" opacity=".55" filter="url(#g)"/>' % (y - 2, w + 2, CURVE))
        o.append('<rect x="-.5" y="%.2f" width="%g" height="2.6" rx="1" fill="%s"/>' % (y - 1.3, w + 1, CURVE))
    o.append("</svg>")
    return "".join(o), w, h * n


# ---------------------------------------------------------------- layout.conf
def layout():
    L = ["# %s -- 3DTHC." % ("Shapey EQ" if NB == 8 else "Shapey 5-Band EQ") + " Written by tools/make_skin_art.py: edit the design there and rerun it, not this file.",
         "# One page: master and theme on top, the curve display, then one column per band (switch, FREQ, GAIN or SLOPE, Q).",
         "# Every themed part is one line per theme (when=theme:<n>). Coordinates are layout space (skin y + 86).", "",
         "theme_ink=e6eef6", "theme_ink_dim=7d8b9a", "theme_accent=d7dce2", "theme_accent_hi=ffffff", "theme_line=2b3746",
         "theme_box=10151b", "theme_lcd=0a0e13", "theme_seg_active=d7dce2", "theme_seg_inactive=121820", "theme_seg_active_tx=06121c",
         "art_css=popup.css", "", "[tab SHAPEY]"]
    for n, (slug, name, _) in enumerate(THEMES):
        L.append('art file="artwork/bg_%s.svg" when=theme:%d' % (slug, n))
    x, w = THEME_SEL
    L += ["", "# theme: value between the arrows",
          'readout cx=%d cy=%d w=%d h=%d box=0 tsize=%d tcolor=eef1f4 label="THEME" key=theme' % (
              x + w // 2, SEL_Y + SEL_H // 2 + Y, w - 2 * ARROW_W - 8, SEL_H, FIELD_TEXT)]
    ax, ay, aw, ah = ANALYZER
    L += ["", "# the analyzer: a switch in the header, and a 72-column haze behind everything on the graph (display only)",
          'toggle cx=%d cy=%d key=analyzer label="ANALYZER" img=images/analyzer_off.png img_on=images/analyzer_on.png w=%d h=%d ns=0' % (
              ax, ay + Y, aw, ah)]
    bw_ = NCOL * COL_W // NBAR
    for k in range(NBAR):
        L.append('meter cx=%d cy=%d w=%d h=%d key=a%d strip=images/bar.png frames=%d' % (
            PLOT_X + k * bw_ + bw_ // 2, PLOT_Y + PLOT_H // 2 + Y, bw_, PLOT_H, k, BAR_STEPS + 1))
    L += ["", "# touch feedback: the column under the finger glows while it's down (the engine's touch picks it)"]
    for c in range(NCOL):
        L.append('button cx=%d cy=%d w=%d h=%d key=noop label="" img=images/touch_glow.png img_on=images/touch_glow.png when=touch:%d' % (
            PLOT_X + c * COL_W + COL_W // 2, PLOT_Y + PLOT_H // 2 + Y, TOUCH_W, PLOT_H, c + 1))
    L += ["", "# the selected band's frequency: a dashed line under the curve (one per column, the engine's mark picks it)"]
    for c in range(NCOL):
        L.append('button cx=%d cy=%d w=%d h=%d key=noop label="" img=images/marker.png img_on=images/marker.png when=mark:%d' % (
            PLOT_X + c * COL_W + COL_W // 2, PLOT_Y + PLOT_H // 2 + Y, COL_W, PLOT_H, c + 1))
    L += ["", "# the curve: 72 columns, each a filmstrip following the engine's c<n>. A touch on one moves the selected band",
          "# there: the column is its frequency, the height its gain (a drag up or down follows the finger)"]
    for c in range(NCOL):
        L.append('meter cx=%d cy=%d w=%d h=%d key=c%d strip=images/curve_col.png frames=%d' % (
            PLOT_X + c * COL_W + COL_W // 2, PLOT_Y + PLOT_H // 2 + Y, COL_W, PLOT_H, c, CURVE_STEPS + 1))
    L += ["", "# the selected band's dot glows while it moves (behind the dots; the engine's grab picks the place)"]
    for lane in range(NLANES):
        for k in range(NDOT):
            L.append('button cx=%d cy=%d w=%d h=%d key=noop label="" img=images/halo.png img_on=images/halo.png when=grab:%d' % (
                PLOT_X + k * (NCOL * COL_W // NDOT) + NCOL * COL_W // NDOT // 2, lane_cy(lane) + Y, HALO[0], HALO[1], lane * NDOT + k + 1))
    L += ["", "# each band's numbered dot on the lane, at its frequency (the engine's dot_<n> picks the place; hidden when off)"]
    for i, (name, kind, col) in enumerate(BANDS):
        for k in range(NDOT):
            L.append('button cx=%d cy=%d w=%d h=%d key=noop label="" img=images/dot_%d.png img_on=images/dot_%d.png when=dot_%d:%d' % (
                PLOT_X + k * (NCOL * COL_W // NDOT) + NCOL * COL_W // NDOT // 2, lane_cy(i) + Y, DOT, DOT, i + 1, i + 1, i + 1, k + 1))
    L += ["", "# the selected band's handle: a horizontal slider across the lane on its frequency. Drag it (anywhere on the lane)",
          "# left and right to move the band; its ring follows the finger. One per band, only the selected one shows"]
    if NLANES > 1:
        L[-2:] = ["", "# each band's handle: a horizontal slider across its own lane on its frequency. Drag it (anywhere on the lane)",
                  "# left and right to move that band; its ring follows the finger, and it becomes the selected band"]
    for i, (name, kind, col) in enumerate(BANDS):
        L.append('slider_h cx=%d cy=%d w=%d h=%d ns=0 vs=8 strip=images/lane.png frames=%d label="%s" key=b%d_freq%s' % (
            PLOT_X + NCOL * COL_W // 2, lane_cy(i) + Y, NCOL * COL_W, LANE_H, LANE_FRAMES, name, i + 1, "" if NLANES > 1 else " when=sel:%d" % i))
    L += ["", "# a tap anywhere on a band's column selects it for the touch graph (under everything else in the column;",
          "# touching one of its knobs or its TYPE selects it too)"]
    for i, (name, kind, col) in enumerate(BANDS):
        top = COLS_Y + COL_PAD + BAND_BTN[1]
        L.append('button cx=%d cy=%d w=%d h=%d key=pick_%d label="" img=images/blank.png img_on=images/blank.png' % (
            band_x(i) + COL_PITCH // 2, top + PICK_BOX[1] // 2 + Y, PICK_BOX[0], PICK_BOX[1], i + 1))
    L += ["", "# the selected band's column glows (the controls sit on top of it)"]
    for i, (name, kind, col) in enumerate(BANDS):
        L.append('button cx=%d cy=%d w=%d h=%d key=noop label="" img=images/ring_%d.png img_on=images/ring_%d.png when=sel:%d' % (
            band_x(i) + COL_PITCH // 2, COLS_Y + COLS_H // 2 + Y, COL_PITCH - 2, COLS_H + 4, i + 1, i + 1, i))
    L += ["", "# each band's header: power switch, then its TYPE (a field MPC writes the type in; a tap opens the list)"]
    for i, (name, kind, col) in enumerate(BANDS):
        bw, bh = BAND_BTN
        x0 = band_x(i) + (COL_PITCH - bw) // 2
        cy = COLS_Y + COL_PAD + bh // 2 + Y
        L.append('toggle cx=%d cy=%d key=b%d_on label="ON" img=images/power_%d_off.png img_on=images/power_%d_on.png w=%d h=%d ns=0' % (
            x0 + POWER_W // 2, cy, i + 1, i + 1, i + 1, POWER_W, bh))
        px = x0 + bw - PILL_W // 2
        L.append('button cx=%d cy=%d w=%d h=%d key=noop label="" img=images/pill_%d.png img_on=images/pill_%d.png' % (
            px, cy, PILL_W, bh, i + 1, i + 1))
        L.append('button cx=%d cy=%d w=%d h=%d key=noop label="" img=images/pill_%d_sel.png img_on=images/pill_%d_sel.png when=sel:%d' % (
            px, cy, PILL_W, bh, i + 1, i + 1, i))
        L.append('popup cx=%d cy=%d w=%d h=%d label="TYPE" key=b%d_type field=none accent=eef1f4 cols=2 cw=%d options="%s"' % (
            px, cy, PILL_W, bh, i + 1, TYPE_CELL, ",".join(TYPES)))
    bx, by, bw, bh = BYPASS
    mx, my = MASTER
    for n, (slug, _, t) in enumerate(THEMES):
        L += ["", "# ---- theme %d: %s" % (n, slug)]
        L.append('toggle cx=%d cy=%d key=bypass label="BYPASS" img=images/%s_bypass_off.png img_on=images/%s_bypass_on.png w=%d h=%d ns=0 when=theme:%d' % (
            bx, by + Y, slug, slug, bw, bh, n))
        L.append('knob cx=%d cy=%d r=20 lay=side bw=192 bh=%d vs=%d ink=%s ink_dim=%s strip=images/%s_knob_r20.png frames=%d label="MASTER" key=master when=theme:%d' % (
            mx, my + Y, max(SEL_H, 50), 34 if NB == 8 else 30, t["knob_name"], t["ink"].lstrip("#"), slug, FRAMES, n))
        x, w = THEME_SEL
        for side, ax in (("prev", x + ARROW_W // 2), ("next", x + w - ARROW_W // 2)):
            L.append('button cx=%d cy=%d w=%d h=%d key=theme_%s label="" img=images/%s_arrow_%s.png img_on=images/%s_arrow_%s_on.png when=theme:%d' % (
                ax, SEL_Y + SEL_H // 2 + Y, ARROW_W, SEL_H, side, slug, side, slug, side, n))
        for i, (name, kind, col) in enumerate(BANDS):
            cx = band_x(i) + COL_PITCH // 2
            top = COLS_Y + COL_PAD + BAND_BTN[1] + 4
            if KNOB_ROW:
                for (lab, key), dx in ((("FREQ", "b%d_freq" % (i + 1)), -78), (("SLOPE" if kind == "cut" else "GAIN", "b%d_x" % (i + 1)), 0),
                                       (("Q", "b%d_q" % (i + 1)), 78)):
                    L.append('knob cx=%d cy=%d r=%d bw=78 ns=%d vs=%d ink=%s ink_dim=%s strip=images/%s_knob_r%d.png frames=%d label="%s" key=%s when=theme:%d' % (
                        cx + dx, top + FREQ_R + 5 + Y, FREQ_R, FREQ_NS, FREQ_VS, t["knob_name"], t["knob_value"], slug, FREQ_R, FRAMES, lab, key, n))
                continue
            L.append('knob cx=%d cy=%d r=%d bw=150 ns=%d vs=%d ink=%s ink_dim=%s strip=images/%s_knob_r%d.png frames=%d label="FREQ" key=b%d_freq when=theme:%d' % (
                cx, top + FREQ_R + 5 + Y, FREQ_R, FREQ_NS, FREQ_VS, t["knob_name"], t["knob_value"], slug, FREQ_R, FRAMES, i + 1, n))
            row2 = top + knob_box(FREQ_R, FREQ_NS, FREQ_VS) + 2
            for (lab, key), dx in ((("SLOPE" if kind == "cut" else "GAIN", "b%d_x" % (i + 1)), -38), (("Q", "b%d_q" % (i + 1)), 38)):
                L.append('knob cx=%d cy=%d r=%d bw=76 ns=%d vs=%d ink=%s ink_dim=%s strip=images/%s_knob_r%d.png frames=%d label="%s" key=%s when=theme:%d' % (
                    cx + dx, row2 + SMALL_R + 5 + Y, SMALL_R, SMALL_NS, SMALL_VS, t["knob_name"], t["knob_value"], slug, SMALL_R, FRAMES, lab, key, n))
    L += ["", "# Q-Links: one column of four per band (freq, gain or slope, Q, type), then master"]
    ql = []
    for i, (name, kind, col) in enumerate(BANDS):
        ql += ["b%d_freq" % (i + 1), "b%d_x" % (i + 1), "b%d_q" % (i + 1), "b%d_type" % (i + 1)]
    L.append('qlinks "BANDS 1-4" = %s' % ",".join(ql[:16]))
    if NB == 8:
        L.append('qlinks "BANDS 5-8" = %s' % ",".join(ql[16:]))
        L.append('qlinks "MASTER" = master')
    else:
        L.append('qlinks "BAND 5, MASTER" = %s' % ",".join(ql[16:] + ["master"]))
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- Shapey 5-Band EQ (SHAPEY_BANDS=5): its own geometry
NB = int(os.environ.get("SHAPEY_BANDS", "8"))
NLANES = 1                                               # lanes under the curve: one shared (8 bands) or one per band (5)
TITLE_SUB = "PARAMETRIC EQ"
KNOB_ROW = False                                         # the band's three knobs in one row (5 bands) or FREQ over two (8)
if NB == 5:
    VST = os.path.join(HERE, "..", "vst5")
    TITLE_SUB = "5-BAND EQ"
    HDR_H = 58                                           # one slim header row: more height for the graph
    SEL_Y, SEL_H, ARROW_W = 10, 38, 48
    THEME_SEL = (922, 200)
    BYPASS = (1200, 29, 120, 38)
    MASTER = (662, 29)                                   # the knob's box: 566 .. 758 (knob at its left, value after)
    ANALYZER = (385, 29, 170, 38)
    FIELD_TEXT = 30
    GRAPH = (16, 62, 1248, 340)
    PLOT_Y, PLOT_H = 70, 172                             # the curve: 172 px tall (the 8-band one is 130)
    LANE_Y, LANE_H, NLANES = 246, 26, 5                  # a lane per band, each with its own dot to drag
    DOT, HALO = 24, (60, 28)
    BANDS = [("LOW CUT", "cut", "#ff5a5f"), ("LOW SHELF", "shelf", "#ff9f40"), ("BELL", "bell", "#ffd84a"),
             ("HIGH SHELF", "shelf", "#b47cff"), ("HIGH CUT", "cut", "#ff6fc6")]
    COLS_Y, COL_PITCH, COLS_H = 410, 249, 210
    PILL_W, TYPE_TEXT, TYPE_CELL = 177, 26, 140
    BAND_BTN = (PILL_W + 4 + POWER_W, 38)
    FREQ_R = SMALL_R = 27
    FREQ_NS = FREQ_VS = SMALL_NS = SMALL_VS = 28
    KNOB_ROW = True
    PICK_BOX = (COL_PITCH - 8, COLS_H - COL_PAD - BAND_BTN[1])


def lane_cy(i):
    """the y (skin) of band i's lane: its own with a lane per band, else the shared one"""
    return LANE_Y + (i if NLANES > 1 else 0) * LANE_H + LANE_H // 2


def main():
    os.makedirs(os.path.join(VST, "artwork"), exist_ok=True)
    img = os.path.join(VST, "images")
    os.makedirs(img, exist_ok=True)
    items = []
    for slug, _, t in THEMES:
        with open(os.path.join(VST, "artwork", "bg_%s.svg" % slug), "w") as f:
            f.write(background(slug, t) + "\n")
        for on in (0, 1):
            items.append((os.path.join(img, "%s_bypass_%s.png" % (slug, "on" if on else "off")), bypass_svg(slug, t, on), BYPASS[2], BYPASS[3]))
        for r in (FREQ_R, SMALL_R, 20):
            svg, w, h = knob_strip_svg(slug, t, r)
            items.append((os.path.join(img, "%s_knob_r%d.png" % (slug, r)), svg, w, h))
        for side in ("prev", "next"):
            for pressed in (0, 1):
                items.append((os.path.join(img, "%s_arrow_%s%s.png" % (slug, side, "_on" if pressed else "")),
                              arrow_svg(t, side, pressed), ARROW_W, SEL_H))
    for i, (name, kind, col) in enumerate(BANDS):
        for on in (0, 1):
            items.append((os.path.join(img, "power_%d_%s.png" % (i + 1, "on" if on else "off")), power_svg(col, on), POWER_W, BAND_BTN[1]))
        items.append((os.path.join(img, "pill_%d.png" % (i + 1)), pill_svg("", col, False), PILL_W, BAND_BTN[1]))
        items.append((os.path.join(img, "pill_%d_sel.png" % (i + 1)), pill_svg("", col, True), PILL_W, BAND_BTN[1]))
        items.append((os.path.join(img, "ring_%d.png" % (i + 1)), column_ring_svg(col), COL_PITCH - 2, COLS_H + 4))
    items.append((os.path.join(img, "marker.png"), marker_svg(), COL_W, PLOT_H))
    bw_, bh_ = PICK_BOX
    items.append((os.path.join(img, "blank.png"), '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"/>' % (bw_, bh_), bw_, bh_))
    items.append((os.path.join(img, "touch_glow.png"), touch_glow_svg(), TOUCH_W, PLOT_H))
    items.append((os.path.join(img, "halo.png"), halo_svg(), *HALO))
    for i, (name, kind, col) in enumerate(BANDS):
        items.append((os.path.join(img, "dot_%d.png" % (i + 1)), dot_svg(i + 1, col), DOT, DOT))
    svg, w, h = lane_strip_svg()
    items.append((os.path.join(img, "lane.png"), svg, w, h))
    svg, w, h = bar_strip_svg()
    items.append((os.path.join(img, "bar.png"), svg, w, h))
    for on in (0, 1):
        items.append((os.path.join(img, "analyzer_%s.png" % ("on" if on else "off")), analyzer_svg(on), ANALYZER[2], ANALYZER[3]))
    svg, w, h = column_strip_svg()
    items.append((os.path.join(img, "curve_col.png"), svg, w, h))
    render_pngs(items)
    with open(os.path.join(VST, "layout.conf"), "w") as f:
        f.write(layout())
    print("wrote %d themes: backgrounds, %d images, layout.conf" % (len(THEMES), len(items)))


if __name__ == "__main__":
    main()
