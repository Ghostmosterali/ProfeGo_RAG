# CLAUDE.md - AI Assistant Guide for ProfeGo_RAG

**Last Updated**: 2025-11-15
**Project Version**: 2.0.0
**Purpose**: Educational plan generation system for Mexican preschool teachers

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Codebase Structure](#codebase-structure)
4. [Development Workflows](#development-workflows)
5. [Key Conventions & Patterns](#key-conventions--patterns)
6. [API Architecture](#api-architecture)
7. [RAG System Details](#rag-system-details)
8. [Environment Setup](#environment-setup)
9. [Common Tasks](#common-tasks)
10. [Code Style](#code-style)
11. [Testing & Debugging](#testing--debugging)
12. [Deployment](#deployment)
13. [Important Notes for AI Assistants](#important-notes-for-ai-assistants)

---

## Project Overview

### What is ProfeGo?

ProfeGo is an **AI-powered educational planning system** specifically designed for **Mexican preschool teachers** (targeting 2nd grade/ages 4-5). It automates the creation of personalized study plans using:

- **Google Gemini AI** for intelligent plan generation
- **RAG (Retrieval-Augmented Generation)** for context-aware recommendations
- **OCR technology** for document processing
- **Cloud storage** for scalability

### Core Functionality

1. **Document Processing**: Extracts text from PDFs, Word docs, images, Excel files
2. **AI Plan Generation**: Creates 4-8 module educational plans with Mexican curriculum alignment
3. **RAG Enhancement**: Retrieves relevant educational content (stories, songs, activities)
4. **Cloud Storage**: User-specific file organization in Google Cloud Storage
5. **User Management**: Firebase authentication with rate limiting

### Target Users

- Preschool teachers in Mexico
- Educational institutions
- Individual educators creating lesson plans

### Educational Framework

ProfeGo aligns with the **Mexican Programa de Educación Preescolar**:

- **8 Campos Formativos** (Formative Fields):
  - Lenguaje y Comunicación
  - Pensamiento Matemático
  - Exploración y Comprensión del Mundo Natural y Social
  - Artes
  - Educación Socioemocional
  - Educación Física
  - And others

- **7 Ejes Articuladores** (Articulating Axes):
  - Inclusión
  - Pensamiento Crítico
  - Interculturalidad Crítica
  - Igualdad de Género
  - Vida Saludable
  - Apropiación de las Culturas a través de la Lectura y la Escritura
  - Artes y Experiencias Estéticas

---

## Technology Stack

### Backend Framework
- **FastAPI 0.115.0** - Modern async web framework
- **Uvicorn 0.30.6** - ASGI server with hot reload
- **SlowAPI 0.1.9** - Rate limiting middleware

### AI & Machine Learning
- **Google Gemini AI** (google-generativeai 0.8.3)
  - Model: `gemini-2.5-flash`
  - Temperature: 0.8 (high creativity for educational content)
  - Max tokens: 16,000
  - Response format: JSON
- **LangChain 0.3.13** - RAG orchestration
- **Sentence Transformers 3.3.1** - Text embeddings
  - Model: `all-MiniLM-L6-v2` (384 dimensions, lightweight)
- **PyTorch 2.9.0** - Deep learning framework
- **Transformers 4.46.3** - NLP models

### Vector Database
- **ChromaDB 0.5.23** - Persistent vector storage
- **chroma-hnswlib 0.7.6** - HNSW indexing for fast similarity search
- Collection: `profego_documents`
- Similarity metric: Cosine similarity

### Cloud Services
- **Google Cloud Storage 2.18.2** - File storage
- **Firebase (Pyrebase4 4.8.0)** - Authentication
- **google-auth 2.40.0** - Service account authentication

### Document Processing
- **Pytesseract 0.3.13** - OCR engine (requires system Tesseract)
- **OpenCV 4.10.0.84** - Image preprocessing
- **python-docx 1.2.0** - Word document generation/reading
- **PyPDF2 3.0.1** - PDF processing
- **Pandas 2.2.3** + **openpyxl 3.1.5** - Excel/CSV handling

### Security
- **python-jose 3.3.0** - JWT token handling
- **cryptography 43.0.3** - Encryption
- **pycryptodome 3.23.0** - Additional crypto utilities

### Utilities
- **python-dotenv 1.1.1** - Environment variable management
- **pydantic 2.11.9** - Data validation and settings
- **json_repair 0.25.0** - JSON error correction
- **aiofiles 24.1.0** - Async file operations
- **tenacity** - Retry logic with exponential backoff

### Frontend
- **Vanilla JavaScript** - No framework (lightweight)
- **Firebase SDK** - Client-side auth
- **Responsive CSS** - Mobile-first design

---

## Codebase Structure

### Root Directory Layout

```
ProfeGo_RAG/
├── frontend/                      # Web interface
│   ├── index.html                # Landing page
│   ├── login.html                # Authentication
│   ├── menu.html                 # Main dashboard
│   ├── styles.css                # 56KB responsive styles
│   ├── shared.js                 # Common utilities
│   ├── login-script.js           # Auth logic
│   └── menu-script.js            # Dashboard logic
│
├── rag_system/                    # RAG implementation
│   ├── __init__.py               # RAGSystem orchestrator (main entry)
│   ├── embeddings.py             # Sentence Transformers wrapper
│   ├── vector_store.py           # ChromaDB interface
│   ├── document_processor.py     # Text chunking & metadata
│   ├── retriever.py              # Similarity search
│   ├── generator.py              # RAG-enhanced plan generation
│   └── metrics.py                # Performance tracking
│
├── rag_data/                      # Knowledge base (159 files)
│   ├── actividades/              # 43 educational activities
│   ├── canciones/                # 65 children's songs
│   ├── cuentos/                  # 51 stories
│   └── vector_db/                # ChromaDB persistent storage
│
├── test_vector_db/                # Test databases
├── test_rag_db/                   # Additional test data
│
├── main.py                        # 2,226 lines - FastAPI app (MAIN ENTRY)
├── gemini_service.py              # 759 lines - AI plan generator
├── gcs_storage.py                 # 367 lines - Cloud storage manager
├── PruebaOcr.py                   # 532 lines - OCR document converter
│
├── bucket.py                      # 668 lines - GCS testing utilities
├── demo_rag_proof.py              # 377 lines - RAG demonstration
├── test_rag.py                    # 229 lines - RAG testing
├── diagnostico_rag.py             # 227 lines - RAG diagnostics
├── init_rag.py                    # 108 lines - RAG initialization
│
├── requirements.txt               # 40+ dependencies
├── .env.example                   # Environment template
├── .gitignore                     # Security-focused
├── README.md                      # User documentation
└── CLAUDE.md                      # This file (AI assistant guide)
```

### File Roles & Responsibilities

#### Core Application Files

| File | Lines | Purpose | Key Classes/Functions |
|------|-------|---------|---------------------|
| `main.py` | 2,226 | FastAPI server, API endpoints | `app`, 18 routes, middleware setup |
| `gemini_service.py` | 759 | AI plan generation | `GeminiPlanGenerator`, `generar_plan_estudio()` |
| `gcs_storage.py` | 367 | Cloud file management | `GCSStorageManagerV2` |
| `PruebaOcr.py` | 532 | Document text extraction | `DocumentConverter`, async processing |

#### RAG System Files

| File | Purpose | Key Classes |
|------|---------|-------------|
| `rag_system/__init__.py` | RAG orchestrator | `RAGSystem`, `initialize_rag_system()` |
| `rag_system/embeddings.py` | Vector embeddings | `GeminiEmbeddings` |
| `rag_system/vector_store.py` | ChromaDB interface | `VectorStore` |
| `rag_system/document_processor.py` | Text chunking | `DocumentProcessor` |
| `rag_system/retriever.py` | Similarity search | `RAGRetriever` |
| `rag_system/generator.py` | RAG plan generation | `RAGPlanGenerator` |
| `rag_system/metrics.py` | Performance metrics | Performance tracking |

#### Testing & Utility Files

| File | Purpose |
|------|---------|
| `bucket.py` | GCS integration testing |
| `test_rag.py` | RAG system testing |
| `demo_rag_proof.py` | RAG demonstration |
| `diagnostico_rag.py` | RAG diagnostics |
| `init_rag.py` | Initialize RAG vector database |

---

## Development Workflows

### Starting the Application

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Run development server
python main.py

# Server runs on:
# - Frontend: http://127.0.0.1:8000
# - API Docs: http://127.0.0.1:8000/docs
# - Health: http://127.0.0.1:8000/health
```

### Initializing RAG System

```bash
# First time setup - index knowledge base
python init_rag.py

# This indexes:
# - 51 stories (cuentos/)
# - 65 songs (canciones/)
# - 43 activities (actividades/)
# Total: 159 documents in vector_db/
```

### Testing RAG System

```bash
# Run comprehensive tests
python test_rag.py

# Run diagnostics
python diagnostico_rag.py

# Test GCS integration
python bucket.py
```

### Document Processing Workflow

1. **User uploads file** → API endpoint `/api/files/upload`
2. **File validation** → Check size (<80MB), extension allowed
3. **GCS storage** → Save to `users/{email}/uploads/{year}/{month}/`
4. **OCR processing** → Extract text via `PruebaOcr.py`
5. **Return text** → Frontend displays extracted content

### Plan Generation Workflow

1. **User provides inputs**:
   - Plan de estudios (curriculum document - required)
   - Diagnóstico (group assessment - optional)
   - Number of modules (4-8)
2. **Text extraction** → OCR on uploaded files
3. **RAG retrieval** → Find relevant stories/songs/activities
4. **Gemini generation** → Create personalized plan
5. **JSON repair** → Fix any malformed JSON
6. **GCS storage** → Save to `users/{email}/processed/{year}/{month}/`
7. **Return plan** → Frontend displays modules

### User-Specific RAG Indexing

```python
# When user uploads new documents for indexing
rag_system = get_rag_system()
rag_system.add_user_documents(
    user_email="teacher@school.com",
    documents=[{"text": "...", "metadata": {...}}]
)
```

---

## Key Conventions & Patterns

### Architecture Patterns

#### 1. Clean Separation of Concerns

```
┌─────────────────┐
│   API Layer     │  main.py (routes, validation, auth)
└────────┬────────┘
         │
┌────────▼────────┐
│  Service Layer  │  gemini_service, gcs_storage, PruebaOcr
└────────┬────────┘
         │
┌────────▼────────┐
│   Data Layer    │  rag_system, ChromaDB, GCS
└─────────────────┘
```

#### 2. Async-First Design

- All FastAPI routes use `async def`
- Large file processing (>5MB) uses async executors
- `aiofiles` for async file I/O

#### 3. Error Handling Strategy

```python
# Pattern used throughout codebase:
try:
    result = await operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal error")
```

#### 4. Retry with Exponential Backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def call_gemini_api():
    # Auto-retry on failure
    pass
```

### Naming Conventions

#### Files
- **Snake case**: `gcs_storage.py`, `gemini_service.py`
- **CamelCase for classes**: `PruebaOcr.py` (contains `DocumentConverter`)

#### Variables
- **Snake case**: `plan_de_estudios`, `num_modulos`
- **Spanish names** for domain concepts: `campo_formativo`, `ejes_articulares`
- **English names** for technical concepts: `user_email`, `file_path`

#### Functions
- **Snake case**: `generar_plan_estudio()`, `process_file_to_txt()`
- **Descriptive names**: Clearly indicate what the function does

#### Classes
- **PascalCase**: `GeminiPlanGenerator`, `RAGSystem`, `DocumentConverter`

#### Constants
- **UPPER_SNAKE_CASE**: `MAX_FILE_SIZE`, `MODEL_NAME`, `TEMPERATURE`

### Code Organization

#### Imports
```python
# Standard library
import os
import json
from datetime import datetime

# Third-party
from fastapi import FastAPI, HTTPException
import google.generativeai as genai

# Local modules
from rag_system import get_rag_system
from gcs_storage import GCSStorageManagerV2
```

#### Logging
```python
import logging

logger = logging.getLogger(__name__)
logger.info("Operation started")
logger.warning("Potential issue")
logger.error("Operation failed")
```

### Data Validation

Uses **Pydantic** models throughout:

```python
from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

class PlanRequest(BaseModel):
    plan_de_estudios: str
    diagnostico: Optional[str] = None
    num_modulos: int = 5
```

### File Organization Patterns

#### GCS Storage Structure
```
bucket-name/
└── users/
    └── {email}/
        ├── uploads/          # User uploaded files
        │   └── {year}/
        │       └── {month}/
        │           └── file.pdf
        └── processed/        # Generated plans
            └── {year}/
                └── {month}/
                    └── plan_abc123.json
```

#### Local Storage (Development)
```
ProfeGo_RAG/
├── rag_data/
│   └── vector_db/           # ChromaDB persistent storage
├── test_vector_db/          # Testing only
└── Documents/               # Git-ignored user data
```

---

## API Architecture

### Main Endpoints (18 total)

#### Authentication
```
POST /api/auth/login       - User login (Firebase)
POST /api/auth/register    - User registration
```

#### File Management
```
POST   /api/files/upload              - Upload file to GCS
GET    /api/files/list                - List user's files
DELETE /api/files/delete/{filename}   - Delete file
GET    /api/files/download/{filename} - Download file
```

#### Plan Generation
```
POST /api/plans/generate              - Generate new plan
GET  /api/plans/list                  - List user's plans
GET  /api/plans/view/{plan_id}        - View specific plan
POST /api/plans/download-word         - Download plan as Word doc
```

#### RAG System
```
GET  /api/rag/status                  - RAG system health
POST /api/rag/analyze                 - Analyze with RAG
```

#### Static Files
```
GET /                                 - Serve index.html
GET /login                            - Serve login.html
GET /menu                             - Serve menu.html
GET /health                           - Health check
```

### CORS Configuration

```python
# Production (with RENDER_EXTERNAL_URL set)
allowed_origins = [
    "https://app.onrender.com",
    "https://app.onrender.com"
]

# Development (RENDER_EXTERNAL_URL not set)
allowed_origins = ["*"]
```

### Rate Limiting

```python
# Plan generation
@limiter.limit("5/hour")
async def generate_plan()

# File uploads
@limiter.limit("10/minute")
async def upload_file()
```

### Authentication Flow

```python
# All protected routes require:
authorization: str = Header(None, alias="Authorization")

# Token format: "Bearer {firebase_id_token}"
# Validated against Firebase
```

### File Size Limits

```python
MAX_FILE_SIZE = 80 * 1024 * 1024  # 80MB

ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt',
    '.jpg', '.jpeg', '.png',
    '.xlsx', '.xls', '.csv',
    '.json', '.xml'
}
```

---

## RAG System Details

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  RAGSystem                      │
│  (Orchestrator - rag_system/__init__.py)       │
└───────────┬─────────────────────────────────────┘
            │
    ┌───────┴────────┐
    │                │
    ▼                ▼
┌─────────┐    ┌──────────────┐
│Embedding│    │ VectorStore  │
│ Service │    │  (ChromaDB)  │
└────┬────┘    └──────┬───────┘
     │                │
     │    ┌───────────┴────────────┐
     │    │                        │
     ▼    ▼                        ▼
┌──────────────┐           ┌──────────────┐
│ Retriever    │           │  Generator   │
│ (Search)     │           │  (Gemini+RAG)│
└──────────────┘           └──────────────┘
```

### Components

#### 1. Embeddings (`rag_system/embeddings.py`)

```python
class GeminiEmbeddings:
    model_name = "all-MiniLM-L6-v2"
    dimensions = 384
    batch_size = 8  # Memory optimization

    def embed_documents(texts: List[str]) -> List[List[float]]
    def embed_query(text: str) -> List[float]
```

**Why this model?**
- Lightweight (33MB)
- Fast inference
- Good performance for educational content
- Low memory footprint (important for deployment)

#### 2. Vector Store (`rag_system/vector_store.py`)

```python
class VectorStore:
    db_path = "./rag_data/vector_db"
    collection_name = "profego_documents"
    distance = "cosine"

    def add_documents(documents, metadatas, ids)
    def similarity_search(query, k=5, filter=None)
    def delete_collection()
```

**Storage Format**:
```json
{
    "id": "cuento_001",
    "embedding": [0.123, -0.456, ...],  // 384 dimensions
    "metadata": {
        "type": "cuento",
        "titulo": "El patito feo",
        "edad": "4-5 años",
        "campo_formativo": "Lenguaje y Comunicación"
    },
    "text": "Había una vez..."
}
```

#### 3. Document Processor (`rag_system/document_processor.py`)

```python
class DocumentProcessor:
    chunk_size = 1000        # Characters
    chunk_overlap = 200      # Characters

    def process_document(text: str, metadata: dict) -> List[dict]
    def chunk_text(text: str) -> List[str]
```

**Chunking Strategy**:
- 1000 characters per chunk
- 200 character overlap (preserves context)
- Metadata propagated to all chunks

#### 4. Retriever (`rag_system/retriever.py`)

```python
class RAGRetriever:
    def retrieve(query: str, k: int = 5) -> List[Document]
    def retrieve_with_scores(query: str, k: int = 5)
```

**Retrieval Process**:
1. Embed query using `GeminiEmbeddings`
2. Cosine similarity search in ChromaDB
3. Return top-k most relevant documents
4. Optionally filter by metadata (user, type, etc.)

#### 5. Generator (`rag_system/generator.py`)

```python
class RAGPlanGenerator:
    def generate_plan(
        query: str,
        retrieved_docs: List[Document],
        num_modulos: int = 5
    ) -> dict
```

**Generation Flow**:
1. Retrieve relevant documents
2. Format context from retrieved docs
3. Construct prompt with context + user input
4. Call Gemini API
5. Parse and validate JSON response

### Knowledge Base Content

#### Categories (159 files total)

| Type | Count | Location | Purpose |
|------|-------|----------|---------|
| Cuentos (Stories) | 51 | `rag_data/cuentos/` | Literacy, comprehension |
| Canciones (Songs) | 65 | `rag_data/canciones/` | Music, rhythm, vocabulary |
| Actividades (Activities) | 43 | `rag_data/actividades/` | Hands-on learning |

#### Metadata Structure

```python
{
    "type": "cuento",  # or "cancion", "actividad"
    "titulo": "El patito feo",
    "edad": "4-5 años",
    "campo_formativo": "Lenguaje y Comunicación",
    "eje_articular": "Apropiación de las Culturas...",
    "duracion": "15 minutos",
    "materiales": ["libro", "cojines"],
    "objetivo": "Desarrollar empatía y comprensión lectora"
}
```

### RAG Initialization

**First time setup**:
```bash
python init_rag.py
```

**What it does**:
1. Scans `rag_data/` directories
2. Reads all `.txt` files
3. Generates embeddings (batch_size=3 for low memory)
4. Stores in ChromaDB (`rag_data/vector_db/`)
5. Logs progress and stats

**Memory Optimization**:
```python
batch_size = 3  # Process 3 documents at a time
gc.collect()     # Force garbage collection between batches
```

### User Document Indexing

```python
# In main.py - when user wants to index their own docs
rag_system = get_rag_system()

documents = [
    {
        "text": extracted_text,
        "metadata": {
            "user_email": user_email,
            "filename": filename,
            "upload_date": datetime.now().isoformat()
        }
    }
]

rag_system.add_user_documents(user_email, documents)
```

### RAG-Enhanced Plan Generation

```python
# gemini_service.py uses RAG
from rag_system import get_rag_system

rag_system = get_rag_system()

# Retrieve relevant content
query = f"actividades para {campo_formativo} nivel preescolar"
relevant_docs = rag_system.retriever.retrieve(query, k=5)

# Inject into prompt
context = "\n".join([doc.text for doc in relevant_docs])
prompt = f"""
Genera un plan de estudio considerando:

RECURSOS SUGERIDOS:
{context}

PLAN DE ESTUDIOS:
{plan_de_estudios}
...
"""
```

---

## Environment Setup

### Required Environment Variables

Create `.env` file in project root:

```bash
# ===================================
# FIREBASE (Authentication)
# ===================================
FIREBASE_API_KEY=your_api_key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789012
FIREBASE_APP_ID=1:123456789012:web:abc123
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com

# ===================================
# GOOGLE CLOUD STORAGE
# ===================================
GCS_BUCKET_NAME=bucket-profe-go
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# For cloud deployment (Render/Railway):
# GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account",...}'

# ===================================
# GOOGLE GEMINI AI
# ===================================
GEMINI_API_KEY=your_gemini_api_key

# ===================================
# DEPLOYMENT (Production only)
# ===================================
RENDER_EXTERNAL_URL=https://your-app.onrender.com

# ===================================
# OPTIONAL CONFIGURATION
# ===================================
MAX_FILE_SIZE_MB=80
PYTHONUNBUFFERED=1
```

### System Dependencies

#### Tesseract OCR (Required)

**Linux/Ubuntu**:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa
```

**macOS**:
```bash
brew install tesseract tesseract-lang
```

**Windows**:
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to `C:\Program Files\Tesseract-OCR`
3. Add to PATH environment variable

**Verify installation**:
```bash
tesseract --version
# Should output: tesseract 4.x.x or 5.x.x
```

#### Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import torch; print(torch.__version__)"
python -c "import chromadb; print(chromadb.__version__)"
```

### Google Cloud Setup

#### 1. Create GCS Bucket

```bash
# Using gcloud CLI
gcloud storage buckets create gs://bucket-profe-go \
    --location=us-central1 \
    --uniform-bucket-level-access

# Or via console: https://console.cloud.google.com/storage
```

#### 2. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create profego-service \
    --display-name="ProfeGo Service Account"

# Grant storage permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:profego-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Download key
gcloud iam service-accounts keys create google-cloud-key.json \
    --iam-account=profego-service@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

**IMPORTANT**: Add `google-cloud-key.json` to `.gitignore`!

#### 3. Firebase Setup

1. Go to https://console.firebase.google.com
2. Create new project
3. Enable Authentication → Email/Password
4. Get config from Project Settings → General → Your apps
5. Add to `.env`

### Gemini API Key

1. Visit: https://makersuite.google.com/app/apikey
2. Create API key (FREE tier available)
3. Add to `.env` as `GEMINI_API_KEY`

**Rate Limits (Free tier)**:
- 60 requests per minute
- 1,500 requests per day
- 32,000 tokens per request

---

## Common Tasks

### Adding New RAG Documents

```bash
# 1. Add files to appropriate directory
cp new_story.txt rag_data/cuentos/

# 2. Re-initialize RAG system
python init_rag.py

# 3. Verify
python diagnostico_rag.py
```

### Testing OCR

```python
from PruebaOcr import process_file_to_txt

# Test single file
result = await process_file_to_txt(
    file_path="/path/to/document.pdf",
    max_pages=10
)
print(result)
```

### Manual Plan Generation

```python
from gemini_service import generar_plan_estudio

plan = await generar_plan_estudio(
    plan_de_estudios="...",
    diagnostico="...",  # Optional
    num_modulos=5,
    user_email="teacher@school.com"
)

print(json.dumps(plan, indent=2, ensure_ascii=False))
```

### Testing GCS Storage

```bash
# Run comprehensive GCS tests
python bucket.py

# Tests:
# - File upload
# - File listing
# - File download
# - File deletion
# - User initialization
```

### Querying RAG System

```python
from rag_system import get_rag_system

rag = get_rag_system()

# Search for content
results = rag.retriever.retrieve(
    query="canciones sobre números para preescolar",
    k=5
)

for doc in results:
    print(f"Título: {doc.metadata['titulo']}")
    print(f"Texto: {doc.text[:200]}...")
    print("---")
```

### Adding New API Endpoint

1. **Define Pydantic model** (if needed):
```python
class NewRequest(BaseModel):
    field1: str
    field2: int
```

2. **Create route** in `main.py`:
```python
@app.post("/api/new-endpoint")
@limiter.limit("10/minute")
async def new_endpoint(
    request: NewRequest,
    authorization: str = Header(None)
):
    # Validate auth
    user_email = validate_firebase_token(authorization)

    # Business logic
    result = do_something(request.field1, request.field2)

    return {"status": "success", "data": result}
```

3. **Add frontend integration** in `menu-script.js`:
```javascript
async function callNewEndpoint(data) {
    const response = await fetch('/api/new-endpoint', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${firebaseToken}`
        },
        body: JSON.stringify(data)
    });
    return await response.json();
}
```

### Debugging Common Issues

#### Issue: "GEMINI_API_KEY not configured"
```bash
# Check .env file exists
cat .env | grep GEMINI_API_KEY

# Verify it's loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"
```

#### Issue: "Tesseract not found"
```bash
# Find Tesseract
which tesseract          # Linux/Mac
where tesseract          # Windows

# Test Tesseract
tesseract --list-langs   # Should show 'spa' for Spanish
```

#### Issue: "Bucket not found"
```bash
# List buckets
gsutil ls

# Check permissions
gsutil iam get gs://bucket-profe-go
```

#### Issue: "ChromaDB collection not found"
```bash
# Re-initialize
python init_rag.py

# Check
python diagnostico_rag.py
```

---

## Code Style

### Python Style Guide

Follows **PEP 8** with some customizations:

#### Formatting
- **Line length**: 100 characters (not strict)
- **Indentation**: 4 spaces
- **String quotes**: Double quotes `"` preferred
- **Docstrings**: Triple double quotes `"""`

#### Docstrings

```python
def generar_plan_estudio(
    plan_de_estudios: str,
    diagnostico: Optional[str] = None,
    num_modulos: int = 5
) -> Dict:
    """
    Genera un plan de estudio personalizado usando Gemini AI

    Args:
        plan_de_estudios: Texto del plan oficial extraído del documento
        diagnostico: Texto del diagnóstico del grupo (opcional)
        num_modulos: Número de módulos a generar (4-8)

    Returns:
        Dict con estructura del plan generado

    Raises:
        HTTPException: Si falla la generación o validación
    """
```

#### Comments

```python
# ===================================
# SECTION HEADERS (for grouping imports, config, etc.)
# ===================================

# Single line explanations
result = complex_operation()  # Inline comments sparingly

# Multi-line explanations
# This is a complex algorithm that:
# 1. Does step one
# 2. Does step two
# 3. Returns result
```

#### Type Hints

**Always use** type hints for function signatures:

```python
from typing import List, Dict, Optional, Union

def process_files(
    file_paths: List[str],
    max_size: int = 80
) -> Dict[str, Union[str, int]]:
    pass
```

### JavaScript Style Guide

#### Formatting
- **Indentation**: 4 spaces (matching Python)
- **String quotes**: Single quotes `'` preferred
- **Semicolons**: Optional but consistent

#### Async/Await
```javascript
async function generatePlan(formData) {
    try {
        const response = await fetch('/api/plans/generate', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Generation failed');
        }

        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
    }
}
```

#### Error Handling
```javascript
// Always catch and display errors
try {
    await operation();
} catch (error) {
    console.error('Operation failed:', error);
    showNotification('Error: ' + error.message, 'error');
}
```

### CSS Conventions

#### Class Naming
- **BEM-style** preferred: `.block__element--modifier`
- **Descriptive names**: `.plan-card`, `.module-header`

#### Organization
```css
/* ===================================
   SECTION NAME
   =================================== */

.selector {
    /* Layout */
    display: flex;

    /* Positioning */
    position: relative;

    /* Box Model */
    width: 100%;
    padding: 1rem;

    /* Typography */
    font-size: 1rem;

    /* Visual */
    background: white;
    border: 1px solid #ccc;

    /* Misc */
    transition: all 0.3s;
}
```

---

## Testing & Debugging

### Manual Testing Checklist

#### Backend Tests
- [ ] Start server: `python main.py`
- [ ] Check health: `curl http://localhost:8000/health`
- [ ] Test OCR: `python PruebaOcr.py`
- [ ] Test RAG: `python test_rag.py`
- [ ] Test GCS: `python bucket.py`
- [ ] View API docs: http://localhost:8000/docs

#### Frontend Tests
- [ ] Login flow
- [ ] File upload (various formats)
- [ ] Plan generation
- [ ] Plan viewing
- [ ] File download
- [ ] Logout

### Logging Configuration

```python
import logging

# Configure at module level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use throughout code
logger.info("Starting operation")
logger.warning("Potential issue detected")
logger.error("Operation failed", exc_info=True)
```

### Debug Mode

```python
# In main.py - enable detailed error messages
app = FastAPI(
    title="ProfeGo API",
    version="2.0.0",
    debug=True  # Only in development!
)
```

### Common Debug Commands

```bash
# Check environment
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('GCS:', os.getenv('GCS_BUCKET_NAME'))"

# Test imports
python -c "from rag_system import get_rag_system; print('RAG OK')"

# Check ChromaDB
python -c "import chromadb; client = chromadb.PersistentClient('./rag_data/vector_db'); print(client.list_collections())"

# Verify Tesseract
tesseract --list-langs
```

### Performance Monitoring

```python
import time

start = time.time()
result = await expensive_operation()
elapsed = time.time() - start

logger.info(f"Operation took {elapsed:.2f}s")
```

---

## Deployment

### Local Development

```bash
# Standard development server
python main.py

# Or with uvicorn directly (hot reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment (Render/Railway)

#### 1. Prepare Repository

**Ensure `.gitignore` includes**:
```
.env
*.json  # Except package.json
google-cloud-key.json
Documents/
```

**Commit and push**:
```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

#### 2. Render Configuration

**Build Command**:
```bash
pip install -r requirements.txt && apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-spa
```

**Start Command**:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Environment Variables** (set in Render dashboard):
```
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=...
FIREBASE_PROJECT_ID=...
FIREBASE_STORAGE_BUCKET=...
FIREBASE_MESSAGING_SENDER_ID=...
FIREBASE_APP_ID=...
FIREBASE_DATABASE_URL=...
GCS_BUCKET_NAME=bucket-profe-go
GEMINI_API_KEY=...
RENDER_EXTERNAL_URL=https://your-app.onrender.com

# For GCS credentials (IMPORTANT)
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```

**Note**: In `gcs_storage.py`, the code checks for `GOOGLE_APPLICATION_CREDENTIALS_JSON` environment variable and creates a temporary file if present.

#### 3. Railway Configuration

Similar to Render, but set environment variables in Railway dashboard.

**Start Command**:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

#### 4. Post-Deployment

1. **Initialize RAG** (if vector_db not in repo):
```bash
# SSH into deployment or run via admin endpoint
python init_rag.py
```

2. **Test endpoints**:
```bash
curl https://your-app.onrender.com/health
curl https://your-app.onrender.com/api/rag/status
```

3. **Monitor logs**:
   - Check Render/Railway logs for errors
   - Look for Tesseract installation success
   - Verify ChromaDB initialization

### Docker Deployment (Optional)

**Dockerfile** (create if needed):
```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run**:
```bash
docker build -t profego .
docker run -p 8000:8000 --env-file .env profego
```

---

## Important Notes for AI Assistants

### When Making Changes

1. **Always read files before editing**
   - Use `Read` tool to see current state
   - Understand context before modifications

2. **Preserve Spanish domain language**
   - Educational terms stay in Spanish: `campo_formativo`, `eje_articular`
   - Technical terms in English: `user_email`, `file_path`

3. **Maintain async patterns**
   - All FastAPI routes should be `async def`
   - Use `await` for I/O operations
   - Use `aiofiles` for file operations

4. **Test before committing**
   - Run `python main.py` to verify syntax
   - Test affected endpoints
   - Check logs for errors

5. **Update documentation**
   - If adding major features, update README.md
   - Update this CLAUDE.md if architecture changes
   - Add docstrings to new functions

### Critical Files - Handle with Care

| File | Why Critical | Before Editing |
|------|--------------|----------------|
| `main.py` | Main application entry | Test all routes after changes |
| `gemini_service.py` | AI generation core | Verify Gemini API calls still work |
| `rag_system/__init__.py` | RAG orchestrator | Test with `test_rag.py` |
| `requirements.txt` | Dependencies | Check version compatibility |
| `.env.example` | Template for users | Keep in sync with actual requirements |

### Security Considerations

1. **Never commit secrets**
   - Check `.gitignore` before adding files
   - Use environment variables for all credentials

2. **Validate user input**
   - Use Pydantic models for request validation
   - Sanitize file uploads
   - Check file extensions and sizes

3. **Firebase token validation**
   - All protected routes must validate tokens
   - Extract `user_email` from validated token
   - Use for access control

4. **Rate limiting**
   - Apply to expensive operations
   - Prevent abuse of AI generation

### Performance Optimization

1. **RAG System**
   - Use small batches (3-8 documents) for low memory
   - Call `gc.collect()` after large operations
   - Use persistent ChromaDB (not in-memory)

2. **File Processing**
   - Async for files >5MB
   - Set reasonable page limits (10-20 for OCR)
   - Stream large downloads

3. **Caching**
   - Consider caching embeddings
   - Cache frequently accessed plans
   - Use ETags for static files

### Common Pitfalls to Avoid

1. **Tesseract path issues**
   - Test on target platform (Linux for Render)
   - Ensure `tesseract-ocr-spa` is installed

2. **ChromaDB persistence**
   - Always use absolute paths
   - Ensure directory exists before initialization

3. **JSON parsing from Gemini**
   - Always use `json_repair` for robustness
   - Validate structure with Pydantic

4. **GCS credentials**
   - Different handling for local vs. cloud deployment
   - Check `GOOGLE_APPLICATION_CREDENTIALS_JSON` env var

5. **CORS in production**
   - Set proper `RENDER_EXTERNAL_URL`
   - Don't use `allow_origins=["*"]` in production

### Debugging Workflow

When user reports an issue:

1. **Reproduce**
   ```bash
   # Check logs
   tail -f logs/app.log

   # Test specific endpoint
   curl -X POST http://localhost:8000/api/endpoint \
        -H "Content-Type: application/json" \
        -d '{"test": "data"}'
   ```

2. **Isolate**
   - Is it frontend or backend?
   - Which component is failing?
   - Can you reproduce in test scripts?

3. **Fix**
   - Make minimal changes
   - Add logging if needed
   - Test thoroughly

4. **Verify**
   - Run affected tests
   - Check related functionality
   - Monitor logs

### Best Practices for AI Assistance

1. **Be explicit about changes**
   - Explain what you're changing and why
   - Show before/after for clarity

2. **Consider backward compatibility**
   - Will existing data still work?
   - Do existing API clients need updates?

3. **Document new patterns**
   - If introducing new architecture, explain it
   - Update this guide if needed

4. **Test integration points**
   - Frontend ↔ Backend
   - Backend ↔ GCS
   - Backend ↔ Gemini
   - Backend ↔ ChromaDB

### Educational Context Awareness

Remember this is for **Mexican preschool education**:

- **Age group**: 4-5 years old (2nd grade preschool)
- **Focus**: Play-based, hands-on learning
- **Language**: Spanish
- **Curriculum**: Official Mexican standards
- **Activities**: Age-appropriate, safe, engaging

When suggesting changes to educational content:
- Keep language simple and encouraging
- Suggest concrete, visual activities
- Consider short attention spans (10-15 min activities)
- Align with Mexican cultural context

### Git Workflow

```bash
# Always work on feature branches
git checkout -b feature/new-feature

# Make changes
# Test thoroughly

# Commit with clear messages
git add .
git commit -m "feat: Add user document indexing to RAG system

- Implement user-specific document upload
- Add metadata filtering in vector store
- Update API endpoint documentation"

# Push to branch specified in instructions
git push -u origin claude/claude-md-mi0ixgi5yfl4mhlv-01Pivobs2oUMviEUrFWUeyvN
```

### Version Control Best Practices

- **Commit often**: Small, focused commits
- **Clear messages**: Describe what and why
- **Test before commit**: Ensure code works
- **Update docs**: Keep README and CLAUDE.md current

---

## Quick Reference

### Start Commands
```bash
# Development
python main.py

# With hot reload
uvicorn main:app --reload

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Test Commands
```bash
python init_rag.py          # Initialize RAG
python test_rag.py          # Test RAG system
python diagnostico_rag.py   # RAG diagnostics
python bucket.py            # Test GCS
```

### Important URLs
- Frontend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Key File Paths
- Config: `.env`
- Credentials: `google-cloud-key.json`
- Vector DB: `./rag_data/vector_db/`
- Knowledge Base: `./rag_data/{cuentos|canciones|actividades}/`

### Environment Variables (Quick Copy)
```bash
FIREBASE_API_KEY=
FIREBASE_AUTH_DOMAIN=
FIREBASE_PROJECT_ID=
FIREBASE_STORAGE_BUCKET=
FIREBASE_MESSAGING_SENDER_ID=
FIREBASE_APP_ID=
FIREBASE_DATABASE_URL=
GCS_BUCKET_NAME=
GOOGLE_APPLICATION_CREDENTIALS=
GEMINI_API_KEY=
```

---

## Changelog

### Version 2.0.0 (Current)
- RAG system integration
- Enhanced plan generation with context retrieval
- User-specific document indexing
- Improved error handling with JSON repair
- Rate limiting and security enhancements

### Future Improvements (TODO)
- [ ] Add unit tests for core functions
- [ ] Implement caching for embeddings
- [ ] Add plan templates for quick generation
- [ ] Export plans to PDF (currently Word only)
- [ ] Multi-language support (beyond Spanish)
- [ ] Analytics dashboard for teachers
- [ ] Collaborative planning features

---

**Document Maintained By**: AI Assistant (Claude)
**For Issues**: Create GitHub issue or contact profego.soporte@gmail.com
**License**: Educational use

---

*This guide is designed to help AI assistants understand and work with the ProfeGo codebase effectively. Keep it updated as the project evolves.*
