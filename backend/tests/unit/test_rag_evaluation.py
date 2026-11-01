import json

from rag_tools.evaluate_rag import evaluate


def test_evaluation_metrics_and_thresholds(monkeypatch, tmp_path):
    corpus = tmp_path / "v1_test"
    (corpus / "chunks").mkdir(parents=True)
    chunk = {"law_key": "LAW", "article_number": "1", "text_hash": "hash", "citation": "LAW art. 1", "text": "Texto fiel"}
    (corpus / "chunks" / "chunks.jsonl").write_text(json.dumps(chunk) + "\n", encoding="utf-8")
    dataset = {
        "version": "eval", "corpus_version": "v1_test", "retrieval": {"top_k": 1, "score_threshold": 0.4},
        "thresholds": {"hit_rate": 1, "recall": 1, "relevance_precision": 1, "citation_accuracy": 1, "faithfulness": 1, "abstention_rate": 1},
        "cases": [
            {"id": "yes", "kind": "answerable", "query": "q", "expected": [{"law_key": "LAW", "article_number": "1"}]},
            {"id": "no", "kind": "unanswerable", "query": "x", "expected": []},
        ],
    }
    dataset_path = tmp_path / "eval.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    monkeypatch.setattr("rag_tools.evaluate_rag.assert_corpus_integrity", lambda *_: None)
    monkeypatch.setattr("rag_tools.evaluate_rag.retrieve_legal_context", lambda query, *_args, **_kwargs: ([dict(chunk)] if query == "q" else []))
    result = evaluate(dataset_path, corpus)
    assert result["passed"] is True
    assert all(value == 1 for value in result["metrics"].values())


def test_evaluation_fails_below_threshold(monkeypatch, tmp_path):
    corpus = tmp_path / "v1_test"
    (corpus / "chunks").mkdir(parents=True)
    (corpus / "chunks" / "chunks.jsonl").write_text("", encoding="utf-8")
    dataset = {"version": "eval", "corpus_version": "v1_test", "retrieval": {"top_k": 1, "score_threshold": 0.4}, "thresholds": {"hit_rate": 1}, "cases": [{"id": "miss", "kind": "answerable", "query": "q", "expected": [{"law_key": "LAW", "article_number": "1"}]}]}
    path = tmp_path / "eval.json"; path.write_text(json.dumps(dataset), encoding="utf-8")
    monkeypatch.setattr("rag_tools.evaluate_rag.assert_corpus_integrity", lambda *_: None)
    monkeypatch.setattr("rag_tools.evaluate_rag.retrieve_legal_context", lambda *_args, **_kwargs: [])
    result = evaluate(path, corpus)
    assert result["passed"] is False
    assert result["failures"]["hit_rate"]["actual"] == 0
