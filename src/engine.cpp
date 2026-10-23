/*
 * Shapey EQ -- a parametric EQ for MPC (3DTHC): a curve you shape by touch. One engine, two plugins:
 *   Shapey EQ (8 bands):        Low Cut, Low Shelf, Bell 1..4, High Shelf, High Cut   (SHAPEY_BANDS 8, the default)
 *   Shapey 5-Band EQ (5 bands): Low Cut, Low Shelf, Bell, High Shelf, High Cut        (SHAPEY_BANDS 5)
 * Those are each band's starting type: any band can be a Bell, Low/High Shelf, Low/High Cut, Notch or Band Pass.
 *
 * Every band is a cascade of biquads (RBJ cookbook), transposed direct form II, run on both channels. Zero latency.
 * Settings glide (about 20 ms) so a knob turn never zips or clicks; a band switched on or off fades in or out the same way.
 *
 * The screen's curve is 72 columns (filmstrip pictures, c0..c71): the engine works out the response at each column's
 * frequency and reports the columns through the wrapper's display_rev poll (values only, no screen rebuild), at most
 * ~7 times a second and only while something changes, since MPC's screen thread pays for every repaint.
 *
 * Parameters are in knob units (0..1000 for a frequency, 0..100 for Q, tenths of a dB for gain) and the engine maps
 * them: frequency is logarithmic 20 Hz .. 20 kHz, Q logarithmic 0.1 .. 10, so a knob turn feels even across the range.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <new>

extern "C" {
#include "engine.h"
}

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static const float SR = 44100.0f;
#ifndef SHAPEY_BANDS
#define SHAPEY_BANDS 8
#endif
static const int NB = SHAPEY_BANDS;            /* bands */
static const int MAXS = 4;                     /* biquad sections per band (48 dB/oct cut) */
static const int NCOL = 72;                    /* curve columns on screen */
static const float CURVE_DB = 18.0f;           /* the graph shows -18 .. +18 dB */
static const int CURVE_STEPS = 60;             /* frames per column: 0 = -18 dB .. 60 = +18 dB */
static const float F_LO = 20.0f, F_HI = 20000.0f;
static const int NDOT = 48;                    /* places a band's numbered dot can sit on its lane under the curve */
/* the 5-band version gives every band its own lane (the 8-band one shares one): grab then also says which lane */
static const bool LANES = NB < 8;
static const int DEF_SEL = NB < 8 ? NB / 2 : NB / 2 - 1;   /* selected at first: the middle bell (Bell / Bell 2) */
static const int TOUCH_HOLD = 86;              /* blocks (~250 ms) a touch glow stays after the finger's last move */
/* the analyzer: what you hear (after the EQ), as NBAR log-spaced columns behind the curve */
static const int NBAR = 72;                    /* one per curve column: a thin spectrum line behind the curve */
static const int FFT_N = 2048;
static const int BAR_STEPS = 24;               /* frames per column: 0 = nothing .. 24 = 0 dBFS, 2.5 dB a step */
static const float BAR_FLOOR = -60.0f;         /* dBFS at frame 0 */
static const int AN_BLOCKS = 34;               /* a new picture every 34 blocks (~99 ms): the wrapper shows engine-made changes
                                                * on a ~100 ms poll (display_rev), so this keeps pace with it -- a steady
                                                * 10 a second, the most that path gives without full screen rebuilds */

/* band types, in the TYPE selector's order */
enum { BELL, LOWSHELF, HIGHSHELF, LOWCUT, HIGHCUT, NOTCH, BANDPASS, NTYPES };
static const char *TYPE_NAMES[NTYPES] = {"Bell", "Low Shelf", "High Shelf", "Low Cut", "High Cut", "Notch", "Band Pass"};
#if SHAPEY_BANDS == 5
static const int DEF_TYPE[NB] = {LOWCUT, LOWSHELF, BELL, HIGHSHELF, HIGHCUT};
static const float DEF_HZ[NB] = {30, 100, 1000, 10000, 18000};
#else
static const int DEF_TYPE[NB] = {LOWCUT, LOWSHELF, BELL, BELL, BELL, BELL, HIGHSHELF, HIGHCUT};
static const float DEF_HZ[NB] = {30, 100, 250, 800, 2500, 6000, 10000, 18000};
#endif
static const int SLOPES[4] = {6, 12, 24, 48};
static bool has_gain(int t) { return t == BELL || t == LOWSHELF || t == HIGHSHELF; }
static bool is_cut(int t) { return t == LOWCUT || t == HIGHCUT; }

static float clampf(float x, float lo, float hi) { return x < lo ? lo : (x > hi ? hi : x); }
static float pos_to_hz(float p) { return F_LO * powf(F_HI / F_LO, clampf(p, 0, 1000) / 1000.0f); }
static float pos_to_q(float p) { return 0.1f * powf(100.0f, clampf(p, 0, 100) / 100.0f); }

struct Biquad {
    float b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
    float zl1 = 0, zl2 = 0, zr1 = 0, zr2 = 0;
};

