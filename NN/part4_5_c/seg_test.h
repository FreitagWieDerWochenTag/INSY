/* Shared 7-segment test for Part 4 (test_txt.c) and Part 5 (test_header.c).
 *
 * Runs digits 0-9 through the network, compares the thresholded outputs with the expected
 * segments and, if given, with the predictions the Python model saved after training
 * (models/7seg_trained_predictions.json).
 */
#ifndef SEG_TEST_H
#define SEG_TEST_H

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "nn.h"

#define SEG_THRESHOLD 0.5f
#define SEG_TOLERANCE 1e-4  /* float in C vs float64 in Python */

/* Same table as nn/datasets.py: segments A-G per digit */
static const int SEG_TARGETS[10][7] = {
    {1, 1, 1, 1, 1, 1, 0}, {0, 1, 1, 0, 0, 0, 0}, {1, 1, 0, 1, 1, 0, 1}, {1, 1, 1, 1, 0, 0, 1},
    {0, 1, 1, 0, 0, 1, 1}, {1, 0, 1, 1, 0, 1, 1}, {1, 0, 1, 1, 1, 1, 1}, {1, 1, 1, 0, 0, 0, 0},
    {1, 1, 1, 1, 1, 1, 1}, {1, 1, 1, 1, 0, 1, 1},
};

/* Read the 10x7 numbers of a JSON array of arrays. Returns 0 on success. */
static int read_reference(const char *path, double ref[10][7])
{
    FILE *f = fopen(path, "r");
    if (!f)
        return -1;
    int count = 0, c;
    while (count < 70 && (c = fgetc(f)) != EOF) {
        if (c == '-' || c == '.' || (c >= '0' && c <= '9')) {
            ungetc(c, f);
            if (fscanf(f, "%lf", &ref[count / 7][count % 7]) != 1)
                break;
            count++;
        }
    }
    fclose(f);
    return count == 70 ? 0 : -1;
}

/* Returns 0 if all digits are correct (and match the reference within tolerance). */
static int run_7seg_test(Network *net, const char *source, const char *reference_path)
{
    if (nn_num_inputs(net) != 4 || nn_num_outputs(net) != 7) {
        fprintf(stderr, "expected a 4-x-7 network\n");
        return 1;
    }
    double ref[10][7];
    int have_ref = reference_path && read_reference(reference_path, ref) == 0;
    if (reference_path && !have_ref)
        fprintf(stderr, "warning: cannot read reference %s\n", reference_path);

    printf("Network from %s: %d layers (", source, net->n_layers);
    for (int l = 0; l < net->n_layers; l++)
        printf("%s%d", l ? "-" : "", net->sizes[l]);
    printf(")\n\nDigit  Input  Expected  Predicted  Max err  Status\n");

    int correct = 0;
    double max_ref_diff = 0.0;
    for (int d = 0; d < 10; d++) {
        float in[4] = {(float)((d >> 3) & 1), (float)((d >> 2) & 1), (float)((d >> 1) & 1), (float)(d & 1)};
        float out[7];
        nn_predict(net, in, out);
        int ok = 1;
        double max_err = 0.0;
        char want[8] = {0}, got[8] = {0};
        for (int s = 0; s < 7; s++) {
            int bit = out[s] >= SEG_THRESHOLD;
            want[s] = (char)('0' + SEG_TARGETS[d][s]);
            got[s] = (char)('0' + bit);
            ok &= bit == SEG_TARGETS[d][s];
            max_err = fmax(max_err, fabs(out[s] - SEG_TARGETS[d][s]));
            if (have_ref)
                max_ref_diff = fmax(max_ref_diff, fabs(out[s] - ref[d][s]));
        }
        correct += ok;
        printf("%5d  %d%d%d%d   %s   %s    %.4f   %s\n", d, (int)in[0], (int)in[1], (int)in[2], (int)in[3],
               want, got, max_err, ok ? "OK" : "FAIL");
    }

    int ref_ok = 1;
    if (have_ref) {
        ref_ok = max_ref_diff <= SEG_TOLERANCE;
        printf("\nMax difference to trained Python model: %.2e (tolerance %.0e) -> %s\n",
               max_ref_diff, SEG_TOLERANCE, ref_ok ? "match" : "MISMATCH");
    }
    printf("Accuracy: %d/10 digits correct (threshold %.1f)\n", correct, SEG_THRESHOLD);
    return correct == 10 && ref_ok ? 0 : 1;
}

#endif /* SEG_TEST_H */
