#!/usr/bin/env python3
"""Writes params.json and presets.json for both Shapey plugins (presets are written in Hz / dB / Q here and converted
to knob units):

    python3 tools/make_params.py          # Shapey EQ (8 bands) -> vst/   and   Shapey 5-Band EQ -> vst5/

Every band has: on, TYPE (Bell, Low Shelf, High Shelf, Low Cut, High Cut, Notch, Band Pass), FREQ, a second knob whose
meaning follows the type (GAIN for bells and shelves, SLOPE for cuts, nothing for notch and band pass; the engine
renames it and writes its value), and Q. Each band keeps its gain and its slope separately, so switching a type and
back loses nothing.
"""
import json
import math
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TYPES = ["Bell", "Low Shelf", "High Shelf", "Low Cut", "High Cut", "Notch", "Band Pass"]
SLOPES = ["6 dB", "12 dB", "24 dB", "48 dB"]
NCOL = 72
VARIANTS = {
    8: dict(dir="vst", types=["Low Cut", "Low Shelf", "Bell", "Bell", "Bell", "Bell", "High Shelf", "High Cut"],
            hz=[30, 100, 250, 800, 2500, 6000, 10000, 18000]),
    5: dict(dir="vst5", types=["Low Cut", "Low Shelf", "Bell", "High Shelf", "High Cut"],
            hz=[30, 100, 1000, 10000, 18000]),
}


def hz_pos(hz):
    return round(1000 * math.log(hz / 20) / math.log(1000))


def q_pos(q):
    return round(100 * math.log(q / 0.1) / math.log(100))


def has_gain(t):
    return t in ("Bell", "Low Shelf", "High Shelf")


def is_cut(t):
    return t in ("Low Cut", "High Cut")


def default_q(t):
    return 0.71 if t in ("Low Shelf", "High Shelf", "Low Cut", "High Cut") else 1.0


def x_value(t, gain=0.0, slope="24 dB"):
    """the second knob's raw value (0..480): gain + 24 dB in tenths, or the slope's quarter of the range"""
    if is_cut(t):
        return SLOPES.index(slope) * 120 + 60
    return round(gain * 10) + 240


