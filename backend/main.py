import os
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from utils.ollama_client import ollama_client
from services.club_service import generate_club_response, is_club_related_query
from services.exercise_service import generate_exercise_response, is_exercise_related_query
from services.terms_service import generate_terms_response, is_terms_related_query
from services.price_service import generate_price_response, is_price_related_query
from services.inbody_service import generate_inbody_response, is_inbody_related_query
from utils.clubs_client import clubs_client
from services.llm_service import get_ai_response
from services.conversation_service import (
    get_history as get_conversation_history,
    record_turn as record_conversation_turn,
    clear_session as clear_conversation_session,
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="The New Gym Club Information Chatbot API",
    description="API cho chatbot cung cấp thông tin chi nhánh The New Gym sử dụng RAG",
    version="1.0.0"
)

# CORS middleware - Cho phép truy cập từ localhost và IP public
# Lấy danh sách origins từ environment variable hoặc dùng mặc định
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
# Thêm IP public nếu có trong env
public_ip = os.getenv("PUBLIC_IP")
if public_ip:
    cors_origins.extend([
        f"http://{public_ip}:3000",
        f"http://{public_ip}",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
        return "Bạn là AI Assistant của The New Gym. Hỗ trợ khách hàng về thông tin chi nhánh và các câu hỏi khác về The New Gym."

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

# API Routes
@app.get("/")
async def root():
    return {"message": "The New Gym Club Information Chatbot API", "status": "running"}

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
        history = get_conversation_history(session_id)
        
        # Load system prompt
        system_prompt = load_system_prompt()
        
        # Check if query is about terms (điều khoản điều kiện)
        try:
            is_terms_query = is_terms_related_query(message)
            if is_terms_query:
                try:
                    terms_response_text = generate_terms_response(message)
                    if terms_response_text:
                        record_conversation_turn(session_id, message, terms_response_text)
                        return ChatResponse(
                            response=terms_response_text,
                            session_id=session_id
                        )
                except Exception as e:
                    print(f"[Chat] Error generating terms response: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue to try other topics or general LLM
        except Exception as e:
            print(f"[Chat] Error checking terms query: {e}")
            import traceback
            traceback.print_exc()
            # Continue to try other topics or general LLM
        
        # Check if query is about exercises
        try:
            is_exercise_query = is_exercise_related_query(message)
            if is_exercise_query:
                try:
                    exercise_response_text = generate_exercise_response(message)
                    if exercise_response_text:
                        record_conversation_turn(session_id, message, exercise_response_text)
                        return ChatResponse(
                            response=exercise_response_text,
                            session_id=session_id
                        )
                except Exception as e:
                    print(f"[Chat] Error generating exercise response: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue to try clubs or general LLM
        except Exception as e:
            print(f"[Chat] Error checking exercise query: {e}")
            import traceback
            traceback.print_exc()
            # Continue to try clubs or general LLM
        
        # Check if query is about InBody
        try:
            is_inbody_query = is_inbody_related_query(message)
            if is_inbody_query:
                try:
                    inbody_response_text = generate_inbody_response(message)
                    if inbody_response_text:
                        record_conversation_turn(session_id, message, inbody_response_text)
                        return ChatResponse(
                            response=inbody_response_text,
                            session_id=session_id
                        )
                except Exception as e:
                    print(f"[Chat] Error generating inbody response: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue to try clubs or general LLM
        except Exception as e:
            print(f"[Chat] Error checking inbody query: {e}")
            import traceback
            traceback.print_exc()
            # Continue to try clubs or general LLM
        
        # Check if query is about clubs
        try:
            is_club_query = is_club_related_query(message)
            if is_club_query:
                try:
                    club_response_text = generate_club_response(message)
                    if club_response_text:
                        record_conversation_turn(session_id, message, club_response_text)
                        return ChatResponse(
                            response=club_response_text,
                            session_id=session_id
                        )
                except Exception as e:
                    print(f"[Chat] Error generating club response: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue to try prices or general LLM
        except Exception as e:
            print(f"[Chat] Error checking club query: {e}")
            import traceback
            traceback.print_exc()
            # Continue to try prices or general LLM
        
        # Check if query is about prices
        try:
            is_price_query = is_price_related_query(message)
            if is_price_query:
                try:
                    price_response_text = generate_price_response(message)
                    if price_response_text:
                        record_conversation_turn(session_id, message, price_response_text)
                        return ChatResponse(
                            response=price_response_text,
                            session_id=session_id
                        )
                except Exception as e:
                    print(f"[Chat] Error generating price response: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue to general LLM
        except Exception as e:
            print(f"[Chat] Error checking price query: {e}")
            import traceback
            traceback.print_exc()
            # Continue to general LLM
        
        # Prepare messages for AI (generic questions)
        vietnamese_reminder = (
            "VUI LÒNG CHỈ TRẢ LỜI BẰNG TIẾNG VIỆT. "
            "Nếu lỡ trả lời bằng ngôn ngữ khác, bạn phải xin lỗi và trả lời lại bằng tiếng Việt. "
        )
        
        if not history:
            user_content = f"{vietnamese_reminder}Đây là câu hỏi của khách:\n\n{message}"
        else:
            user_content = message
        messages = history + [
            {
                "role": "user",
                "content": user_content,
            }
        ]
        
        # Get AI response
        try:
            ai_response = get_ai_response(messages, system_prompt)
            if not ai_response or not ai_response.strip():
                ai_response = "Xin lỗi, mình không thể tạo phản hồi lúc này. Vui lòng thử lại sau."
            record_conversation_turn(session_id, message, ai_response)
            
            return ChatResponse(
                response=ai_response,
                session_id=session_id
            )
        except Exception as e:
            print(f"[Chat] Error getting AI response: {e}")
            import traceback
            traceback.print_exc()
            # Trả về response lỗi thay vì raise exception
            error_response = "Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."
            record_conversation_turn(session_id, message, error_response)
            return ChatResponse(
                response=error_response,
                session_id=session_id
            )
        
    except Exception as e:
        print(f"[Chat] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        # Trả về response lỗi thay vì raise HTTPException
        try:
            error_response = "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại sau."
            record_conversation_turn(session_id, chat_message.message if hasattr(chat_message, 'message') else "", error_response)
            return ChatResponse(
                response=error_response,
                session_id=session_id if hasattr(chat_message, 'session_id') else "unknown"
            )
        except:
            # Nếu không thể tạo response, mới raise exception
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Xóa lịch sử hội thoại của session hiện tại"""
    clear_conversation_session(session_id)
    return {"message": "Session cleared", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)