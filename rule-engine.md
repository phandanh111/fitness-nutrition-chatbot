# 🧠 Rule Engine Design

## Hệ Thống Gợi Ý Bài Tập Dựa Trên InBody

Tài liệu này mô tả **cách Rule Engine hoạt động** một cách đơn giản và dễ hiểu, bao gồm:

- Quy trình chuẩn hóa dữ liệu InBody thành tín hiệu người dùng
- Flow chart từng bước xử lý
- Cách 3 lớp filter hoạt động
- Ví dụ minh họa cụ thể
- Vì sao Rule Engine quyết định thay vì AI

---

## 1. Mục Tiêu Của Rule Engine

Rule Engine là **bộ não quyết định** của hệ thống, chịu trách nhiệm:

- ✅ **Cho phép** bài tập nào được gợi ý
- ❌ **Chặn** bài tập nào không an toàn
- ⭐ **Ưu tiên** bài tập nào phù hợp nhất
- ⚠️ **Hạn chế** bài tập nào không khuyến khích

### Yêu Cầu Quan Trọng

- ✅ **An toàn tuyệt đối** - Không bao giờ gợi ý bài tập nguy hiểm
- ✅ **Rõ ràng** - Có thể giải thích tại sao chọn bài tập này
- ✅ **Ổn định** - Cùng một người → cùng một kết quả
- ✅ **Kiểm tra được** - Có thể xem lại mọi quyết định

---

## 2. Nguyên Tắc Thiết Kế

### Quy Tắc Vàng

1. **Rule Engine KHÔNG dùng AI** - Chỉ dùng logic thuần túy, không suy đoán
2. **Rule Engine KHÔNG đọc text** - Chỉ làm việc với số liệu đã chuẩn hóa
3. **Rule Engine luôn chạy trước** - Đảm bảo an toàn trước khi AI trình bày
4. **Rule Engine không tạo câu trả lời** - Chỉ lọc và sắp xếp bài tập

### Kiến Trúc Hệ Thống

```
Rule Engine = BỘ NÃO (quyết định)
RAG = TRÍ NHỚ (tìm kiếm bài tập)
AI = MIỆNG NÓI (trình bày kết quả)
```

**Điều quan trọng**: Nếu AI tắt, hệ thống vẫn hoạt động và trả về bài tập an toàn!

---

## 3. Flow Chart Tổng Quan