struct Band {
    /* targets (knob units) */
    int on = 0;
    int type = BELL;
    int pending = -1;                          /* a new type waiting for the band to fade out (then it fades back in) */
    float pos = 500, gain = 0, qpos = 43;      /* qpos 43: Q 0.72 */
    int slope = 1;                             /* cuts: 6/12/24/48 dB per octave (kept while the band is another type) */
    /* gliding values (engine units) */
    float lf = 0, g = 0, lq = 0;               /* log2 Hz, dB, log2 Q */
    float mix = 0;                             /* 0 = band out, 1 = in */
    /* a cut runs all four slopes all the time and crossfades to the chosen one, so a slope change never clicks
     * (a filter switched in cold rings); other bands have one variant. Off bands keep running too, for the same reason */
    int nvar = 1;
    int nsec[4] = {1, 1, 1, 1};
    float w[4] = {1, 0, 0, 0};                 /* each variant's share of the output */
    Biquad s[4][MAXS];
    bool settled = false;
};

struct Shapey {
    Band b[NB];
    float master = 0, master_g = 1.0f;         /* target dB, gliding linear gain */
    int bypass = 0, theme = 0;
    float byp = 0;                             /* 0 = EQ, 1 = dry */
    int col[NCOL];                             /* curve frame per column */
    unsigned display_rev = 0;
    int curve_dirty = 1, curve_wait = 0;
    double last_step = -1.0;
    int theme_changed = 0;
    /* the touch graph: tap or drag on the curve moves the selected band there (x = frequency, y = gain) */
    int sel = DEF_SEL;                         /* selected band: Bell 2 (8 bands), Bell (5 bands) */
    int sel_changed = 0;
    int mark = 0;                              /* the selected band's frequency as a curve column + 1 (the marker line) */
    int dot[NB];                               /* each band's numbered dot on the lane: 1..NDOT at its frequency, 0 = off (hidden) */
    /* touch feedback: the graph column under the finger glows while it's down, and the selected band's ring glows while its
     * frequency is moving; each lets go TOUCH_HOLD blocks (~250 ms) after the last change */
    int touch = 0, touch_hold = 0;            /* glowing column + 1, 0 = none */
    int grab = 0, grab_hold = 0;              /* the glowing ring's place on the lane (1..NDOT; with LANES, + lane * NDOT), 0 = none */
    unsigned char col_touched[NCOL];           /* columns a touch moved on the host's side: report the engine's back */
    int band_changed[NB];                      /* bit 0 on, 1 freq, 2 gain: changed by a touch, to report */
    int pend_sel = -1;                         /* a band the host just changed (-2: several, e.g. a preset): selected next block */
    unsigned noise = 1;
    /* analyzer */
    int analyzer = 0;
    float an_buf[FFT_N];
    float fre[FFT_N], fim[FFT_N];              /* FFT work space (per instance: instances may run on different cores) */
    int an_pos = 0, an_wait = 0;
    float bar_db[NBAR];
    int bar[NBAR];
};

/* ---------- filters ---------- */

/* sections a band needs, and each one's design (kind, Q) -- shared by the audio and the curve */
struct Section { int type; float q; };  /* 0 peak, 1 low shelf, 2 high shelf, 3 HP2, 4 LP2, 5 HP1, 6 LP1, 7 notch, 8 band pass */

static int sections(int kind, int slope, float q, Section *out)
{
    switch (kind) {
    case BELL: out[0] = {0, q}; return 1;
    case LOWSHELF: out[0] = {1, q}; return 1;
    case HIGHSHELF: out[0] = {2, q}; return 1;
    case NOTCH: out[0] = {7, q}; return 1;
    case BANDPASS: out[0] = {8, q}; return 1;
    default: break;
    }
    bool hp = kind == LOWCUT;
    int order = SLOPES[slope] / 6;
    if (order == 1) { out[0] = {hp ? 5 : 6, 0.7071f}; return 1; }
    /* Butterworth sections; the band's Q sets the resonance of the last (sharpest) one, Q 0.71 = flat Butterworth */
    static const float BQ2[1] = {0.7071f}, BQ4[2] = {0.5412f, 1.3066f}, BQ8[4] = {0.5098f, 0.6013f, 0.9000f, 2.5629f};
    const float *bq = order == 2 ? BQ2 : order == 4 ? BQ4 : BQ8;
    int n = order / 2;
    for (int i = 0; i < n; ++i) out[i] = {hp ? 3 : 4, bq[i] * (i == n - 1 ? q / 0.7071f : 1.0f)};
    return n;
}

