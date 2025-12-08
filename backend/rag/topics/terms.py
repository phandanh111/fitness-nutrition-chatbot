"""Topic configuration cho điều khoản điều kiện từ PDF file."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List

import PyPDF2

from rag.base_rag import TopicParser, TopicTextBuilder, TopicMetadataBuilder
from rag.unified_rag import register_topic

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TERMS_PDF_PATH = BASE_DIR / "data" / "dieu-khoan-dieu-kien.pdf"
MAX_TERMS_CHUNKS = int(os.getenv("TERMS_EMBED_LIMIT", "1000"))
CHUNK_SIZE = int(os.getenv("TERMS_CHUNK_SIZE", "800"))  # Số ký tự mỗi chunk
CHUNK_OVERLAP = int(os.getenv("TERMS_CHUNK_OVERLAP", "100"))  # Overlap giữa các chunk


class TermsParser(TopicParser):
    """Parser cho điều khoản điều kiện từ PDF file."""

    def parse(self, source_path: Path, **kwargs) -> List[Dict[str, Any]]:
        """Parse PDF và chunk text thành các items."""
        if not source_path.exists():
            raise FileNotFoundError(f"File PDF không tồn tại: {source_path}")

        # Đọc PDF và extract text
        full_text = self._extract_text_from_pdf(source_path)
        
        # Chunk text thành các phần nhỏ
        chunks = self._chunk_text(full_text)
        
        # Tạo items từ chunks
        items = []
        for idx, chunk_text in enumerate(chunks):
            items.append({
                "id": idx + 1,
                "chunk_index": idx + 1,
                "text": chunk_text,
                "total_chunks": len(chunks),
            })
        
        return items[:MAX_TERMS_CHUNKS]

    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text từ PDF file."""
        text_parts = []
        
        try:
            with open(pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            # Clean text: loại bỏ nhiều khoảng trắng, normalize
                            page_text = re.sub(r'\s+', ' ', page_text)
                            page_text = page_text.strip()
                            if page_text:
                                text_parts.append(page_text)
                    except Exception as e:
                        print(f"[TermsParser] Error extracting text from page {page_num}: {e}")
                        continue
                
        except Exception as e:
            raise RuntimeError(f"Lỗi khi đọc PDF: {e}")
        
        return "\n\n".join(text_parts)

    def _chunk_text(self, text: str) -> List[str]:
        """
        Chunk text thành các phần nhỏ với overlap.
        
        Args:
            text: Full text từ PDF
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        # Chia text theo đoạn (paragraph) trước
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # Nếu thêm paragraph này vượt quá CHUNK_SIZE, tạo chunk mới
            if current_length + para_length > CHUNK_SIZE and current_chunk:
                # Tạo chunk từ các paragraphs hiện tại
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(chunk_text)
                
                # Giữ lại một số paragraphs cuối để overlap
                overlap_paras = []
                overlap_length = 0
                for para_back in reversed(current_chunk):
                    if overlap_length + len(para_back) <= CHUNK_OVERLAP:
                        overlap_paras.insert(0, para_back)
                        overlap_length += len(para_back)
                    else:
                        break
                
                current_chunk = overlap_paras
                current_length = overlap_length
            
            current_chunk.append(para)
            current_length += para_length + 2  # +2 cho "\n\n"
        
        # Thêm chunk cuối cùng
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(chunk_text)
        
        return chunks


class TermsTextBuilder(TopicTextBuilder):
    """Text builder cho điều khoản điều kiện."""

    def build_text(self, item: Dict[str, Any]) -> str:
        """Xây dựng text chunk từ item data."""
        text = item.get("text", "")
        chunk_index = item.get("chunk_index", 0)
        total_chunks = item.get("total_chunks", 0)
        
        # Thêm thông tin về vị trí chunk (nếu có nhiều chunks)
        if total_chunks > 1:
            header = f"[Phần {chunk_index}/{total_chunks}]\n\n"
            return header + text
        
        return text


class TermsMetadataBuilder(TopicMetadataBuilder):
    """Metadata builder cho điều khoản điều kiện."""

    def build_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Xây dựng metadata từ item data."""
        return {
            "chunk_index": item.get("chunk_index", 0),
            "total_chunks": item.get("total_chunks", 0),
        }


def register_terms_topic():
    """Đăng ký terms topic vào unified RAG system."""
    register_topic(
        topic_name="terms",
        collection_name="terms_documents",
        parser=TermsParser(),
        text_builder=TermsTextBuilder(),
        metadata_builder=TermsMetadataBuilder(),
        source_path=TERMS_PDF_PATH,
        max_items=MAX_TERMS_CHUNKS,
    )

