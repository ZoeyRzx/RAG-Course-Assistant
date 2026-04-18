from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path

from tqdm import tqdm

# Load .env from the rag/ directory
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

"""
Evaluation code for two experiments:

Experiment 1: Direct LLM vs RAG
- Compare correctness / groundedness / hallucination rate

Experiment 2: Retrieval ablation
- similarity search vs MMR vs MMR + reranker
- Compare generation quality per category

Dataset format (test.json):
[
  {
    "id": 1,
    "question": "...",
    "gold_answer": "...",
    "evidence": "Lecture 5 – Why Pre-training",
    "category": "pretraining"
  }
]

Environment variables:
  EMBEDDING_BACKEND=local
  LOCAL_EMBEDDING_MODEL=/path/to/bge-m3
  LOCAL_EMBEDDING_DEVICE=cpu
  GENERATOR_BACKEND=local
  LOCAL_GENERATOR_MODEL=Qwen/Qwen2.5-7B-Instruct
  LOCAL_GENERATOR_DEVICE=cuda
  LOCAL_GENERATOR_DTYPE=float16
  MODELSCOPE_CACHE_DIR=/data1/zhj/model
  ENABLE_RERANKER=false
  OPENAI_API_KEY=sk-...          # for judge only
  JUDGE_MODEL=gpt-4.1-mini
  EVAL_DATA_PATH=./rag/test.json
  OUTPUT_DIR=./eval_outputs
  TOP_K=3
  TOP_K_RETRIEVAL=6
"""