```
┌─────────────────────────────────────────────────────────────┐
│                    BƯỚC 1: NHẬN DỮ LIỆU                    │
│  - Danh sách bài tập từ hệ thống tìm kiếm                  │
│  - Thông tin InBody của người dùng                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              BƯỚC 2: CHUẨN HÓA DỮ LIỆU                      │
│  Chuyển đổi InBody thành tín hiệu đơn giản:                 │
│  - Tình trạng BMI (gầy/bình thường/thừa cân/béo phì)        │
│  - Tình trạng mỡ cơ thể (thấp/bình thường/cao)              │
│  - Tình trạng cơ (thấp/bình thường/cao)                     │
│  - Có mỡ bụng không?                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           BƯỚC 3: LỚP 1 - LỌC AN TOÀN                       │
│  Loại bỏ ngay các bài tập nguy hiểm:                        │
│  - Nếu có mỡ bụng → Chặn bài tập áp lực cao lên bụng        │
│  - Nếu mỡ cơ thể cao → Chặn bài tập nâng cao                │
│  - Nếu béo phì → Chặn bài tập nâng cao                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           BƯỚC 4: LỚP 2 - ĐIỀU CHỈNH MỤC TIÊU               │
│  Thêm điểm ưu tiên cho bài tập phù hợp:                     │
│  - Nếu muốn giảm mỡ → Ưu tiên bài tập đốt nhiều calo        │
│  - Nếu thừa cân → Ưu tiên bài tập trung bình/cơ bản         │
│  - Nếu gầy → Ưu tiên bài tập trung bình                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│        BƯỚC 5: LỚP 3 - TÍNH ĐIỂM VÀ SẮP XẾP                 │
│  Tính điểm cho mỗi bài tập:                                 │
│  - Độ khó trung bình: +3 điểm                               │
│  - Độ khó cơ bản: +2 điểm                                   │
│  - Độ khó nâng cao: -2 điểm                                 │
│  - Calo cao (>250): +2 điểm                                 │
│  - Calo thấp (<150): -1 điểm                                │
│  - Cộng điểm ưu tiên từ Bước 4                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              BƯỚC 6: LỌC VÀ SẮP XẾP                         │
│  - Loại bỏ bài tập có điểm < 0                              │
│  - Sắp xếp theo điểm từ cao xuống thấp                      │
│  - Chọn top N bài tập tốt nhất                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    KẾT QUẢ CUỐI CÙNG                        │
│  Danh sách bài tập ĐƯỢC PHÉP, đã sắp xếp theo độ phù hợp    │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Flow Chart Chi Tiết - Chuẩn Hóa InBody

### Quy Trình Chuyển Đổi Dữ Liệu

```
┌─────────────────────────────────────────────────────────────┐
│  DỮ LIỆU INBODY THÔ (từ người dùng)                         │
│  - Cân nặng: 80kg                                           │
│  - Chiều cao: 170cm                                         │
│  - BMI: 27.7                                                │
│  - Tỷ lệ mỡ: 26%                                            │
│  - Giới tính: Nam                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  BƯỚC 1: PHÂN LOẠI BMI                                      │
│  So sánh BMI với ngưỡng chuẩn châu Á:                       │
│  - BMI < 18.5 → GẦY                                         │
│  - BMI 18.5-23 → BÌNH THƯỜNG                                │
│  - BMI 23-27.5 → THỪA CÂN                                   │
│  - BMI >= 27.5 → BÉO PHÌ                                    │
│                                                             │
│  Kết quả: BMI 27.7 → THỪA CÂN                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  BƯỚC 2: PHÂN LOẠI MỠ CƠ THỂ                                │
│  So sánh tỷ lệ mỡ với ngưỡng theo giới tính:                │
│                                                             │
│  Nam:                                                       │
│  - < 10% → THẤP                                             │
│  - 10-20% → BÌNH THƯỜNG                                     │
│  - > 20% → CAO                                              │
│                                                             │
│  Nữ:                                                        │
│  - < 20% → THẤP                                             │
│  - 20-30% → BÌNH THƯỜNG                                     │
│  - > 30% → CAO                                              │
│                                                             │
│  Kết quả: 26% (Nam) → CAO                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  BƯỚC 3: ĐÁNH GIÁ TÌNH TRẠNG CƠ                             │
│  Dựa trên BMI và mỡ cơ thể:                                 │
│  - BMI cao nhưng mỡ không cao → Cơ tốt                      │
│  - BMI thấp và mỡ thấp → Cơ thấp                            │
│  - Các trường hợp khác → Cơ bình thường                     │
│                                                             │
│  Kết quả: BMI cao, mỡ cao → Cơ BÌNH THƯỜNG                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  BƯỚC 4: PHÁT HIỆN MỠ BỤNG                                  │
│  Kiểm tra:                                                  │
│  - BMI >= 23 VÀ mỡ cơ thể = CAO → Có mỡ bụng                │
│  - Các trường hợp khác → Không có mỡ bụng                   │
│                                                             │
│  Kết quả: BMI 27.7 >= 23 và mỡ CAO → CÓ MỠ BỤNG             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  TÍN HIỆU NGƯỜI DÙNG (đã chuẩn hóa)                         │
│  ✅ Tình trạng BMI: THỪA CÂN                                │
│  ✅ Tình trạng mỡ: CAO                                      │
│  ✅ Tình trạng cơ: BÌNH THƯỜNG                              │
│  ✅ Có mỡ bụng: CÓ                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Flow Chart Chi Tiết - Lớp 1: Lọc An Toàn

### Mục Tiêu

**Loại bỏ ngay** các bài tập có thể gây hại cho người dùng.

### Quy Trình

