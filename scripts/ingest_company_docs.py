"""
scripts/ingest_company_docs.py
──────────────────────────────────────────────────────────────────────
CLI tool to ingest PDF documents for ANY company into the RAG system.

Usage:
  # Ingest a single PDF:
  python scripts/ingest_company_docs.py --company grand_hotel --name "Grand Palace Hotel" --pdf path/to/brochure.pdf

  # Ingest an entire directory of PDFs:
  python scripts/ingest_company_docs.py --company grand_hotel --name "Grand Palace Hotel" --dir path/to/pdf_folder/
──────────────────────────────────────────────────────────────────────
"""

import os
import sys
import json
import argparse
from datetime import date
from dotenv import load_dotenv

# Ensure root directory is on python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

load_dotenv(os.path.join(REPO_ROOT, "backend", ".env"))

from app.services.pipeline.pdf_extractor import extract_pages_from_pdf, extract_pdfs_from_directory
from app.services.pipeline.chunk import chunk_pages
from app.services.pipeline.ingest import ingest_chunks
from app.config import WEBSITES_CONFIG_PATH


def register_company(website_id: str, display_name: str) -> None:
    """Register or update company in data/websites.json."""
    try:
        with open(WEBSITES_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"websites": []}

    sites = data.setdefault("websites", [])
    existing = next((s for s in sites if s.get("website_id") == website_id), None)

    entry = {
        "website_id": website_id,
        "display_name": display_name,
        "base_url": "uploaded_documents",
        "active": True,
        "onboarded_at": date.today().isoformat(),
    }

    if existing:
        existing.update(entry)
    else:
        sites.append(entry)

    os.makedirs(os.path.dirname(WEBSITES_CONFIG_PATH), exist_ok=True)
    with open(WEBSITES_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Registered company '{display_name}' ({website_id}) in {WEBSITES_CONFIG_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Ingest company PDFs into Qdrant for RAG assistant")
    parser.add_argument("--company", required=True, help="Unique company/tenant ID, e.g., 'grand_hotel'")
    parser.add_argument("--name", required=True, help="Display name, e.g., 'Grand Palace Hotel'")
    parser.add_argument("--pdf", help="Path to a single PDF file")
    parser.add_argument("--dir", help="Path to a directory containing PDF files")

    args = parser.parse_args()

    if not args.pdf and not args.dir:
        print("Error: You must provide either --pdf <filepath> or --dir <folderpath>")
        sys.exit(1)

    print("=" * 65)
    print(f"  Ingesting PDF Documents for: {args.name} ({args.company})")
    print("=" * 65)

    # 1. Extract pages from PDF(s)
    pages = []
    if args.pdf:
        if not os.path.isfile(args.pdf):
            print(f"Error: File not found: {args.pdf}")
            sys.exit(1)
        pages = extract_pages_from_pdf(args.pdf, filename=os.path.basename(args.pdf))
    elif args.dir:
        if not os.path.isdir(args.dir):
            print(f"Error: Directory not found: {args.dir}")
            sys.exit(1)
        pages = extract_pdfs_from_directory(args.dir)

    if not pages:
        print("✗ No usable text extracted from the provided PDF(s).")
        sys.exit(1)

    print(f"✓ Extracted {len(pages)} page(s) of content.")

    # 2. Chunk text
    chunks = chunk_pages(args.company, pages)
    print(f"✓ Generated {len(chunks)} text chunks.")

    # Save chunks to data/{company}/processed/chunks.json for backup and fine-tuning
    processed_dir = os.path.join(REPO_ROOT, "data", args.company, "processed")
    os.makedirs(processed_dir, exist_ok=True)
    chunks_path = os.path.join(processed_dir, "chunks.json")
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)
    print(f"✓ Saved chunk metadata to {chunks_path}")

    # 3. Ingest into Qdrant
    print("Ingesting chunks into Qdrant vector database...")
    points_ingested = ingest_chunks(chunks)
    print(f"✓ Successfully indexed {points_ingested} points in Qdrant!")

    # 4. Register in websites.json
    register_company(args.company, args.name)

    print("=" * 65)
    print(f"  SUCCESS! {args.name} is now live in the Multi-Tenant Assistant.")
    print(f"  You can now query /api/v1/chat with website_id='{args.company}'")
    print("=" * 65)


if __name__ == "__main__":
    main()
