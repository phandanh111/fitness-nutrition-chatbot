"""Exercise-related helpers with embedding-based RAG pipeline."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Any

from rag.exercise_rag import semantic_search, parse_exercises_from_markdown
from services.llm_service import get_ai_response
from constants.rag_prompts import get_rag_system_prompt
from services.conversation_service import get_inbody_data, set_inbody_data

MAX_CONTEXT_EXERCISES = int(os.getenv("EXERCISE_CONTEXT_LIMIT", "10"))

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


def generate_answer_from_context(question: str, context_blocks: List[str], extra_guidance: Optional[str] = None) -> str:
    """Tạo câu trả lời từ context."""
    if not context_blocks:
        return "Xin lỗi, mình chưa tìm thấy thông tin về bài tập này trong dữ liệu hiện có."

    context_text = "\n\n".join(f"[Đoạn {idx}] {block}" for idx, block in enumerate(context_blocks, 1))
    guidance_lines = [
        "QUAN TRỌNG: BẠN PHẢI TUYỆT ĐỐI CHỈ sử dụng thông tin trong các đoạn ngữ cảnh bên trên.",
        "TUYỆT ĐỐI KHÔNG được tự tạo, bịa đặt, hoặc suy đoán thông tin về bài tập, nhóm cơ, thiết bị, hoặc bất kỳ thông tin nào khác.",
        "Nếu ngữ cảnh không chứa thông tin về bài tập được hỏi, bạn PHẢI nói rõ 'Mình chưa tìm thấy thông tin về bài tập này' và KHÔNG được liệt kê các bài tập không có trong ngữ cảnh.",
        "Câu trả lời chỉ 1 JSON OBJECT duy nhất với các key là ngày trong tuần và value là danh sách các bài tập tương ứng bằng tiếng việt, không cần thêm bất kỳ note và text nào khác trước và sau dấu đóng mở của object.",
    ]
    if extra_guidance:
        guidance_lines.append(f"- {extra_guidance}")

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
    
    # Thử parse từ text format: "Tôi nặng 55kg, cao 160cm, BMI 21.5"
    try:
        # Extract các số liệu từ text
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
                # Estimate fat mass if we have weight
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
            
            # Chỉ trả về nếu có ít nhất weight hoặc height
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


def _enhance_query_with_inbody(message: str, inbody_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Enhance query với thông tin InBody nếu có (Option 1 - nhẹ).
    
    Args:
        message: Câu hỏi gốc
        inbody_data: Dữ liệu InBody (optional)
        
    Returns:
        Enhanced query string
    """
    if not inbody_data:
        return message
    
    try:
        # Lazy import để tránh circular import
        from services.inbody_service import analyze_health_status
        
        # Phân tích InBody để lấy thông tin cơ bản
        analysis = analyze_health_status(inbody_data)
        bmi = analysis.get("bmi")
        goals = analysis.get("goals", [])
        
        # Thêm context nhẹ vào query
        context_parts = []
        
        if bmi:
            if bmi < 18.5:
                context_parts.append("cho người gầy cần tăng cân tăng cơ")
            elif bmi >= 25:
                context_parts.append("cho người thừa cân cần giảm mỡ")
        
        if goals:
            # Lấy mục tiêu chính
            main_goal = goals[0] if goals else ""
            if "tăng cân" in main_goal.lower() or "tăng cơ" in main_goal.lower():
                context_parts.append("ưu tiên bài tập tăng cơ")
            elif "giảm mỡ" in main_goal.lower() or "giảm cân" in main_goal.lower():
                context_parts.append("ưu tiên bài tập đốt mỡ cardio")
        
        if context_parts:
            enhanced = f"{message}. {', '.join(context_parts)}"
            print(f"[ExerciseService] Enhanced query: {enhanced}")
            return enhanced
        
    except Exception as e:
        print(f"[ExerciseService] Error enhancing query with InBody: {e}")
    
    return message


