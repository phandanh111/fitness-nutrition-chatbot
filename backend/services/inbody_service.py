"""InBody analysis service - Phân tích dữ liệu InBody và gợi ý bài tập phù hợp."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from services.exercise_service import get_all_exercises, build_context_from_exercises
from services.llm_service import get_ai_response
from constants.rag_prompts import get_rag_system_prompt
from rag.inbody_rag import parse_inbody_from_markdown

# Đường dẫn đến file InBody
BASE_DIR = Path(__file__).resolve().parent.parent
INBODY_MD_PATH = BASE_DIR / "data" / "inbody.md"


def is_inbody_related_query(message: str) -> bool:
    """Phát hiện câu hỏi về InBody bằng semantic search."""
    try:
        from utils.query_classifier import is_inbody_query
        return is_inbody_query(message)
    except Exception as e:
        print(f"[InBodyService] Error in is_inbody_related_query: {e}")
        import traceback
        traceback.print_exc()
        return False


# parse_inbody_from_markdown đã được import từ rag.inbody_rag


def analyze_health_status(inbody_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phân tích tình trạng sức khỏe từ dữ liệu InBody.
    
    Args:
        inbody_data: Dict chứa dữ liệu InBody
        
    Returns:
        Dict chứa phân tích tình trạng sức khỏe
    """
    analysis = {
        "overall_score": None,
        "bmi": None,
        "body_fat_percentage": None,
        "muscle_mass": None,
        "health_status": "unknown",
        "goals": [],
        "recommended_difficulty": "BASIC",
        "focus_areas": [],
        "concerns": [],
    }
    
    try:
        # Lấy thông tin cơ bản
        composition = inbody_data.get("composition", {})
        muscle_fat = inbody_data.get("muscle_fat", {})
        obesity = inbody_data.get("obesity", {})
        score = inbody_data.get("score", {})
        inbody_info = inbody_data.get("inbody_info", {})
        segmental_fat = inbody_data.get("segmental_fat", {})
        segmental_lean = inbody_data.get("segmental_lean", {})
        
        # Parse các giá trị số
        def safe_float(value, default=None):
            try:
                if isinstance(value, str):
                    return float(value)
                return float(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        weight = safe_float(composition.get("weight") or muscle_fat.get("weight"))
        height = safe_float(inbody_info.get("height"))
        age = safe_float(inbody_info.get("age"))
        gender = inbody_info.get("gender", "").lower()
        
        # BMI
        bmi = safe_float(obesity.get("bmi"))
        if not bmi and weight and height:
            # Tính BMI: weight (kg) / (height (m))^2
            height_m = height / 100
            bmi = weight / (height_m ** 2)
        analysis["bmi"] = bmi
        
        # Body Fat Percentage
        pbf = safe_float(obesity.get("pbf"))
        fat_mass = safe_float(muscle_fat.get("fat_mass"))
        if not pbf and fat_mass and weight:
            pbf = (fat_mass / weight) * 100
        analysis["body_fat_percentage"] = pbf
        
        # Skeletal Muscle Mass
        smm = safe_float(muscle_fat.get("smm"))
        analysis["muscle_mass"] = smm
        
        # Overall Score
        overall_score = safe_float(score.get("score"))
        analysis["overall_score"] = overall_score
        
        # Phân tích tình trạng sức khỏe
        concerns = []
        goals = []
        focus_areas = []
        recommended_difficulty = "BASIC"
        
        # Phân tích BMI
        if bmi:
            if bmi < 18.5:
                concerns.append("Thiếu cân (BMI < 18.5)")
                goals.append("Tăng cân lành mạnh")
                goals.append("Tăng khối lượng cơ")
                recommended_difficulty = "BASIC"
            elif bmi >= 18.5 and bmi < 25:
                goals.append("Duy trì cân nặng")
                goals.append("Tăng cơ giảm mỡ")
            elif bmi >= 25 and bmi < 30:
                concerns.append("Thừa cân (BMI 25-30)")
                goals.append("Giảm cân")
                goals.append("Giảm mỡ")
                recommended_difficulty = "MODERATE"
            else:
                concerns.append("Béo phì (BMI >= 30)")
                goals.append("Giảm cân")
                goals.append("Giảm mỡ")
                recommended_difficulty = "BASIC"  # Bắt đầu từ cơ bản
        
        # Phân tích Body Fat %
        if pbf:
            if gender == "male":
                if pbf < 10:
                    concerns.append("Tỷ lệ mỡ quá thấp (< 10%)")
                    goals.append("Tăng khối lượng cơ")
                elif pbf >= 10 and pbf <= 20:
                    pass  # Bình thường
                elif pbf > 20 and pbf <= 25:
                    concerns.append("Tỷ lệ mỡ hơi cao (20-25%)")
                    goals.append("Giảm mỡ")
                    focus_areas.append("Cardio")
                else:
                    concerns.append("Tỷ lệ mỡ cao (> 25%)")
                    goals.append("Giảm mỡ")
                    focus_areas.append("Cardio")
                    focus_areas.append("Full Body")
            else:  # female
                if pbf < 16:
                    concerns.append("Tỷ lệ mỡ quá thấp (< 16%)")
                    goals.append("Tăng khối lượng cơ")
                elif pbf >= 16 and pbf <= 25:
                    pass  # Bình thường
                elif pbf > 25 and pbf <= 32:
                    concerns.append("Tỷ lệ mỡ hơi cao (25-32%)")
                    goals.append("Giảm mỡ")
                    focus_areas.append("Cardio")
                else:
                    concerns.append("Tỷ lệ mỡ cao (> 32%)")
                    goals.append("Giảm mỡ")
                    focus_areas.append("Cardio")
                    focus_areas.append("Full Body")
        
        # Phân tích segmental fat (mỡ theo từng phần)
        if segmental_fat:
            trunk_status = segmental_fat.get("trunk_status", "").lower()
            if trunk_status == "over":
                concerns.append("Mỡ vùng bụng/trunk cao")
                focus_areas.append("Core")
                focus_areas.append("Full Body")
        
        # Phân tích segmental lean (cơ theo từng phần)
        if segmental_lean:
            # Kiểm tra các phần có status "Low" hoặc "Under"
            for key, value in segmental_lean.items():
                if key.endswith("_status") and isinstance(value, str):
                    status_lower = value.lower()
                    if status_lower in ["low", "under"]:
                        part = key.replace("_status", "").replace("_", " ").title()
                        focus_areas.append(part)
        
        # Xác định mục tiêu chính
        if not goals:
            goals.append("Cải thiện sức khỏe tổng thể")
            goals.append("Tăng cơ giảm mỡ")
        
        # Xác định độ khó phù hợp dựa trên overall score
        if overall_score:
            if overall_score >= 80:
                recommended_difficulty = "ADVANCED"
            elif overall_score >= 60:
                recommended_difficulty = "MODERATE"
            else:
                recommended_difficulty = "BASIC"
        
        analysis["health_status"] = "good" if overall_score and overall_score >= 70 else "needs_improvement"
        analysis["goals"] = list(set(goals))  # Remove duplicates
        analysis["recommended_difficulty"] = recommended_difficulty
        analysis["focus_areas"] = list(set(focus_areas))  # Remove duplicates
        analysis["concerns"] = concerns
        
    except Exception as e:
        print(f"[InBodyService] Error analyzing health status: {e}")
        import traceback
        traceback.print_exc()
    
    return analysis


def recommend_exercises(health_analysis: Dict[str, Any], all_exercises: List[Dict]) -> List[Dict]:
    """
    Gợi ý bài tập dựa trên phân tích sức khỏe.
    
    Args:
        health_analysis: Kết quả phân tích từ analyze_health_status
        all_exercises: Danh sách tất cả bài tập
        
    Returns:
        List các bài tập được gợi ý
    """
    if not all_exercises:
        return []
    
    recommended_difficulty = health_analysis.get("recommended_difficulty", "BASIC")
    focus_areas = health_analysis.get("focus_areas", [])
    goals = health_analysis.get("goals", [])
    
    # Lọc bài tập theo độ khó
    filtered_exercises = []
    for ex in all_exercises:
        difficulty = ex.get("difficulty", "").strip()
        
        # Ưu tiên bài tập có độ khó phù hợp
        if difficulty == recommended_difficulty:
            filtered_exercises.append(ex)
        # Hoặc độ khó thấp hơn (an toàn hơn)
        elif recommended_difficulty == "ADVANCED" and difficulty in ["MODERATE", "BASIC", "BEGINNER"]:
            filtered_exercises.append(ex)
        elif recommended_difficulty == "MODERATE" and difficulty in ["BASIC", "BEGINNER"]:
            filtered_exercises.append(ex)
        elif recommended_difficulty == "BASIC" and difficulty == "BEGINNER":
            filtered_exercises.append(ex)
    
    # Nếu không có bài tập nào phù hợp với độ khó, lấy tất cả
    if not filtered_exercises:
        filtered_exercises = all_exercises
    
    # Lọc theo focus areas (nhóm cơ)
    if focus_areas:
        # Map focus areas sang muscle groups trong exercise data
        area_mapping = {
            "Core": ["Core"],
            "Cardio": ["Toàn thân (Full Body)"],
            "Full Body": ["Toàn thân (Full Body)"],
            "Left Arm": ["Tay (Arms)", "Thân trên (Upper Body)"],
            "Right Arm": ["Tay (Arms)", "Thân trên (Upper Body)"],
            "Left Leg": ["Chân (Legs)", "Toàn thân (Full Body)"],
            "Right Leg": ["Chân (Legs)", "Toàn thân (Full Body)"],
            "Trunk": ["Core", "Thân trên (Upper Body)"],
        }
        
        target_muscle_groups = set()
        for area in focus_areas:
            if area in area_mapping:
                target_muscle_groups.update(area_mapping[area])
        
        # Ưu tiên bài tập có nhóm cơ phù hợp
        prioritized = []
        others = []
        
        for ex in filtered_exercises:
            muscle_group = ex.get("muscleGroup", "")
            if any(target in muscle_group for target in target_muscle_groups):
                prioritized.append(ex)
            else:
                others.append(ex)
        
        filtered_exercises = prioritized + others
    
    # Lọc theo goals
    if goals:
        # Nếu mục tiêu là giảm cân/giảm mỡ, ưu tiên bài tập có kcal cao
        if any("giảm" in goal.lower() or "mỡ" in goal.lower() or "cân" in goal.lower() for goal in goals):
            filtered_exercises.sort(key=lambda x: float(x.get("calories", 0) or 0), reverse=True)
        # Nếu mục tiêu là tăng cơ, ưu tiên bài tập strength
        elif any("cơ" in goal.lower() or "tăng" in goal.lower() for goal in goals):
            # Ưu tiên bài tập không phải cardio (reverse=True để True (non-cardio) đứng trước False (cardio))
            filtered_exercises.sort(key=lambda x: "cardio" not in (x.get("nameVi", "") + " " + x.get("nameEn", "")).lower(), reverse=True)
    
    # Trả về tối đa 5 bài tập
    return filtered_exercises[:5]


def generate_inbody_response(message: str) -> str:
    """
    Tạo câu trả lời cho câu hỏi về InBody.
    Đọc dữ liệu InBody từ file inbody.md.
    
    Args:
        message: Câu hỏi về InBody (không cần chứa JSON)
        
    Returns:
        Response text với phân tích và gợi ý bài tập
    """
    # Đọc dữ liệu InBody từ file markdown
    inbody_data = parse_inbody_from_markdown()
    
    if not inbody_data:
        return (
            "Mình không tìm thấy dữ liệu InBody trong hệ thống. "
            "Vui lòng đảm bảo file inbody.md đã được cập nhật với dữ liệu InBody mới nhất."
        )
    
    # Phân tích tình trạng sức khỏe
    health_analysis = analyze_health_status(inbody_data)
    
    # Lấy tất cả bài tập
    all_exercises = get_all_exercises()
    
    # Gợi ý bài tập
    recommended_exercises = recommend_exercises(health_analysis, all_exercises)
    
    # Xây dựng context cho LLM
    analysis_text = build_analysis_context(health_analysis, inbody_data)
    exercise_contexts = build_context_from_exercises(recommended_exercises) if recommended_exercises else []
    
    # Tạo prompt cho LLM
    context_blocks = [analysis_text]
    if exercise_contexts:
        context_blocks.append("\n=== CÁC BÀI TẬP ĐƯỢC GỢI Ý ===\n")
        context_blocks.extend(exercise_contexts)
    
    prompt = (
        f"Bạn là một chuyên gia tư vấn sức khỏe và thể hình của The New Gym. "
        f"Dựa trên phân tích InBody và các bài tập được gợi ý, hãy tạo một phản hồi tư vấn cho khách hàng.\n\n"
        f"=== DỮ LIỆU PHÂN TÍCH INBODY (CHỈ SỬ DỤNG THÔNG TIN NÀY) ===\n"
        f"{analysis_text}\n\n"
    )
    
    if exercise_contexts:
        prompt += (
            f"=== CÁC BÀI TẬP ĐƯỢC GỢI Ý (CHỈ LIỆT KÊ CÁC BÀI TẬP NÀY) ===\n"
            + "\n\n".join(exercise_contexts) + "\n\n"
        )
    
    prompt += (
        f"=== HƯỚNG DẪN TẠO PHẢN HỒI ===\n"
        f"Hãy tạo một phản hồi tư vấn với các phần sau:\n"
        f"1. Tóm tắt tình trạng sức khỏe hiện tại (CHỈ dựa trên các chỉ số có trong phân tích trên)\n"
        f"2. Nhận xét về các điểm cần cải thiện (CHỈ nếu có trong phần 'Các điểm cần lưu ý')\n"
        f"3. Mục tiêu tập luyện đề xuất (CHỈ dựa trên 'Mục tiêu đề xuất' trong phân tích)\n"
        f"4. Giới thiệu các bài tập phù hợp (CHỈ liệt kê các bài tập có trong danh sách gợi ý trên, bao gồm tên, nhóm cơ, độ khó, kcal tiêu thụ)\n"
        f"5. Lời khuyên tổng thể (tích cực, động viên, nhưng không tự thêm thông tin y tế)\n\n"
        f"=== QUY TẮC NGHIÊM NGẶT (TUYỆT ĐỐI TUÂN THỦ) ===\n"
        f"1. TUYỆT ĐỐI KHÔNG được tự tạo, bịa đặt, hoặc thêm bất kỳ chỉ số sức khỏe nào không có trong phân tích trên.\n"
        f"2. TUYỆT ĐỐI KHÔNG được tự thêm các số liệu như BMI, tỷ lệ mỡ, khối lượng cơ nếu chúng không có trong phân tích.\n"
        f"3. TUYỆT ĐỐI KHÔNG được đưa ra chẩn đoán y tế, cảnh báo về bệnh tật, hoặc khuyến nghị y tế chuyên sâu.\n"
        f"4. CHỈ được sử dụng các chỉ số, số liệu, và kết luận CÓ SẴN trong phần 'DỮ LIỆU PHÂN TÍCH INBODY' ở trên.\n"
        f"5. CHỈ được liệt kê các bài tập CÓ TRONG danh sách 'CÁC BÀI TẬP ĐƯỢC GỢI Ý' ở trên.\n"
        f"6. Nếu một chỉ số không có trong phân tích, bạn PHẢI nói rõ 'Mình không có thông tin về [chỉ số đó] trong dữ liệu InBody'.\n"
        f"7. Nếu không có bài tập nào trong danh sách, bạn PHẢI nói rõ và đề nghị liên hệ với huấn luyện viên.\n"
        f"8. Trả lời bằng tiếng Việt, giọng điệu thân thiện, chuyên nghiệp, sử dụng đại từ 'mình'/'bạn'.\n"
        f"9. Nếu có bất kỳ nghi ngờ nào về thông tin sức khỏe, hãy đề nghị khách hàng tham khảo ý kiến bác sĩ hoặc chuyên gia y tế.\n"
    )
    
    messages = [{"role": "user", "content": prompt}]
    response = get_ai_response(messages, get_rag_system_prompt("inbody"))
    
    return response if response else "Xin lỗi, mình không thể tạo phản hồi lúc này. Vui lòng thử lại sau."


def build_analysis_context(health_analysis: Dict[str, Any], inbody_data: Dict[str, Any]) -> str:
    """
    Xây dựng context text từ phân tích sức khỏe.
    
    Args:
        health_analysis: Kết quả phân tích từ analyze_health_status
        inbody_data: Dữ liệu InBody gốc
        
    Returns:
        Text context mô tả phân tích
    """
    lines = []
    
    # Thông tin cơ bản
    inbody_info = inbody_data.get("inbody_info", {})
    if inbody_info:
        age = inbody_info.get("age")
        gender = inbody_info.get("gender")
        height = inbody_info.get("height")
        if age or gender or height:
            info_parts = []
            if age:
                info_parts.append(f"Tuổi: {age}")
            if gender:
                info_parts.append(f"Giới tính: {gender}")
            if height:
                info_parts.append(f"Chiều cao: {height} cm")
            lines.append("Thông tin cá nhân: " + ", ".join(info_parts))
    
    # Overall Score
    if health_analysis.get("overall_score"):
        lines.append(f"Điểm tổng thể: {health_analysis['overall_score']}/100")
    
    # BMI
    if health_analysis.get("bmi"):
        bmi = health_analysis["bmi"]
        bmi_status = ""
        if bmi < 18.5:
            bmi_status = " (Thiếu cân)"
        elif bmi >= 18.5 and bmi < 25:
            bmi_status = " (Bình thường)"
        elif bmi >= 25 and bmi < 30:
            bmi_status = " (Thừa cân)"
        else:
            bmi_status = " (Béo phì)"
        lines.append(f"BMI: {bmi:.1f}{bmi_status}")
    
    # Body Fat Percentage
    if health_analysis.get("body_fat_percentage"):
        pbf = health_analysis["body_fat_percentage"]
        lines.append(f"Tỷ lệ mỡ cơ thể: {pbf:.1f}%")
    
    # Muscle Mass
    if health_analysis.get("muscle_mass"):
        smm = health_analysis["muscle_mass"]
        lines.append(f"Khối lượng cơ xương (SMM): {smm:.1f} kg")
    
    # Health Status
    health_status = health_analysis.get("health_status", "unknown")
    if health_status == "good":
        lines.append("Tình trạng sức khỏe: Tốt")
    elif health_status == "needs_improvement":
        lines.append("Tình trạng sức khỏe: Cần cải thiện")
    
    # Concerns
    concerns = health_analysis.get("concerns", [])
    if concerns:
        lines.append(f"Các điểm cần lưu ý: {', '.join(concerns)}")
    
    # Goals
    goals = health_analysis.get("goals", [])
    if goals:
        lines.append(f"Mục tiêu đề xuất: {', '.join(goals)}")
    
    # Recommended Difficulty
    difficulty = health_analysis.get("recommended_difficulty", "BASIC")
    difficulty_map = {
        "BEGINNER": "Người mới",
        "BASIC": "Cơ bản",
        "MODERATE": "Trung bình",
        "ADVANCED": "Khó"
    }
    lines.append(f"Độ khó bài tập phù hợp: {difficulty_map.get(difficulty, difficulty)}")
    
    # Focus Areas
    focus_areas = health_analysis.get("focus_areas", [])
    if focus_areas:
        lines.append(f"Khu vực cần tập trung: {', '.join(focus_areas)}")
    
    return "\n".join(lines)
