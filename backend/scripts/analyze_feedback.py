
import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FEEDBACK_FILE = DATA_DIR / "feedback.jsonl"

def analyze_feedback():
    if not FEEDBACK_FILE.exists():
        print("No feedback data found.")
        return

    print("Analyzing feedback data...")
    
    total = 0
    likes = 0
    dislikes = 0
    
    # Segmented analysis
    fat_loss_feedback = {"like": 0, "dislike": 0}
    muscle_gain_feedback = {"like": 0, "dislike": 0}
    
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                ftype = entry.get("feedback_type")
                signals = entry.get("inbody_signals") or {}
                
                total += 1
                if ftype == "like":
                    likes += 1
                elif ftype == "dislike":
                    dislikes += 1
                
                # Analyze Segments
                # Fat Loss Group
                if signals.get("body_fat_status") == "HIGH":
                    fat_loss_feedback[ftype] += 1
                
                # Muscle Gain Group
                if signals.get("bmi_status") == "UNDERWEIGHT":
                    muscle_gain_feedback[ftype] += 1
                    
            except Exception as e:
                print(f"Error parsing line: {e}")

    print("-" * 30)
    print(f"Total Feedback: {total}")
    if total > 0:
        print(f"Likes: {likes} ({likes/total*100:.1f}%)")
        print(f"Dislikes: {dislikes} ({dislikes/total*100:.1f}%)")
    else:
        print("Likes: 0 (0.0%)")
        print("Dislikes: 0 (0.0%)")
    print("-" * 30)
    print("Segment Analysis:")
    print(f"Fat Loss Users (High BF): {fat_loss_feedback}")
    print(f"Muscle Gain Users (Underweight): {muscle_gain_feedback}")
    print("-" * 30)
    
    # Recommendation Logic
    recommendations = []
    
    # If Muscle Gain users dislike > 40%, maybe we are too gentle?
    muscle_total = muscle_gain_feedback["like"] + muscle_gain_feedback["dislike"]
    if muscle_total > 0:
        dislike_ratio = muscle_gain_feedback["dislike"] / muscle_total
        if dislike_ratio > 0.4:
            recommendations.append("High Dislike rate in Muscle Gain group. Consider reducing 'BONUS_MUSCLE_GAIN_BASIC' or increasing difficulty?")
            
    # If Fat Loss users like > 70%, our Calorie Weighting is working!
    fat_total = fat_loss_feedback["like"] + fat_loss_feedback["dislike"]
    if fat_total > 0:
         like_ratio = fat_loss_feedback["like"] / fat_total
         if like_ratio > 0.8:
             recommendations.append("Fat Loss weighting is working well. Keep 'WEIGHT_ADJUSTMENT_FAT_LOSS' as is.")

    if recommendations:
        print("RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"- {rec}")
    else:
        print("No specific parameter adjustments needed based on current data.")

if __name__ == "__main__":
    analyze_feedback()
