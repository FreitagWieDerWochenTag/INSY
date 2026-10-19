"""Web page engines: the WebAssembly builds of the C code and the ESP32 sketch must match the Python network.

Runs the modules in Node the same way the page calls them (web/tests/run_wasm.mjs).
Needs Node and a web build (web/build.sh or `make -C part4_5_c web`).
"""

import json
import shutil
import subprocess

import pytest

from nn import NeuralNetwork
from nn.datasets import SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS
from nn.paths import MODELS, ROOT

WASM = ROOT / "web" / "build" / "wasm"
pytestmark = pytest.mark.skipif(not (shutil.which("node") and (WASM / "esp32.js").exists()),
                                reason="needs node and the web build (web/build.sh)")
ALL_INPUTS = [[(d >> b) & 1 for b in (3, 2, 1, 0)] for d in range(16)]


@pytest.fixture(scope="module")
def results():
    proc = subprocess.run(["node", str(ROOT / "web" / "tests" / "run_wasm.mjs"), str(WASM), str(MODELS / "7seg.txt")],
                          check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


@pytest.mark.parametrize("engine", ["nn_txt", "nn_h"])
def test_c_wasm_matches_python(results, engine):
    net = NeuralNetwork.load(MODELS / "7seg.json")
    for x, data in zip(ALL_INPUTS, results[engine]):
        assert data["output"] == pytest.approx(net.predict(x).tolist(), abs=1e-5)


def test_esp32_wasm_drives_the_right_pins(results):
    esp = results["esp32"]
    assert esp["setup"] == [0] * 7
    for digit in range(10):
        assert esp["digits"][digit]["pins"] == SEVEN_SEG_TARGETS[digit]
        assert f"digit {digit} -> input {''.join(map(str, SEVEN_SEG_INPUTS[digit]))}" in esp["digits"][digit]["serial"]
    assert "ignored 'x'" in esp["digits"][10]["serial"]
