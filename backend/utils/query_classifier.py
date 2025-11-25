"""Query classifier dùng semantic search để phân loại câu hỏi tự động."""

from __future__ import annotations

from typing import Literal, Optional

from rag.club_rag import semantic_search as club_semantic_search
from rag.exercise_rag import semantic_search as exercise_semantic_search


def classify_query(message: str, top_k: int = 3, max_score: float = 0.95) -> Literal["clubs", "exercises", "general"]:
    """
    Phân loại câu hỏi bằng cách so sánh semantic search scores giữa clubs và exercises.
    Không cần keywords, hoàn toàn dựa vào embeddings.
    
    Args:
        message: Câu hỏi của người dùng
        top_k: Số lượng kết quả top để so sánh
        max_score: Score tối đa để chấp nhận (score > max_score → quá xa, không phù hợp)
    
    Returns:
        "clubs" nếu câu hỏi liên quan đến clubs
        "exercises" nếu câu hỏi liên quan đến exercises
        "general" nếu không rõ ràng hoặc không có kết quả
    """
    if not message or not message.strip():
        return "general"
    
    # Thử semantic search cho cả hai collections
    club_results = []
    exercise_results = []
    
    try:
        club_results = club_semantic_search(message, top_k=top_k)
    except Exception as e:
        print(f"[QueryClassifier] Club search failed: {e}")
    
    try:
        exercise_results = exercise_semantic_search(message, top_k=top_k)
    except Exception as e:
        print(f"[QueryClassifier] Exercise search failed: {e}")
    
    # Nếu không có kết quả nào, trả về general
    if not club_results and not exercise_results:
        return "general"
    
    # Tính best score và average score cho mỗi collection
    best_club_score = min((r.get("score") or 1.0 for r in club_results), default=1.0) if club_results else 1.0
    best_exercise_score = min((r.get("score") or 1.0 for r in exercise_results), default=1.0) if exercise_results else 1.0
    
    avg_club_score = sum((r.get("score") or 1.0 for r in club_results)) / len(club_results) if club_results else 1.0
    avg_exercise_score = sum((r.get("score") or 1.0 for r in exercise_results)) / len(exercise_results) if exercise_results else 1.0
    
    # Nếu chỉ có một loại kết quả
    if club_results and not exercise_results:
        return "clubs" if best_club_score < max_score else "general"
    
    if exercise_results and not club_results:
        return "exercises" if best_exercise_score < max_score else "general"
    
    # Nếu cả hai đều có score quá cao → general
    if best_club_score > max_score and best_exercise_score > max_score:
        return "general"
    
    # So sánh relative: nếu một cái tốt hơn đáng kể (chênh lệch > 20% hoặc > 0.15)
    score_diff = abs(best_club_score - best_exercise_score)
    relative_diff = score_diff / max(best_club_score, best_exercise_score, 0.01)
    
    # Nếu chênh lệch đáng kể (> 0.15 hoặc > 20%), chọn cái tốt hơn
    if score_diff > 0.15 or relative_diff > 0.2:
        if best_club_score < best_exercise_score:
            return "clubs"
        else:
            return "exercises"
    
    # Nếu scores gần nhau, so sánh average score
    if avg_club_score < avg_exercise_score:
        return "clubs"
    elif avg_exercise_score < avg_club_score:
        return "exercises"
    else:
        # Nếu vẫn bằng nhau, chọn cái có best score tốt hơn
        return "clubs" if best_club_score <= best_exercise_score else "exercises"


def is_club_query(message: str) -> bool:
    """Kiểm tra xem câu hỏi có phải về clubs không."""
    return classify_query(message) == "clubs"


def is_exercise_query(message: str) -> bool:
    """Kiểm tra xem câu hỏi có phải về exercises không."""
    return classify_query(message) == "exercises"
