"""
app/services/finetune_service.py
──────────────────────────────────────────────────────────────────────
Background service to generate instruction-tuning (JSONL) datasets from
company chunks.
──────────────────────────────────────────────────────────────────────
"""

import os
import json
import logging
from langchain_groq import ChatGroq
from app.config import GROQ_API_KEY, GROQ_MODEL, BASE_DIR, get_website_info
from app.services import job_store

logger = logging.getLogger(__name__)


def generate_finetune_dataset_task(job_id: str, website_id: str, max_chunks: int = 40) -> None:
    try:
        job_store.update_job(job_id, status="generating_finetune_data")
        chunks_file = os.path.join(BASE_DIR, "data", website_id, "processed", "chunks.json")
        if not os.path.exists(chunks_file):
            raise FileNotFoundError(f"No processed chunks found for '{website_id}'. Please ingest documents first.")

        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        if not chunks:
            raise ValueError(f"Chunks file for '{website_id}' is empty.")

        info = get_website_info(website_id)
        company_name = info.get("display_name", website_id.replace("_", " ").title())

        output_dir = os.path.join(BASE_DIR, "data", website_id)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "finetune_data.jsonl")

        llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name="llama-3.1-8b-instant" if "gpt-oss" in GROQ_MODEL else GROQ_MODEL,
            temperature=0.3,
            max_tokens=600,
        )

        dataset = []
        selected_chunks = chunks[:max_chunks]

        for idx, chunk in enumerate(selected_chunks, start=1):
            text = chunk.get("chunk_text", "")
            if len(text) < 60:
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
                raw = res.content.strip()
                if raw.startswith("```json"):
                    raw = raw[7:]
                if raw.startswith("```"):
                    raw = raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

                pairs = json.loads(raw)
                for pair in pairs:
                    dataset.append({
                        "messages": [
                            {"role": "system", "content": f"You are a professional and helpful AI assistant for {company_name}."},
                            {"role": "user", "content": pair["question"]},
                            {"role": "assistant", "content": pair["answer"]}
                        ]
                    })
            except Exception as e:
                logger.warning("Error generating pair for chunk %d: %s", idx, e)

        with open(output_file, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item) + "\n")

        job_store.update_job(job_id, status="completed", points_ingested=len(dataset))
        logger.info("Successfully generated %d fine-tuning examples in %s", len(dataset), output_file)

    except Exception as e:
        logger.exception("Fine-tuning data generation failed: %s", e)
        job_store.update_job(job_id, status="failed", error=str(e))
