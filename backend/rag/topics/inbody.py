"""Topic configuration cho inbody."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, List

from rag.base_rag import TopicParser, TopicTextBuilder, TopicMetadataBuilder
from rag.unified_rag import register_topic

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INBODY_MD_PATH = BASE_DIR / "data" / "inbody.md"
MAX_INBODY_TO_EMBED = int(os.getenv("INBODY_EMBED_LIMIT", "10"))


class InBodyParser(TopicParser):
    """Parser cho InBody từ JSON file."""

    def parse(self, source_path: Path, **kwargs) -> List[Dict[str, Any]]:
        """Parse InBody data từ file JSON."""
        if not source_path.exists():
            raise FileNotFoundError(f"File InBody không tồn tại: {source_path}")

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            # Parse JSON
            inbody_data = json.loads(content)
            
            # Kiểm tra xem có phải InBody data không
            if not ("composition" in inbody_data or "inbody_info" in inbody_data or "muscle_fat" in inbody_data):
                raise ValueError("File không chứa InBody data hợp lệ")
            
            # Trả về list với 1 item (InBody data)
            # Mỗi item sẽ được chia thành các chunks khác nhau để embedding
            return [inbody_data]
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Lỗi parse JSON từ file: {e}")
        except Exception as e:
            raise ValueError(f"Lỗi đọc file: {e}")


class InBodyTextBuilder(TopicTextBuilder):
    """Text builder cho InBody - chia thành nhiều chunks để dễ search."""

    def build_text(self, item: Dict[str, Any]) -> str:
        """Xây dựng text chunk từ InBody data."""
        parts = []
        
        # Thông tin cá nhân
        inbody_info = item.get("inbody_info", {})
        if inbody_info:
            age = inbody_info.get("age", "")
            gender = inbody_info.get("gender", "")
            height = inbody_info.get("height", "")
            if age or gender or height:
                info_parts = []
                if age:
                    info_parts.append(f"Tuổi: {age}")
                if gender:
                    info_parts.append(f"Giới tính: {gender}")
                if height:
                    info_parts.append(f"Chiều cao: {height} cm")
                parts.append("Thông tin cá nhân: " + ", ".join(info_parts))
        
        # Composition (thành phần cơ thể)
        composition = item.get("composition", {})
        if composition:
            weight = composition.get("weight", "")
            fat = composition.get("fat", "")
            protein = composition.get("protein", "")
            water = composition.get("water", "")
            mineral = composition.get("mineral", "")
            
            comp_parts = []
            if weight:
                comp_parts.append(f"Cân nặng: {weight} kg")
            if fat:
                comp_parts.append(f"Mỡ: {fat} kg")
            if protein:
                comp_parts.append(f"Protein: {protein} kg")
            if water:
                comp_parts.append(f"Nước: {water} kg")
            if mineral:
                comp_parts.append(f"Khoáng chất: {mineral} kg")
            
            if comp_parts:
                parts.append("Thành phần cơ thể: " + ", ".join(comp_parts))
        
        # Muscle & Fat
        muscle_fat = item.get("muscle_fat", {})
        if muscle_fat:
            fat_mass = muscle_fat.get("fat_mass", "")
            smm = muscle_fat.get("smm", "")  # Skeletal Muscle Mass
            weight = muscle_fat.get("weight", "")
            
            mf_parts = []
            if fat_mass:
                mf_parts.append(f"Khối lượng mỡ: {fat_mass} kg")
            if smm:
                mf_parts.append(f"Khối lượng cơ xương (SMM): {smm} kg")
            if weight:
                mf_parts.append(f"Cân nặng: {weight} kg")
            
            if mf_parts:
                parts.append("Mỡ và cơ: " + ", ".join(mf_parts))
        
        # Obesity (BMI, Body Fat %)
        obesity = item.get("obesity", {})
        if obesity:
            bmi = obesity.get("bmi", "")
            pbf = obesity.get("pbf", "")  # Percent Body Fat
            
            obesity_parts = []
            if bmi:
                bmi_status = ""
                try:
                    bmi_val = float(bmi)
                    if bmi_val < 18.5:
                        bmi_status = " (Thiếu cân)"
                    elif bmi_val >= 18.5 and bmi_val < 25:
                        bmi_status = " (Bình thường)"
                    elif bmi_val >= 25 and bmi_val < 30:
                        bmi_status = " (Thừa cân)"
                    else:
                        bmi_status = " (Béo phì)"
                except:
                    pass
                obesity_parts.append(f"BMI: {bmi}{bmi_status}")
            if pbf:
                obesity_parts.append(f"Tỷ lệ mỡ cơ thể (PBF): {pbf}%")
            
            if obesity_parts:
                parts.append("Chỉ số béo phì: " + ", ".join(obesity_parts))
        
        # Score
        score = item.get("score", {})
        if score:
            overall_score = score.get("score", "")
            if overall_score:
                parts.append(f"Điểm tổng thể: {overall_score}/100")
        
        # Segmental Fat (mỡ theo từng phần)
        segmental_fat = item.get("segmental_fat", {})
        if segmental_fat:
            trunk_status = segmental_fat.get("trunk_status", "")
            if trunk_status and trunk_status.lower() == "over":
                parts.append("Mỡ vùng bụng/trunk: Cao (Over)")
        
        # Segmental Lean (cơ theo từng phần)
        segmental_lean = item.get("segmental_lean", {})
        if segmental_lean:
            # Tìm các phần có status "Low" hoặc "Under"
            low_parts = []
            for key, value in segmental_lean.items():
                if key.endswith("_status") and isinstance(value, str):
                    status_lower = value.lower()
                    if status_lower in ["low", "under"]:
                        part = key.replace("_status", "").replace("_", " ").title()
                        low_parts.append(part)
            
            if low_parts:
                parts.append(f"Khu vực cơ thấp: {', '.join(low_parts)}")
        
        # Thêm keywords để dễ search
        parts.append("\nTừ khóa: InBody, phân tích InBody, tình trạng sức khỏe, đánh giá sức khỏe, body composition, thành phần cơ thể, BMI, tỷ lệ mỡ, khối lượng cơ")
        
        return "\n".join(parts)


class InBodyMetadataBuilder(TopicMetadataBuilder):
    """Metadata builder cho InBody."""

    def build_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Xây dựng metadata từ InBody data."""
        inbody_info = item.get("inbody_info", {})
        obesity = item.get("obesity", {})
        score = item.get("score", {})
        muscle_fat = item.get("muscle_fat", {})
        
        return {
            "age": inbody_info.get("age", ""),
            "gender": inbody_info.get("gender", ""),
            "height": inbody_info.get("height", ""),
            "bmi": obesity.get("bmi", ""),
            "pbf": obesity.get("pbf", ""),  # Percent Body Fat
            "score": score.get("score", ""),
            "smm": muscle_fat.get("smm", ""),  # Skeletal Muscle Mass
            "weight": muscle_fat.get("weight", "") or item.get("composition", {}).get("weight", ""),
        }


def register_inbody_topic():
    """Đăng ký inbody topic vào unified RAG system."""
    register_topic(
        topic_name="inbody",
        collection_name="inbody_documents",
        parser=InBodyParser(),
        text_builder=InBodyTextBuilder(),
        metadata_builder=InBodyMetadataBuilder(),
        source_path=INBODY_MD_PATH,
        max_items=MAX_INBODY_TO_EMBED,
    )
