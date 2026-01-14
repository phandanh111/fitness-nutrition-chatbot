"""Exercise-related helpers with embedding-based RAG pipeline."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Any

from rag.exercise_rag import semantic_search, parse_exercises_from_markdown
from services.llm_service import get_ai_response
from constants.rag_prompts import get_rag_system_prompt
from services.conversation_service import get_inbody_data
from services.rule_engine import RuleEngine
from utils.inbody_normalizer import normalize_inbody_data

MAX_CONTEXT_EXERCISES = int(os.getenv("EXERCISE_CONTEXT_LIMIT", "10"))

# Guidance lines chung cho tất cả responses
BASE_GUIDANCE_LINES = [
    "QUAN TRỌNG: BẠN PHẢI TUYỆT ĐỐI CHỈ sử dụng thông tin trong các đoạn ngữ cảnh bên trên.",
    "TUYỆT ĐỐI KHÔNG được tự tạo, bịa đặt, hoặc suy đoán thông tin về bài tập, nhóm cơ, thiết bị, hoặc bất kỳ thông tin nào khác.",
    "Nếu ngữ cảnh không chứa thông tin về bài tập được hỏi, bạn PHẢI nói rõ 'Mình chưa tìm thấy thông tin về bài tập này' và KHÔNG được liệt kê các bài tập không có trong ngữ cảnh.",
    "Câu trả lời chỉ 1 JSON OBJECT duy nhất với các key là ngày trong tuần và value là danh sách các bài tập tương ứng bằng tiếng việt, không cần thêm bất kỳ note và text nào khác trước và sau dấu đóng mở của object.",
]


def is_workout_plan_query(message: str) -> bool:
    """Kiểm tra xem query có phải về lộ trình/chương trình tập không."""
    return any(keyword in message.lower() for keyword in [
        "lộ trình", "chương trình", "schedule", "kế hoạch", "plan", 
        "tuần", "ngày", "thứ", "1 tuần", "một tuần", "7 ngày"
    ])


def build_context_from_exercises(exercises: List[Dict]) -> List[str]:
    """Xây dựng context từ danh sách exercises."""
    contexts: List[str] = []
    for exercise in exercises[:MAX_CONTEXT_EXERCISES]:
        name = exercise.get("name", "Bài tập")
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


def generate_answer_from_context(question: str, context_blocks: List[str], extra_guidance: Optional[str] = None) -> str:
    """Tạo câu trả lời từ context."""
    if not context_blocks:
        return "Xin lỗi, mình chưa tìm thấy thông tin về bài tập này trong dữ liệu hiện có."

    context_text = "\n\n".join(f"[Đoạn {idx}] {block}" for idx, block in enumerate(context_blocks, 1))
    
    # Sử dụng guidance lines chung
    guidance_lines = BASE_GUIDANCE_LINES.copy()
    
    # Thêm guidance đặc biệt nếu có
    if extra_guidance:
        guidance_lines.append(extra_guidance)

    prompt = (
        f"Ngữ cảnh:\n{context_text}\n\n"
        f"Hướng dẫn:\n" + "\n".join(guidance_lines) + "\n\n"
        f"Câu hỏi của khách: {question}\n\n"
    )
    messages = [{"role": "user", "content": prompt}]
    print(f"[ExerciseService] Messages: {messages}")
    return get_ai_response(messages, get_rag_system_prompt("exercises"))


def parse_inbody_from_message(message: str) -> Optional[Dict[str, Any]]:
    """
    Parse InBody data từ message (có thể là JSON hoặc text).
    
    Args:
        message: Message từ user có thể chứa InBody data
        
    Returns:
        InBody data dict hoặc None nếu không parse được
    """
    import json
    import re
    
    # Thử parse JSON trước
    try:
        # Tìm JSON object trong message
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', message, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            inbody_data = json.loads(json_str)
            
            # Kiểm tra xem có phải InBody data không
            if isinstance(inbody_data, dict):
                if "composition" in inbody_data or "inbody_info" in inbody_data or "muscle_fat" in inbody_data:
                    print(f"[ExerciseService] Parsed InBody data from JSON in message")
                    return inbody_data
    except (json.JSONDecodeError, AttributeError):
        pass
    
    
    try:
        
        weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|kilogram)', message, re.IGNORECASE)
        height_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cm|centimeter)', message, re.IGNORECASE)
        bmi_match = re.search(r'BMI[:\s]*(\d+(?:\.\d+)?)', message, re.IGNORECASE)
        fat_match = re.search(r'(?:tỷ\s*lệ\s*mỡ|body\s*fat|mỡ)[:\s]*(\d+(?:\.\d+)?)\s*%?', message, re.IGNORECASE)
        age_match = re.search(r'(?:tuổi|age)[:\s]*(\d+)', message, re.IGNORECASE)
        gender_match = re.search(r'(?:giới\s*tính|gender)[:\s]*(nam|nữ|male|female)', message, re.IGNORECASE)
        
        if weight_match or height_match or bmi_match:
            inbody_data = {
                "composition": {},
                "inbody_info": {},
                "muscle_fat": {},
                "obesity": {}
            }
            
            if weight_match:
                weight = float(weight_match.group(1))
                inbody_data["composition"]["weight"] = str(weight)
                inbody_data["muscle_fat"]["weight"] = str(weight)
            
            if height_match:
                height = float(height_match.group(1))
                inbody_data["inbody_info"]["height"] = str(height)
            
            if bmi_match:
                bmi = float(bmi_match.group(1))
                inbody_data["obesity"]["bmi"] = str(bmi)
            
            if fat_match:
                fat_pct = float(fat_match.group(1))
                inbody_data["obesity"]["pbf"] = str(fat_pct)
                
                if weight_match:
                    weight = float(weight_match.group(1))
                    fat_mass = (fat_pct / 100) * weight
                    inbody_data["muscle_fat"]["fat_mass"] = str(fat_mass)
                    inbody_data["composition"]["fat"] = str(fat_mass)
            
            if age_match:
                inbody_data["inbody_info"]["age"] = age_match.group(1)
            
            if gender_match:
                gender = gender_match.group(1).lower()
                if gender in ["nam", "male"]:
                    inbody_data["inbody_info"]["gender"] = "Male"
                elif gender in ["nữ", "female"]:
                    inbody_data["inbody_info"]["gender"] = "Female"
            
            
            if weight_match or height_match:
                print(f"[ExerciseService] Parsed InBody data from text in message")
                return inbody_data
                
    except Exception as e:
        print(f"[ExerciseService] Error parsing InBody from text: {e}")
    
    return None


def get_inbody_data_if_available(session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Lấy InBody data từ session nếu có.
    
    Args:
        session_id: Session ID để lấy InBody data
        
    Returns:
        InBody data dict hoặc None nếu không có
    """
    if session_id:
        inbody_data = get_inbody_data(session_id)
        if inbody_data:
            return inbody_data
    return None


