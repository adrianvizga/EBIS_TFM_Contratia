from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


ALLOWED_PROVIDERS = {"boe", "eur_lex"}
MAX_SOURCE_BYTES = 30 * 1024 * 1024


@dataclass(frozen=True)
class DownloadedSource:
    payload: bytes
    final_url: str
    content_type: str


def validate_official_source(document: dict) -> list[str]:
    provider = document.get("provider") or ("boe" if document.get("boe_id") else None)
    official_id = document.get("official_id") or document.get("boe_id")
    source = document.get("source", {})
    parsed = urlparse(source.get("url", ""))
    errors: list[str] = []
    if provider not in ALLOWED_PROVIDERS:
        return [f"proveedor no permitido: {provider}"]
    if not official_id:
        errors.append("falta official_id")
    if parsed.scheme != "https":
        errors.append("la fuente no es una URL HTTPS de BOE" if provider == "boe" else "la fuente no es una URL HTTPS de EUR-Lex")
    if provider == "boe":
        if parsed.hostname not in {"boe.es", "www.boe.es"}:
            errors.append("la fuente no pertenece a BOE")
        url_id = parse_qs(parsed.query).get("id", [None])[0]
        if url_id != official_id or not str(official_id).startswith("BOE-A-"):
            errors.append("URL y official_id de BOE no coinciden")
    elif provider == "eur_lex":
        if parsed.hostname not in {"eur-lex.europa.eu", "data.europa.eu"}:
            errors.append("la fuente no pertenece a EUR-Lex")
        compact_url = source.get("url", "").upper().replace("%3A", ":")
        if str(official_id).upper() not in compact_url:
            errors.append("URL y official_id de EUR-Lex no coinciden")
    return errors


def download_official_source(document: dict, *, timeout: int = 60) -> DownloadedSource:
    errors = validate_official_source(document)
    if errors:
        raise ValueError("; ".join(errors))
    request = Request(
        document["source"]["url"],
        headers={"User-Agent": "ContratIA-corpus/2.0 (+legal-source-archiver)"},
    )
    with urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        content_type = response.headers.get_content_type()
        payload = response.read(MAX_SOURCE_BYTES + 1)
    if len(payload) > MAX_SOURCE_BYTES:
        raise RuntimeError("La fuente oficial supera el tamaño máximo permitido")
    if len(payload) < 500:
        raise RuntimeError("Respuesta oficial incompleta")
    final_document = {**document, "source": {**document["source"], "url": final_url}}
    if validate_official_source(final_document):
        raise RuntimeError(f"Redirección fuera del proveedor oficial: {final_url}")
    lower = payload[:10000].lower()
    provider = document.get("provider") or "boe"
    signatures = (b"boe",) if provider == "boe" else (b"eur-lex", b"european union")
    if not any(signature in lower for signature in signatures):
        raise RuntimeError("La respuesta no contiene la firma esperada del proveedor")
    return DownloadedSource(payload=payload, final_url=final_url, content_type=content_type)
