
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from services.rag_service import build_grounded_answer, retrieve_legal_context
from .build_rag_corpus import get_latest_corpus_path
from .corpus_integrity import assert_corpus_integrity
from .utils import load_config, setup_logging

logger = logging.getLogger(__name__)


def _load_chunks(base_dir: Path) -> dict[tuple[str, str, str], dict]:
    chunks = {}
    for line in (base_dir / "chunks" / "chunks.jsonl").read_text(encoding="utf-8").splitlines():
        chunk = json.loads(line)
        chunks[(chunk["law_key"], str(chunk["article_number"]), chunk["text_hash"])] = chunk
    return chunks


def evaluate(dataset_path: Path, base_dir: Path | None = None) -> dict:
    base_dir = base_dir or Path(get_latest_corpus_path())
    assert_corpus_integrity(base_dir)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if dataset["corpus_version"] != base_dir.name:
        raise ValueError("La evaluación no corresponde a la versión activa del corpus")
    chunks = _load_chunks(base_dir)
    config = dataset["retrieval"]
    details = []
    answerable_hits = []
    recalls = []
    precisions = []
    citation_checks = []
    faithfulness_checks = []
    abstentions = []

    for case in dataset["cases"]:
        context = retrieve_legal_context(
            case["query"], case.get("contract_type", ""), case.get("top_k", config["top_k"]),
            score_threshold=config["score_threshold"], strict=True,
            context=case.get("context"),
        )
        answer = build_grounded_answer(context)
        expected = {(item["law_key"], str(item["article_number"])) for item in case["expected"]}
        retrieved = {(item["law_key"], str(item["article_number"])) for item in context}
        citation_valid = all(
            (item["law_key"], str(item["article_number"]), item.get("text_hash", "")) in chunks
            and chunks[(item["law_key"], str(item["article_number"]), item["text_hash"])]["citation"] == item["citation"]
            for item in context
        )
        faithful = all(f"[{item['citation']}] {item['text'].strip()}" in answer["answer"] for item in context)
        if case["kind"] == "unanswerable":
            abstentions.append(answer["abstained"] and not context)
        else:
            overlap = expected & retrieved
            answerable_hits.append(bool(overlap))
            recalls.append(len(overlap) / len(expected))
            precisions.append(len(overlap) / len(context) if context else 0.0)
        citation_checks.append(citation_valid)
        faithfulness_checks.append(faithful)
        forbidden = {item["law_key"] for item in case.get("forbidden_laws", [])} if case.get("forbidden_laws") and isinstance(case["forbidden_laws"][0], dict) else set(case.get("forbidden_laws", []))
        context_correct = not (forbidden & {item["law_key"] for item in context})
        details.append({"id": case["id"], "retrieved": [item["citation"] for item in context], "abstained": answer["abstained"], "context_correct": context_correct})

    average = lambda values: sum(values) / len(values) if values else 1.0
    metrics = {
        "hit_rate": average(answerable_hits), "recall": average(recalls),
        "relevance_precision": average(precisions), "citation_accuracy": average(citation_checks),
        "faithfulness": average(faithfulness_checks), "abstention_rate": average(abstentions),
        "context_accuracy": average([item["context_correct"] for item in details]),
    }
    failures = {name: {"actual": metrics[name], "required": required} for name, required in dataset["thresholds"].items() if metrics[name] < required}
    return {"dataset": dataset["version"], "metrics": metrics, "thresholds": dataset["thresholds"], "failures": failures, "cases": details, "passed": not failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    setup_logging(); load_config()
    base = Path(__file__).resolve().parents[1] / "legal_corpus" / "es" / args.version if args.version else Path(get_latest_corpus_path())
    dataset = args.dataset or base / "evaluations" / "rag_eval_v1.json"
    try:
        result = evaluate(dataset, base)
    except Exception as exc:
        logger.error("Evaluación RAG fallida: %s", exc, exc_info=True)
        return 2
    report = json.dumps(result, ensure_ascii=False, indent=2)
    print(report)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
