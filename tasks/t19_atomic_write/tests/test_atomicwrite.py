import os
from pathlib import Path

import pytest

from atomicwrite import BACKUP_SUFFIX, TEMP_SUFFIX, render, save


@pytest.fixture(autouse=True)
def no_ambient_backup_policy(monkeypatch):
    """The backup policy is whatever a test says it is, never what the host says."""
    monkeypatch.delenv("ATOMIC_BACKUP", raising=False)


def test_render_sorts_keys_and_terminates_every_line():
    assert render({"zeta": "1", "alpha": "2", "mu": "3"}) == "alpha=2\nmu=3\nzeta=1\n"


def test_render_of_an_empty_mapping_is_empty():
    assert render({}) == ""


def test_render_keeps_values_verbatim():
    assert render({"path": "/var/lib/daemon", "note": "a = b"}) == (
        "note=a = b\npath=/var/lib/daemon\n"
    )


@pytest.mark.parametrize(
    "settings",
    [
        {"": "x"},
        {"a=b": "x"},
        {"a\nb": "x"},
        {"mode": "fast\nowner=root"},
    ],
)
def test_render_rejects_keys_and_values_it_cannot_round_trip(settings):
    with pytest.raises(ValueError):
        render(settings)


def test_save_writes_the_document_and_returns_the_path(tmp_path):
    target = tmp_path / "settings.ini"

    result = save(str(target), {"mode": "fast", "retries": "3"})

    assert isinstance(result, Path)
    assert result == target
    assert target.read_text(encoding="utf-8") == "mode=fast\nretries=3\n"


def test_save_round_trips_non_ascii_as_utf_8(tmp_path):
    target = tmp_path / "settings.ini"
    settings = {"greeting": "\u00e7a va", "city": "M\u00fcnchen", "sign": "\u2713"}

    save(target, settings)

    assert target.read_text(encoding="utf-8") == "city=M\u00fcnchen\ngreeting=\u00e7a va\nsign=\u2713\n"
    assert target.read_bytes() == target.read_text(encoding="utf-8").encode("utf-8")


def test_save_accepts_any_os_pathlike(tmp_path):
    class Handle:
        def __init__(self, path):
            self._path = str(path)

        def __fspath__(self):
            return self._path

    target = tmp_path / "settings.ini"

    result = save(Handle(target), {"mode": "fast"})

    assert result == target
    assert target.read_text(encoding="utf-8") == "mode=fast\n"


def test_save_goes_through_a_sibling_temp_file(tmp_path):
    target = tmp_path / "settings.ini"
    real_replace = os.replace
    seen = {}

    def recording_replace(src, dst):
        source = Path(src)
        seen["src"] = source
        seen["dst"] = Path(dst)
        seen["staged"] = source.read_text(encoding="utf-8")
        seen["target_existed"] = Path(dst).exists()
        return real_replace(src, dst)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "replace", recording_replace)
        save(target, {"mode": "fast"})

    assert seen["src"] == tmp_path / ("settings.ini" + TEMP_SUFFIX)
    assert seen["src"].parent == target.parent
    assert seen["dst"] == target
    assert seen["staged"] == "mode=fast\n"
    assert seen["target_existed"] is False
    assert target.read_text(encoding="utf-8") == "mode=fast\n"


def test_no_temp_file_survives_a_successful_save(tmp_path):
    target = tmp_path / "settings.ini"

    save(target, {"mode": "fast"})
    save(target, {"mode": "slow"})

    assert not (tmp_path / ("settings.ini" + TEMP_SUFFIX)).exists()
    assert target.read_text(encoding="utf-8") == "mode=slow\n"


def test_an_unrenderable_document_changes_nothing_on_disk(tmp_path):
    target = tmp_path / "settings.ini"
    target.write_text("mode=slow\n", encoding="utf-8")

    with pytest.raises(ValueError):
        save(target, {"mode": "fast\nowner=root"})

    assert target.read_text(encoding="utf-8") == "mode=slow\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["settings.ini"]
    assert not (tmp_path / ("settings.ini" + TEMP_SUFFIX)).exists()
    assert not (tmp_path / ("settings.ini" + BACKUP_SUFFIX)).exists()
