"""Cost and category logic of tools/token_usage.py, with made-up usage data."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from token_usage import (Call, build_tables, classify, cost, merge_follow_ups, project_of_call,  # noqa: E402
                         prompt_text, split_by_log, to_json)


def make_call(mode="auto", tools=(), model="claude-opus-5-5", **usage):
    return Call(model=model, mode=mode, usage=usage, tools=list(tools))


def test_cost_uses_opus_5_5_prices():
    call = make_call(input_tokens=1_000_000, output_tokens=1_000_000, cache_read_input_tokens=1_000_000,
                     cache_creation_input_tokens=2_000_000,
                     cache_creation={"ephemeral_5m_input_tokens": 1_000_000, "ephemeral_1h_input_tokens": 1_000_000})
    assert cost(call) == pytest.approx(4 + 20 + 0.20 + 5 + 8)


def test_cost_matches_cost_command_snapshot():
    # /cost showed $1.46 for: 560 input, 27.9k output, 1.8M cache read, 67.0k cache write (1h TTL)
    call = make_call(input_tokens=560, output_tokens=27_900, cache_read_input_tokens=1_800_000,
                     cache_creation_input_tokens=67_000, cache_creation={"ephemeral_1h_input_tokens": 67_000})
    assert cost(call) == pytest.approx(1.46, abs=0.01)


def test_unknown_model_has_no_price():
    assert cost(make_call(model="some-other-model", output_tokens=10)) is None


@pytest.mark.parametrize("call, expected", [
    (make_call(mode="plan", tools=[("Bash", {"command": "ls"})]), "Planning"),
    (make_call(tools=[("AskUserQuestion", {})]), "Planning"),
    (make_call(tools=[("Bash", {"command": ".venv/bin/python -m scripts.train_7seg"})]), "Training & testing"),
    (make_call(tools=[("Bash", {"command": ".venv/bin/pytest -q"})]), "Training & testing"),
    (make_call(tools=[("Edit", {"file_path": "/x/docs/PROMPT_LOG.md"})]), "Documentation"),
    (make_call(tools=[("Write", {"file_path": "/x/nn/neural_network.py"})]), "Implementation"),
    (make_call(tools=[("Read", {"file_path": "/x/docs/Aufgabenstellung.pdf"})]), "Research & context"),
    (make_call(), "Answers"),
])
def test_classify(call, expected):
    assert classify(call) == expected


@pytest.mark.parametrize("content, expected", [
    ("train the net", "train the net"),
    ("<command-name>/plan</command-name>", None),
    ("<task-notification> <task-id>abc</task-id>", None),
])
def test_prompt_text(content, expected):
    entry = {"type": "user", "message": {"content": content}}
    assert prompt_text(entry) == expected


def test_follow_ups_are_merged_into_previous_prompt():
    a, b, c = make_call(output_tokens=1), make_call(output_tokens=2), make_call(output_tokens=3)
    merged = merge_follow_ups([("build it", [a]), ("I did the auth", [b]), ("next task", [c])])
    assert merged == [("build it", [a, b]), ("next task", [c])]


def test_json_matches_tables():
    calls = [make_call(output_tokens=1000), make_call(mode="plan", output_tokens=500)]
    data = to_json(*build_tables([(1, "first", calls[:1]), (2, "second", calls[1:])]))
    assert [p["prompt"] for p in data["by_prompt"]] == ["first", "second"]
    assert data["total"]["calls"] == 2 and data["total"]["output"] == 1500
    assert sum(c["cost"] for c in data["by_category"]) == pytest.approx(data["total"]["cost"])


@pytest.mark.parametrize("tool_input, default, expected", [
    ({"file_path": "/Users/x/INSY/NN/web/part6.html"}, "General", "NN"),
    ({"command": "make -C NN/part4_5_c test"}, "General", "NN"),
    ({"file_path": "/Users/x/INSY/DESIGN.md"}, "NN", "General"),
    ({"command": "git commit -m x"}, "NN", "General"),
    ({"command": "ls"}, "General", "General"),   # no path: the prompt's default
    ({"file_path": "NN/web/assets/style.css", "content": "see DESIGN.md"}, "General", "NN"),   # content doesn't count
])
def test_project_of_call(tool_input, default, expected):
    assert project_of_call(make_call(tools=[("Edit", tool_input)]), default) == expected


def test_split_keeps_global_numbers_and_all_calls():
    nn, general = make_call(tools=[("Edit", {"file_path": "NN/x.py"})]), make_call(tools=[("Edit", {"file_path": "DESIGN.md"})])
    before = make_call(tools=[("Edit", {"file_path": "/Users/x/INSY/CLAUDE.md"})])   # before the repo: still NN
    logs = split_by_log([("old prompt", [before]), ("There are a few things I want to have changed", [nn]),
                         ("There are three things that need to be changed", [nn, general])])
    assert [(n, len(c)) for n, _, c in logs["NN"]] == [(1, 1), (2, 1), (3, 1)]
    assert [(n, len(c)) for n, _, c in logs["General"]] == [(3, 1)]