static void design(Biquad &f, const Section &s, float hz, float db)
{
    float w = 2.0f * (float)M_PI * clampf(hz, 10.0f, 0.49f * SR) / SR;
    float cw = cosf(w), sw = sinf(w), al = sw / (2.0f * s.q);
    float A = powf(10.0f, db / 40.0f);
    float b0, b1, b2, a0, a1, a2;
    switch (s.type) {
    case 0: b0 = 1 + al * A; b1 = -2 * cw; b2 = 1 - al * A; a0 = 1 + al / A; a1 = -2 * cw; a2 = 1 - al / A; break;
    case 1: {
        float sa = 2 * sqrtf(A) * al;
        b0 = A * ((A + 1) - (A - 1) * cw + sa); b1 = 2 * A * ((A - 1) - (A + 1) * cw); b2 = A * ((A + 1) - (A - 1) * cw - sa);
        a0 = (A + 1) + (A - 1) * cw + sa; a1 = -2 * ((A - 1) + (A + 1) * cw); a2 = (A + 1) + (A - 1) * cw - sa; break;
    }
    case 2: {
        float sa = 2 * sqrtf(A) * al;
        b0 = A * ((A + 1) + (A - 1) * cw + sa); b1 = -2 * A * ((A - 1) + (A + 1) * cw); b2 = A * ((A + 1) + (A - 1) * cw - sa);
        a0 = (A + 1) - (A - 1) * cw + sa; a1 = 2 * ((A - 1) - (A + 1) * cw); a2 = (A + 1) - (A - 1) * cw - sa; break;
    }
    case 3: b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = b0; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; break;
    case 4: b0 = (1 - cw) / 2; b1 = 1 - cw; b2 = b0; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; break;
    case 7: b0 = 1; b1 = -2 * cw; b2 = 1; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; break;           /* notch */
    case 8: b0 = al; b1 = 0; b2 = -al; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; break;               /* band pass, 0 dB peak */
    default: {                                   /* first order (bilinear), 6 dB/oct */
        float k = tanf(w / 2);
        if (s.type == 5) { b0 = 1; b1 = -1; } else { b0 = k; b1 = k; }
        b2 = 0; a0 = k + 1; a1 = k - 1; a2 = 0; break;
    }
    }
    f.b0 = b0 / a0; f.b1 = b1 / a0; f.b2 = b2 / a0; f.a1 = a1 / a0; f.a2 = a2 / a0;
}

/* |H| in dB of a whole band at hz, from its target settings (for the curve) */
static float band_db(const Band &b, float hz)
{
    int kind = b.pending >= 0 ? b.pending : b.type;
    Section sec[MAXS];
    float fhz = pos_to_hz(b.pos), q = pos_to_q(b.qpos);
    int n = sections(kind, b.slope, q, sec);
    double w = 2.0 * M_PI * hz / SR, total = 0.0;
    double c1 = cos(w), s1 = sin(w), c2 = cos(2 * w), s2 = sin(2 * w);
    for (int i = 0; i < n; ++i) {
        Biquad f;
        design(f, sec[i], fhz, b.gain / 10.0f);
        double nr = f.b0 + f.b1 * c1 + f.b2 * c2, ni = -(f.b1 * s1 + f.b2 * s2);
        double dr = 1.0 + f.a1 * c1 + f.a2 * c2, di = -(f.a1 * s1 + f.a2 * s2);
        double m = (nr * nr + ni * ni) / fmax(dr * dr + di * di, 1e-30);
        total += 10.0 * log10(fmax(m, 1e-30));
    }
    return (float)total;
}

static float column_hz(int c) { return F_LO * powf(F_HI / F_LO, (c + 0.5f) / NCOL); }

static void update_curve(Shapey *p)
{
    bool moved = false;
    for (int c = 0; c < NCOL; ++c) {
        float hz = column_hz(c), db = p->master;
        for (int i = 0; i < NB; ++i)
            if (p->b[i].on) db += band_db(p->b[i], hz);
        if (p->bypass) db = 0.0f;
        int v = (int)lrintf((clampf(db, -CURVE_DB, CURVE_DB) + CURVE_DB) / (2 * CURVE_DB) * CURVE_STEPS);
        if (v != p->col[c]) { p->col[c] = v; moved = true; }
    }
    for (int i = 0; i < NB; ++i) {
        int d = p->b[i].on ? (int)(NDOT * clampf(p->b[i].pos, 0, 999.9f) / 1000.0f) + 1 : 0;
        if (d != p->dot[i]) { p->dot[i] = d; moved = true; }
    }
    int b = p->sel, m = (int)(NCOL * clampf(p->b[b].pos, 0, 999.9f) / 1000.0f) + 1;
    if (m != p->mark) { p->mark = m; moved = true; }
    if (moved) ++p->display_rev;
}

/* ---------- engine ---------- */

static void band_defaults(Band &b, int i)
{
    b.type = DEF_TYPE[i];
    b.pos = lrintf(1000.0f * logf(DEF_HZ[i] / F_LO) / logf(F_HI / F_LO));
    b.gain = 0;
    b.qpos = b.type == BELL ? 50 : 43;           /* bells Q 1.0, the rest 0.72 */
    b.slope = 2;                                 /* 24 dB/oct */
    b.on = b.type == BELL ? 1 : 0;               /* bells on at 0 dB (flat), the rest off */
}

static void glide(Band &b, float k);

/* a band's filters for its (new) type: cuts run all four slopes (crossfaded), the rest one; cleared, designed at once */
static void set_type(Band &b, int t)
{
    b.type = t;
    b.pending = -1;
    b.nvar = is_cut(t) ? 4 : 1;
    for (int v = 0; v < 4; ++v) {
        b.w[v] = b.nvar > 1 ? (v == b.slope ? 1.0f : 0.0f) : (v == 0 ? 1.0f : 0.0f);
        for (int i = 0; i < MAXS; ++i) b.s[v][i] = Biquad();
    }
    b.settled = false;
    glide(b, 1.0f);
}

