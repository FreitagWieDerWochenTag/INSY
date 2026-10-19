"""Unit tests for neural_network.py."""

import numpy as np
import pytest

from nn import ACTIVATIONS, NeuralNetwork, Neuron
from nn.datasets import SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS, XOR_INPUTS, XOR_TARGETS


def test_neuron_output_matches_formula():
    n = Neuron(2, weights=[0.5, -1.0], bias=0.25)
    z = 1.0 * 0.5 + 2.0 * -1.0 + 0.25
    assert n.activate([1.0, 2.0]) == pytest.approx(1 / (1 + np.exp(-z)))


def test_forward_shapes():
    net = NeuralNetwork([4, 16, 7], seed=1)
    assert net.forward([0, 1, 0, 1]).shape == (7,)
    assert net.predict(SEVEN_SEG_INPUTS).shape == (10, 7)


@pytest.mark.parametrize("activation", list(ACTIVATIONS))
def test_backprop_matches_numerical_gradient(activation):
    """One SGD step must equal -lr * numerical gradient of 0.5 * sum((y - t)^2)."""
    x, t, lr, eps = np.array([0.3, -0.7]), np.array([0.2, 0.9]), 1e-3, 1e-6
    net = NeuralNetwork([2, 3, 2], activation=activation, seed=3)

    def loss(n):
        return 0.5 * np.sum((n.forward(x) - t) ** 2)

    neuron = net.layers[0].neurons[1]
    numeric = []
    for i in range(len(neuron.weights)):
        neuron.weights[i] += eps
        plus = loss(net)
        neuron.weights[i] -= 2 * eps
        minus = loss(net)
        neuron.weights[i] += eps
        numeric.append((plus - minus) / (2 * eps))

    before = neuron.weights.copy()
    net.train_sample(x, t, lr)
    analytic = (before - neuron.weights) / lr
    assert analytic == pytest.approx(numeric, rel=1e-4, abs=1e-8)


def test_training_reduces_loss():
    net = NeuralNetwork([2, 2, 1], seed=0)
    history = net.train(XOR_INPUTS, XOR_TARGETS, epochs=500, learning_rate=0.5, seed=0)
    assert history[-1] < history[0]


def test_json_roundtrip_is_exact(tmp_path):
    net = NeuralNetwork([4, 16, 7], seed=2)
    net.train(SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS, epochs=20, seed=2)
    path = tmp_path / "net.json"
    net.dump_json(path)
    loaded = NeuralNetwork.load(path)
    assert loaded.layer_sizes == net.layer_sizes
    assert np.array_equal(loaded.predict(SEVEN_SEG_INPUTS), net.predict(SEVEN_SEG_INPUTS))


def test_txt_contains_all_parameters(tmp_path):
    net = NeuralNetwork([2, 2, 1], seed=0)
    path = tmp_path / "net.txt"
    net.dump_txt(path)
    lines = [l for l in path.read_text().splitlines() if l.startswith("layer ")]
    assert len(lines) == 3  # 2 hidden + 1 output neuron
    parts = lines[0].split()
    assert parts[4] == "bias" and float(parts[5]) == pytest.approx(net.layers[0].neurons[0].bias)
    weights = [float(w) for w in parts[7:]]
    assert weights == pytest.approx(net.layers[0].neurons[0].weights.tolist())


def test_header_declares_constants(tmp_path):
    net = NeuralNetwork([4, 16, 7], seed=0)
    path = tmp_path / "net.h"
    net.dump_initfile(path, prefix="NN")
    text = path.read_text()
    for token in ("#define NN_NUM_LAYERS 3", "NN_LAYER_SIZES[NN_NUM_LAYERS] = {4, 16, 7}",
                  "NN_L1_WEIGHTS[16][4]", "NN_L2_BIASES[7]", "nn_get_neuron"):
        assert token in text
