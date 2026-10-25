import hashlib
import re
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from pypdf import PdfReader

DATA_DIR = Path("/app/data")
DB_DIR = DATA_DIR / "chroma_db"
DOCS_DIR = DATA_DIR / "documents"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

embedding_function = DefaultEmbeddingFunction()

client = chromadb.PersistentClient(path=str(DB_DIR))

collection = client.get_or_create_collection(
    name="knowledge_documents",
    embedding_function=embedding_function,
    metadata={"description": "KG-RAG knowledge assistant documents"},
)


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".txt":
        return content.decode("utf-8", errors="replace")

    if suffix == ".pdf":
        import io
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    raise ValueError("Only TXT and PDF files are supported.")


def split_text(text: str, chunk_size: int = 800, overlap: int = 120):
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


def ingest_document(filename: str, content: bytes) -> int:
    text = extract_text(filename, content)
    chunks = split_text(text)

    if not chunks:
        raise ValueError(
            "No readable text found. Scanned PDFs need OCR."
        )

    file_hash = hashlib.sha256(content).hexdigest()
    safe_name = Path(filename).name

    # Use a stable ID so re-uploading the same file does not duplicate it.
    collection.delete(where={"file_hash": file_hash})

    ids = [
        f"{file_hash}_{i}"
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=[
            {
                "source": safe_name,
                "file_hash": file_hash,
                "chunk": i,
            }
            for i in range(len(chunks))
        ],
    )

    return len(chunks)


def search_documents(question: str, top_k: int = 3):
    if collection.count() == 0:
        return []

    result = collection.query(
        query_texts=[question],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    # Configurable Chroma distance threshold; lower is a closer match.
    max_distance = float(__import__("os").getenv(
        "RAG_MAX_DISTANCE", "1.0"
    ))

    matches = []

    for i, document in enumerate(result["documents"][0]):
        distance = float(result["distances"][0][i])

        if distance > max_distance:
            continue

        matches.append({
            "text": document,
            "metadata": result["metadatas"][0][i],
            "distance": distance,
        })

    return matches

def document_count() -> int:
    return collection.count()


def list_indexed_documents():
    """List indexed documents grouped by their content hash."""
    result = collection.get(include=["metadatas"])
    documents = {}

    for metadata in result.get("metadatas") or []:
        if not metadata:
            continue

        file_hash = metadata.get("file_hash")
        filename = metadata.get("source", "Unknown")

        if not file_hash:
            continue

        if file_hash not in documents:
            documents[file_hash] = {
                "file_hash": file_hash,
                "filename": filename,
                "chunks": 0,
            }

        documents[file_hash]["chunks"] += 1

    return sorted(
        documents.values(),
        key=lambda item: item["filename"].casefold(),
    )


def get_indexed_document(file_hash: str):
    """Return metadata for one exact indexed document."""
    result = collection.get(
        where={"file_hash": file_hash},
        include=["metadatas"],
    )

    metadatas = result.get("metadatas") or []
    if not metadatas:
        return None

    return {
        "file_hash": file_hash,
        "filename": metadatas[0].get("source", "Unknown"),
        "chunks": len(metadatas),
    }


def delete_indexed_document(file_hash: str) -> int:
    """Delete chunks belonging to one exact file hash."""
    document = get_indexed_document(file_hash)
    if not document:
        return 0

    collection.delete(where={"file_hash": file_hash})
    return document["chunks"]
