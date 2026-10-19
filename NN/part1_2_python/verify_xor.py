"""Part 2 Step 2: load the XOR network from JSON and verify it.

Run from anywhere: python NN/part1_2_python/verify_xor.py
"""

import json
import sys

import numpy as np

from nn import NeuralNetwork
from nn.datasets import XOR_INPUTS, XOR_TARGETS
from nn.paths import MODELS

TOLERANCE = 0.1

net = NeuralNetwork.load(MODELS / "xor.json")
outputs = net.predict(XOR_INPUTS)

ok = True
print("Input    Target  Output  Status")
for x, t, y in zip(XOR_INPUTS, XOR_TARGETS, outputs):
    good = abs(y[0] - t[0]) <= TOLERANCE
    ok &= good
    print(f"{x}  {t[0]}       {y[0]:.4f}  {'OK' if good else 'FAIL'}")

# The imported network must reproduce the predictions of the trained network
with open(MODELS / "xor_trained_predictions.json") as f:
    trained = np.array(json.load(f))
roundtrip = np.allclose(outputs, trained, atol=1e-9)
print(f"\nMax difference to trained model: {np.max(np.abs(outputs - trained)):.2e}")
print(f"Import matches trained model: {roundtrip}")
print(f"All outputs within {TOLERANCE} of target: {ok}")
sys.exit(0 if ok and roundtrip else 1)
