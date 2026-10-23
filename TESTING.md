# Testing Shapey EQ

## Offline (Ubuntu, before the device)

From `~/ShapeyEQ`, with the toolchain in `~/mpc-vst-plugins`:

```bash
MV=~/mpc-vst-plugins
# wrapper host test (parameters, presets, stepping, save/restore, two instances) -- must print PASSED
$MV/tools/test_port.sh vst/vst.json

# EQ response, curve, bypass, latency, clicks, CPU -- must end "0 failure(s)"   (needs numpy)
g++ -O2 -std=gnu++11 -I$MV/wrapper -c src/engine.cpp -o /tmp/shapey_engine.o
gcc -O2 -I$MV/wrapper tests/run_engine.c /tmp/shapey_engine.o -lstdc++ -lm -o /tmp/shapey_run
python3 tests/test_eq.py /tmp/shapey_run

# the band dots follow their frequency, hide when off -- must end "0 failure(s)"
gcc -O2 -I$MV/wrapper tests/test_dots.c /tmp/shapey_engine.o -lstdc++ -lm -o /tmp/shapey_dots && /tmp/shapey_dots
```

Results on 2026-10-21 (offline, x86): host test PASSED; EQ 38/38 (band types: a Bell band as a 24 dB Low Cut, a shelf band as a High Shelf, Notch, Band Pass, gain kept across a type change, no click when a playing band changes type); bells, shelves and cuts land on their
textbook values (a +6 dB bell measures +5.99 dB, cuts -3 dB at the corner and 6/12/24/48 dB per octave), the screen curve
matches, a tap on the curve puts the selected band there (frequency and gain), the analyzer puts a 1 kHz tone at -12 dBFS in the 1 kHz bar at -12 dB and shows the sound after the EQ, bypass is bit-exact, zero latency, no clicks when knobs jump or bands and slopes switch; CPU 0.7 % of one x86 core
with all 8 bands, 48 dB cuts and the analyzer on.

## Build and package

```bash
~/mpc-vst-plugins/tools/build_port.sh vst/vst.json
cd vst && python3 ~/mpc-vst-plugins/tools/release.py --so build/shapey_eq.so \
  --skin "build/skin/3DTHC - VST - Shapey EQ" --entry build/pluginlist-entry.xml --version 1.0.0 -o ~/ShapeyEQ/dist
```

The skin artwork is pre-drawn (`vst/artwork`, `vst/images`); `tools/make_skin_art.py` redraws it after a design change,
`tools/make_params.py` rewrites `params.json` and `presets.json`.

## On the MPC

