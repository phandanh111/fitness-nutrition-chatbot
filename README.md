# The New Gym Chatbot - RAG System với Rule Engine

Chatbot tư vấn về bài tập của The New Gym sử dụng **RAG (Retrieval-Augmented Generation)** kết hợp với **Rule Engine** để đảm bảo an toàn và cá nhân hóa gợi ý bài tập dựa trên thể trạng người dùng.

## ✨ Tính năng

- 🤖 **AI Chatbot**: Tư vấn về bài tập của The New Gym bằng tiếng Việt
- 🔍 **Semantic Search**: Tìm kiếm thông minh dựa trên ngữ nghĩa (RAG)
- 💪 **Thông tin bài tập**: Tư vấn về các bài tập thể hình
- 🧠 **Rule Engine**: Hệ thống quyết định an toàn, cá nhân hóa bài tập dựa trên InBody data
- 🎯 **Query Classification**: Tự động phân loại câu hỏi (exercises, general)
- 📱 **Giao diện web**: Streamlit - đơn giản và dễ sử dụng
- 🚀 **Chạy local**: Không cần API key, hoàn toàn miễn phí với Ollama

## 🛠️ Công nghệ

### Backend & UI

- **Streamlit**: Web UI framework (Python-based)
- **Ollama**: Local AI inference
- **ChromaDB**: Vector database cho RAG
- **Sentence Transformers**: Vietnamese embedding model (`dangvantuan/vietnamese-embedding`)
- **Python 3.8+**

## 🏗️ Kiến trúc Hệ Thống

### Tổng quan Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER QUERY                                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              QUERY CLASSIFICATION                               │
│  (Exercises / General)                                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
              ┌──────────────────────┐
              │  EXERCISES FLOW      │
              │  (với Rule Engine)   │
              └──────────────────────┘
```

### Exercises Flow (với Rule Engine)

```
User Query về bài tập
         │
         ▼
┌─────────────────────────────────────┐
│  1. Parse InBody Data (nếu có)      │
│     - Từ message hoặc session       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  2. Semantic Search (RAG)           │
│     - Tìm bài tập liên quan         │
│     - Trả về top K exercises        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. Rule Engine (nếu có InBody)     │
│     ├─ Normalize InBody → Signals   │
│     ├─ Safety Filter (hard-block)   │
│     ├─ Goal Filter (scoring)        │
│     └─ Scoring & Ranking            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  4. LLM Presentation                │
│     - Tạo câu trả lời từ context    │
│     - Format theo yêu cầu           │
└──────────────┬──────────────────────┘
               │
               ▼
         Response cho User
```

### Rule Engine - 3 Layers

```
┌─────────────────────────────────────────┐
│  Layer 1: Safety Filter                 │
│  - Block ADVANCED nếu obese/high fat    │
│  - Block HIGH_PRESSURE_CORE nếu có      │
│    central fat                          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Layer 2: Goal Filter                   │
│  - Ưu tiên MODERATE/BASIC cho overweight│
│  - Ưu tiên kcal cao cho fat loss        │
│  - Ưu tiên full body exercises          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Layer 3: Scoring & Ranking             │
│  - Tính điểm theo difficulty            │
│  - Tính điểm theo calories              │
│  - Trừ điểm theo risk tags              │
│  - Sắp xếp và filter score < 0          │
└──────────────┬──────────────────────────┘
               │
               ▼
      Allowed Exercises List
```

## 🏗️ Kiến trúc Code

### Unified RAG System

Hệ thống sử dụng **Unified RAG System** với topic registry, cho phép dễ dàng thêm các topics mới:

```
backend/rag/
├── base_rag.py          # Base class chung cho tất cả topics
├── unified_rag.py       # Unified RAG system với topic registry
├── exercise_rag.py      # Wrapper cho exercises topic (backward compatibility)
└── topics/
    └── exercises.py     # Configuration cho exercises topic
```

### Rule Engine System

```
backend/
├── services/
│   ├── rule_engine.py           # Rule Engine với 3 layers
│   └── exercise_service.py      # Exercise query handling (tích hợp Rule Engine)
├── utils/
│   ├── inbody_normalizer.py     # Chuẩn hóa InBody → User Signals
│   └── exercise_helpers.py      # Helper functions chung
└── constants/
    └── exercise_constants.py    # Tất cả constants (thresholds, scores, etc.)
```

### Topics hiện có

1. **Exercises**: Thông tin về các bài tập thể hình (có Rule Engine)

## 🚀 Cài đặt nhanh

### 1. Clone repository

```bash
git clone <repository-url>
cd chat-bot
```

### 2. Cài đặt Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh
```

