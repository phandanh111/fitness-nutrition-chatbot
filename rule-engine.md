# 🧠 Rule Engine – Gợi Ý Bài Tập Dựa Trên InBody

Tài liệu này dành cho **developer** triển khai Rule Engine gợi ý bài tập dựa trên dữ liệu InBody.

Mục tiêu: xây dựng hệ thống **deterministic – an toàn – dễ debug – scale tốt**, trong đó **Rule Engine là bộ quyết định**, AI chỉ dùng để trình bày kết quả.

---

## 1. Tổng quan kiến trúc

```
User Query → RAG (Semantic Search) → Rule Engine → Ranked Exercises → AI Presentation
```

### Phân vai

- **RAG (Semantic Search)**: Tìm danh sách bài tập ứng viên dựa trên query của user
  - Ví dụ: "bài tập ngực" → tìm các bài tập liên quan đến ngực
  - Trả về top K exercises với similarity score
- **Rule Engine**: Quyết định bài tập nào được phép, ưu tiên bài nào dựa trên InBody
  - Nhận danh sách từ RAG (hoặc toàn bộ bài tập nếu không có query cụ thể)
  - Filter và rank lại theo safety rules và goal bias
- **AI (LLM)**: Diễn giải kết quả (không quyết định logic)

> ⚠️ Nếu AI tắt, hệ thống vẫn phải trả về danh sách bài tập an toàn.

### Khi nào cần RAG?

- **Có query cụ thể**: User hỏi "bài tập ngực", "bài tập giảm mỡ" → **CẦN RAG** để tìm bài tập liên quan
- **Không có query cụ thể**: User muốn tất cả bài tập, tạo workout plan → **KHÔNG CẦN RAG**, Rule Engine xử lý toàn bộ danh sách

---

## 2. Nguyên tắc bắt buộc

1. Rule Engine **không dùng AI**
2. Rule Engine **không đọc text tự do** (description, name)
3. Rule Engine **chỉ làm việc với dữ liệu đã chuẩn hóa**
4. Cùng input → **luôn cho cùng output**
5. Mọi quyết định phải **trace & giải thích được**

---

## 3. Input của Rule Engine

### 3.1 User Physiology Signals (chuẩn hóa từ InBody)

```json
{
  "bmi_status": "OVERWEIGHT",
  "body_fat_status": "HIGH",
  "muscle_status": "NORMAL",
  "central_fat": true,
  "bmi_value": 25.3,
  "pbf_value": 22.5
}
```

> **Lưu ý**: `bmi_value` và `pbf_value` là giá trị raw để check các ngưỡng cụ thể (ví dụ: BMI < 16, PBF < 8%).

**Quy ước chuẩn hóa**:

- `bmi_status`:

  - `UNDERWEIGHT` (<18.5)
  - `NORMAL` (18.5–23)
  - `OVERWEIGHT` (23–27.5)
  - `OBESE` (>=27.5)

- `body_fat_status` (theo giới tính):

  - Nam > 20% → `HIGH`
  - Nữ > 30% → `HIGH`

- `central_fat = true` nếu:

  - `segmental_fat.trunk_status == "Over"`

---

### 3.2 Exercise Metadata (từ exercise.md)

Mỗi bài tập **bắt buộc** phải được parse thành metadata:

```json
{
  "id": "chest_builder",
  "difficulty": "MODERATE",
  "calorie": 280,
  "muscle_groups": ["CHEST"],
  "risk_tags": ["HIGH_PRESSURE_CORE"]
}
```

#### Difficulty enum

- `BASIC`
- `MODERATE`
- `ADVANCED`

#### Risk Tags chuẩn

- `HIGH_PRESSURE_CORE` – áp lực ổ bụng cao (Valsalva, crunch nặng)
- `PRESSURE_HIGH` – áp lực cao (khớp, cơ)
- `NONE` – không có rủi ro

---

## 4. Quy trình xử lý tổng thể

```
1. Nhận User Query + InBody data
2. (Tùy chọn) RAG: Tìm bài tập liên quan đến query → danh sách ứng viên
3. Chuẩn hóa InBody → physiology signals
4. Lớp 1: Lọc an toàn (Hard Block)
5. Lớp 2: Cộng điểm theo mục tiêu
6. Lớp 3: Tính điểm & sắp xếp
7. Trả về top N bài tập
```

**Lưu ý**: Nếu không có query cụ thể (ví dụ: tạo workout plan), bỏ qua bước 2 và Rule Engine xử lý toàn bộ danh sách bài tập.

---

## 5. Lớp 1 – Lọc an toàn (Hard Block)