# DEPRECATED: Các function này đã được thay thế bởi Rule Engine và InBody Normalizer
# Chỉ giữ lại để fallback khi Rule Engine lỗi (backward compatibility)
def _personalize_results_with_inbody(
    good_results: List[Dict[str, Any]],
    inbody_data: Optional[Dict[str, Any]],
    workout_plan: bool,
) -> List[Dict[str, Any]]:
    """
    DEPRECATED: Fallback function khi Rule Engine lỗi.
    Đã được thay thế bởi Rule Engine - chỉ dùng trong trường hợp exception.
    """
    if not inbody_data:
        return good_results
    
    # Fallback đơn giản: chỉ sort theo semantic score
    return sorted(good_results, key=lambda x: x.get("score", 1.0))


def is_exercise_related_query(message: str) -> bool:
    """Phát hiện câu hỏi về bài tập bằng semantic search."""
    try:
        from utils.query_classifier import is_exercise_query
        return is_exercise_query(message)
    except Exception as e:
        print(f"[ExerciseService] Error in is_exercise_related_query: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_exercise_response(message: str, inbody_data: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None) -> str:
    """
    Tạo câu trả lời cho câu hỏi về bài tập.
    
    Args:
        message: Câu hỏi về bài tập
        inbody_data: Dữ liệu InBody (nếu có) để cá nhân hóa bài tập
        session_id: Session ID (dùng để lấy InBody data đã lưu nếu cần)
    """
    print(f"[ExerciseService] Generating exercise response for message: {message}")
    
    # Nếu chưa truyền inbody_data vào, thử lấy từ session
    if inbody_data is None and session_id:
        inbody_data = get_inbody_data_if_available(session_id)

    # Kiểm tra xem có phải query về lộ trình/chương trình tập không
    workout_plan = is_workout_plan_query(message)
    
    # Semantic search đơn giản
    semantic_results: List[Dict] = []
    try:
        # Nếu là query về lộ trình, tăng top_k để có nhiều bài tập đa dạng
        search_top_k = 20 if workout_plan else 10
        semantic_results = semantic_search(message, top_k=search_top_k)
    except Exception as exc:
        print(f"[ExerciseService] semantic_search failed: {exc}")
        import traceback
        traceback.print_exc()

    # Xử lý kết quả
    if semantic_results:
        # Nếu là query về lộ trình, không filter theo score threshold (lấy tất cả)
        # Nếu không, chỉ lấy kết quả có score tốt
        if workout_plan:
            # Lấy tất cả kết quả, sắp xếp theo score
            good_results = sorted(
                [item for item in semantic_results if item.get("score") is not None],
                key=lambda x: x.get("score", 1.0)
            )
        else:
            # Filter theo score threshold cho query thông thường
            SEMANTIC_SCORE_THRESHOLD = 0.85
            good_results = [
                item for item in semantic_results 
                if item.get("score") is not None and item.get("score") < SEMANTIC_SCORE_THRESHOLD
            ]
        
        if good_results:
            # Extract exercises từ semantic results (giữ nguyên để fallback)
            original_exercises = [item.get("raw") for item in good_results if item.get("raw")]
            exercises_from_search = original_exercises.copy()
            
            # Áp dụng Rule Engine nếu có InBody data
            if inbody_data and exercises_from_search:
                try:
                    # Chuẩn hóa InBody data thành User Signals
                    user_signals = normalize_inbody_data(inbody_data)
                    print(f"[ExerciseService] User Signals: {user_signals}")
                    
                    # Áp dụng Rule Engine để filter và score bài tập
                    rule_engine = RuleEngine()
                    filtered_exercises = rule_engine.filter_exercises(
                        exercises=exercises_from_search,
                        user_signals=user_signals,
                    )
                    
                    if filtered_exercises:
                        print(f"[ExerciseService] Rule Engine filtered {len(exercises_from_search)} -> {len(filtered_exercises)} exercises")
                        exercises_from_search = filtered_exercises
                    else:
                        print(f"[ExerciseService] Rule Engine blocked all exercises, using original results")
                        # Nếu Rule Engine block hết, vẫn dùng kết quả gốc nhưng cảnh báo
                        exercises_from_search = original_exercises
                except Exception as exc:
                    print(f"[ExerciseService] Rule Engine error: {exc}")
                    import traceback
                    traceback.print_exc()
                    # Fallback: chỉ sort theo semantic score nếu Rule Engine lỗi
                    good_results = sorted(good_results, key=lambda x: x.get("score", 1.0))
                    exercises_from_search = [item.get("raw") for item in good_results if item.get("raw")]
            elif inbody_data is None:
                # Không có InBody, dùng logic cũ để sort theo semantic score
                good_results = sorted(
                    good_results,
                    key=lambda x: x.get("score", 1.0)
                )
                exercises_from_search = [item.get("raw") for item in good_results if item.get("raw")]

            # Lấy top exercises (nhiều hơn nếu là lộ trình)
            max_exercises = MAX_CONTEXT_EXERCISES * 2 if workout_plan else MAX_CONTEXT_EXERCISES
            top_exercises = exercises_from_search[:max_exercises]
            
            if top_exercises:
                contexts = build_context_from_exercises(top_exercises)
                return generate_answer_from_context(message, contexts)
    
    # Fallback: Nếu không có kết quả semantic search, vẫn trả về một số bài tập để tạo lộ trình
    if workout_plan:
        print(f"[ExerciseService] No semantic results for workout plan query, using all exercises as fallback")
        all_exercises = get_all_exercises()
        if all_exercises:
            # Áp dụng Rule Engine nếu có InBody data
            if inbody_data:
                try:
                    user_signals = normalize_inbody_data(inbody_data)
                    rule_engine = RuleEngine()
                    filtered_exercises = rule_engine.filter_exercises(
                        exercises=all_exercises,
                        user_signals=user_signals,
                    )
                    if filtered_exercises:
                        all_exercises = filtered_exercises
                        print(f"[ExerciseService] Rule Engine filtered fallback exercises: {len(filtered_exercises)}")
                except Exception as exc:
                    print(f"[ExerciseService] Rule Engine error in fallback: {exc}")
            
            # Lấy một số bài tập đa dạng
            import random
            selected_exercises = random.sample(all_exercises, min(15, len(all_exercises)))
            contexts = build_context_from_exercises(selected_exercises)
            return generate_answer_from_context(message, contexts)

    # Nếu không tìm thấy kết quả semantic search phù hợp
    return "Mình chưa tìm thấy thông tin về bài tập bạn đang hỏi. Bạn có thể mô tả cụ thể hơn về bài tập hoặc nhóm cơ bạn muốn tập không?"

