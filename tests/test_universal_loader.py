from __future__ import annotations

import base64
from pathlib import Path

from document_loader.universal_loader import UniversalDocumentLoader
from document_loader.extractors.pdf_extractor import extract_text as extract_pdf_text


PDF_BASE64 = (
    "JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4K"
    "ZW5kb2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50"
    "IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAv"
    "TWVkaWFCb3ggWzAgMCAyMDAgMjAwXSAvQ29udGVudHMgNCAwIFIgL1Jlc291cmNlcyA8"
    "PCAvRm9udCA8PCAvRjEgNSAwIFIgPj4gPj4gPj4KZW5kb2JqCjQgMCBvYmoKPDwgL0xl"
    "bmd0aCA0MCA+PgpzdHJlYW0KQlQgL0YxIDI0IFRmIDEwIDEwMCBUZCAoSGVsbG8gUERG"
    "KSBUaiBFVAplbmRzdHJlYW0KZW5kb2JqCjUgMCBvYmoKPDwgL1R5cGUgL0ZvbnQgL1N1"
    "YnR5cGUgL1R5cGUxIC9CYXNlRm9udCAvSGVsdmV0aWNhID4+CmVuZG9iagp4cmVmCjAg"
    "NgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA1"
    "OCAwMDAwMCBuIAowMDAwMDAwMTE1IDAwMDAwIG4gCjAwMDAwMDAyNDEgMDAwMDAgbiAK"
    "MDAwMDAwMDMzMSAwMDAwMCBuIAp0cmFpbGVyCjw8IC9Sb290IDEgMCBSIC9TaXplIDYg"
    "Pj4Kc3RhcnR4cmVmCjQwMQolJUVPRgo="
)


def write_sample_pdf(path: Path) -> None:
    path.write_bytes(base64.b64decode(PDF_BASE64))


def test_recursive_directory_walk(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.md").write_text("# Test\nExpected content")

    nested = root / "nested" / "deep"
    nested.mkdir(parents=True)
    pdf_path = nested / "file2.pdf"
    write_sample_pdf(pdf_path)
 
    loader = UniversalDocumentLoader(
        root_directory=root,
        recursive=True,
        show_progress=False,
        use_multithreading=False,
    )
    docs = loader.load()

    sources = {doc.metadata["source"] for doc in docs}
    assert "file1.md" in sources
    assert "nested/deep/file2.pdf" in sources
    assert len(docs) == 2


def test_markdown_extraction(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "test.md").write_text("# Title\nExpected content")

    loader = UniversalDocumentLoader(
        root_directory=root,
        recursive=True,
        show_progress=False,
        use_multithreading=False,
    )
    docs = loader.load()

    assert len(docs) == 1
    assert "Expected content" in docs[0].page_content


def test_pdf_extraction(tmp_path: Path) -> None:
    pdf_path = tmp_path / "test.pdf"
    write_sample_pdf(pdf_path)

    text = extract_pdf_text(pdf_path)
    assert "Hello PDF" in text


def test_corrupted_file_handling(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "corrupted.pdf").write_bytes(b"not a pdf")

    loader = UniversalDocumentLoader(
        root_directory=root,
        recursive=True,
        show_progress=False,
        use_multithreading=False,
    )

    docs = loader.load()
    assert docs == []
    assert len(loader.errors) == 1


def test_metadata_completeness(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "test.txt").write_text("hello")

    loader = UniversalDocumentLoader(
        root_directory=root,
        recursive=True,
        show_progress=False,
        use_multithreading=False,
    )
    docs = loader.load()

    assert len(docs) == 1
    metadata = docs[0].metadata
    assert "source" in metadata
    assert "file_type" in metadata
    assert "size_bytes" in metadata
    assert "modified_at" in metadata
