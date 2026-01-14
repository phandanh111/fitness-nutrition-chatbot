"""Helper functions chung cho xử lý exercise data."""

from __future__ import annotations

from typing import Dict, List, Any, Optional


def get_difficulty_normalized(exercise: Dict[str, Any]) -> str:
    """
    Lấy và normalize difficulty từ exercise.
    
    Returns:
        Lowercase difficulty string
    """
    return (exercise.get("difficulty") or "").lower()


def get_muscle_group_normalized(exercise: Dict[str, Any]) -> str:
    """
    Lấy và normalize muscle group từ exercise.
    
    Returns:
        Lowercase muscle group string
    """
    return (exercise.get("muscleGroup") or "").lower()


def get_difficulty_upper(exercise: Dict[str, Any]) -> str:
    """
    Lấy và normalize difficulty thành uppercase từ exercise.
    
    Returns:
        Uppercase difficulty string
    """
    return (exercise.get("difficulty") or "").upper()


def parse_risk_tags(exercise: Dict[str, Any]) -> List[str]:
    """
    Parse risk_tags từ exercise (có thể là list hoặc comma-separated string).
    
    Returns:
        List of risk tags
    """
    risk_tags = exercise.get("risk_tags", [])
    
    if isinstance(risk_tags, str):
        # Parse từ comma-separated string
        return [tag.strip() for tag in risk_tags.split(",") if tag.strip()] if risk_tags else []
    elif isinstance(risk_tags, list):
        return risk_tags
    else:
        return []


def parse_calories(exercise: Dict[str, Any]) -> int:
    """
    Parse calories từ exercise.
    
    Returns:
        Calories as integer, 0 nếu không parse được
    """
    calories_str = exercise.get("calories", "")
    try:
        return int(calories_str) if calories_str else 0
    except (ValueError, TypeError):
        return 0


def is_difficulty_advanced(difficulty: str) -> bool:
    """Kiểm tra xem difficulty có phải ADVANCED không."""
    difficulty_lower = difficulty.lower()
    return any(keyword in difficulty_lower for keyword in ["advanced", "nâng cao"])


def is_difficulty_moderate(difficulty: str) -> bool:
    """Kiểm tra xem difficulty có phải MODERATE không."""
    difficulty_lower = difficulty.lower()
    return any(keyword in difficulty_lower for keyword in ["moderate", "trung bình"])


def is_difficulty_basic(difficulty: str) -> bool:
    """Kiểm tra xem difficulty có phải BASIC không."""
    difficulty_lower = difficulty.lower()
    return any(keyword in difficulty_lower for keyword in ["basic", "cơ bản"])


def is_full_body_exercise(muscle_group: str) -> bool:
    """Kiểm tra xem có phải full body exercise không."""
    muscle_lower = muscle_group.lower()
    return any(keyword in muscle_lower for keyword in ["toàn thân", "full body"])


def is_lower_body_exercise(muscle_group: str) -> bool:
    """Kiểm tra xem có phải lower body exercise không."""
    muscle_lower = muscle_group.lower()
    return any(keyword in muscle_lower for keyword in ["thân dưới", "lower body"])


def has_risk_tag(exercise: Dict[str, Any], risk_tag: str) -> bool:
    """Kiểm tra xem exercise có risk tag cụ thể không."""
    risk_tags = parse_risk_tags(exercise)
    return risk_tag in risk_tags
