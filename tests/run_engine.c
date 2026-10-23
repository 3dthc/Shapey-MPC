/* Offline harness: tests/run_engine in.f32 out.s16 [key=value | @block:key=value ...]
 * in.f32: mono float32 at 44.1 kHz (fed as stereo). Writes interleaved int16 stereo.
 * Prints the latency, then the 72 curve columns (0..60) and the 72 analyzer columns (0..24) as the screen would get them. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "engine.h"

static void apply(const mpc_engine_t *e, void *inst, const char *arg)
{
    char k[64]; const char *eq = strchr(arg, '=');
    if (!eq) return;
    snprintf(k, sizeof k, "%.*s", (int)(eq - arg), arg);
    e->set_param(inst, k, eq + 1);
}

int main(int argc, char **argv)
{
    if (argc < 3) { fprintf(stderr, "usage: %s in.f32 out.s16 [key=value ...]\n", argv[0]); return 2; }
    FILE *fi = fopen(argv[1], "rb"), *fo = fopen(argv[2], "wb");
    if (!fi || !fo) { perror("open"); return 1; }
    const mpc_engine_t *e = mpc_engine();
    void *inst = e->create(NULL);
    for (int a = 3; a < argc; ++a) if (argv[a][0] != '@') apply(e, inst, argv[a]);
    float buf[128]; int16_t in[256], out[256]; size_t n;
    for (long blk = 0; (n = fread(buf, sizeof(float), 128, fi)) > 0; ++blk) {
        for (int a = 3; a < argc; ++a)
            if (argv[a][0] == '@' && atol(argv[a] + 1) == blk) apply(e, inst, strchr(argv[a], ':') + 1);
        for (size_t i = 0; i < 128; ++i) {
            float v = i < n ? buf[i] : 0.0f;
            int s = (int)(v * 32767.0f); if (s > 32767) s = 32767; if (s < -32768) s = -32768;
            in[2 * i] = in[2 * i + 1] = (int16_t)s;
        }
        e->process(inst, in, out, 128);
        fwrite(out, sizeof(int16_t), 256, fo);
    }
    char v[32]; e->get_param(inst, "latency", v, sizeof v);
    printf("%s\n", v);
    for (int c = 0; c < 72; ++c) { char k[8]; snprintf(k, sizeof k, "c%d", c); e->get_param(inst, k, v, sizeof v); printf("%d ", atoi(v)); }
    printf("\n");
    for (int k = 0; k < 72; ++k) { char key[8]; snprintf(key, sizeof key, "a%d", k); e->get_param(inst, key, v, sizeof v); printf("%d ", atoi(v)); }
    printf("\n");
    e->destroy(inst);
    fclose(fi); fclose(fo);
    return 0;
}
