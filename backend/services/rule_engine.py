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
                risk_tags = exercise.get("risk_tags", [])
                # Handle cả list và string (comma-separated)
                if isinstance(risk_tags, str):
                    risk_tags = [tag.strip() for tag in risk_tags.split(",") if tag.strip()] if risk_tags else []
                if "HIGH_PRESSURE_CORE" in risk_tags:
                    should_block = True
                    block_reason = "HIGH_PRESSURE_CORE (central fat detected)"

            # Rule 2: High Body Fat Limitation
            if user_signals.body_fat_status == "HIGH":
                difficulty = (exercise.get("difficulty") or "").upper()
                if "ADVANCED" in difficulty or "NÂNG CAO" in difficulty:
                    should_block = True
                    block_reason = "ADVANCED difficulty (high body fat)"

            # Rule 3: Obese BMI Limitation
            if user_signals.bmi_status == "OBESE":
                difficulty = (exercise.get("difficulty") or "").upper()
                if "ADVANCED" in difficulty or "NÂNG CAO" in difficulty:
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

            difficulty = (exercise.get("difficulty") or "").lower()
            muscle_group = (exercise.get("muscleGroup") or "").lower()
            
            # Parse calories
            calories_str = exercise.get("calories", "")
            try:
                calories = int(calories_str) if calories_str else 0
            except (ValueError, TypeError):
                calories = 0

            # Rule 1: Fat Loss Bias
            if user_signals.body_fat_status == "HIGH":
                if calories > 200:
                    goal_bonus += 2.0
                if "moderate" in difficulty or "trung bình" in difficulty:
                    goal_bonus += 3.0
                elif "basic" in difficulty or "cơ bản" in difficulty:
                    goal_bonus += 2.0

            # Rule 2: Overweight/Obesity Preference
            if user_signals.bmi_status in ("OVERWEIGHT", "OBESE"):
                if "moderate" in difficulty or "trung bình" in difficulty:
                    goal_bonus += 3.0
                elif "basic" in difficulty or "cơ bản" in difficulty:
                    goal_bonus += 2.0
                elif "advanced" in difficulty or "nâng cao" in difficulty:
                    goal_bonus -= 2.0

                # Ưu tiên full body exercises
                if "toàn thân" in muscle_group or "full body" in muscle_group:
                    goal_bonus += 2.0
                if "thân dưới" in muscle_group or "lower body" in muscle_group:
                    goal_bonus += 1.0

            # Rule 3: Underweight Preference
            if user_signals.bmi_status == "UNDERWEIGHT":
                if "moderate" in difficulty or "trung bình" in difficulty:
                    goal_bonus += 2.0
                elif "basic" in difficulty or "cơ bản" in difficulty:
                    goal_bonus += 1.0

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

            difficulty = (exercise.get("difficulty") or "").lower()
            calories_str = exercise.get("calories", "")
            
            try:
                calories = int(calories_str) if calories_str else 0
            except (ValueError, TypeError):
                calories = 0

            # Scoring theo difficulty
            if "moderate" in difficulty or "trung bình" in difficulty:
                score += 3.0
            elif "basic" in difficulty or "cơ bản" in difficulty:
                score += 2.0
            elif "advanced" in difficulty or "nâng cao" in difficulty:
                score -= 2.0

            # Scoring theo calories
            if calories > 250:
                score += 2.0
            elif calories < 150:
                score -= 1.0

            # Scoring theo risk_tags
            risk_tags = exercise.get("risk_tags", [])
            # Handle cả list và string (comma-separated)
            if isinstance(risk_tags, str):
                risk_tags = [tag.strip() for tag in risk_tags.split(",") if tag.strip()] if risk_tags else []
            if "HIGH_PRESSURE_CORE" in risk_tags or "PRESSURE_HIGH" in risk_tags:
                score -= 3.0

            # Cộng goal_bonus từ Layer 2
            goal_bonus = exercise.get("goal_bonus", 0.0)
            score += goal_bonus

            # Lưu score vào exercise
            scored = exercise.copy()
            scored["rule_score"] = score
            scored_exercises.append(scored)

        return scored_exercises
