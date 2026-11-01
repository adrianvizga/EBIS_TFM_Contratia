
import os
import logging
from typing import Optional
import PyPDF2
try:
    from docx import Document
except ImportError:
    Document = None

logger = logging.getLogger(__name__)

def extract_text_from_file(file_path: str, mime_type: Optional[str] = None) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_ext == '.pdf':
            return _extract_from_pdf(file_path)
        elif file_ext == '.docx':
            return _extract_from_docx(file_path)
        elif file_ext == '.doc':
            logger.warning("DOC format not supported. Use DOCX, PDF or TXT instead.")
            return ""
        elif file_ext == '.txt':
            return _extract_from_txt(file_path)
        else:
            logger.warning(f"Unsupported file extension for text extraction: {file_ext}")
            return ""
            
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        raise e

def _extract_from_pdf(file_path: str) -> str:
    logger.debug("Extrayendo texto de PDF: %s", file_path)
    text_content = []
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        logger.debug("PDF paginas: %d", len(reader.pages))
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)
    
    return "\n".join(text_content)

def _extract_from_txt(file_path: str) -> str:
    logger.debug("Extrayendo texto de TXT: %s", file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        logger.warning(f"UTF-8 decoding failed for {file_path}, trying latin-1")
        try:
            with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {str(e)}")
            raise


def _extract_from_docx(file_path: str) -> str:
    if Document is None:
        logger.error("python-docx is not installed.")
        return ""
        
    doc = Document(file_path)
    text_content = []
    
    for para in doc.paragraphs:
        if para.text.strip():
            text_content.append(para.text)
            
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if para.text.strip():
                        text_content.append(para.text)

    return "\n".join(text_content)
