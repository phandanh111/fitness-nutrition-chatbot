import os
import sys
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.club_service import generate_club_response, is_club_related_query
from services.exercise_service import generate_exercise_response, is_exercise_related_query
from services.terms_service import generate_terms_response, is_terms_related_query
from services.llm_service import get_ai_response
from services.conversation_service import (
    get_history as get_conversation_history,
    record_turn as record_conversation_turn,
    clear_session as clear_conversation_session,
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
        "content": "Xin chào! Tôi là AI Assistant của The New Gym.\n\nTôi có thể hỗ trợ bạn:\n• Thông tin về các chi nhánh/clubs\n• Tư vấn dinh dưỡng và thể hình\n• Câu hỏi về dịch vụ của The New Gym\n• Tư vấn về chương trình tập luyện\n\nBạn cần hỗ trợ gì hôm nay?"
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
    # Add user message to chat
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
            try:
                session_id = st.session_state.session_id
                message = prompt
                history = get_conversation_history(session_id)
                
                # Load system prompt
                system_prompt = load_system_prompt()
                
                response_text = None
                
                # Check if query is about terms (điều khoản điều kiện)
                try:
                    is_terms_query = is_terms_related_query(message)
                    if is_terms_query:
                        try:
                            terms_response_text = generate_terms_response(message)
                            if terms_response_text:
                                response_text = terms_response_text
                                record_conversation_turn(session_id, message, response_text)
                        except Exception as e:
                            st.error(f"Lỗi khi xử lý câu hỏi về điều khoản: {e}")
                except Exception as e:
                    pass
                
                # Check if query is about exercises
                if not response_text:
                    try:
                        is_exercise_query = is_exercise_related_query(message)
                        if is_exercise_query:
                            try:
                                exercise_response_text = generate_exercise_response(message)
                                if exercise_response_text:
                                    response_text = exercise_response_text
                                    record_conversation_turn(session_id, message, response_text)
                            except Exception as e:
                                st.error(f"Lỗi khi xử lý câu hỏi về bài tập: {e}")
                    except Exception as e:
                        pass
                
                # Check if query is about clubs
                if not response_text:
                    try:
                        is_club_query = is_club_related_query(message)
                        if is_club_query:
                            try:
                                club_response_text = generate_club_response(message)
                                if club_response_text:
                                    response_text = club_response_text
                                    record_conversation_turn(session_id, message, response_text)
                            except Exception as e:
                                st.error(f"Lỗi khi xử lý câu hỏi về chi nhánh: {e}")
                    except Exception as e:
                        pass
                
                # If no specific response, use general AI
                if not response_text:
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
                        record_conversation_turn(session_id, message, response_text)
                    except Exception as e:
                        st.error(f"Lỗi khi lấy phản hồi từ AI: {e}")
                        response_text = "Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."
                        record_conversation_turn(session_id, message, response_text)
                
                # Display response
                if response_text:
                    st.markdown(response_text)
                    assistant_message = {"role": "assistant", "content": response_text}
                    st.session_state.messages.append(assistant_message)
                
            except Exception as e:
                error_msg = "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại sau."
                st.error(error_msg)
                st.exception(e)
                assistant_message = {"role": "assistant", "content": error_msg}
                st.session_state.messages.append(assistant_message)

# Footer
st.divider()