static void *create(const char *)
{
    Shapey *p = new (std::nothrow) Shapey();
    if (!p) return NULL;
    for (int i = 0; i < NB; ++i) {
        Band &b = p->b[i];
        band_defaults(b, i);
        b.lf = log2f(pos_to_hz(b.pos)); b.g = b.gain / 10.0f; b.lq = log2f(pos_to_q(b.qpos));
        b.mix = b.on ? 1.0f : 0.0f;
        set_type(b, b.type);
    }
    for (int c = 0; c < NCOL; ++c) { p->col[c] = -1; p->col_touched[c] = 0; }
    for (int i = 0; i < NB; ++i) { p->band_changed[i] = 0; p->dot[i] = -1; }
    for (int k = 0; k < NBAR; ++k) { p->bar_db[k] = BAR_FLOOR - 20; p->bar[k] = 0; }
    memset(p->an_buf, 0, sizeof p->an_buf);
    update_curve(p);
    return p;
}

static void destroy(void *inst) { delete static_cast<Shapey *>(inst); }

static int band_key(const char *key, const char **field)
{
    if (key[0] != 'b' || key[1] < '1' || key[1] > '0' + NB || key[2] != '_') return -1;
    *field = key + 3;
    return key[1] - '1';
}

static void set_param(void *inst, const char *key, const char *val)
{
    Shapey *p = static_cast<Shapey *>(inst);
    if (!p || !key || !val) return;
    if (!strcmp(key, "state")) {
        /* "e3 nbands bypass theme master analyzer sel  then per band: on pos gain qpos slope type"
         * (e2: 8 bands, no type; e1: no analyzer, sel either -- older saves keep each band's starting type) */
        const char *s = val;
        int n = 0, bp, th, an = 0, sl = 3, nb = 8, ver = 3;
        float ms;
        if (sscanf(s, "e3 %d %d %d %f %d %d%n", &nb, &bp, &th, &ms, &an, &sl, &n) != 6) {
            ver = 2;
            if (sscanf(s, "e2 %d %d %f %d %d%n", &bp, &th, &ms, &an, &sl, &n) != 5) {
                ver = 1;
                if (sscanf(s, "e1 %d %d %f%n", &bp, &th, &ms, &n) != 3) return;
            }
        }
        if (nb != NB) return;                    /* a project saved with the other Shapey: not this one's */
        Band tmp[NB];
        s += n;
        for (int i = 0; i < NB; ++i) {
            int on, slp, ty = DEF_TYPE[i], k = 0;
            float ps, gn, qp;
            if (ver == 3 ? sscanf(s, " %d %f %f %f %d %d%n", &on, &ps, &gn, &qp, &slp, &ty, &k) != 6
                         : sscanf(s, " %d %f %f %f %d%n", &on, &ps, &gn, &qp, &slp, &k) != 5) return;
            s += k;
            tmp[i] = p->b[i];
            tmp[i].on = on ? 1 : 0; tmp[i].pos = clampf(ps, 0, 1000); tmp[i].gain = clampf(gn, -240, 240);
            tmp[i].qpos = clampf(qp, 0, 100); tmp[i].slope = slp >= 0 && slp <= 3 ? slp : 2;
            tmp[i].type = ty >= 0 && ty < NTYPES ? ty : DEF_TYPE[i];
        }
        for (int i = 0; i < NB; ++i) { p->b[i] = tmp[i]; set_type(p->b[i], p->b[i].type); p->b[i].mix = p->b[i].on ? 1.0f : 0.0f; }
        p->bypass = bp ? 1 : 0; p->theme = th >= 0 && th <= 3 ? th : 0; p->master = clampf(ms, -24, 24);
        p->analyzer = an ? 1 : 0; p->sel = sl >= 0 && sl < NB ? sl : DEF_SEL;
        p->curve_dirty = 1;
        return;
    }
    float f = strtof(val, NULL);
    const char *fld;
    int i = band_key(key, &fld);
    if (i >= 0) {
        Band &b = p->b[i];
        int t = b.pending >= 0 ? b.pending : b.type;
        if (!strcmp(fld, "on")) b.on = f > 0.5f;
        else if (!strcmp(fld, "freq")) {
            b.pos = clampf(f, 0, 1000);
            p->grab_hold = TOUCH_HOLD;                               /* the lane drag (or its knob): the dot glows */
        }
        else if (!strcmp(fld, "x")) {                                 /* the second knob: gain or slope, by type */
            if (has_gain(t)) b.gain = clampf(lrintf(f), 0, 480) - 240.0f;
            else if (is_cut(t)) b.slope = (int)clampf(f / 120.0f, 0, 3);
            else return;
        }
        else if (!strcmp(fld, "gain")) b.gain = clampf(f, -240, 240);
        else if (!strcmp(fld, "slope")) b.slope = (int)clampf((float)lrintf(f), 0, 3);
        else if (!strcmp(fld, "q")) b.qpos = clampf(f, 0, 100);
        else if (!strcmp(fld, "type")) {
            int nt = (int)clampf((float)lrintf(f), 0, NTYPES - 1);
            if (nt == t) return;
            if (b.mix <= 0.0f && !b.on) set_type(b, nt);            /* switched off: change at once */
            else b.pending = nt;                                     /* else fade out, change, fade back in (process) */
            p->band_changed[i] |= 4;                                 /* the second knob now means something else: re-report it */
        }
        else return;
        b.settled = false;
        p->curve_dirty = 1;
        /* touching a band's controls selects it (the graph then moves it); several bands at once is a preset: no */
        p->pend_sel = p->pend_sel == -1 || p->pend_sel == i ? i : -2;
        return;
    }
    if (!strcmp(key, "master")) { p->master = clampf(f, -24, 24); p->curve_dirty = 1; }
    else if (!strcmp(key, "bypass")) { p->bypass = f > 0.5f; p->curve_dirty = 1; }
    else if (!strcmp(key, "theme")) p->theme = (int)clampf((float)lrintf(f), 0, 3);
    else if (!strcmp(key, "theme_prev") || !strcmp(key, "theme_next")) {
        /* one step per press, at most ~3 a second (a held press must not race through) */
        if (f < 0.5f) return;
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC, &ts);
        double now = ts.tv_sec + ts.tv_nsec * 1e-9;
        if (p->last_step >= 0.0 && now - p->last_step < 0.3) return;
        p->last_step = now;
        p->theme = (p->theme + (key[6] == 'n' ? 1 : 3)) % 4;
        p->theme_changed = 1;
    }
    else if (!strcmp(key, "analyzer")) {
        if ((f > 0.5f) && !p->analyzer) memset(p->an_buf, 0, sizeof p->an_buf);   /* starts from silence, not stale audio */
        p->analyzer = f > 0.5f;
        if (!p->analyzer) {                          /* off: the bars drop away at once and stay still */
            bool moved = false;
            for (int k = 0; k < NBAR; ++k) { p->bar_db[k] = BAR_FLOOR - 20; if (p->bar[k]) { p->bar[k] = 0; moved = true; } }
            if (moved) ++p->display_rev;
        }
    }
    else if (!strcmp(key, "sel")) {
        int b = (int)clampf((float)lrintf(f), 0, NB - 1);
        if (b != p->sel) { p->sel = b; p->curve_dirty = 1; }
    }
    else if (!strncmp(key, "pick_", 5)) {          /* a band's name: select it for the touch graph */
        int b = atoi(key + 5) - 1;
        if (f > 0.5f && b >= 0 && b < NB && b != p->sel) { p->sel = b; p->sel_changed = 1; p->curve_dirty = 1; }
    }
    else if (key[0] == 'c' && key[1] >= '0' && key[1] <= '9') {
        /* a touch on the curve, column c at height f (0 = -18 dB .. 60 = +18 dB): the selected band goes there */
        int c = atoi(key + 1);
        if (c < 0 || c >= NCOL) return;
        Band &b = p->b[p->sel];
        b.pos = 1000.0f * (c + 0.5f) / NCOL;
        p->band_changed[p->sel] |= 2;
        if (has_gain(b.pending >= 0 ? b.pending : b.type)) {
            float db = clampf(f, 0, CURVE_STEPS) / CURVE_STEPS * 2 * CURVE_DB - CURVE_DB;
            b.gain = lrintf(db * 10.0f / 5.0f) * 5.0f;               /* half-dB steps */
            if (fabsf(b.gain) < 2.5f) b.gain = 0.0f;
            p->band_changed[p->sel] |= 4;
        }
        if (!b.on) { b.on = 1; p->band_changed[p->sel] |= 1; }   /* touching a switched-off band switches it on */
        b.settled = false;
        p->col_touched[c] = 1;
        if (p->touch != c + 1) { p->touch = c + 1; ++p->display_rev; }
        p->touch_hold = TOUCH_HOLD;
        p->grab_hold = TOUCH_HOLD;                                  /* the band's ring glows too: it moved */
        p->curve_dirty = 1;
        p->curve_wait = 0;                                          /* the curve follows the finger straight away */
    }
}

