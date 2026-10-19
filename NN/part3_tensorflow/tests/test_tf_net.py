"""Part 3: the Keras model must compute the same as our network when given the same weights."""

import numpy as np
import pytest

pytest.importorskip("tensorflow")

import tf_net  # noqa: E402
from nn import NeuralNetwork  # noqa: E402
from nn.datasets import SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS, XOR_INPUTS, XOR_TARGETS  # noqa: E402


def test_same_weights_same_forward_pass():
    net = NeuralNetwork([4, 16, 7], seed=3)
    model = tf_net.build_model(net)
    assert tf_net.predict(model, SEVEN_SEG_INPUTS) == pytest.approx(net.predict(SEVEN_SEG_INPUTS), abs=1e-6)
    layers, output = tf_net.layer_values(model, SEVEN_SEG_INPUTS[5])
    net.forward(SEVEN_SEG_INPUTS[5])
    assert [n["z"] for n in layers[0]] == pytest.approx([n.z for n in net.layers[0].neurons], abs=1e-5)
    assert output == pytest.approx(net.predict(SEVEN_SEG_INPUTS[5]).tolist(), abs=1e-6)


def test_our_loss_gives_the_same_training():
    net = NeuralNetwork([2, 2, 1], seed=0)
    model = tf_net.build_model(net)
    ours = net.train(XOR_INPUTS, XOR_TARGETS, epochs=200, learning_rate=0.1, seed=0)
    theirs = tf_net.train(model, XOR_INPUTS, XOR_TARGETS, epochs=200, learning_rate=0.1, loss="half_sse", seed=0)
    assert theirs == pytest.approx(ours, abs=1e-5)
    assert tf_net.predict(model, XOR_INPUTS) == pytest.approx(net.predict(XOR_INPUTS), abs=1e-5)


def test_sample_order_matches_our_shuffle():
    rng = np.random.default_rng(7)
    expected = [rng.permutation(10) for _ in range(3)]
    assert tf_net.sample_order(10, 3, seed=7).tolist() == [list(e) for e in expected]


def test_to_network_round_trip():
    net = NeuralNetwork([4, 16, 7], seed=1)
    back = tf_net.to_network(tf_net.build_model(net))
    assert back.layer_sizes == net.layer_sizes
    assert back.predict(SEVEN_SEG_INPUTS) == pytest.approx(net.predict(SEVEN_SEG_INPUTS), abs=1e-6)


def test_export_weights(tmp_path):
    import json
    net = NeuralNetwork([4, 16, 7], seed=1)
    tf_net.export_weights(tf_net.build_model(net), tmp_path / "w.json")
    data = json.loads((tmp_path / "w.json").read_text())
    assert data["input_size"] == 4 and [layer["units"] for layer in data["layers"]] == [16, 7]
    assert data["layers"][0]["kernel"][2][5] == pytest.approx(net.layers[0].neurons[5].weights[2], abs=1e-7)
