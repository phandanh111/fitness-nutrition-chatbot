"""Constants cho Exercise và Rule Engine."""

# ============================================================================
# DIFFICULTY LEVELS
# ============================================================================

# Difficulty values (English)
DIFFICULTY_ADVANCED = "ADVANCED"
DIFFICULTY_MODERATE = "MODERATE"
DIFFICULTY_BASIC = "BASIC"

# Difficulty values (Vietnamese)
DIFFICULTY_NANG_CAO = "NÂNG CAO"
DIFFICULTY_TRUNG_BINH = "trung bình"
DIFFICULTY_CO_BAN = "cơ bản"

# Difficulty keywords (for matching)
DIFFICULTY_KEYWORDS_ADVANCED = ["advanced", "nâng cao"]
DIFFICULTY_KEYWORDS_MODERATE = ["moderate", "trung bình"]
DIFFICULTY_KEYWORDS_BASIC = ["basic", "cơ bản"]

# ============================================================================
# RISK TAGS
# ============================================================================

RISK_TAG_HIGH_PRESSURE_CORE = "HIGH_PRESSURE_CORE"
RISK_TAG_PRESSURE_HIGH = "PRESSURE_HIGH"

# ============================================================================
# BMI THRESHOLDS (Asian standard)
# ============================================================================

BMI_UNDERWEIGHT_THRESHOLD = 18.5
BMI_NORMAL_THRESHOLD = 23.0
BMI_OVERWEIGHT_THRESHOLD = 27.5
BMI_SEVERE_UNDERWEIGHT_THRESHOLD = 16.0  # BMI < 16: cần tăng cơ
BMI_SEVERE_OBESITY_THRESHOLD = 35.0  # BMI ≥ 35: béo phì nghiêm trọng

# ============================================================================
# BODY FAT THRESHOLDS (%)
# ============================================================================

# Male thresholds
BODY_FAT_MALE_LOW = 10
BODY_FAT_MALE_NORMAL = 20

# Female thresholds
BODY_FAT_FEMALE_LOW = 20
BODY_FAT_FEMALE_NORMAL = 30

# Unknown gender (average)
BODY_FAT_UNKNOWN_LOW = 15
BODY_FAT_UNKNOWN_NORMAL = 25

# Severe underweight thresholds (cần tăng cơ)
BODY_FAT_SEVERE_LOW_THRESHOLD = 8.0  # PBF < 8%: cần tăng cơ

# Severe obesity thresholds (béo phì nghiêm trọng)
BODY_FAT_SEVERE_HIGH_THRESHOLD = 40.0  # PBF ≥ 40%: béo phì nghiêm trọng

# ============================================================================
# CALORIE THRESHOLDS
# ============================================================================

CALORIE_LOW_THRESHOLD = 150
CALORIE_MEDIUM_THRESHOLD = 200
CALORIE_HIGH_THRESHOLD = 250

# ============================================================================
# RULE ENGINE SCORING VALUES
# ============================================================================

# Difficulty scoring
SCORE_DIFFICULTY_MODERATE = 3.0
SCORE_DIFFICULTY_BASIC = 2.0
SCORE_DIFFICULTY_ADVANCED = -2.0

# Calorie scoring
SCORE_CALORIE_HIGH = 2.0  # > 250
SCORE_CALORIE_LOW = -1.0  # < 150

# Risk tag scoring
SCORE_RISK_HIGH_PRESSURE = -3.0

# Goal filter bonuses
BONUS_FAT_LOSS_HIGH_CALORIE = 2.0  # calories > 200
BONUS_FAT_LOSS_MODERATE = 3.0
BONUS_FAT_LOSS_BASIC = 2.0

BONUS_OVERWEIGHT_MODERATE = 3.0
BONUS_OVERWEIGHT_BASIC = 2.0
BONUS_OVERWEIGHT_ADVANCED = -2.0
BONUS_OVERWEIGHT_FULL_BODY = 2.0
BONUS_OVERWEIGHT_LOWER_BODY = 1.0

BONUS_UNDERWEIGHT_MODERATE = 2.0
BONUS_UNDERWEIGHT_BASIC = 1.0

# Muscle gain bonuses (BMI < 16 hoặc PBF < 8%)
BONUS_MUSCLE_GAIN_STRENGTH = 4.0  # Ưu tiên strength training
BONUS_MUSCLE_GAIN_BASIC = 3.0  # Ưu tiên basic difficulty
BONUS_MUSCLE_GAIN_DUMBBELL = 2.0  # Ưu tiên dumbbell exercises

# Severe obesity bonuses (BMI ≥ 35 hoặc PBF ≥ 40%)
BONUS_SEVERE_OBESITY_FULL_BODY = 4.0  # Ưu tiên full body exercises
BONUS_SEVERE_OBESITY_BASIC = 3.0  # Ưu tiên basic difficulty
BONUS_SEVERE_OBESITY_MODERATE = 2.0  # Ưu tiên moderate difficulty

# ============================================================================
# MUSCLE GROUP KEYWORDS
# ============================================================================

MUSCLE_GROUP_FULL_BODY = ["toàn thân", "full body"]
MUSCLE_GROUP_LOWER_BODY = ["thân dưới", "lower body"]

# ============================================================================
# CENTRAL FAT DETECTION
# ============================================================================

CENTRAL_FAT_BMI_THRESHOLD = 23.0

# ============================================================================
# EXERCISE TYPE KEYWORDS
# ============================================================================

# Keywords để detect exercise types
EXERCISE_TYPE_BURN_KEYWORDS = ["burn", "burner", "burn out", "feel the burn"]
EXERCISE_TYPE_HIIT_KEYWORDS = ["hiit", "hiit-up", "high intensity"]
EXERCISE_TYPE_STRENGTH_KEYWORDS = ["strength", "strengthening", "power", "muscle"]
EXERCISE_TYPE_DUMBBELL_KEYWORDS = ["dumbbell", "dumbbells", "tạ đơn"]

# Keywords để detect HIGH_IMPACT exercises
EXERCISE_TYPE_HIGH_IMPACT_KEYWORDS = [
    "jump", "jumping", "jump up", "jump down", "plyometric", "burpee", 
    "sprint", "running", "chạy", "nhảy", "bật nhảy", "high impact"
]

# Keywords để detect TOO_MANY_ABS exercises
EXERCISE_TYPE_TOO_MANY_ABS_KEYWORDS = [
    "abs", "abdominal", "crunch", "sit-up", "bụng", "core", "six pack",
    "ab workout", "core workout", "bụng nhiều", "nhiều động tác bụng"
]
