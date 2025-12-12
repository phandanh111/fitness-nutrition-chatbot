"""Semantic search utilities for The New Gym prices (embedding + vector DB).

Backward compatibility wrapper cho unified RAG system.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

# Import unified RAG system
from rag.unified_rag import semantic_search as unified_semantic_search, build_index as unified_build_index, refresh_index as unified_refresh_index

BASE_DIR = Path(__file__).resolve().parent.parent
PRICES_MD_PATH = BASE_DIR / "data" / "prices.md"

# Parser instance để dùng cho parse_prices_from_markdown (lazy import để tránh circular import)
_parser = None

def _get_parser():
    """Lazy load parser để tránh circular import."""
    global _parser
    if _parser is None:
        from rag.topics.prices import PricesParser
        _parser = PricesParser()
    return _parser


def parse_prices_from_markdown(md_path: Path = None) -> List[Dict]:
    """
    Parse prices từ file markdown (public function - backward compatibility).
    
    Args:
        md_path: Đường dẫn đến file markdown. Nếu None, dùng PRICES_MD_PATH mặc định.
    
    Returns:
        List[Dict]: Danh sách prices
    """
    if md_path is None:
        md_path = PRICES_MD_PATH
    parser = _get_parser()
    return parser.parse(md_path)


def semantic_search(query: str, top_k: int = 5) -> List[Dict]:
    """Run semantic search using the embedding index (backward compatibility)."""
    try:
        return unified_semantic_search("prices", query, top_k)
    except Exception as e:
        print(f"[PriceRAG] Error in semantic_search: {e}")
        import traceback
        traceback.print_exc()
        return []


def build_price_index(force_refresh: bool = False) -> None:
    """
    Rebuild the price embedding index from markdown file (backward compatibility).

    Args:
        force_refresh: Nếu True, xóa collection cũ và tạo mới
    """
    unified_build_index("prices", force_refresh=force_refresh)


def refresh_price_index() -> None:
    """Refresh price index (backward compatibility)."""
    unified_refresh_index("prices")
