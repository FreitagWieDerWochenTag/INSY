"""Part 3: train XOR and the 7-segment decoder with TensorFlow and compare with our network.

All runs use the same architecture, epochs, learning rate, initial weights and sample order:
  ours      - the from-scratch Neuron/Layer/NeuralNetwork (loss 1/2 * sum(diff^2))
  tf_mse    - TensorFlow with Keras-style mean squared error, as the PDF asks
  tf_same   - TensorFlow with our loss, to check that both implementations compute the same thing

Writes models/tf_comparison.json (shown on the web page), the Keras models models/xor_tf.keras and
models/7seg_tf.keras (tf_mse variant) and their weights as models/*_tf_weights.json (for TF.js on the page).

Run from anywhere: python NN/part3_tensorflow/compare_tf.py (needs `pip install -e NN`)
"""

import json
import time

import numpy as np

from nn import NeuralNetwork
import tf_net
from nn.datasets import SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS, XOR_INPUTS, XOR_TARGETS
from nn.paths import MODELS

EPOCHS = 20000
LEARNING_RATE = 0.1
SEED = 0              # same seed as part1_2_python/train_*.py -> ours equals the exported models
THRESHOLD = 0.5
HISTORY_STEP = 20     # store every 20th epoch of the loss curve
CONVERGED = (0.01, 0.001)

DATASETS = {
    "xor": {"sizes": [2, 2, 1], "inputs": XOR_INPUTS, "targets": XOR_TARGETS},
    "7seg": {"sizes": [4, 16, 7], "inputs": SEVEN_SEG_INPUTS, "targets": SEVEN_SEG_TARGETS},
}
RUNS = {
    "ours": "From scratch (NumPy, per neuron)",
    "tf_mse": "TensorFlow, Keras MSE loss",
    "tf_same": "TensorFlow, our loss 1/2*sum(diff^2)",
}


def train_ours(sizes, inputs, targets):
    net = NeuralNetwork(sizes, "sigmoid", seed=SEED)
    start = time.perf_counter()
    history = net.train(inputs, targets, epochs=EPOCHS, learning_rate=LEARNING_RATE, seed=SEED)
    return net.predict(inputs), history, time.perf_counter() - start


def train_tf(sizes, inputs, targets, loss):
    model = tf_net.build_model(NeuralNetwork(sizes, "sigmoid", seed=SEED))  # same start weights
    start = time.perf_counter()  # includes building the TensorFlow graph
    history = tf_net.train(model, inputs, targets, epochs=EPOCHS, learning_rate=LEARNING_RATE,
                           loss=loss, seed=SEED)
    return tf_net.predict(model, inputs), history, time.perf_counter() - start, model


def summarize(predictions, history, seconds, targets):
    targets = np.asarray(targets, dtype=float)
    first_below = {str(t): next((e + 1 for e, v in enumerate(history) if v < t), None) for t in CONVERGED}
    correct = [bool(np.all((p >= THRESHOLD) == (t >= THRESHOLD))) for p, t in zip(predictions, targets)]
    return {
        "seconds": seconds,
        "final_mse": float(np.mean((predictions - targets) ** 2)),
        "max_abs_error": float(np.max(np.abs(predictions - targets))),
        "correct": sum(correct),
        "samples": len(targets),
        "epochs_to_mse": first_below,
        "predictions": predictions.tolist(),
        "history": history[::HISTORY_STEP] + [history[-1]],  # epochs: see history_epochs
    }


def main():
    results = {"epochs": EPOCHS, "learning_rate": LEARNING_RATE, "seed": SEED,
               "history_epochs": list(range(1, EPOCHS + 1, HISTORY_STEP)) + [EPOCHS], "runs": RUNS, "datasets": {}}
    for name, d in DATASETS.items():
        print(f"\n=== {name}  {'-'.join(map(str, d['sizes']))}  ({EPOCHS} epochs, lr {LEARNING_RATE}) ===")
        runs = {}
        pred, hist, secs = train_ours(d["sizes"], d["inputs"], d["targets"])
        runs["ours"] = summarize(pred, hist, secs, d["targets"])
        for key, loss in (("tf_mse", "mse"), ("tf_same", "half_sse")):
            pred, hist, secs, model = train_tf(d["sizes"], d["inputs"], d["targets"], loss)
            runs[key] = summarize(pred, hist, secs, d["targets"])
            if key == "tf_mse":
                model.save(MODELS / f"{name}_tf.keras")
                tf_net.export_weights(model, MODELS / f"{name}_tf_weights.json")  # for the web page (TF.js)

        ours = np.array(runs["ours"]["predictions"])
        for key, r in runs.items():
            r["max_diff_to_ours"] = float(np.max(np.abs(np.array(r["predictions"]) - ours)))

        print(f"{'run':<40}{'time':>9}{'final mse':>12}{'max err':>10}{'correct':>9}"
              f"{'mse<0.01':>10}{'mse<0.001':>11}{'vs ours':>10}")
        for key, r in runs.items():
            e = r["epochs_to_mse"]
            print(f"{RUNS[key]:<40}{r['seconds']:>8.2f}s{r['final_mse']:>12.2e}{r['max_abs_error']:>10.4f}"
                  f"{r['correct']:>6}/{r['samples']}{str(e['0.01']):>10}{str(e['0.001']):>11}"
                  f"{r['max_diff_to_ours']:>10.1e}")
        results["datasets"][name] = {"sizes": d["sizes"], "inputs": d["inputs"],
                                     "targets": d["targets"], "runs": runs}

    with open(MODELS / "tf_comparison.json", "w") as f:
        json.dump(results, f)
    print(f"\nwrote {MODELS / 'tf_comparison.json'}, xor_tf.keras, 7seg_tf.keras, *_tf_weights.json")


if __name__ == "__main__":
    main()
