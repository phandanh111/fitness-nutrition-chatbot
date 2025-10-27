"""
Tính toán TDEE và macro cho dinh dưỡng thể hình
Sử dụng công thức Harris-Benedict và Mifflin-St Jeor
"""

def calculate_bmr_harris_benedict(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Tính BMR (Basal Metabolic Rate) bằng công thức Harris-Benedict
    
    Args:
        weight_kg: Cân nặng (kg)
        height_cm: Chiều cao (cm)
        age: Tuổi
        gender: Giới tính ('male' hoặc 'female')
    
    Returns:
        BMR (kcal/ngày)
    """
    if gender.lower() == 'male':
        bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
    else:  # female
        bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
    
    return round(bmr, 2)

def calculate_bmr_mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Tính BMR bằng công thức Mifflin-St Jeor (chính xác hơn)
    
    Args:
        weight_kg: Cân nặng (kg)
        height_cm: Chiều cao (cm)
        age: Tuổi
        gender: Giới tính ('male' hoặc 'female')
    
    Returns:
        BMR (kcal/ngày)
    """
    if gender.lower() == 'male':
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:  # female
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    
    return round(bmr, 2)

def calculate_tdee(bmr: float, activity_level: str) -> float:
    """
    Tính TDEE (Total Daily Energy Expenditure) dựa trên BMR và mức độ hoạt động
    
    Args:
        bmr: BMR (kcal/ngày)
        activity_level: Mức độ hoạt động ('sedentary', 'light', 'moderate', 'active', 'very_active')
    
    Returns:
        TDEE (kcal/ngày)
    """
    activity_multipliers = {
        'sedentary': 1.2,      # Ít vận động
        'light': 1.375,        # Vận động nhẹ (1-3 buổi/tuần)
        'moderate': 1.55,      # Vận động vừa (3-5 buổi/tuần)
        'active': 1.725,       # Vận động nhiều (6-7 buổi/tuần)
        'very_active': 1.9     # Vận động rất nhiều (2 lần/ngày)
    }
    
    multiplier = activity_multipliers.get(activity_level.lower(), 1.55)
    return round(bmr * multiplier, 2)

def calculate_workout_tdee(bmr: float, workout_days_per_week: int) -> float:
    """
    Tính TDEE dựa trên số buổi tập/tuần
    
    Args:
        bmr: BMR (kcal/ngày)
        workout_days_per_week: Số buổi tập/tuần
    
    Returns:
        TDEE (kcal/ngày)
    """
    if workout_days_per_week == 0:
        multiplier = 1.2
    elif workout_days_per_week <= 2:
        multiplier = 1.375
    elif workout_days_per_week <= 4:
        multiplier = 1.55
    elif workout_days_per_week <= 6:
        multiplier = 1.725
    else:  # 7+ buổi/tuần
        multiplier = 1.9
    
    return round(bmr * multiplier, 2)

def calculate_goal_calories(tdee: float, goal: str) -> float:
    """
    Tính calo mục tiêu dựa trên TDEE và mục tiêu
    
    Args:
        tdee: TDEE (kcal/ngày)
        goal: Mục tiêu ('bulk', 'cut', 'maintain')
    
    Returns:
        Calo mục tiêu (kcal/ngày)
    """
    if goal.lower() == 'bulk' or goal.lower() == 'tăng cơ':
        return round(tdee * 1.1, 2)  # +10% để tăng cơ
    elif goal.lower() == 'cut' or goal.lower() == 'giảm mỡ':
        return round(tdee * 0.85, 2)  # -15% để giảm mỡ
    else:  # maintain hoặc giữ cân
        return round(tdee, 2)

def calculate_macros(calories: float, goal: str) -> dict:
    """
    Tính macro (protein, carb, fat) dựa trên calo và mục tiêu
    
    Args:
        calories: Tổng calo/ngày
        goal: Mục tiêu ('bulk', 'cut', 'maintain')
    
    Returns:
        Dict chứa protein, carb, fat (gram) và tỷ lệ %
    """
    if goal.lower() == 'bulk' or goal.lower() == 'tăng cơ':
        # Tăng cơ: 30% protein, 45% carb, 25% fat
        protein_ratio = 0.30
        carb_ratio = 0.45
        fat_ratio = 0.25
    elif goal.lower() == 'cut' or goal.lower() == 'giảm mỡ':
        # Giảm mỡ: 35% protein, 35% carb, 30% fat
        protein_ratio = 0.35
        carb_ratio = 0.35
        fat_ratio = 0.30
    else:  # maintain
        # Giữ cân: 25% protein, 50% carb, 25% fat
        protein_ratio = 0.25
        carb_ratio = 0.50
        fat_ratio = 0.25
    
    # Tính gram cho mỗi macro
    protein_grams = round((calories * protein_ratio) / 4, 1)  # 1g protein = 4 kcal
    carb_grams = round((calories * carb_ratio) / 4, 1)        # 1g carb = 4 kcal
    fat_grams = round((calories * fat_ratio) / 9, 1)          # 1g fat = 9 kcal
    
    return {
        'protein': {
            'grams': protein_grams,
            'percentage': round(protein_ratio * 100, 1)
        },
        'carb': {
            'grams': carb_grams,
            'percentage': round(carb_ratio * 100, 1)
        },
        'fat': {
            'grams': fat_grams,
            'percentage': round(fat_ratio * 100, 1)
        }
    }

def calculate_nutrition_plan(weight_kg: float, height_cm: float, age: int, 
                           gender: str, workout_days_per_week: int, goal: str) -> dict:
    """
    Tính toán kế hoạch dinh dưỡng hoàn chỉnh
    
    Args:
        weight_kg: Cân nặng (kg)
        height_cm: Chiều cao (cm)
        age: Tuổi
        gender: Giới tính
        workout_days_per_week: Số buổi tập/tuần
        goal: Mục tiêu
    
    Returns:
        Dict chứa tất cả thông tin dinh dưỡng
    """
    # Tính BMR bằng công thức Mifflin-St Jeor (chính xác hơn)
    bmr = calculate_bmr_mifflin_st_jeor(weight_kg, height_cm, age, gender)
    
    # Tính TDEE dựa trên số buổi tập
    tdee = calculate_workout_tdee(bmr, workout_days_per_week)
    
    # Tính calo mục tiêu
    goal_calories = calculate_goal_calories(tdee, goal)
    
    # Tính macro
    macros = calculate_macros(goal_calories, goal)
    
    return {
        'bmr': bmr,
        'tdee': tdee,
        'goal_calories': goal_calories,
        'macros': macros,
        'user_info': {
            'weight_kg': weight_kg,
            'height_cm': height_cm,
            'age': age,
            'gender': gender,
            'workout_days_per_week': workout_days_per_week,
            'goal': goal
        }
    }
