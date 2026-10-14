"""
scripts/setup_client.py
──────────────────────────────────────────────────────────────────────
All-in-One Client Setup Tool.

Configure everything for ANY hotel or company in ONE place:
- Name, ID, Website URL
- Contact details (Phone, Email, Address)
- Knowledge from PDF (.pdf) and Word (.docx) documents ONLY

Usage Option 1 (using client_config.json):
    python scripts/setup_client.py --config client_config.json

Usage Option 2 (via command-line arguments):
    python scripts/setup_client.py \
        --id grand_hotel \
        --name "Grand Palace Hotel" \
        --url "https://grandpalacehotel.com" \
        --phone "+91 9876543210" \
        --email "reservations@grandpalacehotel.com" \
        --address "Marine Drive, Puri, Odisha" \
        --docs "data/grand_hotel/docs"
──────────────────────────────────────────────────────────────────────
"""

import os
import sys
import json
import argparse
from datetime import date
from dotenv import load_dotenv

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

load_dotenv(os.path.join(REPO_ROOT, "backend", ".env"))

from app.services.pipeline.document_extractor import (
    extract_documents_from_directory,
    extract_document,
)
from app.services.pipeline.chunk import chunk_pages
from app.services.pipeline.ingest import ingest_chunks
from app.config import WEBSITES_CONFIG_PATH


def update_websites_registry(
    website_id: str,
    display_name: str,
    base_url: str,
    contact: dict,
    set_active: bool = True
) -> None:
    """Updates data/websites.json and sets the active tenant."""
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
        "base_url": base_url or "documents",
        "active": True,
        "onboarded_at": date.today().isoformat(),
        "contact": contact or {},
    }

    if existing:
        existing.update(entry)
    else:
        sites.append(entry)

    if set_active:
        data["active_id"] = website_id

    os.makedirs(os.path.dirname(WEBSITES_CONFIG_PATH), exist_ok=True)
    with open(WEBSITES_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Updated registry: '{display_name}' ({website_id}) is now ACTIVE in {WEBSITES_CONFIG_PATH}")


def setup_client(
    website_id: str,
    display_name: str,
    website_url: str,
    contact: dict,
    docs_source: str,
) -> None:
    print("=" * 70)
    print(f"  SETTING UP CLIENT: {display_name} ({website_id})")
    print("=" * 70)
    print(f"  Website URL: {website_url or 'N/A'}")
    print(f"  Phone:       {contact.get('phone', 'N/A')}")
    print(f"  Email:       {contact.get('email', 'N/A')}")
    print(f"  Address:     {contact.get('address', 'N/A')}")
    print(f"  Documents:   {docs_source or 'None'}")
    print("-" * 70)

    pages = []
    if docs_source:
        if os.path.isdir(docs_source):
            pages = extract_documents_from_directory(docs_source)
        elif os.path.isfile(docs_source):
            pages = extract_document(docs_source, os.path.basename(docs_source))
        else:
            print(f"Warning: Document path '{docs_source}' does not exist.")

    if not pages:
        print("✗ No PDF or Word (.docx) documents were extracted.")
        print("  Please make sure your files end with .pdf or .docx.")
        print("  (Text files are ignored as requested).")
        sys.exit(1)

    print(f"✓ Successfully extracted {len(pages)} sections/pages from documents.")

    # 2. Chunking
    chunks = chunk_pages(website_id, pages)
    print(f"✓ Created {len(chunks)} contextual chunks.")

    # Save chunks for reference
    processed_dir = os.path.join(REPO_ROOT, "data", website_id, "processed")
    os.makedirs(processed_dir, exist_ok=True)
    with open(os.path.join(processed_dir, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

    # 3. Embedding and Ingestion into Qdrant
    print("Indexing into Qdrant vector database...")
    points = ingest_chunks(chunks)
    print(f"✓ Successfully indexed {points} vectors in Qdrant!")

    # 4. Update websites.json
    update_websites_registry(
        website_id=website_id,
        display_name=display_name,
        base_url=website_url,
        contact=contact,
        set_active=True,
    )

    print("=" * 70)
    print(f"  SUCCESS! {display_name} is configured and LIVE.")
    print("  • Backend RAG will now use this company's details & documents.")
    print("  • Frontend Chat Widget will automatically display this assistant.")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Configure and train assistant for any hotel/company in ONE place")
    parser.add_argument("--config", help="Path to client_config.json file")
    parser.add_argument("--id", help="Company ID / slug, e.g. 'grand_hotel'")
    parser.add_argument("--name", help="Display name, e.g. 'Grand Palace Hotel'")
    parser.add_argument("--url", default="", help="Website URL")
    parser.add_argument("--phone", default="", help="Phone number")
    parser.add_argument("--email", default="", help="Email address")
    parser.add_argument("--address", default="", help="Physical address")
    parser.add_argument("--docs", default="", help="Path to PDF/DOCX file or folder")

    args = parser.parse_args()

    if args.config:
        if not os.path.isfile(args.config):
            print(f"Error: Config file not found: {args.config}")
            sys.exit(1)
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        setup_client(
            website_id=cfg["website_id"],
            display_name=cfg["display_name"],
            website_url=cfg.get("website_url", ""),
            contact=cfg.get("contact", {}),
            docs_source=cfg.get("docs_dir") or cfg.get("documents", ""),
        )
    else:
        if not args.id or not args.name or not args.docs:
            print("Error: Missing required arguments. Either specify --config client_config.json")
            print("or provide: --id <id> --name <name> --docs <path_to_pdf_or_folder>")
            sys.exit(1)

        contact = {
            "phone": args.phone,
            "email": args.email,
            "address": args.address,
        }
        setup_client(
            website_id=args.id,
            display_name=args.name,
            website_url=args.url,
            contact=contact,
            docs_source=args.docs,
        )


if __name__ == "__main__":
    main()
