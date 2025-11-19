# Luồng Xử Lý RAG Chatbot - The New Gym

Tài liệu này mô tả chi tiết cách thức và trình tự thực hiện (luồng xử lý) của hệ thống RAG chatbot trong dự án The New Gym.

---

## 📋 Mục Lục

1. [Tổng Quan Hệ Thống](#tổng-quan-hệ-thống)
2. [Giai Đoạn 1: Xây Dựng Index (Ingest Pipeline)](#giai-đoạn-1-xây-dựng-index-ingest-pipeline)
3. [Giai Đoạn 2: Xử Lý Câu Hỏi (Serving Pipeline)](#giai-đoạn-2-xử-lý-câu-hỏi-serving-pipeline)
4. [Chi Tiết Các Thành Phần](#chi-tiết-các-thành-phần)
5. [Ví Dụ Luồng Xử Lý](#ví-dụ-luồng-xử-lý)

---

## Tổng Quan Hệ Thống

Hệ thống RAG chatbot của The New Gym được chia thành 2 giai đoạn chính:

1. **Ingest Pipeline**: Xây dựng và cập nhật vector database từ dữ liệu API
2. **Serving Pipeline**: Xử lý câu hỏi của người dùng và trả về câu trả lời

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG CHATBOT SYSTEM                           │
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
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Giai Đoạn 1: Xây Dựng Index (Ingest Pipeline)

Giai đoạn này được thực hiện **offline** để xây dựng vector database từ dữ liệu API. Index được xây dựng lại mỗi khi chạy `run.sh` hoặc khi gọi script `build_club_index.py`.

### Trình Tự Thực Hiện

#### Bước 1: Khởi Tạo Môi Trường

**File**: `backend/rag/club_rag.py`

```python
# Thiết lập các biến môi trường
- HF_HUB_ENABLE_HF_XET = "0"
- HF_HUB_ENABLE_XET = "0"
- HF_HUB_ENABLE_HF_TRANSFER = "0"
- HF_HOME = DATA_DIR / "hf_cache"
```

**Mục đích**:

- Tắt các tính năng không cần thiết của HuggingFace Hub
- Đặt thư mục cache để tránh lỗi permission

#### Bước 2: Tạo Thư Mục Lưu Trữ

**File**: `backend/rag/club_rag.py` → `_ensure_data_dir()`

```
backend/data/rag/
├── chroma/          # ChromaDB persistent storage
└── hf_cache/        # HuggingFace model cache
```

#### Bước 3: Khởi Tạo ChromaDB Client

**File**: `backend/rag/club_rag.py` → `_get_client()`

- Tạo `PersistentClient` với đường dẫn `backend/data/rag/chroma`
- Client này sẽ lưu trữ vector database trên disk

#### Bước 4: Tải Mô Hình Embedding

**File**: `backend/rag/club_rag.py`

```python
_embedding_model = TextEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
```

**Mô hình**: `paraphrase-multilingual-MiniLM-L12-v2`

- Hỗ trợ đa ngôn ngữ (bao gồm tiếng Việt)
- Kích thước embedding: 384 dimensions
- Được tải và cache trong `hf_cache/`

#### Bước 5: Lấy Dữ Liệu Từ API

**File**: `backend/rag/club_rag.py` → `build_club_index()`

```python
clubs = clubs_client.get_active_clubs(use_cache=not force_refresh)
```

**File**: `backend/utils/clubs_client.py` → `get_active_clubs()`

1. Kiểm tra cache (TTL = 5 phút)
2. Nếu cache hợp lệ → trả về cache
3. Nếu không → gọi API `GET /api/v1/general/clubs`
4. Lọc các club có `isActive == 1`
5. Lưu vào cache và trả về

**API Endpoint**: `https://stg-mobile.gateway.thenewgym.vn/api/v1/general/clubs`

#### Bước 6: Xây Dựng Text Chunks

**File**: `backend/rag/club_rag.py` → `_build_text_from_club()`

Với mỗi club, tạo một text chunk chứa:

```
Tên: {nameVi hoặc nameEn}
Địa chỉ: {location hoặc address}
Quận/Huyện: {district.districtName}
Thành phố: {city.cityName}
Link: {informationUrl}
Mô tả: {description} (nếu có)
```

**Ví dụ**:

```
Tên: Hoàng Văn Thụ
Địa chỉ: 123 Hoàng Văn Thụ, Phường 4, Tân Bình, Hồ Chí Minh
Quận/Huyện: Tân Bình
Thành phố: Hồ Chí Minh
Link: https://thenewgym.vn/hoang-van-thu/
```

#### Bước 7: Tạo Embeddings

**File**: `backend/rag/club_rag.py` → `FastEmbedFunction`

Với mỗi text chunk:

1. Gọi `_embedding_model.embed(text)`
2. Nhận về vector 384 dimensions
3. Vector này đại diện cho ngữ nghĩa của text chunk

#### Bước 8: Lưu Vào ChromaDB

**File**: `backend/rag/club_rag.py` → `build_club_index()`

```python
collection.add(
    ids=[club_id_1, club_id_2, ...],
    documents=[text_chunk_1, text_chunk_2, ...],
    metadatas=[metadata_1, metadata_2, ...]
)
```

**Metadata** cho mỗi document:

```json
{
  "name": "Hoàng Văn Thụ",
  "city": "Hồ Chí Minh",
  "district": "Tân Bình",
  "link": "https://thenewgym.vn/hoang-van-thu/",
  "raw": "{toàn bộ JSON của club}"
}
```

**Collection Name**: `club_documents`
**Distance Metric**: Cosine similarity (`hnsw:space: cosine`)

#### Bước 9: Lưu Metadata JSON

**File**: `backend/rag/club_rag.py` → `build_club_index()`

Lưu file `backend/data/rag/clubs_meta.json` chứa:

- ID của mỗi club
- Tên, địa chỉ, thành phố, quận
- Link và raw data

**Mục đích**: Dùng để tra cứu nhanh metadata mà không cần query ChromaDB

### Kết Quả

Sau khi hoàn thành ingest pipeline:

- ✅ Vector database được lưu trong `backend/data/rag/chroma/`
- ✅ Metadata JSON được lưu trong `backend/data/rag/clubs_meta.json`
- ✅ Sẵn sàng cho giai đoạn serving

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

#### Bước 2: Phân Loại Intent (Club-Related hay Không)

**File**: `backend/main.py` → `is_club_related_query()`

**File**: `backend/services/club_service.py` → `is_club_related_query()`

Kiểm tra các từ khóa:

- Từ khóa club: "club", "phòng gym", "chi nhánh", "địa điểm", "cơ sở", ...
- Tên thành phố: "hcm", "hồ chí minh", "đà nẵng", "cần thơ", ...
- Tên quận: "quận 1", "quận 2", "gò vấp", "tân bình", ...
- Câu hỏi số lượng: "bao nhiêu", "có mấy", "có bao nhiêu" + "gym"/"chi nhánh"

**Kết quả**:

- ✅ `is_club_query = True` → Chuyển sang xử lý club
- ❌ `is_club_query = False` → Chuyển sang LLM tổng quát

#### Bước 3: Xử Lý Câu Hỏi Club (Nếu Có)

**File**: `backend/services/club_service.py` → `generate_club_response()`

##### 3.1. Chuẩn Bị Dữ Liệu

```python
# Lấy tất cả clubs hoặc chỉ active clubs
wants_inactive = any(keyword in message for keyword in INACTIVE_KEYWORDS)
all_clubs = clubs_client.fetch_clubs()
clubs = all_clubs if wants_inactive else clubs_client.get_active_clubs()
```

##### 3.2. Kiểm Tra Câu Hỏi Số Lượng

```python
is_count_query = any(keyword in normalized for keyword in COUNT_KEYWORDS)
# COUNT_KEYWORDS = ["bao nhiêu", "có mấy", "có bao nhiêu", "tổng số", "số lượng"]
```

Nếu là câu hỏi số lượng → Trả về tổng quan ngay lập tức (không dùng RAG)

##### 3.3. Tìm Kiếm Theo Tên Club (Exact Match)

**File**: `backend/services/club_service.py` → `find_club_by_name()`

```python
club = find_club_by_name(message, all_clubs)
```

**Logic**:

1. Normalize message và tên club (lowercase, bỏ dấu)
2. So khớp với `nameVi` hoặc `nameEn`
3. Nếu tìm thấy → Trả về club đó

**Ví dụ**: "Hoàng Văn Thụ" → Tìm thấy club có tên "Hoàng Văn Thụ"

##### 3.4. Tìm Kiếm Theo Quận/Huyện

**File**: `backend/services/club_service.py` → `detect_district_from_message()`

```python
requested_district = detect_district_from_message(message)
if requested_district:
    district_clubs = find_clubs_by_district(requested_district, clubs)
```

**Logic**:

1. Sử dụng `DISTRICT_ALIAS_MAP` để chuẩn hóa tên quận
   - Ví dụ: "gò vấp" → "Gò Vấp", "quận gò vấp" → "Gò Vấp"
2. Tìm các club có `district.districtName` khớp
3. Nếu tìm thấy → Trả về danh sách clubs trong quận đó

**Ví dụ**: "quận gò vấp" → Tìm thấy các club ở "Gò Vấp"

##### 3.5. Tìm Kiếm Theo Thành Phố

**File**: `backend/services/club_service.py` → `detect_city_from_message()`

```python
requested_city = detect_city_from_message(message)
if requested_city:
    city_clubs = [club for club in clubs
                  if normalize_text(club.get("city", {}).get("cityName", "")) == target_norm]
```

**Logic**:

1. Sử dụng `CITY_ALIAS_MAP` để chuẩn hóa tên thành phố
   - Ví dụ: "hcm" → "Hồ Chí Minh", "tphcm" → "Hồ Chí Minh"
2. Tìm các club có `city.cityName` khớp
3. Nếu tìm thấy → Trả về danh sách clubs trong thành phố đó

**Ví dụ**: "đà nẵng" → Tìm thấy các club ở "Đà Nẵng"

##### 3.6. Semantic Search (RAG) - Fallback

**Chỉ chạy khi**: Không tìm thấy kết quả từ exact match, quận, hoặc thành phố

**File**: `backend/rag/club_rag.py` → `semantic_search()`

```python
semantic_results = semantic_search(message, top_k=MAX_CONTEXT_CLUBS)
```

**Trình tự**:

1. Lấy collection từ ChromaDB
2. Tạo embedding cho câu hỏi của người dùng
3. Query ChromaDB với `collection.query(query_texts=[query], n_results=top_k)`
4. ChromaDB trả về top-k documents có embedding gần nhất (cosine similarity)
5. Parse kết quả và trả về danh sách clubs

**Ví dụ**:

- Câu hỏi: "chi nhánh gym có hồ bơi ở khu trung tâm"
- Semantic search tìm các club có mô tả/địa chỉ liên quan đến "hồ bơi", "trung tâm"

##### 3.7. Xây Dựng Context

**File**: `backend/services/club_service.py` → `build_context_from_clubs()`

Với mỗi club được tìm thấy (tối đa `MAX_CONTEXT_CLUBS = 4`), tạo context block:

```
Tên: {nameVi hoặc nameEn}
Địa chỉ: {location}
Quận/Huyện: {district.districtName}
Thành phố: {city.cityName}
Link: {informationUrl}
```

**Ví dụ**:

```
[Đoạn 1] Tên: Hoàng Văn Thụ
Địa chỉ: 123 Hoàng Văn Thụ, Phường 4, Tân Bình, Hồ Chí Minh
Quận/Huyện: Tân Bình
Thành phố: Hồ Chí Minh
Link: https://thenewgym.vn/hoang-van-thu/

[Đoạn 2] Tên: Nguyễn Chí Thanh
...
```

Nếu có nhiều clubs (theo quận/thành phố), thêm context thống kê:

**File**: `backend/services/club_service.py` → `build_counts_context()`

```
Tổng quan khu vực {label}:
- Chi nhánh đang hoạt động: {count}
```

##### 3.8. Tạo Câu Trả Lời Từ Context

**File**: `backend/services/club_service.py` → `generate_answer_from_context()`

**Prompt được xây dựng**:

```
Ngữ cảnh:
[Đoạn 1] Tên: Hoàng Văn Thụ
...

Hướng dẫn:
- Chỉ sử dụng thông tin trong các đoạn ngữ cảnh.
- Liệt kê tối đa 3 chi nhánh phù hợp nhất, mỗi chi nhánh gồm tên, địa chỉ, link (nếu có).
- Dùng Markdown để hiển thị link dạng (URL).

Câu hỏi của khách: {message}
```

**System Prompt** (`RAG_SYSTEM_PROMPT`):

```
Bạn là AI Assistant của The New Gym.
Chỉ trả lời dựa trên ngữ cảnh cung cấp, không tự suy đoán thêm.
Luôn trả lời bằng tiếng Việt, giọng thân thiện, mạch lạc.
Mỗi chi nhánh nên bao gồm tên (ưu tiên tiếng Việt), địa chỉ và link ở dạng [Tên](URL).
Nếu không tìm thấy thông tin phù hợp trong ngữ cảnh, hãy nói rõ và gợi ý khách cung cấp thêm dữ liệu.
```

##### 3.9. Gọi LLM

**File**: `backend/services/llm_service.py` → `get_ai_response()`

**Logic**:

1. Kiểm tra `AI_PROVIDER` (mặc định: "ollama")
2. Nếu `ollama` → Gọi `get_ollama_response()`
3. Nếu `deepseek` → Gọi `get_deepseek_response()`

**Ollama**:

- Endpoint: `http://localhost:11434/api/chat`
- Model: Được cấu hình trong `utils/ollama_client.py`

**DeepSeek**:

- Endpoint: `https://api.deepseek.com/chat/completions`
- Model: `deepseek-chat` (hoặc từ env `DEEPSEEK_MODEL`)
- API Key: Từ env `DEEPSEEK_API_KEY`

**Request**:

```json
{
  "model": "...",
  "messages": [
    { "role": "system", "content": "{RAG_SYSTEM_PROMPT}" },
    { "role": "user", "content": "{prompt với context}" }
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

##### 3.10. Trả Về Response

**File**: `backend/main.py` → `@app.post("/chat")`

```python
return ChatResponse(
    response=club_response_text,  # Từ LLM
    session_id=session_id,
    nutrition_info=None
)
```

#### Bước 4: Xử Lý Câu Hỏi Không Liên Quan Club

Nếu `is_club_query = False`:

**File**: `backend/main.py` → `@app.post("/chat")`

```python
# Load system prompt tổng quát
system_prompt = load_system_prompt()  # Từ prompt_system.txt

# Gọi LLM trực tiếp (không có context)
ai_response = get_ai_response(messages, system_prompt)
```

**System Prompt**: Từ `backend/prompt_system.txt`

- Hướng dẫn AI về dinh dưỡng, thể hình, thông tin chung về The New Gym

---

## Chi Tiết Các Thành Phần

### 1. ClubsClient (`backend/utils/clubs_client.py`)

**Vai trò**: Client để lấy dữ liệu từ API

**Tính năng**:

- Cache dữ liệu (TTL = 5 phút)
- Lấy tất cả clubs hoặc chỉ active clubs
- Tìm kiếm theo tên, thành phố, quận
- Format dữ liệu cho prompt

**Methods chính**:

- `fetch_clubs()`: Lấy tất cả clubs từ API
- `get_active_clubs()`: Lấy chỉ clubs đang hoạt động
- `get_clubs_by_city()`: Lọc theo thành phố
- `get_clubs_by_district()`: Lọc theo quận
- `search_clubs()`: Tìm kiếm theo từ khóa

### 2. ClubService (`backend/services/club_service.py`)

**Vai trò**: Xử lý logic liên quan đến club queries

**Tính năng**:

- Phát hiện intent club-related
- Chuẩn hóa tên thành phố/quận (alias mapping)
- Tìm kiếm exact match (tên, quận, thành phố)
- Xây dựng context từ clubs
- Tạo câu trả lời từ context

**Functions chính**:

- `is_club_related_query()`: Phát hiện câu hỏi về club
- `detect_city_from_message()`: Phát hiện tên thành phố
- `detect_district_from_message()`: Phát hiện tên quận
- `find_club_by_name()`: Tìm club theo tên
- `find_clubs_by_district()`: Tìm clubs theo quận
- `generate_club_response()`: Tạo câu trả lời cho câu hỏi về club
- `generate_answer_from_context()`: Gọi LLM với context

### 3. ClubRAG (`backend/rag/club_rag.py`)

**Vai trò**: Quản lý vector database và semantic search

**Tính năng**:

- Xây dựng index từ clubs (ingest)
- Semantic search với embeddings
- Quản lý ChromaDB collection

**Functions chính**:

- `build_club_index()`: Xây dựng/rebuild index
- `semantic_search()`: Tìm kiếm semantic với query
- `refresh_club_index()`: Force rebuild index

### 4. LLMService (`backend/services/llm_service.py`)

**Vai trò**: Interface để gọi LLM (Ollama hoặc DeepSeek)

**Tính năng**:

- Hỗ trợ nhiều AI provider
- Xử lý lỗi và fallback

**Functions chính**:

- `get_ai_response()`: Dispatcher chọn provider
- `get_ollama_response()`: Gọi Ollama API
- `get_deepseek_response()`: Gọi DeepSeek API

### 5. Main API (`backend/main.py`)

**Vai trò**: FastAPI application, xử lý HTTP requests

**Endpoints chính**:

- `POST /chat`: Xử lý câu hỏi của người dùng
- `GET /clubs`: Lấy danh sách clubs
- `GET /clubs/active`: Lấy clubs đang hoạt động
- `GET /clubs/search`: Tìm kiếm clubs
- `GET /ai-status`: Kiểm tra trạng thái AI provider

---

## Ví Dụ Luồng Xử Lý

### Ví Dụ 1: Câu Hỏi Về Quận Cụ Thể

**Input**: "Bạn có chi nhánh nào ở Gò Vấp không?"

**Luồng xử lý**:

1. ✅ `is_club_related_query()` → `True` (có từ khóa "chi nhánh", "gò vấp")

2. ✅ `generate_club_response()` được gọi

3. ✅ `detect_district_from_message()` → Tìm thấy "Gò Vấp"

   - Normalize: "gò vấp" → "Gò Vấp" (từ `DISTRICT_ALIAS_MAP`)

4. ✅ `find_clubs_by_district("Gò Vấp", clubs)` → Tìm thấy 2 clubs

5. ✅ `build_context_from_clubs()` → Tạo context cho 2 clubs

6. ✅ `build_counts_context("Gò Vấp", district_clubs)` → Thêm thống kê

7. ✅ `generate_answer_from_context()` → Gọi LLM với context

8. ✅ LLM trả về: "Mình tìm thấy 2 chi nhánh ở Quận Gò Vấp: ..."

9. ✅ Response được trả về cho frontend

**Kết quả**: Không cần dùng RAG (semantic search) vì đã tìm thấy bằng exact match.

---

### Ví Dụ 2: Câu Hỏi Semantic (Cần RAG)

**Input**: "Chi nhánh gym có hồ bơi ở khu trung tâm"

**Luồng xử lý**:

1. ✅ `is_club_related_query()` → `True`

2. ✅ `generate_club_response()` được gọi

3. ❌ `find_club_by_name()` → Không tìm thấy

4. ❌ `detect_district_from_message()` → Không tìm thấy

5. ❌ `detect_city_from_message()` → Không tìm thấy

6. ❌ `is_count_query` → `False`

7. ✅ `semantic_search(message, top_k=4)` được gọi

   - Tạo embedding cho câu hỏi
   - Query ChromaDB
   - Trả về top-4 clubs có embedding gần nhất

8. ✅ `build_context_from_clubs()` → Tạo context từ 4 clubs

9. ✅ `generate_answer_from_context()` → Gọi LLM với context

10. ✅ LLM trả về: "Mình gợi ý một vài chi nhánh phù hợp nhất: ..."

11. ✅ Response được trả về cho frontend

**Kết quả**: Sử dụng RAG (semantic search) để tìm clubs phù hợp với ngữ nghĩa của câu hỏi.

---

### Ví Dụ 3: Câu Hỏi Số Lượng

**Input**: "Bạn hiện đang có bao nhiêu chi nhánh vậy?"

**Luồng xử lý**:

1. ✅ `is_club_related_query()` → `True`

2. ✅ `generate_club_response()` được gọi

3. ✅ `is_count_query` → `True` (có "bao nhiêu")

4. ✅ `build_overall_context(clubs)` → Tạo context tổng quan

5. ✅ `generate_answer_from_context()` → Gọi LLM với context tổng quan

6. ✅ LLM trả về: "Hiện tại The New Gym có X chi nhánh đang hoạt động: ..."

7. ✅ Response được trả về cho frontend

**Kết quả**: Không cần exact match hay RAG, chỉ cần thống kê tổng quan.

---

### Ví Dụ 4: Câu Hỏi Không Liên Quan Club

**Input**: "Tôi muốn tăng cơ, nên ăn gì?"

**Luồng xử lý**:

1. ❌ `is_club_related_query()` → `False`

2. ✅ Chuyển sang LLM tổng quát

3. ✅ `load_system_prompt()` → Load `prompt_system.txt`

4. ✅ `get_ai_response(messages, system_prompt)` → Gọi LLM trực tiếp

5. ✅ LLM trả về câu trả lời về dinh dưỡng

6. ✅ Response được trả về cho frontend

**Kết quả**: Không sử dụng RAG, chỉ dùng LLM tổng quát.

---

## Tóm Tắt

### Ưu Tiên Xử Lý Câu Hỏi Club

1. **Câu hỏi số lượng** → Trả về tổng quan ngay (không dùng RAG)
2. **Exact match tên club** → Trả về club đó
3. **Exact match quận/huyện** → Trả về clubs trong quận đó
4. **Exact match thành phố** → Trả về clubs trong thành phố đó
5. **Semantic search (RAG)** → Fallback khi không tìm thấy exact match

### Khi Nào Index Được Rebuild?

- Khi chạy `bash run.sh` (tự động)
- Khi gọi script `python backend/scripts/build_club_index.py` (thủ công)
- Khi `semantic_search()` phát hiện collection không tồn tại (tự động rebuild)

### Lưu Ý

- Index chỉ chứa **active clubs** (`isActive == 1`)
- Cache của `clubs_client` có TTL = 5 phút
- Vector database được lưu persistent trên disk
- Metadata JSON được lưu riêng để tra cứu nhanh
