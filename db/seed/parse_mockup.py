"""Parse mockup data.js into Python structures."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_JS = ROOT / "data.js"


def _extract_array(name: str, text: str) -> str:
    pattern = rf"window\.{name}\s*=\s*(\[)"
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"Could not find window.{name} in data.js")
    start = m.start(1)
    depth = 0
    in_str: str | None = None
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ("'", '"'):
            in_str = ch
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError(f"Unclosed array for {name}")


def _js_to_json(js: str) -> str:
    """Best-effort JS object literal → JSON."""
    out = []
    i = 0
    n = len(js)
    in_str: str | None = None
    escape = False
    while i < n:
        ch = js[i]
        if in_str:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = '"'
            out.append('"')
            i += 1
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (js[j].isalnum() or js[j] in "._"):
                j += 1
            word = js[i:j]
            if word in ("true", "false", "null"):
                out.append(word)
            else:
                out.append(json.dumps(word))
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _expand_row_calls(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        nums = [int(x.strip()) for x in match.group(1).split(",")]
        pairs = ", ".join(f'"kcc-{i + 1:02d}": {v}' for i, v in enumerate(nums))
        return "{" + pairs + "}"

    return re.sub(r"row\(\[([^\]]+)\]\)", repl, text)


def load_mockup_data() -> dict:
    text = _expand_row_calls(DATA_JS.read_text(encoding="utf-8"))
    kccs = json.loads(_js_to_json(_extract_array("KCCS", text)))
    carcinogens = json.loads(_js_to_json(_extract_array("CARCINOGENS", text)))
    assays = json.loads(_js_to_json(_extract_array("ASSAYS", text)))
    literature = json.loads(_js_to_json(_extract_array("LITERATURE", text)))
    return {"kccs": kccs, "carcinogens": carcinogens, "assays": assays, "literature": literature}
