# Smart Doc Agent (CampusHub / BatchOS)


#INGESTION PIPELINE
![Uploading smart_doc_ingesetion.png…]()


An intelligent document ingestion, metadata extraction, and contextual RAG (Retrieval-Augmented Generation) assistant designed for college campuses and academic cohorts.

Smart Doc Agent automates multi-format academic document ingestion, uses Small Language Models (SLMs) hosted on Groq for ultra-fast structured metadata extraction, indexes vectors in Supabase (pgvector), and delivers scoped access control across batches, courses, and subjects.

---

## 🌟 Key Features

- **Blazing Fast Ingestion & SLM Metadata Extraction**: Offloads text classification and context summarization to Groq-hosted SLMs (`llama-3.3-70b-versatile` / `openai/gpt-oss-20b`), generating structured JSON schemas (type, title, summary, deadlines).
- **Multi-Format Processing**: Full pipeline support for PDF, DOCX, PPTX, and image formats.
- **Role-Based Document Scope & Security**:
  - **Students**: Seamless access tied directly to their active `batch_id` and registered subjects.
  - **Faculty**: Multi-batch course material management and cohort-specific document distribution.
- **Robust Storage & Vector Store**: Hybrid architecture pairing AWS S3 bucket storage for raw documents with Supabase Postgres + `pgvector` for metadata and semantic chunk search.
- **Modern Full-Stack Experience**: Clean, responsive frontend built with React, TypeScript, and Vite, backed by a modular Python / Flask service managed via `uv`.

---

## 🏗️ Architecture & Tech Stack

```
Smart_doc_agent/
├── frontend/                # React (TypeScript) + Vite + Lucide Icons
│   ├── src/
│   │   ├── api/             # API client services
│   │   ├── features/        # Upload, Dashboard, Subject, & Profile Views
│   │   └── types/           # Strict TypeScript contracts & schemas
├── rag/                     # Python Flask + RAG Pipeline (managed via uv)
│   ├── ingestion/           # File ingestion, chunking, and parser logic
│   ├── language_models/     # Groq client integration & SLM prompting
│   ├── lib/                 # AWS S3 & Supabase clients
│   ├── modules/             # User, auth, and routing modules
│   └── app.py               # Flask application entry point
```

### Core Technologies

- **Frontend**: React 18, TypeScript, Vite, TailwindCSS / Custom CSS, Lucide React
- **Backend / RAG Engine**: Python 3.12, Flask, Pydantic, `uv` package manager
- **Language Models & Inference**: Groq Cloud SDK (LPU-accelerated structured inference)
- **Database & Auth**: Supabase (PostgreSQL, Row-Level Security, pgvector)
- **Cloud Storage**: AWS S3 (Presigned URLs & raw file persistence)
- **Upcoming / Queue Infrastructure**: Celery + Redis for asynchronous background ingestion workers

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+** (with [`uv`](https://docs.astral.sh/uv/) installed)
- **Node.js 18+** & `npm` / `pnpm`
- **Supabase Account** (PostgreSQL with `pgvector` enabled)
- **Groq Cloud API Key**
- **AWS S3 Bucket** & IAM credentials

---

### 1. Backend Setup (`rag`)

1. Navigate to the `rag` directory:

   ```bash
   cd rag
   ```

2. Create and configure your environment variables:

   ```bash
   cp .env.example .env   # Or create .env manually
   ```

   Add the following configuration:

   ```env
   # Groq API
   GROQ_API_KEY="gsk_your_groq_api_key"
   GROQ_MODEL="llama-3.3-70b-versatile"

   # Supabase
   SUPABASE_URL="https://your-project.supabase.co"
   SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
   SUPABASE_ANON_KEY="your-anon-key"

   # AWS S3
   AWS_ACCESS_KEY_ID="your_access_key"
   AWS_SECRET_ACCESS_KEY="your_secret_key"
   AWS_REGION="your_aws_region"
   AWS_S3_BUCKET_NAME="your_bucket_name"

   # Flask
   FLASK_ENV="development"
   PORT=5000
   ```

3. Install dependencies and run the server using `uv`:
   ```bash
   uv run app.py
   ```

The backend server will run on `http://127.0.0.1:5000`.

---

### 2. Frontend Setup (`frontend`)

1. Navigate to the `frontend` directory:

   ```bash
   cd frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The web interface will launch on `http://localhost:5173`.

---

## 📄 Ingestion & Metadata Pipeline

1. **File Upload**: Faculty or students upload academic material via the drag-and-drop web UI with targeted `batch_id` association.
2. **Binary Storage**: Raw files are preserved in AWS S3 with deterministic object identifiers.
3. **Groq SLM Extraction**: Document content is parsed, and a sample slice is dispatched to Groq's high-speed LPU inference using strict JSON schema enforcement:
   ```json
   {
     "description": "50-100 word synthesized overview",
     "document_type": "notice | assignment | syllabus | notes | time_table | others",
     "deadline": "YYYY-MM-DD (or null)"
   }
   ```
4. **Relational & Vector Indexing**: Structured fields and UUID mappings are committed to Supabase tables for scoped retrieval and query routing.

---

## 🗺️ Roadmap

- [x] S3 document upload and storage integration
- [x] Groq SLM JSON structured metadata extraction
- [x] Supabase UUID validation and batch mapping
- [ ] End-to-end vector chunk retrieval testing & evaluation
- [ ] Background worker integration (Celery + Redis Pub/Sub)
- [ ] Interactive query agent with streaming conversational responses

---

## 🔒 Security Notice

Never commit `.env` files or secret keys to version control. Ensure all sensitive tokens (Groq API, Supabase service roles, AWS credentials) are stored solely in local environment files or your production secret management vault.
README.md
Displaying README.md.
