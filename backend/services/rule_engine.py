"""Rule Engine cho hệ thống gợi ý bài tập dựa trên InBody.

Rule Engine chịu trách nhiệm ra quyết định cuối cùng về bài tập nào:
- ĐƯỢC PHÉP
- KHÔNG ĐƯỢC PHÉP
- ƯU TIÊN hay HẠN CHẾ

Rule Engine KHÔNG dùng LLM, chỉ làm việc với dữ liệu đã chuẩn hóa.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from utils.inbody_normalizer import UserSignals
from utils.exercise_helpers import (
    get_difficulty_normalized,
    get_difficulty_upper,
    get_muscle_group_normalized,
    parse_risk_tags,
    parse_calories,
    is_difficulty_advanced,
    is_difficulty_moderate,
    is_difficulty_basic,
    is_full_body_exercise,
    is_lower_body_exercise,
    has_risk_tag,
)
from constants.exercise_constants import (
    RISK_TAG_HIGH_PRESSURE_CORE,
    RISK_TAG_PRESSURE_HIGH,
    CALORIE_MEDIUM_THRESHOLD,
    CALORIE_HIGH_THRESHOLD,
    CALORIE_LOW_THRESHOLD,
    SCORE_DIFFICULTY_MODERATE,
    SCORE_DIFFICULTY_BASIC,
    SCORE_DIFFICULTY_ADVANCED,
    SCORE_CALORIE_HIGH,
    SCORE_CALORIE_LOW,
    SCORE_RISK_HIGH_PRESSURE,
    BONUS_FAT_LOSS_HIGH_CALORIE,
    BONUS_FAT_LOSS_MODERATE,
    BONUS_FAT_LOSS_BASIC,
    BONUS_OVERWEIGHT_MODERATE,
    BONUS_OVERWEIGHT_BASIC,
    BONUS_OVERWEIGHT_ADVANCED,
    BONUS_OVERWEIGHT_FULL_BODY,
    BONUS_OVERWEIGHT_LOWER_BODY,
    BONUS_UNDERWEIGHT_MODERATE,
    BONUS_UNDERWEIGHT_BASIC,
)


class RuleEngine:
    """Rule Engine với 3 layers: Safety Filter, Goal Filter, Scoring & Ranking."""

    def __init__(self):
        """Khởi tạo Rule Engine."""
        pass

    def filter_exercises(
        self,
        exercises: List[Dict[str, Any]],
        user_signals: UserSignals,
    ) -> List[Dict[str, Any]]:
        """
        Lọc và chấm điểm bài tập dựa trên User Signals.
        
        Args:
            exercises: Danh sách bài tập với metadata đầy đủ
            user_signals: User Signals đã chuẩn hóa
            
        Returns:
            Danh sách bài tập ĐƯỢC PHÉP đã được sắp xếp theo score
        """
        if not exercises:
            return []

        # Layer 1: Safety Filter (hard-block)
        safe_exercises = self._safety_filter(exercises, user_signals)
        
        if not safe_exercises:
            return []

        # Layer 2: Goal Filter (điều chỉnh score)
        goal_adjusted = self._goal_filter(safe_exercises, user_signals)

        # Layer 3: Scoring & Ranking
        scored_exercises = self._scoring_and_ranking(goal_adjusted, user_signals)

        # Sắp xếp theo score (thấp hơn = tốt hơn, vì score là distance)
        # Nhưng với Rule Engine score, cao hơn = tốt hơn
        scored_exercises.sort(key=lambda x: x.get("rule_score", 0), reverse=True)

        # Loại bỏ bài tập có score < 0
        final_exercises = [
            ex for ex in scored_exercises 
            if ex.get("rule_score", 0) >= 0
        ]

        return final_exercises

    def _safety_filter(
        self,
        exercises: List[Dict[str, Any]],
        user_signals: UserSignals,
    ) -> List[Dict[str, Any]]:
        """
        Layer 1: Safety Filter - Loại bỏ bài tập có nguy cơ gây hại.
        
        Rules:
        1. Nếu CENTRAL_FAT = true -> Block exercises with risk_tag = HIGH_PRESSURE_CORE
        2. Nếu BODY_FAT_STATUS = HIGH -> Block difficulty = ADVANCED
        3. Nếu BMI_STATUS = OBESE -> Block difficulty = ADVANCED
        """
        safe_exercises = []

        for exercise in exercises:
            should_block = False
            block_reason = None

            # Rule 1: Central Fat Protection
            if user_signals.central_fat:
                if has_risk_tag(exercise, RISK_TAG_HIGH_PRESSURE_CORE):
                    should_block = True
                    block_reason = f"{RISK_TAG_HIGH_PRESSURE_CORE} (central fat detected)"

            # Rule 2: High Body Fat Limitation
            if user_signals.body_fat_status == "HIGH":
                difficulty = get_difficulty_upper(exercise)
                if is_difficulty_advanced(difficulty):
                    should_block = True
                    block_reason = "ADVANCED difficulty (high body fat)"

            # Rule 3: Obese BMI Limitation
            if user_signals.bmi_status == "OBESE":
                difficulty = get_difficulty_upper(exercise)
                if is_difficulty_advanced(difficulty):
                    should_block = True
                    block_reason = "ADVANCED difficulty (obese BMI)"

            if not should_block:
                safe_exercises.append(exercise)
            else:
                print(f"[RuleEngine] Blocked exercise '{exercise.get('name')}': {block_reason}")

        return safe_exercises

    def _goal_filter(
        self,
        exercises: List[Dict[str, Any]],
        user_signals: UserSignals,
    ) -> List[Dict[str, Any]]:
        """
        Layer 2: Goal Filter - Điều chỉnh score theo mục tiêu cơ thể.
        
        Rules:
        1. Nếu BODY_FAT_STATUS = HIGH -> Prefer kcal > 200, MODERATE difficulty
        2. Nếu BMI_STATUS = OVERWEIGHT/OBESE -> Prefer MODERATE/BASIC, full body exercises
        3. Nếu MUSCLE_STATUS = NORMAL -> Không force hypertrophy overload
        """
        goal_adjusted = []

        for exercise in exercises:
            # Copy exercise để không modify original
            adjusted = exercise.copy()
            goal_bonus = 0.0

            difficulty = get_difficulty_normalized(exercise)
            muscle_group = get_muscle_group_normalized(exercise)
            calories = parse_calories(exercise)

            # Rule 1: Fat Loss Bias
            if user_signals.body_fat_status == "HIGH":
                if calories > CALORIE_MEDIUM_THRESHOLD:
                    goal_bonus += BONUS_FAT_LOSS_HIGH_CALORIE
                if is_difficulty_moderate(difficulty):
                    goal_bonus += BONUS_FAT_LOSS_MODERATE
                elif is_difficulty_basic(difficulty):
                    goal_bonus += BONUS_FAT_LOSS_BASIC

            # Rule 2: Overweight/Obesity Preference
            if user_signals.bmi_status in ("OVERWEIGHT", "OBESE"):
                if is_difficulty_moderate(difficulty):
                    goal_bonus += BONUS_OVERWEIGHT_MODERATE
                elif is_difficulty_basic(difficulty):
                    goal_bonus += BONUS_OVERWEIGHT_BASIC
                elif is_difficulty_advanced(difficulty):
                    goal_bonus += BONUS_OVERWEIGHT_ADVANCED

                # Ưu tiên full body exercises
                if is_full_body_exercise(muscle_group):
                    goal_bonus += BONUS_OVERWEIGHT_FULL_BODY
                if is_lower_body_exercise(muscle_group):
                    goal_bonus += BONUS_OVERWEIGHT_LOWER_BODY

            # Rule 3: Underweight Preference
            if user_signals.bmi_status == "UNDERWEIGHT":
                if is_difficulty_moderate(difficulty):
                    goal_bonus += BONUS_UNDERWEIGHT_MODERATE
                elif is_difficulty_basic(difficulty):
                    goal_bonus += BONUS_UNDERWEIGHT_BASIC

            adjusted["goal_bonus"] = goal_bonus
            goal_adjusted.append(adjusted)

        return goal_adjusted

    def _scoring_and_ranking(
        self,
        exercises: List[Dict[str, Any]],
        user_signals: UserSignals,
    ) -> List[Dict[str, Any]]:
        """
        Layer 3: Scoring & Ranking - Tính điểm và sắp xếp bài tập.
        
        Scoring Strategy:
        - Mỗi bài tập bắt đầu với score = 0
        - Cộng/trừ điểm theo rule:
          * difficulty = MODERATE: +3
          * difficulty = BASIC: +2
          * difficulty = ADVANCED: -2
          * kcal > 250: +2
          * kcal < 150: -1
          * risk_tag = PRESSURE_HIGH: -3
        - Cộng goal_bonus từ Layer 2
        """
        scored_exercises = []

        for exercise in exercises:
            score = 0.0

            difficulty = get_difficulty_normalized(exercise)
            calories = parse_calories(exercise)

            # Scoring theo difficulty
            if is_difficulty_moderate(difficulty):
                score += SCORE_DIFFICULTY_MODERATE
            elif is_difficulty_basic(difficulty):
                score += SCORE_DIFFICULTY_BASIC
            elif is_difficulty_advanced(difficulty):
                score += SCORE_DIFFICULTY_ADVANCED

            # Scoring theo calories
            if calories > CALORIE_HIGH_THRESHOLD:
                score += SCORE_CALORIE_HIGH
            elif calories < CALORIE_LOW_THRESHOLD:
                score += SCORE_CALORIE_LOW

            # Scoring theo risk_tags
            if has_risk_tag(exercise, RISK_TAG_HIGH_PRESSURE_CORE) or has_risk_tag(exercise, RISK_TAG_PRESSURE_HIGH):
                score += SCORE_RISK_HIGH_PRESSURE

            # Cộng goal_bonus từ Layer 2
            goal_bonus = exercise.get("goal_bonus", 0.0)
            score += goal_bonus

            # Lưu score vào exercise
            scored = exercise.copy()
            scored["rule_score"] = score
            scored_exercises.append(scored)

        return scored_exercises
