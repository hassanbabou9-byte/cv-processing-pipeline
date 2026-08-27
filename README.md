# CV Processing Pipeline

**AI-powered CV processing system** for uploading PDF/DOCX resumes, extracting structured candidate data, validating it, and storing it in PostgreSQL.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-v0.100%2B-green) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue) ![Docker](https://img.shields.io/badge/Docker-Supported-blue)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Docker Deployment](#docker-deployment)
- [Streamlit Frontend](#streamlit-frontend)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)
- [Troubleshooting](#troubleshooting)

---

## Overview

The **CV Processing Pipeline** is an enterprise-oriented Python/FastAPI backend designed to automatically process CV documents at scale. It orchestrates a complete end-to-end pipeline:

```
PDF/DOCX Upload
    ↓
Document Parsing (Docling)
    ↓
Markdown Extraction & Cleaning
    ↓
LLM Extraction (OpenRouter/Ollama)
    ↓
Pydantic Validation
    ↓
Data Normalization
    ↓
ORM Mapping
    ↓
PostgreSQL Persistence
```

**Key Design Principle:** Each CV is processed independently — a failure on one CV does not stop the pipeline for others in the batch.

---

## Quick Start

The easiest way to run the complete project is Docker Compose. Docker starts the API, PostgreSQL, and MinIO together.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Compose enabled
- An LLM provider: an [OpenRouter](https://openrouter.ai/) API key or a local [Ollama](https://ollama.com/) installation
- Git

### 1. Clone the repository

```bash
git clone <repository-url>
cd cv-pipline
```

### 2. Create the local environment file

Copy the committed template and update the values marked for your environment. Do not commit `.env`; it contains credentials and is ignored by Git.

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS/Linux
cp .env.example .env
```

At minimum, set `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, and `MINIO_SECRET_KEY` to non-default values. Choose one LLM option:

- **OpenRouter:** set `LLM_PROVIDER=openrouter` and provide `OPENROUTER_API_KEY`.
- **Ollama:** install Ollama, pull the model named by `OLLAMA_MODEL`, and keep `LLM_PROVIDER=ollama`.

### 3. Start the services

```bash
docker compose up --build
```

The first build can take several minutes because Docling downloads model files. When startup completes, use:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- MinIO Console: <http://localhost:9001>

### 4. Start the frontend

Open a second terminal, activate a Python environment, install the dependencies, and run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run frontend/app.py
```

Then open <http://localhost:8501>. The frontend uses the API at `http://127.0.0.1:8000`.

### 5. Stop the project

```bash
docker compose down
```

Use `docker compose down -v` only when you intentionally want to delete the PostgreSQL, MinIO, and Docling cache volumes.

---

## Key Features

✅ **Dual LLM Support**
- Primary: OpenRouter (production-grade, multi-model support)
- Fallback: Ollama (on-premises, air-gapped environments)
- Automatic failover with semantic retry logic

✅ **Batch Processing**
- Upload up to 100 CVs per request
- Parallel processing with error isolation
- Per-CV status tracking

✅ **Multi-Format Support**
- PDF documents with OCR fallback
- DOCX/Word documents
- Automatic format detection

✅ **Enterprise Data Model**
- Candidate profiles (Collaborateur)
- Professional experiences
- Academic diplomas & training
- Certifications & skills
- Projects & activities
- Language proficiency
- Relationship mapping (skills, projects, activities)

✅ **Production-Ready Architecture**
- Structured logging (debug/info/warning/error levels)
- Centralized error handling with custom exceptions
- Environment-based configuration
- Database connection pooling
- Transaction management with rollback
- Data validation at multiple layers

✅ **Robust Validation**
- Pydantic schema validation
- Custom field validators
- Extraction validation with retry logic
- Semantic LLM retry on malformed responses

✅ **Data Integrity**
- Normalization layer for consistent data
- Relationship entity building
- Duplicate detection and merging
- UUID-based referential integrity

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────┐
│                   Client (FastAPI)                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              API Layer (Routers)                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  POST /upload        POST /process/{cv_id}       │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          Service Layer (Business Logic)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  CVProcessingService                             │  │
│  │  - Pipeline orchestration                        │  │
│  │  - Error handling & retry logic                  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┬──────────────────┐
        ↓                 ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Docling      │  │ LLM Chains   │  │ Normalization│
│ Document     │  │ & Extraction │  │ & Mapping    │
│ Parser       │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          Repository Layer (Data Access)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Collaborateur, Experience, Diplome,             │  │
│  │  Formation, Certificat, Competence, etc.         │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           SQLAlchemy ORM + PostgreSQL                    │
└─────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Responsibility |
|-----------|-----------------|
| **API Routers** | HTTP endpoint definitions, request/response validation |
| **Services** | Business logic orchestration, error handling |
| **Parsers** | Document parsing (Docling), markdown extraction |
| **LLM Chains** | Prompt engineering, LLM invocation, output parsing |
| **Mappers** | Entity building, data normalization, DB mapping |
| **Repositories** | Database CRUD operations via SQLAlchemy |
| **Models** | SQLAlchemy ORM entity definitions |
| **Schemas** | Pydantic validation models (API & extraction) |

---

## Tech Stack

### Backend Framework
- **FastAPI** – Modern async web framework
- **Uvicorn** – ASGI server
- **Pydantic** – Data validation & serialization
- **Pydantic-Settings** – Configuration management

### Document Processing
- **Docling** – Advanced document parsing with layout analysis
- **python-multipart** – Multipart form data handling

### AI/LLM
- **LangChain** – LLM orchestration framework
- **LangChain-OpenAI** – OpenRouter integration
- **LangChain-Ollama** – Ollama provider support

### Database
- **SQLAlchemy** – ORM framework (2.0+)
- **PostgreSQL** – Primary database (v18+)
- **psycopg** – PostgreSQL adapter with binary support

### DevOps & Configuration
- **Docker & Docker Compose** – Containerization
- **Python-dotenv** – Environment variable management
- **python-multipart** – File upload handling

### Python
- **Python 3.11+** – Target runtime

---

## Installation & Setup

### Prerequisites

- **Python 3.11+**
- **PostgreSQL 18+** (or use Docker)
- **Git**
- **Ollama** (optional, for fallback LLM provider)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd cv-pipline
```

### Step 2: Create Virtual Environment

```bash
# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```env
# App
APP_NAME=CV Processing Pipeline
APP_VERSION=0.1.0
ENVIRONMENT=development
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cv_pipeline
POSTGRES_DB=cv_pipeline
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=5432

# LLM Provider Selection
LLM_PROVIDER=ollama              # or: openrouter
LLM_TEMPERATURE=0.0
LLM_MAX_RETRIES=2
LLM_TIMEOUT_SECONDS=60
LLM_PARSE_RETRIES=2
LLM_MAX_OUTPUT_TOKENS=4096
LLM_CONTEXT_WINDOW=8192

# OpenRouter (if using as primary)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4o-mini

# Ollama (if using as primary or fallback)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# MinIO object storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=candidate-images
MINIO_SECURE=false

# FastAPI
API_PORT=8000
```

### Step 5: Initialize Database

The database is automatically initialized on application startup via `app/db/init_db.py`. No manual SQL scripts required.

```bash
# The database schema will be created automatically when the app starts
```

### Step 6: Run Locally (Development)

```bash
# Start PostgreSQL if not running
# Then run the FastAPI server:

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Open `/docs` for the interactive Swagger UI or `/redoc` for ReDoc.

---

## Configuration

### Environment Variables Reference

#### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | CV Processing Pipeline | Application name |
| `APP_VERSION` | 0.1.0 | Version string |
| `ENVIRONMENT` | development | Environment: `development`, `staging`, `production` |
| `LOG_LEVEL` | INFO | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

#### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql+psycopg://... | Full PostgreSQL connection string |
| `POSTGRES_DB` | cv_pipeline | Database name |
| `POSTGRES_USER` | postgres | Database user |
| `POSTGRES_PASSWORD` | postgres | Database password |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |

#### LLM Provider Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | LLM provider: `ollama` or `openrouter` |
| `LLM_TEMPERATURE` | `0.0` | Sampling temperature |
| `LLM_MAX_RETRIES` | `2` | Provider request retries |
| `LLM_TIMEOUT_SECONDS` | `60` | Provider request timeout |
| `LLM_PARSE_RETRIES` | `2` | Retries for malformed extraction output |
| `LLM_MAX_OUTPUT_TOKENS` | `4096` | Maximum extraction response size |
| `LLM_CONTEXT_WINDOW` | `8192` | LLM context window size |
| `OPENROUTER_API_KEY` | - | API key when using OpenRouter |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API base URL |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | OpenRouter model identifier |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1` | Ollama model name |

#### MinIO Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ENDPOINT` | `minio:9000` | MinIO host and port inside Docker |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `candidate-images` | Bucket for candidate images |
| `MINIO_SECURE` | `false` | Use HTTPS for MinIO connections |

#### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | 8000 | Server port |

### Provider Selection Strategy

The system supports two LLM providers with automatic failover:

1. **OpenRouter** (Production-Grade)
   - Multi-model support (Claude, GPT-4, etc.)
   - Consistent API, rate limiting
   - Requires API key and internet connectivity

2. **Ollama** (On-Premises)
   - Runs locally, no internet required
   - Suitable for air-gapped environments
   - Lower latency, full data privacy
   - Requires Ollama server running

**Retry behavior:**
- The configured provider is retried when a request fails
- Malformed extraction output is retried according to `LLM_PARSE_RETRIES`
- If extraction still fails, the request returns an error with details

---

## Docker Deployment

### Quick Start with Docker Compose

#### 1. Start All Services

```bash
docker compose up --build -d
```

This starts:
- **PostgreSQL** database (port 5432)
- **MinIO** object storage API (port 9000)
- **MinIO Console** (port 9001)
- **FastAPI** application (port 8000)

#### 2. Verify Deployment

```bash
# Check running containers
docker compose ps

# View logs
docker compose logs -f api
```

#### 3. Access the API

- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **PostgreSQL:** localhost:5432
- **MinIO API:** http://localhost:9000
- **MinIO Console:** http://localhost:9001

#### 4. Stop Services

```bash
docker compose down

# Also remove volumes (WARNING: deletes data)
docker compose down -v
```

### Docker Compose Environment

The `docker-compose.yml` includes:

- **PostgreSQL 18 Alpine** (optimized image)
- **FastAPI Container** (built from Dockerfile)
- **Persistent Volumes:** Data and Docling caches
- **Health Checks:** PostgreSQL readiness verification
- **MinIO Object Storage:** Candidate images are stored in the `candidate-images` bucket
- **Network Isolation:** Custom bridge network

### Docker Configuration Notes

- **Ollama Integration:** If using Ollama on the Windows host, `docker-compose.yml` automatically routes to `host.docker.internal:11434`
- **Data Persistence:** 
  - `./data:/app/data` → Uploaded CVs and parsed markdown
  - `docling_cache:/root/.cache` → Docling model cache
- **Environment:** All settings loaded from `.env` file

### Building Docker Image Manually

```bash
# Build the image
docker build -t cv-pipeline:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+psycopg://user:pass@postgres:5432/cv_pipeline \
  --env-file .env \
  cv-pipeline:latest
```

---

## Streamlit Frontend

The Streamlit frontend provides a browser-based view of candidates and communicates with FastAPI over HTTP. It does not connect directly to PostgreSQL or MinIO.

Start the API first, then run the frontend from the project root:

```bash
python -m streamlit run frontend/app.py
```

Open the URL printed by Streamlit, usually `http://localhost:8501`. The frontend expects the API at `http://127.0.0.1:8000`; update `API_BASE_URL` in `frontend/app.py` when the API runs elsewhere.

---

## Candidate Image Extraction

When a CV contains an embedded candidate photo, the processing pipeline:

1. Extracts usable embedded images from PDF or DOCX files.
2. Ignores images smaller than the minimum supported dimensions.
3. Prefers an image containing a face when one is detected.
4. Falls back to the largest usable image when no face is detected.
5. Uploads the selected image to the configured MinIO bucket.

Image extraction is optional. A CV without a usable photo is still processed successfully. PostgreSQL stores the MinIO object key in the candidate record; the image bytes remain in MinIO.

Retrieve an image through the API:

```http
GET /candidates/{collaborateur_id}/image
```

The Streamlit frontend displays the image through this API endpoint and does not access MinIO directly.

## API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. **Upload CVs**

```http
POST /upload
Content-Type: multipart/form-data

files: [File, File, ...]  (up to 100 files)
```

**Description:** Upload and process CV documents in batch.

**Request:**
- **files** (multipart): Array of PDF or DOCX files (max 100 per request)

**Response (200 OK):**
```json
{
  "uploaded": 3,
  "processed": 2,
  "failed": 1,
  "cv_ids": [
    "4c2c0210-647a-4ae1-83ed-78f84dd18c71",
    "53125535-66f4-4d2a-b9df-ac58a2b3bbee"
  ],
  "errors": [
    {
      "filename": "invalid.pdf",
      "error": "File format not supported"
    }
  ]
}
```

**Supported Formats:**
- PDF (`.pdf`)
- DOCX (`.docx`)

**Error Handling:**
- Individual CV failures do NOT stop processing of others
- Each failed CV includes an error message
- Successful CVs are persisted immediately

**Example Usage:**
```bash
# Using curl
curl -X POST "http://localhost:8000/upload" \
  -F "files=@resume1.pdf" \
  -F "files=@resume2.docx"

# Using Python requests
import requests
with open('resume.pdf', 'rb') as f:
    files = {'files': f}
    response = requests.post('http://localhost:8000/upload', files=files)
```

---

#### 2. **Process CV**

```http
POST /process/{cv_id}
Content-Type: application/json
```

**Description:** Extract structured information from a previously uploaded CV using LLM.

**Path Parameters:**
- **cv_id** (string, UUID): Unique identifier from `/upload` response

**Response (200 OK):**
```json
{
  "cv_id": "4c2c0210-647a-4ae1-83ed-78f84dd18c71",
  "extraction": {
    "nom": "Dupont",
    "prenom": "Jean",
    "email": "jean.dupont@email.com",
    "langues": [
      {
        "nom": "French",
        "niveau": "Native"
      },
      {
        "nom": "English",
        "niveau": "Fluent"
      }
    ],
    "experiences": [
      {
        "entreprise": "Acme Corp",
        "poste": "Senior Developer",
        "type": "CDI",
        "debut": "2020-01",
        "fin": "2023-12",
        "description": "Led development of cloud infrastructure..."
      }
    ],
    "diplomes": [
      {
        "intitule": "Master in Computer Science",
        "etablissement": "University of Paris",
        "niveau_academique": "Master",
        "specialite": "Software Engineering",
        "date_obtention": "2019",
        "mention": "Très Bien"
      }
    ],
    "formations": [...],
    "certificats": [...],
    "competences": [...],
    "projets": [...],
    "activites": [...]
  }
}
```

**Error Responses:**
- **404:** CV not found (invalid cv_id)
- **422:** LLM extraction failed (malformed response)
- **500:** Server error (DB issue, LLM unavailable)

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/process/4c2c0210-647a-4ae1-83ed-78f84dd18c71" \
  -H "Content-Type: application/json"
```

---

#### 3. **List Candidates**

```http
GET /candidates?limit=100&offset=0
```

Returns candidates stored in PostgreSQL. `limit` must be between 1 and 500; `offset` defaults to 0.

```bash
curl "http://localhost:8000/candidates?limit=20&offset=0"
```

#### 4. **Get Candidate**

```http
GET /candidates/{collaborateur_id}
```

Returns one candidate by UUID.

#### 5. **Get Candidate Image**

```http
GET /candidates/{collaborateur_id}/image
```

Streams the candidate image from MinIO when an image is available.

---

### OpenAPI/Swagger UI

Full API documentation is available interactively at:
```
http://localhost:8000/docs
```

Alternatively, ReDoc (alternative UI):
```
http://localhost:8000/redoc
```

---

## Database Schema

### Entity Relationship Diagram

```
Collaborateur (1) ────── (N) Experience
    │                         │
    ├─ (1) ────── (N) Diplome
    │
    ├─ (1) ────── (N) Formation
    │
    ├─ (1) ────── (N) Certificat
    │
    ├─ (1) ────── (N) Activite
    │
    ├─ (M) ────── (N) Competence (via CollaborateurCompetence)
    │
    └─ (M) ────── (N) Projet (via CollaborateurProjet)
```

### Key Tables

#### `collaborateurs` (Candidates/Employees)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, Default: uuid_v4 |
| `version` | INTEGER | Default: 0 |
| `nom` | VARCHAR | NOT NULL |
| `prenom` | VARCHAR | DEFAULT '' |
| `email` | VARCHAR | NOT NULL, UNIQUE |
| `telephone_professionnel` | VARCHAR | NULL |
| `bio_professionnelle` | TEXT | NULL |
| `role` | VARCHAR | DEFAULT 'COLLABORATEUR' |
| `statut` | VARCHAR | DEFAULT 'ACTIF' |
| `image_object_key` | VARCHAR | NULL; MinIO object key |

`image_object_key` references the candidate image stored in the configured MinIO bucket. The image bytes are not stored in PostgreSQL. It is `NULL` when the CV has no usable candidate image.

#### `experiences` (Professional Experience)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `collaborateur_id` | UUID | FK → collaborateurs |
| `entreprise` | VARCHAR | NOT NULL |
| `poste` | VARCHAR | NOT NULL |
| `type` | VARCHAR | (e.g., CDI, CDD) |
| `date_debut` | DATE | NULL |
| `date_fin` | DATE | NULL |
| `description` | TEXT | NULL |

#### `diplomes` (Academic Diplomas)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `collaborateur_id` | UUID | FK → collaborateurs |
| `intitule` | VARCHAR | NOT NULL |
| `etablissement` | VARCHAR | NOT NULL |
| `niveau_academique` | VARCHAR | (e.g., License, Master) |
| `specialite` | VARCHAR | NULL |
| `date_obtention` | DATE | NULL |
| `mention` | VARCHAR | NULL |

#### `formations` (Trainings/Courses)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `collaborateur_id` | UUID | FK → collaborateurs |
| `nom` | VARCHAR | NOT NULL |
| `organisme` | VARCHAR | NOT NULL |
| `date_debut` | DATE | NULL |
| `date_fin` | DATE | NULL |

#### `certificats` (Certifications)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `collaborateur_id` | UUID | FK → collaborateurs |
| `nom` | VARCHAR | NOT NULL |
| `organisme` | VARCHAR | NOT NULL |
| `date_obtention` | DATE | NULL |

#### `competences` (Skills)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `nom` | VARCHAR | NOT NULL, UNIQUE |
| `domaine` | VARCHAR | NULL |

#### `collaborateur_competence` (Skills Junction)

| Column | Type | Constraints |
|--------|------|-------------|
| `collaborateur_id` | UUID | FK → collaborateurs |
| `competence_id` | UUID | FK → competences |
| `niveau` | VARCHAR | (e.g., Novice, Expert) |

#### `projets` (Projects)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `nom` | VARCHAR | NOT NULL |
| `description` | TEXT | NULL |
| `date_debut` | DATE | NULL |
| `date_fin` | DATE | NULL |

#### `collaborateur_projet` (Projects Junction)

| Column | Type | Constraints |
|--------|------|-------------|
| `collaborateur_id` | UUID | FK → collaborateurs |
| `projet_id` | UUID | FK → projets |
| `role` | VARCHAR | NULL |

#### `activites` (Activities)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `collaborateur_id` | UUID | FK → collaborateurs |
| `titre` | VARCHAR | NOT NULL |
| `description` | TEXT | NULL |
| `date_debut` | DATE | NULL |
| `date_fin` | DATE | NULL |

---

## Project Structure

```
cv-pipline/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app entrypoint
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py              # FastAPI dependency injection
│   │   ├── error_handlers.py            # Exception handlers
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── upload.py                # POST /upload endpoint
│   │       ├── process.py               # POST /process/{cv_id}
│   │       └── candidates.py            # Candidate query endpoints
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                  # Centralized configuration
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py                # Custom exception classes
│   │   └── logging.py                   # Logging configuration
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                      # SQLAlchemy declarative base
│   │   ├── init_db.py                   # Database initialization
│   │   └── session.py                   # Database session management
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── chains/
│   │   │   ├── __init__.py
│   │   │   └── cv_extraction_chain.py   # LLM extraction pipeline
│   │   ├── output_parsers/
│   │   │   ├── __init__.py
│   │   │   └── cv_json_parser.py        # JSON output parser
│   │   ├── prompts/
│   │   │   ├── __init__.py
│   │   │   └── cv_extraction_prompt.py  # LLM prompt templates
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── base.py                  # Base provider interface
│   │       ├── ollama_provider.py       # Ollama integration
│   │       ├── openrouter_provider.py   # OpenRouter integration
│   │       └── provider_factory.py      # Provider factory pattern
│   │
│   ├── mappers/
│   │   ├── __init__.py
│   │   ├── db_mapper.py                 # Schema → ORM mapping
│   │   ├── entity_builders.py           # Entity factory functions
│   │   └── normalization/
│   │       ├── __init__.py
│   │       └── normalizer.py            # Data normalization
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── collaborateur.py             # Candidate entity
│   │   ├── experience.py                # Experience entity
│   │   ├── diplome.py                   # Diploma entity
│   │   ├── formation.py                 # Training entity
│   │   ├── certificat.py                # Certification entity
│   │   ├── competence.py                # Skill entity
│   │   ├── collaborateur_competence.py  # Skills junction table
│   │   ├── projet.py                    # Project entity
│   │   ├── collaborateur_projet.py      # Projects junction table
│   │   ├── activite.py                  # Activity entity
│   │   └── enums.py                     # Enum definitions
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── docling/
│   │       ├── __init__.py
│   │       ├── document_parser.py       # Docling integration
│   │       ├── markdown_extractor.py    # Markdown extraction
│   │       └── text_cleaner.py          # Text normalization
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base_repository.py           # Base CRUD operations
│   │   ├── collaborateur_repository.py  # Candidate persistence
│   │   ├── experience_repository.py     # Experience persistence
│   │   ├── diplome_repository.py        # Diploma persistence
│   │   ├── formation_repository.py      # Training persistence
│   │   ├── certificat_repository.py     # Certification persistence
│   │   ├── competence_repository.py     # Skill persistence
│   │   ├── projet_repository.py         # Project persistence
│   │   └── activite_repository.py       # Activity persistence
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── api_models.py                # API request/response models
│   │   └── cv_extraction.py             # LLM extraction schema
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cv_processing_service.py     # Main orchestration service
│   │   └── candidate_service.py         # Candidate business logic
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── date_utils.py                # Date parsing & formatting
│   │   ├── file_storage.py              # File system operations
│   │   └── uuid_utils.py                # UUID utilities
│   │
│   └── validators/
│       ├── __init__.py
│       └── extraction_validators.py     # Extraction validation logic
│
├── data/
│   ├── uploads/                         # Raw uploaded files
│   └── parsed/                          # Cleaned markdown output
│
├── docker-compose.yml                   # Docker services orchestration
├── Dockerfile                           # FastAPI container definition
├── requirements.txt                     # Python dependencies
├── .env.example                         # Environment template
└── README.md                            # This file
```

### Directory Responsibilities

| Directory | Purpose |
|-----------|---------|
| `api/` | HTTP routing, request/response contracts |
| `config/` | Configuration management & validation |
| `core/` | Core exceptions, logging, utilities |
| `db/` | Database connection, session management |
| `llm/` | AI/LLM integration (providers, chains, prompts) |
| `mappers/` | Data transformation & normalization |
| `models/` | SQLAlchemy ORM entity definitions |
| `parsers/` | Document parsing logic |
| `repositories/` | Data access layer (CRUD) |
| `schemas/` | Pydantic validation models |
| `services/` | Business logic orchestration |
| `utils/` | Shared utility functions |
| `validators/` | Validation rules & logic |
| `data/` | Runtime file storage |

---

## Development Guide

### Running Locally

#### 1. Set Up Development Environment

```bash
# Clone repository
git clone <repo-url>
cd cv-pipline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\Activate.ps1 on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env  # Windows
# or: cp .env.example .env  # macOS/Linux
```

#### 2. Configure PostgreSQL

**Option A: Local PostgreSQL**
```bash
# Ensure PostgreSQL is running locally
# Update DATABASE_URL in .env:
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/cv_pipeline

# Create database (if not exists)
createdb cv_pipeline
```

**Option B: Docker PostgreSQL**
```bash
# Use Docker Compose to run only PostgreSQL
docker compose up -d postgres

# Update .env:
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cv_pipeline
```

#### 3. Configure LLM Providers

**For OpenRouter:**
```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk_live_...
OPENROUTER_MODEL=anthropic/claude-3-5-sonnet
```

**For Ollama (Local):**
```bash
# Install and start Ollama
ollama pull llama2
ollama serve

# In .env:
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

#### 4. Start Development Server

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

#### 5. Test API

```bash
# Swagger UI
open http://localhost:8000/docs

# Or use curl to upload a CV
curl -X POST "http://localhost:8000/upload" \
  -F "files=@/path/to/resume.pdf"
```

### Testing Workflow

#### 1. Manual Testing

```bash
# Upload a test CV
curl -X POST "http://localhost:8000/upload" \
  -F "files=@test_resume.pdf" \
  -v

# Extract structured data using returned cv_id
curl -X POST "http://localhost:8000/process/4c2c0210-647a-4ae1-83ed-78f84dd18c71" \
  -H "Content-Type: application/json" \
  -v
```

#### 2. Database Inspection

```bash
# Connect to PostgreSQL
psql postgresql://postgres:postgres@localhost:5432/cv_pipeline

# List tables
\dt

# Query candidates
SELECT id, nom, prenom, email FROM collaborateurs LIMIT 5;

# Query experiences for a candidate
SELECT * FROM experiences WHERE collaborateur_id = '<uuid>' LIMIT 10;
```

### Debugging

#### Enable Debug Logging

```env
LOG_LEVEL=DEBUG
```

#### View Application Logs

```bash
# Terminal 1: Run API server
python -m uvicorn app.main:app --reload --log-level debug

# Terminal 2: Tail logs
tail -f <app.log>
```

#### Inspect Request/Response

Use Swagger UI at `http://localhost:8000/docs` for interactive testing with request/response inspection.

### Common Development Tasks

#### Adding a New Entity

1. Create model in `app/models/my_entity.py` (SQLAlchemy)
2. Create repository in `app/repositories/my_entity_repository.py`
3. Create Pydantic schema in `app/schemas/api_models.py` if API exposed
4. Add extraction schema in `app/schemas/cv_extraction.py` if LLM extracts it
5. Run server (database auto-migrates)

#### Adding a New LLM Provider

1. Create provider class in `app/llm/providers/my_provider.py` extending `BaseProvider`
2. Register in `app/llm/providers/provider_factory.py`
3. Update `app/config/settings.py` with new provider configuration
4. Test with `/upload` and `/process` endpoints

#### Modifying the Extraction Prompt

Edit `app/llm/prompts/cv_extraction_prompt.py`. The prompt is used by:
- `app/llm/chains/cv_extraction_chain.py`
- Response is validated against `app/schemas/cv_extraction.py`

### Code Quality & Standards

- **Linting:** Follow PEP 8 conventions
- **Type Hints:** Use for all function parameters and returns
- **Docstrings:** Module, class, and function docstrings required
- **Error Handling:** Use custom exceptions from `app/core/exceptions.py`
- **Logging:** Use structured logging from `app/core/logging.py`

---

## Troubleshooting

### Common Issues

#### 1. **Database Connection Error**

```
sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed
```

**Solutions:**
- Verify PostgreSQL is running: `psql --version`
- Check `DATABASE_URL` in `.env` matches your setup
- Ensure credentials are correct: `postgres:password@localhost:5432/cv_pipeline`
- If using Docker: `docker compose ps` and check container health

```bash
# Test connection
psql <DATABASE_URL>
```

#### 2. **LLM Provider Not Responding**

```
langchain_core.exceptions.LLMError: Error calling OpenRouter API
```

**For OpenRouter:**
- Verify `OPENROUTER_API_KEY` is set and valid
- Check API quota at https://openrouter.ai/activity
- Verify internet connectivity
- Try fallback provider (Ollama)

**For Ollama:**
- Ensure Ollama is running: `ollama serve`
- Check `OLLAMA_BASE_URL` (default: http://localhost:11434)
- Pull required model: `ollama pull llama2`
- Check Docker routing if running in container: `host.docker.internal:11434`

```bash
# Test Ollama connectivity
curl http://localhost:11434/api/tags
```

#### 3. **File Upload Fails**

```
HTTPException: At least one CV file must be provided.
```

**Solutions:**
- Ensure file is PDF or DOCX format
- Check file size (reasonable for typical CV)
- Verify Content-Type header is `multipart/form-data`

#### 4. **LLM Extraction Returns Malformed JSON**

```
pydantic_core._pydantic_core.ValidationError: 1 validation error
```

**Solutions:**
- Check `OPENROUTER_MODEL` or `OLLAMA_MODEL` is appropriate for text extraction
- Review extraction prompt in `app/llm/prompts/cv_extraction_prompt.py`
- System includes semantic retry logic—may succeed on second attempt
- Check logs for LLM response: `LOG_LEVEL=DEBUG`

#### 5. **Docling Parsing Fails**

```
DocumentParsingError: Failed to parse document
```

**Solutions:**
- Verify PDF is not corrupted: try opening in PDF reader
- Check for embedded fonts/encodings that Docling doesn't support
- Try DOCX format as alternative
- Check Docling model cache: `rm -rf ~/.cache/docling`

#### 6. **Docker Container Won't Start**

```
Error response from daemon: Ports are in use
```

**Solutions:**
```bash
# Find process using port 8000 or 5432
lsof -i :8000
lsof -i :5432

# Kill process or change port in .env:
API_PORT=8001
```

**Or use different compose file:**
```bash
docker compose down
docker compose up -d
```

#### 7. **Out of Memory (Docker)**

```
ERROR: Cannot allocate memory
```

**Solutions:**
```bash
# Increase Docker memory allocation (Docker Desktop Settings)
# Or limit container memory:
docker run --memory=4g cv-pipeline:latest
```

### Getting Help

1. **Check logs:**
   ```bash
  docker compose logs -f api
   # or locally:
   python -m uvicorn app.main:app --reload --log-level debug
   ```

2. **Enable debug mode:** Set `LOG_LEVEL=DEBUG` in `.env`

3. **Verify configuration:** Review `.env` against `.env.example`

4. **Check database state:**
   ```bash
   psql <DATABASE_URL>
   SELECT * FROM collaborateurs;
   ```

5. **Test LLM connectivity separately:**
   ```python
   from app.llm.providers.provider_factory import get_llm_provider
   provider = get_llm_provider()
   response = provider.generate("Test prompt")
   ```

---

## Performance & Scaling Considerations

### Database Optimization
- **Indexing:** Configured on `collaborateurs(email)`, `competences(nom)`
- **Connection Pooling:** SQLAlchemy connection pool (pool_size=10, max_overflow=20)
- **Query Batching:** Use repositories for efficient queries

### Document Processing
- **Batch Size:** Up to 100 CVs per request (adjust `MAX_FILES_PER_BATCH` in `upload.py`)
- **Docling Cache:** Persisted in Docker volume for faster model loading
- **OCR Fallback:** Automatic, adds latency but handles scanned PDFs

### LLM Performance
- **Provider Failover:** Automatic retry if primary provider fails
- **Semantic Retry:** Retries on malformed LLM responses
- **Rate Limiting:** Respect OpenRouter/Ollama rate limits

### Recommendations for Production

1. **Database:**
   - Use managed PostgreSQL (RDS, Neon, etc.)
   - Enable connection pooling (PgBouncer)
   - Monitor query performance

2. **LLM:**
   - Cache prompt templates
   - Use fallback provider strategy
   - Monitor API usage and costs

3. **Deployment:**
   - Use Kubernetes or container orchestration
   - Set resource limits (CPU, memory)
   - Implement health checks
   - Add load balancing for multiple instances

4. **Monitoring:**
   - Aggregate logs (ELK, DataDog, etc.)
   - Monitor API response times
   - Track LLM API costs
   - Alert on failures

---

## Contributing

### Branch Strategy
- `main` – Production-ready code
- `develop` – Development branch
- `feature/` – Feature branches from develop

### Commit Messages
```
feat: Add support for scanned PDF OCR
fix: Resolve LLM fallback logic bug
docs: Update README with scaling guide
refactor: Simplify entity normalization
```

### Pull Request Process
1. Create feature branch from `develop`
2. Make changes with clear commits
3. Add/update tests and documentation
4. Submit PR with description
5. Code review and approval
6. Merge to `develop`, then `main` for release

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Support & Contact

For questions, issues, or contributions:
- **GitHub Issues:** Report bugs and request features
- **Documentation:** See README.md and inline code comments
- **Email:** [contact information if applicable]

---

**Last Updated:** August 2024  
**Version:** 0.1.0
- Extract structured information from unstructured CVs.
- Process multiple CVs through a single API request.
- Process each CV independently.
- Prevent one failed CV from stopping the entire batch.
- Validate LLM-generated information before persistence.
- Separate extraction, validation, normalization, mapping, and persistence.
- Store structured CV information in PostgreSQL.

---

# Architecture

```text
                         +----------------------+
                         |        Client        |
                         |   Swagger / Postman  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |       FastAPI        |
                         |      API Layer       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |  Processing Service  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |       Docling        |
                         |  PDF / DOCX Parsing  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   Cleaned Markdown   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |    LLM Extraction    |
                         | OpenRouter / Ollama  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |  Structured JSON     |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Pydantic Validation  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     Normalizer       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      DB Mapper       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     Repository       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     PostgreSQL       |
                         +----------------------+
                        