### 3. Tải model DeepSeek R1

```bash
ollama pull deepseek-r1:7b
```

### 4. Khởi động Ollama

```bash
ollama serve
```

### 5. Cài đặt Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 6. Build RAG Index

```bash
# Build index cho exercises
python scripts/build_exercise_index.py --force
```

### 7. Cấu hình Environment

```bash
cp env.example .env
# Chỉnh sửa .env nếu cần
```

### 8. Chạy Streamlit App

```bash
# Cách 1: Sử dụng script tự động (khuyến nghị)
cd ..
chmod +x run_streamlit.sh
./run_streamlit.sh

# Cách 2: Chạy thủ công
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
streamlit run streamlit_app.py
```

## 📖 Sử dụng

1. Mở trình duyệt tại `http://localhost:8501` (hoặc port được hiển thị)
2. Chat với bot về:
   - **Thông tin bài tập**: "Bài tập nào tốt cho ngực?"
   - **Bài tập cá nhân hóa**: Nhập InBody data trước, sau đó hỏi về bài tập
   - **Câu hỏi chung**: Các câu hỏi về dịch vụ The New Gym

### Ví dụ với InBody Data

**Bước 1**: Nhập InBody data vào chat

```
Tôi nặng 80kg, cao 170cm, BMI 27.7, tỷ lệ mỡ 26%, giới tính nam
```

**Bước 2**: Hỏi về bài tập

```
Bài tập nào tốt cho tôi?
```

**Kết quả**: Bot sẽ:

- Parse InBody data → User Signals (OVERWEIGHT, HIGH body fat, CENTRAL_FAT)
- Tìm bài tập liên quan bằng semantic search
- Áp dụng Rule Engine:
  - Block ADVANCED exercises (vì high body fat)
  - Block HIGH_PRESSURE_CORE exercises (vì central fat)
  - Ưu tiên MODERATE/BASIC exercises
  - Ưu tiên full body exercises
- Trả về danh sách bài tập an toàn và phù hợp

## 🔧 Cấu hình

### Environment Variables

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:7b
OLLAMA_TIMEOUT=120
OLLAMA_MAX_TOKENS=2000

# RAG Configuration
EMBED_MODEL=dangvantuan/vietnamese-embedding
EXERCISE_EMBED_LIMIT=500
EXERCISE_CONTEXT_LIMIT=4

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### Rule Engine Configuration

Các constants có thể chỉnh sửa trong `backend/constants/exercise_constants.py`:

- **BMI Thresholds**: `BMI_UNDERWEIGHT_THRESHOLD`, `BMI_NORMAL_THRESHOLD`, `BMI_OVERWEIGHT_THRESHOLD`
- **Body Fat Thresholds**: Theo giới tính (nam/nữ)
- **Scoring Values**: Điểm cho difficulty, calories, risk tags
- **Calorie Thresholds**: `CALORIE_LOW_THRESHOLD`, `CALORIE_MEDIUM_THRESHOLD`, `CALORIE_HIGH_THRESHOLD`

## 📁 Cấu trúc Project

```
chat-bot/
├── backend/
│   ├── streamlit_app.py          # Streamlit app (main UI)
│   ├── main.py                    # FastAPI app (optional, for API)
│   ├── requirements.txt           # Python dependencies
│   ├── env.example               # Environment template
│   ├── prompt_system.txt         # AI system prompt
│   ├── data/
│   │   ├── exercise.md           # Dữ liệu exercises (markdown)
│   │   └── rag/
│   │       ├── chroma/           # ChromaDB storage
│   │       └── hf_cache/         # HuggingFace model cache
│   ├── rag/
│   │   ├── base_rag.py           # Base RAG class
│   │   ├── unified_rag.py        # Unified RAG system
│   │   ├── exercise_rag.py       # Exercises wrapper
│   │   └── topics/
│   │       └── exercises.py      # Exercises topic config
│   ├── services/
│   │   ├── exercise_service.py   # Exercise query handling (tích hợp Rule Engine)
│   │   ├── rule_engine.py         # Rule Engine với 3 layers
│   │   ├── llm_service.py        # LLM integration
│   │   └── conversation_service.py # Conversation history & InBody storage
│   ├── utils/
│   │   ├── query_classifier.py   # Query classification
│   │   ├── inbody_normalizer.py  # Chuẩn hóa InBody → User Signals
│   │   ├── exercise_helpers.py   # Helper functions cho exercise parsing
│   │   └── ollama_client.py      # Ollama integration
│   ├── constants/
│   │   ├── rag_prompts.py        # RAG prompts
│   │   └── exercise_constants.py # Constants cho Rule Engine
│   └── scripts/
│       ├── build_exercise_index.py # Build RAG index script
│       ├── test_rule_engine.py    # Test Rule Engine
│       ├── view_chroma_data.py    # View ChromaDB data
│       └── view_vectors.py        # View vectors
├── docs/
│   ├── rag_processing_flow.md    # RAG flow documentation
│   └── how_vector_search_works.md # Vector search explanation
├── run_streamlit.sh              # Quick start script (Streamlit)
├── rule-engine.md                 # Rule Engine design document
├── TEST_RULE_ENGINE.md            # Hướng dẫn test Rule Engine
├── OPTIMIZATION_SUMMARY.md        # Tóm tắt tối ưu code
└── README.md                      # This file
```

