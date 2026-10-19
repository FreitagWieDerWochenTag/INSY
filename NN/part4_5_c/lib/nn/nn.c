#include "nn.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static float activate(nn_activation act, float z)
{
    switch (act) {
    case NN_TANH: return tanhf(z);
    case NN_RELU: return z > 0.0f ? z : 0.0f;
    default:      return 1.0f / (1.0f + expf(-z));
    }
}

int nn_parse_activation(const char *name, nn_activation *out)
{
    if (strcmp(name, "sigmoid") == 0) *out = NN_SIGMOID;
    else if (strcmp(name, "tanh") == 0) *out = NN_TANH;
    else if (strcmp(name, "relu") == 0) *out = NN_RELU;
    else return -1;
    return 0;
}

int nn_create(Network *net, int n_layers, const int *sizes, nn_activation activation)
{
    memset(net, 0, sizeof(*net));
    if (n_layers < 2 || n_layers > NN_MAX_LAYERS)
        return -1;
    net->n_layers = n_layers;
    net->activation = activation;
    for (int l = 0; l < n_layers; l++) {
        if (sizes[l] <= 0)
            return -1;
        net->sizes[l] = sizes[l];
    }
    for (int l = 0; l < n_layers - 1; l++) {
        Layer *layer = &net->layers[l];
        layer->n_neurons = sizes[l + 1];
        layer->neurons = calloc((size_t)layer->n_neurons, sizeof(Neuron));
        layer->outputs = calloc((size_t)layer->n_neurons, sizeof(float));
        if (!layer->neurons || !layer->outputs) {
            nn_free(net);
            return -1;
        }
        for (int n = 0; n < layer->n_neurons; n++) {
            Neuron *neuron = &layer->neurons[n];
            neuron->n_inputs = sizes[l];
            neuron->weights = calloc((size_t)sizes[l], sizeof(float));
            if (!neuron->weights) {
                nn_free(net);
                return -1;
            }
        }
    }
    return 0;
}

void nn_free(Network *net)
{
    for (int l = 0; l < net->n_layers - 1; l++) {
        Layer *layer = &net->layers[l];
        for (int n = 0; layer->neurons && n < layer->n_neurons; n++)
            free(layer->neurons[n].weights);
        free(layer->neurons);
        free(layer->outputs);
    }
    memset(net, 0, sizeof(*net));
}

int nn_load_txt(Network *net, const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) {
        fprintf(stderr, "nn_load_txt: cannot open %s\n", path);
        return -1;
    }
    char line[8192], word[32];
    int n_layers = 0, sizes[NN_MAX_LAYERS], have_sizes = 0, created = 0, loaded = 0, expected = 0;
    nn_activation act = NN_SIGMOID;

    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n')
            continue;
        if (sscanf(line, "layers %d", &n_layers) == 1) {
            if (n_layers < 2 || n_layers > NN_MAX_LAYERS)
                goto bad;
        } else if (strncmp(line, "sizes", 5) == 0) {
            char *p = line + 5;
            for (int l = 0; l < n_layers; l++)
                sizes[l] = (int)strtol(p, &p, 10);
            have_sizes = 1;
        } else if (sscanf(line, "activation %31s", word) == 1) {
            if (nn_parse_activation(word, &act) != 0)
                goto bad;
        } else if (strncmp(line, "layer ", 6) == 0) {
            if (!created) {
                if (!have_sizes || nn_create(net, n_layers, sizes, act) != 0)
                    goto bad;
                created = 1;
                for (int l = 1; l < n_layers; l++)
                    expected += sizes[l];
            }
            int li, ni, used;
            float bias;
            /* "layer L neuron N bias B weights W0 W1 ..." with L = 1 for the first hidden layer */
            if (sscanf(line, "layer %d neuron %d bias %f weights%n", &li, &ni, &bias, &used) != 3
                || li < 1 || li >= n_layers || ni < 0 || ni >= sizes[li])
                goto bad;
            Neuron *neuron = &net->layers[li - 1].neurons[ni];
            neuron->bias = bias;
            char *p = line + used, *end;
            for (int w = 0; w < neuron->n_inputs; w++, p = end) {
                neuron->weights[w] = strtof(p, &end);
                if (end == p)
                    goto bad;
            }
            loaded++;
        }
    }
    fclose(f);
    if (!created || loaded != expected) {
        fprintf(stderr, "nn_load_txt: %s has %d of %d neurons\n", path, loaded, expected);
        if (created)
            nn_free(net);
        return -1;
    }
    return 0;

bad:
    fprintf(stderr, "nn_load_txt: cannot parse %s near: %s", path, line);
    fclose(f);
    if (created)
        nn_free(net);
    return -1;
}

const float *nn_forward(Network *net, const float *inputs)
{
    const float *values = inputs;
    for (int l = 0; l < net->n_layers - 1; l++) {
        Layer *layer = &net->layers[l];
        for (int n = 0; n < layer->n_neurons; n++) {
            Neuron *neuron = &layer->neurons[n];
            float z = neuron->bias;
            for (int i = 0; i < neuron->n_inputs; i++)
                z += neuron->weights[i] * values[i];
            neuron->z = z;
            neuron->output = activate(net->activation, z);
            layer->outputs[n] = neuron->output;
        }
        values = layer->outputs;
    }
    return values;
}

void nn_predict(Network *net, const float *inputs, float *outputs)
{
    const float *result = nn_forward(net, inputs);
    memcpy(outputs, result, (size_t)nn_num_outputs(net) * sizeof(float));
}
