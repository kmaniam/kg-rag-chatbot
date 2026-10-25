# 🧠 NEXORA AI — KG-RAG Knowledge Assistant

**A Hybrid Retrieval-Augmented Generation (RAG) Application Powered by Chroma, NetworkX, FastAPI, and OpenAI**

NEXORA AI is an AI-powered knowledge assistant that combines document-based retrieval with knowledge graph exploration to help users find relevant technical information and generate evidence-grounded answers.

The project demonstrates how Retrieval-Augmented Generation, vector search, graph-based knowledge representation, and large language models can work together in a practical, containerized application.

## 🚀 Project Objectives

- Build a knowledge assistant that answers questions using indexed documents.
- Retrieve relevant document chunks using vector similarity search.
- Extract and explore entities and relationships through a knowledge graph.
- Provide source evidence alongside generated answers.
- Support PDF and TXT document uploads.
- Implement administrator authorization for document indexing, listing, and deletion.
- Deploy the application using Docker on an Ubuntu VPS.

## ✨ Key Features

### 1. Hybrid RAG Architecture
Combines document retrieval and knowledge graph search to provide relevant context for AI-generated answers.

### 2. Document Indexing
- Upload PDF and TXT documents.
- Extract readable text and split it into manageable chunks.
- Store document chunks in Chroma.
- Identify indexed documents using SHA-256 content hashes.
- Filter out search results that do not meet the configured relevance threshold.

### 3. Knowledge Graph
- Extract factual relationships from document content.
- Represent entities and relationships using NetworkX.
- Persist graph data for reuse between application restarts.
- Explore relevant relationships alongside document evidence.

### 4. Evidence-Based Answers
The application retrieves relevant document passages and graph relationships before generating an answer. When sufficient supporting evidence is unavailable, the application can return an insufficient-evidence response instead of relying on unsupported information.

### 5. Document Management and Security
- Token-protected document uploads.
- Administrator-authorized document listing.
- Explicit confirmation and administrator token validation for deletion.
- Deletion of document chunks using the document's content hash.
- Protection against ambiguous graph cleanup when multiple documents share a filename.

### 6. Web Interface
A custom NEXORA AI interface provides:
- Interactive question-and-answer chat.
- Retrieved source evidence.
- Knowledge graph information.
- Indexed chunk and graph statistics.
- Document upload and management controls.

## 🏗️ Technology Stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Vector database | Chroma |
| Knowledge graph | NetworkX |
| Language model | OpenAI API |
| Embeddings | Chroma default embedding function |
| PDF extraction | pypdf |
| Application server | Uvicorn |
| Containerization | Docker and Docker Compose |
| VPS operating system | Ubuntu 24.04 LTS |
| HTTPS routing | Traefik |

## 🔄 How It Works

1. An administrator uploads a PDF or TXT document.
2. The application extracts the document's text.
3. The text is split into smaller chunks.
4. Chroma stores the chunks and their metadata for retrieval.
5. The application extracts factual relationships for the knowledge graph.
6. A user submits a technical question.
7. The application searches the document collection and knowledge graph.
8. Relevant evidence is passed to the language model.
9. The assistant generates an answer and displays retrieved source passages.

## 🗺️ Architecture

```text
                  User / Administrator
                           |
                           v
                 NEXORA AI Web Interface
                    HTML / CSS / JS
                           |
                           v
                    FastAPI Backend
                     /           \
                    /             \
                   v               v
           Chroma Vector DB    NetworkX Graph
           Document Chunks    Entities & Relations
                   \               /
                    \             /
                     v           v
                     Retrieval
                          |
                          v
                    OpenAI API
                          |
                          v
                 Evidence-Grounded Answer
```

## 🔐 Security Considerations

- Administrative endpoints require a valid `NEXORA_ADMIN_TOKEN`.
- The backend performs authorization checks independently of the frontend.
- The application should never expose API keys or administrator tokens in source code.
- Environment files, indexed data, logs, and private credentials must not be committed to GitHub.
- Production deployments should use HTTPS and appropriate access controls.

**Important:** Administrator token validation is currently based on a shared secret. A production multi-user deployment should introduce individual accounts, role-based access control, audit logging, and stronger credential-management practices.

## 🐳 Running with Docker

### Prerequisites

- Docker Engine
- Docker Compose
- An OpenAI API key
- A configured administrator token

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_REPOSITORY_DIRECTORY>
```

### 2. Configure environment variables

Create a local `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-nano
NEXORA_ADMIN_TOKEN=replace_with_a_strong_secret
RAG_MAX_DISTANCE=1.0
```

Use the model and settings appropriate for your deployment. Never commit the real `.env` file.

### 3. Build and start the application

```bash
docker compose up -d --build
```

### 4. Check the container

```bash
docker compose ps
docker compose logs --tail 100 chatbot
```

If the application is configured for local port 8000, check its health endpoint:

```bash
curl http://127.0.0.1:8000/api/health
```

Refer to `compose.yaml` and the deployment configuration for the actual port and networking requirements.

## 📁 Project Structure

```text
kg-rag-chatbot/
├── api.py
├── rag_pipeline.py
├── knowledge_graph.py
├── graph_extraction.py
├── llm_answer.py
├── seed_graph.py
├── frontend/
│   └── index.html
├── Dockerfile
├── compose.yaml
├── .env.example
├── .gitignore
└── README.md
```

The data directory is created and mounted separately for persistent vector database and graph storage. Do not commit production data unless it has been reviewed and intentionally sanitized.

## 🧪 Validation and Testing

The project has been tested with:
- Python syntax validation.
- Document indexing and retrieval.
- Evidence citation navigation.
- Relevance filtering for unrelated questions.
- Document upload and indexing feedback.
- Document management through the web interface.
- Unauthorized document-listing and deletion requests returning HTTP 401.

These checks validate specific application behaviors; they do not replace a complete security audit or automated regression test suite.

## 🔮 Future Enhancements

- Administrator audit logs for uploads and deletions.
- Individual administrator accounts and role-based access control.
- Automated tests for the API and RAG pipeline.
- Improved graph extraction retry and recovery handling.
- Document versioning and re-indexing controls.
- Search and graph visualization improvements.
- Evaluation of retrieval relevance and answer quality.
- Monitoring, metrics, and production deployment automation.

## 👨‍💻 Author

**Kesavaraj Subramaniam**

Database Engineering | Oracle DBA | Database Automation | Generative AI | RAG Applications

This project represents my practical exploration of AI-powered knowledge retrieval, knowledge graphs, and containerized application development.

---

*Built as a learning and engineering project to explore practical applications of Generative AI and Retrieval-Augmented Generation.*
