"""Shared fixture: a small trained net, exported and compiled into all C programs (Parts 4-6)."""

import json
import shutil
import subprocess

import numpy as np
import pytest

from nn import NeuralNetwork
from nn.datasets import SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS
from nn.paths import ROOT

HAVE_C = bool(shutil.which("make") and shutil.which("cc"))


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    """Train a small net, export it like part1_2_python/train_7seg.py and build all C programs against it."""
    models = tmp_path_factory.mktemp("models")
    net = NeuralNetwork([4, 16, 7], seed=0)
    net.train(SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS, epochs=3000, learning_rate=0.5, seed=0)
    assert np.all((net.predict(SEVEN_SEG_INPUTS) >= 0.5) == np.array(SEVEN_SEG_TARGETS))
    net.dump_txt(models / "7seg.txt")
    net.dump_initfile(models / "7seg_net.h")
    with open(models / "7seg_trained_predictions.json", "w") as f:
        json.dump(net.predict(SEVEN_SEG_INPUTS).tolist(), f)
    build = tmp_path_factory.mktemp("build")
    subprocess.run(["make", "-s", "-C", str(ROOT / "part4_5_c"), f"BUILD={build}", f"MODEL_DIR={models}", "all"],
                   check=True, capture_output=True, text=True)
    return net, models, build



def run(args, **kw):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, **kw)
