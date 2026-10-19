"""Feedforward neural network from scratch (Neuron -> Layer -> NeuralNetwork).

Implements Part 1 of Aufgabenstellung.pdf: forward pass, backpropagation with per-sample
gradient descent, and export/import as JSON, human-readable TXT and a C header (.h).
"""

import json
import re

import numpy as np


# Each activation is (function, derivative expressed through the neuron's output).
# Using the output keeps backprop simple: the neuron already stores it.
ACTIVATIONS = {
    "sigmoid": (lambda z: 1.0 / (1.0 + np.exp(-z)), lambda out: out * (1.0 - out)),
    "tanh": (np.tanh, lambda out: 1.0 - out * out),
    "relu": (lambda z: np.maximum(0.0, z), lambda out: 1.0 if out > 0 else 0.0),
}


class Neuron:
    """A single neuron: output = activation(dot(inputs, weights) + bias)."""

    def __init__(self, n_inputs, activation="sigmoid", rng=None, weights=None, bias=None):
        if activation not in ACTIVATIONS:
            raise ValueError(f"Unknown activation '{activation}', choose from {list(ACTIVATIONS)}")
        rng = rng if rng is not None else np.random.default_rng()
        self.activation = activation
        self.weights = (np.asarray(weights, dtype=float) if weights is not None
                        else rng.uniform(-1.0, 1.0, n_inputs))
        self.bias = float(bias) if bias is not None else float(rng.uniform(-1.0, 1.0))
        self.last_inputs = None
        self.z = None
        self.output = None

    def activate(self, inputs):
        """Compute and store the neuron's output for the given inputs.

        Keeps the inputs, the pre-activation z and the output (used by backprop and the visualization).
        """
        self.last_inputs = np.asarray(inputs, dtype=float)
        self.z = float(np.dot(self.last_inputs, self.weights) + self.bias)
        self.output = float(ACTIVATIONS[self.activation][0](self.z))
        return self.output

    def delta(self, error):
        """Local gradient dLoss/dz from the error dLoss/dOutput (chain rule through activation)."""
        return error * ACTIVATIONS[self.activation][1](self.output)

    def update(self, delta, learning_rate):
        """Gradient descent step: W -= alpha * dJ/dW, b -= alpha * dJ/db."""
        self.weights -= learning_rate * delta * self.last_inputs
        self.bias -= learning_rate * delta


class Layer:
    """A fully connected layer made of Neuron objects."""

    def __init__(self, n_inputs, n_neurons, activation="sigmoid", rng=None):
        self.neurons = [Neuron(n_inputs, activation, rng) for _ in range(n_neurons)]

    def forward(self, inputs):
        """Forward pass: output of every neuron in this layer."""
        return np.array([neuron.activate(inputs) for neuron in self.neurons])

    def backward(self, errors, learning_rate):
        """Backpropagate errors (dLoss/dOutput per neuron) and update weights.

        Returns the errors for the previous layer. They are computed with the weights *before*
        the update, as required by the chain rule.
        """
        deltas = [neuron.delta(err) for neuron, err in zip(self.neurons, errors)]
        prev_errors = sum(d * neuron.weights for d, neuron in zip(deltas, self.neurons))
        for neuron, d in zip(self.neurons, deltas):
            neuron.update(d, learning_rate)
        return prev_errors