def _filter_exercises_by_inbody(
    semantic_results: List[Dict], 
    inbody_data: Optional[Dict[str, Any]] = None
) -> List[Dict]:
    """
    Filter và re-rank exercises dựa trên InBody data (Option 2).
    
    Args:
        semantic_results: Kết quả semantic search
        inbody_data: Dữ liệu InBody (optional)
        
    Returns:
        Filtered và re-ranked results
    """
    if not inbody_data or not semantic_results:
        return semantic_results
    
    try:
        # Lazy import để tránh circular import
        from services.inbody_service import analyze_health_status
        
        # Phân tích InBody
        analysis = analyze_health_status(inbody_data)
        bmi = analysis.get("bmi")
        pbf = analysis.get("body_fat_percentage")
        goals = analysis.get("goals", [])
        recommended_difficulty = analysis.get("recommended_difficulty", "BASIC")
        focus_areas = analysis.get("focus_areas", [])
        
        # Parse exercises từ raw data
        exercises_with_scores = []
        for result in semantic_results:
            raw_data = result.get("raw")
            if not raw_data:
                continue
            
            # Parse raw JSON nếu cần
            try:
                if isinstance(raw_data, str):
                    import json
                    exercise = json.loads(raw_data)
                else:
                    exercise = raw_data
            except:
                exercise = raw_data if isinstance(raw_data, dict) else {}
            
            score = result.get("score", 1.0)
            exercises_with_scores.append({
                "exercise": exercise,
                "original_score": score,
                "adjusted_score": score,  # Sẽ được điều chỉnh
                "result": result
            })
        
        # Filter và re-rank
        filtered = []
        
        for item in exercises_with_scores:
            exercise = item["exercise"]
            adjusted_score = item["original_score"]
            
            # 1. Filter theo độ khó
            difficulty = exercise.get("difficulty", "").strip()
            difficulty_match = False
            
            # Extract difficulty level
            if "(" in difficulty:
                match = re.search(r'\(([^)]+)\)', difficulty)
                if match:
                    difficulty_clean = match.group(1).strip()
                else:
                    difficulty_clean = difficulty
            else:
                difficulty_clean = difficulty
            
            # Kiểm tra độ khó phù hợp
            if recommended_difficulty == "BASIC" or recommended_difficulty == "BEGINNER":
                if difficulty_clean in ["BASIC", "BEGINNER"]:
                    difficulty_match = True
                    adjusted_score *= 0.9  # Boost score
                elif difficulty_clean in ["MODERATE", "ADVANCED"]:
                    adjusted_score *= 1.1  # Penalize score
            elif recommended_difficulty == "MODERATE":
                if difficulty_clean in ["BASIC", "BEGINNER", "MODERATE"]:
                    difficulty_match = True
                    if difficulty_clean == "MODERATE":
                        adjusted_score *= 0.9  # Boost
                elif difficulty_clean == "ADVANCED":
                    adjusted_score *= 1.1  # Penalize
            elif recommended_difficulty == "ADVANCED":
                difficulty_match = True  # Advanced có thể làm tất cả
                if difficulty_clean == "ADVANCED":
                    adjusted_score *= 0.9  # Boost
            
            # 2. Filter theo goals
            name = (exercise.get("nameVi", "") + " " + exercise.get("nameEn", "")).lower()
            muscle_group = exercise.get("muscleGroup", "").lower()
            
            # Nếu mục tiêu là giảm mỡ/giảm cân
            if any("giảm" in goal.lower() or "mỡ" in goal.lower() or "cân" in goal.lower() for goal in goals):
                # Ưu tiên bài tập cardio, full body, high calories
                if any(keyword in name for keyword in ["cardio", "hiit", "burn", "circuit"]):
                    adjusted_score *= 0.85  # Boost significantly
                if "full body" in muscle_group or "toàn thân" in muscle_group:
                    adjusted_score *= 0.9  # Boost
                calories = exercise.get("calories", "")
                try:
                    cal_value = float(str(calories).replace(" kcal", "").strip())
                    if cal_value > 200:
                        adjusted_score *= 0.9  # Boost high calorie exercises
                except:
                    pass
            
            # Nếu mục tiêu là tăng cân/tăng cơ
            elif any("tăng" in goal.lower() or "cơ" in goal.lower() for goal in goals):
                # Ưu tiên bài tập strength, builder, power
                if any(keyword in name for keyword in ["builder", "build", "power", "strong", "gains"]):
                    adjusted_score *= 0.85  # Boost significantly
                # Tránh bài tập cardio quá nhiều
                if "cardio" in name and "light" not in name:
                    adjusted_score *= 1.1  # Penalize
            
            # 3. Filter theo focus areas
            if focus_areas:
                area_keywords = {
                    "Core": ["core", "abs", "bụng"],
                    "Cardio": ["cardio", "hiit", "burn"],
                    "Full Body": ["full body", "toàn thân"],
                }
                
                matched = False
                for area in focus_areas:
                    if area in area_keywords:
                        keywords = area_keywords[area]
                        if any(kw in name or kw in muscle_group for kw in keywords):
                            adjusted_score *= 0.9  # Boost
                            matched = True
                            break
            
            # 4. Filter theo BMI cụ thể
            if bmi:
                if bmi < 18.5:  # Gầy
                    # Tránh bài tập cardio nặng, ưu tiên strength
                    if "cardio" in name and "light" not in name:
                        adjusted_score *= 1.15  # Penalize
                    if any(kw in name for kw in ["builder", "build", "power"]):
                        adjusted_score *= 0.85  # Boost
                elif bmi >= 25:  # Thừa cân
                    # Ưu tiên cardio, tránh bài tập quá nặng
                    if "cardio" in name or "hiit" in name:
                        adjusted_score *= 0.85  # Boost
                    if "advanced" in difficulty.lower():
                        adjusted_score *= 1.1  # Penalize nếu quá khó
            
            item["adjusted_score"] = adjusted_score
            filtered.append(item)
        
        # Sort lại theo adjusted_score (thấp hơn = tốt hơn)
        filtered.sort(key=lambda x: x["adjusted_score"])
        
        # Trả về results với score đã điều chỉnh
        return [item["result"] for item in filtered]
        
    except Exception as e:
        print(f"[ExerciseService] Error filtering exercises by InBody: {e}")
        import traceback
        traceback.print_exc()
        return semantic_results  # Fallback về kết quả gốc


