import os
from typing import Dict, List

from utils.ollama_client import ollama_client


def get_ai_response(messages: List[Dict], system_prompt: str) -> str:
    """Chỉ sử dụng Ollama với deepseek-r1:14b"""
    try:
        if not ollama_client.is_available():
            return "Xin lỗi, Ollama service chưa sẵn sàng. Vui lòng chạy 'ollama serve' trước."
        return ollama_client.chat(messages, system_prompt)
    except Exception as e:
        return f"Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu: {str(e)}"

