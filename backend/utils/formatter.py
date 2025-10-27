"""
Các hàm format dữ liệu cho chatbot dinh dưỡng
"""

def format_nutrition_info(nutrition_plan: dict) -> str:
    """
    Format thông tin dinh dưỡng thành text dễ đọc
    
    Args:
        nutrition_plan: Dict chứa thông tin dinh dưỡng từ calculator.py
    
    Returns:
        String được format
    """
    user = nutrition_plan['user_info']
    
    text = f"""
📊 **THÔNG TIN DINH DƯỠNG CỦA BẠN**

👤 **Thông tin cá nhân:**
- Chiều cao: {user['height_cm']}cm
- Cân nặng: {user['weight_kg']}kg
- Tuổi: {user['age']}, Giới tính: {user['gender']}
- Mục tiêu: {user['goal']}
- Số buổi tập/tuần: {user['workout_days_per_week']}

⚡ **Năng lượng:**
- BMR (chuyển hóa cơ bản): {nutrition_plan['bmr']} kcal/ngày
- TDEE (tổng tiêu hao): {nutrition_plan['tdee']} kcal/ngày
- **Calo mục tiêu: {nutrition_plan['goal_calories']} kcal/ngày**

🥗 **Macronutrients:**
- **Protein**: {nutrition_plan['macros']['protein']['grams']}g ({nutrition_plan['macros']['protein']['percentage']}%)
- **Carbohydrate**: {nutrition_plan['macros']['carb']['grams']}g ({nutrition_plan['macros']['carb']['percentage']}%)
- **Fat**: {nutrition_plan['macros']['fat']['grams']}g ({nutrition_plan['macros']['fat']['percentage']}%)
"""
    return text

def format_meal_suggestion(meal_type: str, calories: int, protein: int, carb: int, fat: int, 
                          foods: list) -> str:
    """
    Format gợi ý bữa ăn
    
    Args:
        meal_type: Loại bữa ăn (sáng, trưa, tối, phụ)
        calories: Tổng calo
        protein: Protein (g)
        carb: Carb (g)
        fat: Fat (g)
        foods: List các món ăn với format [{"name": "tên món", "amount": "lượng", "calories": calo}]
    
    Returns:
        String được format
    """
    text = f"\n🍽️ **{meal_type.upper()}** (~{calories} kcal)\n"
    text += f"Macro: P:{protein}g | C:{carb}g | F:{fat}g\n\n"
    
    for food in foods:
        text += f"• {food['name']}: {food['amount']} (~{food['calories']} kcal)\n"
    
    return text