```
┌─────────────────────────────────────────────────────────────┐
│  DANH SÁCH BÀI TẬP TỪ HỆ THỐNG TÌM KIẾM                     │
│  (Ví dụ: 10 bài tập về ngực)                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌───────────────────────────┐
        │  Xét từng bài tập một:    │
        └───────────┬───────────────┘
                    │
        ┌───────────▼───────────────────────────────────┐
        │  QUY TẮC 1: Bảo vệ người có mỡ bụng           │
        │  Nếu người dùng CÓ mỡ bụng:                   │
        │    → Kiểm tra bài tập có áp lực cao lên bụng? │
        │    → Nếu CÓ → CHẶN bài tập này                │
        │    → Nếu KHÔNG → Tiếp tục                     │
        └───────────┬───────────────────────────────────┘
                    │
        ┌───────────▼───────────────────────────────────┐
        │  QUY TẮC 2: Giới hạn cho người mỡ cao         │
        │  Nếu người dùng có mỡ cơ thể CAO:             │
        │    → Kiểm tra bài tập có độ khó NÂNG CAO?     │
        │    → Nếu CÓ → CHẶN bài tập này                │
        │    → Nếu KHÔNG → Tiếp tục                     │
        └───────────┬───────────────────────────────────┘
                    │
        ┌───────────▼───────────────────────────────────┐
        │  QUY TẮC 3: Giới hạn cho người béo phì        │
        │  Nếu người dùng BÉO PHÌ:                      │
        │    → Kiểm tra bài tập có độ khó NÂNG CAO?     │
        │    → Nếu CÓ → CHẶN bài tập này                │
        │    → Nếu KHÔNG → Tiếp tục                     │
        └───────────┬───────────────────────────────────┘
                    │
        ┌───────────▼───────────────┐
        │  Nếu bài tập KHÔNG bị     │
        │  chặn bởi quy tắc nào:    │
        │    → Thêm vào danh sách   │
        │      bài tập AN TOÀN      │
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │  DANH SÁCH BÀI TẬP        │
        │  AN TOÀN (đã loại bỏ      │
        │  bài tập nguy hiểm)       │
        └───────────────────────────┘
```

### Ví Dụ Cụ Thể

**Tình huống**: Người dùng có mỡ bụng và mỡ cơ thể cao

**Danh sách bài tập ban đầu**:

- Chest Builder (Trung bình)
- Chest Power (Trung bình)
- Chest & Abs (Cơ bản)
- Chest & Tri Terror (Nâng cao) ← Bị chặn
- Chest & Ab Pump (Cơ bản, áp lực bụng) ← Bị chặn

**Kết quả sau Lớp 1**:

- ✅ Chest Builder
- ✅ Chest Power
- ✅ Chest & Abs

**Lý do chặn**:

- "Chest & Tri Terror": Độ khó NÂNG CAO → Không phù hợp với người mỡ cao
- "Chest & Ab Pump": Áp lực cao lên bụng → Không an toàn cho người có mỡ bụng

### Dựa Vào Đâu Để Lọc Bài Tập?

Rule Engine lọc bài tập dựa trên **2 nguồn thông tin chính**:

#### 1. Metadata Của Bài Tập (Từ File exercise.md)

Mỗi bài tập có các thông tin sau:

- **Độ khó (difficulty)**:

  - "Cơ bản" hoặc "BASIC"
  - "Trung bình" hoặc "MODERATE"
  - "Nâng cao" hoặc "ADVANCED"

- **Risk Tags (Nhãn rủi ro)**:

  - `HIGH_PRESSURE_CORE`: Bài tập có áp lực cao lên vùng bụng/core
  - `PRESSURE_HIGH`: Bài tập có áp lực cao nói chung
  - Risk tags có thể được:
    - Gán thủ công trong file exercise.md
    - Tự động phát hiện từ tên/mô tả bài tập (nếu có từ "core", "bụng", "ab", "abs", "pressure", "intense")

- **Calories (Kcal tiêu thụ)**: Số calo bài tập đốt được

- **Muscle Group (Nhóm cơ)**: Nhóm cơ bài tập tác động (ví dụ: "Toàn thân", "Thân dưới")

**Ví dụ từ file exercise.md**:

```
## Bài Tập 1 — Chest & Ab Pump
- Độ khó: Cơ bản (BASIC)
- Kcal tiêu thụ: 155
- Nhóm cơ: Core (Core), Thân trên (Upper Body), Ngực (Chest)
- Mô tả: ... kết hợp ngực và cơ bụng (core) ...
```

→ Hệ thống tự động phát hiện: Có từ "ab", "core" → Gán `HIGH_PRESSURE_CORE`

#### 2. Tín Hiệu Người Dùng (Từ InBody Đã Chuẩn Hóa)

Sau khi chuẩn hóa InBody, ta có các tín hiệu:

- **Central Fat (Mỡ bụng)**: `true` hoặc `false`

  - `true` = Có mỡ bụng (BMI >= 23 VÀ mỡ cơ thể = CAO)

- **Body Fat Status (Tình trạng mỡ)**: `"HIGH"`, `"NORMAL"`, hoặc `"LOW"`

  - `"HIGH"` = Mỡ cao (Nam > 20%, Nữ > 30%)

- **BMI Status (Tình trạng BMI)**: `"UNDERWEIGHT"`, `"NORMAL"`, `"OVERWEIGHT"`, hoặc `"OBESE"`
  - `"OBESE"` = Béo phì (BMI >= 27.5)

#### 3. Cách Rule Engine Kết Hợp 2 Nguồn Thông Tin

