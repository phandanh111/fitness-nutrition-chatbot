import os
import requests
from typing import Dict, List

from utils.ollama_client import ollama_client

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def get_ai_response(messages: List[Dict], system_prompt: str) -> str:
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
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return (data["choices"][0]["message"]["content"] or "").strip()
    except requests.RequestException as e:
        return f"Lỗi DeepSeek: {str(e)}"

