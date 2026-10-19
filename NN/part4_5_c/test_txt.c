/* Part 4: load the 7-segment net from the .txt export and test digits 0-9.
 *
 * Usage: build/test_txt [models/7seg.txt] [models/7seg_trained_predictions.json]
 */
#include "seg_test.h"

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : "../models/7seg.txt";
    const char *reference = argc > 2 ? argv[2] : NULL;
    Network net;
    if (nn_load_txt(&net, path) != 0)
        return 2;
    int result = run_7seg_test(&net, path, reference);
    nn_free(&net);
    return result;
}
