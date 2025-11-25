"""Async Query Classifier using semantic similarity scores."""

from __future__ import annotations
import logging
import math
from typing import Literal, List, Dict

# Semantically compatible async methods
from rag.club_rag import async_semantic_search as club_search
from rag.exercise_rag import async_semantic_search as exercise_search

logger = logging.getLogger("QueryClassifier")
logger.setLevel(logging.DEBUG)  # DEBUG logging


# ---------------------------
#   Utility: Score Extractor
# ---------------------------
def extract_scores(results: List[Dict]) -> tuple[float, float]:
    """Return (best_score, avg_score) given list of results."""
    if not results:
        return 1.0, 1.0

    scores = [r.get("score", 1.0) for r in results]
    best = min(scores)
    avg = sum(scores) / len(scores)

    return best, avg


# ---------------------------
#   Utility: Dynamic Threshold
# ---------------------------
def dynamic_threshold(message: str, base: float = 0.90) -> float:
    """
    Tự động tối ưu threshold:
    - Query ngắn/không rõ: threshold thấp → strict hơn.
    - Query dài/rõ ràng: threshold cao → tolerant hơn.
    """

    length = len(message.split())
    if length <= 3:
        return base - 0.10      # Query rất ngắn → khó phân loại → cần strict hơn
    if length <= 7:
        return base - 0.05      # Query ngắn vừa
    return base                 # Query dài → nhiều thông tin → threshold bình thường


# ---------------------------
#    Main Classifier Async
# ---------------------------
async def classify_query(
    message: str,
    top_k: int = 3,
) -> Literal["clubs", "exercises", "general"]:

    if not message or not message.strip():
        return "general"

    # Threshold tùy duyệt theo query
    max_score = dynamic_threshold(message)
    logger.debug(f"[Classifier] Using dynamic threshold = {max_score:.3f}")

    # Run 2 searches concurrently (tăng hiệu suất)
    import asyncio
    club_task = asyncio.create_task(club_search(message, top_k=top_k))
    exercise_task = asyncio.create_task(exercise_search(message, top_k=top_k))

    club_results, exercise_results = await asyncio.gather(
        club_task, exercise_task, return_exceptions=False
    )

    logger.debug(f"[Search] club_results={club_results}")
    logger.debug(f"[Search] exercise_results={exercise_results}")

    # If both empty -> general
    if not club_results and not exercise_results:
        logger.debug("[Classifier] Both results empty → general")
        return "general"

    # Extract scores
    club_best, club_avg = extract_scores(club_results)
    ex_best, ex_avg = extract_scores(exercise_results)

    logger.debug(
        f"[Scores] Club(best={club_best:.3f}, avg={club_avg:.3f}) | "
        f"Exercise(best={ex_best:.3f}, avg={ex_avg:.3f})"
    )

    # Both irrelevant (above threshold)
    if club_best > max_score and ex_best > max_score:
        logger.debug("[Classifier] Both above threshold → general")
        return "general"

    # If one empty
    if club_results and not exercise_results:
        return "clubs" if club_best < max_score else "general"

    if exercise_results and not club_results:
        return "exercises" if ex_best < max_score else "general"

    # Comparative score logic
    diff = abs(club_best - ex_best)
    rel = diff / max(min(club_best, ex_best), 0.01)

    logger.debug(f"[Compare] diff={diff:.3f}, relative={rel:.3f}")

    # Strong difference
    if diff > 0.12 or rel > 0.18:
        result = "clubs" if club_best < ex_best else "exercises"
        logger.debug(f"[Classifier] Strong difference → {result}")
        return result

    # Otherwise compare averages
    if club_avg < ex_avg:
        return "clubs"
    if ex_avg < club_avg:
        return "exercises"

    # Final fallback
    return "clubs" if club_best <= ex_best else "exercises"


# ------------------------------------
#   Helper boolean check functions
# ------------------------------------
async def is_club_query(message: str) -> bool:
    return (await classify_query(message)) == "clubs"

async def is_exercise_query(message: str) -> bool:
    return (await classify_query(message)) == "exercises"