# =========================
# Config
# =========================
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "qwen-plus")
EVAL_DATA_PATH = os.getenv("EVAL_DATA_PATH", "./rag/test.json")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./eval_outputs")
TOP_K = int(os.getenv("TOP_K", "3"))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "6"))
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./faiss_index")
RETRIEVAL_EMBEDDING_MODEL = os.getenv(
    "RETRIEVAL_EMBEDDING_MODEL", "/data1/zhj/model/BAAI/bge-m3"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# Data classes
# =========================
@dataclass
class EvalItem:
    id: int
    question: str
    gold_answer: str
    evidence: str
    category: str


@dataclass
class RetrievalResult:
    source: str
    section: Optional[str]
    chunk_id: Optional[str]
    text: str
    score: Optional[float] = None


@dataclass
class GenerationEval:
    correctness: int
    groundedness: int
    hallucination: int
    relevance: int
    rationale: str


# =========================
# Utils
# =========================
def load_eval_data(path: str) -> List[EvalItem]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [EvalItem(**item) for item in raw]


def docs_to_context(docs: List[RetrievalResult]) -> str:
    blocks = []
    for i, d in enumerate(docs, start=1):
        blocks.append(
            f"[S{i}] source={d.source}; section={d.section}; chunk_id={d.chunk_id}\n{d.text}"
        )
    return "\n\n".join(blocks)


# =========================
# Local RAG pipeline
# retrieval: bge-m3 via rag.pipelines
# generation: Qwen2.5 via rag.generation
# =========================
class LocalRAGPipeline:
    """Uses the existing rag pipeline (bge-m3 embedding + Qwen2.5 generation)."""

    def __init__(self):
        from .config import get_settings
        from .generation import AnswerGenerator
        from .indexing import VectorIndex
        from .retrieval import Retriever
        from .stores import MetadataStore

        self.settings = get_settings()
        self.metadata_store = MetadataStore(self.settings.metadata_db_path)
        self.vector_index = VectorIndex(self.settings)
        self.retriever = Retriever(
            self.settings, self.vector_index, self.metadata_store
        )
        self.generator = AnswerGenerator(self.settings)

    def _to_results(self, chunks) -> List[RetrievalResult]:
        return [
            RetrievalResult(
                source=c.title,
                section=c.section,
                chunk_id=c.chunk_id,
                text=c.text,
                score=c.retrieval_score,
            )
            for c in chunks
        ]

    def retrieve_similarity(
        self, question: str, k: int = TOP_K
    ) -> List[RetrievalResult]:
        _nq, retrieved, _support = self.retriever.retrieve(question, top_k=k)
        return self._to_results(retrieved[:k])

    def retrieve_mmr(
        self, question: str, k: int = TOP_K, fetch_k: int = TOP_K_RETRIEVAL
    ) -> List[RetrievalResult]:
        vectorstore = self.vector_index.load()
        docs = vectorstore.max_marginal_relevance_search(question, k=k, fetch_k=fetch_k)
        return [
            RetrievalResult(
                source=doc.metadata.get("title", "unknown"),
                section=doc.metadata.get("section"),
                chunk_id=doc.metadata.get("chunk_id"),
                text=doc.page_content,
                score=None,
            )
            for doc in docs
        ]

    def retrieve_mmr_rerank(
        self, question: str, k_final: int = TOP_K, fetch_k: int = TOP_K_RETRIEVAL
    ) -> List[RetrievalResult]:
        vectorstore = self.vector_index.load()
        docs = vectorstore.max_marginal_relevance_search(
            question, k=fetch_k, fetch_k=max(fetch_k * 2, 10)
        )
        try:
            from sentence_transformers import CrossEncoder

            reranker_model = os.getenv(
                "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )
            reranker = CrossEncoder(reranker_model)
            pairs = [(question, doc.page_content[:1200]) for doc in docs]
            scores = reranker.predict(pairs)
            ranked = sorted(zip(docs, scores), key=lambda x: float(x[1]), reverse=True)
            top_docs = [doc for doc, _s in ranked[:k_final]]
            top_scores = [float(s) for _d, s in ranked[:k_final]]
        except Exception:
            top_docs = docs[:k_final]
            top_scores = [None] * len(top_docs)
        return [
            RetrievalResult(
                source=doc.metadata.get("title", "unknown"),
                section=doc.metadata.get("section"),
                chunk_id=doc.metadata.get("chunk_id"),
                text=doc.page_content,
                score=score,
            )
            for doc, score in zip(top_docs, top_scores)
        ]

    def generate_with_context(self, question: str, docs: List[RetrievalResult]) -> str:
        from .models import ChunkHit

        chunks = [
            ChunkHit(
                source_id=i + 1,
                chunk_id=d.chunk_id or "unknown",
                doc_id=d.source,
                title=d.source,
                text=d.text,
                page_start=None,
                page_end=None,
                section=d.section,
                retrieval_score=d.score,
            )
            for i, d in enumerate(docs)
        ]
        return self.generator.answer(question, chunks)

    def direct_answer(self, question: str) -> str:
        return self.generator.direct_answer(question)


# =========================
# LLM Judge (Qwen API via OpenAI-compatible interface)
# =========================
class LLMJudge:
    def __init__(self):
        from langchain_openai import ChatOpenAI

        self.llm = ChatOpenAI(
            model=os.getenv("JUDGE_MODEL", "qwen-plus"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv(
                "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
        )

    def evaluate(
        self, question: str, gold_answer: str, predicted_answer: str, context: str
    ) -> GenerationEval:
        prompt = f"""You are evaluating a RAG QA system.

Score the answer using the following binary labels:
- correctness: 1 if the predicted answer is factually correct relative to the gold answer, else 0
- groundedness: 1 if the predicted answer is supported by the provided context, else 0
- hallucination: 1 if the predicted answer contains unsupported or fabricated information, else 0
- relevance: 1 if the predicted answer addresses the question, else 0

Return JSON only with keys: correctness, groundedness, hallucination, relevance, rationale

Question:
{question}

Gold answer:
{gold_answer}

Predicted answer:
{predicted_answer}

Retrieved context:
{context}""".strip()

        response = self.llm.invoke(prompt).content.strip()
        # strip markdown code fences if present
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
            response = response.strip()

        try:
            parsed = json.loads(response)
        except Exception:
            parsed = {
                "correctness": 0,
                "groundedness": 0,
                "hallucination": 1,
                "relevance": 0,
                "rationale": f"Judge parsing failed. Raw output: {response}",
            }

        return GenerationEval(
            correctness=int(parsed.get("correctness", 0)),
            groundedness=int(parsed.get("groundedness", 0)),
            hallucination=int(parsed.get("hallucination", 1)),
            relevance=int(parsed.get("relevance", 0)),
            rationale=parsed.get("rationale", ""),
        )


# =========================
# Experiment 1
# Direct LLM vs RAG
# =========================
def run_experiment_1(eval_items: List[EvalItem]) -> Dict[str, Any]:
    rag = LocalRAGPipeline()
    judge = LLMJudge()

    detailed_results = []

    for item in tqdm(eval_items, desc="Experiment 1"):
        direct_answer = rag.direct_answer(item.question)

        rag_docs = rag.retrieve_mmr(
            question=item.question, k=TOP_K, fetch_k=TOP_K_RETRIEVAL
        )
        rag_answer = rag.generate_with_context(item.question, rag_docs)
        rag_context = docs_to_context(rag_docs)

        direct_eval = judge.evaluate(
            question=item.question,
            gold_answer=item.gold_answer,
            predicted_answer=direct_answer,
            context="",
        )
        rag_eval = judge.evaluate(
            question=item.question,
            gold_answer=item.gold_answer,
            predicted_answer=rag_answer,
            context=rag_context,
        )

        detailed_results.append(
            {
                "id": item.id,
                "question": item.question,
                "gold_answer": item.gold_answer,
                "evidence": item.evidence,
                "category": item.category,
                "direct_llm": {
                    "answer": direct_answer,
                    **asdict(direct_eval),
                },
                "rag": {
                    "answer": rag_answer,
                    "retrieved_docs": [asdict(doc) for doc in rag_docs],
                    **asdict(rag_eval),
                },
            }
        )

    summary = _summarize_exp1(detailed_results)
    output = {"summary": summary, "details": detailed_results}

    out_path = os.path.join(OUTPUT_DIR, "experiment_1_direct_vs_rag.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Experiment 1 results saved to {out_path}")

    return output


def _summarize_exp1(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    def avg(field: str, system: str) -> float:
        return sum(item[system][field] for item in results) / max(len(results), 1)

    # per-category breakdown
    categories: Dict[str, List] = {}
    for item in results:
        cat = item["category"]
        categories.setdefault(cat, []).append(item)

    per_category = {}
    for cat, items in categories.items():
        per_category[cat] = {
            "count": len(items),
            "direct_llm_correctness": sum(i["direct_llm"]["correctness"] for i in items)
            / len(items),
            "rag_correctness": sum(i["rag"]["correctness"] for i in items) / len(items),
        }

    return {
        "n": len(results),
        "direct_llm": {
            "correctness": avg("correctness", "direct_llm"),
            "groundedness": avg("groundedness", "direct_llm"),
            "hallucination_rate": avg("hallucination", "direct_llm"),
            "relevance": avg("relevance", "direct_llm"),
        },
        "rag": {
            "correctness": avg("correctness", "rag"),
            "groundedness": avg("groundedness", "rag"),
            "hallucination_rate": avg("hallucination", "rag"),
            "relevance": avg("relevance", "rag"),
        },
        "per_category": per_category,
    }


# =========================
# Experiment 2
# Similarity vs MMR vs MMR+Reranker
# =========================
def run_experiment_2(eval_items: List[EvalItem]) -> Dict[str, Any]:
    rag = LocalRAGPipeline()
    judge = LLMJudge()

    detailed_results = []

    for item in tqdm(eval_items, desc="Experiment 2"):
        sim_docs = rag.retrieve_similarity(item.question, k=TOP_K)
        mmr_docs = rag.retrieve_mmr(item.question, k=TOP_K, fetch_k=TOP_K_RETRIEVAL)
        mmr_rerank_docs = rag.retrieve_mmr_rerank(
            item.question, k_final=TOP_K, fetch_k=TOP_K_RETRIEVAL
        )

        sim_answer = rag.generate_with_context(item.question, sim_docs)
        mmr_answer = rag.generate_with_context(item.question, mmr_docs)
        mmr_rerank_answer = rag.generate_with_context(item.question, mmr_rerank_docs)

        sim_eval = judge.evaluate(
            item.question, item.gold_answer, sim_answer, docs_to_context(sim_docs)
        )
        mmr_eval = judge.evaluate(
            item.question, item.gold_answer, mmr_answer, docs_to_context(mmr_docs)
        )
        mmr_rerank_eval = judge.evaluate(
            item.question,
            item.gold_answer,
            mmr_rerank_answer,
            docs_to_context(mmr_rerank_docs),
        )

        detailed_results.append(
            {
                "id": item.id,
                "question": item.question,
                "gold_answer": item.gold_answer,
                "evidence": item.evidence,
                "category": item.category,
                "similarity": {
                    "retrieved_docs": [asdict(doc) for doc in sim_docs],
                    "answer": sim_answer,
                    **asdict(sim_eval),
                },
                "mmr": {
                    "retrieved_docs": [asdict(doc) for doc in mmr_docs],
                    "answer": mmr_answer,
                    **asdict(mmr_eval),
                },
                "mmr_reranker": {
                    "retrieved_docs": [asdict(doc) for doc in mmr_rerank_docs],
                    "answer": mmr_rerank_answer,
                    **asdict(mmr_rerank_eval),
                },
            }
        )

    summary = _summarize_exp2(detailed_results)
    output = {"summary": summary, "details": detailed_results}

    out_path = os.path.join(OUTPUT_DIR, "experiment_2_retrieval_ablation.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Experiment 2 results saved to {out_path}")

    return output


def _summarize_exp2(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    methods = ["similarity", "mmr", "mmr_reranker"]
    summary = {}
    for method in methods:
        vals = [item[method] for item in results]
        n = max(len(vals), 1)
        summary[method] = {
            "correctness": sum(v["correctness"] for v in vals) / n,
            "groundedness": sum(v["groundedness"] for v in vals) / n,
            "hallucination_rate": sum(v["hallucination"] for v in vals) / n,
            "relevance": sum(v["relevance"] for v in vals) / n,
        }
    return summary


# =========================
# Main
# =========================
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", choices=["1", "2", "all"], default="all")
    args = parser.parse_args()

    eval_items = load_eval_data(EVAL_DATA_PATH)
    print(f"Loaded {len(eval_items)} evaluation items from {EVAL_DATA_PATH}")

    if args.exp in ("1", "all"):
        exp1 = run_experiment_1(eval_items)
        print("\n=== Experiment 1 Summary: Direct LLM vs RAG ===")
        print(json.dumps(exp1["summary"], indent=2, ensure_ascii=False))

    if args.exp in ("2", "all"):
        exp2 = run_experiment_2(eval_items)
        print("\n=== Experiment 2 Summary: Similarity vs MMR vs MMR+Reranker ===")
        print(json.dumps(exp2["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