def format_daily_menu(nutrition_plan: dict) -> str:
    """
    Tạo thực đơn mẫu cho cả ngày dựa trên thông tin dinh dưỡng
    
    Args:
        nutrition_plan: Dict chứa thông tin dinh dưỡng
    
    Returns:
        String thực đơn được format
    """
    goal = nutrition_plan['user_info']['goal'].lower()
    total_calories = nutrition_plan['goal_calories']
    
    # Chia calo cho các bữa ăn
    if goal in ['bulk', 'tăng cơ']:
        # Tăng cơ: 4 bữa chính + 2 bữa phụ
        breakfast_cal = int(total_calories * 0.25)  # 25%
        lunch_cal = int(total_calories * 0.30)      # 30%
        dinner_cal = int(total_calories * 0.25)     # 25%
        snack1_cal = int(total_calories * 0.10)     # 10%
        snack2_cal = int(total_calories * 0.10)     # 10%
    else:
        # Giảm mỡ/giữ cân: 3 bữa chính + 1 bữa phụ
        breakfast_cal = int(total_calories * 0.30)  # 30%
        lunch_cal = int(total_calories * 0.35)      # 35%
        dinner_cal = int(total_calories * 0.25)     # 25%
        snack_cal = int(total_calories * 0.10)      # 10%
    
    text = "\n🍽️ **THỰC ĐƠN MẪU CHO NGÀY**\n"
    text += "=" * 50 + "\n"
    
    # Bữa sáng
    if goal in ['bulk', 'tăng cơ']:
        breakfast_foods = [
            {"name": "Yến mạch", "amount": "80g", "calories": int(breakfast_cal * 0.4)},
            {"name": "Sữa tươi không đường", "amount": "200ml", "calories": int(breakfast_cal * 0.2)},
            {"name": "Chuối", "amount": "1 quả", "calories": int(breakfast_cal * 0.2)},
            {"name": "Hạt chia", "amount": "1 thìa", "calories": int(breakfast_cal * 0.1)},
            {"name": "Mật ong", "amount": "1 thìa", "calories": int(breakfast_cal * 0.1)}
        ]
    else:
        breakfast_foods = [
            {"name": "Trứng", "amount": "2 quả", "calories": int(breakfast_cal * 0.3)},
            {"name": "Bánh mì đen", "amount": "2 lát", "calories": int(breakfast_cal * 0.4)},
            {"name": "Bơ", "amount": "1 thìa", "calories": int(breakfast_cal * 0.2)},
            {"name": "Cà chua", "amount": "1 quả", "calories": int(breakfast_cal * 0.1)}
        ]
    
    text += format_meal_suggestion("Bữa sáng", breakfast_cal, 
                                  int(breakfast_cal * 0.3 / 4), int(breakfast_cal * 0.5 / 4), 
                                  int(breakfast_cal * 0.2 / 9), breakfast_foods)
    
    # Bữa trưa
    if goal in ['bulk', 'tăng cơ']:
        lunch_foods = [
            {"name": "Ức gà", "amount": "150g", "calories": int(lunch_cal * 0.4)},
            {"name": "Cơm trắng", "amount": "120g", "calories": int(lunch_cal * 0.4)},
            {"name": "Rau xanh", "amount": "100g", "calories": int(lunch_cal * 0.1)},
            {"name": "Dầu olive", "amount": "1 thìa", "calories": int(lunch_cal * 0.1)}
        ]
    else:
        lunch_foods = [
            {"name": "Cá hồi", "amount": "120g", "calories": int(lunch_cal * 0.4)},
            {"name": "Khoai lang", "amount": "100g", "calories": int(lunch_cal * 0.3)},
            {"name": "Salad rau", "amount": "150g", "calories": int(lunch_cal * 0.1)},
            {"name": "Dầu olive", "amount": "1 thìa", "calories": int(lunch_cal * 0.2)}
        ]
    
    text += format_meal_suggestion("Bữa trưa", lunch_cal,
                                  int(lunch_cal * 0.35 / 4), int(lunch_cal * 0.45 / 4),
                                  int(lunch_cal * 0.2 / 9), lunch_foods)
    
    # Bữa tối
    if goal in ['bulk', 'tăng cơ']:
        dinner_foods = [
            {"name": "Thịt bò", "amount": "120g", "calories": int(dinner_cal * 0.4)},
            {"name": "Khoai tây", "amount": "150g", "calories": int(dinner_cal * 0.3)},
            {"name": "Rau củ", "amount": "100g", "calories": int(dinner_cal * 0.1)},
            {"name": "Dầu olive", "amount": "1 thìa", "calories": int(dinner_cal * 0.2)}
        ]
    else:
        dinner_foods = [
            {"name": "Ức gà", "amount": "100g", "calories": int(dinner_cal * 0.4)},
            {"name": "Rau xanh", "amount": "200g", "calories": int(dinner_cal * 0.2)},
            {"name": "Quinoa", "amount": "80g", "calories": int(dinner_cal * 0.3)},
            {"name": "Dầu olive", "amount": "1 thìa", "calories": int(dinner_cal * 0.1)}
        ]
    
    text += format_meal_suggestion("Bữa tối", dinner_cal,
                                  int(dinner_cal * 0.35 / 4), int(dinner_cal * 0.45 / 4),
                                  int(dinner_cal * 0.2 / 9), dinner_foods)
    
    # Bữa phụ
    if goal in ['bulk', 'tăng cơ']:
        text += format_meal_suggestion("Bữa phụ 1 (trước tập)", snack1_cal,
                                      int(snack1_cal * 0.4 / 4), int(snack1_cal * 0.5 / 4),
                                      int(snack1_cal * 0.1 / 9), [
                                          {"name": "Chuối", "amount": "1 quả", "calories": int(snack1_cal * 0.6)},
                                          {"name": "Whey protein", "amount": "1 scoop", "calories": int(snack1_cal * 0.4)}
                                      ])
        
        text += format_meal_suggestion("Bữa phụ 2 (sau tập)", snack2_cal,
                                      int(snack2_cal * 0.5 / 4), int(snack2_cal * 0.3 / 4),
                                      int(snack2_cal * 0.2 / 9), [
                                          {"name": "Sữa tươi", "amount": "250ml", "calories": int(snack2_cal * 0.4)},
                                          {"name": "Whey protein", "amount": "1 scoop", "calories": int(snack2_cal * 0.4)},
                                          {"name": "Hạt óc chó", "amount": "10g", "calories": int(snack2_cal * 0.2)}
                                      ])
    else:
        text += format_meal_suggestion("Bữa phụ", snack_cal,
                                      int(snack_cal * 0.4 / 4), int(snack_cal * 0.4 / 4),
                                      int(snack_cal * 0.2 / 9), [
                                          {"name": "Hạt hạnh nhân", "amount": "15g", "calories": int(snack_cal * 0.6)},
                                          {"name": "Táo", "amount": "1 quả", "calories": int(snack_cal * 0.4)}
                                      ])
    
    text += "\n" + "=" * 50
    text += f"\n📊 **TỔNG KẾT NGÀY:** {total_calories} kcal"
    text += f"\n🥗 **Macro tổng:** P:{nutrition_plan['macros']['protein']['grams']}g | C:{nutrition_plan['macros']['carb']['grams']}g | F:{nutrition_plan['macros']['fat']['grams']}g"
    
    return text

