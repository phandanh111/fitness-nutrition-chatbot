"""Semantic search utilities for The New Gym terms & conditions (embedding + vector DB).

Backward compatibility wrapper cho unified RAG system.
"""

from __future__ import annotations

from typing import Dict, List

# Import unified RAG system
from rag.unified_rag import semantic_search as unified_semantic_search, build_index as unified_build_index, refresh_index as unified_refresh_index


def semantic_search(query: str, top_k: int = 5) -> List[Dict]:
    """Run semantic search using the embedding index (backward compatibility)."""
    try:
        return unified_semantic_search("terms", query, top_k)
    except Exception as e:
        print(f"[TermsRAG] Error in semantic_search: {e}")
        import traceback
        traceback.print_exc()
        return []


def build_terms_index(force_refresh: bool = False) -> None:
    """
    Rebuild the terms embedding index from PDF file (backward compatibility).
    
    Args:
        force_refresh: Nếu True, xóa collection cũ và tạo mới
    """
    unified_build_index("terms", force_refresh=force_refresh)


def refresh_terms_index() -> None:
    """Refresh terms index (backward compatibility)."""
    unified_refresh_index("terms")

