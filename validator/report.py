"""report.json, summary.txt and a self-contained report.html (summary table → click through to evidence)."""

from __future__ import annotations

import html
import json
from pathlib import Path

CSS = """:root{--bg:#fff;--fg:#1d1d1f;--mut:#6e6e73;--line:#d2d2d7;--card:#f5f5f7;--code:#f0f0f2;
--PASS:#1a7f37;--FAIL:#cf222e;--WARN:#9a6700;--ERROR:#8250df;--SKIPPED:#6e7781}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--fg:#f5f5f7;--mut:#a1a1a6;--line:#3a3a3c;--card:#1f1f22;
--code:#0d0d0f;--PASS:#3fb950;--FAIL:#f85149;--WARN:#d29922;--ERROR:#a371f7;--SKIPPED:#8b949e}}
body{background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,system-ui,sans-serif;max-width:1300px;margin:auto;padding:24px 16px}
.mut{color:var(--mut)}table{border-collapse:collapse;font-size:12px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:3px 6px;white-space:nowrap}th{background:var(--card)}td a{color:inherit;text-decoration:none}
.PASS{color:var(--PASS)}.FAIL{color:var(--FAIL);font-weight:700}.WARN{color:var(--WARN);font-weight:600}.ERROR{color:var(--ERROR)}.SKIPPED{color:var(--SKIPPED)}
details{background:var(--card);border:1px solid var(--line);border-radius:6px;margin:4px 0;padding:4px 10px}
pre{background:var(--code);padding:6px;white-space:pre-wrap;font-size:12px}h2{margin-top:28px;border-bottom:1px solid var(--line)}"""


def verdict(checks: list[dict]) -> str:
    """INVALID if any task-level FAIL; REVIEW if any WARN/ERROR; else VALID. (verifier_isolation is systemic.)"""
    st = [c["status"] for c in checks if c["name"] != "verifier_isolation"]
    return "INVALID" if "FAIL" in st else "REVIEW" if ("WARN" in st or "ERROR" in st) else "VALID"


def write(out: Path, results: dict[str, list[dict]], meta: dict) -> None:
    names = []
    for checks in results.values():
        for c in checks:
            if c["name"] not in names:
                names.append(c["name"])
    tasks = [{"task": t, "verdict": verdict(cs), "checks": cs} for t, cs in results.items()]
    (out / "report.json").write_text(json.dumps({"meta": meta, "tasks": tasks}, indent=2))
    lines = [f"{'task':<26} {'verdict':<8} problems"]
    for t in tasks:
        probs = [f"{c['name']}={c['status']}" for c in t["checks"] if c["status"] in ("FAIL", "WARN", "ERROR")]
        lines.append(f"{t['task']:<26} {t['verdict']:<8} {', '.join(probs)}")
    (out / "summary.txt").write_text("\n".join(lines) + "\n")
    e = html.escape
    counts = {v: sum(t["verdict"] == v for t in tasks) for v in ("VALID", "REVIEW", "INVALID")}
    h = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
         f"<title>Task validation report</title><style>{CSS}</style><h1>Task validation report</h1>",
         f"<p class=mut>{e(meta['started'])} · <code>{e(meta['command'])}</code> · {len(tasks)} tasks · "
         f"<span class=PASS>{counts['VALID']} VALID</span> · <span class=WARN>{counts['REVIEW']} REVIEW</span> · "
         f"<span class=FAIL>{counts['INVALID']} INVALID</span> · tasks/ unchanged: {meta['tasks_unchanged']}</p>",
         "<table><tr><th>task</th><th>verdict</th>" + "".join(f"<th>{e(n)}</th>" for n in names) + "</tr>"]
    vcls = {"VALID": "PASS", "REVIEW": "WARN", "INVALID": "FAIL"}
    for t in tasks:
        by = {c["name"]: c for c in t["checks"]}
        cells = "".join(f"<td class={by[n]['status']}><a href='#{e(t['task'])}-{n}' title='{e(by[n]['reason'])}'>"
                        f"{by[n]['status']}</a></td>" if n in by else "<td></td>" for n in names)
        h.append(f"<tr><td><a href='#{e(t['task'])}'>{e(t['task'])}</a></td><td class={vcls[t['verdict']]}>"
                 f"{t['verdict']}</td>{cells}</tr>")
    h.append("</table><p class=mut>Hover a cell for the reason; click for details and links to the raw evidence.</p>")
    for t in tasks:
        h.append(f"<h2 id='{e(t['task'])}'>{e(t['task'])} · <span class={vcls[t['verdict']]}>{t['verdict']}</span></h2>")
        for c in t["checks"]:
            d = f"{t['task']}/{c['name']}"
            op = " open" if c["status"] in ("FAIL", "WARN", "ERROR") else ""
            h.append(f"<details id='{e(t['task'])}-{c['name']}'{op}><summary><span class={c['status']}>{c['status']}</span>"
                     f" · T{c['tier']} <b>{e(c['name'])}</b> · {e(c['reason'])}</summary>")
            if c["fix"]:
                h.append(f"<p><b>Fix:</b> {e(c['fix'])}</p>")
            if c["details"]:
                h.append("<pre>" + e("\n".join(c["details"])) + "</pre>")
            runs = sorted(p.name for p in (out / d / "runs").iterdir()) if (out / d / "runs").is_dir() else []
            links = [f"<a href='{e(d)}/result.txt'>result.txt</a>"] + [f"<a href='{e(d)}/runs/{e(r)}/'>{e(r)}</a>" for r in runs]
            if (out / d / "llm-call.json").exists():
                links.append(f"<a href='{e(d)}/llm-call.json'>llm-call.json</a>")
            h.append("<p class=mut>Evidence: " + " · ".join(links) + "</p></details>")
    (out / "report.html").write_text("\n".join(h))
