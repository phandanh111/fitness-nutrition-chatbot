"""Query classifier dùng semantic search và vector comparison để phân loại câu hỏi tự động."""

from __future__ import annotations

from typing import Literal

from rag.unified_rag import semantic_search


def classify_query(message: str, top_k: int = 3, max_score: float = 0.80) -> Literal["clubs", "exercises", "terms", "prices", "general"]:
    """
    Phân loại câu hỏi bằng cách so sánh semantic search scores giữa clubs, exercises, terms, và prices.
    Hoàn toàn dựa vào vector embeddings, không dùng keywords.
    
    Args:
        message: Câu hỏi của người dùng
        top_k: Số lượng kết quả top để so sánh
        max_score: Score tối đa để chấp nhận (score > max_score → quá xa, không phù hợp)
                  Score là cosine distance, càng nhỏ càng tương đồng (0 = giống hệt, 1 = khác biệt hoàn toàn)
    
    Returns:
        "clubs" nếu câu hỏi liên quan đến clubs (score < max_score và tốt nhất)
        "exercises" nếu câu hỏi liên quan đến exercises (score < max_score và tốt nhất)
        "terms" nếu câu hỏi liên quan đến điều khoản điều kiện (score < max_score và tốt nhất)
        "prices" nếu câu hỏi liên quan đến giá cả (score < max_score và tốt nhất)
        "general" nếu tất cả scores đều > max_score hoặc không có kết quả
    """
    if not message or not message.strip():
        return "general"
    
    # Thử semantic search cho cả bốn collections
    club_results = []
    exercise_results = []
    terms_results = []
    prices_results = []
    
    try:
        club_results = semantic_search("clubs", message, top_k=top_k)
    except Exception as e:
        print(f"[QueryClassifier] Club search failed: {e}")
        club_results = []
    
    try:
        exercise_results = semantic_search("exercises", message, top_k=top_k)
    except Exception as e:
        print(f"[QueryClassifier] Exercise search failed: {e}")
        exercise_results = []
    
    try:
        terms_results = semantic_search("terms", message, top_k=top_k)
    except Exception as e:
        print(f"[QueryClassifier] Terms search failed: {e}")
        terms_results = []
    
    try:
        prices_results = semantic_search("prices", message, top_k=top_k)
    except Exception as e:
        print(f"[QueryClassifier] Prices search failed: {e}")
        prices_results = []
    
    # Nếu không có kết quả nào, trả về general
    if not club_results and not exercise_results and not terms_results and not prices_results:
        return "general"
    
    # Tính best score (score nhỏ nhất = tương đồng nhất) cho mỗi collection
    best_club_score = min((r.get("score") or 1.0 for r in club_results), default=1.0) if club_results else 1.0
    best_exercise_score = min((r.get("score") or 1.0 for r in exercise_results), default=1.0) if exercise_results else 1.0
    best_terms_score = min((r.get("score") or 1.0 for r in terms_results), default=1.0) if terms_results else 1.0
    best_prices_score = min((r.get("score") or 1.0 for r in prices_results), default=1.0) if prices_results else 1.0
    
    # Tạo dict để dễ so sánh
    scores = {
        "clubs": best_club_score,
        "exercises": best_exercise_score,
        "terms": best_terms_score,
        "prices": best_prices_score,
    }
    
    # Lọc các scores tốt (score < max_score)
    good_scores = {k: v for k, v in scores.items() if v < max_score}
    
    # Nếu không có score nào tốt, trả về general
    if not good_scores:
        return "general"
    
    # Chọn topic có score tốt nhất (nhỏ nhất)
    best_topic = min(good_scores.items(), key=lambda x: x[1])[0]
    return best_topic


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


def is_terms_query(message: str) -> bool:
    """Kiểm tra xem câu hỏi có phải về điều khoản điều kiện không."""
    try:
        return classify_query(message) == "terms"
    except Exception as e:
        print(f"[QueryClassifier] Error in is_terms_query: {e}")
        import traceback
        traceback.print_exc()
        return False


def is_price_query(message: str) -> bool:
    """Kiểm tra xem câu hỏi có phải về giá cả không."""
    try:
        return classify_query(message) == "prices"
    except Exception as e:
        print(f"[QueryClassifier] Error in is_price_query: {e}")
        import traceback
        traceback.print_exc()
        return False
