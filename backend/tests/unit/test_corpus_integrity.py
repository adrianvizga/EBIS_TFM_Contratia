import hashlib
import json

import pytest

from rag_tools.corpus_integrity import assert_corpus_integrity, validate_corpus_integrity


def _write_corpus(tmp_path):
    source = tmp_path / "sources" / "law.html"
    normalized = tmp_path / "normalized" / "law.md"
    source.parent.mkdir()
    normalized.parent.mkdir()
    source.write_text("<html>boe.es</html>", encoding="utf-8")
    normalized.write_text("## Artículo 1\nTexto", encoding="utf-8")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "version": "v1_test", "jurisdiction": "ES", "language": "es", "generated_at": "2026-06-20",
        "documents": [{
            "law_key": "TEST", "law_name": "Test", "boe_id": "BOE-A-1",
            "source": {"type": "boe_consolidated", "url": "https://www.boe.es/buscar/act.php?id=BOE-A-1", "retrieved_at": "2026-06-20", "consolidated_at": "2026-06-19", "license": "BOE"},
            "files": {"source_path": "sources/law.html", "normalized_path": "normalized/law.md"},
            "hashes": {"source_sha256": digest(source), "normalized_sha256": digest(normalized)},
        }],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return source


def test_valid_manifest_and_hashes_pass(tmp_path):
    _write_corpus(tmp_path)
    assert validate_corpus_integrity(tmp_path, validate_chunks=False) == []


def test_missing_resource_fails(tmp_path):
    _write_corpus(tmp_path).unlink()
    errors = validate_corpus_integrity(tmp_path, validate_chunks=False)
    assert any("falta el recurso" in error for error in errors)


def test_changed_hash_fails(tmp_path):
    source = _write_corpus(tmp_path)
    source.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="hash inválido"):
        assert_corpus_integrity(tmp_path, validate_chunks=False)


def test_incoherent_dates_and_url_fail(tmp_path):
    _write_corpus(tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["documents"][0]["source"]["retrieved_at"] = "2026-06-21"
    manifest["documents"][0]["source"]["url"] = "http://example.com/law"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = validate_corpus_integrity(tmp_path, validate_chunks=False)
    assert any("posterior" in error for error in errors)
    assert any("URL HTTPS de BOE" in error for error in errors)


def test_missing_manifest_returns_error(tmp_path):
    errors = validate_corpus_integrity(tmp_path, validate_chunks=False)
    assert any("manifiesto" in e.lower() for e in errors)


def test_invalid_json_manifest_returns_error(tmp_path):
    (tmp_path / "manifest.json").write_text("not json", encoding="utf-8")
    errors = validate_corpus_integrity(tmp_path, validate_chunks=False)
    assert any("inválido" in e for e in errors)


def test_missing_required_manifest_field_reported(tmp_path):
    _write_corpus(tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    del manifest["jurisdiction"]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = validate_corpus_integrity(tmp_path, validate_chunks=False)
    assert any("jurisdiction" in e for e in errors)


def test_invalid_generated_at_reported(tmp_path):
    _write_corpus(tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["generated_at"] = "not-a-date"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = validate_corpus_integrity(tmp_path, validate_chunks=False)
    assert any("generated_at" in e for e in errors)


def test_duplicate_law_key_reported(tmp_path):
    _write_corpus(tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    doc = manifest["documents"][0]
    manifest["documents"].append(doc)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = validate_corpus_integrity(tmp_path, validate_chunks=False)
    assert any("duplicada" in e for e in errors)


def test_missing_document_field_reported(tmp_path):
    _write_corpus(tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    del manifest["documents"][0]["law_name"]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = validate_corpus_integrity(tmp_path, validate_chunks=False)
    assert any("law_name" in e for e in errors)


def test_chunk_validation_with_valid_chunks(tmp_path):
    _write_corpus(tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    chunk = {"chunk_id": "c1", "law_key": "TEST", "doc_version": "v1_test", "text": "x"}
    (chunks_dir / "chunks.jsonl").write_text(json.dumps(chunk) + "\n", encoding="utf-8")
    errors = validate_corpus_integrity(tmp_path, validate_chunks=True)
    assert errors == []


def test_chunk_with_missing_chunks_file(tmp_path):
    _write_corpus(tmp_path)
    errors = validate_corpus_integrity(tmp_path, validate_chunks=True)
    assert any("chunks" in e for e in errors)


def test_normalization_outdated_reported(tmp_path):
    _write_corpus(tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["documents"][0]["normalization"] = {"status": "outdated", "source_sha256": "abc"}
    path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = validate_corpus_integrity(tmp_path, validate_chunks=False)
    assert any("normalización desactualizada" in e for e in errors)
