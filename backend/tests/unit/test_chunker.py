import os
import re
import pytest
import tempfile
from rag_tools.chunker import LegalChunker

pytestmark = pytest.mark.unit


@pytest.fixture
def chunker():
    return LegalChunker(chunk_max_tokens=900, chunk_min_tokens=250)


@pytest.fixture
def small_chunker():
    return LegalChunker(chunk_max_tokens=100, chunk_min_tokens=10)


class TestLAUChunking:

    def test_lau_article_split(self, chunker, tmp_path):
        content = """# LAU 29/1994

## Artículo 1. Ámbito de aplicación

La presente ley establece el régimen jurídico aplicable a los arrendamientos
de fincas urbanas que se destinen a vivienda o a usos distintos del de vivienda.

## Artículo 2. Arrendamiento de vivienda

Se considera arrendamiento de vivienda aquel arrendamiento que recae sobre una
edificación habitable cuyo destino primordial sea satisfacer la necesidad
permanente de vivienda del arrendatario.

## Artículo 3. Arrendamiento para uso distinto

Se considera arrendamiento para uso distinto del de vivienda aquel arrendamiento
que, recayendo sobre una edificación, tenga como destino primordial uno distinto
del establecido en el artículo anterior.
"""
        f = tmp_path / "lau.md"
        f.write_text(content, encoding="utf-8")

        chunks = list(chunker.chunk_file(str(f), "LAU_1994"))
        assert len(chunks) >= 3

    def test_lau_chunk_has_metadata(self, chunker, tmp_path):
        content = """## Artículo 1. Ámbito de aplicación

La presente ley establece el régimen jurídico."""
        f = tmp_path / "lau.md"
        f.write_text(content, encoding="utf-8")

        chunks = list(chunker.chunk_file(str(f), "LAU_1994"))
        assert len(chunks) >= 1
        c = chunks[0]
        assert "chunk_id" in c
        assert "law_key" in c
        assert c["law_key"] == "LAU_1994"
        assert "article_number" in c
        assert "text" in c


class TestCCChunking:

    def test_cc_hierarchy(self, chunker, tmp_path):
        content = """# Código Civil

## Libro IV. De las obligaciones y contratos

### Título VI. Del contrato de arrendamiento

#### Capítulo I. Disposiciones generales

## Artículo 1542. Definición

El arrendamiento puede ser de cosas, o de obras o servicios.

## Artículo 1543. Arrendamiento de cosas

En el arrendamiento de cosas, una de las partes se obliga a dar a la otra
el goce o uso de una cosa por tiempo determinado y precio cierto.
"""
        f = tmp_path / "cc.md"
        f.write_text(content, encoding="utf-8")

        chunks = list(chunker.chunk_file(str(f), "CC_ES"))
        assert len(chunks) >= 2
        for c in chunks:
            assert c.get("structure_path") is not None


class TestTokenLimits:

    def test_max_tokens_respected(self, chunker, tmp_path):
        paragraphs = [f"Párrafo {i}: " + "palabra " * 50 for i in range(20)]
        content = "## Artículo 1. Artículo largo\n\n" + "\n\n".join(paragraphs)

        f = tmp_path / "lau_long.md"
        f.write_text(content, encoding="utf-8")

        chunks = list(chunker.chunk_file(str(f), "LAU_1994"))
        for c in chunks:
            assert c["token_count"] <= 900 + 50  # small tolerance for header added

    def test_long_article_sub_chunks(self, small_chunker, tmp_path):
        content = "## Artículo 1. Artículo muy largo\n\n"
        content += "\n\n".join([f"Párrafo {i}: " + "contenido legal extenso " * 20 for i in range(10)])

        f = tmp_path / "lau_sub.md"
        f.write_text(content, encoding="utf-8")

        chunks = list(small_chunker.chunk_file(str(f), "LAU_1994"))
        assert len(chunks) > 1


class TestChunkIdFormat:

    def test_chunk_id_deterministic(self, chunker, tmp_path):
        content = "## Artículo 1. Test\n\nContenido del artículo de prueba."
        f = tmp_path / "lau.md"
        f.write_text(content, encoding="utf-8")

        chunks1 = list(chunker.chunk_file(str(f), "LAU_1994"))
        chunks2 = list(chunker.chunk_file(str(f), "LAU_1994"))
        assert chunks1[0]["chunk_id"] == chunks2[0]["chunk_id"]

    def test_chunk_id_format(self, chunker, tmp_path):
        content = "## Artículo 42. Obligaciones\n\nEl arrendatario deberá cumplir."
        f = tmp_path / "lau.md"
        f.write_text(content, encoding="utf-8")

        chunks = list(chunker.chunk_file(str(f), "LAU_1994"))
        cid = chunks[0]["chunk_id"]
        assert cid.startswith("ES|LAU_1994|ART|42|PART|")
        assert "sha256:" in cid


class TestChunkerEdgeCases:

    def test_empty_input(self, chunker, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        chunks = list(chunker.chunk_file(str(f), "LAU_1994"))
        assert chunks == []

    def test_nonexistent_file(self, chunker):
        chunks = list(chunker.chunk_file("/nonexistent/file.md", "LAU_1994"))
        assert chunks == []

    def test_count_tokens(self, chunker):
        count = chunker.count_tokens("Hola mundo, este es un texto de prueba")
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_empty(self, chunker):
        count = chunker.count_tokens("")
        assert count == 0
