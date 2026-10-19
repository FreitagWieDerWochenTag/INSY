/* Command-line forward pass for the visualization server (viz/server.py).
 * Prints z and activation of every neuron as JSON, so the page can draw what the C code computed.
 *
 *   build/nn_cli_txt models/7seg.txt 0101    weights from the .txt export (Part 4)
 *   build/nn_cli_h 0101                      weights compiled in from 7seg_net.h (Part 5)
 */
#include <stdio.h>
#include <string.h>

#ifdef NN_FROM_HEADER
#include "7seg_net.h"
#include "nn_from_header.h"
#else
#include "nn.h"
#endif

int main(int argc, char **argv)
{
    Network net;
#ifdef NN_FROM_HEADER
    if (argc != 2) {
        fprintf(stderr, "usage: %s BITS\n", argv[0]);
        return 2;
    }
    const char *bits = argv[1];
    if (nn_init_from_header(&net) != 0)
        return 2;
#else
    if (argc != 3) {
        fprintf(stderr, "usage: %s MODEL.txt BITS\n", argv[0]);
        return 2;
    }
    const char *bits = argv[2];
    if (nn_load_txt(&net, argv[1]) != 0)
        return 2;
#endif
    int n_in = nn_num_inputs(&net);
    float inputs[64];
    if ((int)strlen(bits) != n_in || n_in > 64) {
        fprintf(stderr, "expected %d bits\n", n_in);
        nn_free(&net);
        return 2;
    }
    for (int i = 0; i < n_in; i++) {
        if (bits[i] != '0' && bits[i] != '1') {
            fprintf(stderr, "bits must be 0/1\n");
            nn_free(&net);
            return 2;
        }
        inputs[i] = (float)(bits[i] - '0');
    }

    const float *out = nn_forward(&net, inputs);
    printf("{\"layers\": [");
    for (int l = 0; l < net.n_layers - 1; l++) {
        printf("%s[", l ? ", " : "");
        for (int n = 0; n < net.layers[l].n_neurons; n++) {
            const Neuron *neuron = &net.layers[l].neurons[n];
            printf("%s{\"z\": %.9g, \"a\": %.9g}", n ? ", " : "", neuron->z, neuron->output);
        }
        printf("]");
    }
    printf("], \"output\": [");
    for (int s = 0; s < nn_num_outputs(&net); s++)
        printf("%s%.9g", s ? ", " : "", out[s]);
    printf("]}\n");
    nn_free(&net);
    return 0;
}