**Quy tắc 1: Chặn bài tập áp lực cao lên bụng**

```
NẾU người dùng có mỡ bụng (central_fat = true)
VÀ bài tập có risk_tag = "HIGH_PRESSURE_CORE"
THÌ → CHẶN bài tập này
```

**Ví dụ**:

- Người dùng: BMI 27.7, mỡ 26% → Có mỡ bụng (`central_fat = true`)
- Bài tập: "Chest & Ab Pump" có `risk_tags = ["HIGH_PRESSURE_CORE"]`
- Kết quả: **CHẶN** vì không an toàn cho người có mỡ bụng

**Quy tắc 2: Chặn bài tập nâng cao cho người mỡ cao**

```
NẾU người dùng có mỡ cơ thể cao (body_fat_status = "HIGH")
VÀ bài tập có độ khó = "Nâng cao" hoặc "ADVANCED"
THÌ → CHẶN bài tập này
```

**Ví dụ**:

- Người dùng: Mỡ 26% (Nam) → Mỡ cao (`body_fat_status = "HIGH"`)
- Bài tập: "Chest & Tri Terror" có `difficulty = "Nâng cao (ADVANCED)"`
- Kết quả: **CHẶN** vì người mỡ cao chưa có nền tảng thể lực tốt

**Quy tắc 3: Chặn bài tập nâng cao cho người béo phì**

```
NẾU người dùng béo phì (bmi_status = "OBESE")
VÀ bài tập có độ khó = "Nâng cao" hoặc "ADVANCED"
THÌ → CHẶN bài tập này
```

**Ví dụ**:

- Người dùng: BMI 28.0 → Béo phì (`bmi_status = "OBESE"`)
- Bài tập: "Chest Flex & Chill" có `difficulty = "Nâng cao (ADVANCED)"`
- Kết quả: **CHẶN** vì người béo phì có nguy cơ chấn thương cao

#### 4. Tóm Tắt: Dựa Vào Đâu?

| Quy Tắc                     | Dựa Vào Metadata Bài Tập            | Dựa Vào Tín Hiệu Người Dùng |
| --------------------------- | ----------------------------------- | --------------------------- |
| **Chặn áp lực bụng**        | `risk_tags` có `HIGH_PRESSURE_CORE` | `central_fat = true`        |
| **Chặn nâng cao (mỡ cao)**  | `difficulty = "ADVANCED"`           | `body_fat_status = "HIGH"`  |
| **Chặn nâng cao (béo phì)** | `difficulty = "ADVANCED"`           | `bmi_status = "OBESE"`      |

**Lưu ý quan trọng**:

- Metadata bài tập được lưu trong file `exercise.md` và được parse tự động
- Risk tags có thể được gán thủ công hoặc tự động phát hiện từ tên/mô tả
- Tín hiệu người dùng được tính toán từ InBody thông qua hàm chuẩn hóa
- Rule Engine chỉ so sánh các giá trị đã chuẩn hóa, không đọc text tự do

---

## 6. Flow Chart Chi Tiết - Lớp 2: Điều Chỉnh Mục Tiêu

### Mục Tiêu

**Thêm điểm ưu tiên** cho bài tập phù hợp với mục tiêu của người dùng.

### Quy Trình

```
┌─────────────────────────────────────────────────────────────┐
│  DANH SÁCH BÀI TẬP AN TOÀN (từ Lớp 1)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌───────────────────────────┐
        │  Xét từng bài tập một:    │
        └───────────┬───────────────┘
                    │
        ┌───────────▼───────────────────────────────────┐
        │  QUY TẮC 1: Ưu tiên giảm mỡ                     │
        │  Nếu người dùng có mỡ cơ thể CAO:               │
        │    → Bài tập đốt nhiều calo (>200) → +2 điểm   │
        │    → Bài tập độ khó TRUNG BÌNH → +3 điểm       │
        │    → Bài tập độ khó CƠ BẢN → +2 điểm           │
        └───────────┬───────────────────────────────────┘
                    │
        ┌───────────▼───────────────────────────────────┐
        │  QUY TẮC 2: Ưu tiên cho người thừa cân/béo phì│
        │  Nếu người dùng THỪA CÂN hoặc BÉO PHÌ:         │
        │    → Bài tập TRUNG BÌNH → +3 điểm             │
        │    → Bài tập CƠ BẢN → +2 điểm                 │
        │    → Bài tập NÂNG CAO → -2 điểm               │
        │    → Bài tập TOÀN THÂN → +2 điểm              │
        │    → Bài tập THÂN DƯỚI → +1 điểm              │
        └───────────┬───────────────────────────────────┘
                    │
        ┌───────────▼───────────────────────────────────┐
        │  QUY TẮC 3: Ưu tiên cho người gầy              │
        │  Nếu người dùng GẦY:                           │
        │    → Bài tập TRUNG BÌNH → +2 điểm             │
        │    → Bài tập CƠ BẢN → +1 điểm                 │
        └───────────┬───────────────────────────────────┘
                    │
        ┌───────────▼───────────────┐
        │  Cộng tất cả điểm ưu tiên │
        │  Lưu vào "điểm mục tiêu"  │
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │  DANH SÁCH BÀI TẬP        │
        │  với điểm mục tiêu        │
        │  (chưa sắp xếp)           │
        └───────────────────────────┘
```

