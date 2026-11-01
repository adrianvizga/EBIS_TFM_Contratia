import re
import logging
from typing import List, Dict, Generator, Any
import tiktoken
from .utils import normalize_text, get_safe_hash

logger = logging.getLogger(__name__)


class _RegexTokenEncoding:

    def encode(self, text: str) -> List[str]:
        return re.findall(r'\w+|[^\w\s]', text, flags=re.UNICODE)


class LegalChunker:

    def __init__(self, chunk_max_tokens=900, chunk_min_tokens=250):
        self.chunk_max_tokens = chunk_max_tokens
        self.chunk_min_tokens = chunk_min_tokens
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as error:
            logger.warning("No se pudo cargar tiktoken; usando conteo aproximado: %s", error)
            self.encoding = _RegexTokenEncoding()

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def chunk_file(self, file_path: str, law_key: str, extra_meta: Dict[str, Any] = {}) -> Generator[Dict, None, None]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return

        yield from self._chunk_legal_document(content, law_key, extra_meta)

    def _chunk_legal_document(self, content: str, law_key: str, extra_meta: Dict) -> Generator[Dict, None, None]:
        unit_pattern = re.compile(
            r'^#+\s+(?P<label>(?:Art[ií]culo|Art\.)\s+(?P<number>\d+(?:[.ºª]|\s*(?:bis|ter|qu[aá]ter|[a-z]))?)'
            r'|Disposici[oó]n\s+(?P<disposition>adicional|transitoria|derogatoria|final)\s+[^.\n]+'
            r'|Anexo(?:\s+[IVXLCDM\d]+)?)',
            re.IGNORECASE,
        )
        hierarchy_pattern = re.compile(r'^#+\s+(Libro|T[ií]tulo|Cap[ií]tulo|Secci[oó]n)\b', re.IGNORECASE)
        hierarchy: dict[str, str] = {}
        current_lines: list[str] = []
        current_meta: dict[str, Any] | None = None

        def flush():
            if not current_meta or not current_lines:
                return []
            return list(self._yield_generic_chunks(current_lines, current_meta, law_key, extra_meta))

        for line in content.splitlines():
            stripped = line.strip()
            hierarchy_match = hierarchy_pattern.match(stripped)
            if hierarchy_match:
                if current_lines:
                    yield from flush()
                    current_lines = []
                    current_meta = None
                hierarchy[hierarchy_match.group(1).lower()] = stripped.lstrip("# ").strip()
                continue
            match = unit_pattern.match(stripped)
            if match:
                yield from flush()
                label = match.group("label")
                number = match.group("number") or re.sub(r"\s+", "_", label.lower())
                current_meta = {
                    "number": number.strip().rstrip(".ºª"),
                    "label": label.strip(),
                    "kind": "article" if match.group("number") else "provision",
                    "path": " / ".join(hierarchy.values()) or None,
                }
                current_lines = [line]
            elif current_lines:
                current_lines.append(line)
        yield from flush()

    def _yield_generic_chunks(self, lines: List[str], meta: Dict, law_key: str, extra_meta: Dict):
        ranges = extra_meta.get("include_article_ranges", [])
        if ranges and meta["kind"] != "article":
            return
        if meta["kind"] == "article" and ranges:
            number_match = re.match(r"\d+", meta["number"])
            if not number_match or not any(start <= int(number_match.group()) <= end for start, end in ranges):
                return
        normalized_text = normalize_text("\n".join(lines))
        body = "\n".join(normalized_text.splitlines()[1:]).strip()
        title_marker = (lines[0] if lines else "").casefold()
        if not body or re.fullmatch(r"\(?\s*(?:derogad[oa]|suprimid[oa])\s*\)?\.?", body, re.IGNORECASE) or "(derogado)" in title_marker:
            return
        sub_chunks = self._split_long_text(normalized_text, self.chunk_max_tokens)
        header = lines[0].strip().lstrip("# ").strip()
        title = header[len(meta["label"]):].strip(" .") or None
        citation_prefix = extra_meta.get("citation_prefix") or ({"CC_ES": "CC", "LAU_1994": "LAU"}.get(law_key, law_key))
        safe_number = re.sub(r"[^0-9A-Za-zÀ-ÿ_-]+", "_", meta["number"]).strip("_")
        unit_tag = "ART" if meta["kind"] == "article" else "PROV"
        for index, chunk_text in enumerate(sub_chunks):
            part_label = "full" if len(sub_chunks) == 1 else f"p{index + 1}"
            if index and not re.match(r"^#+\s+", chunk_text):
                chunk_text = f"## {header}\n\n{chunk_text}"
            chunk_hash = get_safe_hash(chunk_text)
            citation = f"{citation_prefix} art. {meta['number']}" if meta["kind"] == "article" else f"{citation_prefix}, {meta['label']}"
            if len(sub_chunks) > 1:
                citation += f" (parte {index + 1})"
            chunk = {
                "chunk_id": f"ES|{law_key}|{unit_tag}|{safe_number}|PART|{part_label}|sha256:{chunk_hash[:12]}",
                "law_key": law_key,
                "law_name": extra_meta.get("law_name") or ({"CC_ES": "Código Civil", "LAU_1994": "Ley de Arrendamientos Urbanos"}.get(law_key, law_key)),
                "article_number": meta["number"],
                "article_title": title,
                "unit_type": meta["kind"],
                "structure_path": meta["path"],
                "citation": citation,
                "text": chunk_text,
                "text_hash": chunk_hash,
                "token_count": self.count_tokens(chunk_text),
            }
            chunk.update(extra_meta)
            yield chunk

    def _split_long_text(self, text: str, max_tokens: int) -> List[str]:
        if self.count_tokens(text) <= max_tokens:
            return [text]
        
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for p in paragraphs:
            p_tokens = self.count_tokens(p)
            
            if current_chunk and (current_tokens + p_tokens > max_tokens):
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [p]
                current_tokens = p_tokens
            else:
                current_chunk.append(p)
                current_tokens += p_tokens
        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks

    def _chunk_lau(self, content: str, law_key: str, extra_meta: Dict) -> Generator[Dict, None, None]:
        pattern = re.compile(r'^##\s+Artículo\s+(\d+)', re.MULTILINE)
        
        matches = list(pattern.finditer(content))
        
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i+1].start() if i + 1 < len(matches) else len(content)
            
            article_header_raw = match.group(0)
            article_num = match.group(1)
            
            article_full_text = content[start:end].strip()
            
            header_line = article_full_text.split('\n')[0]
            title_part = header_line.replace(article_header_raw, '').strip(" .")
            title = title_part if title_part else None

            normalized_text = normalize_text(article_full_text)
            
            standard_header = f"## Artículo {article_num}"
            if title:
                standard_header += f". {title}"
            
            sub_chunks = self._split_long_text(normalized_text, self.chunk_max_tokens)
            
            for idx, chunk_text in enumerate(sub_chunks):
                part_label = "full" if len(sub_chunks) == 1 else f"p{idx+1}"
                
                final_text = chunk_text
                if not re.match(r'^##\s+Artículo', final_text, re.IGNORECASE):
                    final_text = f"{standard_header}\n\n{chunk_text}"
                
                chunk_hash_full = get_safe_hash(final_text)
                chunk_hash_prefix = chunk_hash_full[:12]
                
                chunk_id = f"ES|{law_key}|ART|{article_num}|PART|{part_label}|sha256:{chunk_hash_prefix}"
                
                citation = f"LAU art. {article_num}"
                if len(sub_chunks) > 1:
                    citation += f" (parte {idx+1})"
                
                chunk_data = {
                    "chunk_id": chunk_id,
                    "law_key": law_key,
                    "law_name": "Ley de Arrendamientos Urbanos",
                    "article_number": article_num,
                    "article_title": title,
                    "citation": citation,
                    "text": final_text,
                    "text_hash": chunk_hash_full,
                    "token_count": self.count_tokens(final_text)
                }
                chunk_data.update(extra_meta)
                
                yield chunk_data

    def _chunk_cc(self, content: str, law_key: str, extra_meta: Dict) -> Generator[Dict, None, None]:
        lines = content.split('\n')
        
        current_book = None
        current_title = None
        current_chapter = None
        
        article_buffer = []
        article_meta = {}
        
        for line in lines:
            line_stripped = line.strip()
            
            if re.match(r'^#+\s+Libro', line_stripped, re.IGNORECASE):
                current_book = line_stripped.lstrip('# ').strip()
                continue
            
            if re.match(r'^#+\s+título', line_stripped, re.IGNORECASE):
                current_title = line_stripped.lstrip('# ').strip()
                current_chapter = None
                continue
                
            if re.match(r'^#+\s+capítulo', line_stripped, re.IGNORECASE):
                current_chapter = line_stripped.lstrip('# ').strip()
                continue
            
            art_match = re.match(r'^#+\s+Artículo\s+(\d+)', line_stripped, re.IGNORECASE)
            
            if art_match:
                if article_buffer and 'num' in article_meta:
                    yield from self._yield_cc_chunk(article_buffer, article_meta, law_key, extra_meta)
                
                art_num = art_match.group(1)
                
                path_parts = []
                if current_book: path_parts.append(current_book)
                if current_title: path_parts.append(current_title)
                if current_chapter: path_parts.append(current_chapter)
                structure_path = " / ".join(path_parts) if path_parts else None
                
                article_meta = {
                    "num": art_num,
                    "header": line_stripped,
                    "path": structure_path
                }
                article_buffer = [line]
            
            else:
                if article_buffer:
                    article_buffer.append(line)
        
        if article_buffer and 'num' in article_meta:
            yield from self._yield_cc_chunk(article_buffer, article_meta, law_key, extra_meta)

    def _yield_cc_chunk(self, lines: List[str], meta: Dict, law_key: str, extra_meta: Dict):
        full_text = "\n".join(lines)
        normalized_text = normalize_text(full_text)
        
        header = meta['header']
        title_clean = re.sub(r'^#+\s+Artículo\s+\d+[\.\s]*', '', header, flags=re.IGNORECASE).strip()
        title = title_clean if title_clean else None
        
        sub_chunks = self._split_long_text(normalized_text, self.chunk_max_tokens)
        
        for idx, chunk_text in enumerate(sub_chunks):
            part_label = "full" if len(sub_chunks) == 1 else f"p{idx+1}"
            
            chunk_hash_full = get_safe_hash(chunk_text)
            chunk_hash_prefix = chunk_hash_full[:12]
            
            chunk_id = f"ES|{law_key}|ART|{meta['num']}|PART|{part_label}|sha256:{chunk_hash_prefix}"
            
            citation = f"CC art. {meta['num']}"
            if len(sub_chunks) > 1:
                citation += f" (parte {idx+1})"
            
            chunk_data = {
                "chunk_id": chunk_id,
                "law_key": law_key,
                "law_name": "Código Civil",
                "article_number": meta['num'],
                "article_title": title,
                "structure_path": meta['path'],
                "citation": citation,
                "text": chunk_text,
                "text_hash": chunk_hash_full,
                "token_count": self.count_tokens(chunk_text)
            }
            chunk_data.update(extra_meta)
            
            yield chunk_data
