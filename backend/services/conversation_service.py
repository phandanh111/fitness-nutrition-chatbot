import os
import json
from collections import deque
from threading import Lock
from typing import Deque, Dict, List, Literal, Optional, Any

Role = Literal["user", "assistant"]

DEFAULT_MAX_MESSAGES = 12
MAX_MESSAGES = int(os.getenv("CHAT_HISTORY_MAX_MESSAGES", DEFAULT_MAX_MESSAGES))

_history: Dict[str, Deque[Dict[str, str]]] = {}
_inbody_data: Dict[str, Dict[str, Any]] = {}  # Store InBody data per session
_lock = Lock()


def _get_session_buffer(session_id: str) -> Deque[Dict[str, str]]:
    buffer = _history.get(session_id)
    if buffer is None:
        buffer = deque(maxlen=MAX_MESSAGES)
        _history[session_id] = buffer
    return buffer


def get_history(session_id: str) -> List[Dict[str, str]]:
    """Return a copy of chat history for the given session."""
    with _lock:
        buffer = _history.get(session_id)
        if not buffer:
            return []
        return [msg.copy() for msg in buffer]


def append_message(session_id: str, role: Role, content: str) -> None:
    """Append a message to the session history, trimming when needed."""
    normalized_content = (content or "").strip()
    if not normalized_content:
        return

    normalized_role: Role = "assistant" if role == "assistant" else "user"
    with _lock:
        buffer = _get_session_buffer(session_id)
        buffer.append({"role": normalized_role, "content": normalized_content})


def record_turn(session_id: str, user_message: str, assistant_message: Optional[str]) -> None:
    """Store a user → assistant turn."""
    append_message(session_id, "user", user_message)
    if assistant_message:
        append_message(session_id, "assistant", assistant_message)


def clear_session(session_id: str) -> None:
    """Remove conversation history for a specific session."""
    with _lock:
        _history.pop(session_id, None)


def clear_all_sessions() -> None:
    """Remove all stored sessions."""
    with _lock:
        _history.clear()
        _inbody_data.clear()


def set_inbody_data(session_id: str, inbody_data: Dict[str, Any]) -> None:
    """Lưu InBody data cho session."""
    with _lock:
        _inbody_data[session_id] = inbody_data


def get_inbody_data(session_id: str) -> Optional[Dict[str, Any]]:
    """Lấy InBody data cho session."""
    with _lock:
        return _inbody_data.get(session_id)


def clear_inbody_data(session_id: str) -> None:
    """Xóa InBody data cho session."""
    with _lock:
        _inbody_data.pop(session_id, None)