def format_quick_tips(goal: str) -> str:
    """
    Tạo tips nhanh dựa trên mục tiêu
    
    Args:
        goal: Mục tiêu của người dùng
    
    Returns:
        String tips được format
    """
    tips = {
        'bulk': [
            "💪 Ăn đủ calo: +300-500 kcal so với TDEE",
            "🥩 Protein cao: 1.6-2.2g/kg cân nặng",
            "⏰ Ăn 4-6 bữa/ngày để đảm bảo năng lượng",
            "💧 Uống đủ nước: 3-4 lít/ngày",
            "🏋️ Tập luyện đều đặn để kích thích tăng cơ"
        ],
        'cut': [
            "🔥 Calo thâm hụt: -300-500 kcal so với TDEE",
            "🥗 Ăn nhiều rau xanh để no lâu",
            "⏰ Ăn 3 bữa chính + 1 bữa phụ",
            "💧 Uống nước trước bữa ăn để giảm cảm giác đói",
            "🏃‍♂️ Kết hợp cardio và strength training"
        ],
        'maintain': [
            "⚖️ Ăn đúng calo TDEE để giữ cân",
            "🥗 Cân bằng macro: 25% protein, 50% carb, 25% fat",
            "⏰ Ăn đều đặn 3 bữa/ngày",
            "💧 Uống đủ nước: 2-3 lít/ngày",
            "🏋️ Duy trì tập luyện để giữ cơ bắp"
        ]
    }
    
    goal_key = goal.lower()
    if goal_key in ['tăng cơ']:
        goal_key = 'bulk'
    elif goal_key in ['giảm mỡ']:
        goal_key = 'cut'
    elif goal_key in ['giữ cân']:
        goal_key = 'maintain'
    
    goal_tips = tips.get(goal_key, tips['maintain'])
    
    text = "\n💡 **TIPS QUAN TRỌNG:**\n"
    for tip in goal_tips:
        text += f"{tip}\n"
    
    return text
