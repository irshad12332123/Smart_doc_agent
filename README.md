# Smart Doc Agent

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=20232A)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![Flask](https://img.shields.io/badge/Flask-3-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL%20%7C%20pgvector-3FCF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![Amazon S3](https://img.shields.io/badge/Amazon%20S3-Object%20Storage-569A31?logo=amazons3&logoColor=white)](https://aws.amazon.com/s3/)
[![Celery](https://img.shields.io/badge/Celery-Async%20Jobs-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-Job%20Broker-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![RAG](https://img.shields.io/badge/RAG-Hybrid%20Retrieval-6E56CF)](#architecture)
[![BM25](https://img.shields.io/badge/Search-BM25%20%2B%20Dense%20Vectors-0F766E)](#features)

Smart Doc Agent is an academic document intelligence platform for uploading, organizing, and querying course material. It combines scoped access control with asynchronous document ingestion, structured metadata extraction, hybrid retrieval, and evidence-aware answers.

The repository contains a React/TypeScript web application and a Python/Flask RAG backend. Documents are stored in Amazon S3, metadata and vector chunks are stored in Supabase/Postgres, and sparse retrieval is maintained locally with BM25S.

## Features

- Role-aware authentication for students, faculty, and administrators.
- Academic scoping by course, semester, batch, subject, and unit.
- Upload and deduplication of PDF, DOCX, TXT, and Markdown files.
- Background ingestion through Celery and Redis.
- Structured metadata extraction with Groq, including document type, summary, deadline, and unit.
- Gemini-powered embeddings and answer generation.
- Hybrid retrieval combining dense vector search and BM25 sparse search.
- Reciprocal Rank Fusion with optional cross-encoder reranking.
- Deterministic document lookup for metadata and filter-based queries.
- Streaming chat responses with source and document references.
- Supabase migrations for authentication, academic scope, document lookup, and ingestion jobs.

## Architecture

```text
                           +----------------------+
                           | React + TypeScript UI |
                           |        Vite           |
                           +----------+-----------+
                                      |
                                      | HTTP / SSE
                                      v
                           +----------+-----------+
                           | Flask API + Query     |
                           | orchestration graph   |
                           +-----+------------+----+
                                 |            |
                    upload/jobs  |            | query/chat
                                 v            v
                         +-------+----+  +----+----------------+
                         | Celery +   |  | Hybrid retrieval   |
                         | Redis      |  | dense + BM25 + RRF |
                         +-------+----+  +----+----------------+
                                 |            |
                                 v            v
             +-------------------+--+   +----+----------------+
             | S3 raw files         |   | Supabase/Postgres   |
             |                      |   | metadata + vectors |
             +----------------------+   +--------------------+
```

### Ingestion flow

1. An authorized user uploads one or more files with academic scope metadata.
2. The API hashes the file, rejects duplicates, uploads the original to S3, and creates an ingestion job.
3. A Celery worker loads and chunks the document.
4. Groq extracts structured document metadata and Gemini generates embeddings.
5. Document metadata and chunks are written to Supabase. The local BM25S index is regenerated.
6. The query graph can combine deterministic filters, dense retrieval, sparse retrieval, reranking, evidence evaluation, and answer generation.

## Technology stack

| Area | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, React Markdown, Lucide React |
| API | Python 3.12+, Flask |
| RAG orchestration | LangChain/LangGraph components, hybrid retrieval, RRF |
| Language models | Groq for metadata extraction; Gemini for embeddings and chat |
| Database and authentication | Supabase/PostgreSQL with `pgvector` and Row Level Security |
| Object storage | Amazon S3 with presigned URLs |
| Background processing | Celery with Redis |
| Sparse index | BM25S with PyStemmer |
| Python environment | `uv` |

## Repository layout

```text
.
├── backend/
│   ├── rag/                  # Flask application and RAG services
│   │   ├── app.py            # Application entry point
│   │   ├── ingestion/        # Upload and ingestion job routes
│   │   ├── services/         # Ingestion, retrieval, fusion, and reranking
│   │   ├── query_engine/     # Query routing and rewriting
│   │   ├── modules/          # Authentication and user modules
│   │   ├── loader/           # PDF, DOCX, text, and Markdown loading
│   │   └── async_engine/     # Celery application and tasks
│   ├── data/bm25_index/      # Persisted sparse index artifacts
│   ├── supabase/migrations/  # Database migrations, in timestamp order
│   ├── tests/                # Backend unit and integration tests
│   ├── pyproject.toml        # Python project configuration
│   └── .env.example          # Backend environment template
├── frontend/
│   ├── src/api/              # Backend API client and SSE handling
│   ├── src/features/         # Auth, upload, library, subjects, chat, profile
│   ├── src/components/       # Shared layout and UI components
│   └── .env.example          # Frontend environment template
└── README.md
```

## Prerequisites

- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 18 or newer and npm
- A Supabase project with the required extensions enabled
- An Amazon S3 bucket and credentials with access to that bucket
- A Groq API key
- A Gemini API key
- Redis, when using asynchronous ingestion

## Local setup

### 1. Configure Supabase

Apply the SQL migrations in `backend/supabase/migrations/` in timestamp order. You can run them through the Supabase CLI or the Supabase SQL editor. The migrations create the authentication registry, academic scope, document lookup functions, and asynchronous ingestion job tables.

The authentication flow expects student and faculty registry records to exist before users can register. See [`backend/rag/modules/auth/README.md`](backend/rag/modules/auth/README.md) for the registration workflow.

### 2. Configure and run the backend

```bash
cd backend
uv sync
cp .env.example .env
```

Set the values in `backend/.env` before starting the API. At minimum, configure the following:

```dotenv
GROQ_API_KEY=your-groq-api-key
GEMINI_API_KEY=your-gemini-api-key

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-publishable-key
SUPABASE_SERVICE_ROLE_KEY=your-server-only-service-role-key

AWS_ACCESS_KEY=your-access-key
AWS_SECRET_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

AUTH_REGISTRATION_TOKEN_SECRET=generate-a-long-random-secret
PORT=8000
```

The backend client reads `SUPABASE_KEY` for ordinary requests. If you use the supplied `.env.example`, copy the value from `SUPABASE_ANON_KEY` into `SUPABASE_KEY` or rename that variable in your local `.env`.

Start the Flask API:

```bash
uv run python rag/app.py
```

The API is available at `http://localhost:8000`. Verify the process is running with:

```bash
curl http://localhost:8000/api/health
```

### 3. Start Redis and the Celery worker

Redis must be reachable through `REDIS_URL`. The default used by the worker is `redis://localhost:6379/0` when no value is configured.

Start Redis using your local installation or managed Redis provider, then run the worker from the `backend` directory:

```bash
cd backend
PYTHONPATH=rag uv run celery -A async_engine.celery_app:celery worker --loglevel=info -Q ingestion
```

Without a running worker, upload requests can be accepted but remain queued or report an enqueue failure.

### 4. Configure and run the frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend environment should point to the backend:

```dotenv
BACKEND_API_URL=http://localhost:8000
```

The web application is available at `http://localhost:5173`.

## Configuration reference

The most commonly used backend settings are:

| Variable | Purpose | Default |
| --- | --- | --- |
| `PORT` | Flask port | `8000` |
| `GROQ_MODEL` | Groq metadata extraction model | `openai/gpt-oss-20b` |
| `GEMINI_MODEL_NAME` | Gemini chat model | `gemini-3.5-flash-lite` |
| `EMBEDDING_MODEL_NAME` | Embedding model | `google-embedding-2` |
| `EMBEDDING_DIMENSIONS` | Vector dimensions | `768` |
| `MAX_UPLOAD_BYTES` | Maximum upload size | `25 MB` |
| `S3_SIGNED_URL_TTL_SECONDS` | Presigned URL lifetime | `300` |
| `REDIS_URL` | Celery broker/result backend | local Redis URL |
| `BM25_INDEX_DIR` | Sparse index location | `backend/data/bm25_index` |
| `AUTH_ALLOWED_ORIGINS` | Comma-separated CORS allowlist | local origins |

Do not expose `SUPABASE_SERVICE_ROLE_KEY`, AWS secret credentials, or `AUTH_REGISTRATION_TOKEN_SECRET` to the browser.

## API overview

The Flask API is organized into authentication, user, document, ingestion, retrieval, and chat endpoints.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Report service, model, and sparse-index status |
| `POST` | `/auth/check` | Check registration eligibility |
| `POST` | `/auth/register` | Register an eligible user |
| `POST` | `/auth/login` | Authenticate a user |
| `GET` | `/auth/me` | Return the current authenticated user |
| `GET` | `/u/profile` | Return the current academic profile |
| `POST` | `/api/ingest` | Upload files and queue ingestion jobs |
| `GET` | `/api/jobs/<job_id>` | Inspect an ingestion job |
| `GET` | `/api/documents` | List accessible documents |
| `GET` | `/api/documents/<id>/file` | Generate a presigned file URL |
| `POST` | `/api/query` | Execute a non-streaming RAG query |
| `POST` | `/api/chat` | Stream an answer using Server-Sent Events |
| `POST` | `/api/retrieve/sparse` | Query the BM25 retriever |
| `POST` | `/api/retrieve/hybrid` | Query dense+sparse retrieval with optional reranking |
| `GET/POST` | `/api/evaluation/run` | Run the retrieval evaluation benchmark |

Authenticated endpoints expect:

```http
Authorization: Bearer <supabase-access-token>
```

The `/api/chat` endpoint emits SSE events such as `documents`, `sources`, `token`, `done`, and `error`.

## Testing and quality checks

Run the backend test suite with:

```bash
cd backend
uv run python -m unittest discover -s tests
```

Build and type-check the frontend with:

```bash
cd frontend
npm run lint
npm run build
```

## Security considerations

- Keep all `.env` files and credentials out of version control.
- Use the Supabase service-role key only on the backend for privileged operations.
- Use presigned S3 URLs instead of exposing bucket credentials or public objects.
- Keep `AUTH_REGISTRATION_TOKEN_SECRET` private and rotate it if compromised.
- Review and restrict `AUTH_ALLOWED_ORIGINS` for deployed environments.
- Apply Supabase Row Level Security policies from the migrations before exposing the application.

## Contributing

1. Create a focused branch from the current default branch.
2. Make the smallest change that addresses the issue.
3. Add or update backend tests for behavior changes.
4. Run the backend tests and frontend lint/build checks locally.
5. Open a pull request with a concise summary, validation steps, and any migration or environment changes.

When changing database behavior, add a new timestamped migration rather than editing an already-applied migration.

## License

No license file is currently included in this repository. Add a license before distributing the project outside its intended development or evaluation environment.
