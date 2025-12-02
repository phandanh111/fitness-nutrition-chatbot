"""Semantic search utilities for The New Gym exercises (embedding + vector DB).

Backward compatibility wrapper cho unified RAG system.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

# Import unified RAG system
from rag.unified_rag import semantic_search as unified_semantic_search, build_index as unified_build_index, refresh_index as unified_refresh_index

BASE_DIR = Path(__file__).resolve().parent.parent
EXERCISE_MD_PATH = BASE_DIR / "data" / "exercise.md"

# Parser instance để dùng cho parse_exercises_from_markdown (lazy import để tránh circular import)
_parser = None

def _get_parser():
    """Lazy load parser để tránh circular import."""
    global _parser
    if _parser is None:
        from rag.topics.exercises import ExercisesParser
        _parser = ExercisesParser()
    return _parser


def parse_exercises_from_markdown(md_path: Path = None) -> List[Dict]:
    """
    Parse exercises từ file markdown (public function - backward compatibility).
    
    Args:
        md_path: Đường dẫn đến file markdown. Nếu None, dùng EXERCISE_MD_PATH mặc định.
    
    Returns:
        List[Dict]: Danh sách exercises
    """
    if md_path is None:
        md_path = EXERCISE_MD_PATH
    parser = _get_parser()
    return parser.parse(md_path)


def semantic_search(query: str, top_k: int = 5) -> List[Dict]:
    """Run semantic search using the embedding index (backward compatibility)."""
    try:
        return unified_semantic_search("exercises", query, top_k)
    except Exception as e:
        print(f"[ExerciseRAG] Error in semantic_search: {e}")
        import traceback
        traceback.print_exc()
        return []


def build_exercise_index(force_refresh: bool = False) -> None:
    """
    Rebuild the exercise embedding index from markdown file (backward compatibility).

    Args:
        force_refresh: Nếu True, xóa collection cũ và tạo mới
    """
    unified_build_index("exercises", force_refresh=force_refresh)


def refresh_exercise_index() -> None:
    """Refresh exercise index (backward compatibility)."""
    unified_refresh_index("exercises")

