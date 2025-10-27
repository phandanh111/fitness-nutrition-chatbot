"""
Fitness Nutrition Chatbot API
Backend cho chatbot tư vấn dinh dưỡng thể hình sử dụng Ollama
"""

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

# Load system prompt
def load_system_prompt():
    try:
        with open("prompt_system.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Bạn là chuyên gia dinh dưỡng thể hình. Hãy tư vấn dinh dưỡng cho người tập gym."

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

def get_ai_response(messages: List[Dict], system_prompt: str) -> str:
    """Gọi Ollama API để lấy phản hồi"""
    try:
        if not ollama_client.is_available():
            return "Xin lỗi, Ollama service chưa sẵn sàng. Vui lòng chạy 'ollama serve' trước."
        
        response = ollama_client.chat(messages, system_prompt)
        return response
    
    except Exception as e:
        return f"Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu: {str(e)}"

# API Routes
@app.get("/")
async def root():
    return {"message": "Fitness Nutrition Chatbot API", "status": "running"}

@app.get("/ai-status")
async def get_ai_status():
    """Kiểm tra trạng thái AI provider"""
    if AI_PROVIDER.lower() == "ollama":
        status = ollama_client.test_connection()
        return {
            "provider": "ollama",
            "available": status["available"],
            "models": status["models"],
            "error": status["error"]
        }
    else:
        return {"provider": "unknown", "available": False, "error": "Unknown AI provider"}

@app.post("/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage):
    """Xử lý tin nhắn chat"""
    try:
        session_id = chat_message.session_id
        message = chat_message.message
        
        # Load system prompt
        system_prompt = load_system_prompt()
        
        # Extract user info from message
        user_info = extract_user_info_from_message(message)
        
        # Update session with new info
        if session_id not in user_sessions:
            user_sessions[session_id] = {}
        
        user_sessions[session_id].update(user_info)
        
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