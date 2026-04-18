# Course Material RAG Backend

This backend is now split into two explicit pipelines:

1. Offline indexing pipeline
2. Online query pipeline

The goal is to support course-material question answering over:

- PDF
- PPT-exported PDF
- lecture notes
- assignment handouts
- FAQ in Markdown
- plain text files

## Architecture

### Offline: indexing pipeline

The indexing pipeline does the following:

1. Parse supported files (`pdf`, `md`, `txt`)
2. Clean extracted text
3. Split content by paragraph / section with overlap
4. Attach metadata to each chunk
5. Compute embeddings
6. Write embeddings into a FAISS vector index
7. Store raw text and chunk metadata in a SQLite metadata store

Outputs:

- `Vector DB`: semantic retrieval
- `Metadata Store / Doc Store`: original text, page range, title, section, chunk metadata

### Online: query pipeline

The query pipeline does the following:

1. Normalize the user question
2. Retrieve top-k chunks from FAISS
3. Optionally rerank with a cross-encoder
4. Assemble the final context
5. Generate a grounded answer
6. Return:
   - answer
   - citations
   - supporting chunks
   - retrieved chunks
   - fallback decision

## Module layout

```text
rag/
app.py
cli.py
config.py
models.py
parsing.py
chunking.py
indexing.py
stores.py
retrieval.py
generation.py
pipelines.py
rag_backend_prototype.py
```

## Core metadata retained

Each chunk keeps the fields needed for traceable RAG:

- `doc_id`
- `title`
- `page_start`
- `page_end`
- `section`
- `chunk_id`

## Storage design

### Vector DB

FAISS stores the chunk embeddings for ANN retrieval.

Default path:

```text
rag/storage/faiss_index
```

### Metadata store

SQLite stores:

- document-level raw text
- document metadata
- chunk text
- chunk metadata

Default path:

```text
rag/storage/metadata.sqlite3
```

## Chunking defaults

The default chunking strategy is intentionally conservative:

- target chunk size: `600` tokens
- max chunk size: `800` tokens
- overlap: `80` tokens

Chunks are built from paragraph / section blocks, not sentence-only fragments.

## Environment variables

Example `.env`:

```env
OPENAI_API_KEY=your_key_here
RAG_DATA_DIR=./rag/storage
VECTOR_DB_PATH=./rag/storage/faiss_index
METADATA_DB_PATH=./rag/storage/metadata.sqlite3
EMBEDDING_BACKEND=openai
EMBEDDING_MODEL=text-embedding-3-small
LOCAL_EMBEDDING_MODEL=BAAI/bge-m3
LOCAL_EMBEDDING_DEVICE=cpu
GEN_MODEL=gpt-4.1-mini
GENERATOR_BACKEND=openai
LOCAL_GENERATOR_MODEL=Qwen/Qwen2.5-7B-Instruct
LOCAL_GENERATOR_DEVICE=cpu
LOCAL_GENERATOR_DTYPE=auto
LOCAL_GENERATOR_MAX_NEW_TOKENS=512
LOCAL_GENERATOR_DO_SAMPLE=false
LOCAL_GENERATOR_TEMPERATURE=0.1
ENABLE_RERANKER=false
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
CHUNK_TARGET_TOKENS=600
CHUNK_MAX_TOKENS=800
CHUNK_OVERLAP_TOKENS=80
TOP_K_RETRIEVAL=5
FETCH_K_RETRIEVAL=8
MAX_CONTEXT_CHARS=12000
MIN_RERANK_SCORE=-2.0
```

## CLI usage

Run from repository root.

### Build / rebuild the index

```bash
python -m rag.cli build-index ./data/course_materials
```

You can also pass multiple files and directories:

```bash
python -m rag.cli build-index ./docs/lecture1.pdf ./docs/faq.md ./notes
```

### Query the indexed corpus

```bash
python -m rag.cli query "What is retrieval-augmented generation?" --top-k 3
```

### Offline local query with a Hugging Face model

```bash
EMBEDDING_BACKEND=local \
LOCAL_EMBEDDING_MODEL=BAAI/bge-m3 \
GENERATOR_BACKEND=local \
LOCAL_GENERATOR_MODEL=Qwen/Qwen2.5-7B-Instruct \
LOCAL_GENERATOR_DEVICE=cpu \
ENABLE_RERANKER=false \
python -m rag.cli query "What is retrieval-augmented generation?" --top-k 3
```

### List indexed documents

```bash
python -m rag.cli list-docs
```

## PowerShell scripts

These scripts are intended for quick local testing on Windows.

### Install dependencies

```powershell
powershell -ExecutionPolicy Bypass -File .\rag\scripts\setup.ps1
```

### Run a local smoke test

