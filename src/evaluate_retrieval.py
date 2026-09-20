"""Reproducible retrieval benchmark for the three UI configurations."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_advanced, rerank_rrf


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
DEFAULT_JSON_OUTPUT = ROOT / "group_project" / "evaluation" / "benchmark_results.json"
DEFAULT_MD_OUTPUT = ROOT / "group_project" / "evaluation" / "BENCHMARK.md"
TOKEN_PATTERN = re.compile(r"[0-9A-Za-zÀ-ỹĐđ]+", re.UNICODE)


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(value) if len(token) > 1}


def _source_rank(results: list[dict[str, Any]], source_id: str) -> int | None:
    needle = source_id.lower()
    for rank, item in enumerate(results, 1):
        metadata = item.get("metadata") or {}
        searchable = " ".join(
            str(value)
            for value in (
                item.get("id"),
                metadata.get("source_id"),
                metadata.get("source"),
                metadata.get("title"),
                metadata.get("url"),
            )
            if value
        ).lower()
        if needle in searchable:
            return rank
    return None


def _context_recall(results: list[dict[str, Any]], expected_context: str) -> float:
    expected = _tokens(expected_context)
    if not expected:
        return 0.0
    retrieved = _tokens(" ".join(str(item.get("content") or "") for item in results))
    return len(expected & retrieved) / len(expected)


def _score_case(
    results: list[dict[str, Any]], case: dict[str, Any], latency_ms: float
) -> dict[str, Any]:
    rank = _source_rank(results, str(case.get("source_id") or ""))
    return {
        "source_hit": rank is not None,
        "source_rank": rank,
        "reciprocal_rank": 0.0 if rank is None else 1.0 / rank,
        "context_token_recall": round(_context_recall(results, case["expected_context"]), 4),
        "latency_ms": round(latency_ms, 2),
        "retrieved_ids": [str(item.get("id") or "") for item in results],
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "source_hit_at_k": round(mean(float(row["source_hit"]) for row in rows), 4),
        "mrr": round(mean(row["reciprocal_rank"] for row in rows), 4),
        "context_token_recall": round(mean(row["context_token_recall"] for row in rows), 4),
        "avg_latency_ms": round(mean(row["latency_ms"] for row in rows), 2),
    }


def evaluate(dataset: list[dict[str, Any]], top_k: int = 5) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    per_strategy: dict[str, list[dict[str, Any]]] = {
        "semantic": [],
        "hybrid_rrf": [],
        "hybrid_reranker": [],
    }

    for index, case in enumerate(dataset, 1):
        query = case["question"]
        candidate_k = max(top_k * 3, 12)

        started = perf_counter()
        dense = semantic_search(query, top_k=candidate_k)
        dense_ms = (perf_counter() - started) * 1000

        started = perf_counter()
        sparse = lexical_search(query, top_k=candidate_k)
        hybrid_candidates = rerank_rrf([dense, sparse], top_k=candidate_k)
        hybrid_ms = dense_ms + (perf_counter() - started) * 1000

        started = perf_counter()
        reranked = rerank_advanced(query, hybrid_candidates, top_k=top_k)
        reranker_ms = hybrid_ms + (perf_counter() - started) * 1000

        outputs = {
            "semantic": _score_case(dense[:top_k], case, dense_ms),
            "hybrid_rrf": _score_case(hybrid_candidates[:top_k], case, hybrid_ms),
            "hybrid_reranker": _score_case(reranked, case, reranker_ms),
        }
        for name, row in outputs.items():
            per_strategy[name].append(row)

        details.append({
            "index": index,
            "question": query,
            "source_id": case.get("source_id"),
            "strategies": outputs,
        })
        print(f"[{index:02d}/{len(dataset):02d}] {query}")

    return {
        "dataset_size": len(dataset),
        "top_k": top_k,
        "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "gemini"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
        "reranker_provider": "jina" if os.getenv("JINA_API_KEY", "").strip() else "gemini-or-safe-fallback",
        "metrics": {name: _aggregate(rows) for name, rows in per_strategy.items()},
        "cases": details,
    }


def _markdown_report(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    labels = {
        "semantic": "Semantic",
        "hybrid_rrf": "Hybrid + RRF",
        "hybrid_reranker": "Hybrid + Neural Reranker",
    }
    lines = [
        "# Local retrieval benchmark",
        "",
        f"Dataset: {result['dataset_size']} grounded questions · top-k: {result['top_k']}",
        f"Embedding: `{result['embedding_model']}` · reranker: `{result['reranker_provider']}`",
        "",
        "| Strategy | Source hit@k | MRR | Context token recall | Avg latency |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for key, label in labels.items():
        row = metrics[key]
        lines.append(
            f"| {label} | {row['source_hit_at_k']:.3f} | {row['mrr']:.3f} | "
            f"{row['context_token_recall']:.3f} | {row['avg_latency_ms']:.1f} ms |"
        )
    lines.extend([
        "",
        "Source hit and MRR use the expected corpus source ID. Context token recall measures how many normalized tokens from the expected context appear in the retrieved top-k chunks.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    result = evaluate(dataset, top_k=args.top_k)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_output.write_text(_markdown_report(result), encoding="utf-8")
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
