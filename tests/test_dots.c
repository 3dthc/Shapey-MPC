/* Each band's numbered dot follows its frequency on the lane (48 places) and hides when the band is off.
 *   gcc -I$MV/wrapper tests/test_dots.c engine.o -lstdc++ -lm -o test_dots && ./test_dots */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "engine.h"
int main(void) {
    const mpc_engine_t *e = mpc_engine(); void *p = e->create(NULL);
    int16_t in[256] = {0}, out[256]; char v[32]; int fails = 0;
    e->set_param(p, "b4_freq", "500"); for (int i = 0; i < 60; ++i) e->process(p, in, out, 128);
    e->get_param(p, "dot_4", v, sizeof v); printf("Bell 2 at pos 500 -> dot %s (want 25)\n", v); fails += atoi(v) != 25;
    e->get_param(p, "dot_1", v, sizeof v); printf("Low Cut off -> dot %s (want 0)\n", v); fails += atoi(v) != 0;
    e->set_param(p, "b1_on", "1"); e->set_param(p, "b1_freq", "0"); for (int i = 0; i < 60; ++i) e->process(p, in, out, 128);
    e->get_param(p, "dot_1", v, sizeof v); printf("Low Cut on at 20 Hz -> dot %s (want 1)\n", v); fails += atoi(v) != 1;
    e->set_param(p, "b8_on", "1"); e->set_param(p, "b8_freq", "1000"); for (int i = 0; i < 60; ++i) e->process(p, in, out, 128);
    e->get_param(p, "dot_8", v, sizeof v); printf("High Cut at 20 kHz -> dot %s (want 48)\n", v); fails += atoi(v) != 48;
    /* touch feedback: a touch on graph column 30 lights it and the selected band's ring; both let go ~250 ms later */
    e->set_param(p, "c30", "40"); e->process(p, in, out, 128);
    e->get_param(p, "touch", v, sizeof v); printf("touch on column 30 -> touch %s (want 31)\n", v); fails += atoi(v) != 31;
    e->get_param(p, "grab", v, sizeof v); printf("  and the ring glows at %s (want > 0)\n", v); fails += atoi(v) <= 0;
    for (int i = 0; i < 100; ++i) e->process(p, in, out, 128);          /* ~290 ms */
    e->get_param(p, "touch", v, sizeof v); printf("finger lifted -> touch %s (want 0)\n", v); fails += atoi(v) != 0;
    e->get_param(p, "grab", v, sizeof v); printf("  ring glow %s (want 0)\n", v); fails += atoi(v) != 0;
    e->set_param(p, "b4_freq", "700"); e->process(p, in, out, 128);    /* a lane drag (or knob) on Bell 2: it is selected and glows */
    e->get_param(p, "grab", v, sizeof v); printf("lane drag -> ring glow at %s (want 34)\n", v); fails += atoi(v) != 34;
    e->get_param(p, "sel", v, sizeof v); printf("  and Bell 2 is the selected band: sel %s (want 3)\n", v); fails += atoi(v) != 3;
    printf("%d failure(s)\n", fails); return fails;
}
