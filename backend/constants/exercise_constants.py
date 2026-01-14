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

# ============================================================================
# MUSCLE GROUP KEYWORDS
# ============================================================================

MUSCLE_GROUP_FULL_BODY = ["toàn thân", "full body"]
MUSCLE_GROUP_LOWER_BODY = ["thân dưới", "lower body"]

# ============================================================================
# CENTRAL FAT DETECTION
# ============================================================================

CENTRAL_FAT_BMI_THRESHOLD = 23.0
