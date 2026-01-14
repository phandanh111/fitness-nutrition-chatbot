# 🧠 Rule Engine Design
## InBody-based Exercise Recommendation System

Tài liệu này mô tả chi tiết **cách Rule Engine hoạt động**, bao gồm:
- Chuẩn hoá dữ liệu InBody
- Cấu trúc rule
- Thứ tự áp dụng rule
- Cách lọc & chấm điểm bài tập
- Vì sao Rule Engine quyết định thay vì LLM

---

## 1. Mục tiêu của Rule Engine

Rule Engine chịu trách nhiệm **ra quyết định cuối cùng** về bài tập nào:
- ĐƯỢC PHÉP
- KHÔNG ĐƯỢC PHÉP
- ƯU TIÊN hay HẠN CHẾ

Rule Engine phải đảm bảo:
- Không hallucination
- Không suy đoán y khoa
- Quyết định deterministic
- Audit & debug được

---

## 2. Nguyên tắc thiết kế

1. Rule Engine KHÔNG dùng LLM
2. Rule Engine KHÔNG dùng text prompt
3. Rule Engine chỉ làm việc với dữ liệu đã chuẩn hoá
4. Rule Engine không sinh text
5. Rule Engine luôn chạy trước RAG & LLM

---

## 3. Input & Output của Rule Engine

### 3.1 Input

Rule Engine nhận vào 2 nguồn dữ liệu:

#### A. User Signals (đã chuẩn hoá từ InBody)

Ví dụ:

- BMI_STATUS = OVERWEIGHT
- BODY_FAT_STATUS = HIGH
- MUSCLE_STATUS = NORMAL
- CENTRAL_FAT = true

#### B. Exercise Catalog (metadata)

Mỗi bài tập có metadata:

- difficulty
- kcal
- muscle_tags
- risk_tags

---

### 3.2 Output

Output của Rule Engine là:

- Danh sách bài tập **ĐƯỢC PHÉP**
- Danh sách này đã:
  - An toàn
  - Phù hợp thể trạng
  - Không cần AI suy luận

Ví dụ:

- Chest Builder
- Chest Power
- Chest & Abs

---

## 4. Kiến trúc nội bộ Rule Engine

Rule Engine được chia thành 3 tầng:

1. Safety Filter Layer
2. Goal Filter Layer
3. Scoring & Ranking Layer

---

## 5. Layer 1 – Safety Filter Layer

### 5.1 Mục tiêu

- LOẠI BỎ bài tập có nguy cơ gây hại
- ƯU TIÊN an toàn hơn hiệu quả

### 5.2 Ví dụ rule an toàn

#### Rule: Central Fat Protection

IF:
- CENTRAL_FAT = true

THEN:
- Block exercises with risk_tag = HIGH_PRESSURE_CORE

---

#### Rule: High Body Fat Limitation

IF:
- BODY_FAT_STATUS = HIGH

THEN:
- Block difficulty = ADVANCED

---

### 5.3 Đặc điểm

- Rule hard-block (loại ngay)
- Không có scoring
- Không có override

---

## 6. Layer 2 – Goal Filter Layer

### 6.1 Mục tiêu

- Định hướng bài tập phù hợp mục tiêu cơ thể
- Không can thiệp safety

---

### 6.2 Ví dụ rule mục tiêu

#### Fat Loss Bias Rule

IF:
- BODY_FAT_STATUS = HIGH

THEN:
- Prefer kcal > 200
- Prefer difficulty = MODERATE

---

#### Muscle Preservation Rule

IF:
- MUSCLE_STATUS = NORMAL

THEN:
- Do NOT force hypertrophy overload

---

### 6.3 Đặc điểm

- Không block bài tập
- Chỉ ảnh hưởng scoring

---

## 7. Layer 3 – Scoring & Ranking Layer

### 7.1 Mục tiêu

- Chọn bài tập tốt nhất trong danh sách an toàn
- Tránh chọn bài quá nhẹ hoặc quá nặng

---

### 7.2 Scoring Strategy

Mỗi bài tập bắt đầu với score = 0

Cộng / trừ điểm theo rule:

| Điều kiện | Điểm |
|---------|------|
| difficulty = MODERATE | +3 |
| difficulty = BASIC | +2 |
| difficulty = ADVANCED | -2 |
| kcal > 250 | +2 |
| kcal < 150 | -1 |
| risk_tag = PRESSURE_HIGH | -3 |

---

### 7.3 Threshold

- Nếu score < 0 → loại bài tập
- Giữ top N bài tập theo score

---

## 8. Thứ tự thực thi (Execution Order)

1. Load User Signals
2. Load Exercise Catalog
3. Apply Safety Filter (hard block)
4. Apply Goal Bias Rules
5. Calculate Score
6. Sort by Score
7. Select Top N
8. Output Allowed Exercises

---

## 9. Ví dụ chạy thực tế

### Input Signals

- BODY_FAT_STATUS = HIGH
- MUSCLE_STATUS = NORMAL
- CENTRAL_FAT = true

---

### Bước 1 – Safety Filter

- Loại bài:
  - HIGH_PRESSURE_CORE
  - ADVANCED

---

### Bước 2 – Goal Bias

- Ưu tiên:
  - MODERATE
  - kcal cao

---

### Bước 3 – Scoring

| Exercise | Score |
|-------|------|
| Chest Builder | 5 |
| Chest Power | 4 |
| Chest & Abs | 3 |
| Chest & Tri Terror | -1 (LOẠI) |

---

### Output

- Chest Builder
- Chest Power
- Chest & Abs

---

## 10. Vì sao Rule Engine > Fine-tune

| Tiêu chí | Rule Engine | Fine-tune |
|-------|-----------|----------|
| An toàn | ✅ | ❌ |
| Audit | ✅ | ❌ |
| Debug | ✅ | ❌ |
| Cá nhân hoá | ✅ | ⚠️ |
| Thay đổi nhanh | ✅ | ❌ |

---

## 11. Anti-patterns (KHÔNG ĐƯỢC LÀM)

- Đưa InBody raw vào prompt
- Để LLM chọn bài tập
- Viết rule bằng text prompt
- Dùng temperature > 0 cho logic

---

## 12. Mở rộng trong tương lai

- Rule theo độ tuổi
- Rule theo giới tính
- Rule theo tiền sử chấn thương
- Rule theo feedback người dùng

---

## 13. Nguyên tắc vàng

Rule Engine = NÃO  
RAG = TRÍ NHỚ  
LLM = MIỆNG NÓI  

Nếu LLM tắt → hệ vẫn chạy.

---

## 14. Kết luận

Rule Engine là nền tảng quyết định của hệ thống gợi ý bài tập.

LLM chỉ là công cụ trình bày, không phải người ra quyết định.

Thiết kế này:
- An toàn
- Có trách nhiệm
- Production-ready
