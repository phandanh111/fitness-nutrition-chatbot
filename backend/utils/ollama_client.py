"""
Ollama client để giao tiếp với Ollama models
"""

import os
import requests
import json
from typing import List, Dict, Optional

class OllamaClient:
    def __init__(self, base_url: str = None, model: str = None):
        # Đọc từ environment variables nếu không được truyền vào
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "deepseek-r1:7b")
        self.api_url = f"{self.base_url}/api/chat"
    
    def set_model(self, model: str) -> None:
        """Cập nhật model được sử dụng."""
        self.model = model
        print(f"[OllamaClient] Model changed to: {model}")
    
    def is_available(self) -> bool:
        """
        Kiểm tra Ollama service có sẵn sàng không
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """
        Lấy danh sách các model có sẵn
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except:
            return []
    
    def chat(self, messages: List[Dict], system_prompt: str = "") -> str:
        """
        Gửi tin nhắn đến Ollama và nhận phản hồi
        
        Args:
            messages: Danh sách tin nhắn [{"role": "user", "content": "..."}]
            system_prompt: System prompt cho model
        
        Returns:
            Phản hồi từ model
        """
        try:
            # Chuẩn bị payload cho Ollama
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "2000"))  # Tăng max_tokens cho model lớn
                }
            }
            
            # Thêm system prompt nếu có
            if system_prompt:
                payload["messages"].insert(0, {
                    "role": "system", 
                    "content": system_prompt
                })
            
            # Gửi request với timeout có thể config từ env (mặc định 120s cho model lớn)
            timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT", "120"))
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=timeout_seconds
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('message', {}).get('content', 'Xin lỗi, không thể tạo phản hồi.')
            else:
                return f"Lỗi API: {response.status_code} - {response.text}"
                
        except requests.exceptions.Timeout:
            return "Xin lỗi, request timeout. Vui lòng thử lại."
        except requests.exceptions.ConnectionError:
            return "Không thể kết nối đến Ollama. Vui lòng đảm bảo Ollama đang chạy."
        except Exception as e:
            return f"Lỗi không xác định: {str(e)}"
    
    def test_connection(self) -> Dict:
        """
        Test kết nối và trả về thông tin chi tiết
        """
        result = {
            "available": False,
            "models": [],
            "error": None
        }
        
        try:
            # Test kết nối
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                result["available"] = True
                data = response.json()
                result["models"] = [model['name'] for model in data.get('models', [])]
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text}"
        except requests.exceptions.ConnectionError:
            result["error"] = "Không thể kết nối đến Ollama service"
        except Exception as e:
            result["error"] = str(e)
        
        return result

# Tạo instance global
ollama_client = OllamaClient()
