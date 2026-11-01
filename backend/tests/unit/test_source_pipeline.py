import hashlib
import json

import pytest

from rag_tools.normalize_official_sources import normalize_corpus, normalize_html
from rag_tools.source_providers import validate_official_source


def test_boe_and_eur_lex_urls_are_validated():
    boe = {"provider": "boe", "official_id": "BOE-A-2007-20555", "source": {"url": "https://www.boe.es/buscar/act.php?id=BOE-A-2007-20555"}}
    eur = {"provider": "eur_lex", "official_id": "02016R0679-20160504", "source": {"url": "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:02016R0679-20160504"}}
    assert validate_official_source(boe) == []
    assert validate_official_source(eur) == []


@pytest.mark.parametrize("url", ["http://www.boe.es/buscar/act.php?id=BOE-A-1", "https://example.com/?id=BOE-A-1"])
def test_invalid_provider_urls_are_rejected(url):
    document = {"provider": "boe", "official_id": "BOE-A-1", "source": {"url": url}}
    assert validate_official_source(document)


def test_html_normalizer_extracts_articles_and_ignores_forms():
    source = b'''<html><body><h4 class="titulo_num">TITULO I</h4><div class="bloque" id="a1"><h5 class="articulo">Articulo 1. Objeto.</h5><p class="parrafo">Texto legal.</p><form><p>Version antigua</p></form></div></body></html>'''
    result = normalize_html(source)
    assert "## Articulo 1. Objeto." in result
    assert "Texto legal." in result
    assert "Version antigua" not in result


def test_normalization_links_hash_to_source(tmp_path):
    (tmp_path / "sources").mkdir()
    source = tmp_path / "sources" / "law.html"
    source.write_text('<h5 class="articulo">Artículo 1.</h5><p class="parrafo">Texto.</p>', encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = {"documents": [{"law_key": "X", "files": {"source_path": "sources/law.html", "normalized_path": "normalized/law.md"}, "hashes": {"source_sha256": digest}}]}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    normalize_corpus(tmp_path)
    result = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert result["documents"][0]["normalization"]["status"] == "current"
    assert result["documents"][0]["normalization"]["source_sha256"] == digest
