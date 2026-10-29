from pathspec import _expand_braces, matches


def test_basename_pattern():
    assert matches("src/app/main.py", ["*.py"]) is True
    assert matches("src/app/main.txt", ["*.py"]) is False


def test_star_does_not_cross_a_slash():
    assert matches("src/app/main.py", ["src/*.py"]) is False
    assert matches("src/main.py", ["src/*.py"]) is True


def test_question_mark_matches_one_character():
    assert matches("a1.py", ["a?.py"]) is True
    assert matches("a12.py", ["a?.py"]) is False


def test_double_star_prefix():
    assert matches("a/b/c/main.py", ["**/main.py"]) is True
    assert matches("main.py", ["**/main.py"]) is True


def test_double_star_suffix():
    assert matches("build/x/y/z.o", ["build/**"]) is True
    assert matches("buildx/y.o", ["build/**"]) is False


def test_negation_last_match_wins():
    patterns = ["*.log", "!keep.log"]
    assert matches("debug.log", patterns) is True
    assert matches("keep.log", patterns) is False


def test_expand_braces():
    assert _expand_braces("src/{a,b}/*.py") == ["src/a/*.py", "src/b/*.py"]
    assert _expand_braces("plain.py") == ["plain.py"]


def test_brace_groups_match():
    assert matches("src/a/main.py", ["src/{a,b}/*.py"]) is True
    assert matches("src/c/main.py", ["src/{a,b}/*.py"]) is False


def test_no_patterns():
    assert matches("main.py", []) is False
