"""Club-related helpers with embedding-based RAG pipeline."""

from __future__ import annotations

import os
import unicodedata
from typing import Dict, List, Optional, Tuple

from constants.clubs import (
    RAW_CITY_ALIAS_PAIRS,
    RAW_DISTRICT_ALIAS_PAIRS,
    COUNT_KEYWORDS,
    ACTIVE_KEYWORDS,
    INACTIVE_KEYWORDS,
    ADDRESS_KEYWORDS,
)
from utils.clubs_client import clubs_client
from rag.club_rag import semantic_search
from services.llm_service import get_ai_response

CityAliasMap = Dict[str, str]
DistrictAliasMap = Dict[str, str]

MAX_CONTEXT_CLUBS = int(os.getenv("CLUB_CONTEXT_LIMIT", "4"))
RAG_SYSTEM_PROMPT = (
    "Bạn là AI Assistant của The New Gym. "
    "Chỉ trả lời dựa trên ngữ cảnh cung cấp, không tự suy đoán thêm. "
    "Luôn trả lời bằng tiếng Việt, giọng thân thiện, mạch lạc. "
    "Mỗi chi nhánh nên bao gồm tên (ưu tiên tiếng Việt), địa chỉ và link ở dạng [Tên](URL). "
    "Nếu không tìm thấy thông tin phù hợp trong ngữ cảnh, hãy nói rõ và gợi ý khách cung cấp thêm dữ liệu."
)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _build_alias_map(pairs: List[Tuple[str, List[str]]]) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    for canonical, aliases in pairs:
        for alias in aliases:
            alias_map[alias] = canonical
            alias_map[normalize_text(alias)] = canonical
    return alias_map


CITY_ALIAS_MAP: CityAliasMap = _build_alias_map(RAW_CITY_ALIAS_PAIRS)
DISTRICT_ALIAS_MAP: DistrictAliasMap = _build_alias_map(RAW_DISTRICT_ALIAS_PAIRS)


