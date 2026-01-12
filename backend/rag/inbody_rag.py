"""Semantic search utilities for The New Gym InBody (embedding + vector DB).

Backward compatibility wrapper cho unified RAG system.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

# Import unified RAG system
from rag.unified_rag import semantic_search as unified_semantic_search, build_index as unified_build_index, refresh_index as unified_refresh_index

BASE_DIR = Path(__file__).resolve().parent.parent
INBODY_MD_PATH = BASE_DIR / "data" / "inbody.md"

# Parser instance để dùng cho parse_inbody_from_markdown (lazy import để tránh circular import)
_parser = None

def _get_parser():
    """Lazy load parser để tránh circular import."""
    global _parser
    if _parser is None:
        from rag.topics.inbody import InBodyParser
        _parser = InBodyParser()
    return _parser


def parse_inbody_from_markdown(md_path: Path = None) -> Dict:
    """
    Parse InBody data từ file markdown (chứa JSON).
    
    Args:
        md_path: Đường dẫn đến file markdown. Nếu None, dùng INBODY_MD_PATH mặc định.
    
    Returns:
        Dict: InBody data (hoặc None nếu không parse được)
    """
    if md_path is None:
        md_path = INBODY_MD_PATH
    
    parser = _get_parser()
    results = parser.parse(md_path)
    if results:
        return results[0]  # InBody chỉ có 1 item
    return None


def semantic_search(query: str, top_k: int = 5) -> List[Dict]:
    """Run semantic search using the embedding index (backward compatibility)."""
    try:
        return unified_semantic_search("inbody", query, top_k)
    except Exception as e:
        print(f"[InBodyRAG] Error in semantic_search: {e}")
        import traceback
        traceback.print_exc()
        return []


def build_inbody_index(force_refresh: bool = False) -> None:
    """
    Rebuild the InBody embedding index from markdown file (backward compatibility).

    Args:
        force_refresh: Nếu True, xóa collection cũ và tạo mới
    """
    unified_build_index("inbody", force_refresh=force_refresh)


def refresh_inbody_index() -> None:
    """Refresh InBody index (backward compatibility)."""
    unified_refresh_index("inbody")
