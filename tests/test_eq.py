#!/usr/bin/env python3
"""Offline checks for Shapey EQ: white noise in, the response measured from the output, compared with what each
band should do (textbook targets, not the engine's own maths), plus the screen curve, bypass, and clicks.

    python3 tests/test_eq.py path/to/run_engine
"""
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

SR = 44100
HARNESS = sys.argv[1] if len(sys.argv) > 1 else "tests/run_engine"
failures = []


def check(name, ok, detail=""):
    print("%-56s %s  %s" % (name, "PASS" if ok else "FAIL", detail))
    if not ok:
        failures.append(name)


def hz_pos(hz):
    return round(1000 * math.log(hz / 20) / math.log(1000))


def q_pos(q):
    return round(100 * math.log(q / 0.1) / math.log(100))


def run(sig, *args, **params):
    with tempfile.TemporaryDirectory() as d:
        fi, fo = os.path.join(d, "in.f32"), os.path.join(d, "out.s16")
        sig.astype(np.float32).tofile(fi)
        out = subprocess.run([HARNESS, fi, fo] + ["%s=%s" % kv for kv in params.items()] + list(args),
                             check=True, capture_output=True, text=True).stdout.split("\n")
        y = np.fromfile(fo, dtype=np.int16).reshape(-1, 2).astype(np.float64) / 32768.0
    return y[:, 0], y[:, 1], [int(v) for v in out[1].split()]


def flat(**extra):
    """every band off: a clean slate for a single band test"""
    p = {"b%d_on" % i: 0 for i in range(1, 9)}
    p.update(extra)
    return p


NOISE = np.random.default_rng(7).normal(0, 0.05, 4 * SR)