static int fmt_hz(char *buf, int len, float hz)
{
    if (hz >= 10000.0f) return snprintf(buf, (size_t)len, "%.1f kHz", hz / 1000.0f);
    if (hz >= 1000.0f) return snprintf(buf, (size_t)len, "%.2f kHz", hz / 1000.0f);
    return snprintf(buf, (size_t)len, "%d Hz", (int)lrintf(hz));
}

static int get_param(void *inst, const char *key, char *buf, int len)
{
    Shapey *p = static_cast<Shapey *>(inst);
    if (!p || !key || !buf || len <= 0) return 0;
    if (!strcmp(key, "state")) {
        int n = snprintf(buf, (size_t)len, "e3 %d %d %d %g %d %d", NB, p->bypass, p->theme, p->master, p->analyzer, p->sel);
        for (int i = 0; i < NB && n < len; ++i)
            n += snprintf(buf + n, (size_t)(len - n), " %d %g %g %g %d %d", p->b[i].on, p->b[i].pos, p->b[i].gain, p->b[i].qpos,
                          p->b[i].slope, p->b[i].pending >= 0 ? p->b[i].pending : p->b[i].type);
        return n < len ? n : 0;
    }
    if (!strcmp(key, "display_rev")) return snprintf(buf, (size_t)len, "%u", p->display_rev);
    if (!strcmp(key, "latency")) return snprintf(buf, (size_t)len, "0");
    if (key[0] == 'c' && key[1] >= '0' && key[1] <= '9') {
        int c = atoi(key + 1);
        if (c < 0 || c >= NCOL) return 0;
        /* a third of a step over the frame: lands on it whether MPC rounds or truncates */
        return snprintf(buf, (size_t)len, "%d.3", p->col[c] < 0 ? CURVE_STEPS / 2 : p->col[c]);
    }
    const char *fld;
    int i = band_key(key, &fld);
    if (i >= 0) {
        const Band &b = p->b[i];
        if (!strcmp(fld, "on")) return snprintf(buf, (size_t)len, "%d", b.on);
        if (!strcmp(fld, "freq")) return snprintf(buf, (size_t)len, "%g", b.pos);
        if (!strcmp(fld, "gain")) return snprintf(buf, (size_t)len, "%g", b.gain);
        if (!strcmp(fld, "q")) return snprintf(buf, (size_t)len, "%g", b.qpos);
        if (!strcmp(fld, "slope")) return snprintf(buf, (size_t)len, "%d", b.slope);
        int t = b.pending >= 0 ? b.pending : b.type;
        if (!strcmp(fld, "type")) return snprintf(buf, (size_t)len, "%d", t);
        if (!strcmp(fld, "x")) return snprintf(buf, (size_t)len, "%g", has_gain(t) ? b.gain + 240.0f : is_cut(t) ? b.slope * 120.0f + 60.0f : 240.0f);
        if (!strcmp(fld, "x_name")) return snprintf(buf, (size_t)len, "%s", has_gain(t) ? "GAIN" : is_cut(t) ? "SLOPE" : "-");
        if (!strcmp(fld, "x_display")) {
            if (has_gain(t)) return snprintf(buf, (size_t)len, "%+.1f dB", b.gain / 10.0f);
            if (is_cut(t)) return snprintf(buf, (size_t)len, "%d dB", SLOPES[b.slope]);
            return snprintf(buf, (size_t)len, "-");
        }
        if (!strcmp(fld, "type_name")) return snprintf(buf, (size_t)len, "%s", TYPE_NAMES[t]);
        /* the knobs' value text */
        if (!strcmp(fld, "freq_display")) return fmt_hz(buf, len, pos_to_hz(b.pos));
        if (!strcmp(fld, "gain_display")) return snprintf(buf, (size_t)len, "%+.1f dB", b.gain / 10.0f);
        if (!strcmp(fld, "q_display")) return snprintf(buf, (size_t)len, "%.2f", pos_to_q(b.qpos));
        return 0;
    }
    if (!strcmp(key, "master")) return snprintf(buf, (size_t)len, "%g", p->master);
    if (!strcmp(key, "master_display")) return snprintf(buf, (size_t)len, "%+.1f dB", p->master);
    if (!strcmp(key, "bypass")) return snprintf(buf, (size_t)len, "%d", p->bypass);
    if (!strcmp(key, "theme")) return snprintf(buf, (size_t)len, "%d", p->theme);
    if (!strcmp(key, "sel")) return snprintf(buf, (size_t)len, "%d", p->sel);
    if (!strcmp(key, "mark")) return snprintf(buf, (size_t)len, "%d", p->mark);
    if (!strcmp(key, "touch")) return snprintf(buf, (size_t)len, "%d", p->touch);
    if (!strcmp(key, "grab")) return snprintf(buf, (size_t)len, "%d", p->grab);
    if (!strncmp(key, "dot_", 4)) {
        int i = atoi(key + 4) - 1;
        return i >= 0 && i < NB ? snprintf(buf, (size_t)len, "%d", p->dot[i] < 0 ? 0 : p->dot[i]) : 0;
    }
    if (!strcmp(key, "analyzer")) return snprintf(buf, (size_t)len, "%d", p->analyzer);
    if (key[0] == 'a' && key[1] >= '0' && key[1] <= '9') {
        int k = atoi(key + 1);
        if (k < 0 || k >= NBAR) return 0;
        return snprintf(buf, (size_t)len, "%d.3", p->bar[k]);
    }
    return 0;
}

