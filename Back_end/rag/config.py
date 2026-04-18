from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    base_dir: Path = Path(__file__).resolve().parent
    data_dir: Path = Path(os.getenv("RAG_DATA_DIR", str(Path(__file__).resolve().parent / "storage")))
    vector_db_path: Path = Path(
        os.getenv("VECTOR_DB_PATH", str(Path(__file__).resolve().parent / "storage" / "faiss_index"))
    )
    metadata_db_path: Path = Path(
        os.getenv("METADATA_DB_PATH", str(Path(__file__).resolve().parent / "storage" / "metadata.sqlite3"))
    )
    embedding_backend: str = os.getenv("EMBEDDING_BACKEND", "openai").strip().lower()
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    local_embedding_model: str = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-m3")
    local_embedding_device: str = os.getenv("LOCAL_EMBEDDING_DEVICE", "cpu")
    local_embedding_normalize: bool = _bool_env("LOCAL_EMBEDDING_NORMALIZE", True)
    generator_backend: str = os.getenv("GENERATOR_BACKEND", "openai").strip().lower()
    generator_model: str = os.getenv("GEN_MODEL", "gpt-4.1-mini")
    local_generator_model: str = os.getenv("LOCAL_GENERATOR_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    local_generator_device: str = os.getenv("LOCAL_GENERATOR_DEVICE", "cpu")
    local_generator_dtype: str = os.getenv("LOCAL_GENERATOR_DTYPE", "auto").strip().lower()
    local_generator_max_new_tokens: int = int(os.getenv("LOCAL_GENERATOR_MAX_NEW_TOKENS", "512"))
    local_generator_do_sample: bool = _bool_env("LOCAL_GENERATOR_DO_SAMPLE", False)
    local_generator_temperature: float = float(os.getenv("LOCAL_GENERATOR_TEMPERATURE", "0.1"))
    local_generator_trust_remote_code: bool = _bool_env("LOCAL_GENERATOR_TRUST_REMOTE_CODE", False)
    local_generator_disable_thinking: bool = _bool_env("LOCAL_GENERATOR_DISABLE_THINKING", True)
    reranker_model: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    enable_reranker: bool = _bool_env("ENABLE_RERANKER", False)
    chunk_target_tokens: int = int(os.getenv("CHUNK_TARGET_TOKENS", "600"))
    chunk_max_tokens: int = int(os.getenv("CHUNK_MAX_TOKENS", "800"))
    chunk_overlap_tokens: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "80"))
    retrieval_top_k: int = int(os.getenv("TOP_K_RETRIEVAL", "5"))
    retrieval_fetch_k: int = int(os.getenv("FETCH_K_RETRIEVAL", "8"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))
    rerank_score_threshold: float | None = (
        float(os.getenv("MIN_RERANK_SCORE"))
        if os.getenv("MIN_RERANK_SCORE") is not None
        else None
    )
    supported_extensions: tuple[str, ...] = (".pdf", ".md", ".txt")


def get_settings() -> Settings:
    return Settings()
