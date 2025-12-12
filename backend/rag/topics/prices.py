"""Topic configuration cho prices."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List

from rag.base_rag import TopicParser, TopicTextBuilder, TopicMetadataBuilder
from rag.unified_rag import register_topic

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PRICES_MD_PATH = BASE_DIR / "data" / "prices.md"
MAX_PRICES_TO_EMBED = int(os.getenv("PRICE_EMBED_LIMIT", "100"))


class PricesParser(TopicParser):
    """Parser cho prices từ markdown file."""

    def parse(self, source_path: Path, **kwargs) -> List[Dict[str, Any]]:
        """Parse prices từ file markdown."""
        if not source_path.exists():
            raise FileNotFoundError(f"File markdown không tồn tại: {source_path}")

        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()

        prices = []
        # Pattern để match mỗi Nhóm Chi Nhánh section: ## Nhóm Chi Nhánh X — ...
        pattern = r"## Nhóm Chi Nhánh (\d+) — (.+?)\n(.*?)(?=\n## Nhóm Chi Nhánh|\n## Ghi Chú Chung|\Z)"

        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            group_num = match.group(1)
            group_name = match.group(2).strip()
            group_content = match.group(3).strip()

            # Parse các field từ content
            price_data = {
                "id": int(group_num),
                "groupName": group_name,
                "branches": "",
                "area": "",
                "provinceBranches": "",
                "packages": [],
            }

            # Parse từng dòng
            for line in group_content.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Remove leading "- "
                if line.startswith("- "):
                    line = line[2:].strip()

                # Parse các field
                if line.startswith("Nhóm chi nhánh:"):
                    price_data["branches"] = line.replace("Nhóm chi nhánh:", "").strip()
                elif line.startswith("Khu vực:"):
                    price_data["area"] = line.replace("Khu vực:", "").strip()
                elif line.startswith("Chi nhánh tỉnh:"):
                    price_data["provinceBranches"] = line.replace("Chi nhánh tỉnh:", "").strip()
                elif line.startswith("Gói ") or line.startswith("Ưu đãi") or line.startswith("Giá trung bình"):
                    # Đây là thông tin về gói giá - lưu toàn bộ dòng
                    price_data["packages"].append(line)

            prices.append(price_data)

        # Parse Ghi Chú Chung
        notes_pattern = r"## Ghi Chú Chung\n(.*?)(?=\Z)"
        notes_match = re.search(notes_pattern, content, re.DOTALL)
        if notes_match:
            notes_content = notes_match.group(1).strip()
            notes = []
            for line in notes_content.split("\n"):
                line = line.strip()
                if line and line.startswith("- "):
                    notes.append(line[2:].strip())
            
            if notes:
                price_data = {
                    "id": 999,  # ID đặc biệt cho ghi chú
                    "groupName": "Ghi Chú Chung",
                    "notes": notes,
                }
                prices.append(price_data)

        # Tạo item tổng hợp về giá thấp nhất để dễ search
        all_packages = []
        for price_item in prices:
            if price_item.get("packages"):
                all_packages.extend(price_item["packages"])
        
        if all_packages:
            # Tìm giá thấp nhất
            min_price = None
            min_price_pkg = None
            for pkg in all_packages:
                if isinstance(pkg, str):
                    # Tìm số tiền trong text (format: 249.000 VNĐ hoặc 249000 VNĐ)
                    price_matches = re.findall(r'(\d+\.?\d*)\s*(?:\.)?\s*000\s*VNĐ', pkg)
                    if price_matches:
                        try:
                            price_value = float(price_matches[0].replace('.', ''))
                            if min_price is None or price_value < min_price:
                                min_price = price_value
                                min_price_pkg = pkg
                        except:
                            pass
            
            if min_price_pkg and min_price:
                summary_item = {
                    "id": 1000,  # ID đặc biệt cho tổng hợp
                    "groupName": "Tổng Hợp Giá",
                    "packages": [
                        f"Giá thấp nhất: {min_price_pkg}",
                        f"Giá gói tập thấp nhất của gym là {min_price_pkg}",
                        f"Gói tập rẻ nhất: {min_price_pkg}",
                        f"Để được tập ở gym, giá thấp nhất là {min_price_pkg}",
                    ],
                }
                prices.append(summary_item)

        return prices[:MAX_PRICES_TO_EMBED]


class PricesTextBuilder(TopicTextBuilder):
    """Text builder cho prices."""

    def build_text(self, item: Dict[str, Any]) -> str:
        """Xây dựng text chunk chi tiết từ price data."""
        parts = []

        # Tên nhóm
        group_name = item.get("groupName", "")
        if group_name:
            parts.append(f"Nhóm chi nhánh: {group_name}")

        # Chi nhánh
        branches = item.get("branches", "")
        if branches:
            parts.append(f"Chi nhánh: {branches}")

        # Khu vực
        area = item.get("area", "")
        if area:
            parts.append(f"Khu vực: {area}")

        # Chi nhánh tỉnh (nếu có)
        province_branches = item.get("provinceBranches", "")
        if province_branches:
            parts.append(f"Chi nhánh tỉnh: {province_branches}")

        # Các gói giá - format để dễ search
        packages = item.get("packages", [])
        if packages:
            parts.append("\nCác gói giá và giá cả:")
            min_price = None
            min_price_text = None
            for pkg in packages:
                if isinstance(pkg, str):
                    parts.append(f"- {pkg}")
                    # Extract giá để tìm giá thấp nhất
                    if "Giá" in pkg or "giá" in pkg:
                        # Tìm số tiền trong text
                        price_matches = re.findall(r'(\d+\.?\d*)\s*(?:\.)?\s*000\s*VNĐ', pkg)
                        if price_matches:
                            try:
                                price_value = float(price_matches[0].replace('.', ''))
                                if min_price is None or price_value < min_price:
                                    min_price = price_value
                                    min_price_text = pkg
                            except:
                                pass
                elif isinstance(pkg, dict):
                    description = pkg.get("description", "")
                    if description:
                        parts.append(f"- {description}")
            
            # Thêm thông tin về giá thấp nhất nếu tìm thấy
            if min_price_text and min_price:
                parts.append(f"\nGiá thấp nhất trong nhóm này: {min_price_text}")

        # Ghi chú (nếu có)
        notes = item.get("notes", [])
        if notes:
            parts.append("\nGhi chú:")
            for note in notes:
                parts.append(f"- {note}")

        # Thêm keywords để dễ search
        parts.append("\nTừ khóa: giá cả, gói tập, giá gói tập, giá thấp nhất, giá rẻ nhất, giá gói 1 tháng, giá gói 3 tháng, giá gói 6 tháng")

        return "\n".join(parts)


class PricesMetadataBuilder(TopicMetadataBuilder):
    """Metadata builder cho prices."""

    def build_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Xây dựng metadata từ price data."""
        return {
            "groupName": item.get("groupName", ""),
            "branches": item.get("branches", ""),
            "area": item.get("area", ""),
            "provinceBranches": item.get("provinceBranches", ""),
            "packageCount": len(item.get("packages", [])),
        }


def register_prices_topic():
    """Đăng ký prices topic vào unified RAG system."""
    register_topic(
        topic_name="prices",
        collection_name="price_documents",
        parser=PricesParser(),
        text_builder=PricesTextBuilder(),
        metadata_builder=PricesMetadataBuilder(),
        source_path=PRICES_MD_PATH,
        max_items=MAX_PRICES_TO_EMBED,
    )