/* what the engine changed itself, so the screen follows: theme (arrows), the selected band (a name tapped), a band a touch
 * on the curve moved (its knobs follow), and the touched columns (the host's copy moved with the finger: put back) */
extern "C" int mpc_engine_changed(void *inst, char *key, int len)
{
    Shapey *p = static_cast<Shapey *>(inst);
    if (!p) return 0;
    if (p->theme_changed) { p->theme_changed = 0; snprintf(key, (size_t)len, "theme"); return 1; }
    if (p->sel_changed) { p->sel_changed = 0; snprintf(key, (size_t)len, "sel"); return 1; }
    for (int i = 0; i < NB; ++i)
        if (p->band_changed[i]) {
            int bit = p->band_changed[i] & 1 ? 1 : p->band_changed[i] & 2 ? 2 : 4;
            p->band_changed[i] &= ~bit;
            snprintf(key, (size_t)len, "b%d_%s", i + 1, bit == 1 ? "on" : bit == 2 ? "freq" : "x");
            return 1;
        }
    if (p->curve_dirty) return 0;                    /* touched columns: once the curve is redrawn */
    for (int c = 0; c < NCOL; ++c)
        if (p->col_touched[c]) { p->col_touched[c] = 0; snprintf(key, (size_t)len, "c%d", c); return 1; }
    return 0;
}

