"""Query classifier dùng semantic search và vector comparison để phân loại câu hỏi tự động."""

from __future__ import annotations

from typing import Literal

from rag.unified_rag import semantic_search


def classify_query(message: str, top_k: int = 3, max_score: float = 0.80) -> Literal["exercises", "general"]:
    """
    Phân loại câu hỏi giữa exercises và general.
    Hoàn toàn dựa vào vector embeddings, không dùng keywords.
    """
    if not message or not message.strip():
        return "general"

    exercise_results = []

    try:
        exercise_results = semantic_search("exercises", message, top_k=top_k)
    except Exception as e:
        print(f"[QueryClassifier] Exercise search failed: {e}")
        exercise_results = []

    if not exercise_results:
        return "general"

    best_exercise_score = min((r.get("score") or 1.0 for r in exercise_results), default=1.0)

    if best_exercise_score < max_score:
        return "exercises"

    return "general"


def is_exercise_query(message: str) -> bool:
    """Kiểm tra xem câu hỏi có phải về exercises không."""
    try:
        return classify_query(message) == "exercises"
    except Exception as e:
        print(f"[QueryClassifier] Error in is_exercise_query: {e}")
        import traceback
        traceback.print_exc()
        return False
