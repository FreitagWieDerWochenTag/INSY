/* Part 5: initialize the 7-segment net from the generated header and test digits 0-9.
 * The weights are compiled in, so no file is read (except the optional reference).
 *
 * Usage: build/test_header [models/7seg_trained_predictions.json]
 */
#include "7seg_net.h"
#include "nn_from_header.h"
#include "seg_test.h"

int main(int argc, char **argv)
{
    Network net;
    if (nn_init_from_header(&net) != 0)
        return 2;
    int result = run_7seg_test(&net, "7seg_net.h", argc > 1 ? argv[1] : NULL);
    nn_free(&net);
    return result;
}
