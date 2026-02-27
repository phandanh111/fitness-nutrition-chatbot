
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Path to feedback file
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FEEDBACK_FILE = DATA_DIR / "feedback.jsonl"

def save_feedback(
    message_id: str,
    user_query: str,
    bot_response: str,
    feedback_type: str,  # "like" or "dislike"
    inbody_data: Optional[Dict[str, Any]] = None,
    recommended_exercises: Optional[list] = None
) -> bool:
    """
    Save user feedback to a JSONL file.
    
    Args:
        message_id: Unique ID for the message
        user_query: The user's question
        bot_response: The bot's answer
        feedback_type: "like" or "dislike"
        inbody_data: User's InBody data (for context)
        recommended_exercises: List of exercises recommended (if any)
        
    Returns:
        bool: True if saved successfully
    """
    try:
        # Create data directory if not exists
        if not DATA_DIR.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
        feedback_entry = {
            "timestamp": time.time(),
            "message_id": message_id,
            "feedback_type": feedback_type,
            "user_query": user_query,
            "bot_response": bot_response,
            "inbody_signals": inbody_data, # Normalize or keep raw? Keep raw for now
            "recommended_exercises": recommended_exercises
        }
        
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry, ensure_ascii=False) + "\n")
            
        print(f"[FeedbackService] Saved {feedback_type} feedback for message {message_id}")
        return True
    except Exception as e:
        print(f"[FeedbackService] Error saving feedback: {e}")
        return False

def get_feedback_stats() -> Dict[str, int]:
    """Get basic feedback statistics."""
    stats = {"like": 0, "dislike": 0, "total": 0}
    try:
        if not FEEDBACK_FILE.exists():
            return stats
            
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    ftype = entry.get("feedback_type")
                    if ftype in stats:
                        stats[ftype] += 1
                    stats["total"] += 1
                except:
                    pass
        return stats
    except Exception:
        return stats
