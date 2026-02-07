from __future__ import annotations

from pathlib import Path

from document_loader.extractors.html_extractor import extract_text as extract_html
from document_loader.extractors.json_extractor import extract_text as extract_json


def test_html_extraction_strips_scripts(tmp_path: Path) -> None:
    html_path = tmp_path / "test.html"
    html_path.write_text(
        "<html><head><script>var a=1;</script></head><body><h1>Title</h1></body></html>",
        encoding="utf-8",
    )

    text = extract_html(html_path)
    assert "Title" in text
    assert "var a" not in text


def test_json_extraction(tmp_path: Path) -> None:
    json_path = tmp_path / "test.json"
    json_path.write_text('{"key": "value"}', encoding="utf-8")

    text = extract_json(json_path)
    assert "\"key\"" in text
    assert "value" in text
