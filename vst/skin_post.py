#!/usr/bin/env python3
"""Shapey EQ skin touch-up, run by gen_vst.py after the skin is built (vst.json "skin_post"):

    python3 skin_post.py "<skin dir>"

The lane handles (a horizontal slider per band, on its frequency) show only their ring: the builder gives every slider a
value label under it, which here would print over the graph's frequency scale, so it is removed. The TYPE fields'
text gets bigger (TYPE_TEXT) and the field's full width (the builder keeps 44 px for a list arrow these fields don't
draw). Fails if either is not found, so a builder change can't silently undo it.
"""
import json
import os
import sys

skin = sys.argv[1]
path = os.path.join(skin, "Plugin Skins", "TUI.json") if os.path.isdir(os.path.join(skin, "Plugin Skins")) else os.path.join(skin, "TUI.json")
tui = json.load(open(path))
changed = 0
fields = 0
TYPE_TEXT = 22.0   # MPC font height; tools/make_skin_art.py sizes the 100 x 38 fields for it


def walk(o):
    global changed
    if isinstance(o, dict):
        if str(o.get("key", "")).startswith("shSlider_h"):
            comps = o.get("value", {}).get("componentsData", [])
            keep = [c for c in comps if c.get("componentData", {}).get("type") != "Label"]
            changed += len(comps) - len(keep)
            o["value"]["componentsData"] = keep
        if str(o.get("key", "")).startswith("shPopField"):
            global fields
            for c in o.get("value", {}).get("componentsData", []):
                cd = c.get("componentData", {})
                if cd.get("type") == "Label" and cd.get("data", {}).get("type") == "Value":
                    cd["data"]["textStyle"]["font"]["height"] = TYPE_TEXT
                    b = c["bounds"] if "bounds" in c else None
                    if b and isinstance(b.get("bounds"), str):
                        x, y, w, h = (int(v) for v in b["bounds"].split())
                        b["bounds"] = "%d %d %d %d" % (2, y, w + 40, h)   # was (8, y, field - 44): now (2, y, field - 4)
                    fields += 1
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)


walk(tui)
if not changed or not fields:
    raise SystemExit("skin_post.py: no lane slider label or TYPE field found (did the skin builder change?)")
json.dump(tui, open(path, "w"), indent=1)
print("skin_post.py: %d lane slider label(s) removed, %d TYPE field(s) resized" % (changed, fields))
