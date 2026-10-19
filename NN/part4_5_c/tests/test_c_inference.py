"""Parts 4/5: the C network (from .txt and from .h) must match the Python network."""

import json

import pytest

from conftest import HAVE_C, run

pytestmark = pytest.mark.skipif(not HAVE_C, reason="needs make and cc")
ALL_INPUTS = [[(d >> b) & 1 for b in (3, 2, 1, 0)] for d in range(16)]


@pytest.mark.parametrize("program", ["test_txt", "test_header"])
def test_7seg_tests_pass(built, program):
    _, models, build = built
    args = [build / program] + ([models / "7seg.txt"] if program == "test_txt" else [])
    proc = run(args + [models / "7seg_trained_predictions.json"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "10/10 digits correct" in proc.stdout and "-> match" in proc.stdout


@pytest.mark.parametrize("program", ["nn_cli_txt", "nn_cli_h"])
def test_c_forward_matches_python(built, program):
    net, models, build = built
    for x in ALL_INPUTS:  # also the untrained codes 10-15
        bits = "".join(map(str, x))
        args = [build / program] + ([models / "7seg.txt"] if program == "nn_cli_txt" else []) + [bits]
        proc = run(args, check=True)
        data = json.loads(proc.stdout)
        assert data["output"] == pytest.approx(net.predict(x).tolist(), abs=1e-5)
        net.forward(x)
        hidden_z = [n.z for n in net.layers[0].neurons]
        assert [n["z"] for n in data["layers"][0]] == pytest.approx(hidden_z, abs=1e-4)


def test_txt_loader_rejects_incomplete_file(built, tmp_path):
    _, models, build = built
    lines = (models / "7seg.txt").read_text().splitlines()
    broken = tmp_path / "broken.txt"
    broken.write_text("\n".join(lines[:-1]) + "\n")  # last output neuron missing
    proc = run([build / "nn_cli_txt", broken, "0101"])
    assert proc.returncode != 0 and "neurons" in proc.stderr
