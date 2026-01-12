import os
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from utils.ollama_client import ollama_client
from services.exercise_service import generate_exercise_response, is_exercise_related_query
from services.llm_service import get_ai_response
from services.conversation_service import (
    get_history as get_conversation_history,
    record_turn as record_conversation_turn,
    clear_session as clear_conversation_session,
    set_inbody_data,
    get_inbody_data,
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="The New Gym Exercise Chatbot API",
    description="API cho chatbot tư vấn bài tập gym sử dụng RAG",
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

# Chỉ sử dụng Ollama với deepseek-r1:14b

# Load system prompt
def load_system_prompt():
    try:
        with open("prompt_system.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Bạn là AI Assistant của The New Gym. Hỗ trợ khách hàng về bài tập gym và các câu hỏi khác về The New Gym."

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
    return {"message": "The New Gym Exercise Chatbot API", "status": "running"}

@app.get("/ai-status")
async def get_ai_status():
    """Kiểm tra trạng thái Ollama"""
    status = ollama_client.test_connection()
    return {
        "provider": "ollama",
        "model": ollama_client.model,
        "available": status["available"],
        "models": status["models"],
        "error": status["error"]
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage):
    """Xử lý tin nhắn chat"""
    try:
        session_id = chat_message.session_id
        message = chat_message.message
        history = get_conversation_history(session_id)
        
        # Parse InBody data từ message nếu có và lưu vào session
        from services.exercise_service import parse_inbody_from_message
        parsed_inbody = parse_inbody_from_message(message)
        if parsed_inbody:
            print(f"[Chat] Detected InBody data in message, saving to session {session_id}")
            set_inbody_data(session_id, parsed_inbody)
        
        # Load system prompt
        system_prompt = load_system_prompt()
        
        # Check if query is about exercises
        try:
            is_exercise_query = is_exercise_related_query(message)
            if is_exercise_query:
                try:
                    # Lấy InBody data từ session (có thể là vừa parse hoặc đã lưu trước đó)
                    inbody_data = get_inbody_data(session_id)
                    # Nếu vừa parse được InBody, ưu tiên dùng data vừa parse
                    if parsed_inbody:
                        inbody_data = parsed_inbody
                    exercise_response_text = generate_exercise_response(message, inbody_data=inbody_data, session_id=session_id)
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
                    # Continue to general LLM
        except Exception as e:
            print(f"[Chat] Error checking exercise query: {e}")
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

@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Xóa lịch sử hội thoại của session hiện tại"""
    clear_conversation_session(session_id)
    return {"message": "Session cleared", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)