import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from services.document_text_extractor import extract_text_from_file

pytestmark = pytest.mark.unit

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), '..', 'fixtures')


@pytest.fixture(autouse=True)
def ensure_fixtures_dir():
    os.makedirs(FIXTURES_DIR, exist_ok=True)


class TestTxtExtraction:

    def test_extract_txt_utf8(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello, this is a test contract.", encoding="utf-8")
        result = extract_text_from_file(str(txt_file))
        assert result == "Hello, this is a test contract."

    def test_extract_txt_accents(self, tmp_path):
        txt_file = tmp_path / "accents.txt"
        content = "Cláusula de arrendamiento con señor García y niño"
        txt_file.write_text(content, encoding="utf-8")
        result = extract_text_from_file(str(txt_file))
        assert "Cláusula" in result
        assert "señor" in result
        assert "niño" in result

    def test_extract_txt_multiline(self, tmp_path):
        txt_file = tmp_path / "multi.txt"
        content = "Primera línea\nSegunda línea\nTercera línea"
        txt_file.write_text(content, encoding="utf-8")
        result = extract_text_from_file(str(txt_file))
        assert "Primera línea" in result
        assert "Tercera línea" in result


class TestPdfExtraction:

    def test_extract_pdf_single_page(self):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Contrato de arrendamiento"

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        with patch("services.document_text_extractor.PyPDF2.PdfReader", return_value=mock_reader):
            with patch("builtins.open", MagicMock()):
                with patch("os.path.exists", return_value=True):
                    with patch("os.path.splitext", return_value=("file", ".pdf")):
                        result = extract_text_from_file("test.pdf")
        assert "Contrato de arrendamiento" in result

    def test_extract_pdf_multi_page(self):
        pages = []
        for i in range(3):
            page = MagicMock()
            page.extract_text.return_value = f"Página {i+1} contenido"
            pages.append(page)

        mock_reader = MagicMock()
        mock_reader.pages = pages

        with patch("services.document_text_extractor.PyPDF2.PdfReader", return_value=mock_reader):
            with patch("builtins.open", MagicMock()):
                with patch("os.path.exists", return_value=True):
                    with patch("os.path.splitext", return_value=("file", ".pdf")):
                        result = extract_text_from_file("test.pdf")
        assert "Página 1" in result
        assert "Página 3" in result

    def test_extract_corrupted_pdf(self, tmp_path):
        pdf_file = tmp_path / "corrupted.pdf"
        pdf_file.write_bytes(b"not a real pdf content")
        with pytest.raises(Exception):
            extract_text_from_file(str(pdf_file))


class TestDocxExtraction:

    def test_extract_docx_paragraphs(self):
        mock_para1 = MagicMock()
        mock_para1.text = "Primer párrafo del contrato"
        mock_para2 = MagicMock()
        mock_para2.text = "Segundo párrafo del contrato"

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_doc.tables = []

        with patch("services.document_text_extractor.Document", return_value=mock_doc):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.splitext", return_value=("file", ".docx")):
                    result = extract_text_from_file("test.docx")
        assert "Primer párrafo" in result
        assert "Segundo párrafo" in result

    def test_extract_docx_tables(self):
        mock_cell_para = MagicMock()
        mock_cell_para.text = "Celda importante"
        mock_cell = MagicMock()
        mock_cell.paragraphs = [mock_cell_para]
        mock_row = MagicMock()
        mock_row.cells = [mock_cell]
        mock_table = MagicMock()
        mock_table.rows = [mock_row]

        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_doc.tables = [mock_table]

        with patch("services.document_text_extractor.Document", return_value=mock_doc):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.splitext", return_value=("file", ".docx")):
                    result = extract_text_from_file("test.docx")
        assert "Celda importante" in result


class TestEdgeCases:

    def test_extract_doc_unsupported(self, tmp_path):
        doc_file = tmp_path / "test.doc"
        doc_file.write_bytes(b"fake doc content")
        result = extract_text_from_file(str(doc_file))
        assert result == ""

    def test_extract_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            extract_text_from_file("/nonexistent/path/file.txt")

    def test_extract_unknown_extension_returns_empty(self, tmp_path):
        unknown = tmp_path / "file.xyz"
        unknown.write_bytes(b"some data")
        result = extract_text_from_file(str(unknown))
        assert result == ""

    def test_extract_txt_latin1_fallback(self, tmp_path):
        latin1_file = tmp_path / "latin1.txt"
        latin1_file.write_bytes("Conträt señor".encode("latin-1"))
        result = extract_text_from_file(str(latin1_file))
        assert result != ""

    def test_extract_docx_when_library_missing(self):
        with patch("services.document_text_extractor.Document", None):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.splitext", return_value=("file", ".docx")):
                    result = extract_text_from_file("test.docx")
        assert result == ""
