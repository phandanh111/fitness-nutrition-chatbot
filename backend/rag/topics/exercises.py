"""Topic configuration cho exercises."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List

from rag.base_rag import TopicParser, TopicTextBuilder, TopicMetadataBuilder
from rag.unified_rag import register_topic

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXERCISE_MD_PATH = BASE_DIR / "data" / "exercise.md"
MAX_EXERCISES_TO_EMBED = int(os.getenv("EXERCISE_EMBED_LIMIT", "500"))


def _detect_risk_tags(exercise_data: Dict[str, Any]) -> List[str]:
    """
    Tự động detect risk_tags từ description và name của bài tập.
    
    Rules:
    - Nếu có "core", "bụng", "ab", "abs" trong description/name -> HIGH_PRESSURE_CORE
    - Nếu có "nâng cao", "advanced", "terror" trong name -> có thể có risk cao
    """
    risk_tags = []
    
    name = (exercise_data.get("name", "") or "").lower()
    description = (exercise_data.get("description", "") or "").lower()
    muscle_group = (exercise_data.get("muscleGroup", "") or "").lower()
    
    combined_text = f"{name} {description} {muscle_group}"
    
    # Detect HIGH_PRESSURE_CORE
    core_keywords = ["core", "bụng", "ab", "abs", "abdominal"]
    if any(keyword in combined_text for keyword in core_keywords):
        # Chỉ đánh dấu nếu là bài tập ADVANCED hoặc có từ "pressure", "intense"
        difficulty = (exercise_data.get("difficulty", "") or "").lower()
        if "advanced" in difficulty or "nâng cao" in difficulty:
            risk_tags.append("HIGH_PRESSURE_CORE")
        elif any(word in combined_text for word in ["pressure", "intense", "mạnh", "áp lực"]):
            risk_tags.append("HIGH_PRESSURE_CORE")
    
    return risk_tags


class ExercisesParser(TopicParser):
    """Parser cho exercises từ markdown file."""

    def parse(self, source_path: Path, **kwargs) -> List[Dict[str, Any]]:
        """Parse exercises từ file markdown."""
        if not source_path.exists():
            raise FileNotFoundError(f"File markdown không tồn tại: {source_path}")

        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()

        exercises = []
        # Pattern để match mỗi Bài Tập section: ## Bài Tập X — Name
        pattern = r"## Bài Tập (\d+) — (.+?)\n(.*?)(?=\n## Bài Tập|\Z)"

        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            exercise_num = match.group(1)
            exercise_name = match.group(2).strip()
            exercise_content = match.group(3).strip()

            # Parse các field từ content
            exercise_data = {
                "id": int(exercise_num),
                # name: tên bài tập (hiển thị chính)
                "name": exercise_name,
                "muscleGroup": "",
                "difficulty": "",
                "calories": "",
                "description": "",
                "benefits": "",
                "risk_tags": [],  # Danh sách risk tags
            }

            # Parse từng dòng
            for line in exercise_content.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Remove leading "- "
                if line.startswith("- "):
                    line = line[2:].strip()

                # Parse các field
                if line.startswith("Nhóm cơ:"):
                    exercise_data["muscleGroup"] = line.replace("Nhóm cơ:", "").strip()
                elif line.startswith("Tên bài tập:"):
                    value = line.replace("Tên bài tập:", "").strip()
                    # Ghi đè tên nếu có trong nội dung
                    exercise_data["name"] = value
                elif line.startswith("Độ khó:"):
                    exercise_data["difficulty"] = line.replace("Độ khó:", "").strip()
                elif line.startswith("Kcal tiêu thụ:"):
                    exercise_data["calories"] = line.replace("Kcal tiêu thụ:", "").strip()
                elif line.startswith("Mô tả:"):
                    exercise_data["description"] = line.replace("Mô tả:", "").strip()
                elif line.startswith("Lợi ích:"):
                    exercise_data["benefits"] = line.replace("Lợi ích:", "").strip()
                elif line.startswith("Risk tags:") or line.startswith("Nhãn rủi ro:"):
                    # Parse risk tags (có thể là comma-separated)
                    tags_str = line.replace("Risk tags:", "").replace("Nhãn rủi ro:", "").strip()
                    if tags_str:
                        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                        exercise_data["risk_tags"] = tags

            # Tự động detect risk_tags từ description/name nếu chưa có
            if not exercise_data.get("risk_tags"):
                exercise_data["risk_tags"] = _detect_risk_tags(exercise_data)

            exercises.append(exercise_data)

        return exercises[:MAX_EXERCISES_TO_EMBED]


class ExercisesTextBuilder(TopicTextBuilder):
    """Text builder cho exercises."""

    def build_text(self, item: Dict[str, Any]) -> str:
        """Xây dựng text chunk chi tiết từ exercise data."""
        parts = []

        # Tên bài tập
        name_display = item.get("name", "")
        
        if name_display:
            parts.append(f"Bài tập: {name_display}")

        # Nhóm cơ
        muscle_group = item.get("muscleGroup", "")
        if muscle_group:
            parts.append(f"Nhóm cơ: {muscle_group}")

        # Độ khó
        difficulty = item.get("difficulty", "")
        if difficulty:
            parts.append(f"Độ khó: {difficulty}")

        # Kcal tiêu thụ
        calories = item.get("calories", "")
        if calories:
            parts.append(f"Kcal tiêu thụ: {calories}")

        description = item.get("description", "")
        if description:
            parts.append(f"Mô tả: {description}")

        benefits = item.get("benefits", "")
        if benefits:
            parts.append(f"Lợi ích: {benefits}")

        return "\n".join(parts)


class ExercisesMetadataBuilder(TopicMetadataBuilder):
    """Metadata builder cho exercises."""

    def build_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Xây dựng metadata từ exercise data."""
        # ChromaDB không chấp nhận list trong metadata, cần chuyển thành string
        risk_tags = item.get("risk_tags", [])
        risk_tags_str = ",".join(risk_tags) if isinstance(risk_tags, list) and risk_tags else ""
        
        return {
            "name": item.get("name", ""),
            "muscleGroup": item.get("muscleGroup", ""),
            "difficulty": item.get("difficulty", ""),
            "calories": item.get("calories", ""),
            "description": item.get("description", ""),
            "benefits": item.get("benefits", ""),
            "risk_tags": risk_tags_str,  # Lưu dưới dạng string (comma-separated)
        }


def register_exercises_topic():
    """Đăng ký exercises topic vào unified RAG system."""
    register_topic(
        topic_name="exercises",
        collection_name="exercise_documents",
        parser=ExercisesParser(),
        text_builder=ExercisesTextBuilder(),
        metadata_builder=ExercisesMetadataBuilder(),
        source_path=EXERCISE_MD_PATH,
        max_items=MAX_EXERCISES_TO_EMBED,
    )