## 🔄 Flow Chi Tiết

### 1. User Query → Response Flow

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: User gửi message                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Parse InBody Data (nếu có)                         │
│  - Tìm pattern: weight, height, BMI, body fat, gender       │
│  - Lưu vào session nếu parse được                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Query Classification                               │
│  - Semantic search "exercises"                              │
│  - Phân loại exercises hoặc general                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
              ┌──────────────────────┐
              │  EXERCISES FLOW      │
              │                      │
              │  1. Semantic Search  │
              │  2. Rule Engine      │
              │  3. LLM Response     │
              │                      │
              └──────────────────────┘
```

### 2. Exercises Flow Chi Tiết

```
User: "Bài tập nào tốt cho ngực?"
      (có InBody: 80kg, 170cm, BMI 27.7, 26% fat)

┌─────────────────────────────────────────────────────────────┐
│  1. Parse InBody từ session                                 │
│     → {weight: 80, height: 170, bmi: 27.7, pbf: 26}         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Semantic Search (RAG)                                   │
│     → Tìm top 10 exercises về "ngực"                        │
│     → ["Chest Builder", "Chest Power", "Chest & Tri..."]    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Normalize InBody → User Signals                         │
│     → BMI_STATUS: OVERWEIGHT                                │
│     → BODY_FAT_STATUS: HIGH                                 │
│     → CENTRAL_FAT: true                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Rule Engine - Safety Filter                             │
│     ✗ Block "Chest & Tri Terror" (ADVANCED)                 │
│     ✗ Block exercises với HIGH_PRESSURE_CORE                │
│     ✓ Allow: "Chest Builder", "Chest Power", "Chest & Abs"  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Rule Engine - Goal Filter                               │
│     +3 điểm cho MODERATE exercises                          │
│     +2 điểm cho BASIC exercises                             │
│     +2 điểm cho full body exercises                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Rule Engine - Scoring & Ranking                         │
│     Chest Builder: score = 5.0                              │
│     Chest Power: score = 4.0                                │
│     Chest & Abs: score = 3.0                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  7. LLM Presentation                                        │
│     → Tạo câu trả lời từ top exercises                      │
│     → Format theo yêu cầu (JSON cho workout plan)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
              Response cho User
```

### 3. Rule Engine - 3 Layers Chi Tiết

#### Layer 1: Safety Filter (Hard-Block)

```python
# Rule 1: Central Fat Protection
IF CENTRAL_FAT = true:
    BLOCK exercises với risk_tag = HIGH_PRESSURE_CORE

# Rule 2: High Body Fat Limitation
IF BODY_FAT_STATUS = HIGH:
    BLOCK difficulty = ADVANCED

# Rule 3: Obese BMI Limitation
IF BMI_STATUS = OBESE:
    BLOCK difficulty = ADVANCED
```

#### Layer 2: Goal Filter (Scoring Adjustment)

```python
# Rule 1: Fat Loss Bias
IF BODY_FAT_STATUS = HIGH:
    +2 điểm nếu calories > 200
    +3 điểm nếu MODERATE difficulty
    +2 điểm nếu BASIC difficulty

# Rule 2: Overweight/Obesity Preference
IF BMI_STATUS in (OVERWEIGHT, OBESE):
    +3 điểm nếu MODERATE
    +2 điểm nếu BASIC
    -2 điểm nếu ADVANCED
    +2 điểm nếu full body exercise

# Rule 3: Underweight Preference
IF BMI_STATUS = UNDERWEIGHT:
    +2 điểm nếu MODERATE
    +1 điểm nếu BASIC
```

#### Layer 3: Scoring & Ranking

```python
# Base Scoring
MODERATE difficulty: +3 điểm
BASIC difficulty: +2 điểm
ADVANCED difficulty: -2 điểm

