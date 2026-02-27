# 🧪 Hướng dẫn Test Rule Engine

## Cách 1: Chạy Script Test (Nhanh nhất)

```bash
cd backend
source venv/bin/activate  # hoặc venv\Scripts\activate trên Windows
python scripts/test_rule_engine.py
```

Script này sẽ test:

- ✅ InBody Normalizer (chuẩn hóa dữ liệu)
- ✅ Safety Filter Layer (block bài tập không an toàn)
- ✅ Scoring & Ranking Layer (tính điểm và sắp xếp)
- ✅ Full Workflow (nhiều scenarios khác nhau)

## Cách 2: Test trong Streamlit App (Thực tế nhất)

### Bước 1: Khởi động ứng dụng

```bash
# Từ thư mục gốc
chmod +x run_streamlit.sh
./run_streamlit.sh
```

Hoặc chạy thủ công:

```bash
cd backend
source venv/bin/activate
streamlit run streamlit_app.py
```

### Bước 2: Mở trình duyệt

Truy cập: `http://localhost:8501`

### Bước 3: Test với InBody Data

#### Test Case 1: Obese với High Body Fat (sẽ block ADVANCED exercises)

**Nhập vào chat:**

```
Tôi nặng 95kg, cao 170cm, BMI 32.9, tỷ lệ mỡ 30%, giới tính nam
```

**Sau đó hỏi:**

```
Bài tập nào tốt cho tôi?
```

**Kỳ vọng:**

- ✅ Rule Engine sẽ block các bài tập ADVANCED
- ✅ Ưu tiên bài tập MODERATE/BASIC
- ✅ Console sẽ hiển thị: `[RuleEngine] Blocked exercise '...': ADVANCED difficulty (obese BMI)`

#### Test Case 2: Overweight với Central Fat (sẽ block HIGH_PRESSURE_CORE)

**Nhập vào chat:**

```
Tôi nặng 80kg, cao 170cm, BMI 27.7, tỷ lệ mỡ 26%, giới tính nam
```

**Sau đó hỏi:**

```
Bài tập nào tốt cho ngực và bụng?
```

**Kỳ vọng:**

- ✅ Rule Engine sẽ block các bài tập có risk_tag HIGH_PRESSURE_CORE
- ✅ Console sẽ hiển thị: `[RuleEngine] Blocked exercise '...': HIGH_PRESSURE_CORE (central fat detected)`

#### Test Case 3: Normal BMI (không block gì)

**Nhập vào chat:**

```
Tôi nặng 65kg, cao 170cm, BMI 22.5, tỷ lệ mỡ 15%, giới tính nam
```

**Sau đó hỏi:**

```
Bài tập nào tốt cho ngực?
```

**Kỳ vọng:**

- ✅ Rule Engine không block bài tập nào
- ✅ Tất cả bài tập đều được phép (tùy vào semantic search)

#### Test Case 4: Lộ trình tập (workout plan)

**Nhập InBody data trước:**

```
Tôi nặng 75kg, cao 170cm, BMI 26, tỷ lệ mỡ 25%
```

**Sau đó hỏi:**

```
Tạo cho tôi lộ trình tập 1 tuần
```

**Kỳ vọng:**

- ✅ Rule Engine filter bài tập an toàn
- ✅ LLM tạo lộ trình từ các bài tập đã được filter

## Cách 3: Test qua API (Nếu có FastAPI server)

```bash
# Khởi động FastAPI server
cd backend
source venv/bin/activate
python main.py
```

**Test với curl:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "message": "Tôi nặng 80kg, cao 170cm, BMI 27.7, tỷ lệ mỡ 26%. Bài tập nào tốt cho tôi?"
  }'
```

## Kiểm tra Logs

Khi Rule Engine hoạt động, bạn sẽ thấy logs trong console:

```
[ExerciseService] User Signals: UserSignals({'bmi_status': 'OVERWEIGHT', 'body_fat_status': 'HIGH', 'muscle_status': 'NORMAL', 'central_fat': True})
[RuleEngine] Blocked exercise 'Chest & Tri Terror': ADVANCED difficulty (high body fat)
[ExerciseService] Rule Engine filtered 10 -> 7 exercises
```

## Các điểm cần kiểm tra

### ✅ InBody Normalizer

- [ ] Chuẩn hóa BMI thành BMI_STATUS đúng
- [ ] Phân loại BODY_FAT_STATUS đúng theo giới tính
- [ ] Detect CENTRAL_FAT đúng

### ✅ Safety Filter Layer

- [ ] Block ADVANCED exercises khi BODY_FAT_STATUS = HIGH
- [ ] Block ADVANCED exercises khi BMI_STATUS = OBESE
- [ ] Block HIGH_PRESSURE_CORE khi CENTRAL_FAT = true

### ✅ Goal Filter Layer

- [ ] Ưu tiên MODERATE/BASIC cho overweight/obese
- [ ] Ưu tiên kcal cao cho fat loss
- [ ] Ưu tiên full body exercises

### ✅ Scoring & Ranking Layer

- [ ] Tính điểm đúng theo difficulty
- [ ] Tính điểm đúng theo calories
- [ ] Sắp xếp theo score (cao nhất trước)

## Troubleshooting

### Rule Engine không chạy?

1. Kiểm tra InBody data có được parse không:

   - Xem console logs: `[ExerciseService] Parsed InBody data...`
   - Nếu không có, thử format khác: `BMI: 27.7, Weight: 80kg, Height: 170cm`

2. Kiểm tra imports:

   ```bash
   cd backend
   source venv/bin/activate
   python -c "from services.rule_engine import RuleEngine; print('OK')"
   ```

3. Kiểm tra exercises có risk_tags không:
   ```bash
   python -c "from rag.exercise_rag import parse_exercises_from_markdown; ex = parse_exercises_from_markdown(); print(ex[0].get('risk_tags', []))"
   ```

### Exercises bị block hết?

- Đây là behavior đúng nếu user có nhiều risk factors
- Rule Engine sẽ fallback về kết quả gốc nếu block hết
- Kiểm tra console: `[ExerciseService] Rule Engine blocked all exercises, using original results`

## Kết quả mong đợi

Sau khi test, bạn sẽ thấy:

1. **Console logs rõ ràng** về User Signals và filtering
2. **Bài tập được filter** theo thể trạng
3. **Không có ADVANCED exercises** cho người obese/high body fat
4. **Không có HIGH_PRESSURE_CORE** cho người có central fat
5. **Scoring và ranking** hoạt động đúng
