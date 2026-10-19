"""Part 6: the unchanged ESP32 sketch, built for the PC against the Arduino mock, drives the right pins."""

import pytest

from conftest import HAVE_C, run
from nn.datasets import SEVEN_SEG_INPUTS, SEVEN_SEG_TARGETS

pytestmark = pytest.mark.skipif(not HAVE_C, reason="needs make and cc")


def test_esp32_sketch_drives_the_right_pins(built):
    net, _, build = built
    proc = run([build / "esp32_sim"], input="0123456789x\n", check=True)
    gpio = [dict(map(int, kv.split("=")) for kv in line.split()[1:])
            for line in proc.stdout.splitlines() if line.startswith("#GPIO")]
    pins = [0, 4, 16, 17, 5, 18, 19]  # segments A-G, wiring table of the PDF
    assert all(level == 0 for level in gpio[0].values())  # all segments off after setup()
    for digit in range(10):
        expected = (net.predict(SEVEN_SEG_INPUTS[digit]) >= 0.5).astype(int).tolist()
        assert [gpio[digit + 1][p] for p in pins] == expected == SEVEN_SEG_TARGETS[digit]
    assert "ignored 'x'" in proc.stdout
