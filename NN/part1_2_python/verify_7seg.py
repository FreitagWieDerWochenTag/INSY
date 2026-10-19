"""Part 2 Step 4: load the 7-segment decoder from JSON and test digits 0-9.

Run from anywhere: python NN/part1_2_python/verify_7seg.py
"""

import json
import sys

import numpy as np

from nn import NeuralNetwork
from nn.datasets import SEGMENT_NAMES, SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS
from nn.paths import MODELS

THRESHOLD = 0.5


def render(segments):
    """ASCII picture of a 7-segment digit (segments = [A..G] as 0/1)."""
    a, b, c, d, e, f, g = segments
    return [" _ " if a else "   ",
            ("|" if f else " ") + ("_" if g else " ") + ("|" if b else " "),
            ("|" if e else " ") + ("_" if d else " ") + ("|" if c else " ")]


net = NeuralNetwork.load(MODELS / "7seg.json")
outputs = net.predict(SEVEN_SEG_INPUTS)

correct = 0
print(f"Digit  Input      Expected {SEGMENT_NAMES}  Predicted {SEGMENT_NAMES}  Max err  Status")
for digit, (x, t, y) in enumerate(zip(SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS, outputs)):
    bits = [int(v >= THRESHOLD) for v in y]
    good = bits == t
    correct += good
    max_err = max(abs(v - tv) for v, tv in zip(y, t))
    print(f"{digit:5d}  {''.join(map(str, x))}       {''.join(map(str, t))}          "
          f"{''.join(map(str, bits))}           {max_err:.4f}   {'OK' if good else 'FAIL'}")

print("\nRendered predictions:")
pictures = [render([int(v >= THRESHOLD) for v in y]) for y in outputs]
for row in range(3):
    print("  ".join(p[row] for p in pictures))

with open(MODELS / "7seg_trained_predictions.json") as f:
    trained = np.array(json.load(f))
roundtrip = np.allclose(outputs, trained, atol=1e-9)
print(f"\nMax difference to trained model: {np.max(np.abs(outputs - trained)):.2e}")
print(f"Import matches trained model: {roundtrip}")
print(f"Accuracy: {correct}/10 digits correct (threshold {THRESHOLD})")
sys.exit(0 if correct == 10 and roundtrip else 1)