def response(**params):
    """measured gain in dB vs frequency (transfer function from noise in -> out, after the glide has settled)"""
    l, r, curve = run(NOISE, **params)
    x, y = NOISE[SR:], l[SR:]
    n = 8192
    X = np.zeros(n // 2 + 1, complex); Y = np.zeros_like(X); P = np.zeros(n // 2 + 1)
    win = np.hanning(n)
    for s in range(0, len(x) - n, n // 2):
        a, b = np.fft.rfft(x[s:s + n] * win), np.fft.rfft(y[s:s + n] * win)
        Y += b * np.conj(a); P += np.abs(a) ** 2
    H = np.abs(Y) / np.maximum(P, 1e-20)
    f = np.fft.rfftfreq(n, 1 / SR)
    return f, 20 * np.log10(np.maximum(H, 1e-9)), curve, l, r


def at(f, db, hz):
    i = np.argmin(np.abs(f - hz))
    return float(np.mean(db[max(1, i - 2):i + 3]))


# 1. all flat (defaults: bells on at 0 dB): transparent
f, db, curve, l, r = response()
dev = np.max(np.abs(db[(f > 30) & (f < 18000)]))
check("defaults are flat (bells at 0 dB)", dev < 0.1, "max deviation %.3f dB" % dev)
check("screen curve is flat at 0 dB", all(c == 30 for c in curve), "columns %s" % sorted(set(curve)))
check("stereo channels match", np.max(np.abs(l - r)) < 1e-9)

# 2. a bell: +6 dB at 1 kHz, Q 1 -> +6 at 1 kHz, about +3 at the -3 dB points (Q 1: 0.62 / 1.62 kHz), 0 far away
f, db, curve, *_ = response(**flat(b4_on=1, b4_freq=hz_pos(1000), b4_gain=60, b4_q=q_pos(1.0)))
check("bell +6 dB at 1 kHz", abs(at(f, db, 1000) - 6) < 0.3, "%.2f dB" % at(f, db, 1000))
check("bell: about half the gain an octave-ish away (620 Hz)", 2.0 < at(f, db, 620) < 4.0, "%.2f dB" % at(f, db, 620))
check("bell leaves 100 Hz and 10 kHz alone", abs(at(f, db, 100)) < 0.3 and abs(at(f, db, 10000)) < 0.3,
      "%.2f / %.2f dB" % (at(f, db, 100), at(f, db, 10000)))
peak_col = max(range(72), key=lambda c: curve[c])
col_hz = 20 * 1000 ** ((peak_col + 0.5) / 72)
check("screen curve peaks over 1 kHz at +6 dB", 800 < col_hz < 1250 and abs(curve[peak_col] - 40) <= 1,
      "column %d (%.0f Hz) frame %d (want 40)" % (peak_col, col_hz, curve[peak_col]))

# 3. a narrower, deeper cut
f, db, *_ = response(**flat(b3_on=1, b3_freq=hz_pos(300), b3_gain=-120, b3_q=q_pos(4.0)))
check("bell -12 dB at 300 Hz, Q 4", abs(at(f, db, 300) + 12) < 0.6, "%.2f dB" % at(f, db, 300))
check("narrow: 600 Hz barely touched", abs(at(f, db, 600)) < 1.0, "%.2f dB" % at(f, db, 600))

# 4. shelves: half the gain at the corner, full gain well past it
f, db, *_ = response(**flat(b2_on=1, b2_freq=hz_pos(200), b2_gain=60, b2_q=q_pos(0.71)))
check("low shelf +6 dB: ~+3 at 200 Hz, ~+6 at 40 Hz, 0 at 4 kHz",
      abs(at(f, db, 200) - 3) < 0.6 and abs(at(f, db, 40) - 6) < 0.6 and abs(at(f, db, 4000)) < 0.3,
      "%.2f / %.2f / %.2f dB" % (at(f, db, 200), at(f, db, 40), at(f, db, 4000)))
f, db, *_ = response(**flat(b7_on=1, b7_freq=hz_pos(5000), b7_gain=-60, b7_q=q_pos(0.71)))
check("high shelf -6 dB: ~-3 at 5 kHz, ~-6 at 16 kHz, 0 at 300 Hz",
      abs(at(f, db, 5000) + 3) < 0.6 and abs(at(f, db, 16000) + 6) < 0.8 and abs(at(f, db, 300)) < 0.3,
      "%.2f / %.2f / %.2f dB" % (at(f, db, 5000), at(f, db, 16000), at(f, db, 300)))

# 5. cuts: -3 dB at the corner, then the slope per octave
for slope, per_oct in ((0, 6), (1, 12), (2, 24), (3, 48)):
    f, db, *_ = response(**flat(b1_on=1, b1_freq=hz_pos(200), b1_slope=slope, b1_q=q_pos(0.71)))
    corner, oct_down = at(f, db, 200), at(f, db, 50) - at(f, db, 100)
    check("low cut %d dB/oct at 200 Hz" % per_oct, abs(corner + 3) < 0.7 and abs(oct_down + per_oct) < per_oct * 0.2 + 1,
          "%.2f dB at 200 Hz, %.1f dB per octave below" % (corner, oct_down))
f, db, *_ = response(**flat(b8_on=1, b8_freq=hz_pos(2000), b8_slope=2, b8_q=q_pos(0.71)))
check("high cut 24 dB/oct at 2 kHz", abs(at(f, db, 2000) + 3) < 0.7 and abs(at(f, db, 8000) - at(f, db, 4000) + 24) < 6
      and abs(at(f, db, 300)) < 0.3, "%.2f dB at 2 kHz, %.1f dB 4->8 kHz" % (at(f, db, 2000), at(f, db, 8000) - at(f, db, 4000)))
f, db, *_ = response(**flat(b1_on=1, b1_freq=hz_pos(200), b1_slope=1, b1_q=q_pos(3.0)))
check("cut Q 3: a resonant bump at the corner", at(f, db, 200) > 5, "%.2f dB at 200 Hz" % at(f, db, 200))

# 6. master and bypass
f, db, *_ = response(master=-6)
check("master -6 dB", abs(np.median(db[(f > 50) & (f < 15000)]) + 6) < 0.1, "%.2f dB" % np.median(db[(f > 50) & (f < 15000)]))
l, r, curve = run(NOISE, bypass=1, master=12, b4_gain=120)
dry = np.trunc(NOISE.astype(np.float32) * np.float32(32767)) / 32768     # as the harness feeds it
diff = np.max(np.abs(l[SR:len(NOISE)] - dry[SR:]))
check("bypass is the dry signal", diff < 1e-6, "max diff %.2e" % diff)
check("bypass shows a flat curve", all(c == 30 for c in curve))

# 7. zero latency: an impulse comes out at sample 0
imp = np.zeros(SR // 2); imp[1000] = 0.5
l, *_ = run(imp)
check("zero latency (impulse in place)", int(np.argmax(np.abs(l))) == 1000, "peak at %d" % int(np.argmax(np.abs(l))))

# 8. no clicks: sweep a bell's gain and frequency, switch a band and the slope while a tone plays
t = np.arange(3 * SR) / SR
tone = 0.4 * np.sin(2 * np.pi * 220 * t).astype(np.float64)
l, *_ = run(tone, "@100:b4_gain=-240", "@200:b4_freq=%d" % hz_pos(220), "@300:b1_on=1", "@300:b1_freq=%d" % hz_pos(400),
            "@400:b1_slope=3", "@500:b4_on=0", "@600:master=-12",
            **flat(b4_on=1, b4_freq=hz_pos(1000), b4_gain=120))
d2 = np.abs(np.diff(l[:len(tone) - 300], 2))                 # (the file's own abrupt end excluded)
ref = np.max(np.abs(np.diff(tone, 2))) * 1.0
check("no clicks when knobs jump, bands switch, slopes change", np.max(d2) < 4 * ref,
      "max 2nd difference %.4f (tone's own %.4f)" % (np.max(d2), ref))

# 9. the touch graph: pick a band by its name, then a tap on the curve puts it there (x = frequency, y = gain)
def response_args(*args, **params):
    l, r, curve = run(NOISE, *args, **params)
    x, y = NOISE[SR:], l[SR:len(NOISE)]
    n = 8192
    Y = np.zeros(n // 2 + 1, complex); P = np.zeros(n // 2 + 1); win = np.hanning(n)
    for s in range(0, len(x) - n, n // 2):
        a, b = np.fft.rfft(x[s:s + n] * win), np.fft.rfft(y[s:s + n] * win)
        Y += b * np.conj(a); P += np.abs(a) ** 2
    return np.fft.rfftfreq(n, 1 / SR), 20 * np.log10(np.maximum(np.abs(Y) / np.maximum(P, 1e-20), 1e-9)), curve


col_hz = lambda c: 20 * 1000 ** ((c + 0.5) / 72)
f, db, curve = response_args("@10:pick_5=1", "@12:c40=50")              # Bell 3 to column 40, +12 dB
check("tap on the curve: Bell 3 lands there (%.0f Hz, +12 dB)" % col_hz(40), abs(at(f, db, col_hz(40)) - 12) < 0.5,
      "%.2f dB at %.0f Hz" % (at(f, db, col_hz(40)), col_hz(40)))
check("the curve shows the tapped point", abs(curve[40] - 50) <= 1, "column 40 at frame %d (want 50)" % curve[40])
f, db, curve = response_args("@10:pick_1=1", "@12:c20=55")                # Low Cut (off) to column 20: switched on, no gain
check("tap with a cut selected: it switches on at that frequency (-3 dB)", abs(at(f, db, col_hz(20)) + 3) < 0.8,
      "%.2f dB at %.0f Hz" % (at(f, db, col_hz(20)), col_hz(20)))
f, db, curve = response_args("@10:pick_4=1", "@12:c30=40", "@14:c30=45", "@16:c30=20")   # a drag: the last height wins
check("a drag up and down: the gain follows the finger (Bell 2, -6 dB)", abs(at(f, db, col_hz(30)) + 6) < 0.5,
      "%.2f dB at %.0f Hz" % (at(f, db, col_hz(30)), col_hz(30)))

# 10. the analyzer: a 1 kHz tone at -12 dBFS lights the bar over 1 kHz at -12 dB; off, nothing moves
def bars(sig, **params):
    with tempfile.TemporaryDirectory() as d:
        fi, fo = os.path.join(d, "in.f32"), os.path.join(d, "out.s16")
        sig.astype(np.float32).tofile(fi)
        out = subprocess.run([HARNESS, fi, fo] + ["%s=%s" % kv for kv in params.items()], check=True, capture_output=True, text=True).stdout
    return [int(v) for v in out.split("\n")[2].split()]


t = np.arange(2 * SR) / SR
tone1k = 10 ** (-12 / 20) * np.sin(2 * np.pi * 1000 * t)
bk = int(72 * math.log(1000 / 20) / math.log(1000))                # the column 1 kHz falls in
b = bars(tone1k, analyzer=1)
check("analyzer: 1 kHz at -12 dBFS lights its bar at about -12 dB", abs(b[bk] - 19) <= 1 and max(b) == b[bk],
      "bar %d = frame %d (want 19 = -12 dB); peak at bar %d" % (bk, b[bk], b.index(max(b))))
check("analyzer: far from 1 kHz stays low (< -45 dB)", max(b[:bk - 12] + b[bk + 13:]) <= 6, "highest elsewhere %d" % max(b[:bk - 12] + b[bk + 13:]))
b = bars(tone1k, analyzer=1, **flat(b4_on=1, b4_freq=hz_pos(1000), b4_gain=-120, b4_q=q_pos(1.0)))
check("analyzer shows the EQ'd sound (-12 dB bell at 1 kHz: bar drops 12 dB)", abs(b[bk] - 14) <= 1, "frame %d (want 14)" % b[bk])
b = bars(tone1k)
check("analyzer off: every bar at 0", max(b) == 0, "max %d" % max(b))

# 12. band types: any band can be any type; the second knob (x) is gain or slope by type, each kept separately
f, db, *_ = response(**flat(b4_on=1, b4_type=3, b4_freq=hz_pos(200), b4_x=300, b4_q=q_pos(0.71)))   # Low Cut, 24 dB
check("Bell 2 as a Low Cut: -3 dB at 200 Hz", abs(at(f, db, 200) + 3) < 0.5, "%.2f dB" % at(f, db, 200))
check("  and 24 dB an octave below", abs(at(f, db, 100) + 24) < 1.5, "%.2f dB at 100 Hz" % at(f, db, 100))
f, db, *_ = response(**flat(b2_on=1, b2_type=2, b2_freq=hz_pos(5000), b2_x=300, b2_q=q_pos(0.71)))  # High Shelf, +6
check("Low Shelf band as a High Shelf: +6 dB up top, 0 below", abs(at(f, db, 16000) - 6) < 0.5 and abs(at(f, db, 200)) < 0.3,
      "%.2f dB at 16 kHz, %.2f at 200 Hz" % (at(f, db, 16000), at(f, db, 200)))
f, db, *_ = response(**flat(b5_on=1, b5_type=5, b5_freq=hz_pos(1000), b5_q=q_pos(4.0)))                 # Notch
lo = float(np.min(db[(f > 900) & (f < 1100)]))
check("Notch at 1 kHz: deep at 1 kHz, untouched an octave away", lo < -20 and abs(at(f, db, 500)) < 0.5 and abs(at(f, db, 2000)) < 0.5,
      "%.1f dB at the notch, %.2f / %.2f dB at 500 Hz / 2 kHz" % (lo, at(f, db, 500), at(f, db, 2000)))
f, db, *_ = response(**flat(b6_on=1, b6_type=6, b6_freq=hz_pos(1000), b6_q=q_pos(2.0)))                 # Band Pass
check("Band Pass at 1 kHz: 0 dB there, falls away either side", abs(at(f, db, 1000)) < 0.5 and at(f, db, 100) < -12 and at(f, db, 10000) < -12,
      "%.2f dB at 1 kHz, %.1f / %.1f dB at 100 Hz / 10 kHz" % (at(f, db, 1000), at(f, db, 100), at(f, db, 10000)))
f, db, *_ = response_args("@20:b4_type=3", "@40:b4_x=420", "@60:b4_type=0",
                          **flat(b4_on=1, b4_freq=hz_pos(1000), b4_x=360, b4_q=q_pos(1.0)))           # Bell +12 -> cut -> Bell
check("a type change and back keeps the gain (+12 dB bell)", abs(at(f, db, 1000) - 12) < 0.5, "%.2f dB at 1 kHz" % at(f, db, 1000))
t = np.arange(3 * SR) / SR
tone = 0.1 * np.sin(2 * np.pi * 220 * t)                           # quiet: +12 dB on it must not clip
l, *_ = run(tone, "@100:b4_type=5", "@200:b4_type=3", "@300:b4_type=6", "@400:b4_type=1", "@500:b4_type=0",
            **flat(b4_on=1, b4_freq=hz_pos(220), b4_x=360))
d2 = np.abs(np.diff(l[:len(tone) - 300], 2))
ref = np.max(d2[60 * 128:95 * 128])                                    # the +12 dB tone's own, before any change
check("no clicks when a playing band changes type", np.max(d2) < 4 * ref, "max 2nd difference %.4f (the boosted tone's own %.4f)" % (np.max(d2), ref))

# 11. CPU: everything on, 48 dB cuts
import time
p = flat(**{"b%d_on" % i: 1 for i in range(1, 9)}, b1_slope=3, b8_slope=3, analyzer=1)
t0 = time.time(); run(np.random.default_rng(1).normal(0, .1, 20 * SR), **p); dt = time.time() - t0
check("CPU: 20 s of audio, all 8 bands, 48 dB cuts, analyzer on", dt < 2.0, "%.2f s (%.1f %% of real time, x86)" % (dt, 100 * dt / 20))

print("\n%d failure(s)" % len(failures))
sys.exit(1 if failures else 0)