> ❗ Bài tập bị block ở bước này **không được chấm điểm**.

### Rule 1 – Người có mỡ bụng

```
IF central_fat == true
AND risk_tags CONTAIN "HIGH_PRESSURE_CORE"
→ BLOCK
```

### Rule 2 – Người mỡ cao

```
IF body_fat_status == "HIGH"
AND difficulty == "ADVANCED"
→ BLOCK
```

### Rule 3 – Người béo phì

```
IF bmi_status == "OBESE"
AND difficulty == "ADVANCED"
→ BLOCK
```

### Rule 4 – Người thiếu cân nghiêm trọng

```
IF BMI < 16 OR PBF < 8%
AND (exercise_type == "BURN" OR exercise_type == "HIIT" OR calorie > 250)
→ BLOCK
```

> **Mục tiêu**: Tránh các bài tập đốt calo cao, ưu tiên tăng cơ.

### Rule 5 – Người béo phì nghiêm trọng

```
IF BMI ≥ 35 OR PBF ≥ 40%
AND (exercise_type == "HIGH_IMPACT" OR exercise_type == "TOO_MANY_ABS")
→ BLOCK
```

> **Mục tiêu**: Tránh các bài tập tác động cao và quá nhiều động tác bụng, ưu tiên bài tập an toàn.

---

## 6. Lớp 2 – Điều chỉnh theo mục tiêu (Goal Bias)

> Chỉ **cộng/trừ điểm**, không block.

### Khi body_fat_status == HIGH

- Calorie > 200 → +2
- MODERATE → +3
- BASIC → +2

### Khi bmi_status == OVERWEIGHT | OBESE

- MODERATE → +3
- BASIC → +2
- ADVANCED → -2
- FULL_BODY → +2
- LOWER_BODY → +1

### Khi bmi_status == UNDERWEIGHT

- MODERATE → +2
- BASIC → +1

### Khi BMI < 16 OR PBF < 8% (Thiếu cân nghiêm trọng - Ưu tiên tăng cơ)

- STRENGTH exercises → +4
- BASIC difficulty → +3
- DUMBBELL exercises → +2

> **Mục tiêu**: Tăng cơ bắp, tránh đốt calo quá nhiều.

### Khi BMI ≥ 35 OR PBF ≥ 40% (Béo phì nghiêm trọng - Ưu tiên giảm mỡ)

- FULL_BODY exercises → +4
- BASIC difficulty → +3
- MODERATE difficulty → +2

> **Mục tiêu**: Giảm mỡ toàn thân, tập an toàn với cường độ vừa phải.

---

## 7. Lớp 3 – Tính điểm & sắp xếp

### Điểm cơ bản

| Điều kiện                             | Điểm |
| ------------------------------------- | ---- |
| MODERATE                              | +3   |
| BASIC                                 | +2   |
| ADVANCED                              | -2   |
| Calorie > 250                         | +2   |
| Calorie < 150                         | -1   |
| HIGH_PRESSURE_CORE hoặc PRESSURE_HIGH | -3   |

### Công thức

```
total_score = base_score + goal_bonus
```

### Hậu xử lý

- Loại bài `total_score < 0`
- Sort giảm dần theo `total_score`
- Chọn top N

---

## 8. Output Contract

```json
{
  "recommended_exercises": [
    {
      "id": "chest_builder",
      "score": 13,
      "reasons": ["moderate_intensity", "high_calorie", "safe_for_central_fat"]
    }
  ],
  "blocked_exercises": [
    {
      "id": "chest_tri_terror",
      "reason": "advanced_not_allowed_for_high_fat"
    }
  ]
}
```

---

## 9. Những điều KHÔNG được làm

- ❌ Đưa InBody thô vào AI
- ❌ Để AI tự chọn bài tập
- ❌ Viết rule bằng ngôn ngữ mơ hồ
- ❌ Dùng AI cho logic quyết định

---

## 10. Nguyên tắc vàng

```
Rule Engine quyết định
AI chỉ trình bày quyết định đó
```

> Hệ thống phải **an toàn, ổn định, giải thích được**, ngay cả khi AI không hoạt động.

---

## 11. Gợi ý mở rộng (optional)

- Thêm rule theo **tuổi, giới tính, chấn thương**
- Thêm feedback loop (user rating)
- Chuyển điểm rời rạc → weight-based scoring
- Thêm audit log cho từng rule

---

## 12. Tóm tắt nhanh cho dev

```
Normalize → Block → Score → Sort → Return
```

Đây là toàn bộ đặc tả cần thiết để **implement Rule Engine production-ready**.
