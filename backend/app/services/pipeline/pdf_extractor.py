"""
app/services/pipeline/pdf_extractor.py
──────────────────────────────────────────────────────────────────────
Extracts clean, readable text from PDF documents page by page.
Supports local files, byte streams (FastAPI UploadFile), and directories.
──────────────────────────────────────────────────────────────────────
"""

import os
import io
import re
import logging
from typing import BinaryIO, Union
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def clean_extracted_text(text: str) -> str:
    """Clean up extracted PDF text, normalizing whitespace and line breaks."""
    if not text:
        return ""
    # Collapse multiple spaces into one
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse more than 2 consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove surrogate characters / invalid unicode if any
    text = text.encode("utf-8", "ignore").decode("utf-8")
    return text.strip()


def extract_pages_from_pdf(
    source: Union[str, bytes, BinaryIO],
    filename: str = "document.pdf"
) -> list[dict]:
    """
    Extracts text page-by-page from a PDF file path or byte stream.

    Returns:
        list of dicts: [
            {
                "url": f"{filename}#page={page_num}",
                "page_title": f"{filename} (Page {page_num})",
                "page_type": "pdf_document",
                "doc_type": "pdf",
                "text": str,
                "page_number": int,
                "source_file": filename
            },
            ...
        ]
    """
    if isinstance(source, bytes):
        stream = io.BytesIO(source)
    elif isinstance(source, str):
        if not os.path.exists(source):
            raise FileNotFoundError(f"PDF file not found: {source}")
        stream = open(source, "rb")
    else:
        stream = source

    try:
        reader = PdfReader(stream)
        total_pages = len(reader.pages)
        logger.info("Extracting %d pages from PDF: %s", total_pages, filename)

        pages = []
        for idx, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            cleaned = clean_extracted_text(raw_text)

            if len(cleaned) < 40:
                logger.debug("Skipping page %d of %s (insufficient text)", idx, filename)
                continue

            clean_filename = os.path.basename(filename)
            pages.append({
                "url": f"{clean_filename}#page={idx}",
                "page_title": f"{clean_filename} - Page {idx}",
                "page_type": "pdf_document",
                "doc_type": "pdf",
                "text": cleaned,
                "page_number": idx,
                "source_file": clean_filename,
            })

        logger.info("Successfully extracted %d usable pages from %s", len(pages), filename)
        return pages

    except Exception as e:
        logger.error("Failed to extract text from PDF %s: %s", filename, e)
        raise RuntimeError(f"Error processing PDF '{filename}': {e}") from e

    finally:
        if isinstance(source, str) and hasattr(stream, "close"):
            stream.close()


def extract_pdfs_from_directory(dir_path: str) -> list[dict]:
    """Extracts text from all PDF files inside a directory."""
    if not os.path.isdir(dir_path):
        raise NotADirectoryError(f"Directory not found: {dir_path}")

    all_pages = []
    pdf_files = [f for f in os.listdir(dir_path) if f.lower().endswith(".pdf")]
    logger.info("Found %d PDF file(s) in %s", len(pdf_files), dir_path)

    for pdf_file in sorted(pdf_files):
        full_path = os.path.join(dir_path, pdf_file)
        pages = extract_pages_from_pdf(full_path, filename=pdf_file)
        all_pages.extend(pages)

    return all_pages