| # | Do | Expect |
|---|----|--------|
| 1 | Insert Shapey EQ on an audio track | Loads; one page; flat line at 0 dB; Bell 1-4 lit, cuts and shelves dark |
| T1 | **Touch graph (first check):** Bell 2 is selected (green outline). Tap the graph at about 1k, high up | Bell 2 jumps to that frequency and gain: the hump appears under your finger, its knobs follow, the dashed line moves to 1k |
| T2 | Touch the graph and drag up and down without lifting | The gain follows your finger. **Tell me** whether a tap jumps straight to where you touch, or only a drag moves it (from where it was) |
| T3 | Tap an empty part of another band's column (or turn one of its knobs), then tap the graph | That band is selected (its column and TYPE field glow) and it moves instead |
| T4 | Select LOW CUT (switched off) and tap the graph at 200 Hz | It switches on at 200 Hz (a cut has no gain: only the frequency follows) |
| T5 | A band's round power button | Switches it on or off, fading in or out |
| D1 | Look at the lane under the curve | A numbered dot in each switched-on band's colour sits at its frequency; a white ring circles the selected band's dot |
| D2 | **Drag along the lane, left and right** (any band selected, Low and High Cut too) | The selected band follows your finger: its ring, the curve and its FREQ knob move; its coloured dot catches up. **Tell me** whether the ring jumps to where you touch or moves from where it was |
| D3 | Switch a band off | Its dot disappears; on again, it comes back |
| D4 | Touch and drag on the graph | A soft column of light shows where your finger is, and the band's dot glows; both fade ~¼ s after you let go |
| D5 | Drag the ring on the lane | The dot glows while it moves, then settles |
| A1 | ANALYZER on while a track plays | A soft haze behind the curve moves with the music (a steady 10 updates a second): bass on the left, highs on the right; the curve, taps and drags all still work over it |
| A2 | Boost a bell under a busy part of the spectrum | The haze there rises by about the boost (they show the sound after the EQ) |
| A3 | Leave the analyzer on for a minute of playback; tap knobs, open the PRESET menu | The screen stays responsive. **Tell me** if it gets sluggish: the rate or column count can come down |
| A4 | ANALYZER off | The haze disappears and the screen goes still; saved with the project |
| Y1 | **Band types:** tap Band 4's TYPE field (shows "Bell") | A list of 7 opens: Bell, Low Shelf, High Shelf, Low Cut, High Cut, Notch, Band Pass. **Tell me** if the text is too big, too small, or cut off |
| Y2 | Pick Low Cut | The list closes; the field shows Low Cut; the second knob's name changes from GAIN to SLOPE and shows 24 dB; the curve becomes a cut. **Tell me** if the knob's name doesn't change straight away |
| Y3 | Pick Notch, then Band Pass | The second knob shows "-" (no gain); a narrow dip, then a hump that keeps only the middle; Q changes the width |
| Y4 | Back to Bell | The gain it had before comes back (each band keeps its gain and its slope separately) |
| Y5 | Change a type while audio plays | A quick fade (~20 ms), no click |
| Y6 | Make Band 1 (Low Cut) a Bell, Band 8 a Low Shelf | Any band can be any type; the dots, the graph taps and the lane still work |
| 2 | Bell 2: Gain +12, then sweep FREQ | The curve's hump follows, the sound follows; no zipper or clicks |
| 3 | Bell 2 Q: 0.1 to 10 | Wide hill to a narrow spike |
| 4 | LOW CUT on, FREQ 200 Hz, SLOPE 6 / 12 / 24 / 48 dB | Low end goes; steeper each step; the curve's edge steepens; no click on a slope change |
| 5 | Low Cut Q up | A bump at the corner (resonance) |
| 6 | LOW SHELF / HIGH SHELF on, Gain +/- | The whole low / high end tilts |
| 7 | HIGH CUT on, FREQ 3 kHz | Dull, telephone-like top end |
| 8 | Tap a band's switch while audio plays | It fades in or out (no click); its light and name brighten or dim |
| 9 | MASTER -6 dB | Quieter; the curve drops 6 dB |
| 10 | BYPASS | The dry sound; the curve goes flat |
| 11 | PRESET menu: Flat, Vocal Clarity, Vocal Air, Warm Vocal, De-Mud, De-Ess, Telephone, Low Cut, Bass Boost, Bright Mix, Hum Notch | Each redraws the curve and sets every band, types included (De-Ess and Hum Notch use notches) |
| 12 | Q-Links: BANDS 1-4, BANDS 5-8, MASTER pages | One Q-Link column per band: Freq, Gain (or Slope), Q, Type (three clicks per type) |
| 13 | Turn a Q-Link fast while audio plays, watch the screen | The curve keeps up (a steady 10 redraws a second) and the screen stays responsive |
| 14 | THEME arrows | Grey, Classic, White, Silver; the display stays dark in every theme |
| 15 | Save project, reload | Every band (types too), master, bypass and theme come back. A project saved with 1.5.x opens with its bands as they were (default types); Q-Link or automation assignments made in 1.5.x need redoing (the parameter list changed) |
| 16 | 4+ instances while playing | No dropouts |
| 17 | **Track edit → automation**, turn the Q-Links | Each Q-Link moves its parameter and stays there (the toolchain's 2026-10-21 wrapper fix). Back on the plugin screen, picking a TYPE still renames the second knob straight away |

## Shapey 5-Band EQ

The same engine built with 5 bands (`vst5/`, uid `Sh5E`, `shapey_5band_eq.so`): Low Cut, Low Shelf, Bell, High Shelf, High Cut
by default, every band any type. A slimmer header gives the curve 172 px (the 8-band's is 130), and every band has its own lane
under the curve, so any band's dot can be dragged directly.

```bash
MV=~/mpc-vst-plugins
$MV/tools/test_port.sh vst5/vst.json                     # must print PASSED
g++ -O2 -std=gnu++11 -DSHAPEY_BANDS=5 -I$MV/wrapper -c src/engine.cpp -o /tmp/shapey5.o
gcc -O2 -I$MV/wrapper tests/test_lanes5.c /tmp/shapey5.o -lstdc++ -lm -o /tmp/shapey_lanes5 && /tmp/shapey_lanes5   # 0 failure(s)
$MV/tools/build_port.sh vst5/vst.json
cd vst5 && python3 $MV/tools/release.py --so build/shapey_5band_eq.so \
  --skin "build/skin/3DTHC - VST - Shapey 5-Band EQ" --entry build/pluginlist-entry.xml --version 1.0.0 -o ~/ShapeyEQ/dist
```
`tools/make_skin_art.py` and `tools/preview_demo.py` draw the 5-band version with `SHAPEY_BANDS=5` set.

| # | Do | Expect |
|---|----|--------|
| F1 | Insert Shapey 5-Band EQ next to Shapey EQ | Both are in the plugin list under their own names; both load |
| F2 | Look at the graph | Five coloured, numbered lanes under the curve; each switched-on band's dot on its own lane, a white ring on every lane |
| F3 | **Drag dot 2 along its lane, then dot 4** (without tapping anything else first) | Each band follows your finger and becomes the selected one (its column glows); the curve follows. **Tell me** if a lane drag moves the wrong band or jumps |
| F4 | Tap or drag on the curve | The last band you touched moves there (frequency and gain), as in Shapey EQ |
| F5 | High Cut (off) | Its lane shows the ring only, no dot; dragging it moves the frequency; switch it on and the dot appears |
| F6 | Band types, presets, master, theme, save/reload, Q-Links (BANDS 1-4, then BAND 5, MASTER) | As Shapey EQ's Y1-Y6 and 9-15 |