static void midi(void *, const uint8_t *, int) {}

static void render(void *, int16_t *out_lr, int frames)
{
    if (out_lr && frames > 0) memset(out_lr, 0, (size_t)frames * 2 * sizeof(int16_t));
}

static inline int16_t to_s16(float x)
{
    x *= 32768.0f;
    return x >= 32767.0f ? 32767 : (x <= -32768.0f ? -32768 : (int16_t)lrintf(x));
}

/* glide each band toward its targets and redesign its sections; returns once settled so idle bands cost nothing */
static void glide(Band &b, float k)
{
    int kind = b.type;
    float tlf = log2f(pos_to_hz(b.pos)), tg = b.gain / 10.0f, tlq = log2f(pos_to_q(b.qpos));
    if (b.settled) return;
    b.lf += (tlf - b.lf) * k; b.g += (tg - b.g) * k; b.lq += (tlq - b.lq) * k;
    if (fabsf(tlf - b.lf) < 1e-4f && fabsf(tg - b.g) < 1e-3f && fabsf(tlq - b.lq) < 1e-4f) {
        b.lf = tlf; b.g = tg; b.lq = tlq; b.settled = true;
    }
    Section sec[MAXS];
    for (int v = 0; v < b.nvar; ++v) {
        int n = sections(kind, b.nvar > 1 ? v : b.slope, exp2f(b.lq), sec);
        b.nsec[v] = n;
        for (int i = 0; i < n; ++i) design(b.s[v][i], sec[i], exp2f(b.lf), b.g);
    }
}

/* in-place radix-2 FFT (re, im of n = power of two) */
static void fft(float *re, float *im, int n)
{
    for (int i = 1, j = 0; i < n; ++i) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) { float t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
    }
    for (int len = 2; len <= n; len <<= 1) {
        float a = -2.0f * (float)M_PI / len, wr = cosf(a), wi = sinf(a);
        for (int i = 0; i < n; i += len) {
            float cr = 1.0f, ci = 0.0f;
            for (int j = 0; j < len / 2; ++j) {
                float ur = re[i + j], ui = im[i + j];
                float vr = re[i + j + len / 2] * cr - im[i + j + len / 2] * ci;
                float vi = re[i + j + len / 2] * ci + im[i + j + len / 2] * cr;
                re[i + j] = ur + vr; im[i + j] = ui + vi;
                re[i + j + len / 2] = ur - vr; im[i + j + len / 2] = ui - vi;
                float t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
            }
        }
    }
}

/* the last FFT_N samples -> NBAR levels; quick to rise, falling 2.5 dB a picture (~25 dB a second) so it glides down */
static void update_analyzer(Shapey *p)
{
    float *re = p->fre, *im = p->fim;
    for (int i = 0; i < FFT_N; ++i) {
        float w = 0.5f - 0.5f * cosf(2.0f * (float)M_PI * i / FFT_N);
        re[i] = p->an_buf[(p->an_pos + i) & (FFT_N - 1)] * w;
        im[i] = 0.0f;
    }
    fft(re, im, FFT_N);
    const float binhz = SR / FFT_N, norm = 4.0f / FFT_N;          /* a full-scale sine reads 0 dBFS (Hann gain 1/2) */
    bool moved = false;
    for (int k = 0; k < NBAR; ++k) {
        float f0 = F_LO * powf(F_HI / F_LO, (float)k / NBAR), f1 = F_LO * powf(F_HI / F_LO, (float)(k + 1) / NBAR);
        int b0 = (int)(f0 / binhz), b1 = (int)(f1 / binhz);
        if (b1 < b0 + 1) b1 = b0 + 1;
        float pw = 0.0f;
        for (int b = b0; b <= b1 && b < FFT_N / 2; ++b) pw = fmaxf(pw, re[b] * re[b] + im[b] * im[b]);   /* the bar's loudest bin */
        float db = 10.0f * log10f(pw * norm * norm + 1e-20f);
        p->bar_db[k] = db > p->bar_db[k] ? db : fmaxf(db, p->bar_db[k] - 2.5f);
        int v = (int)lrintf(clampf((p->bar_db[k] - BAR_FLOOR) / -BAR_FLOOR * BAR_STEPS, 0, BAR_STEPS));
        if (v != p->bar[k]) { p->bar[k] = v; moved = true; }
    }
    if (moved) ++p->display_rev;
}

