"""Semantic search utilities for The New Gym clubs (embedding + vector DB).

Backward compatibility wrapper cho unified RAG system.
"""

from __future__ import annotations

from typing import Dict, List

# Import unified RAG system
from rag.unified_rag import semantic_search as unified_semantic_search, build_index as unified_build_index, refresh_index as unified_refresh_index


def semantic_search(query: str, top_k: int = 5) -> List[Dict]:
    """Run semantic search using the embedding index (backward compatibility)."""
    try:
        return unified_semantic_search("clubs", query, top_k)
    except Exception as e:
        print(f"[ClubRAG] Error in semantic_search: {e}")
        import traceback
        traceback.print_exc()
        return []


def build_club_index(force_refresh: bool = False, source: str = "markdown") -> None:
    """
    Rebuild the club embedding index from markdown file (backward compatibility).
    
    Args:
        force_refresh: Nếu True, xóa collection cũ và tạo mới
        source: Nguồn dữ liệu ("markdown" hoặc "api"). Mặc định: "markdown"
    """
    unified_build_index("clubs", force_refresh=force_refresh, source=source)


def refresh_club_index() -> None:
    """Refresh club index (backward compatibility)."""
    unified_refresh_index("clubs")
