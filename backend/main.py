import os
import json
import re
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from utils.calculator import calculate_nutrition_plan
from utils.formatter import format_nutrition_info, format_daily_menu, format_quick_tips
from utils.ollama_client import ollama_client
from services.club_service import generate_club_response, is_club_related_query
from utils.clubs_client import clubs_client
from services.llm_service import get_ai_response

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
AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
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