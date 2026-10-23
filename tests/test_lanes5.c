/* Shapey 5-Band EQ: every band has its own lane. Its dot sits there, and a drag on it selects that band and glows on
 * that band's lane (grab = lane * 48 + place).
 *   g++ -DSHAPEY_BANDS=5 -c src/engine.cpp -o e5.o && gcc -I$MV/wrapper tests/test_lanes5.c e5.o -lstdc++ -lm -o t && ./t */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "engine.h"
int main(void) {
    const mpc_engine_t *e = mpc_engine(); void *p = e->create(NULL);
    int16_t in[256] = {0}, out[256]; char v[64]; int fails = 0;
    e->get_param(p, "sel", v, sizeof v); printf("starts with the Bell selected: sel %s (want 2)\n", v); fails += atoi(v) != 2;
    e->get_param(p, "b1_type_name", v, sizeof v); printf("band 1 is %s (want Low Cut)\n", v); fails += strcmp(v, "Low Cut") != 0;
    e->get_param(p, "b5_type_name", v, sizeof v); printf("band 5 is %s (want High Cut)\n", v); fails += strcmp(v, "High Cut") != 0;
    e->set_param(p, "b4_freq", "500"); e->process(p, in, out, 128);       /* a drag on lane 4 */
    e->get_param(p, "sel", v, sizeof v); printf("drag on lane 4 -> sel %s (want 3)\n", v); fails += atoi(v) != 3;
    e->get_param(p, "grab", v, sizeof v); printf("  glows on lane 4 at %s (want %d)\n", v, 3 * 48 + 25); fails += atoi(v) != 3 * 48 + 25;
    printf("%d failure(s)\n", fails); return fails;
}
