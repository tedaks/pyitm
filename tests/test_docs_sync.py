# tests/test_docs_sync.py
"""Docs that state the fidelity contract must agree with each other and with the pin."""

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent


def _section(path, heading):
    text = (ROOT / path).read_text(encoding="utf-8")
    m = re.search(rf"^#+ {re.escape(heading)}\n(.*?)(?=^#+ )", text, re.M | re.S)
    assert m, f"{path}: no '{heading}' section"
    return m.group(1).strip()


def test_fidelity_policy_identical_in_claude_and_agents():
    heading = "Fidelity policy: match the C++ exactly"
    assert _section("CLAUDE.md", heading) == _section("AGENTS.md", heading)


def test_pinned_commit_quoted_consistently():
    script = (ROOT / "tools" / "build_itm_reference.sh").read_text(encoding="utf-8")
    pin = re.search(r"^ITM_COMMIT=([0-9a-f]{40})", script, re.M).group(1)
    for doc in ("README.md", "CLAUDE.md", "AGENTS.md", "LICENSE.md"):
        quoted = set(re.findall(r"`([0-9a-f]{7,40})`", (ROOT / doc).read_text(encoding="utf-8")))
        assert quoted, f"{doc} quotes no pinned commit"
        assert all(pin.startswith(q) for q in quoted), f"{doc} quotes {quoted}, pin is {pin[:7]}"
