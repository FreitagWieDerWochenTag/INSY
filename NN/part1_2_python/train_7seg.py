"""Part 2 Step 3: train the 4-bit BCD -> 7-segment decoder (4-16-7) and export it.

Run from anywhere: python NN/part1_2_python/train_7seg.py
"""

import json

from nn import NeuralNetwork
from nn.datasets import SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS
from nn.paths import MODELS

SEED = 0

net = NeuralNetwork([4, 16, 7], activation="sigmoid", seed=SEED)
history = net.train(SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS, epochs=20000, learning_rate=0.1,
                    seed=SEED, log_every=2000)

net.dump_json(MODELS / "7seg.json")
with open(MODELS / "7seg_trained_predictions.json", "w") as f:
    json.dump(net.predict(SEVEN_SEG_INPUTS).tolist(), f)  # reference for the import test
net.dump_txt(MODELS / "7seg.txt")
net.dump_initfile(MODELS / "7seg_net.h", prefix="NN")
print(f"\nfinal mse {history[-1]:.6f}")
print(f"exported to {MODELS}: 7seg.json, 7seg_trained_predictions.json, 7seg.txt, 7seg_net.h")
