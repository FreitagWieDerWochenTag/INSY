"""Part 2 Step 1: train XOR (2-2-1, 20000 epochs, alpha 0.1) and export the network.

Run from anywhere: python NN/part1_2_python/train_xor.py
"""

import json

from nn import NeuralNetwork
from nn.datasets import XOR_INPUTS, XOR_TARGETS
from nn.paths import MODELS

SEED = 0  # 2-2-1 XOR can get stuck in a local minimum (e.g. seed 2); seed 0 converges

net = NeuralNetwork([2, 2, 1], activation="sigmoid", seed=SEED)
history = net.train(XOR_INPUTS, XOR_TARGETS, epochs=20000, learning_rate=0.1, seed=SEED,
                    log_every=2000)

print("\nInput    Target  Output")
for x, t, y in zip(XOR_INPUTS, XOR_TARGETS, net.predict(XOR_INPUTS)):
    print(f"{x}  {t[0]}       {y[0]:.4f}")

net.dump_json(MODELS / "xor.json")
with open(MODELS / "xor_trained_predictions.json", "w") as f:
    json.dump(net.predict(XOR_INPUTS).tolist(), f)  # reference for the import test
net.dump_txt(MODELS / "xor.txt")
net.dump_initfile(MODELS / "xor_net.h", prefix="XOR")
print(f"\nfinal mse {history[-1]:.6f}")
print(f"exported to {MODELS}: xor.json, xor_trained_predictions.json, xor.txt, xor_net.h")