This validates parsing, chunking, and SQLite storage without calling OpenAI.

```powershell
powershell -ExecutionPolicy Bypass -File .\rag\scripts\smoke-test.ps1
```

### Build an index from the bundled sample data

This requires `OPENAI_API_KEY`.

```powershell
powershell -ExecutionPolicy Bypass -File .\rag\scripts\build-sample-index.ps1
```

### Query the current index

This requires `OPENAI_API_KEY`.

```powershell
powershell -ExecutionPolicy Bypass -File .\rag\scripts\query-sample.ps1 -Question "What is retrieval-augmented generation?"
```

### Run the full demo flow

This runs smoke test, build index, list docs, and query in sequence.

```powershell
powershell -ExecutionPolicy Bypass -File .\rag\scripts\demo-end-to-end.ps1
```

### Start the API

```powershell
powershell -ExecutionPolicy Bypass -File .\rag\scripts\run-api.ps1
```

## Bash scripts

These scripts are intended for Linux or macOS shells.

### Install dependencies

```bash
bash ./rag/scripts/setup.sh
```

### Run a local smoke test

This validates parsing, chunking, and SQLite storage without calling OpenAI.

```bash
bash ./rag/scripts/smoke-test.sh
```

### Build an index from the bundled sample data

This requires `OPENAI_API_KEY`.

```bash
export OPENAI_API_KEY="your_key_here"
bash ./rag/scripts/build-sample-index.sh
```

### Query the current index

This requires `OPENAI_API_KEY`.

```bash
bash ./rag/scripts/query-sample.sh --question "What is retrieval-augmented generation?" --top-k 3
```

### Run the full demo flow

This runs smoke test, build index, list docs, and query in sequence.

```bash
bash ./rag/scripts/demo-end-to-end.sh
```

### Start the API

```bash
bash ./rag/scripts/run-api.sh --host 0.0.0.0 --port 8000
```

## Offline Qwen scripts

These scripts use local embeddings plus a local Hugging Face causal LM.

### Build the sample index with local embeddings

```bash
bash ./rag/scripts/build-sample-index-local.sh
```

### Query with a local Qwen model

```bash
bash ./rag/scripts/query-local-qwen.sh \
  --generator-model Qwen/Qwen2.5-7B-Instruct \
  --device cpu \
  --question "What is RAG?"
```

### Run the full offline demo

```bash
bash ./rag/scripts/demo-offline-qwen.sh \
  --generator-model Qwen/Qwen2.5-7B-Instruct \
  --device cpu
```

### Start the API with a local Qwen model

```bash
bash ./rag/scripts/run-api-local-qwen.sh \
  --generator-model Qwen/Qwen2.5-7B-Instruct \
  --device cpu \
  --host 0.0.0.0 \
  --port 8000
```

## API usage

Start the API from repository root:

```bash
uvicorn rag.app:app --reload
```

Endpoints:

- `GET /`
- `GET /health`
- `GET /documents`
- `POST /index/rebuild`
- `POST /query`

### `POST /index/rebuild`

```json
{
  "paths": [
    "C:/Users/Max/Project/NTU/ai6130-proj/data"
  ]
}
```

### `POST /query`

```json
{
  "question": "What is retrieval-augmented generation?",
  "top_k": 3
}
```

Example response:

```json
{
  "question": "What is retrieval-augmented generation?",
  "normalized_question": "What is retrieval-augmented generation?",
  "answer": "Retrieval-augmented generation combines retrieval with generation so the model answers using retrieved evidence [1].",
  "citations": [
    {
      "source_id": 1,
      "chunk_id": "abcd1234:0000",
      "doc_id": "abcd1234",
      "title": "lecture_3",
      "text": "RAG first retrieves relevant documents before generation...",
      "page_start": 12,
      "page_end": 12,
      "section": "Retrieval-Augmented Generation",
      "retrieval_score": 0.91,
      "rerank_score": 7.82,
      "metadata": {}
    }
  ],
  "supporting_chunks": ["... omitted for brevity ..."],
  "retrieved_chunks": ["... omitted for brevity ..."],
  "used_fallback": false,
  "decision": "sendable"
}
```

## Notes

- `pdf`, `md`, and `txt` are supported in this version.
- PDF section detection is heuristic because extracted page text often loses layout.
- The vector index and metadata store are intentionally separate.
- Reranking is optional and disabled by default. Set `ENABLE_RERANKER=true` if you want to enable the cross-encoder reranker.
- For fully offline runs, set both `EMBEDDING_BACKEND=local` and `GENERATOR_BACKEND=local`.
- `LOCAL_GENERATOR_MODEL` can be either a Hugging Face repo id or a local model directory.
- If no relevant evidence exists, the generator is instructed to reply:
  `I don't know based on the provided materials.`
