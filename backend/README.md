# Smart Doc Agent Backend

Flask backend service powering document ingestion, metadata extraction, vector search, and RAG retrieval.

## Directory Structure

```
backend/
├── data/              # BM25 index and datasets
│   └── bm25_index/
├── rag/               # Core RAG pipeline, services, and Flask application
│   ├── app.py         # Main Flask server entry point
│   ├── chunker/       # Document chunking logic
│   ├── config/        # Environment and retrieval configurations
│   ├── documents/     # Document repository and services
│   ├── embedder/      # Dense vector embedding models
│   ├── evaluation/    # Evaluation metrics and datasets
│   ├── ingestion/     # Parsing and ingestion pipeline
│   ├── intent/        # Small Language Model (SLM) intent extractor & schemas
│   ├── language_models/ # SLM and LLM connectors (Groq, Gemini)
│   ├── lib/           # Supabase and AWS S3 integrations
│   ├── loader/        # File loaders (PDF, DOCX, etc.)
│   ├── modules/       # Flask blueprints (auth, user)
│   ├── query_engine/  # Router and query rewrite services
│   ├── s3/            # AWS S3 presigned URL and storage service
│   ├── services/      # Dense/Sparse retrievers, fusion, and reranker
│   └── utils/         # Helper utilities
├── src/               # Package entrypoint for CLI execution
├── supabase/          # Database schema migrations
├── tests/             # Unit and integration test suites
├── pyproject.toml     # Python dependencies and project settings (managed via uv)
└── requirements.txt   # Exported requirements
```

## Running the Backend

### Using `uv`:
```bash
cd backend
uv run python rag/app.py
```

### Running Tests:
```bash
cd backend
python3 -m unittest discover tests
```