class NeuralNetwork:
    """Feedforward network. layer_sizes = [inputs, hidden..., outputs], e.g. [4, 16, 7]."""

    def __init__(self, layer_sizes, activation="sigmoid", seed=None):
        if len(layer_sizes) < 2:
            raise ValueError("Need at least an input and an output size")
        self.layer_sizes = list(layer_sizes)
        self.activation = activation
        rng = np.random.default_rng(seed)
        self.layers = [Layer(n_in, n_out, activation, rng)
                       for n_in, n_out in zip(layer_sizes[:-1], layer_sizes[1:])]

    # ---------- inference ----------

    def forward(self, inputs):
        """Propagate inputs through all layers and return the output layer's activations."""
        values = np.asarray(inputs, dtype=float)
        for layer in self.layers:
            values = layer.forward(values)
        return values

    def predict(self, inputs):
        """Inference only: output for one sample, or a 2D array for a list of samples."""
        inputs = np.asarray(inputs, dtype=float)
        if inputs.ndim == 1:
            return self.forward(inputs)
        return np.array([self.forward(x) for x in inputs])

    # ---------- training ----------

    def train_sample(self, inputs, targets, learning_rate):
        """One forward + backward pass for a single sample. Returns its squared error."""
        diff = self.forward(inputs) - np.asarray(targets, dtype=float)
        errors = diff  # d(0.5 * sum(diff^2)) / dOutput
        for layer in reversed(self.layers):
            errors = layer.backward(errors, learning_rate)
        return float(np.mean(diff ** 2))

    def train(self, inputs, targets, epochs=20000, learning_rate=0.1, shuffle=True,
              seed=None, log_every=0):
        """Stochastic gradient descent over all samples for the given number of epochs.

        Returns the mean squared error of every epoch. Prints progress every `log_every` epochs.
        """
        inputs = np.asarray(inputs, dtype=float)
        targets = np.asarray(targets, dtype=float)
        rng = np.random.default_rng(seed)
        history = []
        for epoch in range(1, epochs + 1):
            order = rng.permutation(len(inputs)) if shuffle else range(len(inputs))
            loss = np.mean([self.train_sample(inputs[i], targets[i], learning_rate) for i in order])
            history.append(float(loss))
            if log_every and (epoch % log_every == 0 or epoch == 1):
                print(f"epoch {epoch:6d}  mse {loss:.6f}")
        return history

    # ---------- JSON ----------

    def to_dict(self):
        return {
            "layer_sizes": self.layer_sizes,
            "activation": self.activation,
            "layers": [{"neurons": [{"weights": n.weights.tolist(), "bias": n.bias}
                                    for n in layer.neurons]} for layer in self.layers],
        }

    def dump_json(self, path):
        """Export the network to a JSON file (full float precision, exact round-trip)."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data):
        net = cls(data["layer_sizes"], data.get("activation", "sigmoid"))
        for layer, layer_data in zip(net.layers, data["layers"]):
            layer.neurons = [Neuron(len(n["weights"]), net.activation,
                                    weights=n["weights"], bias=n["bias"])
                             for n in layer_data["neurons"]]
        return net

    @classmethod
    def load(cls, path):
        """Reconstruct a network from a JSON file written by dump_json()."""
        with open(path) as f:
            return cls.from_dict(json.load(f))

    # ---------- TXT ----------

    def dump_txt(self, path):
        """Export to a human-readable text file that a C program can parse with fscanf.

        Layer 1 is the first hidden layer (layer 0 would be the input layer, which has no weights).
        """
        lines = [
            "# Neural network export",
            f"layers {len(self.layer_sizes)}",
            "sizes " + " ".join(str(s) for s in self.layer_sizes),
            f"activation {self.activation}",
        ]
        for li, layer in enumerate(self.layers, start=1):
            lines.append(f"# layer {li}: {len(layer.neurons)} neurons, "
                         f"{self.layer_sizes[li - 1]} weights each")
            for ni, n in enumerate(layer.neurons):
                weights = " ".join(f"{w:.9g}" for w in n.weights)
                lines.append(f"layer {li} neuron {ni} bias {n.bias:.9g} weights {weights}")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")

    # ---------- C header ----------

    def dump_initfile(self, path, prefix="NN"):
        """Generate a C header with all layer sizes, weights and biases as constants.

        Contains NN_NUM_LAYERS, NN_LAYER_SIZES[], NN_L<k>_WEIGHTS[n][m], NN_L<k>_BIASES[n],
        pointer tables NN_WEIGHTS[] / NN_BIASES[] and nn_get_neuron() to initialize a C network.
        """
        p = prefix.upper()
        low = prefix.lower()
        guard = re.sub(r"\W", "_", f"{p}_NET_H").upper()
        n_weight_layers = len(self.layers)
        out = [
            "/* Auto-generated by neural_network.py - do not edit. */",
            f"#ifndef {guard}",
            f"#define {guard}",
            "",
            f"#define {p}_NUM_LAYERS {len(self.layer_sizes)}  /* including input layer */",
            f"#define {p}_NUM_INPUTS {self.layer_sizes[0]}",
            f"#define {p}_NUM_OUTPUTS {self.layer_sizes[-1]}",
            f"#define {p}_ACTIVATION_{self.activation.upper()} 1",
            "",
            f"static const int {p}_LAYER_SIZES[{p}_NUM_LAYERS] = "
            "{" + ", ".join(str(s) for s in self.layer_sizes) + "};",
            "",
        ]
        for li, layer in enumerate(self.layers, start=1):
            n_out, n_in = len(layer.neurons), self.layer_sizes[li - 1]
            out.append(f"/* layer {li}: {n_out} neurons x {n_in} inputs */")
            out.append(f"static const float {p}_L{li}_WEIGHTS[{n_out}][{n_in}] = {{")
            for n in layer.neurons:
                out.append("    {" + ", ".join(f"{w:.9g}f" for w in n.weights) + "},")
            out.append("};")
            out.append(f"static const float {p}_L{li}_BIASES[{n_out}] = {{")
            out.append("    " + ", ".join(f"{n.bias:.9g}f" for n in layer.neurons))
            out.append("};")
            out.append("")
        out += [
            "/* Index k = weight layer (0 = first hidden layer). */",
            f"static const float *const {p}_WEIGHTS[{n_weight_layers}] = {{"
            + ", ".join(f"&{p}_L{i}_WEIGHTS[0][0]" for i in range(1, n_weight_layers + 1)) + "};",
            f"static const float *const {p}_BIASES[{n_weight_layers}] = {{"
            + ", ".join(f"{p}_L{i}_BIASES" for i in range(1, n_weight_layers + 1)) + "};",
            "",
            "/* Fetch weights (length = size of previous layer) and bias of one neuron. */",
            f"static inline void {low}_get_neuron(int layer, int neuron,",
            "                                  const float **weights, float *bias)",
            "{",
            f"    int n_in = {p}_LAYER_SIZES[layer];",
            f"    *weights = {p}_WEIGHTS[layer] + neuron * n_in;",
            f"    *bias = {p}_BIASES[layer][neuron];",
            "}",
            "",
            f"#endif /* {guard} */",
        ]
        with open(path, "w") as f:
            f.write("\n".join(out) + "\n")
