"""Club-related helpers with embedding-based RAG pipeline."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from utils.clubs_client import clubs_client
from rag.club_rag import semantic_search
from services.llm_service import get_ai_response

MAX_CONTEXT_CLUBS = int(os.getenv("CLUB_CONTEXT_LIMIT", "4"))
RAG_SYSTEM_PROMPT = (
    "Bạn là AI Assistant của The New Gym với phong cách trò chuyện tự nhiên, thân thiện, giống như một tư vấn viên đang nói chuyện trực tiếp với khách. "
    "QUAN TRỌNG: BẠN PHẢI TUYỆT ĐỐI CHỈ sử dụng thông tin trong ngữ cảnh được cung cấp. "
    "TUYỆT ĐỐI KHÔNG được tự tạo, bịa đặt, hoặc suy đoán thông tin về chi nhánh, địa chỉ, tên, hoặc bất kỳ thông tin nào khác. "
    "Nếu ngữ cảnh không chứa thông tin về chi nhánh được hỏi, bạn PHẢI nói rõ 'Mình chưa tìm thấy chi nhánh nào ở [khu vực]' và KHÔNG được liệt kê các chi nhánh không có trong ngữ cảnh. "
    "Luôn trả lời bằng tiếng Việt, dùng đại từ thân mật (ví dụ: 'mình', 'bạn'), câu văn mềm mại, ngắn gọn, hạn chế lặp lại. "
    "Mỗi chi nhánh nên bao gồm tên (ưu tiên tiếng Việt), địa chỉ và link ở dạng [Tên](URL) - CHỈ khi thông tin này có trong ngữ cảnh."
)


def split_clubs_by_status(clubs: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    active = [club for club in clubs if club.get("isActive") == 1]
    inactive = [club for club in clubs if club.get("isActive") != 1]
    return active, inactive


def find_clubs_by_district(district_name: str, clubs: List[Dict]) -> List[Dict]:
    normalized_target = normalize_text(district_name)
    canonical = DISTRICT_ALIAS_MAP.get(district_name) or DISTRICT_ALIAS_MAP.get(normalized_target, district_name)
    simplified = normalize_text(canonical.replace("quận", "").replace("district", "").strip())

    results = []
    for club in clubs:
        club_district = club.get("district", {}).get("districtName", "")
        club_location = club.get("location", "")
        normalized_club_district = normalize_text(club_district)
        normalized_club_location = normalize_text(club_location)

        if (
            normalize_text(canonical) in normalized_club_district
            or (simplified and simplified in normalized_club_district)
            or normalize_text(canonical) in normalized_club_location
            or (simplified and simplified in normalized_club_location)
        ):
            results.append(club)
    return results


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
        "- Liệt kê tối đa 3 chi nhánh phù hợp nhất, mỗi chi nhánh gồm tên, địa chỉ, link (nếu có) - CHỈ khi thông tin này có trong ngữ cảnh.",
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
        f"LƯU Ý CUỐI CÙNG: Nếu câu hỏi về một khu vực cụ thể (ví dụ: Thủ Đức, Quận X) nhưng trong ngữ cảnh không có chi nhánh nào ở khu vực đó, bạn PHẢI trả lời 'Mình chưa tìm thấy chi nhánh nào ở [khu vực đó]' và KHÔNG được liệt kê các chi nhánh ở khu vực khác như thể chúng ở khu vực được hỏi."
    )
    messages = [{"role": "user", "content": prompt}]
    return get_ai_response(messages, RAG_SYSTEM_PROMPT)


def is_club_related_query(_: str) -> bool:
    """Dự án chỉ phục vụ thông tin chi nhánh → mọi câu đều xử lý bằng RAG."""
    return True


def search_clubs_by_keyword(message: str, clubs: List[Dict]) -> List[Dict]:
    """Tìm chi nhánh nếu từ khóa xuất hiện trực tiếp trong dữ liệu (không alias phức tạp)."""
    query = message.lower()
    if not query.strip():
        return []

    results: List[Dict] = []
    for club in clubs:
        fields = [
            club.get("nameVi") or "",
            club.get("nameEn") or "",
            club.get("location") or "",
            club.get("address") or "",
            club.get("district", {}).get("districtName", "") or "",
            club.get("city", {}).get("cityName", "") or "",
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
            results.append(club)
    return results


def generate_club_response(message: str) -> str:
    clubs = clubs_client.get_active_clubs()

    if not clubs:
        return "Xin lỗi, hiện chưa có dữ liệu về các chi nhánh trong hệ thống."

    keyword_matches = search_clubs_by_keyword(message, clubs)
    if keyword_matches:
        label = (
            keyword_matches[0].get("district", {}).get("districtName")
            or keyword_matches[0].get("city", {}).get("cityName")
            or message
        )
        contexts = build_context_from_clubs(keyword_matches)
        contexts.append(build_counts_context(label, keyword_matches))
        return generate_answer_from_context(
            message,
            contexts,
            extra_guidance="Nhấn mạnh đây là các chi nhánh khớp trực tiếp với nội dung người dùng vừa hỏi.",
        )

    semantic_results: List[Dict] = []
    try:
        semantic_results = semantic_search(message, top_k=MAX_CONTEXT_CLUBS)
    except Exception as exc:
        print(f"[ClubService] semantic_search failed: {exc}")

    if semantic_results:
        semantic_clubs = [item.get("raw") for item in semantic_results if item.get("raw")]
        if semantic_clubs:
            contexts = build_context_from_clubs(semantic_clubs)
            return generate_answer_from_context(message, contexts)

    overview_context = build_overall_context(clubs)
    no_data_message = build_no_data_message("khu vực bạn quan tâm", "city", clubs)
    return generate_answer_from_context(
        message,
        [overview_context, no_data_message],
        extra_guidance="Nếu khách cần cụ thể hơn, hãy đề nghị họ mô tả rõ khu vực hoặc tên chi nhánh.",
    )

