"""Prevent UTF-8 byte-order marks in repository text files."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UTF8_BOM = b"\xef\xbb\xbf"

TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".json",
    ".md",
    ".toml",
    ".yaml",
    ".yml",
    ".css",
    ".html",
    ".txt",
}

EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
}


def test_repository_text_files_do_not_contain_utf8_bom() -> None:
    offenders: list[str] = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        if any(part in EXCLUDED_DIRECTORIES for part in path.parts):
            continue

        if path.read_bytes().startswith(UTF8_BOM):
            offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, (
        "UTF-8 BOM found in repository text files: "
        + ", ".join(sorted(offenders))
    )