calories > 250: +2 điểm
calories < 150: -1 điểm

HIGH_PRESSURE_CORE risk: -3 điểm

# Final Score = Base Score + Goal Bonus
# Filter: score >= 0
# Sort: descending (cao nhất trước)
```

## 🎯 Ví dụ sử dụng

### Chat với bot về bài tập (không có InBody):

```
User: "Bài tập nào tốt cho ngực?"

Bot: "Mình gợi ý một số bài tập cho ngực:
- [Chest Builder] - Nhóm cơ: Ngực, Độ khó: Trung bình
- [Chest Power] - Nhóm cơ: Ngực, Độ khó: Trung bình..."
```

### Chat với bot về bài tập (có InBody):

```
User: "Tôi nặng 80kg, cao 170cm, BMI 27.7, tỷ lệ mỡ 26%, giới tính nam"
Bot: "Đã lưu thông tin InBody của bạn."

User: "Bài tập nào tốt cho tôi?"

Bot: "Dựa trên thể trạng của bạn, mình gợi ý:
- [Chest Builder] - MODERATE, 280 kcal
- [Chest Power] - MODERATE, 260 kcal
- [Chest & Abs] - BASIC, 130 kcal

Lưu ý: Mình đã loại bỏ các bài tập ADVANCED và bài tập có áp lực cao lên core để đảm bảo an toàn."
```

## 🔍 Query Classification

Hệ thống tự động phân loại câu hỏi bằng semantic search:

1. **Exercises**: Câu hỏi về bài tập, nhóm cơ, tập luyện
2. **General**: Câu hỏi chung về The New Gym và dịch vụ

## 🧪 Testing

### Test Rule Engine

```bash
cd backend
source venv/bin/activate
python scripts/test_rule_engine.py
```

Xem chi tiết trong [TEST_RULE_ENGINE.md](TEST_RULE_ENGINE.md)

## 🚀 Script tự động

Sử dụng `run_streamlit.sh` để khởi động nhanh:

```bash
chmod +x run_streamlit.sh
./run_streamlit.sh
```

Sau đó truy cập `http://localhost:8501` trong trình duyệt.

**Lưu ý**: Streamlit app sẽ tự động gọi trực tiếp các services từ backend, không cần chạy FastAPI server riêng.

## 🔍 Troubleshooting

### Ollama không chạy

```bash
# Kiểm tra Ollama
ollama list

# Khởi động Ollama
ollama serve

# Kiểm tra model
ollama pull deepseek-r1:7b
```

### RAG Index chưa được build

```bash
# Build index
cd backend
python scripts/build_exercise_index.py --force
```

### Backend/Streamlit lỗi

```bash
# Kiểm tra dependencies
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Kiểm tra environment
cat .env

# Chạy lại Streamlit
streamlit run streamlit_app.py
```

### Rule Engine không hoạt động

1. Kiểm tra InBody data có được parse không (xem console logs)
2. Kiểm tra imports:
   ```bash
   python -c "from services.rule_engine import RuleEngine; print('OK')"
   ```
3. Xem chi tiết trong [TEST_RULE_ENGINE.md](TEST_RULE_ENGINE.md)

## 📚 Tài liệu

- [Rule Engine Design](rule-engine.md): Chi tiết về Rule Engine
- [RAG Processing Flow](docs/rag_processing_flow.md): Chi tiết về luồng xử lý RAG
- [How Vector Search Works](docs/how_vector_search_works.md): Giải thích cách vector search hoạt động
- [Test Rule Engine](TEST_RULE_ENGINE.md): Hướng dẫn test Rule Engine
- [Optimization Summary](OPTIMIZATION_SUMMARY.md): Tóm tắt tối ưu code

## 🎯 Nguyên tắc thiết kế

### Rule Engine

1. **KHÔNG dùng LLM** để quyết định
2. **KHÔNG dùng text prompt** cho logic
3. Chỉ làm việc với **dữ liệu đã chuẩn hóa**
4. **Deterministic** - cùng input → cùng output
5. **Audit & Debug** được - có thể trace mọi quyết định
6. **Chạy trước RAG & LLM** - đảm bảo an toàn

### Kiến trúc

```
Rule Engine = NÃO (quyết định)
RAG = TRÍ NHỚ (tìm kiếm)
LLM = MIỆNG NÓI (trình bày)
```

Nếu LLM tắt → hệ vẫn chạy và trả về bài tập an toàn.

## 📝 License

MIT License - Xem file LICENSE để biết thêm chi tiết.

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

## 📞 Support

Nếu gặp vấn đề, hãy tạo issue trên GitHub repository.
