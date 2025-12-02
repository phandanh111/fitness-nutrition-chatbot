"""
Client đọc thông tin clubs từ file markdown (thay cho API).
"""

import os
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

# Define CLUBS_MD_PATH locally để tránh circular import
BASE_DIR = Path(__file__).resolve().parent.parent
CLUBS_MD_PATH = BASE_DIR / "data" / "clubs.md"

def _parse_clubs_from_markdown(md_path: Path):
    """Parse clubs từ markdown - lazy import để tránh circular dependency."""
    try:
        from rag.topics.clubs import ClubsParser
        parser = ClubsParser()
        return parser._parse_from_markdown(md_path)
    except ImportError:
        # Fallback: parse trực tiếp nếu không thể import
        import re
        if not md_path.exists():
            raise FileNotFoundError(f"File markdown không tồn tại: {md_path}")
        
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        clubs = []
        pattern = r"## CLB (\d+) — (.+?) \(([A-Z0-9]+)\)\n(.*?)(?=\n## CLB|\Z)"
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            club_num = match.group(1)
            club_name = match.group(2).strip()
            club_id = match.group(3).strip()
            club_content = match.group(4).strip()
            
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
            
            for line in club_content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("- "):
                    line = line[2:].strip()
                
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
            
            if club_data["address"]:
                parts = [p.strip() for p in club_data["address"].split(",")]
                if len(parts) >= 3:
                    district_name = parts[-3] if len(parts) >= 3 else ""
                    city_name = parts[-2] if len(parts) >= 2 else ""
                    if district_name:
                        club_data["district"] = {"districtName": district_name}
                    if city_name:
                        club_data["city"] = {"cityName": city_name}
            
            clubs.append(club_data)
        
        return clubs

