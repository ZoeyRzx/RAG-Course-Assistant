from __future__ import annotations

try:
    from .app import app
    from .config import get_settings
    from .pipelines import RAGSystem
except ImportError:
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from rag.app import app
    from rag.config import get_settings
    from rag.pipelines import RAGSystem


settings = get_settings()
rag_system = RAGSystem(settings)


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    sample_question = "What is retrieval-augmented generation?"
    try:
        result = rag_system.query(sample_question)
    except Exception as exc:
        print(f"Backend debug run failed: {exc}")
    else:
        print(json.dumps(asdict(result), indent=2))
