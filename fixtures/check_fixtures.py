"""Run the validator on the fixtures and compare with expected.json.   python fixtures/check_fixtures.py"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
exp = json.loads((ROOT / "expected.json").read_text())
subprocess.run([sys.executable, str(ROOT / "make_fixtures.py")], check=True, capture_output=True)
subprocess.run([sys.executable, "validate.py", str(ROOT / "generated"), "--out", "results/fixtures"],
               cwd=ROOT.parent, capture_output=True)
report = json.loads((ROOT.parent / "results" / "fixtures" / "report.json").read_text())
bad = 0
for t in report["tasks"]:
    want = exp.get(t["task"], {})
    for c in t["checks"]:
        n, got = c["name"], c["status"]
        if n == "duplicates":
            continue
        ok_set = set(want[n] if isinstance(want[n], list) else [want[n]]) if n in want else {exp["_inherited"].get(n, "PASS"), "PASS", "SKIPPED"}
        if got not in ok_set:
            bad += 1
            print(f"MISMATCH {t['task']}/{n}: expected {want.get(n, 'PASS/SKIPPED')}, got {got}: {c['reason']}")
    print(f"{t['task']:<18} " + " ".join(f"{c['name']}={c['status']}" for c in t["checks"]
                                         if c["status"] not in ("PASS", "SKIPPED") and c["name"] != "duplicates"))
print("ALL FIXTURES MATCH" if not bad else f"{bad} mismatch(es)")
sys.exit(1 if bad else 0)
