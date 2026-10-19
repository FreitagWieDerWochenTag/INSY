"""Glue between the web page and the unchanged `nn` package, run by Pyodide in py-worker.js.

Every value the Parts 1+2 page shows comes from these calls into the real NeuralNetwork class.
Arguments and results are JSON strings, so nothing is converted by hand on the JavaScript side.
"""

import json
import sys
import time

sys.path.insert(0, "/home/pyodide")

from nn import NeuralNetwork  # noqa: E402
from nn.datasets import SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS, XOR_INPUTS, XOR_TARGETS  # noqa: E402

DATASETS = {"xor": ([2, 2, 1], XOR_INPUTS, XOR_TARGETS), "7seg": ([4, 16, 7], SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS)}
nets = {}


def load(name, path):
    """NeuralNetwork.load() of an exported JSON file, like scripts verify_*.py."""
    nets[name] = NeuralNetwork.load(path)
    return json.dumps(nets[name].to_dict())


def forward(name, bits_json):
    """Forward pass; returns z and activation of every neuron (stored by Neuron.activate)."""
    net = nets[name]
    start = time.perf_counter()
    output = net.forward(json.loads(bits_json))
    elapsed_ms = (time.perf_counter() - start) * 1000
    layers = [[{"z": n.z, "a": n.output} for n in layer.neurons] for layer in net.layers]
    return json.dumps({"layers": layers, "output": output.tolist(), "compute_ms": elapsed_ms})


def predict_all(name, inputs_json):
    return json.dumps(nets[name].predict(json.loads(inputs_json)).tolist())


def train(name, dataset, epochs, learning_rate, seed, log_every, compare_to):
    """NeuralNetwork.train() exactly like train_xor.py / train_7seg.py; progress is printed every log_every epochs."""
    sizes, inputs, targets = DATASETS[dataset]
    net = NeuralNetwork(sizes, "sigmoid", seed=seed)
    start = time.perf_counter()
    history = net.train(inputs, targets, epochs=epochs, learning_rate=learning_rate, seed=seed, log_every=log_every)
    seconds = time.perf_counter() - start
    nets[name] = net
    result = {"history": history, "seconds": seconds, "net": net.to_dict(),
              "predictions": net.predict(inputs).tolist(), "targets": targets}
    if compare_to in nets:  # largest weight/bias difference to the exported model
        other = nets[compare_to]
        result["max_param_diff"] = max(
            max(abs(a.bias - b.bias), *(abs(wa - wb) for wa, wb in zip(a.weights, b.weights)))
            for la, lb in zip(net.layers, other.layers) for a, b in zip(la.neurons, lb.neurons))
    return json.dumps(result)