def detect_city_from_message(message: str) -> Optional[str]:
    normalized = normalize_text(message)
    sorted_aliases = sorted(CITY_ALIAS_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for alias, city in sorted_aliases:
        if normalize_text(alias) in normalized:
            return city
    return None


def detect_district_from_message(message: str) -> Optional[str]:
    normalized = normalize_text(message)
    sorted_aliases = sorted(DISTRICT_ALIAS_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for alias, canonical in sorted_aliases:
        if normalize_text(alias) in normalized:
            return canonical
    return None


def find_club_by_name(message: str, clubs: List[Dict]) -> Optional[Dict]:
    normalized = normalize_text(message)
    for club in clubs:
        name_vi = normalize_text(club.get("nameVi", ""))
        name_en = normalize_text(club.get("nameEn", ""))
        if name_vi and name_vi in normalized:
            return club
        if name_en and name_en in normalized:
            return club
    return None


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
    suggestions: Dict[str, int] = {}
    key_name = "district" if level == "district" else "city"
    for club in clubs:
        area = club.get(key_name, {}).get(f"{key_name}Name", "")
        if not area or area == label:
            continue
        suggestions[area] = suggestions.get(area, 0) + 1

    if suggestions:
        top_suggestions = sorted(suggestions.items(), key=lambda x: x[1], reverse=True)[:3]
        lines = [
            f"Mình chưa tìm thấy chi nhánh nào ở {label}.",
            "Các khu vực lân cận đang có chi nhánh:",
        ]
        for area, count in top_suggestions:
            lines.append(f"- {area}: {count} chi nhánh đang hoạt động")
        return "\n".join(lines)
    return f"Mình chưa tìm thấy chi nhánh nào ở {label}. Bạn muốn mình gợi ý khu vực khác không?"


def generate_answer_from_context(question: str, context_blocks: List[str], extra_guidance: Optional[str] = None) -> str:
    if not context_blocks:
        return "Xin lỗi, mình chưa tìm thấy thông tin phù hợp trong dữ liệu hiện có."

    context_text = "\n\n".join(f"[Đoạn {idx}] {block}" for idx, block in enumerate(context_blocks, 1))
    guidance_lines = [
        "- Chỉ sử dụng thông tin trong các đoạn ngữ cảnh.",
        "- Liệt kê tối đa 3 chi nhánh phù hợp nhất, mỗi chi nhánh gồm tên, địa chỉ, link (nếu có).",
        "- Dùng Markdown để hiển thị link dạng [Xem thêm](URL).",
    ]
    if extra_guidance:
        guidance_lines.append(f"- {extra_guidance}")

    prompt = (
        f"Ngữ cảnh:\n{context_text}\n\n"
        f"Hướng dẫn:\n" + "\n".join(guidance_lines) + "\n\n"
        f"Câu hỏi của khách: {question}"
    )
    messages = [{"role": "user", "content": prompt}]
    return get_ai_response(messages, RAG_SYSTEM_PROMPT)


def is_club_related_query(message: str) -> bool:
    message_lower = message.lower()
    club_keywords = [
        "club",
        "phòng gym",
        "chi nhánh",
        "địa điểm",
        "cơ sở",
        "gym ở",
        "phòng tập ở",
        "địa chỉ",
        "ở đâu",
        "quận",
        "thành phố",
        "hcm",
        "hồ chí minh",
        "tphcm",
        "tp.hcm",
        "đà nẵng",
        "cần thơ",
        "biên hòa",
        "vũng tàu",
        "long xuyên",
        "hậu giang",
        "đồng nai",
        "an giang",
        "bà rịa vũng tàu",
        "hoàng văn thụ",
        "âu cơ",
        "quang trung",
        "điện biên phủ",
        "nguyễn chí thanh",
        "nguyễn thị thập",
        "ung văn khiêm",
        "nguyễn ái quốc",
        "trần hưng đạo",
        "hoàng diệu",
        "phan đăng lưu",
        "nam kỳ khởi nghĩa",
        "lý thường kiệt",
        "bao nhiêu",
        "có mấy",
        "danh sách",
        "liệt kê",
    ]
    has_club_keyword = any(keyword in message_lower for keyword in club_keywords)
    has_count_query = any(word in message_lower for word in ["bao nhiêu", "có mấy", "có bao nhiêu"]) and any(
        word in message_lower for word in ["gym", "phòng", "club", "chi nhánh", "cơ sở", "địa điểm"]
    )
    return has_club_keyword or has_count_query


def generate_club_response(message: str) -> str:
    normalized_initial = normalize_text(message)
    wants_inactive_initial = any(keyword in normalized_initial for keyword in INACTIVE_KEYWORDS)
    all_clubs = clubs_client.fetch_clubs()
    clubs = all_clubs if wants_inactive_initial else clubs_client.get_active_clubs()

    if not clubs:
        return "Xin lỗi, hiện chưa có dữ liệu về các chi nhánh trong hệ thống."

    normalized = normalize_text(message)
    is_count_query = any(keyword in normalized for keyword in COUNT_KEYWORDS)

    club = find_club_by_name(message, all_clubs)
    if club:
        context_blocks = build_context_from_clubs([club])
        return generate_answer_from_context(message, context_blocks)

    requested_district = detect_district_from_message(message)
    if requested_district:
        district_clubs = find_clubs_by_district(requested_district, clubs)
        if district_clubs:
            contexts = build_context_from_clubs(district_clubs)
            contexts.append(build_counts_context(requested_district, district_clubs))
            return generate_answer_from_context(message, contexts)
        return build_no_data_message(requested_district, "district", clubs)

    requested_city = detect_city_from_message(message)
    if requested_city:
        city_clubs = []
        target_norm = normalize_text(requested_city)
        for club in clubs:
            club_city = club.get("city", {}).get("cityName", "")
            club_location = club.get("location", "")
            if normalize_text(club_city) == target_norm or target_norm in normalize_text(club_location):
                city_clubs.append(club)
        if city_clubs:
            contexts = build_context_from_clubs(city_clubs)
            contexts.append(build_counts_context(requested_city, city_clubs))
            return generate_answer_from_context(message, contexts)
        return build_no_data_message(requested_city, "city", clubs)

    if is_count_query:
        overview_context = build_overall_context(clubs)
        return generate_answer_from_context(message, [overview_context], extra_guidance="Nhấn mạnh số lượng theo từng khu vực.")

    semantic_results = semantic_search(message, top_k=MAX_CONTEXT_CLUBS)
    if semantic_results:
        semantic_clubs = [item.get("raw") for item in semantic_results if item.get("raw")]
        contexts = build_context_from_clubs(semantic_clubs)
        return generate_answer_from_context(message, contexts)

    if any(keyword in normalized for keyword in ADDRESS_KEYWORDS):
        return (
            "Bạn muốn biết địa chỉ của chi nhánh nào ạ?\n\n"
            "Bạn có thể cung cấp:\n"
            "- Tên chi nhánh (ví dụ: Hoàng Văn Thụ, Nguyễn Chí Thanh)\n"
            "- Hoặc khu vực mong muốn (ví dụ: Quận 3, Tân Bình, Gò Vấp)\n"
            "- Hoặc thành phố (ví dụ: Hồ Chí Minh, Đà Nẵng)"
        )

    overview_context = build_overall_context(clubs)
    return generate_answer_from_context(message, [overview_context], extra_guidance="Nếu khách cần chi tiết hơn, hãy gợi ý họ nêu rõ khu vực.")

