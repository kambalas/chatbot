from __future__ import annotations

from pathlib import Path
from typing import Optional

from pypdf import PdfReader


def extract_text(path: Path) -> str:
    text = _extract_with_pypdf(path)
    if text.strip():
        return text

    # OCR fallback (optional dependency)
    ocr_text = _extract_with_ocr(path)
    return ocr_text or ""

def _extract_with_pypdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            parts.append(page_text)
    return "\n".join(parts)


def _extract_with_ocr(path: Path) -> str:
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except Exception:
        return ""

    images = convert_from_path(path)
    parts = []
    for image in images:
        text = pytesseract.image_to_string(image)
        if text.strip():
            parts.append(text)

    return "\n".join(parts)