### Ví Dụ Cụ Thể

**Tình huống**: Người dùng thừa cân, mỡ cao

**Bài tập**: Chest Builder

- Độ khó: Trung bình
- Calo: 280
- Nhóm cơ: Ngực

**Tính điểm mục tiêu**:

- Quy tắc 1 (mỡ cao): Calo > 200 → +2, Trung bình → +3 = **+5 điểm**
- Quy tắc 2 (thừa cân): Trung bình → +3 = **+3 điểm**

**Tổng điểm mục tiêu**: 5 + 3 = **+8 điểm**

---

## 7. Flow Chart Chi Tiết - Lớp 3: Tính Điểm và Sắp Xếp

### Mục Tiêu

**Tính điểm tổng thể** và **sắp xếp** bài tập theo độ phù hợp.

### Quy Trình

```
┌─────────────────────────────────────────────────────────────┐
│  DANH SÁCH BÀI TẬP với điểm mục tiêu (từ Lớp 2)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌───────────────────────────┐
        │  Xét từng bài tập một:    │
        └───────────┬───────────────┘
                    │
        ┌───────────▼───────────────────────────────────┐
        │  BƯỚC 1: Tính điểm cơ bản                     │
        │  Bắt đầu với 0 điểm:                          │
        │                                                 │
        │  Điểm theo độ khó:                             │
        │    - Trung bình → +3 điểm                      │
        │    - Cơ bản → +2 điểm                          │
        │    - Nâng cao → -2 điểm                        │
        │                                                 │
        │  Điểm theo calo:                                │
        │    - Calo cao (>250) → +2 điểm                 │
        │    - Calo thấp (<150) → -1 điểm               │
        │                                                 │
        │  Điểm theo rủi ro:                              │
        │    - Có rủi ro cao → -3 điểm                   │
        └───────────┬───────────────────────────────────┘
                    │
        ┌───────────▼───────────────────────────────────┐
        │  BƯỚC 2: Cộng điểm mục tiêu                    │
        │  Điểm tổng = Điểm cơ bản + Điểm mục tiêu       │
        └───────────┬───────────────────────────────────┘
                    │
        ┌───────────▼───────────────┐
        │  Lưu điểm tổng vào bài tập │
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │  Sắp xếp theo điểm        │
        │  (từ cao xuống thấp)      │
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │  Loại bỏ bài tập          │
        │  có điểm < 0               │
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │  Chọn top N bài tập       │
        │  tốt nhất                  │
        └───────────────────────────┘
```

### Ví Dụ Tính Điểm

**Bài tập**: Chest Builder

- Độ khó: Trung bình
- Calo: 280
- Điểm mục tiêu: +8 (từ Lớp 2)

**Tính điểm cơ bản**:

- Trung bình: +3 điểm
- Calo > 250: +2 điểm
- **Tổng điểm cơ bản**: 3 + 2 = **5 điểm**

**Điểm tổng**:

- Điểm cơ bản: 5 điểm
- Điểm mục tiêu: +8 điểm
- **Tổng cộng**: 5 + 8 = **13 điểm**

---

## 8. Ví Dụ Hoàn Chỉnh - Từ Đầu Đến Cuối

### Tình Huống

**Người dùng**:

- Cân nặng: 80kg
- Chiều cao: 170cm
- BMI: 27.7
- Tỷ lệ mỡ: 26%
- Giới tính: Nam

**Câu hỏi**: "Bài tập nào tốt cho ngực?"

### Bước 1: Chuẩn Hóa Dữ Liệu

```
InBody thô → Tín hiệu người dùng:

✅ Tình trạng BMI: THỪA CÂN (BMI 27.7)
✅ Tình trạng mỡ: CAO (26% - Nam)
✅ Tình trạng cơ: BÌNH THƯỜNG
✅ Có mỡ bụng: CÓ (BMI cao + mỡ cao)
```

