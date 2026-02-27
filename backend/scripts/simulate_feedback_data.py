
import json
import random
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FEEDBACK_FILE = DATA_DIR / "feedback.jsonl"

def generate_mock_feedback():
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating mock feedback to {FEEDBACK_FILE}...")
    
    entries = []
    
    # Scene 1: Fat Loss Users LIKE High Calorie Exercises (Success Case)
    for _ in range(10):
        entries.append({
            "timestamp": time.time(),
            "message_id": f"mock_{random.randint(10000,99999)}",
            "feedback_type": "like",
            "user_query": "Bài tập giảm cân",
            "inbody_signals": {"body_fat_status": "HIGH"},
            "recommended_exercises": [{"name": "Burpees", "calories": 300}, {"name": "Jumping Jacks", "calories": 250}]
        })

    # Scene 2: Muscle Gain Users DISLIKE Basic Exercises (They want harder stuff?)
    # Suggests we might need to lower BONUS_MUSCLE_GAIN_BASIC or increase difficulty preference?
    for _ in range(5):
        entries.append({
            "timestamp": time.time(),
            "message_id": f"mock_{random.randint(10000,99999)}",
            "feedback_type": "dislike",
            "user_query": "Bài tập tăng cơ",
            "inbody_signals": {"bmi_status": "UNDERWEIGHT", "muscle_status": "LOW"},
            "recommended_exercises": [{"name": "Push up basic", "difficulty": "BASIC"}]
        })
        
    # Scene 3: General positive usage
    for _ in range(5):
         entries.append({
            "timestamp": time.time(),
            "message_id": f"mock_{random.randint(10000,99999)}",
            "feedback_type": "like",
            "user_query": "Bài tập ngực",
            "inbody_signals": {"body_fat_status": "NORMAL"},
            "recommended_exercises": [{"name": "Bench Press"}]
        })

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"Generated {len(entries)} mock feedback entries.")

if __name__ == "__main__":
    generate_mock_feedback()
