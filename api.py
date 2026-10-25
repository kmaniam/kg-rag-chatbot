
import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi import Header
def verify_admin_token(x_nexora_token: str = Header(default="")):
    expected = os.getenv("NEXORA_ADMIN_TOKEN", "")
    if not expected or x_nexora_token != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing admin token.",
        )
from rag_pipeline import (
    document_count,
    extract_text,
    ingest_document,
    search_documents,
    split_text,
    list_indexed_documents,
    get_indexed_document,
    delete_indexed_document,
)
from knowledge_graph import (
    add_relationship,
    graph_stats,
    remove_document_relationships,
    save_graph,
    search_graph,
)
from graph_extraction import extract_relationships
from llm_answer import generate_answer

app = FastAPI(
    title="NEXORA AI API",
    docs_url=None,
    redoc_url=None,
)

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "frontend" / "index.html")

FRONTEND_DIR = Path(__file__).parent / "frontend"


# The browser frontend will be served from the same domain.
# Keep the API same-origin; do not enable unrestricted CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    question: str


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "NEXORA AI"}


@app.get("/api/stats")
def stats():
    return {
        "indexed_chunks": document_count(),
        **graph_stats(),
    }

@app.get("/api/documents", dependencies=[Depends(verify_admin_token)])
def list_documents():
    return {"documents": list_indexed_documents()}


@app.delete(
    "/api/documents/{file_hash}",
    dependencies=[Depends(verify_admin_token)],
)
def remove_indexed_document(file_hash: str):
    import re

    if not re.fullmatch(r"[a-fA-F0-9]{64}", file_hash):
        raise HTTPException(status_code=400, detail="Invalid document identifier.")

    document = get_indexed_document(file_hash)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Graph relationships are currently tagged by filename, not file hash.
    # Refuse deletion if another indexed document has the same filename.
    same_name = [
        item for item in list_indexed_documents()
        if item["filename"] == document["filename"]
    ]
    if len(same_name) > 1:
        raise HTTPException(
            status_code=409,
            detail=(
                "Deletion blocked because multiple indexed files share this filename. "
                "Graph ownership must be disambiguated first."
            ),
        )

    removed_chunks = delete_indexed_document(file_hash)
    if removed_chunks == 0:
        raise HTTPException(status_code=404, detail="Document not found.")

    remove_document_relationships(document["filename"])
    save_graph()

    return {
        "ok": True,
        "filename": document["filename"],
        "chunks_removed": removed_chunks,
        "message": "Document and its attributable graph relationships were removed.",
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Enter a question.")

    try:
        vector_results = search_documents(question, top_k=3)
        graph_results = search_graph(question)
        answer = generate_answer(
            question,
            vector_results,
            graph_results,
        )

        sources = []
        for index, item in enumerate(vector_results, start=1):
            metadata = item.get("metadata", {})
            sources.append({
                "label": f"Document source {index}",
                "filename": metadata.get("source", "Unknown"),
                "text": item.get("text", ""),
                "distance": item.get("distance"),
            })

        return {
            "answer": answer,
            "sources": sources,
            "relationships": graph_results,
        }

    except Exception as exc:
        # Keep technical details in server logs, not in public responses.
        print(f"Chat request failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="The assistant could not generate an answer. Please try again.",
        ) from exc

@app.post("/api/upload", dependencies=[Depends(verify_admin_token)])
#@app.post("/api/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    results = []

    for uploaded in files:
        filename = Path(uploaded.filename or "upload.txt").name

        if Path(filename).suffix.lower() not in {".txt", ".pdf"}:
            results.append({
                "filename": filename,
                "ok": False,
                "error": "Only TXT and PDF files are supported.",
            })
            continue

        try:
            content = await uploaded.read()

            if not content:
                raise ValueError("The uploaded file is empty.")

            if len(content) > 10 * 1024 * 1024:
                raise ValueError("File size exceeds the 10 MB limit.")

            text = extract_text(filename, content)
            chunks = split_text(text)

            if not chunks:
                raise ValueError(
                    "No readable text found. Scanned PDFs need OCR."
                )

                        # Index the document first so graph extraction cannot block RAG.
            indexed_chunks = ingest_document(filename, content)

            relationships = []
            skipped_batches = 0
            graph_extraction_ok = False

            try:
                relationships, skipped_batches = extract_relationships(
                    chunks, filename
                )
                graph_extraction_ok = True
            except Exception as exc:
                skipped_batches = 1
                print(
                    f"Document indexed, but graph extraction failed for "
                    f"{filename}: {type(exc).__name__}: {exc}"
                )

            added = 0

            if graph_extraction_ok:
                remove_document_relationships(filename)

                for item in relationships:
                    if add_relationship(
                        item["source"],
                        item["relation"],
                        item["target"],
                        document=filename,
                    ):
                        added += 1

                save_graph()

            added = 0
            for item in relationships:
                if add_relationship(
                    item["source"],
                    item["relation"],
                    item["target"],
                    document=filename,
                ):
                    added += 1

            save_graph()

            results.append({
                "filename": filename,
                "ok": True,
                "chunks": indexed_chunks,
                "relationships_extracted": len(relationships),
                "relationships_added": added,
                "skipped_batches": skipped_batches,
            })

        except Exception as exc:
            print(f"Upload failed for {filename}: {type(exc).__name__}: {exc}")
            results.append({
                "filename": filename,
                "ok": False,
                "error": "Indexing failed. Check the server logs.",
            })

        finally:
            await uploaded.close()

    return {"results": results, "stats": stats()}


@app.get("/api/evidence")
def evidence(question: str):
    question = question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Enter a question.")

    return {
        "sources": search_documents(question, top_k=3),
        "relationships": search_graph(question),
    }