### Bước 2: Tìm Kiếm Bài Tập

Hệ thống tìm được **10 bài tập** về ngực từ cơ sở dữ liệu.

### Bước 3: Lọc An Toàn (Lớp 1)

**Quy tắc áp dụng**:

1. **Có mỡ bụng** → Chặn bài tập áp lực cao lên bụng

   - ❌ "Chest & Ab Pump" (có áp lực cao lên bụng)

2. **Mỡ cơ thể cao** → Chặn bài tập nâng cao
   - ❌ "Chest & Tri Terror" (nâng cao)
   - ❌ "Chest Flex & Chill" (nâng cao)

**Kết quả**: Còn lại **7 bài tập** an toàn

### Bước 4: Điều Chỉnh Mục Tiêu (Lớp 2)

**Quy tắc áp dụng**:

1. **Mỡ cao** → Ưu tiên bài tập đốt nhiều calo và trung bình/cơ bản
2. **Thừa cân** → Ưu tiên bài tập trung bình/cơ bản, toàn thân

**Ví dụ tính điểm**:

- **Chest Builder** (Trung bình, 280 calo):

  - Mỡ cao: Calo cao (+2) + Trung bình (+3) = +5
  - Thừa cân: Trung bình (+3) = +3
  - **Tổng điểm mục tiêu**: +8

- **Chest & Abs** (Cơ bản, 130 calo):
  - Mỡ cao: Cơ bản (+2) = +2
  - Thừa cân: Cơ bản (+2) = +2
  - **Tổng điểm mục tiêu**: +4

### Bước 5: Tính Điểm và Sắp Xếp (Lớp 3)

**Ví dụ tính điểm tổng**:

- **Chest Builder**:

  - Điểm cơ bản: Trung bình (+3) + Calo cao (+2) = 5
  - Điểm mục tiêu: +8
  - **Tổng điểm**: 13

- **Chest & Abs**:
  - Điểm cơ bản: Cơ bản (+2) + Calo thấp (-1) = 1
  - Điểm mục tiêu: +4
  - **Tổng điểm**: 5

**Sắp xếp theo điểm** (từ cao xuống thấp):

1. Chest Builder: 13 điểm
2. Chest Power: 13 điểm
3. Chest & Triceps: 13 điểm
4. Chest & Abs: 5 điểm
5. ...

### Bước 6: Kết Quả Cuối Cùng

**Top 5 bài tập được gợi ý**:

1. ✅ Chest Builder (13 điểm)
2. ✅ Chest Power (13 điểm)
3. ✅ Chest & Triceps (13 điểm)
4. ✅ Chest & Abs (5 điểm)
5. ✅ Triceps & Chest Flex (6 điểm)

**Lưu ý**: Tất cả bài tập nâng cao và bài tập áp lực cao đã bị loại bỏ để đảm bảo an toàn!

---

## 9. Các Quy Tắc Chi Tiết

### Lớp 1: Quy Tắc An Toàn (Hard-Block)

#### Quy Tắc 1.1: Bảo Vệ Người Có Mỡ Bụng

**Điều kiện**: Người dùng có mỡ bụng

**Hành động**: Chặn ngay các bài tập có áp lực cao lên vùng bụng

**Lý do**: Người có mỡ bụng thường có vấn đề về sức khỏe tim mạch, bài tập áp lực cao có thể gây nguy hiểm.

**Ví dụ**:

- ❌ Chặn: "Chest & Ab Pump" (áp lực cao lên bụng)
- ✅ Cho phép: "Chest Builder" (không có áp lực bụng)

#### Quy Tắc 1.2: Giới Hạn Cho Người Mỡ Cao

**Điều kiện**: Người dùng có mỡ cơ thể cao

**Hành động**: Chặn các bài tập độ khó nâng cao

**Lý do**: Người có mỡ cao thường chưa có nền tảng thể lực tốt, bài tập nâng cao dễ gây chấn thương.

**Ví dụ**:

- ❌ Chặn: "Chest & Tri Terror" (nâng cao)
- ✅ Cho phép: "Chest Builder" (trung bình)

#### Quy Tắc 1.3: Giới Hạn Cho Người Béo Phì

**Điều kiện**: Người dùng béo phì (BMI >= 27.5)

**Hành động**: Chặn các bài tập độ khó nâng cao

**Lý do**: Người béo phì có nguy cơ chấn thương cao hơn, cần bài tập an toàn hơn.