def generate_exercise_response(message: str, inbody_data: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None) -> str:
    """
    Tạo câu trả lời cho câu hỏi về bài tập.
    
    Args:
        message: Câu hỏi về bài tập
        inbody_data: Dữ liệu InBody để cá nhân hóa (optional, nếu None sẽ lấy từ session)
        session_id: Session ID để lấy InBody data từ session (optional)
    """
    # Nếu không có inbody_data, thử lấy từ session
    if not inbody_data and session_id:
        inbody_data = get_inbody_data_if_available(session_id)
    # Kiểm tra câu hỏi về số lượng
    print(f"[ExerciseService] Generating exercise response for message: {message}")
    if is_count_query(message):
        all_exercises = get_all_exercises()
        if not all_exercises:
            return "Xin lỗi, hiện chưa có dữ liệu về các bài tập trong hệ thống."
        
        total_context = build_total_counts_context(all_exercises)
        print(f"[ExerciseService] Total context: {total_context}")
        return generate_answer_from_context(
            message,
            [total_context],
            extra_guidance="Trả lời rõ ràng tổng số bài tập và phân loại theo độ khó nếu có. KHÔNG liệt kê từng bài tập, chỉ trả lời về số lượng.",
        )
    
    # Enhance query với InBody nếu có (Option 1 - nhẹ)
    enhanced_query = _enhance_query_with_inbody(message, inbody_data)
    
    # Semantic search với top_k lớn hơn để có nhiều options
    search_top_k = 20 if inbody_data else 10
    semantic_results: List[Dict] = []
    try:
        semantic_results = semantic_search(enhanced_query, top_k=search_top_k)
    except Exception as exc:
        print(f"[ExerciseService] semantic_search failed: {exc}")
        import traceback
        traceback.print_exc()

    # Filter và re-rank dựa trên InBody nếu có (Option 2)
    if inbody_data and semantic_results:
        print(f"[ExerciseService] Filtering {len(semantic_results)} results with InBody data")
        semantic_results = _filter_exercises_by_inbody(semantic_results, inbody_data)
        print(f"[ExerciseService] After filtering: {len(semantic_results)} results")

    # Chỉ sử dụng kết quả nếu score tốt (score < 0.85 nghĩa là tương đồng tốt)
    SEMANTIC_SCORE_THRESHOLD = 0.85
    if semantic_results:
        # Lọc các kết quả có score tốt (score < threshold)
        good_results = [
            item for item in semantic_results 
            if item.get("score") is not None and item.get("score") < SEMANTIC_SCORE_THRESHOLD
        ]
        
        if good_results:
            # Lấy top exercises sau khi filter
            top_results = good_results[:MAX_CONTEXT_EXERCISES]
            semantic_exercises = [item.get("raw") for item in top_results if item.get("raw")]
            if semantic_exercises:
                contexts = build_context_from_exercises(semantic_exercises)
                return generate_answer_from_context(message, contexts)

    # Nếu không tìm thấy kết quả semantic search phù hợp (score quá cao = không tương đồng)
    # Trả về thông báo chung - không dùng keyword check, hoàn toàn dựa vào vector similarity
    return "Mình chưa tìm thấy thông tin về bài tập bạn đang hỏi. Bạn có thể mô tả cụ thể hơn về bài tập hoặc nhóm cơ bạn muốn tập không?"

