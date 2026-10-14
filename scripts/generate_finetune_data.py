"""
scripts/generate_finetune_data.py
──────────────────────────────────────────────────────────────────────
Generates an instruction-tuning dataset (JSONL format) from any company's
processed chunks (from PDFs or URLs).

Usage:
  python scripts/generate_finetune_data.py --company grand_hotel --max-chunks 50
──────────────────────────────────────────────────────────────────────
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

load_dotenv(os.path.join(REPO_ROOT, "backend", ".env"))

from langchain_groq import ChatGroq
from app.config import GROQ_API_KEY, GROQ_MODEL, get_website_info


def main():
    parser = argparse.ArgumentParser(description="Generate fine-tuning Q&A dataset from company chunks")
    parser.add_argument("--company", required=True, help="Company ID (e.g., 'crushaders_tech', 'grand_hotel')")
    parser.add_argument("--max-chunks", type=int, default=40, help="Maximum number of chunks to process")
    parser.add_argument("--output", help="Optional output JSONL file path")

    args = parser.parse_args()

    chunks_file = os.path.join(REPO_ROOT, "data", args.company, "processed", "chunks.json")
    if not os.path.exists(chunks_file):
        print(f"Error: Chunks file not found at {chunks_file}")
        print("Please ingest company data first using scrape_site.py or ingest_company_docs.py.")
        sys.exit(1)

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        print("Error: No chunks found in chunks.json.")
        sys.exit(1)

    info = get_website_info(args.company)
    company_name = info.get("display_name", args.company.replace("_", " ").title())

    output_path = args.output or os.path.join(REPO_ROOT, "data", args.company, "finetune_data.jsonl")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("=" * 65)
    print(f"  Generating Fine-Tuning Data for: {company_name} ({args.company})")
    print(f"  Input Chunks: {min(len(chunks), args.max_chunks)}")
    print(f"  Output File:  {output_path}")
    print("=" * 65)

    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant" if "gpt-oss" in GROQ_MODEL else GROQ_MODEL,
        temperature=0.3,
        max_tokens=600,
    )

    dataset = []
    selected_chunks = chunks[:args.max_chunks]

    for idx, chunk in enumerate(selected_chunks, start=1):
        text = chunk.get("chunk_text", "")
        if len(text) < 80:
            continue

        prompt = f"""You are creating training data for an AI assistant representing {company_name}.
Based solely on the following context, generate 2 natural user questions and accurate, professional answers.

CONTEXT:
\"\"\"{text}\"\"\"

Format your output STRICTLY as a JSON array of objects:
[
  {{"question": "user question 1", "answer": "assistant answer 1"}},
  {{"question": "user question 2", "answer": "assistant answer 2"}}
]
Do not include any explanation or markdown formatting other than raw JSON."""

        try:
            res = llm.invoke(prompt)
            raw_content = res.content.strip()
            # Clean possible markdown fence
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            if raw_content.startswith("```"):
                raw_content = raw_content[3:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
            raw_content = raw_content.strip()

            pairs = json.loads(raw_content)
            for pair in pairs:
                dataset.append({
                    "messages": [
                        {"role": "system", "content": f"You are a professional and helpful AI assistant for {company_name}."},
                        {"role": "user", "content": pair["question"]},
                        {"role": "assistant", "content": pair["answer"]}
                    ]
                })
            print(f"  [{idx}/{len(selected_chunks)}] Generated {len(pairs)} pairs from chunk {chunk.get('chunk_index', idx)}")
        except Exception as e:
            print(f"  [{idx}/{len(selected_chunks)}] Skipped chunk due to error: {e}")
            continue

    with open(output_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")

    print("=" * 65)
    print(f"✓ DONE! Generated {len(dataset)} training examples in {output_path}")
    print("  You can now use this JSONL file to fine-tune any model (OpenAI, LoRA, Unsloth, etc.)!")
    print("=" * 65)


if __name__ == "__main__":
    main()
