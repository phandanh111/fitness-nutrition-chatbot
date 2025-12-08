"""Query classifier dùng semantic search và vector comparison để phân loại câu hỏi tự động."""

from __future__ import annotations

from typing import Literal

from rag.unified_rag import semantic_search


def classify_query(message: str, top_k: int = 3, max_score: float = 0.80) -> Literal["clubs", "exercises", "general"]:
    """
    Phân loại câu hỏi bằng cách so sánh semantic search scores giữa clubs và exercises.
    Hoàn toàn dựa vào vector embeddings, không dùng keywords.
    
    Args:
        message: Câu hỏi của người dùng
        top_k: Số lượng kết quả top để so sánh
        max_score: Score tối đa để chấp nhận (score > max_score → quá xa, không phù hợp)
                  Score là cosine distance, càng nhỏ càng tương đồng (0 = giống hệt, 1 = khác biệt hoàn toàn)
    
    Returns:
        "clubs" nếu câu hỏi liên quan đến clubs (score < max_score và tốt hơn exercises)
        "exercises" nếu câu hỏi liên quan đến exercises (score < max_score và tốt hơn clubs)
        "general" nếu cả hai scores đều > max_score hoặc không có kết quả
    """
    if not message or not message.strip():
        return "general"
    
    # Thử semantic search cho cả hai collections
    club_results = []
    exercise_results = []
    
    try:
        club_results = semantic_search("clubs", message, top_k=top_k)
    except Exception as e:
        print(f"[QueryClassifier] Club search failed: {e}")
        import traceback
        traceback.print_exc()
        club_results = []  # Đảm bảo là empty list
    
    try:
        exercise_results = semantic_search("exercises", message, top_k=top_k)
    except Exception as e:
        print(f"[QueryClassifier] Exercise search failed: {e}")
        import traceback
        traceback.print_exc()
        exercise_results = []  # Đảm bảo là empty list
    
    # Nếu không có kết quả nào, trả về general
    if not club_results and not exercise_results:
        return "general"
    
    # Tính best score (score nhỏ nhất = tương đồng nhất) và average score cho mỗi collection
    # Score trong ChromaDB là cosine distance: 0 = giống hệt, 1 = khác biệt hoàn toàn
    best_club_score = min((r.get("score") or 1.0 for r in club_results), default=1.0) if club_results else 1.0
    best_exercise_score = min((r.get("score") or 1.0 for r in exercise_results), default=1.0) if exercise_results else 1.0
    
    avg_club_score = sum((r.get("score") or 1.0 for r in club_results)) / len(club_results) if club_results else 1.0
    avg_exercise_score = sum((r.get("score") or 1.0 for r in exercise_results)) / len(exercise_results) if exercise_results else 1.0
    
    # Nếu chỉ có một loại kết quả
    if club_results and not exercise_results:
        # Chỉ phân loại là clubs nếu score tốt (tương đồng cao)
        return "clubs" if best_club_score < max_score else "general"
    
    if exercise_results and not club_results:
        # Chỉ phân loại là exercises nếu score tốt (tương đồng cao)
        return "exercises" if best_exercise_score < max_score else "general"
    
    # Nếu cả hai đều có score quá cao (không tương đồng) → general query
    if best_club_score > max_score and best_exercise_score > max_score:
        return "general"
    
    # Nếu cả hai đều có score tốt, so sánh để chọn cái tốt hơn
    # Score nhỏ hơn = tương đồng hơn = tốt hơn
    score_diff = abs(best_club_score - best_exercise_score)
    
    # Nếu một score tốt hơn đáng kể (chênh lệch > 0.1 hoặc > 15% relative)
    relative_diff = score_diff / max(best_club_score, best_exercise_score, 0.01)
    
    if score_diff > 0.1 or relative_diff > 0.15:
        # Chọn cái có score tốt hơn (nhỏ hơn)
        if best_club_score < best_exercise_score:
            return "clubs" if best_club_score < max_score else "general"
        else:
            return "exercises" if best_exercise_score < max_score else "general"
    
    # Nếu scores gần nhau, so sánh average score
    if avg_club_score < avg_exercise_score:
        return "clubs" if best_club_score < max_score else "general"
    elif avg_exercise_score < avg_club_score:
        return "exercises" if best_exercise_score < max_score else "general"
    else:
        # Nếu vẫn bằng nhau, chọn cái có best score tốt hơn (nhỏ hơn)
        if best_club_score <= best_exercise_score:
            return "clubs" if best_club_score < max_score else "general"
        else:
            return "exercises" if best_exercise_score < max_score else "general"


def is_club_query(message: str) -> bool:
    """Kiểm tra xem câu hỏi có phải về clubs không."""
    try:
        return classify_query(message) == "clubs"
    except Exception as e:
        print(f"[QueryClassifier] Error in is_club_query: {e}")
        import traceback
        traceback.print_exc()
        return False


def is_exercise_query(message: str) -> bool:
    """Kiểm tra xem câu hỏi có phải về exercises không."""
    try:
        return classify_query(message) == "exercises"
    except Exception as e:
        print(f"[QueryClassifier] Error in is_exercise_query: {e}")
        import traceback
        traceback.print_exc()
        return False
