/* Forward-only neural network in C (Parts 4-6 of Aufgabenstellung.pdf).
 *
 * Same structure as the Python version: Neuron -> Layer -> Network. No training, the weights
 * come either from the .txt export (nn_load_txt, Part 4) or from the generated header
 * (nn_init_from_header in nn_from_header.h, Part 5). Uses float so it runs fast on the ESP32.
 */
#ifndef NN_H
#define NN_H

#ifdef __cplusplus
extern "C" {
#endif

#define NN_MAX_LAYERS 8

typedef enum { NN_SIGMOID, NN_TANH, NN_RELU } nn_activation;

typedef struct {
    int n_inputs;
    float *weights;   /* n_inputs values */
    float bias;
    float z;          /* last pre-activation, kept for inspection */
    float output;     /* last activation */
} Neuron;

typedef struct {
    int n_neurons;
    Neuron *neurons;
    float *outputs;   /* outputs of all neurons, input of the next layer */
} Layer;

typedef struct {
    int n_layers;                   /* including the input layer, like NN_NUM_LAYERS */
    int sizes[NN_MAX_LAYERS];
    nn_activation activation;
    Layer layers[NN_MAX_LAYERS - 1]; /* layers[0] = first hidden layer */
} Network;

/* Allocate a network with the given layer sizes. Weights and biases start at 0. Returns 0 on success. */
int nn_create(Network *net, int n_layers, const int *sizes, nn_activation activation);
void nn_free(Network *net);

/* Parse "sigmoid" / "tanh" / "relu". Returns 0 on success. */
int nn_parse_activation(const char *name, nn_activation *out);

/* Part 4: build the network from the .txt export (format: see dump_txt in nn/neural_network.py).
 * Returns 0 on success, prints the reason to stderr otherwise. */
int nn_load_txt(Network *net, const char *path);

/* Propagate the inputs through all layers. Returns the output layer's activations
 * (owned by the network, valid until the next call). */
const float *nn_forward(Network *net, const float *inputs);

/* Copy the output layer's result into outputs (NN output size values). */
void nn_predict(Network *net, const float *inputs, float *outputs);

static inline int nn_num_inputs(const Network *net) { return net->sizes[0]; }
static inline int nn_num_outputs(const Network *net) { return net->sizes[net->n_layers - 1]; }

#ifdef __cplusplus
}
#endif

#endif /* NN_H */
