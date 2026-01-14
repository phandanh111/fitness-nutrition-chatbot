"""Chuẩn hóa InBody data thành User Signals cho Rule Engine."""

from __future__ import annotations

from typing import Dict, Optional, Any, Literal

# User Signal Types
BMIStatus = Literal["UNDERWEIGHT", "NORMAL", "OVERWEIGHT", "OBESE", "UNKNOWN"]
BodyFatStatus = Literal["LOW", "NORMAL", "HIGH", "UNKNOWN"]
MuscleStatus = Literal["LOW", "NORMAL", "HIGH", "UNKNOWN"]


class UserSignals:
    """User Signals đã chuẩn hóa từ InBody data."""

    def __init__(
        self,
        bmi_status: BMIStatus = "UNKNOWN",
        body_fat_status: BodyFatStatus = "UNKNOWN",
        muscle_status: MuscleStatus = "UNKNOWN",
        central_fat: bool = False,
    ):
        self.bmi_status = bmi_status
        self.body_fat_status = body_fat_status
        self.muscle_status = muscle_status
        self.central_fat = central_fat

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành dict để dễ debug."""
        return {
            "bmi_status": self.bmi_status,
            "body_fat_status": self.body_fat_status,
            "muscle_status": self.muscle_status,
            "central_fat": self.central_fat,
        }

    def __repr__(self) -> str:
        return f"UserSignals({self.to_dict()})"


def normalize_inbody_data(inbody_data: Optional[Dict[str, Any]]) -> UserSignals:
    """
    Chuẩn hóa InBody data thành User Signals.
    
    Args:
        inbody_data: InBody data dict từ conversation_service hoặc parse từ message
        
    Returns:
        UserSignals object với các signals đã chuẩn hóa
    """
    if not inbody_data:
        return UserSignals()

    # Tính BMI
    bmi = _compute_bmi_from_inbody(inbody_data)
    bmi_status = _classify_bmi_status(bmi)

    # Phân loại Body Fat Status
    body_fat_status = _classify_body_fat_status(inbody_data)

    # Phân loại Muscle Status
    muscle_status = _classify_muscle_status(inbody_data)

    # Kiểm tra Central Fat (mỡ bụng)
    central_fat = _detect_central_fat(inbody_data)

    return UserSignals(
        bmi_status=bmi_status,
        body_fat_status=body_fat_status,
        muscle_status=muscle_status,
        central_fat=central_fat,
    )


def _compute_bmi_from_inbody(inbody_data: Dict[str, Any]) -> Optional[float]:
    """Tính BMI từ inbody_data nếu có đủ dữ liệu."""
    try:
        # Ưu tiên BMI có sẵn
        obesity = inbody_data.get("obesity", {}) or {}
        if "bmi" in obesity:
            return float(obesity["bmi"])
    except Exception:
        pass

    try:
        # Tự tính từ cân nặng (kg) và chiều cao (cm)
        composition = inbody_data.get("composition", {}) or {}
        inbody_info = inbody_data.get("inbody_info", {}) or {}
        weight = composition.get("weight")
        height_cm = inbody_info.get("height")
        if weight is None or height_cm is None:
            return None
        weight = float(weight)
        height_m = float(height_cm) / 100.0
        if height_m <= 0:
            return None
        return weight / (height_m ** 2)
    except Exception:
        return None


def _classify_bmi_status(bmi: Optional[float]) -> BMIStatus:
    """
    Phân loại BMI status theo chuẩn châu Á.
    
    - UNDERWEIGHT: BMI < 18.5
    - NORMAL: 18.5 <= BMI < 23
    - OVERWEIGHT: 23 <= BMI < 27.5
    - OBESE: BMI >= 27.5
    """
    if bmi is None:
        return "UNKNOWN"
    if bmi < 18.5:
        return "UNDERWEIGHT"
    if bmi < 23:
        return "NORMAL"
    if bmi < 27.5:
        return "OVERWEIGHT"
    return "OBESE"


def _classify_body_fat_status(inbody_data: Dict[str, Any]) -> BodyFatStatus:
    """
    Phân loại Body Fat Status dựa trên PBF (Percent Body Fat).
    
    Ngưỡng tham khảo:
    - Nam: LOW < 10%, NORMAL 10-20%, HIGH > 20%
    - Nữ: LOW < 20%, NORMAL 20-30%, HIGH > 30%
    """
    try:
        obesity = inbody_data.get("obesity", {}) or {}
        pbf_str = obesity.get("pbf")
        if pbf_str is None:
            return "UNKNOWN"

        pbf = float(pbf_str)
        inbody_info = inbody_data.get("inbody_info", {}) or {}
        gender = (inbody_info.get("gender") or "").lower()

        # Ngưỡng theo giới tính
        if gender in ["male", "nam"]:
            if pbf < 10:
                return "LOW"
            elif pbf <= 20:
                return "NORMAL"
            else:
                return "HIGH"
        elif gender in ["female", "nữ"]:
            if pbf < 20:
                return "LOW"
            elif pbf <= 30:
                return "NORMAL"
            else:
                return "HIGH"
        else:
            # Không biết giới tính, dùng ngưỡng trung bình
            if pbf < 15:
                return "LOW"
            elif pbf <= 25:
                return "NORMAL"
            else:
                return "HIGH"
    except Exception:
        return "UNKNOWN"


def _classify_muscle_status(inbody_data: Dict[str, Any]) -> MuscleStatus:
    """
    Phân loại Muscle Status dựa trên SMM (Skeletal Muscle Mass).
    
    Tạm thời dùng heuristic đơn giản:
    - Nếu có BMI và BMI cao nhưng body fat không cao -> muscle tốt
    - Nếu BMI thấp và body fat thấp -> muscle thấp
    """
    try:
        bmi = _compute_bmi_from_inbody(inbody_data)
        body_fat_status = _classify_body_fat_status(inbody_data)

        if bmi is None:
            return "UNKNOWN"

        # Heuristic: Nếu BMI cao nhưng body fat không cao -> có thể muscle tốt
        if bmi >= 23 and body_fat_status != "HIGH":
            return "NORMAL"  # hoặc HIGH nếu có thêm dữ liệu
        elif bmi < 18.5 and body_fat_status == "LOW":
            return "LOW"
        else:
            return "NORMAL"  # Mặc định
    except Exception:
        return "UNKNOWN"


def _detect_central_fat(inbody_data: Dict[str, Any]) -> bool:
    """
    Phát hiện Central Fat (mỡ bụng) dựa trên WHR hoặc heuristic.
    
    Tạm thời dùng heuristic:
    - Nếu BMI >= 23 và BODY_FAT_STATUS = HIGH -> có thể có central fat
    """
    try:
        bmi = _compute_bmi_from_inbody(inbody_data)
        body_fat_status = _classify_body_fat_status(inbody_data)

        if bmi is None:
            return False

        # Heuristic đơn giản: BMI cao + body fat cao -> có thể có central fat
        if bmi >= 23 and body_fat_status == "HIGH":
            return True

        # Có thể thêm logic dựa trên WHR nếu có trong InBody data
        # Ví dụ: obesity.get("whr") > 0.9 (nam) hoặc > 0.85 (nữ)

        return False
    except Exception:
        return False
