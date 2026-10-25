import json
import os

from openai import OpenAI

MAX_CHUNKS_PER_REQUEST = 1
MAX_BATCHES_PER_DOCUMENT = 20


def extract_relationships(chunks, source_document):
    """Extract document-supported subject–relation–object triples."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    model = os.getenv("OPENAI_MODEL", "gpt-5-nano")
    client = OpenAI(api_key=api_key, timeout=60.0, max_retries=1)

    relationships = []
    batches = [
        chunks[i:i + MAX_CHUNKS_PER_REQUEST]
        for i in range(0, len(chunks), MAX_CHUNKS_PER_REQUEST)
    ]
    batches_to_process = batches[:MAX_BATCHES_PER_DOCUMENT]

    for batch_number, batch in enumerate(batches_to_process, start=1):
        text = "\n\n".join(batch)[:2500]

        response = client.responses.create(
            model=model,
            reasoning={"effort": "low"},
            instructions=(
                "Extract factual knowledge graph relationships from the "
                "provided document text. Return ONLY valid JSON with this "
                'shape: {"relationships":[{"source":"...","relation":"...",'
                '"target":"..."}]}. Each relationship must be directly '
                "supported by the text. Use concise entity names and short "
                "verb phrases. Do not infer unsupported facts. Do not use "
                "outside knowledge. If there are no supported relationships, "
                'return {"relationships":[]}. Maximum 20 relationships.'
            ),
            input=f"Source document: {source_document}\n\nDocument text:\n{text}",
            max_output_tokens=1200,
        )

        if response.status != "completed":
            reason = getattr(response.incomplete_details, "reason", None)
            print(
                f"Skipping graph extraction batch {batch_number}: "
                f"{response.status}; reason={reason}"
            )
            continue
        output = response.output_text.strip()
        if not output:
            raise RuntimeError(
                f"Graph extraction batch {batch_number} returned no text."
            )

        # Be tolerant if the model wraps JSON in a Markdown code fence.
        output = output.removeprefix("```json").removeprefix("```")
        output = output.removesuffix("```").strip()
        data = json.loads(output)

        for item in data.get("relationships", []):
            source = str(item.get("source", "")).strip()
            relation = str(item.get("relation", "")).strip()
            target = str(item.get("target", "")).strip()

            if source and relation and target:
                relationships.append({
                    "source": source[:200],
                    "relation": relation[:100],
                    "target": target[:200],
                })

    skipped_batches = len(batches) - len(batches_to_process)
    return relationships, skipped_batches
