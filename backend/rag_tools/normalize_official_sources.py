from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

from .corpus_integrity import sha256_file


HEADING_CLASSES = {"libro", "titulo_num", "titulo_tit", "capitulo_num", "capitulo_tit", "seccion", "articulo", "title-article-norm"}
TEXT_CLASSES = {"parrafo", "parrafo_2", "parrafo_3", "parrafo_4", "apartado", "texto", "stitle-article-norm", "norm"}


class LegalHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag in {"script", "style", "form", "nav", "footer"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        classes = set((attrs_map.get("class") or "").split())
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} or classes & HEADING_CLASSES:
            self._capture = "heading"
            self._buffer = []
        elif tag in {"p", "li", "div"} and classes & TEXT_CLASSES:
            if not self._capture:
                self._capture = "text"
                self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "form", "nav", "footer"} and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if self._ignored_depth or not self._capture:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "div"}:
            value = re.sub(r"\s+", " ", html.unescape("".join(self._buffer))).strip()
            if value and not value.startswith("[Bloque ") and "Seleccionar redacción" not in value:
                prefix = "## " if re.match(r"^Art[ií]culo\s+", value, re.I) else ("# " if self._capture == "heading" else "")
                self.lines.append(prefix + value)
            self._capture = None
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture and not self._ignored_depth:
            self._buffer.append(data)


def normalize_html(payload: bytes) -> str:
    decoded = payload.decode("utf-8-sig", errors="strict")
    parser = LegalHTMLParser()
    parser.feed(decoded)
    lines = parser.lines
    first_article = next((index for index, line in enumerate(lines) if re.match(r"^## Art[ií]culo\s+", line, re.I)), 0)
    useful = lines[max(0, first_article - 8):]
    text = "\n\n".join(useful)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    if len(re.findall(r"^## Art[ií]culo\s+", text, re.MULTILINE | re.IGNORECASE)) == 0:
        raise ValueError("La normalización no encontró artículos")
    return text


def infer_consolidated_date(payload: bytes, document: dict) -> str:
    decoded = payload.decode("utf-8-sig", errors="replace")
    if document.get("provider") == "eur_lex":
        match = re.search(r"\b(\d{2})\.(\d{2})\.(\d{4})\b", decoded[:5000])
    else:
        match = re.search(r"[ÚUuú]ltima actualizaci[oó]n[^0-9]*(\d{2})/(\d{2})/(\d{4})", html.unescape(decoded), re.IGNORECASE)
    if not match:
        return document.get("source", {}).get("consolidated_at", "")
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def normalize_corpus(base_dir: Path) -> None:
    manifest_path = base_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for document in manifest["documents"]:
        source_path = base_dir / document["files"]["source_path"]
        normalized_path = base_dir / document["files"]["normalized_path"]
        normalized_path.parent.mkdir(parents=True, exist_ok=True)
        payload = source_path.read_bytes()
        normalized_path.write_text(normalize_html(payload), encoding="utf-8", newline="\n")
        if "source" in document:
            document["source"]["consolidated_at"] = infer_consolidated_date(payload, document)
        hashes = document.setdefault("hashes", {})
        hashes["source_sha256"] = sha256_file(source_path)
        hashes["normalized_sha256"] = sha256_file(normalized_path)
        document["normalization"] = {
            "status": "current",
            "source_sha256": hashes["source_sha256"],
            "format": "structured_markdown_v2",
        }
        notes = document["files"].get("notes_path")
        if notes and (base_dir / notes).is_file():
            hashes["notes_sha256"] = sha256_file(base_dir / notes)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_dir", type=Path)
    args = parser.parse_args()
    normalize_corpus(args.base_dir)
