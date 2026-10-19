"""Token usage and API cost per prompt and per category, read from the Claude Code session log.

Claude Code stores each session as JSONL in ~/.claude/projects/<project-dir>/<session-id>.jsonl.
Every API response carries a `usage` block. One response is logged as several lines (one per content
block) with the same message id, so we merge them into one call per id.

A new "prompt" starts with a user message typed by the user, or with feedback the user gave while
rejecting a tool call ("the user said: ..."). Local slash commands (/plan, /cost) are not prompts.

Each API call gets a category (planning, implementation, ...) from the permission mode it ran in and
the tools it called - see classify().

All sessions of this project are combined in chronological order, so prompt numbers keep counting
across sessions. Sessions without a single prompt (e.g. only an automatic title call) are skipped.

Usage:
    python NN/tools/token_usage.py              # print tables for all sessions of this project
    python NN/tools/token_usage.py --write-log  # also write the cost tables into NN/docs/PROMPT_LOG.md
    python NN/tools/token_usage.py path/to/session.jsonl
"""

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the NN project folder
REPO = ROOT.parent  # Claude Code runs in the repo root, so its sessions are stored under that path
LOG_FILE = ROOT / "docs" / "PROMPT_LOG.md"
BLOCK_START, BLOCK_END = "<!-- COSTS:START -->", "<!-- COSTS:END -->"
REJECTION_MARKER = "the user said:"

# USD per 1M tokens (source: claude-api skill, model table cached 2026-06-24).
# Cache writes: 5-minute TTL = 1.25x input, 1-hour TTL = 2x input.
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20,
                        "cache_write_5m": 5.00, "cache_write_1h": 8.00},
}

CATEGORIES = ["Planning", "Implementation", "Training & testing", "Documentation",
              "Research & context", "Answers"]
TOKEN_FIELDS = [("input", "Input"), ("cache_write", "Cache write"),
                ("cache_read", "Cache read"), ("output", "Output")]


@dataclass
class Call:
    """One API response (all log lines sharing a message id)."""
    model: str
    mode: str
    usage: dict
    tools: list = field(default_factory=list)  # (tool name, input dict)

    def tokens(self):
        u = self.usage
        return {"input": u.get("input_tokens") or 0,
                "cache_write": u.get("cache_creation_input_tokens") or 0,
                "cache_read": u.get("cache_read_input_tokens") or 0,
                "output": u.get("output_tokens") or 0}


def cost(call):
    """Dollar cost of one API call, or None if the model has no known price."""
    p = PRICES.get(call.model)
    if p is None:
        return None
    u = call.usage
    split = u.get("cache_creation") or {}
    write_1h = split.get("ephemeral_1h_input_tokens", 0) or 0
    write_5m = (u.get("cache_creation_input_tokens") or 0) - write_1h  # no split -> assume 5m
    return ((u.get("input_tokens") or 0) * p["input"]
            + (u.get("output_tokens") or 0) * p["output"]
            + (u.get("cache_read_input_tokens") or 0) * p["cache_read"]
            + write_5m * p["cache_write_5m"] + write_1h * p["cache_write_1h"]) / 1e6


TRAINING = re.compile(r"train_|verify_|compare_tf|make .*test|pio run|test_xor|test_7seg|pytest|/api/|7seg_net\.h|check\.c")
DOCS = re.compile(r"PROMPT_LOG|CLAUDE\.md|token_usage")


def classify(call):
    """Category of one API call. First matching rule wins (see CATEGORIES)."""
    names = {name for name, _ in call.tools}
    if call.mode == "plan" or names & {"AskUserQuestion", "ExitPlanMode", "EnterPlanMode"} or any(
            "/.claude/plans/" in str(args.get("file_path", "")) for _, args in call.tools):
        return "Planning"
    commands = " ".join(str(args.get("command", "")) for name, args in call.tools if name == "Bash")
    if TRAINING.search(commands):
        return "Training & testing"
    edited = [str(args.get("file_path", "")) for name, args in call.tools if name in ("Write", "Edit")]
    if any(p.endswith(".md") for p in edited) or DOCS.search(commands):
        return "Documentation"
    if names & {"Write", "Edit", "Bash", "NotebookEdit"}:
        return "Implementation"
    if names:
        return "Research & context"
    return "Answers"


def first_timestamp(path):
    for line in open(path):
        match = re.search(r'"timestamp":"([^"]+)"', line)
        if match:
            return match.group(1)
    return ""