static void process(void *inst, const int16_t *in_lr, int16_t *out_lr, int frames)
{
    Shapey *p = static_cast<Shapey *>(inst);
    if (!p || !in_lr || !out_lr || frames <= 0) return;

    /* the curve: worked out within ~9 ms of a change (it's cheap), so every ~100 ms display_rev poll shows where the finger
     * or knob is now -- a steady 10 redraws a second while things move, none while they don't */
    if (p->pend_sel >= 0 && p->pend_sel != p->sel) { p->sel = p->pend_sel; p->sel_changed = 1; p->curve_dirty = 1; }
    p->pend_sel = -1;
    if (p->touch_hold > 0 && --p->touch_hold == 0 && p->touch) { p->touch = 0; ++p->display_rev; }
    {
        int g = 0;
        if (p->grab_hold > 0) {
            --p->grab_hold;
            g = (int)(NDOT * clampf(p->b[p->sel].pos, 0, 999.9f) / 1000.0f) + 1;
            if (LANES) g += p->sel * NDOT;                          /* a lane per band: the glow goes on the band's own lane */
        }
        if (g != p->grab) { p->grab = g; ++p->display_rev; }
    }
    if (p->curve_wait > 0) --p->curve_wait;
    if (p->curve_dirty && p->curve_wait == 0) { p->curve_dirty = 0; p->curve_wait = 3; update_curve(p); }
    if (p->analyzer && ++p->an_wait >= AN_BLOCKS) { p->an_wait = 0; update_analyzer(p); }

    const int SUB = 8;                           /* coefficients follow the glide every 8 samples */
    const float k = 1.0f - expf(-(float)SUB / (0.02f * SR));          /* ~20 ms glide */
    const float fade = (float)SUB / (0.01f * SR);                      /* 10 ms band on/off fade */
    const float mg = powf(10.0f, p->master / 20.0f);
    const float byp_t = p->bypass ? 1.0f : 0.0f;

    for (int i0 = 0; i0 < frames; i0 += SUB) {
        int n = frames - i0 < SUB ? frames - i0 : SUB;
        float mix0[NB], w0[NB][4];
        for (int bi = 0; bi < NB; ++bi) {
            Band &b = p->b[bi];
            mix0[bi] = b.mix;
            for (int v = 0; v < 4; ++v) w0[bi][v] = b.w[v];
            float tm = b.on && b.pending < 0 ? 1.0f : 0.0f;                /* a type change fades the band out first */
            if (b.mix != tm) b.mix = fabsf(tm - b.mix) <= fade ? tm : b.mix + (tm > b.mix ? fade : -fade);
            if (b.pending >= 0 && b.mix <= 0.0f && mix0[bi] <= 0.0f) set_type(b, b.pending);   /* out: switch, fade back in */
            if (b.nvar > 1)
                for (int v = 0; v < 4; ++v) {
                    float tw = v == b.slope ? 1.0f : 0.0f;
                    if (b.w[v] != tw) b.w[v] = fabsf(tw - b.w[v]) <= fade ? tw : b.w[v] + (tw > b.w[v] ? fade : -fade);
                }
            glide(b, k);
        }
        float g0 = p->master_g, g1 = g0 + (mg - g0) * k;
        p->master_g = fabsf(g1 - mg) < 1e-5f ? mg : g1;
        float b0 = p->byp, b1v = fabsf(byp_t - b0) <= fade ? byp_t : b0 + (byp_t > b0 ? fade : -fade);
        p->byp = b1v;
        for (int j = 0; j < n; ++j) {
            int idx = 2 * (i0 + j);
            float dl = in_lr[idx] / 32768.0f, dr = in_lr[idx + 1] / 32768.0f;
            float t = (float)(j + 1) / n;                /* fades move every sample, not in steps */
            p->noise = p->noise * 1664525u + 1013904223u;
            float tiny = ((int)(p->noise >> 9) - (1 << 22)) * 1e-28f;     /* keeps the filters out of denormals */
            float l = dl + tiny, r = dr + tiny;
            for (int bi = 0; bi < NB; ++bi) {
                Band &b = p->b[bi];
                float fl = 0.0f, fr = 0.0f;
                for (int v = 0; v < b.nvar; ++v) {
                    float vl = l, vr = r;
                    for (int s = 0; s < b.nsec[v]; ++s) {
                        Biquad &q = b.s[v][s];
                        float yl = q.b0 * vl + q.zl1;
                        q.zl1 = q.b1 * vl - q.a1 * yl + q.zl2;
                        q.zl2 = q.b2 * vl - q.a2 * yl;
                        float yr = q.b0 * vr + q.zr1;
                        q.zr1 = q.b1 * vr - q.a1 * yr + q.zr2;
                        q.zr2 = q.b2 * vr - q.a2 * yr;
                        vl = yl; vr = yr;
                    }
                    float wv = b.nvar > 1 ? w0[bi][v] + (b.w[v] - w0[bi][v]) * t : 1.0f;
                    fl += vl * wv; fr += vr * wv;
                }
                float m = mix0[bi] + (b.mix - mix0[bi]) * t;
                if (m <= 0.0f) continue;
                if (m >= 1.0f) { l = fl; r = fr; }
                else { l += (fl - l) * m; r += (fr - r) * m; }
            }
            float gg = g0 + (p->master_g - g0) * t, by = b0 + (b1v - b0) * t;
            l *= gg; r *= gg;
            if (by >= 1.0f) { l = dl; r = dr; }
            else if (by > 0.0f) { l += (dl - l) * by; r += (dr - r) * by; }
            out_lr[idx] = to_s16(l);
            out_lr[idx + 1] = to_s16(r);
            if (p->analyzer) { p->an_buf[p->an_pos] = 0.5f * (l + r); p->an_pos = (p->an_pos + 1) & (FFT_N - 1); }
        }
    }
}

static const mpc_engine_t engine = {create, destroy, midi, set_param, get_param, render, process};

extern "C" const mpc_engine_t *mpc_engine(void) { return &engine; }
