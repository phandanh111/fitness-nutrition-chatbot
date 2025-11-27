"""Exercise-related helpers with embedding-based RAG pipeline."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

from rag.exercise_rag import semantic_search, parse_exercises_from_markdown
from services.llm_service import get_ai_response
from constants.rag_prompts import get_rag_system_prompt

MAX_CONTEXT_EXERCISES = int(os.getenv("EXERCISE_CONTEXT_LIMIT", "4"))

COUNT_QUERY_PATTERNS = [
    r"bao nhiêu",
    r"tổng\s*(cộng)?",
    r"có\s*mấy",
    r"tổng số",
    r"bao nhiêu (bài tập|exercise)",
    r"mấy bài tập",
    r"có bao nhiêu",
]


def build_context_from_exercises(exercises: List[Dict]) -> List[str]:
    """Xây dựng context từ danh sách exercises."""
    contexts: List[str] = []
    for exercise in exercises[:MAX_CONTEXT_EXERCISES]:
        name = exercise.get("nameVi") or exercise.get("nameEn") or exercise.get("name", "Bài tập")
        muscle_group = exercise.get("muscleGroup", "")
        difficulty = exercise.get("difficulty", "")
        calories = exercise.get("calories", "")

        lines = [f"Bài tập: {name}"]
        if muscle_group:
            lines.append(f"Nhóm cơ: {muscle_group}")
        if difficulty:
            lines.append(f"Độ khó: {difficulty}")
        if calories:
            lines.append(f"Kcal tiêu thụ: {calories}")
        
        contexts.append("\n".join(lines))
    return contexts


def get_all_exercises() -> List[Dict]:
    """Lấy tất cả exercises từ markdown file (không giới hạn)."""
    try:
        return parse_exercises_from_markdown()
    except Exception as exc:
        print(f"[ExerciseService] Failed to load exercises: {exc}")
        return []


def build_total_counts_context(exercises: List[Dict]) -> str:
    """Xây dựng context về tổng số bài tập."""
    total = len(exercises)
    
    # Đếm theo độ khó
    difficulty_counts = {}
    for ex in exercises:
        diff = ex.get("difficulty", "").strip()
        if diff:
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
    
    lines = [
        f"Tổng số bài tập: {total}",
    ]
    
    if difficulty_counts:
        lines.append("\nPhân loại theo độ khó:")
        for diff, count in sorted(difficulty_counts.items()):
            lines.append(f"- {diff}: {count} bài tập")
    
    lines.append("\nDữ liệu này được tính trực tiếp từ file exercise.md.")
    return "\n".join(lines)


def is_count_query(message: str) -> bool:
    """Kiểm tra xem câu hỏi có phải về số lượng không."""
    lower = message.lower()
    for pattern in COUNT_QUERY_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False


def search_exercises_by_keyword(message: str, exercises: List[Dict]) -> List[Dict]:
    """Tìm bài tập nếu từ khóa xuất hiện trực tiếp trong dữ liệu."""
    query = message.lower()
    if not query.strip():
        return []

    results: List[Dict] = []
    for exercise in exercises:
        fields = [
            exercise.get("nameVi", ""),
            exercise.get("nameEn", ""),
            exercise.get("name", ""),
            exercise.get("muscleGroup", ""),
            exercise.get("difficulty", ""),
        ]
        field_matches = False
        for field in fields:
            field_lower = field.lower()
            if not field_lower:
                continue
            if field_lower in query:
                field_matches = True
                break
            if query in field_lower:
                field_matches = True
                break
        if field_matches:
            results.append(exercise)
    return results


def generate_answer_from_context(question: str, context_blocks: List[str], extra_guidance: Optional[str] = None) -> str:
    """Tạo câu trả lời từ context."""
    if not context_blocks:
        return "Xin lỗi, mình chưa tìm thấy thông tin về bài tập này trong dữ liệu hiện có."

    context_text = "\n\n".join(f"[Đoạn {idx}] {block}" for idx, block in enumerate(context_blocks, 1))
    guidance_lines = [
        "QUAN TRỌNG: BẠN PHẢI TUYỆT ĐỐI CHỈ sử dụng thông tin trong các đoạn ngữ cảnh bên trên.",
        "TUYỆT ĐỐI KHÔNG được tự tạo, bịa đặt, hoặc suy đoán thông tin về bài tập, nhóm cơ, thiết bị, hoặc bất kỳ thông tin nào khác.",
        "Nếu ngữ cảnh không chứa thông tin về bài tập được hỏi, bạn PHẢI nói rõ 'Mình chưa tìm thấy thông tin về bài tập này' và KHÔNG được liệt kê các bài tập không có trong ngữ cảnh.",
        "- Liệt kê tối đa 3 bài tập phù hợp nhất, mỗi bài tập gồm tên, nhóm cơ, mô tả, lợi ích, thiết bị - CHỈ khi thông tin này có trong ngữ cảnh.",
        "- Giữ giọng điệu mềm mại, gần gũi, dùng đại từ 'mình'/'bạn', tránh nhắc lặp lại cùng một câu.",
        "- Nếu người dùng hỏi về nhóm cơ cụ thể, hãy tập trung vào các bài tập cho nhóm cơ đó.",
    ]
    if extra_guidance:
        guidance_lines.append(f"- {extra_guidance}")

    prompt = (
        f"Ngữ cảnh:\n{context_text}\n\n"
        f"Hướng dẫn:\n" + "\n".join(guidance_lines) + "\n\n"
        f"Câu hỏi của khách: {question}\n\n"
        f"LƯU Ý CUỐI CÙNG: Nếu câu hỏi về một bài tập hoặc nhóm cơ cụ thể nhưng trong ngữ cảnh không có thông tin, bạn PHẢI trả lời 'Mình chưa tìm thấy thông tin về [bài tập/nhóm cơ đó]' và KHÔNG được liệt kê các bài tập khác như thể chúng phù hợp."
    )
    messages = [{"role": "user", "content": prompt}]
    return get_ai_response(messages, get_rag_system_prompt("exercises"))


def is_exercise_related_query(message: str) -> bool:
    """Phát hiện câu hỏi về bài tập bằng semantic search."""
    from utils.query_classifier import is_exercise_query
    return is_exercise_query(message)


def generate_exercise_response(message: str) -> str:
    """Tạo câu trả lời cho câu hỏi về bài tập."""
    # Kiểm tra câu hỏi về số lượng
    if is_count_query(message):
        all_exercises = get_all_exercises()
        if not all_exercises:
            return "Xin lỗi, hiện chưa có dữ liệu về các bài tập trong hệ thống."
        
        total_context = build_total_counts_context(all_exercises)
        return generate_answer_from_context(
            message,
            [total_context],
            extra_guidance="Trả lời rõ ràng tổng số bài tập và phân loại theo độ khó nếu có. KHÔNG liệt kê từng bài tập, chỉ trả lời về số lượng.",
        )
    
    # Thử semantic search trước
    semantic_results: List[Dict] = []
    try:
        semantic_results = semantic_search(message, top_k=MAX_CONTEXT_EXERCISES)
    except Exception as exc:
        print(f"[ExerciseService] semantic_search failed: {exc}")

    if semantic_results:
        semantic_exercises = [item.get("raw") for item in semantic_results if item.get("raw")]
        if semantic_exercises:
            contexts = build_context_from_exercises(semantic_exercises)
            return generate_answer_from_context(message, contexts)

    # Nếu không tìm thấy, trả về thông báo
    return "Mình chưa tìm thấy thông tin về bài tập bạn đang hỏi. Bạn có thể mô tả cụ thể hơn về bài tập hoặc nhóm cơ bạn muốn tập không?"