def project_logs():
    """All session logs of this project, oldest session first."""
    project_dir = Path.home() / ".claude" / "projects" / str(REPO).replace("/", "-")
    logs = sorted(project_dir.glob("*.jsonl"), key=first_timestamp)
    if not logs:
        sys.exit(f"No session logs found in {project_dir}")
    return logs


def collect_sessions(paths):
    """Prompts of several sessions in order. Sessions without any prompt are skipped."""
    prompts = []
    for path in paths:
        session = collect(path)
        if any(text != "(before first prompt)" for text, _ in session):
            prompts += session
            print(f"Session log: {path}")
        else:
            print(f"Skipped (no prompt): {path}")
    return prompts


def prompt_text(entry):
    """Return the prompt text if this log entry starts a new user prompt, else None."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return None
    content = entry["message"].get("content")
    if isinstance(content, str):
        # local slash commands (/plan, /cost, ...) and background-task notifications are logged
        # as user messages but are no prompts
        is_not_prompt = content.lstrip().startswith(("<command-", "<local-command", "<task-notification"))
        return None if is_not_prompt else content
    for block in content or []:
        if block.get("type") == "tool_result" and block.get("is_error"):
            text = block.get("content")
            text = text if isinstance(text, str) else " ".join(
                b.get("text", "") for b in text or [] if isinstance(b, dict))
            if REJECTION_MARKER in text:
                return "(feedback) " + text.split(REJECTION_MARKER, 1)[1].strip()
    return None


def collect(path):
    """Return [(prompt text, [Call, ...]), ...] in session order."""
    prompts = []
    mode = "default"
    plan_approved = False  # the log records the mode switch late, so the approval itself ends plan mode
    exit_plan_ids = set()
    for line in open(path):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") == "permission-mode":
            mode = entry.get("permissionMode", mode)
            continue
        text = prompt_text(entry)
        if text is not None:
            prompts.append((text, {}))
            plan_approved = False
            continue
        if entry.get("type") == "user" and isinstance(entry["message"].get("content"), list):
            for block in entry["message"]["content"]:
                if (isinstance(block, dict) and block.get("tool_use_id") in exit_plan_ids
                        and not block.get("is_error")):
                    plan_approved = True
        message = entry.get("message")
        if entry.get("type") != "assistant" or not isinstance(message, dict) or not message.get("usage"):
            continue
        if not prompts:
            prompts.append(("(before first prompt)", {}))
        calls = prompts[-1][1]
        key = message.get("id") or entry.get("uuid")
        call = calls.get(key)
        if call is None:
            effective = "auto" if mode == "plan" and plan_approved else mode
            call = calls[key] = Call(model=message.get("model", "?"), mode=effective, usage=message["usage"])
        call.usage = message["usage"]  # later lines of the same response carry the final numbers
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                call.tools.append((block.get("name"), block.get("input") or {}))
                if block.get("name") == "ExitPlanMode":
                    exit_plan_ids.add(block.get("id"))
    return [(text, list(calls.values())) for text, calls in prompts]


def summarize(calls):
    """Sum tokens and cost of a list of calls."""
    total = {k: 0 for k, _ in TOKEN_FIELDS}
    dollars, unpriced = 0.0, 0
    for c in calls:
        for k, v in c.tokens().items():
            total[k] += v
        price = cost(c)
        if price is None:
            unpriced += 1
        else:
            dollars += price
    return {**total, "calls": len(calls), "cost": dollars, "unpriced": unpriced}


def snippet(text, width=48):
    text = " ".join(text.split())
    return text if len(text) <= width else text[:width - 1] + "…"


def build_tables(prompts):
    """Return (by_category, by_prompt, total) summaries."""
    all_calls = [c for _, calls in prompts for c in calls]
    by_category = {cat: summarize([c for c in all_calls if classify(c) == cat]) for cat in CATEGORIES}
    by_prompt = [(snippet(text), summarize(calls)) for text, calls in prompts]
    total = summarize(all_calls)
    # every call is counted exactly once in both breakdowns
    for key in ("calls", "output", "cache_read"):
        assert sum(s[key] for s in by_category.values()) == total[key]
        assert sum(s[key] for _, s in by_prompt) == total[key]
    return by_category, by_prompt, total


def render_markdown(by_category, by_prompt, total):
    def row(label, s, share=True):
        cells = [label, f"{s['calls']}"] + [f"{s[k]:,}" for k, _ in TOKEN_FIELDS] + [f"${s['cost']:.2f}"]
        if share:
            cells.append(f"{100 * s['cost'] / total['cost']:.0f} %" if total["cost"] else "–")
        return "| " + " | ".join(cells) + " |"

    head = ["Category", "API calls"] + [label for _, label in TOKEN_FIELDS] + ["Cost", "Share"]
    lines = [
        BLOCK_START,
        "## API tokens & cost",
        "",
        "*Generated by `python tools/token_usage.py --write-log`. Do not edit by hand.*",
        "",
        "| " + " | ".join(head) + " |",
        "|" + "---|" * 2 + "---:|" * (len(head) - 2),
    ]
    lines += [row(cat, s) for cat, s in by_category.items() if s["calls"]]
    lines.append(row("**Total**", total).replace(f"| {total['calls']} |", f"| **{total['calls']}** |", 1)
                 .replace(f"${total['cost']:.2f}", f"**${total['cost']:.2f}**"))
    lines += [
        "",
        "**By prompt**",
        "",
        "| # | Prompt | API calls | Output | Cache read | Cost |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    lines += [f"| {i} | {text.replace('|', '/')} | {s['calls']} | {s['output']:,} | {s['cache_read']:,} | ${s['cost']:.2f} |"
              for i, (text, s) in enumerate(by_prompt, start=1)]
    notes = [
        "",
        "Category rules: **Planning** = plan mode or questions/plan approval · **Training & testing** = training, "
        "verify scripts, pytest, API checks · **Documentation** = Markdown files and this log · "
        "**Implementation** = other file edits and shell commands · **Research & context** = reading files, PDF, skills · "
        "**Answers** = replies without a tool call.",
        "",
        "Prices (USD per 1M tokens, Claude Opus 5.5): input $4 · output $20 · cache read $0.20 · "
        "cache write $5 (5 min) / $8 (1 h). `/cost` also counts small side calls (e.g. session titles, ~$0.002) "
        "that are not in the session log. The prompt that is running while the table is generated is only "
        f"partly included. Last updated {time.strftime('%Y-%m-%d %H:%M')}.",
    ]
    if total["unpriced"]:
        notes.append(f"\n⚠ {total['unpriced']} calls use a model without a known price and are not in the cost.")
    return "\n".join(lines + notes + [BLOCK_END])


def write_log(markdown):
    """Replace the cost block in PROMPT_LOG.md, or insert it after the intro on first use."""
    text = LOG_FILE.read_text()
    if BLOCK_START in text:
        pattern = re.compile(re.escape(BLOCK_START) + ".*?" + re.escape(BLOCK_END), re.S)
        text = pattern.sub(lambda _: markdown, text, count=1)
    else:
        head, sep, rest = text.partition("\n---\n")
        text = f"{head}\n{markdown}\n{sep}{rest}" if sep else f"{text}\n{markdown}\n"
    LOG_FILE.write_text(text)


def print_console(by_category, by_prompt, total):
    cols = "".join(f"{label:>13}" for _, label in TOKEN_FIELDS)
    print(f"{'':<22}{'calls':>6}{cols}{'cost':>10}")
    for cat, s in by_category.items():
        print(f"{cat:<22}{s['calls']:>6}" + "".join(f"{s[k]:>13,}" for k, _ in TOKEN_FIELDS) + f"{'$' + format(s['cost'], '.2f'):>10}")
    print(f"{'TOTAL':<22}{total['calls']:>6}" + "".join(f"{total[k]:>13,}" for k, _ in TOKEN_FIELDS)
          + f"{'$' + format(total['cost'], '.2f'):>10}\n")
    for i, (text, s) in enumerate(by_prompt, start=1):
        print(f"{i:>2}  {s['calls']:>3} calls  {s['output']:>7,} out  {'$' + format(s['cost'], '.2f'):>7}  {text}")


def main():
    parser = argparse.ArgumentParser(description="Token usage and cost of the Claude Code sessions")
    parser.add_argument("log", nargs="?", help="one session .jsonl (default: all sessions of this project)")
    parser.add_argument("--write-log", action="store_true", help=f"write the tables into {LOG_FILE.name}")
    args = parser.parse_args()

    paths = [Path(args.log)] if args.log else project_logs()
    prompts = collect_sessions(paths)
    print()
    tables = build_tables(prompts)
    print_console(*tables)
    if args.write_log:
        write_log(render_markdown(*tables))
        print(f"\nwrote cost tables to {LOG_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
