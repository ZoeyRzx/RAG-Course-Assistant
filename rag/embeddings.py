from __future__ import annotations

from typing import Any

from langchain_core.embeddings import Embeddings


def _resolve_model_path(model_name: str) -> str:
    """Try to resolve model via modelscope if huggingface is unreachable."""
    import os
    # If it's already a local path, use it directly
    if os.path.exists(model_name):
        return model_name
    try:
        from modelscope import snapshot_download
        cache_dir = os.getenv("MODELSCOPE_CACHE_DIR")
        kwargs = {"cache_dir": cache_dir} if cache_dir else {}
        local_path = snapshot_download(model_name, **kwargs)
        return local_path
    except Exception:
        # Fall back to original name (HF cache or direct load)
        return model_name


class LocalSentenceTransformerEmbeddings(Embeddings):
    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        normalize_embeddings: bool = True,
    ):
        self.model_name = model_name
        self.device = device
        self.normalize_embeddings = normalize_embeddings
        self._model: Any | None = None

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            model_path = _resolve_model_path(self.model_name)
            self._model = SentenceTransformer(model_path, device=self.device)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [embedding.tolist() for embedding in embeddings]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
