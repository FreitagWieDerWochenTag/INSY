"""Part 3: the same networks in TensorFlow/Keras, for the comparison with our implementation.

Separate from the `nn` package (Parts 1+2), so the from-scratch network works without TensorFlow installed.
The Keras model can start from the exact initial weights of one of our networks and is trained
on the same per-sample order, so the two implementations differ only in what we want to compare.
"""

import json
import os

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # hide TensorFlow's C++ start-up messages

import keras  # noqa: E402
import tensorflow as tf  # noqa: E402

from nn import NeuralNetwork  # noqa: E402

LOSSES = {
    # what Aufgabenstellung.pdf asks for: mean over the outputs -> gradient 2/n_out * diff
    "mse": lambda y, out: tf.reduce_mean(tf.square(out - y)),
    # the loss our backprop uses: 0.5 * sum(diff^2) -> gradient diff (see train_sample)
    "half_sse": lambda y, out: 0.5 * tf.reduce_sum(tf.square(out - y)),
}


def build_model(net):
    """Keras Sequential model with the same layer sizes, activation and weights as `net`."""
    model = keras.Sequential(
        [keras.Input((net.layer_sizes[0],))]
        + [keras.layers.Dense(n, activation=net.activation) for n in net.layer_sizes[1:]])
    for dense, layer in zip(model.layers, net.layers):
        kernel = np.array([n.weights for n in layer.neurons]).T  # Keras: (inputs, neurons)
        dense.set_weights([kernel, np.array([n.bias for n in layer.neurons])])
    return model


def sample_order(n_samples, epochs, seed):
    """Per-epoch shuffle order, identical to NeuralNetwork.train(shuffle=True, seed=seed)."""
    rng = np.random.default_rng(seed)
    return np.stack([rng.permutation(n_samples) for _ in range(epochs)]).astype(np.int32)


def train(model, inputs, targets, epochs=20000, learning_rate=0.1, loss="mse", seed=0):
    """Plain SGD, one sample per step, compiled into one TensorFlow graph.

    Returns the mean squared error of every epoch (same metric as NeuralNetwork.train).
    """
    x_all = tf.constant(inputs, tf.float32)
    y_all = tf.constant(targets, tf.float32)
    n = len(inputs)
    loss_fn = LOSSES[loss]
    optimizer = keras.optimizers.SGD(learning_rate=learning_rate)
    optimizer.build(model.trainable_variables)  # variables must exist before the graph loop
    order = tf.constant(sample_order(n, epochs, seed))

    @tf.function
    def run():
        history = tf.TensorArray(tf.float32, size=epochs)
        for epoch in tf.range(epochs):
            total = tf.constant(0.0)
            for step in tf.range(n):
                idx = order[epoch, step]
                x, y = x_all[idx][None], y_all[idx][None]
                with tf.GradientTape() as tape:
                    out = model(x, training=True)
                    value = loss_fn(y, out)
                grads = tape.gradient(value, model.trainable_variables)
                optimizer.apply_gradients(zip(grads, model.trainable_variables))
                total += tf.reduce_mean(tf.square(out - y))
            history = history.write(epoch, total / n)
        return history.stack()

    return run().numpy().astype(float).tolist()


def predict(model, inputs):
    return model(tf.constant(inputs, tf.float32)).numpy().astype(float)


def layer_values(model, inputs):
    """Pre-activation z and activation a of every neuron, computed by TensorFlow for one sample."""
    values = tf.constant([inputs], tf.float32)
    layers = []
    for dense in model.layers:
        z = tf.matmul(values, dense.kernel) + dense.bias
        values = dense(values)
        layers.append([{"z": float(zi), "a": float(ai)} for zi, ai in zip(z[0].numpy(), values[0].numpy())])
    return layers, values[0].numpy().astype(float).tolist()


def to_network(model, activation="sigmoid"):
    """Convert the Keras weights into our NeuralNetwork (e.g. to export them as JSON/TXT/.h)."""
    sizes = [model.layers[0].kernel.shape[0]] + [d.units for d in model.layers]
    net = NeuralNetwork(sizes, activation)
    for dense, layer in zip(model.layers, net.layers):
        kernel, bias = (v.numpy().astype(float) for v in (dense.kernel, dense.bias))
        for j, neuron in enumerate(layer.neurons):
            neuron.weights = kernel[:, j].copy()
            neuron.bias = float(bias[j])
    return net


def export_weights(model, path, activation="sigmoid"):
    """Write the Dense kernels and biases as JSON, in Keras layout (kernel = inputs x neurons).

    Only used by the web page, which rebuilds the same model in TensorFlow.js for the visualization.
    """
    layers = [{"units": d.units, "activation": activation,
               "kernel": d.kernel.numpy().astype(float).tolist(), "bias": d.bias.numpy().astype(float).tolist()}
              for d in model.layers]
    with open(path, "w") as f:
        json.dump({"input_size": int(model.layers[0].kernel.shape[0]), "layers": layers}, f)
