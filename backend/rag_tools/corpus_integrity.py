
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from .source_providers import validate_official_source


REQUIRED_DOCUMENT_FIELDS = {"law_key", "law_name", "source", "files", "hashes"}
REQUIRED_SOURCE_FIELDS = {"type", "url", "retrieved_at", "consolidated_at", "license"}
REQUIRED_FILE_FIELDS = {"source_path", "normalized_path"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_path(base_dir: Path, relative_path: str) -> Path:
    candidate = (base_dir / relative_path).resolve()
    if base_dir.resolve() not in candidate.parents:
        raise ValueError(f"Ruta fuera del corpus: {relative_path}")
    return candidate


def validate_corpus_integrity(base_dir: str | Path, *, validate_chunks: bool = True) -> list[str]:
    base = Path(base_dir)
    errors: list[str] = []
    manifest_path = base / "manifest.json"
    if not manifest_path.is_file():
        return [f"Falta el manifiesto: {manifest_path}"]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Manifiesto inválido: {exc}"]

    for field in ("version", "jurisdiction", "language", "generated_at", "documents"):
        if not manifest.get(field):
            errors.append(f"Falta manifest.{field}")
    try:
        generated_at = date.fromisoformat(manifest.get("generated_at", ""))
    except ValueError:
        generated_at = None
        errors.append("manifest.generated_at no es una fecha ISO")

    seen_keys: set[str] = set()
    for index, document in enumerate(manifest.get("documents", [])):
        prefix = f"documents[{index}]"
        missing = REQUIRED_DOCUMENT_FIELDS - document.keys()
        if missing:
            errors.append(f"{prefix}: faltan campos {sorted(missing)}")
            continue
        law_key = document["law_key"]
        if law_key in seen_keys:
            errors.append(f"law_key duplicada: {law_key}")
        seen_keys.add(law_key)

        source = document["source"]
        missing_source = REQUIRED_SOURCE_FIELDS - source.keys()
        if missing_source:
            errors.append(f"{law_key}: faltan metadatos de fuente {sorted(missing_source)}")
        for source_error in validate_official_source(document):
            errors.append(f"{law_key}: {source_error}")
        for field in ("retrieved_at", "consolidated_at"):
            try:
                value = date.fromisoformat(source.get(field, ""))
                if generated_at and value > generated_at:
                    errors.append(f"{law_key}: {field} posterior a generated_at")
            except ValueError:
                errors.append(f"{law_key}: {field} no es una fecha ISO")

        files = document["files"]
        for field in REQUIRED_FILE_FIELDS | ({"notes_path"} if "notes_path" in files else set()):
            relative = files.get(field)
            if not relative:
                errors.append(f"{law_key}: falta files.{field}")
                continue
            try:
                path = _safe_path(base, relative)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if not path.is_file():
                errors.append(f"{law_key}: falta el recurso {relative}")

        hash_map = {"source_sha256": "source_path", "normalized_sha256": "normalized_path"}
        if files.get("notes_path"):
            hash_map["notes_sha256"] = "notes_path"
        for hash_field, file_field in hash_map.items():
            expected = document["hashes"].get(hash_field)
            path = base / files.get(file_field, "")
            if not expected:
                errors.append(f"{law_key}: falta hashes.{hash_field}")
            elif path.is_file() and sha256_file(path) != expected:
                errors.append(f"{law_key}: hash inválido para {files[file_field]}")
        normalization = document.get("normalization")
        if normalization and normalization.get("status") != "current":
            errors.append(f"{law_key}: normalización desactualizada")
        if normalization and normalization.get("source_sha256") != document["hashes"].get("source_sha256"):
            errors.append(f"{law_key}: normalización no corresponde a la fuente")

    if validate_chunks:
        chunks_path = base / "chunks" / "chunks.jsonl"
        if not chunks_path.is_file():
            errors.append("Falta chunks/chunks.jsonl")
        else:
            for line_number, line in enumerate(chunks_path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"Chunk JSON inválido en línea {line_number}")
                    continue
                if chunk.get("doc_version") != manifest.get("version"):
                    errors.append(f"Chunk {line_number}: doc_version incoherente")
                    break
                if chunk.get("law_key") not in seen_keys:
                    errors.append(f"Chunk {line_number}: law_key desconocida")
                    break
    return errors


def assert_corpus_integrity(base_dir: str | Path, *, validate_chunks: bool = True) -> None:
    errors = validate_corpus_integrity(base_dir, validate_chunks=validate_chunks)
    if errors:
        raise ValueError("Corpus inválido:\n- " + "\n- ".join(errors))
