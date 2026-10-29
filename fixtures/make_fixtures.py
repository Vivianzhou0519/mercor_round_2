"""Fixtures = test cases for the validator itself: copies of t01 with exactly one planted defect each.
If 'good' passes and each broken copy trips only its own check, the checks can be trusted.
    python fixtures/make_fixtures.py   -> fixtures/generated/
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "tasks" / "t01_word_wrap"
OUT = ROOT / "generated"
ORACLE_CODE = (SRC / "solution" / "solve.sh").read_text().split("<< '__HARBOR_EOF__'\n")[1].split("__HARBOR_EOF__")[0]


def copy(name):
    d = OUT / name
    shutil.copytree(SRC, d)
    return d


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    copy("f1_good")
    # starter already correct -> doing nothing scores 1
    (copy("f2_nop_passes") / "environment" / "wordwrap.py").write_text(ORACLE_CODE)
    # reference solution writes a wrong implementation
    d = copy("f3_oracle_fails")
    p = d / "solution" / "solve.sh"
    p.write_text(p.read_text().replace("length + 1 + len(word) <= width", "length + 1 + len(word) < width"))
    # a random test -> identical runs disagree
    d = copy("f4_flaky")
    with open(d / "tests" / "test_wordwrap.py", "a") as f:
        f.write("\n\ndef test_coin_flip():\n    import random\n    assert random.random() < 0.5\n")
    # the solution pasted into a file the agent can see
    d = copy("f5_leak")
    (d / "environment" / "NOTES.md").write_text("Draft fix:\n\n```python\n" + ORACLE_CODE + "```\n")
    df = d / "environment" / "Dockerfile"
    df.write_text(df.read_text().replace("COPY wordwrap.py /app/wordwrap.py", "COPY wordwrap.py /app/wordwrap.py\nCOPY NOTES.md /app/NOTES.md"))
    # verifier runs pytest in the agent's dir -> an agent conftest.py can force a pass
    d = copy("f6_hackable")
    p = d / "tests" / "test.sh"
    p.write_text(p.read_text().replace('cd "$APP_DIR"\n', 'cd "$APP_DIR"\ncp "$TESTS_DIR"/test_*.py "$APP_DIR"/\n')
                 .replace('-m pytest "$TESTS_DIR"', "-m pytest ."))
    print("\n".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