class ClubsClient:
    def __init__(self, markdown_path: Optional[Path] = None):
        self._markdown_path = Path(markdown_path or CLUBS_MD_PATH)
        self._cache: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 300  # Cache 5 phút
        self._debug = os.getenv("CLUBS_DEBUG", "false").lower() == "true"
        self._last_source = "none"
    
    def _is_cache_valid(self) -> bool:
        """Kiểm tra cache còn hợp lệ không"""
        if self._cache is None or self._cache_timestamp is None:
            return False
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_ttl
    
    def _log(self, message: str) -> None:
        """Ghi log khi bật chế độ debug"""
        if self._debug:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[ClubsClient][{timestamp}] {message}")
    
    def _load_from_markdown(self) -> List[Dict]:
        """Đọc dữ liệu từ file markdown."""
        try:
            clubs = _parse_clubs_from_markdown(self._markdown_path)
            self._last_source = "markdown"
            self._log(f"Loaded {len(clubs)} clubs from markdown: {self._markdown_path}")
            return clubs
        except FileNotFoundError:
            self._last_source = "markdown_missing"
            self._log(f"Markdown file không tồn tại: {self._markdown_path}")
            return []
        except Exception as exc:
            self._last_source = "markdown_error"
            self._log(f"Không thể đọc markdown: {exc}")
            return []

    def fetch_clubs(self, use_cache: bool = True) -> List[Dict]:
        """
        Lấy danh sách clubs từ markdown (hoặc cache).
        """
        if use_cache and self._is_cache_valid():
            self._last_source = "cache"
            self._log(
                f"Using cached clubs data (count={len(self._cache) if self._cache else 0})"
            )
            return self._cache or []

        clubs = self._load_from_markdown()
        self._cache = clubs
        self._cache_timestamp = datetime.now()
        return clubs
    
    def get_club_by_id(self, club_id: int) -> Optional[Dict]:
        """Lấy thông tin club theo ID"""
        clubs = self.fetch_clubs()
        for club in clubs:
            if club.get("id") == club_id:
                return club
        return None
    
    def get_club_by_name(self, name: str) -> Optional[Dict]:
        """Tìm club theo tên (tiếng Việt hoặc tiếng Anh)"""
        clubs = self.fetch_clubs()
        name_lower = name.lower()
        for club in clubs:
            if (club.get("nameVi", "").lower() == name_lower or 
                club.get("nameEn", "").lower() == name_lower):
                return club
        return None
    
    def search_clubs(self, query: str, use_cache: bool = True) -> List[Dict]:
        """Tìm kiếm clubs theo từ khóa"""
        self._log(f"Searching clubs with query='{query}' (use_cache={use_cache})")
        clubs = self.fetch_clubs(use_cache=use_cache)
        query_lower = query.lower()
        results = []
        
        for club in clubs:
            # Tìm trong tên Việt, tên Anh, địa chỉ, quận, thành phố
            if (query_lower in club.get("nameVi", "").lower() or
                query_lower in club.get("nameEn", "").lower() or
                query_lower in club.get("address", "").lower() or
                query_lower in club.get("location", "").lower() or
                query_lower in club.get("district", {}).get("districtName", "").lower() or
                query_lower in club.get("city", {}).get("cityName", "").lower()):
                results.append(club)
        
        self._log(f"Search result count: {len(results)}")
        return results
    
    def get_active_clubs(self, use_cache: bool = True) -> List[Dict]:
        """Lấy danh sách clubs đang hoạt động"""
        self._log(f"Getting active clubs (use_cache={use_cache})")
        clubs = self.fetch_clubs(use_cache=use_cache)
        active_clubs = [club for club in clubs if club.get("isActive") == 1]
        self._log(f"Active clubs count: {len(active_clubs)}")
        return active_clubs
    
    def get_clubs_by_city(self, city_name: str, use_cache: bool = True) -> List[Dict]:
        """Lấy danh sách clubs theo thành phố"""
        self._log(f"Filtering clubs by city='{city_name}' (use_cache={use_cache})")
        clubs = self.fetch_clubs(use_cache=use_cache)
        city_lower = city_name.lower()
        filtered = [club for club in clubs 
                if city_lower in club.get("city", {}).get("cityName", "").lower()]
        self._log(f"Clubs found in city '{city_name}': {len(filtered)}")
        return filtered
    
    def get_clubs_by_district(self, district_name: str, use_cache: bool = True) -> List[Dict]:
        """Lấy danh sách clubs theo quận/huyện"""
        self._log(f"Filtering clubs by district='{district_name}' (use_cache={use_cache})")
        clubs = self.fetch_clubs(use_cache=use_cache)
        district_lower = district_name.lower()
        filtered = [club for club in clubs 
                if district_lower in club.get("district", {}).get("districtName", "").lower()]
        self._log(f"Clubs found in district '{district_name}': {len(filtered)}")
        return filtered
    
    def format_clubs_for_prompt(self, clubs: List[Dict] = None) -> str:
        """
        Format danh sách clubs thành text để đưa vào prompt
        
        Args:
            clubs: Danh sách clubs (nếu None thì lấy tất cả)
        
        Returns:
            Text mô tả clubs
        """
        if clubs is None:
            clubs = self.fetch_clubs()
        
        if not clubs:
            return "Hiện tại không có thông tin về các club."
        
        # Nhóm clubs theo thành phố để dễ đếm
        clubs_by_city = {}
        for club in clubs:
            city_name = club.get("city", {}).get("cityName", "Không xác định")
            if city_name not in clubs_by_city:
                clubs_by_city[city_name] = []
            clubs_by_city[city_name].append(club)
        
        lines = ["=" * 80]
        lines.append("THÔNG TIN CÁC CLUB CỦA PHÒNG GYM - DỮ LIỆU TỪ API")
        lines.append("=" * 80)
        lines.append("")
        lines.append("⚠️ QUAN TRỌNG: BẠN PHẢI SỬ DỤNG ĐÚNG TÊN VÀ THÔNG TIN DƯỚI ĐÂY.")
        lines.append("KHÔNG được tự tạo tên như 'Club A', 'Club B' hay bất kỳ tên nào khác.")
        lines.append("")
        
        # Thống kê theo thành phố
        lines.append("📊 THỐNG KÊ THEO THÀNH PHỐ:")
        for city_name, city_clubs in sorted(clubs_by_city.items()):
            active_count = sum(1 for c in city_clubs if c.get("isActive") == 1)
            total_count = len(city_clubs)
            lines.append(f"  • {city_name}: {total_count} club (trong đó {active_count} đang hoạt động)")
        
        lines.append("")
        lines.append("📋 DANH SÁCH CHI TIẾT TỪNG CLUB (SỬ DỤNG ĐÚNG TÊN NÀY):")
        lines.append("")
        
        # Đếm tổng số clubs
        total_all = len(clubs)
        club_counter = 1
        
        # Sắp xếp theo thành phố rồi theo tên
        for city_name in sorted(clubs_by_city.keys()):
            city_clubs = clubs_by_city[city_name]
            lines.append(f"━━━ {city_name} ━━━")
            for club in sorted(city_clubs, key=lambda x: x.get("nameVi", "")):
                name_vi = club.get("nameVi", "")
                name_en = club.get("nameEn", "")
                location = club.get("location", "")
                is_active = "Đang hoạt động" if club.get("isActive") == 1 else "Tạm đóng"
                info_url = club.get("informationUrl", "")
                district = club.get("district", {}).get("districtName", "")
                
                # Format với số thứ tự và tên thực tế
                lines.append(f"{club_counter}. TÊN CLUB: {name_vi} ({name_en})")
                lines.append(f"   Địa chỉ: {location}")
                if district:
                    lines.append(f"   Quận/Huyện: {district}")
                lines.append(f"   Trạng thái: {is_active}")
                if info_url:
                    lines.append(f"   Link: {info_url}")
                lines.append("")
                club_counter += 1
        
        lines.append("=" * 80)
        lines.append(f"TỔNG CỘNG: {total_all} clubs trong hệ thống")
        lines.append("=" * 80)
        lines.append("")
        lines.append("LƯU Ý CUỐI CÙNG: Khi trả lời, bạn PHẢI sử dụng ĐÚNG tên clubs ở trên.")
        lines.append("Ví dụ: 'Hoàng Văn Thụ', 'Điện Biên Phủ', 'Nguyễn Chí Thanh', v.v.")
        lines.append("KHÔNG được tạo tên mới như 'Club A', 'Club B', 'Club 1', 'Club 2'.")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def clear_cache(self) -> None:
        """Xóa cache thủ công"""
        self._cache = None
        self._cache_timestamp = None
        self._last_source = "none"
        self._log("Clubs cache cleared manually")
    
    def get_last_source(self) -> str:
        """Lấy nguồn dữ liệu gần nhất (api, cache, error, ... )"""
        return self._last_source

    def get_cache_timestamp_iso(self) -> Optional[str]:
        """Trả về thời điểm cache gần nhất ở dạng ISO string"""
        if self._cache_timestamp is None:
            return None
        return self._cache_timestamp.isoformat()

# Tạo instance global
clubs_client = ClubsClient()

