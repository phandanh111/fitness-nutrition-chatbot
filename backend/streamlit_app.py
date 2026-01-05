import os
import sys
import streamlit as st
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.exercise_service import generate_exercise_response, is_exercise_related_query, parse_inbody_from_message
from services.llm_service import get_ai_response
from services.conversation_service import (
    get_history as get_conversation_history,
    record_turn as record_conversation_turn,
    clear_session as clear_conversation_session,
    set_inbody_data,
    get_inbody_data,
)

# Load system prompt
def load_system_prompt():
    try:
        with open("prompt_system.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Bạn là AI Assistant của The New Gym. Hỗ trợ khách hàng về thông tin chi nhánh và các câu hỏi khác về The New Gym."

# Page configuration
st.set_page_config(
    page_title="The New Gym AI",
    page_icon="🏋️",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
    }
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
    }
    .welcome-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Welcome message
    welcome_msg = {
        "role": "assistant",
        "content": "Xin chào! Tôi là AI Assistant của The New Gym.\n\nTôi có thể hỗ trợ bạn:\n• Tư vấn bài tập gym và chương trình tập luyện\n• Gợi ý bài tập theo nhóm cơ, độ khó\n• Thông tin về lượng kcal tiêu thụ của từng bài\n\nBạn cần hỗ trợ gì hôm nay?"
    }
    st.session_state.messages.append(welcome_msg)

if "session_id" not in st.session_state:
    import time
    import random
    st.session_state.session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Cài đặt")
    
    # Clear chat button
    if st.button("Xóa lịch sử chat", use_container_width=True):
        logger.info(f"[SESSION] Clearing session: {st.session_state.session_id}")
        st.session_state.messages = []
        clear_conversation_session(st.session_state.session_id)
        # Reset welcome message
        welcome_msg = {
            "role": "assistant",
            "content": "Xin chào! Tôi là AI Assistant của The New Gym.\n\nTôi có thể hỗ trợ bạn:\n• Thông tin về các chi nhánh/clubs\n• Tư vấn dinh dưỡng và thể hình\n• Câu hỏi về dịch vụ của The New Gym\n• Tư vấn về chương trình tập luyện\n\nBạn cần hỗ trợ gì hôm nay?"
        }
        st.session_state.messages = [welcome_msg]
        st.rerun()
    
    st.divider()
    
    # AI Status
    st.subheader("🤖 Trạng thái AI")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
    if AI_PROVIDER.lower() == "ollama":
        from utils.ollama_client import ollama_client
        status = ollama_client.test_connection()
        if status["available"]:
            st.success("✅ Ollama đang hoạt động")
            if status["models"]:
                st.caption(f"Models: {', '.join(status['models'])}")
        else:
            st.error("❌ Ollama không khả dụng")
            st.caption(f"Lỗi: {status.get('error', 'Unknown')}")
    elif AI_PROVIDER.lower() == "deepseek":
        DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
        if DEEPSEEK_API_KEY:
            st.success("✅ DeepSeek API đã cấu hình")
        else:
            st.error("❌ Thiếu DEEPSEEK_API_KEY")

# Chat container
chat_container = st.container()

# Display chat messages
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Nhập tin nhắn của bạn..."):
    # Start timing
    start_time = time.time()
    session_id = st.session_state.session_id
    
    # Log incoming request
    message_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
    logger.info(f"[REQUEST] Session: {session_id[:20]}... | Message: {message_preview}")
    
    # Add user message to chat
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
            try:
                message = prompt
                history = get_conversation_history(session_id)
                history_length = len(history)
                
                # Load system prompt
                system_prompt = load_system_prompt()
                
                response_text = None
                response_type = None
                
                # Parse InBody data từ message nếu có
                inbody_data = parse_inbody_from_message(message)
                if inbody_data:
                    logger.info(f"[INBODY] Detected InBody data in message, saving to session {session_id[:20]}...")
                    set_inbody_data(session_id, inbody_data)
                    response_text = "Mình đã lưu thông tin InBody của bạn. Bây giờ bạn có thể hỏi về lịch tập hoặc bài tập phù hợp!"
                    response_type = "INBODY_SAVED"
                    record_conversation_turn(session_id, message, response_text)
                    logger.info(f"[RESPONSE] Type: INBODY_SAVED")
                
                # Check if query is about exercises
                if not response_text:
                    try:
                        is_exercise_query = is_exercise_related_query(message)
                        if is_exercise_query:
                            logger.info(f"[QUERY_TYPE] Detected: EXERCISE | Session: {session_id[:20]}...")
                            try:
                                # Lấy InBody data từ session nếu có
                                inbody_data = get_inbody_data(session_id)
                                exercise_response_text = generate_exercise_response(message, inbody_data=inbody_data, session_id=session_id)
                                if exercise_response_text:
                                    response_text = exercise_response_text
                                    response_type = "EXERCISE"
                                    record_conversation_turn(session_id, message, response_text)
                                    logger.info(f"[RESPONSE] Type: EXERCISE | Length: {len(response_text)} chars")
                            except Exception as e:
                                logger.error(f"[ERROR] Exercise response generation failed: {e}", exc_info=True)
                                st.error(f"Lỗi khi xử lý câu hỏi về bài tập: {e}")
                    except Exception as e:
                        logger.debug(f"[QUERY_CHECK] Exercise check failed: {e}")
                        pass
                
                # If no specific response, use general AI
                if not response_text:
                    logger.info(f"[QUERY_TYPE] Detected: GENERAL | Session: {session_id[:20]}... | History: {history_length} messages")
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
                        response_text = ai_response
                        response_type = "GENERAL"
                        record_conversation_turn(session_id, message, response_text)
                        logger.info(f"[RESPONSE] Type: GENERAL | Length: {len(response_text)} chars")
                    except Exception as e:
                        logger.error(f"[ERROR] General AI response failed: {e}", exc_info=True)
                        st.error(f"Lỗi khi lấy phản hồi từ AI: {e}")
                        response_text = "Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."
                        response_type = "ERROR"
                        record_conversation_turn(session_id, message, response_text)
                
                # Display response
                if response_text:
                    st.markdown(response_text)
                    assistant_message = {"role": "assistant", "content": response_text}
                    st.session_state.messages.append(assistant_message)
                    
                    # Log successful response
                    elapsed_time = time.time() - start_time
                    logger.info(
                        f"[SUCCESS] Session: {session_id[:20]}... | "
                        f"Type: {response_type or 'UNKNOWN'} | "
                        f"Response: {len(response_text)} chars | "
                        f"Time: {elapsed_time:.2f}s"
                    )
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                error_msg = "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại sau."
                logger.error(
                    f"[ERROR] Session: {session_id[:20]}... | "
                    f"Exception: {str(e)} | "
                    f"Time: {elapsed_time:.2f}s",
                    exc_info=True
                )
                st.error(error_msg)
                st.exception(e)
                assistant_message = {"role": "assistant", "content": error_msg}
                st.session_state.messages.append(assistant_message)

# Footer
st.divider()
