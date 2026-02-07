from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

from document_loader.extractors.csv_extractor import extract_text as extract_csv
from document_loader.extractors.docx_extractor import extract_text as extract_docx
from document_loader.extractors.excel_extractor import extract_text as extract_excel
from document_loader.extractors.html_extractor import extract_text as extract_html
from document_loader.extractors.json_extractor import extract_text as extract_json
from document_loader.extractors.markdown_extractor import extract_text as extract_markdown
from document_loader.extractors.pdf_extractor import extract_text as extract_pdf
from document_loader.extractors.text_extractor import extract_text as extract_text
from document_loader.extractors.image_extractor import extract_text as extract_image


Extractor = Callable[[Path], str]

try:
    from document_loader.extractors.pptx_extractor import extract_text as extract_pptx
except Exception:  # pragma: no cover - optional dependency
    extract_pptx = None

EXTRACTOR_BY_EXTENSION: Dict[str, Extractor] = {
       ".csv": extract_csv,
    ".doc": extract_docx,
    ".docx": extract_docx,
    ".htm": extract_html,
    ".html": extract_html,
    ".json": extract_json,
    ".md": extract_markdown,
    ".pdf": extract_pdf,
    ".txt": extract_text,
    ".xls": extract_excel,
    ".xlsx": extract_excel,

}

if extract_pptx is not None:
    EXTRACTOR_BY_EXTENSION[".pptx"] = extract_pptx
