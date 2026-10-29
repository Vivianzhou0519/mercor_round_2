import os

import pytest

from atomicwrite import BACKUP_SUFFIX, TEMP_SUFFIX, save


@pytest.fixture(autouse=True)
def no_ambient_backup_policy(monkeypatch):
    """Every test states the policy it wants; none inherits the host's environment."""
    monkeypatch.delenv("ATOMIC_BACKUP", raising=False)


def test_backup_holds_the_previous_contents_by_default(tmp_path):
    target = tmp_path / "settings.ini"
    target.write_text("mode=slow\n", encoding="utf-8")

    save(target, {"mode": "fast"})

    backup = tmp_path / ("settings.ini" + BACKUP_SUFFIX)
    assert backup.read_text(encoding="utf-8") == "mode=slow\n"
    assert target.read_text(encoding="utf-8") == "mode=fast\n"


def test_backup_tracks_the_most_recent_previous_version(tmp_path):
    target = tmp_path / "settings.ini"

    save(target, {"mode": "one"})
    save(target, {"mode": "two"})
    save(target, {"mode": "three"})

    backup = tmp_path / ("settings.ini" + BACKUP_SUFFIX)
    assert backup.read_text(encoding="utf-8") == "mode=two\n"
    assert target.read_text(encoding="utf-8") == "mode=three\n"


def test_a_brand_new_file_gets_no_backup(tmp_path):
    target = tmp_path / "settings.ini"

    save(target, {"mode": "fast"})

    assert sorted(p.name for p in tmp_path.iterdir()) == ["settings.ini"]


def test_policy_zero_writes_no_backup_and_disturbs_none(tmp_path, monkeypatch):
    target = tmp_path / "settings.ini"
    target.write_text("mode=slow\n", encoding="utf-8")
    backup = tmp_path / ("settings.ini" + BACKUP_SUFFIX)
    backup.write_text("mode=ancient\n", encoding="utf-8")

    monkeypatch.setenv("ATOMIC_BACKUP", "0")
    save(target, {"mode": "fast"})

    assert backup.read_text(encoding="utf-8") == "mode=ancient\n"
    assert target.read_text(encoding="utf-8") == "mode=fast\n"


def test_policy_is_reread_on_every_call(tmp_path, monkeypatch):
    target = tmp_path / "settings.ini"
    target.write_text("mode=v1\n", encoding="utf-8")
    backup = tmp_path / ("settings.ini" + BACKUP_SUFFIX)

    monkeypatch.setenv("ATOMIC_BACKUP", "0")
    save(target, {"mode": "v2"})
    assert not backup.exists()

    monkeypatch.setenv("ATOMIC_BACKUP", "1")
    save(target, {"mode": "v3"})
    assert backup.read_text(encoding="utf-8") == "mode=v2\n"

    monkeypatch.setenv("ATOMIC_BACKUP", "verbose")
    save(target, {"mode": "v4"})
    assert backup.read_text(encoding="utf-8") == "mode=v3\n"
    assert target.read_text(encoding="utf-8") == "mode=v4\n"


def test_a_crash_during_replace_leaves_no_debris(tmp_path):
    target = tmp_path / "settings.ini"
    target.write_text("mode=slow\n", encoding="utf-8")

    def exploding_replace(src, dst):
        raise OSError("simulated power loss during rename")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "replace", exploding_replace)
        with pytest.raises(OSError):
            save(target, {"mode": "fast"})

    assert target.read_text(encoding="utf-8") == "mode=slow\n"
    assert not (tmp_path / ("settings.ini" + TEMP_SUFFIX)).exists()
