/* Desktop: the mouse on the graph ("xy" = "down|drag|up|wheel+|wheel- x y", x and y 0..1, top left 0 0) grabs the nearest
 * band's point and moves it anywhere: any frequency (not just a column's), gain in 0.1 dB; the wheel is its Q.
 *   g++ -c -I$MV/wrapper -Ivst/build src/engine.cpp -o engine.o; gcc -I$MV/wrapper tests/test_xy.c engine.o -lstdc++ -lm */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "engine.h"
static const mpc_engine_t *e; static void *p;
static double g(const char *k) { char v[64] = ""; e->get_param(p, k, v, sizeof v); return atof(v); }
static int fails;
#define CHECK(c, ...) do { printf((c) ? "ok   " : "FAIL "); printf(__VA_ARGS__); printf("\n"); fails += !(c); } while (0)
int main(void) {
    e = mpc_engine(); p = e->create(NULL);
    int16_t in[256] = {0}, out[256];
    char key[32];
    /* Bell 2 (band 4) sits at 800 Hz, 0 dB: its point is at x = pos/1000, y = 0.5 */
    double x4 = g("b4_freq") / 1000.0;
    e->set_param(p, "xy", "down 0.9 0.5");           /* far from every band: the selected one comes here */
    int sel0 = (int)g("sel");
    e->set_param(p, "xy", "up 0 0");
    char cmd[64];
    snprintf(cmd, sizeof cmd, "down %.4f 0.51", x4);    /* on Bell 2's point: it is grabbed */
    e->set_param(p, "xy", cmd);
    CHECK((int)g("sel") == 3, "a press on Bell 2's point selects it (sel %d, was %d)", (int)g("sel"), sel0);
    e->set_param(p, "xy", "drag 0.6137 0.25");         /* anywhere: between columns, and up */
    CHECK(fabs(g("b4_freq") - 613.7) < 0.01, "free frequency: pos %.2f (want 613.70, not a column's)", g("b4_freq"));
    CHECK(fabs(g("b4_x") - (240 + 90)) < 0.6, "gain follows: knob %g (want 330 = +9.0 dB)", g("b4_x"));
    e->set_param(p, "xy", "drag 0.6137 0.2531");
    CHECK(fabs(g("b4_x") - (240 + 89)) < 0.6, "0.1 dB steps: knob %g (want 329 = +8.9 dB)", g("b4_x"));
    double q0 = g("b4_q");
    e->set_param(p, "xy", "wheel+ 0.5 0.5"); e->set_param(p, "xy", "wheel+ 0.5 0.5");
    CHECK(g("b4_q") > q0, "wheel up: Q %g -> %g", q0, g("b4_q"));
    e->set_param(p, "xy", "up 0 0");
    e->set_param(p, "xy", "drag 0.1 0.1");             /* released: a stray drag moves nothing */
    CHECK(fabs(g("b4_freq") - 613.7) < 0.01, "after release, a drag does nothing");
    /* the host hears about the moves (its knobs follow) */
    int fq = 0, gx = 0, qq = 0;
    for (int k = 0; k < 64 && mpc_engine_changed(p, key, sizeof key) > 0; ++k) {
        fq |= !strcmp(key, "b4_freq"); gx |= !strcmp(key, "b4_x"); qq |= !strcmp(key, "b4_q");
    }
    CHECK(fq && gx && qq, "reported to the host: freq %d, gain %d, Q %d", fq, gx, qq);
    for (int i = 0; i < 40; ++i) e->process(p, in, out, 128);
    /* a cut: up and down does nothing to it, the wheel steps its slope */
    e->set_param(p, "b1_on", "1"); e->set_param(p, "b1_freq", "100");
    e->set_param(p, "xy", "down 0.1 0.5");
    CHECK((int)g("sel") == 0, "Low Cut grabbed at its point (sel %d)", (int)g("sel"));
    double sl = g("b1_x");
    e->set_param(p, "xy", "wheel+ 0.1 0.5");
    CHECK(g("b1_x") > sl, "wheel on a cut: slope %g -> %g", sl, g("b1_x"));
    e->set_param(p, "xy", "up 0 0");
    e->set_param(p, "xy", "nonsense");                 /* junk is ignored */
    printf("%d failure(s)\n", fails);
    e->destroy(p);
    return fails != 0;
}