def params(nb):
    V = VARIANTS[nb]
    P = []
    for i in range(1, nb + 1):
        t = V["types"][i - 1]
        # short names: MPC writes them under the knobs (the band's number and colour are on its column)
        P.append({"key": "b%d_on" % i, "name": "Band %d On" % i, "min": 0, "max": 1, "default": 1 if t == "Bell" else 0, "display": "int"})
        P.append({"key": "b%d_type" % i, "name": "Type", "options": TYPES, "default": t, "qlink_ticks": 3,
                  "refresh_display": True})   # the second knob's name and text follow it (dynamic_name / dynamic_display)
        P.append({"key": "b%d_freq" % i, "name": "FREQ", "min": 0, "max": 1000, "default": hz_pos(V["hz"][i - 1]),
                  "dynamic_display": True})
        P.append({"key": "b%d_x" % i, "name": "GAIN" if has_gain(t) else "SLOPE", "min": 0, "max": 480,
                  "default": x_value(t), "dynamic_name": True, "dynamic_display": True})
        P.append({"key": "b%d_q" % i, "name": "Q", "min": 0, "max": 100, "default": q_pos(default_q(t)), "dynamic_display": True})
    P += [{"key": "master", "name": "Master", "min": -24, "max": 24, "default": 0, "dynamic_display": True},
          {"key": "bypass", "name": "Bypass", "min": 0, "max": 1, "default": 0, "display": "int"},
          {"key": "theme", "name": "Theme", "options": ["Grey", "Classic", "White", "Silver"], "default": "Grey", "qlink_ticks": 3},
          {"key": "theme_prev", "name": "Theme <", "momentary": True},
          {"key": "theme_next", "name": "Theme >", "momentary": True},
          {"key": "noop", "name": "-", "momentary": True}]
    P += [{"key": "c%d" % c, "name": "Curve %d" % (c + 1), "min": 0, "max": 60, "default": 30} for c in range(NCOL)]
    # the touch graph: which band a tap on the curve moves (the last band touched), and its frequency marker
    P += [{"key": "sel", "name": "Selected Band", "options": ["Band %d" % (i + 1) for i in range(nb)], "default": "Band %d" % (nb // 2 + (1 if nb < 8 else 0))},
          {"key": "mark", "name": "Marker", "options": ["-"] + [str(c + 1) for c in range(NCOL)], "default": "-"}]
    P += [{"key": "pick_%d" % i, "name": "Pick Band %d" % i, "momentary": True} for i in range(1, nb + 1)]
    # each band's numbered dot on the lane under the curve: its place (1..48 along the frequency axis), "-" when off
    P += [{"key": "dot_%d" % i, "name": "Band %d Dot" % i, "options": ["-"] + [str(k + 1) for k in range(48)], "default": "-"}
          for i in range(1, nb + 1)]
    # touch feedback: the graph column under the finger (+1), and the selected band's ring place on the lane while it moves
    P += [{"key": "touch", "name": "Touch", "options": ["-"] + [str(c + 1) for c in range(NCOL)], "default": "-"},
          {"key": "grab", "name": "Grab", "options": ["-"] + [str(k + 1) for k in range(48 * (nb if nb < 8 else 1))], "default": "-"}]
    # the analyzer: a switch, and a 72-column spectrum line the engine sets (display only)
    P += [{"key": "analyzer", "name": "Analyzer", "min": 0, "max": 1, "default": 0, "display": "int"}]
    P += [{"key": "a%d" % k, "name": "Spectrum %d" % (k + 1), "min": 0, "max": 24, "default": 0} for k in range(72)]
    return P


def band_values(nb, i, on, t=None, hz=None, val=None, q=None):
    V = VARIANTS[nb]
    t = t or V["types"][i - 1]
    gain = val if isinstance(val, (int, float)) else 0.0
    slope = val if isinstance(val, str) else "24 dB"
    return {"b%d_on" % i: 1 if on else 0, "b%d_type" % i: TYPES.index(t), "b%d_freq" % i: hz_pos(hz or V["hz"][i - 1]),
            "b%d_x" % i: x_value(t, gain, slope), "b%d_q" % i: q_pos(q or default_q(t))}


def preset(nb, name, master=0.0, **bands):
    """bands: b1=(hz, gain|slope, q) on the band's default type, or (type, hz, gain|slope, q). Anything not given is the
    default: off for cuts and shelves, on and flat for bells"""
    vals = {"master": master}
    for i in range(1, nb + 1):
        spec = bands.get("b%d" % i)
        if spec is None:
            vals.update(band_values(nb, i, VARIANTS[nb]["types"][i - 1] == "Bell"))
            continue
        t = spec[0] if spec[0] in TYPES else None
        hz, val, q = spec[1:] if t else spec
        vals.update(band_values(nb, i, True, t, hz, val, q))
    return {"name": name, "values": vals}


def presets(nb):
    p = lambda *a, **k: preset(nb, *a, **k)
    if nb == 8:
        return [
            p("Flat"),
            p("Vocal Clarity", b1=(80, "24 dB", None), b3=(250, -2.5, 1.2), b5=(3000, 2.5, 1.0), b7=(10000, 2.0, 0.71)),
            p("Vocal Air", b1=(100, "24 dB", None), b6=(6500, -1.5, 3.0), b7=(12000, 4.0, 0.71)),
            p("Warm Vocal", b1=(70, "24 dB", None), b2=(150, 2.0, 0.71), b4=(800, -1.0, 1.0), b5=(3500, -1.5, 1.0),
              b8=(15000, "12 dB", None)),
            p("De-Mud", b1=(60, "24 dB", None), b3=(300, -4.0, 1.4), b4=(500, -2.0, 1.0)),
            p("De-Ess", b1=(80, "24 dB", None), b6=("Notch", 6500, None, 4.0)),
            p("Telephone", b1=(400, "24 dB", None), b4=(1200, 6.0, 1.4), b8=(3000, "24 dB", None), master=-3.0),
            p("Low Cut", b1=(100, "24 dB", None)),
            p("Bass Boost", b2=(90, 5.0, 0.71), b3=(250, -2.0, 1.0)),
            p("Bright Mix", b2=(100, 1.5, 0.71), b7=(8000, 3.0, 0.71)),
            p("Hum Notch", b1=(40, "24 dB", None), b3=("Notch", 60, None, 8.0), b4=("Notch", 120, None, 8.0)),
        ]
    return [
        p("Flat"),
        p("Vocal Clarity", b1=(80, "24 dB", None), b2=("Bell", 250, -2.5, 1.2), b3=(3000, 2.5, 1.0), b4=(10000, 2.0, 0.71)),
        p("Vocal Air", b1=(100, "24 dB", None), b3=(6500, -1.5, 3.0), b4=(12000, 4.0, 0.71)),
        p("Warm Vocal", b1=(70, "24 dB", None), b2=(150, 2.0, 0.71), b3=(3500, -1.5, 1.0), b5=(15000, "12 dB", None)),
        p("De-Mud", b1=(60, "24 dB", None), b3=(300, -4.0, 1.4)),
        p("De-Ess", b1=(80, "24 dB", None), b3=("Notch", 6500, None, 4.0)),
        p("Telephone", b1=(400, "24 dB", None), b3=(1200, 6.0, 1.4), b5=(3000, "24 dB", None), master=-3.0),
        p("Low Cut", b1=(100, "24 dB", None)),
        p("Bass Boost", b2=(90, 5.0, 0.71), b3=(250, -2.0, 1.0)),
        p("Bright Mix", b2=(100, 1.5, 0.71), b4=(8000, 3.0, 0.71)),
    ]


def main():
    for nb, V in VARIANTS.items():
        d = os.path.join(ROOT, V["dir"])
        os.makedirs(d, exist_ok=True)
        P, S = params(nb), presets(nb)
        with open(os.path.join(d, "params.json"), "w") as f:
            f.write('{\n  "params": [\n' + ",\n".join("    " + json.dumps(p) for p in P) + "\n  ]\n}\n")
        with open(os.path.join(d, "presets.json"), "w") as f:
            f.write('{\n  "presets": [\n' + ",\n".join("    " + json.dumps(p) for p in S) + "\n  ]\n}\n")
        print("%s: %d params, %d presets" % (V["dir"], len(P), len(S)))


if __name__ == "__main__":
    main()
