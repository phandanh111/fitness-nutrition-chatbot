"""Topic configuration cho clubs."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from rag.base_rag import TopicParser, TopicTextBuilder, TopicMetadataBuilder
from rag.unified_rag import register_topic

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CLUBS_MD_PATH = BASE_DIR / "data" / "clubs.md"
MAX_CLUBS_TO_EMBED = int(os.getenv("CLUB_EMBED_LIMIT", "2000"))


class ClubsParser(TopicParser):
    """Parser cho clubs từ markdown file."""

    def parse(self, source_path: Path, **kwargs) -> List[Dict[str, Any]]:
        """Parse clubs từ file markdown."""
        source = kwargs.get("source", "markdown")
        
        if source == "markdown":
            return self._parse_from_markdown(source_path)
        else:
            # Fallback về API nếu cần
            from utils.clubs_client import clubs_client
            force_refresh = kwargs.get("force_refresh", False)
            clubs = clubs_client.get_active_clubs(use_cache=not force_refresh)
            return clubs[:MAX_CLUBS_TO_EMBED]

    def _parse_from_markdown(self, md_path: Path) -> List[Dict]:
        """Parse clubs từ file markdown."""
        if not md_path.exists():
            raise FileNotFoundError(f"File markdown không tồn tại: {md_path}")

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        clubs = []
        # Pattern để match mỗi CLB section: ## CLB X — Name (ID)
        pattern = r"## CLB (\d+) — (.+?) \(([A-Z0-9]+)\)\n(.*?)(?=\n## CLB|\Z)"

        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            club_num = match.group(1)
            club_name = match.group(2).strip()
            club_id = match.group(3).strip()
            club_content = match.group(4).strip()

            # Parse các field từ content
            club_data = {
                "id": int(club_num),
                "key": club_id,
                "nameVi": "",
                "nameEn": "",
                "address": "",
                "location": "",
                "openDate": "",
                "isActive": 0,
                "informationUrl": "",
                "latitude": None,
                "longitude": None,
                "city": {},
                "district": {},
            }

            # Parse từng dòng
            for line in club_content.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Remove leading "- "
                if line.startswith("- "):
                    line = line[2:].strip()

                # Parse các field
                if line.startswith("Tên tiếng Việt:"):
                    club_data["nameVi"] = line.replace("Tên tiếng Việt:", "").strip()
                elif line.startswith("Tên tiếng Anh:"):
                    club_data["nameEn"] = line.replace("Tên tiếng Anh:", "").strip()
                elif line.startswith("Địa chỉ:"):
                    address = line.replace("Địa chỉ:", "").strip()
                    club_data["address"] = address
                    club_data["location"] = address
                elif line.startswith("Ngày mở:"):
                    date_str = line.replace("Ngày mở:", "").strip()
                    # Convert DD/MM/YYYY to ISO format
                    if "/" in date_str:
                        parts = date_str.split("/")
                        if len(parts) == 3:
                            club_data["openDate"] = f"{parts[2]}-{parts[1]}-{parts[0]}T00:00:00.000Z"
                elif line.startswith("Hoạt động:"):
                    is_active = line.replace("Hoạt động:", "").strip().lower()
                    club_data["isActive"] = 1 if is_active == "có" else 0
                elif line.startswith("Website:"):
                    club_data["informationUrl"] = line.replace("Website:", "").strip()
                elif line.startswith("Tọa độ:"):
                    coords = line.replace("Tọa độ:", "").strip()
                    if coords and coords != "Không có":
                        try:
                            lat, lon = map(float, coords.split(","))
                            club_data["latitude"] = lat
                            club_data["longitude"] = lon
                        except:
                            pass

            # Parse city và district từ địa chỉ
            if club_data["address"]:
                # Format: "địa chỉ, quận/huyện, thành phố, Việt Nam"
                parts = [p.strip() for p in club_data["address"].split(",")]
                if len(parts) >= 3:
                    district_name = parts[-3] if len(parts) >= 3 else ""
                    city_name = parts[-2] if len(parts) >= 2 else ""

                    if district_name:
                        club_data["district"] = {"districtName": district_name}
                    if city_name:
                        club_data["city"] = {"cityName": city_name}

            clubs.append(club_data)

        # Lọc chỉ lấy clubs đang hoạt động
        clubs = [c for c in clubs if c.get("isActive") == 1][:MAX_CLUBS_TO_EMBED]
        return clubs


class ClubsTextBuilder(TopicTextBuilder):
    """Text builder cho clubs."""

    def build_text(self, item: Dict[str, Any]) -> str:
        """Xây dựng text chunk chi tiết từ club data."""
        # Lấy thông tin cơ bản
        name_vi = item.get("nameVi", "")
        name_en = item.get("nameEn", "")
        location = item.get("location", "") or item.get("address", "")

        # Thông tin địa lý
        city = ""
        district = ""
        if isinstance(item.get("city"), dict):
            city = item.get("city", {}).get("cityName", "")
        elif isinstance(item.get("city"), str):
            city = item.get("city", "")

        if isinstance(item.get("district"), dict):
            district = item.get("district", {}).get("districtName", "")
        elif isinstance(item.get("district"), str):
            district = item.get("district", "")

        # Thông tin khác
        info_url = item.get("informationUrl", "")

        # Xây dựng text chunk
        parts = []

        # Tên chi nhánh (ưu tiên tiếng Việt)
        if name_vi:
            parts.append(f"Chi nhánh: {name_vi}")
            if name_en and name_en != name_vi:
                parts.append(f"Tên tiếng Anh: {name_en}")
        elif name_en:
            parts.append(f"Chi nhánh: {name_en}")

        # Địa chỉ đầy đủ
        if location:
            parts.append(f"Địa chỉ: {location}")

        # Thông tin địa lý chi tiết
        location_parts = []
        if district:
            location_parts.append(district)
        if city:
            location_parts.append(city)

        if location_parts:
            parts.append(f"Khu vực: {', '.join(location_parts)}")

        # Link thông tin
        if info_url:
            parts.append(f"Trang web: {info_url}")

        # Thông tin bổ sung (tọa độ, ngày mở cửa)
        if item.get("latitude") and item.get("longitude"):
            parts.append(f"Tọa độ: {item.get('latitude')}, {item.get('longitude')}")

        if item.get("openDate"):
            parts.append(f"Ngày mở cửa: {item.get('openDate')}")

        # Trạng thái
        is_active = item.get("isActive", 0)
        status = "Đang hoạt động" if is_active == 1 else "Tạm đóng"
        parts.append(f"Trạng thái: {status}")

        return "\n".join(parts)


class ClubsMetadataBuilder(TopicMetadataBuilder):
    """Metadata builder cho clubs."""

    def build_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Xây dựng metadata từ club data."""
        city_name = ""
        district_name = ""
        if isinstance(item.get("city"), dict):
            city_name = item.get("city", {}).get("cityName", "")
        if isinstance(item.get("district"), dict):
            district_name = item.get("district", {}).get("districtName", "")

        return {
            "name": item.get("nameVi") or item.get("nameEn"),
            "city": city_name,
            "district": district_name,
            "link": item.get("informationUrl"),
        }


def register_clubs_topic():
    """Đăng ký clubs topic vào unified RAG system."""
    register_topic(
        topic_name="clubs",
        collection_name="club_documents",
        parser=ClubsParser(),
        text_builder=ClubsTextBuilder(),
        metadata_builder=ClubsMetadataBuilder(),
        source_path=CLUBS_MD_PATH,
        max_items=MAX_CLUBS_TO_EMBED,
    )

