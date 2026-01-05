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
                "name": exercise_name,
                "nameVi": "",
                "nameEn": "",
                "muscleGroup": "",
                "difficulty": "",
                "calories": "",
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
                elif line.startswith("Tên tiếng Việt:"):
                    exercise_data["nameVi"] = line.replace("Tên tiếng Việt:", "").strip()
                elif line.startswith("Tên tiếng Anh:"):
                    exercise_data["nameEn"] = line.replace("Tên tiếng Anh:", "").strip()
                elif line.startswith("Độ khó:"):
                    exercise_data["difficulty"] = line.replace("Độ khó:", "").strip()
                elif line.startswith("Kcal tiêu thụ:"):
                    exercise_data["calories"] = line.replace("Kcal tiêu thụ:", "").strip()

            exercises.append(exercise_data)

        return exercises[:MAX_EXERCISES_TO_EMBED]


class ExercisesTextBuilder(TopicTextBuilder):
    """Text builder cho exercises."""

    def build_text(self, item: Dict[str, Any]) -> str:
        """Xây dựng text chunk chi tiết từ exercise data."""
        parts = []

        # Tên bài tập (ưu tiên tiếng Việt)
        name_vi = item.get("nameVi", "")
        name_en = item.get("nameEn", "")
        name_display = name_vi if name_vi else (name_en if name_en else item.get("name", ""))
        
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

        return "\n".join(parts)


class ExercisesMetadataBuilder(TopicMetadataBuilder):
    """Metadata builder cho exercises."""

    def build_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Xây dựng metadata từ exercise data."""
        return {
            "name": item.get("nameVi") or item.get("nameEn") or item.get("name"),
            "nameVi": item.get("nameVi", ""),
            "nameEn": item.get("nameEn", ""),
            "muscleGroup": item.get("muscleGroup", ""),
            "difficulty": item.get("difficulty", ""),
            "calories": item.get("calories", ""),
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

