"""
Build a single static index.html that displays every raw output from
results/raw/ in a side-by-side grid: rows = prompts, columns = formats.

SVG outputs are inlined inside a sandboxed iframe (srcdoc) so malformed
markup can't break the page layout. ASCII / Braille render in <pre>.

Run after generate.py finishes:
    python build_site.py
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from prompts import FORMATS, PROMPTS

ROOT = Path(__file__).parent
RAW = ROOT / "results" / "raw"
OUT = ROOT / "index.html"

SVG_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.DOTALL | re.IGNORECASE)


def load_pair(prompt_id: str, fmt: str) -> tuple[str, dict]:
    txt_path = RAW / f"{prompt_id}__{fmt}.txt"
    json_path = RAW / f"{prompt_id}__{fmt}.json"
    text = txt_path.read_text(encoding="utf-8") if txt_path.exists() else ""
    meta = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}
    return text, meta


def extract_svg(text: str) -> str | None:
    m = SVG_RE.search(text)
    return m.group(0) if m else None


def render_cell(text: str, meta: dict, fmt: str) -> str:
    ttft = meta.get("ttft_s")
    total = meta.get("total_s")
    chars = meta.get("char_count", len(text))
    err = meta.get("error")

    meta_bits = [f"{chars} chars"]
    if ttft is not None:
        meta_bits.append(f"ttft {ttft:.2f}s")
    if total is not None:
        meta_bits.append(f"total {total:.2f}s")
    if err:
        meta_bits.append("ERROR")
    meta_line = " · ".join(meta_bits)

    if not text and not err:
        body = '<div class="empty">(no output)</div>'
    elif err:
        body = f'<div class="error">{html.escape(err)}</div>'
    elif fmt == "svg":
        svg = extract_svg(text)
        if svg:
            srcdoc = html.escape(
                "<!doctype html><html><body style='margin:0;display:flex;"
                "align-items:center;justify-content:center;height:100vh;"
                "background:#fff'>" + svg + "</body></html>",
                quote=True,
            )
            body = (
                f'<iframe class="svg-frame" srcdoc="{srcdoc}" sandbox></iframe>'
                f'<details><summary>raw</summary>'
                f'<pre class="raw">{html.escape(text)}</pre></details>'
            )
        else:
            body = (
                '<div class="warn">no &lt;svg&gt; found</div>'
                f'<pre class="raw">{html.escape(text)}</pre>'
            )
    else:
        # ASCII / Braille
        body = f'<pre class="art">{html.escape(text)}</pre>'

    return f'<div class="cell"><div class="meta">{html.escape(meta_line)}</div>{body}</div>'


def render_row(entry: dict) -> str:
    cells = []
    for fmt in FORMATS:
        text, meta = load_pair(entry["id"], fmt)
        cells.append(render_cell(text, meta, fmt))
    return (
        f'<tr><th class="rowhead">'
        f'<div class="pid">{html.escape(entry["id"])}</div>'
        f'<div class="target">{html.escape(entry["target"])}</div>'
        f'</th>'
        + "".join(f"<td>{c}</td>" for c in cells)
        + "</tr>"
    )


CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
       margin: 0; padding: 24px; background: #fafafa; color: #111; }
h1 { margin: 0 0 4px; font-size: 22px; }
.sub { color: #666; margin-bottom: 20px; font-size: 13px; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top;
         background: #fff; }
th.fmthead { background: #f0f0f0; font-size: 13px; text-transform: uppercase;
             letter-spacing: 0.5px; }
th.rowhead { background: #f7f7f7; text-align: left; min-width: 180px; max-width: 220px; }
.pid { font-family: ui-monospace, "SF Mono", monospace; font-size: 11px;
       color: #888; }
.target { font-size: 14px; margin-top: 4px; }
.cell { min-width: 260px; }
.meta { font-family: ui-monospace, "SF Mono", monospace; font-size: 11px;
        color: #888; margin-bottom: 6px; }
.svg-frame { width: 220px; height: 220px; border: 1px dashed #ccc;
             background: #fff; }
pre.art { font-family: ui-monospace, "SF Mono", "Menlo", monospace;
          font-size: 13px; line-height: 1.1; background: #fff; color: #111;
          padding: 8px; margin: 0; white-space: pre; overflow-x: auto;
          border: 1px solid #eee; }
pre.raw { font-family: ui-monospace, monospace; font-size: 10px;
          color: #555; background: #f5f5f5; padding: 6px; margin: 4px 0 0;
          max-height: 160px; overflow: auto; white-space: pre-wrap; }
details { margin-top: 6px; font-size: 11px; color: #666; }
.warn { color: #b15a00; font-size: 12px; margin-bottom: 4px; }
.error { color: #b00020; font-size: 12px; white-space: pre-wrap;
         font-family: ui-monospace, monospace; }
.empty { color: #aaa; font-style: italic; font-size: 12px; }
@media (prefers-color-scheme: dark) {
  body { background: #111; color: #eee; }
  th, td { border-color: #333; background: #1a1a1a; }
  th.fmthead { background: #222; }
  th.rowhead { background: #181818; }
  .pid, .meta { color: #888; }
  pre.art { background: #0f0f0f; color: #eee; border-color: #2a2a2a; }
  pre.raw { background: #1a1a1a; color: #aaa; }
  .svg-frame { background: #fff; }
}
"""


def main() -> None:
    if not RAW.exists() or not any(RAW.glob("*.txt")):
        raise SystemExit(f"No outputs found in {RAW}. Run generate.py first.")

    head = (
        "<thead><tr><th class='rowhead fmthead'>prompt</th>"
        + "".join(f"<th class='fmthead'>{fmt}</th>" for fmt in FORMATS)
        + "</tr></thead>"
    )
    rows = "\n".join(render_row(entry) for entry in PROMPTS)

    # Read one meta file to find the model id
    model_id = "(unknown)"
    for entry in PROMPTS:
        for fmt in FORMATS:
            jp = RAW / f"{entry['id']}__{fmt}.json"
            if jp.exists():
                model_id = json.loads(jp.read_text(encoding="utf-8")).get("model_id", model_id)
                break
        if model_id != "(unknown)":
            break

    out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Gemma 4 E4B — Widget Art Eval</title>
<style>{CSS}</style>
</head>
<body>
<h1>Gemma 4 E4B — Widget Art Eval</h1>
<div class="sub">model: <code>{html.escape(model_id)}</code> · {len(PROMPTS)} prompts × {len(FORMATS)} formats</div>
<table>
{head}
<tbody>
{rows}
</tbody>
</table>
</body>
</html>
"""
    OUT.write_text(out, encoding="utf-8")
    print(f"[done] wrote {OUT}")


if __name__ == "__main__":
    main()