**Ví dụ**:

- ❌ Chặn: Tất cả bài tập nâng cao
- ✅ Cho phép: Chỉ bài tập cơ bản và trung bình

---

### Lớp 2: Quy Tắc Mục Tiêu (Điều Chỉnh Điểm)

#### Quy Tắc 2.1: Ưu Tiên Giảm Mỡ

**Điều kiện**: Người dùng có mỡ cơ thể cao

**Hành động**: Thêm điểm cho bài tập phù hợp giảm mỡ

**Ưu tiên**:

- Bài tập đốt nhiều calo (>200 calo) → +2 điểm
- Bài tập độ khó trung bình → +3 điểm
- Bài tập độ khó cơ bản → +2 điểm

**Lý do**: Người có mỡ cao cần bài tập đốt nhiều năng lượng và không quá khó để duy trì lâu dài.

#### Quy Tắc 2.2: Ưu Tiên Cho Người Thừa Cân/Béo Phì

**Điều kiện**: Người dùng thừa cân hoặc béo phì

**Hành động**: Thêm điểm cho bài tập phù hợp

**Ưu tiên**:

- Bài tập trung bình → +3 điểm
- Bài tập cơ bản → +2 điểm
- Bài tập nâng cao → -2 điểm (không khuyến khích)
- Bài tập toàn thân → +2 điểm
- Bài tập thân dưới → +1 điểm

**Lý do**: Người thừa cân cần bài tập vừa sức, ưu tiên bài tập toàn thân để đốt mỡ hiệu quả.

#### Quy Tắc 2.3: Ưu Tiên Cho Người Gầy

**Điều kiện**: Người dùng gầy (BMI < 18.5)

**Hành động**: Thêm điểm cho bài tập phù hợp tăng cơ

**Ưu tiên**:

- Bài tập trung bình → +2 điểm
- Bài tập cơ bản → +1 điểm

**Lý do**: Người gầy cần bài tập vừa phải để tăng cơ dần, không quá nặng gây mệt mỏi.

---

### Lớp 3: Quy Tắc Tính Điểm

#### Điểm Theo Độ Khó

- **Trung bình**: +3 điểm (phù hợp nhất cho đa số)
- **Cơ bản**: +2 điểm (an toàn, dễ thực hiện)
- **Nâng cao**: -2 điểm (chỉ phù hợp người có nền tảng)

#### Điểm Theo Calo

- **Calo cao (>250)**: +2 điểm (đốt nhiều năng lượng)
- **Calo thấp (<150)**: -1 điểm (ít hiệu quả)
- **Calo trung bình (150-250)**: 0 điểm (không cộng không trừ)

#### Điểm Theo Rủi Ro

- **Có rủi ro cao**: -3 điểm (không khuyến khích)

#### Điểm Tổng

**Điểm tổng = Điểm cơ bản + Điểm mục tiêu**

- Điểm cơ bản: Từ độ khó, calo, rủi ro
- Điểm mục tiêu: Từ Lớp 2 (điều chỉnh theo thể trạng)

---

## 10. Thứ Tự Thực Thi

### Quy Trình Tổng Thể

```
1. Nhận dữ liệu
   ↓
2. Chuẩn hóa InBody thành tín hiệu người dùng
   ↓
3. Lọc an toàn (Lớp 1) - Loại bỏ bài tập nguy hiểm
   ↓
4. Điều chỉnh mục tiêu (Lớp 2) - Thêm điểm ưu tiên
   ↓
5. Tính điểm và sắp xếp (Lớp 3) - Tính điểm tổng
   ↓
6. Lọc điểm < 0 và sắp xếp theo điểm
   ↓
7. Chọn top N bài tập tốt nhất
   ↓
8. Trả về kết quả
```

### Đặc Điểm Quan Trọng

- **Tuần tự**: Mỗi lớp chạy sau lớp trước
- **Không bỏ qua**: Nếu Lớp 1 chặn hết → Không có bài tập nào được gợi ý
- **Cộng dồn**: Điểm từ các lớp được cộng lại
- **Cuối cùng**: Chỉ bài tập có điểm >= 0 mới được giữ lại

---

## 11. Vì Sao Rule Engine Quan Trọng?

### So Sánh Với Cách Làm Khác

| Cách Làm            | Ưu Điểm                                                           | Nhược Điểm                                                                    |
| ------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| **Để AI chọn**      | Linh hoạt                                                         | ❌ Có thể hallucinate<br>❌ Không giải thích được<br>❌ Không đảm bảo an toàn |
| **Fine-tune model** | Học được pattern                                                  | ❌ Tốn kém<br>❌ Khó debug<br>❌ Black box                                    |
| **Rule Engine**     | ✅ An toàn<br>✅ Giải thích được<br>✅ Dễ sửa<br>✅ Không tốn kém | Cần viết rules                                                                |

