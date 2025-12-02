# Luồng Xử Lý RAG Chatbot - The New Gym

Tài liệu này mô tả chi tiết cách thức và trình tự thực hiện (luồng xử lý) của hệ thống RAG chatbot trong dự án The New Gym với **Unified RAG System**.

---

## 📋 Mục Lục

1. [Tổng Quan Hệ Thống](#tổng-quan-hệ-thống)
2. [Unified RAG System](#unified-rag-system)
3. [Giai Đoạn 1: Xây Dựng Index (Ingest Pipeline)](#giai-đoạn-1-xây-dựng-index-ingest-pipeline)
4. [Giai Đoạn 2: Xử Lý Câu Hỏi (Serving Pipeline)](#giai-đoạn-2-xử-lý-câu-hỏi-serving-pipeline)
5. [Query Classification](#query-classification)
6. [Chi Tiết Các Thành Phần](#chi-tiết-các-thành-phần)
7. [Ví Dụ Luồng Xử Lý](#ví-dụ-luồng-xử-lý)

---

## Tổng Quan Hệ Thống

Hệ thống RAG chatbot của The New Gym sử dụng **Unified RAG System** với topic registry, cho phép dễ dàng mở rộng với nhiều topics khác nhau.

### Kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED RAG SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │  INGEST PIPELINE │              │ SERVING PIPELINE │         │
│  │  (Offline)       │              │  (Online)        │         │
│  └──────────────────┘              └──────────────────┘         │
│           │                                │                    │
│           ▼                                ▼                    │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │  Vector Store    │◀─────────────│  Query Handler   │         │
│  │  (ChromaDB)      │              │                  │         │
│  └──────────────────┘              └──────────────────┘         │
│           │                                │                    │
│           ▼                                ▼                    │
│  ┌──────────────────────────────────────────────┐               │
│  │         TOPIC REGISTRY                       │               │
│  │  - clubs (club_documents)                    │               │
│  │  - exercises (exercise_documents)            │               │
│  │  - [future topics...]                        │               │
│  └──────────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Topics hiện có

1. **Clubs**: Thông tin về các chi nhánh The New Gym

   - Collection: `club_documents`
   - Source: `data/clubs.md`
   - Max items: 2000

2. **Exercises**: Thông tin về các bài tập thể hình
   - Collection: `exercise_documents`
   - Source: `data/exercise.md`
   - Max items: 500

---

## Unified RAG System

### Cấu trúc

Hệ thống sử dụng **Base RAG Class** và **Topic Registry** để quản lý nhiều topics:

```python
# Base RAG Class (rag/base_rag.py)
class BaseRAG:
    - topic_name: str
    - collection_name: str
    - parser: TopicParser
    - text_builder: TopicTextBuilder
    - metadata_builder: TopicMetadataBuilder
    - source_path: Path
    - max_items: int

# Topic Registry (rag/unified_rag.py)
_rag_registry: Dict[str, BaseRAG] = {
    "clubs": BaseRAG(...),
    "exercises": BaseRAG(...)
}
```

### Cách thêm topic mới

1. Tạo file `rag/topics/your_topic.py` với 3 classes:

   - `YourTopicParser` (kế thừa `TopicParser`)
   - `YourTopicTextBuilder` (kế thừa `TopicTextBuilder`)
   - `YourTopicMetadataBuilder` (kế thừa `TopicMetadataBuilder`)

2. Đăng ký topic trong `rag/__init__.py`:

   ```python
   from rag.topics.your_topic import register_your_topic
   register_your_topic()
   ```

3. Sử dụng:
   ```python
   from rag.unified_rag import semantic_search, build_index
   build_index("your_topic", force_refresh=True)
   results = semantic_search("your_topic", "query", top_k=5)
   ```

---

## Giai Đoạn 1: Xây Dựng Index (Ingest Pipeline)

Giai đoạn này được thực hiện **offline** để xây dựng vector database từ file Markdown.

### Trình Tự Thực Hiện

#### Bước 1: Khởi Tạo Môi Trường

**File**: `rag/base_rag.py`

```python
# Thiết lập các biến môi trường
- HF_HUB_ENABLE_HF_XET = "0"
- HF_HUB_ENABLE_XET = "0"
- HF_HUB_ENABLE_HF_TRANSFER = "0"
- HF_HUB_DISABLE_TELEMETRY = "1"
- HF_HOME = DATA_DIR / "hf_cache"
- HF_HUB_CACHE = DATA_DIR / "hf_cache"
```

#### Bước 2: Tải Mô Hình Embedding

**File**: `rag/base_rag.py` → `_get_embedding_model()`

```python
model = SentenceTransformer("dangvantuan/vietnamese-embedding")
```

**Mô hình**: `dangvantuan/vietnamese-embedding`

- Hỗ trợ tiếng Việt
- Kích thước embedding: 384 dimensions
- Được cache trong `data/rag/hf_cache/`

#### Bước 3: Đăng Ký Topics

**File**: `rag/unified_rag.py` → `_auto_register_topics()`

Topics được đăng ký tự động khi gọi `semantic_search()` hoặc `build_index()` lần đầu (lazy registration).

#### Bước 4: Parse Dữ Liệu Từ Markdown

**File**: `rag/topics/clubs.py` → `ClubsParser.parse()`

**Nguồn dữ liệu**: `backend/data/clubs.md` hoặc `backend/data/exercise.md`

**Format file Markdown**:

```markdown
## CLB 1 — Tên Club (ID)

- Tên tiếng Việt: ...
- Tên tiếng Anh: ...
- Địa chỉ: ...
- Ngày mở: ...
- Hoạt động: có/không
- Website: ...
- Tọa độ: ...
```

**Quá trình parse**:

1. Đọc toàn bộ nội dung file markdown
2. Sử dụng regex pattern để tách từng section
3. Parse từng field từ nội dung
4. Parse thành phố và quận từ địa chỉ (cho clubs)

#### Bước 5: Xây Dựng Text Chunks

**File**: `rag/topics/clubs.py` → `ClubsTextBuilder.build_text()`

Với mỗi item, tạo một text chunk chứa thông tin quan trọng:

**Clubs**:

```
Chi nhánh: {nameVi hoặc nameEn}
Tên tiếng Anh: {nameEn} (nếu khác nameVi)
Địa chỉ: {location hoặc address}
Khu vực: {district}, {city}
Trang web: {informationUrl}
Tọa độ: {latitude}, {longitude} (nếu có)
Ngày mở cửa: {openDate} (nếu có)
Trạng thái: Đang hoạt động / Tạm đóng
```

**Exercises**:

```
Bài tập: {nameVi hoặc nameEn}
Tên tiếng Anh: {nameEn} (nếu khác nameVi)
Nhóm cơ: {muscleGroup}
Độ khó: {difficulty}
Kcal tiêu thụ: {calories}
```

#### Bước 6: Tạo Embeddings

**File**: `rag/base_rag.py` → `VietnameseEmbeddingFunction._embed()`

1. Tokenize text tiếng Việt: `tokenize(text)`
2. Gọi `model.encode(tokenized_texts)` để tạo embeddings
3. Nhận về vector 384 dimensions

#### Bước 7: Lưu Vào ChromaDB

**File**: `rag/base_rag.py` → `BaseRAG.build_index()`

```python
collection.add(
    ids=[item_id_1, item_id_2, ...],
    documents=[text_chunk_1, text_chunk_2, ...],
    metadatas=[metadata_1, metadata_2, ...]
)
```

**Metadata** chứa:

- Thông tin quan trọng của item (name, city, district, etc.)
- `raw`: Toàn bộ JSON của item (serialized)

**Collection Name**: Mỗi topic có collection riêng

- Clubs: `club_documents`
- Exercises: `exercise_documents`

**Distance Metric**: Cosine similarity (`hnsw:space: cosine`)

### Build Index

```bash
# Build tất cả topics
python scripts/build_club_index.py --force

# Chỉ build clubs
python scripts/build_club_index.py --force --skip-exercises

# Incremental update (không force)
python scripts/build_club_index.py
```

---

## Giai Đoạn 2: Xử Lý Câu Hỏi (Serving Pipeline)

Giai đoạn này được thực hiện **online** mỗi khi người dùng gửi câu hỏi qua API `/chat`.

### Trình Tự Thực Hiện

#### Bước 1: Nhận Request Từ Frontend

**File**: `backend/main.py` → `@app.post("/chat")`

```python
POST /chat
{
  "message": "Bạn có chi nhánh nào ở Gò Vấp không?",
  "session_id": "user_123"
}
```

#### Bước 2: Query Classification

**File**: `backend/utils/query_classifier.py` → `classify_query()`

Hệ thống tự động phân loại câu hỏi bằng cách:

1. Gọi `semantic_search("clubs", message, top_k=3)`
2. Gọi `semantic_search("exercises", message, top_k=3)`
3. So sánh scores giữa hai kết quả:
   - Nếu club score tốt hơn đáng kể → `"clubs"`
   - Nếu exercise score tốt hơn đáng kể → `"exercises"`
   - Nếu cả hai đều có score quá cao → `"general"`

**Logic so sánh**:

- Tính best score và average score cho mỗi topic
- Nếu chênh lệch > 0.15 hoặc > 20% → chọn topic tốt hơn
- Nếu scores gần nhau → so sánh average score

#### Bước 3: Xử Lý Câu Hỏi Exercises (Ưu tiên)

**File**: `backend/main.py` → `is_exercise_related_query()`

Nếu `is_exercise_query = True`:

1. Gọi `generate_exercise_response(message)`
2. Kiểm tra câu hỏi về số lượng → Trả về thống kê
3. Thử semantic search với topic "exercises"
4. Xây dựng context từ kết quả
5. Gọi LLM với context và trả về

#### Bước 4: Xử Lý Câu Hỏi Clubs

**File**: `backend/main.py` → `is_club_related_query()`

Nếu `is_club_query = True`:

1. Gọi `generate_club_response(message)`
2. Lấy danh sách clubs đang hoạt động
3. **Tìm kiếm theo keyword** (bước đầu tiên):
   - Tìm clubs có từ khóa trong name, address, district, city
   - Nếu tìm thấy → Xây dựng context và trả về
4. **Semantic search** (nếu không có keyword match):
   - Gọi `semantic_search("clubs", message, top_k=4)`
   - Xây dựng context từ kết quả
5. **Fallback** (nếu không tìm thấy):
   - Trả về overall context + no data message

#### Bước 5: Xử Lý Câu Hỏi General

Nếu không phải exercises hoặc clubs:

1. Load system prompt từ `prompt_system.txt`
2. Gọi LLM trực tiếp (không có RAG context)
3. Trả về response

---

## Query Classification

### Cách hoạt động

**File**: `backend/utils/query_classifier.py`

```python
def classify_query(message: str) -> Literal["clubs", "exercises", "general"]:
    # 1. Semantic search cho cả hai topics
    club_results = semantic_search("clubs", message, top_k=3)
    exercise_results = semantic_search("exercises", message, top_k=3)

    # 2. So sánh scores
    best_club_score = min(r.get("score") for r in club_results)
    best_exercise_score = min(r.get("score") for r in exercise_results)

    # 3. Quyết định dựa trên scores
    if best_club_score < best_exercise_score - 0.15:
        return "clubs"
    elif best_exercise_score < best_club_score - 0.15:
        return "exercises"
    else:
        return "general"
```

### Ưu điểm

- Không cần keywords hardcode
- Tự động học từ embeddings
- Có thể phân biệt các câu hỏi tương tự

---

## Chi Tiết Các Thành Phần

### 1. BaseRAG (`rag/base_rag.py`)

**Vai trò**: Base class chung cho tất cả topics

**Tính năng**:

- Quản lý ChromaDB client và collection
- Embedding model (shared across all topics)
- Build index từ source data
- Semantic search

**Methods chính**:

- `build_index()`: Xây dựng/rebuild index
- `semantic_search()`: Tìm kiếm semantic với query
- `refresh_index()`: Force rebuild index

### 2. UnifiedRAG (`rag/unified_rag.py`)

**Vai trò**: Topic registry và unified API

**Tính năng**:

- Đăng ký topics (lazy registration)
- Unified API cho tất cả topics
- Quản lý registry

**Functions chính**:

- `register_topic()`: Đăng ký topic mới
- `semantic_search(topic_name, query, top_k)`: Semantic search cho topic
- `build_index(topic_name, force_refresh, **kwargs)`: Build index cho topic
- `get_all_topics()`: Lấy danh sách topics

### 3. Topic Configurations (`rag/topics/`)

**Clubs** (`rag/topics/clubs.py`):

- `ClubsParser`: Parse clubs từ markdown
- `ClubsTextBuilder`: Xây dựng text chunk từ club data
- `ClubsMetadataBuilder`: Xây dựng metadata từ club data

**Exercises** (`rag/topics/exercises.py`):

- `ExercisesParser`: Parse exercises từ markdown
- `ExercisesTextBuilder`: Xây dựng text chunk từ exercise data
- `ExercisesMetadataBuilder`: Xây dựng metadata từ exercise data

### 4. QueryClassifier (`utils/query_classifier.py`)

**Vai trò**: Phân loại câu hỏi tự động

**Tính năng**:

- Dùng semantic search để phân loại
- So sánh scores giữa các topics
- Trả về "clubs", "exercises", hoặc "general"

### 5. ClubService (`services/club_service.py`)

**Vai trò**: Xử lý logic liên quan đến club queries

**Tính năng**:

- Tìm kiếm keyword-based
- Xây dựng context từ clubs
- Tạo câu trả lời từ context

### 6. ExerciseService (`services/exercise_service.py`)

**Vai trò**: Xử lý logic liên quan đến exercise queries

**Tính năng**:

- Semantic search cho exercises
- Xây dựng context từ exercises
- Tạo câu trả lời từ context

---

## Ví Dụ Luồng Xử Lý

### Ví Dụ 1: Câu Hỏi Về Clubs (Keyword Match)

**Input**: "Bạn có chi nhánh nào ở Gò Vấp không?"

**Luồng xử lý**:

1. ✅ `classify_query()` → `"clubs"` (semantic search tìm thấy clubs có score tốt hơn)
2. ✅ `is_club_related_query()` → `True`
3. ✅ `generate_club_response()` được gọi
4. ✅ `search_clubs_by_keyword()` → Tìm thấy clubs có "Gò Vấp" trong `district.districtName`
5. ✅ `build_context_from_clubs()` → Tạo context cho các clubs tìm được
6. ✅ `generate_answer_from_context()` → Gọi LLM với context
7. ✅ LLM trả về: "Mình tìm thấy X chi nhánh ở Gò Vấp: ..."
8. ✅ Response được trả về cho frontend

**Kết quả**: Không cần dùng semantic search vì đã tìm thấy bằng keyword search.

---

### Ví Dụ 2: Câu Hỏi Về Exercises

**Input**: "Bài tập nào tốt cho ngực?"

**Luồng xử lý**:

1. ✅ `classify_query()` → `"exercises"` (semantic search tìm thấy exercises có score tốt hơn)
2. ✅ `is_exercise_related_query()` → `True`
3. ✅ `generate_exercise_response()` được gọi
4. ✅ `semantic_search("exercises", message, top_k=4)` → Tìm thấy exercises về ngực
5. ✅ `build_context_from_exercises()` → Tạo context từ 4 exercises
6. ✅ `generate_answer_from_context()` → Gọi LLM với context
7. ✅ LLM trả về: "Mình gợi ý một số bài tập cho ngực: ..."
8. ✅ Response được trả về cho frontend

**Kết quả**: Sử dụng RAG (semantic search) để tìm exercises phù hợp.

---

### Ví Dụ 3: Câu Hỏi Semantic (Cần RAG)

**Input**: "Chi nhánh gym có hồ bơi ở khu trung tâm"

**Luồng xử lý**:

1. ✅ `classify_query()` → `"clubs"`
2. ✅ `is_club_related_query()` → `True`
3. ✅ `generate_club_response()` được gọi
4. ❌ `search_clubs_by_keyword()` → Không tìm thấy keyword match trực tiếp
5. ✅ `semantic_search("clubs", message, top_k=4)` được gọi
   - Tạo embedding cho câu hỏi
   - Query ChromaDB
   - Trả về top-4 clubs có embedding gần nhất
6. ✅ `build_context_from_clubs()` → Tạo context từ 4 clubs
7. ✅ `generate_answer_from_context()` → Gọi LLM với context
8. ✅ LLM trả về: "Mình gợi ý một vài chi nhánh phù hợp nhất: ..."
9. ✅ Response được trả về cho frontend

**Kết quả**: Sử dụng RAG (semantic search) để tìm clubs phù hợp với ngữ nghĩa của câu hỏi.

---

### Ví Dụ 4: Câu Hỏi Không Tìm Thấy Kết Quả

**Input**: "Bạn có chi nhánh nào ở Thủ Đức không?"

**Luồng xử lý**:

1. ✅ `classify_query()` → `"clubs"`
2. ✅ `is_club_related_query()` → `True`
3. ✅ `generate_club_response()` được gọi
4. ❌ `search_clubs_by_keyword()` → Không tìm thấy
5. ❌ `semantic_search()` → Không tìm thấy clubs ở Thủ Đức
6. ✅ `build_overall_context()` → Tạo context tổng quan
7. ✅ `build_no_data_message("Thủ Đức", "city", clubs)` → Tạo thông báo không tìm thấy + gợi ý 3 chi nhánh khác
8. ✅ `generate_answer_from_context()` → Gọi LLM với context tổng quan + no data message
9. ✅ LLM trả về: "Mình chưa tìm thấy chi nhánh nào ở Thủ Đức. Bạn có thể tham khảo một số chi nhánh đang hoạt động gần khu vực khác: ..."
10. ✅ Response được trả về cho frontend

**Kết quả**: Trả về thông báo không tìm thấy kèm gợi ý các chi nhánh khác.

---

### Ví Dụ 5: Câu Hỏi General

**Input**: "Tôi muốn biết về dịch vụ của The New Gym"

**Luồng xử lý**:

1. ✅ `classify_query()` → `"general"` (cả clubs và exercises đều có score cao)
2. ❌ `is_exercise_related_query()` → `False`
3. ❌ `is_club_related_query()` → `False`
4. ✅ Chuyển sang LLM tổng quát
5. ✅ `load_system_prompt()` → Load `prompt_system.txt`
6. ✅ `get_ai_response(messages, system_prompt)` → Gọi LLM trực tiếp
7. ✅ LLM trả về câu trả lời về dịch vụ
8. ✅ Response được trả về cho frontend

**Kết quả**: Không sử dụng RAG, chỉ dùng LLM tổng quát.

---

## Tóm Tắt

### Ưu Tiên Xử Lý Câu Hỏi

1. **Query Classification**: Phân loại câu hỏi (exercises, clubs, general)
2. **Exercises**:
   - Semantic search → Build context → LLM
3. **Clubs**:
   - Keyword search → Semantic search (fallback) → Build context → LLM
4. **General**:
   - LLM trực tiếp (không có RAG context)

### Khi Nào Index Được Rebuild?

- **Force rebuild**: Khi chạy `python scripts/build_club_index.py --force`
- **Incremental update**: Khi chạy `python scripts/build_club_index.py` (nếu DB đã tồn tại)
- **Auto rebuild**: Khi `semantic_search()` phát hiện collection không tồn tại (tự động rebuild)

### Lưu Ý

- Index chỉ chứa **active clubs** (`isActive == 1`)
- Dữ liệu nguồn: File Markdown (`data/clubs.md`, `data/exercise.md`)
- Vector database được lưu persistent trên disk (SQLite trong `data/rag/chroma/`)
- Mỗi topic có collection riêng trong ChromaDB
- Topics được đăng ký tự động (lazy registration) khi cần
