import os
import json
import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from utils.calculator import calculate_nutrition_plan
from utils.formatter import format_nutrition_info, format_daily_menu, format_quick_tips
from utils.ollama_client import ollama_client
from utils.clubs_client import clubs_client
from constants.clubs import (
    RAW_CITY_ALIAS_PAIRS,
    RAW_DISTRICT_ALIAS_PAIRS,
    COUNT_KEYWORDS,
    ACTIVE_KEYWORDS,
    INACTIVE_KEYWORDS,
    ADDRESS_KEYWORDS,
    DISTRICT_KEYWORDS,
)
import requests

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Fitness Nutrition Chatbot API",
    description="API cho chatbot tư vấn dinh dưỡng thể hình sử dụng Ollama",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI Provider configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "deepseek")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Load system prompt
def load_system_prompt():
    try:
        with open("prompt_system.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Bạn là AI Assistant đa tác vụ của The New Gym. Hỗ trợ khách hàng về thông tin chi nhánh, tư vấn dinh dưỡng, và các câu hỏi khác về The New Gym."

# In-memory storage for user sessions
user_sessions: Dict[str, Dict] = {}

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str
    nutrition_info: Optional[Dict] = None

class UserInfo(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    goal: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    session_id: str


def normalize_text(text: str) -> str:
    """Chuyển text về dạng lower-case và bỏ dấu để so khớp"""
    if not text:
        return ""
    text = text.lower()
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


CITY_ALIAS_MAP: Dict[str, str] = {}
for canonical, aliases in RAW_CITY_ALIAS_PAIRS:
    for alias in aliases:
        CITY_ALIAS_MAP[alias] = canonical
        CITY_ALIAS_MAP[normalize_text(alias)] = canonical


DISTRICT_ALIAS_MAP: Dict[str, str] = {}
for canonical, aliases in RAW_DISTRICT_ALIAS_PAIRS:
    for alias in aliases:
        DISTRICT_ALIAS_MAP[alias] = canonical
        DISTRICT_ALIAS_MAP[normalize_text(alias)] = canonical


def detect_city_from_message(message: str) -> Optional[str]:
    """Phát hiện thành phố từ câu hỏi, ưu tiên alias dài hơn"""
    normalized = normalize_text(message)
    
    # Duyệt alias đã chuẩn hoá, dài trước
    sorted_aliases = sorted(CITY_ALIAS_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for alias, city in sorted_aliases:
        normalized_alias = normalize_text(alias)
        if normalized_alias in normalized:
            return city
    return None


def detect_district_from_message(message: str) -> Optional[str]:
    """Phát hiện quận/huyện từ câu hỏi"""
    normalized = normalize_text(message)
    # Danh sách các quận/huyện phổ biến ở HCM và các thành phố khác
    # Sắp xếp theo độ dài giảm dần để tránh match sai (quận 10, 11, 12 trước quận 1, 2, 3)
    sorted_aliases = sorted(DISTRICT_ALIAS_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for alias, canonical in sorted_aliases:
        normalized_alias = normalize_text(alias)
        if normalized_alias in normalized:
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


def format_club_entry(club: Dict, index: Optional[int] = None) -> str:
    """Format thông tin club"""
    name_vi = club.get("nameVi") or club.get("nameEn") or "Chi nhánh"
    location = club.get("location", club.get("address", ""))
    info_url = club.get("informationUrl")
    
    prefix = f"{index}. " if index else ""
    lines = [f"{prefix}**{name_vi}**"]
    if location:
        lines.append(f"   Địa chỉ: {location}")
    if info_url:
        lines.append(f"Link tham khảo: {info_url}")
    
    return "\n".join(lines)


def build_city_summary(city_name: str, clubs: List[Dict], is_count_query: bool, only_active: bool, only_inactive: bool) -> str:
    """Tạo câu trả lời cho các chi nhánh trong một thành phố"""
    if not clubs:
        # Tìm chi nhánh gần nhất
        all_clubs = clubs_client.fetch_clubs()
        if all_clubs:
            # Tìm chi nhánh ở thành phố khác gần nhất
            other_cities = {}
            for club in all_clubs:
                club_city = club.get("city", {}).get("cityName", "")
                if club_city and club_city != city_name:
                    if club_city not in other_cities:
                        other_cities[club_city] = []
                    other_cities[club_city].append(club)
            
            if other_cities:
                suggestions = []
                for other_city, city_clubs in list(other_cities.items())[:3]:
                    active_count = sum(1 for c in city_clubs if c.get("isActive") == 1)
                    if active_count > 0:
                        suggestions.append(f"- {other_city}: {active_count} chi nhánh đang hoạt động")
                
                if suggestions:
                    return (
                        f"Mình chưa tìm thấy chi nhánh nào của The New Gym ở {city_name}.\n\n"
                        f"Bạn có muốn mình gợi ý các thành phố gần nhất có chi nhánh không?\n\n"
                        + "\n".join(suggestions)
                    )
        
        return f"Mình chưa tìm thấy chi nhánh nào của The New Gym ở {city_name}. Bạn muốn mình gợi ý khu vực gần nhất không?"
    
    active_clubs, inactive_clubs = split_clubs_by_status(clubs)
    
    # Giới hạn tối đa 3 chi nhánh khi hiển thị
    max_display = 3
    
    if only_inactive:
        if not inactive_clubs:
            return f"Hiện không có chi nhánh nào tạm đóng tại {city_name}."
        sections = [f"Có {len(inactive_clubs)} chi nhánh tạm đóng tại {city_name}:"]
        for idx, club in enumerate(inactive_clubs[:max_display], 1):
            sections.append(format_club_entry(club, idx))
        if len(inactive_clubs) > max_display:
            sections.append(f"\n... và {len(inactive_clubs) - max_display} chi nhánh khác.")
    else:
        if not active_clubs:
            return f"Hiện không có chi nhánh nào đang hoạt động tại {city_name}."
        
        if is_count_query:
            sections = [f"The New Gym có **{len(active_clubs)}** chi nhánh đang hoạt động tại {city_name}:"]
        else:
            sections = [f"Các chi nhánh đang hoạt động tại {city_name}:"]
        
        for idx, club in enumerate(active_clubs[:max_display], 1):
            sections.append(format_club_entry(club, idx))
        
        if len(active_clubs) > max_display:
            sections.append(f"\n... và {len(active_clubs) - max_display} chi nhánh khác.")
            sections.append(f"Bạn muốn xem danh sách đầy đủ không?")
    
    return "\n\n".join(sections)


def build_overall_summary(clubs: List[Dict]) -> str:
    if not clubs:
        return "Hiện hệ thống chưa có dữ liệu về bất kỳ chi nhánh nào."
    # Nhóm theo thành phố
    city_groups: Dict[str, List[Dict]] = {}
    for club in clubs:
        city_name = club.get("city", {}).get("cityName", "Không xác định")
        city_groups.setdefault(city_name, []).append(club)
    # Chỉ thống kê chi nhánh đang hoạt động
    total_active = sum(1 for c in clubs if c.get("isActive") == 1)
    sections = [f"Hệ thống ghi nhận tổng cộng {total_active} chi nhánh đang hoạt động trên {len(city_groups)} tỉnh/thành."]
    for city_name, city_clubs in sorted(city_groups.items()):
        active_clubs, _ = split_clubs_by_status(city_clubs)
        sections.append(f"- {city_name}: {len(active_clubs)} chi nhánh đang hoạt động")
    sections.append("Bạn muốn xem chi tiết về thành phố hoặc chi nhánh cụ thể nào không?")
    sections.append("(Nguồn: API clubs của hệ thống)")
    return "\n".join(sections)


def build_single_club_summary(club: Dict) -> str:
    """Tạo câu trả lời cho một chi nhánh cụ thể"""
    name_vi = club.get("nameVi") or club.get("nameEn") or "Chi nhánh"
    location = club.get("location", club.get("address", ""))
    city_name = club.get("city", {}).get("cityName")
    info_url = club.get("informationUrl")
    
    lines = [f"Chi nhánh **{name_vi}** của The New Gym:"]
    if location:
        lines.append(f"Địa chỉ: {location}")
    if city_name:
        lines.append(f"Thành phố: {city_name}")
    
    return "\n".join(lines)


def find_clubs_by_district(district_name: str, clubs: List[Dict]) -> List[Dict]:
    """Tìm clubs theo quận/huyện với matching chính xác"""
    normalized_target = normalize_text(district_name)
    canonical = DISTRICT_ALIAS_MAP.get(district_name) or DISTRICT_ALIAS_MAP.get(normalized_target, district_name)
    results = []
    for club in clubs:
        club_district = club.get("district", {}).get("districtName", "")
        club_location = club.get("location", "")
        if normalize_text(canonical) in normalize_text(club_district) or normalize_text(canonical) in normalize_text(club_location):
            results.append(club)
    return results


def generate_club_response(message: str) -> str:
    """Tạo câu trả lời cho câu hỏi về clubs"""
    # Mặc định chỉ dùng các chi nhánh đang hoạt động; nếu người dùng hỏi về chi nhánh tạm đóng thì lấy toàn bộ
    normalized_initial = normalize_text(message)
    wants_inactive_initial = any(keyword in normalized_initial for keyword in INACTIVE_KEYWORDS)
    all_clubs = clubs_client.fetch_clubs()
    clubs = all_clubs if wants_inactive_initial else clubs_client.get_active_clubs()
    
    if not clubs:
        return "Xin lỗi, hiện chưa có dữ liệu về các chi nhánh trong hệ thống."
    
    normalized = normalize_text(message)
    is_count_query = any(keyword in normalized for keyword in COUNT_KEYWORDS)
    wants_active = any(keyword in normalized for keyword in ACTIVE_KEYWORDS)
    wants_inactive = any(keyword in normalized for keyword in INACTIVE_KEYWORDS)
    
    # Tìm theo tên club cụ thể
    club = find_club_by_name(message, all_clubs)
    if club:
        return build_single_club_summary(club)
    
    # Tìm theo quận/huyện
    requested_district = detect_district_from_message(message)
    if requested_district:
        district_clubs = find_clubs_by_district(requested_district, clubs)
        if district_clubs:
            city_name = district_clubs[0].get("city", {}).get("cityName", "")
            return build_city_summary(f"{requested_district}, {city_name}", district_clubs, is_count_query, wants_active, wants_inactive)
        else:
            # Tìm các quận gần nhất
            all_districts = {}
            for c in clubs:
                d = c.get("district", {}).get("districtName", "")
                if d:
                    if d not in all_districts:
                        all_districts[d] = []
                    all_districts[d].append(c)
            
            suggestions = []
            for dist, dist_clubs in list(all_districts.items())[:3]:
                active_count = sum(1 for c in dist_clubs if c.get("isActive") == 1)
                if active_count > 0:
                    suggestions.append(f"- {dist}: {active_count} chi nhánh đang hoạt động")
            
            if suggestions:
                return (
                    f"Mình chưa tìm thấy chi nhánh nào ở {requested_district}.\n\n"
                    f"Bạn có muốn xem các quận/huyện gần nhất có chi nhánh không?\n\n"
                    + "\n".join(suggestions)
                )
            return f"Mình chưa tìm thấy chi nhánh nào ở {requested_district}. Bạn muốn mình gợi ý khu vực gần nhất không?"
    
    # Tìm theo thành phố
    requested_city = detect_city_from_message(message)
    if requested_city:
        target_norm = normalize_text(requested_city)
        city_clubs = []
        for c in clubs:
            club_city = c.get("city", {}).get("cityName", "")
            club_location = c.get("location", "")
            normalized_club_city = normalize_text(club_city)
            normalized_club_location = normalize_text(club_location)
            
            # Match chính xác với thành phố
            if normalized_club_city == target_norm:
                city_clubs.append(c)
            # Hoặc thành phố có trong location
            elif target_norm in normalized_club_location:
                city_clubs.append(c)
        
        return build_city_summary(requested_city, city_clubs, is_count_query, wants_active, wants_inactive)
    
    # Nếu người dùng hỏi địa chỉ nhưng không nêu tên cụ thể
    if any(keyword in normalized for keyword in ADDRESS_KEYWORDS):
        return (
            "Bạn muốn biết địa chỉ của chi nhánh nào ạ?\n\n"
            "Hãy cho mình biết:\n"
            "- Tên chi nhánh (ví dụ: Hoàng Văn Thụ, Điện Biên Phủ...)\n"
            "- Hoặc khu vực bạn muốn tìm (ví dụ: Quận 3, Tân Bình...)\n"
            "- Hoặc thành phố (ví dụ: Hồ Chí Minh, Đà Nẵng...)"
        )
    
    # Nếu người dùng chỉ hỏi chung chung
    return build_overall_summary(clubs)


def is_club_related_query(message: str) -> bool:
    """Kiểm tra xem câu hỏi có liên quan đến clubs không"""
    message_lower = message.lower()
    club_keywords = [
        'club', 'phòng gym', 'chi nhánh', 'địa điểm', 'cơ sở',
        'gym ở', 'phòng tập ở', 'địa chỉ', 'ở đâu', 'quận',
        'thành phố', 'hcm', 'hồ chí minh', 'tphcm', 'tp.hcm',
        'đà nẵng', 'cần thơ', 'biên hòa', 'vũng tàu', 
        'long xuyên', 'hậu giang', 'đồng nai', 'an giang',
        'bà rịa vũng tàu', 'hoàng văn thụ', 'âu cơ', 
        'quang trung', 'điện biên phủ', 'nguyễn chí thanh', 
        'nguyễn thị thập', 'ung văn khiêm', 'nguyễn ái quốc', 
        'trần hưng đạo', 'hoàng diệu', 'phan đăng lưu', 
        'nam kỳ khởi nghĩa', 'lý thường kiệt', 'bao nhiêu',
        'có mấy', 'danh sách', 'liệt kê'
    ]
    # Kiểm tra nếu có từ khóa về clubs hoặc số lượng/đếm
    has_club_keyword = any(keyword in message_lower for keyword in club_keywords)
    # Kiểm tra nếu có từ về số lượng kết hợp với từ về địa điểm/gym
    has_count_query = any(word in message_lower for word in ['bao nhiêu', 'có mấy', 'có bao nhiêu']) and \
                     any(word in message_lower for word in ['gym', 'phòng', 'club', 'chi nhánh', 'cơ sở', 'địa điểm'])
    return has_club_keyword or has_count_query

def extract_user_info_from_message(message: str) -> Dict:
    """Trích xuất thông tin người dùng từ tin nhắn"""
    info = {}
    message_lower = message.lower()
    
    # Extract height
    if "cao" in message_lower and "m" in message_lower:
        height_match = re.search(r'(\d+\.?\d*)\s*m', message_lower)
        if height_match:
            info['height_cm'] = float(height_match.group(1)) * 100
    
    # Extract weight
    if "nặng" in message_lower and "kg" in message_lower:
        weight_match = re.search(r'(\d+\.?\d*)\s*kg', message_lower)
        if weight_match:
            info['weight_kg'] = float(weight_match.group(1))
    
    # Extract age
    if "tuổi" in message_lower:
        age_match = re.search(r'(\d+)\s*tuổi', message_lower)
        if age_match:
            info['age'] = int(age_match.group(1))
    
    # Extract gender
    if "nam" in message_lower or "trai" in message_lower:
        info['gender'] = 'male'
    elif "nữ" in message_lower or "gái" in message_lower:
        info['gender'] = 'female'
    
    # Extract goal
    if "tăng cơ" in message_lower or "bulk" in message_lower:
        info['goal'] = 'tăng cơ'
    elif "giảm mỡ" in message_lower or "cut" in message_lower:
        info['goal'] = 'giảm mỡ'
    elif "giữ cân" in message_lower or "maintain" in message_lower:
        info['goal'] = 'giữ cân'
    
    # Extract workout days
    if "tập" in message_lower and "buổi" in message_lower:
        workout_match = re.search(r'(\d+)\s*buổi', message_lower)
        if workout_match:
            info['workout_days_per_week'] = int(workout_match.group(1))
    
    return info

def get_ai_response(messages: List[Dict], system_prompt: str) -> str:
    """Gọi AI provider theo cấu hình (ollama | deepseek)."""
    provider = (AI_PROVIDER or "ollama").lower()
    if provider == "deepseek":
        return get_deepseek_response(messages, system_prompt)
    return get_ollama_response(messages, system_prompt)

def get_ollama_response(messages: List[Dict], system_prompt: str) -> str:
    try:
        if not ollama_client.is_available():
            return "Xin lỗi, Ollama service chưa sẵn sàng. Vui lòng chạy 'ollama serve' trước."
        return ollama_client.chat(messages, system_prompt)
    except Exception as e:
        return f"Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu: {str(e)}"

def get_deepseek_response(messages: List[Dict], system_prompt: str) -> str:
    try:
        if not DEEPSEEK_API_KEY:
            return "Xin lỗi, DEEPSEEK_API_KEY chưa được cấu hình. Vui lòng đặt AI_PROVIDER=ollama hoặc thêm DEEPSEEK_API_KEY."
        url = f"{DEEPSEEK_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        # DeepSeek is OpenAI-compatible; extract content
        return (data["choices"][0]["message"]["content"] or "").strip()
    except requests.RequestException as e:
        return f"Lỗi DeepSeek: {str(e)}"

# API Routes
@app.get("/")
async def root():
    return {"message": "Fitness Nutrition Chatbot API", "status": "running"}

@app.get("/ai-status")
async def get_ai_status():
    """Kiểm tra trạng thái AI provider"""
    provider = (AI_PROVIDER or "ollama").lower()
    if provider == "ollama":
        status = ollama_client.test_connection()
        return {
            "provider": "ollama",
            "available": status["available"],
            "models": status["models"],
            "error": status["error"]
        }
    elif provider == "deepseek":
        return {
            "provider": "deepseek",
            "available": bool(DEEPSEEK_API_KEY),
            "models": [DEEPSEEK_MODEL] if DEEPSEEK_MODEL else [],
            "error": None if DEEPSEEK_API_KEY else "Missing DEEPSEEK_API_KEY"
        }
    else:
        return {"provider": provider, "available": False, "error": "Unknown AI provider"}

@app.post("/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage):
    """Xử lý tin nhắn chat"""
    try:
        session_id = chat_message.session_id
        message = chat_message.message
        
        # Load system prompt
        system_prompt = load_system_prompt()
        
        # Check if query is about clubs
        is_club_query = is_club_related_query(message)
        club_response_text: Optional[str] = None
        
        if is_club_query:
            club_response_text = generate_club_response(message)
        
        # Extract user info from message
        user_info = extract_user_info_from_message(message)
        
        # Update session with new info
        if session_id not in user_sessions:
            user_sessions[session_id] = {}
        
        user_sessions[session_id].update(user_info)
        
        if is_club_query and club_response_text:
            return ChatResponse(
                response=club_response_text,
                session_id=session_id,
                nutrition_info=None
            )
        
        # Prepare messages for AI
        messages = [{"role": "user", "content": message}]
        
        # Get AI response
        ai_response = get_ai_response(messages, system_prompt)
        
        # Calculate nutrition info if we have enough data
        nutrition_info = None
        if session_id in user_sessions:
            session_data = user_sessions[session_id]
            if all(key in session_data for key in ['height_cm', 'weight_kg', 'age', 'gender', 'goal', 'workout_days_per_week']):
                try:
                    nutrition_info = calculate_nutrition_plan(
                        height_cm=session_data['height_cm'],
                        weight_kg=session_data['weight_kg'],
                        age=session_data['age'],
                        gender=session_data['gender'],
                        goal=session_data['goal'],
                        workout_days_per_week=session_data['workout_days_per_week']
                    )
                except Exception as e:
                    print(f"Error calculating nutrition: {e}")
        
        return ChatResponse(
            response=ai_response,
            session_id=session_id,
            nutrition_info=nutrition_info
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clubs")
async def get_clubs(refresh: bool = False):
    """Lấy danh sách tất cả clubs"""
    try:
        clubs = clubs_client.fetch_clubs(use_cache=not refresh)
        source = clubs_client.get_last_source()
        return {
            "code": 1010,
            "message": "GET_CLUBS_REFRESH" if refresh else "GET_CLUBS",
            "data": clubs,
            "meta": {
                "count": len(clubs),
                "source": source,
                "cache_last_updated": clubs_client.get_cache_timestamp_iso(),
                "refresh": refresh
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clubs/search")
async def search_clubs(q: str, refresh: bool = False):
    """Tìm kiếm clubs theo từ khóa"""
    try:
        if not q:
            raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
        results = clubs_client.search_clubs(q, use_cache=not refresh)
        source = clubs_client.get_last_source()
        return {
            "code": 1010,
            "message": "SEARCH_CLUBS_REFRESH" if refresh else "SEARCH_CLUBS",
            "data": results,
            "meta": {
                "count": len(results),
                "source": source,
                "cache_last_updated": clubs_client.get_cache_timestamp_iso(),
                "refresh": refresh,
                "query": q
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clubs/active")
async def get_active_clubs(refresh: bool = False):
    """Lấy danh sách clubs đang hoạt động"""
    try:
        clubs = clubs_client.get_active_clubs(use_cache=not refresh)
        source = clubs_client.get_last_source()
        return {
            "code": 1010,
            "message": "GET_ACTIVE_CLUBS_REFRESH" if refresh else "GET_ACTIVE_CLUBS",
            "data": clubs,
            "meta": {
                "count": len(clubs),
                "source": source,
                "cache_last_updated": clubs_client.get_cache_timestamp_iso(),
                "refresh": refresh
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clubs/cache")
async def clear_clubs_cache():
    """Xóa cache clubs để lần gọi tiếp theo lấy dữ liệu mới"""
    try:
        clubs_client.clear_cache()
        return {
            "message": "Clubs cache cleared",
            "meta": {
                "cache_last_updated": clubs_client.get_cache_timestamp_iso(),
                "source": clubs_client.get_last_source()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/user-info")
async def update_user_info(user_info: UserInfo):
    """Cập nhật thông tin người dùng"""
    try:
        session_id = user_info.session_id
        
        # Update session data
        user_sessions[session_id] = {
            "height_cm": user_info.height_cm,
            "weight_kg": user_info.weight_kg,
            "age": user_info.age,
            "gender": user_info.gender,
            "goal": user_info.goal,
            "workout_days_per_week": user_info.workout_days_per_week
        }
        
        return {"message": "User info updated successfully", "session_id": session_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nutrition-plan/{session_id}")
async def get_nutrition_plan(session_id: str):
    """Lấy kế hoạch dinh dưỡng cho session"""
    try:
        if session_id not in user_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = user_sessions[session_id]
        
        if not all(key in session_data for key in ['height_cm', 'weight_kg', 'age', 'gender', 'goal', 'workout_days_per_week']):
            raise HTTPException(status_code=400, detail="Incomplete user information")
        
        nutrition_plan = calculate_nutrition_plan(
            height_cm=session_data['height_cm'],
            weight_kg=session_data['weight_kg'],
            age=session_data['age'],
            gender=session_data['gender'],
            goal=session_data['goal'],
            workout_days_per_week=session_data['workout_days_per_week']
        )
        
        return nutrition_plan
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)