### Lợi Ích Của Rule Engine

1. **An Toàn Tuyệt Đối**

   - Không bao giờ gợi ý bài tập nguy hiểm
   - Có thể kiểm tra từng quy tắc

2. **Giải Thích Được**

   - Có thể nói rõ tại sao chọn bài tập này
   - Có thể trace lại mọi quyết định

3. **Dễ Sửa Đổi**

   - Chỉ cần sửa constants hoặc thêm rule mới
   - Không cần retrain model

4. **Ổn Định**
   - Cùng một người → Cùng một kết quả
   - Không phụ thuộc vào AI

---

## 12. Những Điều KHÔNG ĐƯỢC Làm

### ❌ Đưa Dữ Liệu InBody Thô Vào AI

**Sai**:

```
"Người dùng có BMI 27.7, mỡ 26%, hãy chọn bài tập phù hợp"
```

**Đúng**: Chuẩn hóa thành tín hiệu trước, sau đó dùng Rule Engine

### ❌ Để AI Quyết Định Bài Tập

**Sai**: Để AI tự chọn bài tập từ danh sách

**Đúng**: Rule Engine lọc trước, AI chỉ trình bày kết quả

### ❌ Viết Quy Tắc Bằng Câu Văn

**Sai**: "Nếu BMI cao thì chọn bài tập nhẹ"

**Đúng**: `IF bmi_status == "OBESE": block ADVANCED`

### ❌ Dùng AI Với Nhiệt Độ Cao Cho Logic

**Sai**: Dùng AI với temperature > 0 để quyết định

**Đúng**: Rule Engine deterministic, AI chỉ trình bày

---

## 13. Mở Rộng Trong Tương Lai

### Có Thể Thêm Các Quy Tắc Mới

1. **Theo Độ Tuổi**

   - Người trẻ (<18): Chặn bài tập nâng cao
   - Người già (>60): Ưu tiên bài tập cơ bản

2. **Theo Giới Tính**

   - Nữ: Ưu tiên bài tập thân dưới
   - Nam: Cân bằng các nhóm cơ

3. **Theo Tiền Sử Chấn Thương**

   - Có chấn thương đầu gối: Chặn bài tập chân nâng cao
   - Có chấn thương lưng: Chặn bài tập cúi người

4. **Theo Mục Tiêu Tập Luyện**

   - Muốn tăng cơ: Ưu tiên bài tập trung bình/nâng cao
   - Muốn giảm cân: Ưu tiên bài tập đốt nhiều calo

5. **Theo Phản Hồi Người Dùng**
   - Bài tập được đánh giá tốt: Tăng điểm
   - Bài tập được đánh giá kém: Giảm điểm

---

## 14. Nguyên Tắc Vàng

```
Rule Engine = BỘ NÃO (quyết định)
RAG = TRÍ NHỚ (tìm kiếm bài tập)
AI = MIỆNG NÓI (trình bày kết quả)
```

**Điều quan trọng nhất**:

**Nếu AI tắt → Hệ thống vẫn hoạt động và trả về bài tập an toàn!**

Rule Engine không phụ thuộc vào AI, đảm bảo hệ thống luôn an toàn.

---

## 15. Kết Luận

Rule Engine là **nền tảng quyết định** của hệ thống gợi ý bài tập.

**AI chỉ là công cụ trình bày**, không phải người ra quyết định.

Thiết kế này đảm bảo:

- ✅ **An toàn** - Không bao giờ gợi ý bài tập nguy hiểm
- ✅ **Rõ ràng** - Có thể giải thích mọi quyết định
- ✅ **Ổn định** - Cùng input → Cùng output
- ✅ **Linh hoạt** - Dễ thêm/sửa quy tắc mới
- ✅ **Sẵn sàng sản xuất** - Production-ready

---

## 16. Tóm Tắt Flow Ngắn Gọn

```
1. Nhận InBody → Chuẩn hóa thành tín hiệu
2. Tìm bài tập → Lọc an toàn (chặn nguy hiểm)
3. Điều chỉnh → Thêm điểm ưu tiên (theo mục tiêu)
4. Tính điểm → Sắp xếp (theo độ phù hợp)
5. Chọn top N → Trả về bài tập tốt nhất
```

**Đơn giản vậy thôi!** 🎯
