from pathlib import Path

from engine.application import _write_atomic
from engine.reports.readable import normalize_language


def test_normalize_language() -> None:
    assert normalize_language("sv-SE") == "sv"
    assert normalize_language("en_GB") == "en"
    assert normalize_language("de") == "en"
    assert normalize_language(None) == "en"


def test_write_atomic(tmp_path: Path) -> None:
    target = tmp_path / "reports" / "result.txt"
    _write_atomic(target, "first")
    _write_atomic(target, "second")
    assert target.read_text(encoding="utf-8") == "second"
    assert not target.with_suffix(".txt.tmp").exists()
