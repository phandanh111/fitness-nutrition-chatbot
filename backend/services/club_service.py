"""Club-related helpers with embedding-based RAG pipeline."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

from utils.clubs_client import clubs_client
from rag.club_rag import semantic_search
from services.llm_service import get_ai_response
from constants.rag_prompts import get_rag_system_prompt

MAX_CONTEXT_CLUBS = int(os.getenv("CLUB_CONTEXT_LIMIT", "4"))

COUNT_QUERY_PATTERNS = [
    r"bao nhiêu",
    r"tổng\\s*(cộng)?",
    r"có\\s*mấy",
    r"tổng số",
    r"bao nhiêu (club|chi nhánh|phòng)",
    r"mấy chi nhánh",
]


def split_clubs_by_status(clubs: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    active = [club for club in clubs if club.get("isActive") == 1]
    inactive = [club for club in clubs if club.get("isActive") != 1]
    return active, inactive


def build_context_from_clubs(clubs: List[Dict]) -> List[str]:
    contexts: List[str] = []
    for club in clubs[:MAX_CONTEXT_CLUBS]:
        name = club.get("nameVi") or club.get("nameEn") or "Chi nhánh"
        location = club.get("location") or club.get("address") or ""
        district = club.get("district", {}).get("districtName")
        city = club.get("city", {}).get("cityName")
        link = club.get("informationUrl")

        lines = [f"Tên: {name}"]
        if location:
            lines.append(f"Địa chỉ: {location}")
        if district:
            lines.append(f"Quận/Huyện: {district}")
        if city:
            lines.append(f"Thành phố: {city}")
        if link:
            lines.append(f"Link: {link}")
        contexts.append("\n".join(lines))
    return contexts


def build_counts_context(label: str, clubs: List[Dict]) -> str:
    active_clubs, inactive_clubs = split_clubs_by_status(clubs)
    lines = [
        f"Tổng quan khu vực {label}:",
        f"- Chi nhánh đang hoạt động: {len(active_clubs)}",
    ]
    if inactive_clubs:
        lines.append(f"- Chi nhánh tạm đóng: {len(inactive_clubs)}")
    return "\n".join(lines)


def build_overall_context(clubs: List[Dict]) -> str:
    if not clubs:
        return "Hệ thống chưa có dữ liệu chi nhánh."

    city_groups: Dict[str, List[Dict]] = {}
    for club in clubs:
        city = club.get("city", {}).get("cityName", "Không xác định")
        city_groups.setdefault(city, []).append(club)

    lines = ["Tổng quan số chi nhánh đang hoạt động theo tỉnh/thành:"]
    for city_name, city_clubs in sorted(city_groups.items()):
        active, _ = split_clubs_by_status(city_clubs)
        if active:
            lines.append(f"- {city_name}: {len(active)} chi nhánh hoạt động")
    return "\n".join(lines)


def build_total_counts_context(clubs: List[Dict]) -> str:
    active_clubs, inactive_clubs = split_clubs_by_status(clubs)
    lines = [
        f"Tổng số chi nhánh đang hoạt động: {len(active_clubs)}",
    ]
    if inactive_clubs:
        lines.append(f"Tổng số chi nhánh tạm đóng: {len(inactive_clubs)}")
    lines.append("Dữ liệu này được tính trực tiếp từ file clubs.md.")
    return "\n".join(lines)


def is_count_query(message: str) -> bool:
    lower = message.lower()
    return any(re.search(pattern, lower) for pattern in COUNT_QUERY_PATTERNS)


def build_no_data_message(label: str, level: str, clubs: List[Dict]) -> str:
    active_clubs = [club for club in clubs if club.get("isActive") == 1]
    if not active_clubs:
        return f"Mình chưa tìm thấy chi nhánh nào ở {label}. Hệ thống hiện chưa có dữ liệu chi nhánh đang hoạt động."

    key_name = "district" if level == "district" else "city"
    area_groups: Dict[str, List[Dict]] = {}
    for club in active_clubs:
        area = club.get(key_name, {}).get(f"{key_name}Name")
        fallback_area = club.get("city", {}).get("cityName") if key_name == "district" else area
        normalized_area = area or fallback_area or "Khu vực khác"
        if normalized_area == label:
            continue
        area_groups.setdefault(normalized_area, []).append(club)

    if not area_groups:
        area_groups["Khu vực khác"] = active_clubs

    sorted_areas = sorted(area_groups.items(), key=lambda item: len(item[1]), reverse=True)
    suggested_clubs: List[Dict] = []
    for _, area_clubs in sorted_areas:
        for club in area_clubs:
            suggested_clubs.append(club)
            if len(suggested_clubs) >= 3:
                break
        if len(suggested_clubs) >= 3:
            break

    def format_club_line(club: Dict) -> str:
        name = club.get("nameVi") or club.get("nameEn") or "Chi nhánh"
        link = club.get("informationUrl")
        location = club.get("location") or club.get("address") or ""
        display_name = f"[{name}]({link})" if link else name
        return f"- {display_name}" + (f" – {location}" if location else "")

    lines = [
        f"Mình chưa tìm thấy chi nhánh nào ở {label}.",
        "Bạn có thể tham khảo một số chi nhánh đang hoạt động gần khu vực khác:",
    ]
    lines.extend(format_club_line(club) for club in suggested_clubs)
    return "\n".join(lines)


def generate_answer_from_context(question: str, context_blocks: List[str], extra_guidance: Optional[str] = None) -> str:
    if not context_blocks:
        return "Xin lỗi, mình chưa tìm thấy thông tin phù hợp trong dữ liệu hiện có."

    context_text = "\n\n".join(f"[Đoạn {idx}] {block}" for idx, block in enumerate(context_blocks, 1))
    guidance_lines = [
        "QUAN TRỌNG: BẠN PHẢI TUYỆT ĐỐI CHỈ sử dụng thông tin trong các đoạn ngữ cảnh bên trên.",
        "TUYỆT ĐỐI KHÔNG được tự tạo, bịa đặt, hoặc suy đoán thông tin về chi nhánh, địa chỉ, tên, hoặc bất kỳ thông tin nào khác.",
        "Nếu ngữ cảnh không chứa thông tin về chi nhánh được hỏi, bạn PHẢI nói rõ 'Mình chưa tìm thấy chi nhánh nào ở [khu vực]' và KHÔNG được liệt kê các chi nhánh không có trong ngữ cảnh.",
        "TUYỆT ĐỐI KHÔNG được tự động gợi ý các chi nhánh hoặc bài tập nếu câu hỏi không liên quan đến thông tin trong ngữ cảnh.",
        "Nếu câu hỏi về giờ mở cửa, giá cả, dịch vụ, hoặc thông tin khác không có trong ngữ cảnh, bạn PHẢI thừa nhận rằng mình không có thông tin và đề nghị liên hệ trực tiếp với The New Gym.",
        "- Liệt kê tối đa 3 chi nhánh phù hợp nhất, mỗi chi nhánh gồm tên, địa chỉ, link (nếu có) - CHỈ khi thông tin này có trong ngữ cảnh VÀ liên quan trực tiếp đến câu hỏi.",
        "- Dùng Markdown để hiển thị link dạng [Tên](URL).",
        "- Nếu chỉ có 1 chi nhánh phù hợp thì CHỈ nêu chi nhánh đó, KHÔNG thêm câu như 'không có chi nhánh nào khác'.",
        "- Giữ giọng điệu mềm mại, gần gũi, dùng đại từ 'mình'/'bạn', tránh nhắc lặp lại cùng một câu.",
    ]
    if extra_guidance:
        guidance_lines.append(f"- {extra_guidance}")

    prompt = (
        f"Ngữ cảnh:\n{context_text}\n\n"
        f"Hướng dẫn:\n" + "\n".join(guidance_lines) + "\n\n"
        f"Câu hỏi của khách: {question}\n\n"
        f"LƯU Ý CUỐI CÙNG: Nếu câu hỏi về một khu vực cụ thể (ví dụ: Thủ Đức, Quận X) nhưng trong ngữ cảnh không có chi nhánh nào ở khu vực đó, bạn PHẢI trả lời 'Mình chưa tìm thấy chi nhánh nào ở [khu vực đó]' và KHÔNG được liệt kê các chi nhánh ở khu vực khác như thể chúng ở khu vực được hỏi. "
        f"Nếu câu hỏi KHÔNG liên quan đến thông tin chi nhánh trong ngữ cảnh (ví dụ: giờ mở cửa, giá cả, dịch vụ), bạn PHẢI trả lời trực tiếp về câu hỏi đó và KHÔNG được tự động gợi ý các chi nhánh hoặc bài tập."
    )
    messages = [{"role": "user", "content": prompt}]
    return get_ai_response(messages, get_rag_system_prompt("clubs"))


def is_club_related_query(message: str) -> bool:
    """Phát hiện câu hỏi về chi nhánh/clubs bằng semantic search."""
    try:
        from utils.query_classifier import is_club_query
        return is_club_query(message)
    except Exception as e:
        print(f"[ClubService] Error in is_club_related_query: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_club_response(message: str) -> str:
    clubs = clubs_client.get_active_clubs()

    if not clubs:
        return "Xin lỗi, hiện chưa có dữ liệu về các chi nhánh trong hệ thống."

    if is_count_query(message):
        total_context = build_total_counts_context(clubs)
        overview_context = build_overall_context(clubs)
        return generate_answer_from_context(
            message,
            [total_context, overview_context],
            extra_guidance="Trả lời rõ ràng tổng số chi nhánh đang hoạt động và phân bố theo khu vực.",
        )

    # Chỉ dùng semantic search, không dùng keyword matching
    semantic_results: List[Dict] = []
    try:
        semantic_results = semantic_search(message, top_k=MAX_CONTEXT_CLUBS)
    except Exception as exc:
        print(f"[ClubService] semantic_search failed: {exc}")
        import traceback
        traceback.print_exc()

    # Chỉ sử dụng kết quả nếu score tốt (score < 0.85 nghĩa là tương đồng tốt)
    # Score trong ChromaDB là distance (cosine distance), càng nhỏ càng tốt
    SEMANTIC_SCORE_THRESHOLD = 0.85
    if semantic_results:
        # Lọc các kết quả có score tốt (score < threshold)
        good_results = [
            item for item in semantic_results 
            if item.get("score") is not None and item.get("score") < SEMANTIC_SCORE_THRESHOLD
        ]
        
        if good_results:
            semantic_clubs = [item.get("raw") for item in good_results if item.get("raw")]
            if semantic_clubs:
                contexts = build_context_from_clubs(semantic_clubs)
                contexts.append(build_overall_context(clubs))
                return generate_answer_from_context(message, contexts)

    # Nếu không tìm thấy kết quả semantic search phù hợp (score quá cao = không tương đồng)
    # Trả về thông báo chung - không dùng keyword check, hoàn toàn dựa vào vector similarity
    return "Xin lỗi, mình chưa tìm thấy thông tin phù hợp về câu hỏi này trong hệ thống. Bạn có thể mô tả cụ thể hơn về chi nhánh hoặc khu vực bạn quan tâm không?"

