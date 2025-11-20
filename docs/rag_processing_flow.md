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

1. **Ingest Pipeline**: Xây dựng và cập nhật vector database từ file Markdown
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

Giai đoạn này được thực hiện **offline** để xây dựng vector database từ file Markdown `clubs.md`. Index được xây dựng lại khi chạy `run.sh` với `FORCE_RAG_REBUILD=true` hoặc khi file ChromaDB chưa tồn tại. Mặc định, hệ thống sẽ cập nhật index hiện có (incremental update).

### Trình Tự Thực Hiện

#### Bước 1: Khởi Tạo Môi Trường

**File**: `backend/rag/club_rag.py`

```python
# Thiết lập các biến môi trường
- HF_HUB_ENABLE_HF_XET = "0"
- HF_HUB_ENABLE_XET = "0"
- HF_HUB_ENABLE_HF_TRANSFER = "0"
- HF_HUB_DISABLE_TELEMETRY = "1"
- HF_HOME = DATA_DIR / "hf_cache"
```

**Mục đích**:

- Tắt các tính năng không cần thiết của HuggingFace Hub
- Đặt thư mục cache để tránh lỗi permission trên macOS

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
- Client này sẽ lưu trữ vector database trên disk (SQLite)
- Nếu collection đã tồn tại và `force_refresh=False`, sẽ sử dụng collection hiện có

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

#### Bước 5: Đọc Dữ Liệu Từ File Markdown

**File**: `backend/rag/club_rag.py` → `build_club_index()` → `_parse_clubs_from_markdown()`

**Nguồn dữ liệu**: `backend/data/clubs.md`

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

1. Đọc toàn bộ nội dung file `clubs.md`
2. Sử dụng regex pattern để tách từng section club:
   ```python
   pattern = r"## CLB (\d+) — (.+?) \(([A-Z0-9]+)\)\n(.*?)(?=\n## CLB|\Z)"
   ```
3. Parse từng field từ nội dung:
   - Tên tiếng Việt, tên tiếng Anh
   - Địa chỉ (được dùng để parse thành phố/quận)
   - Ngày mở (convert từ DD/MM/YYYY sang ISO format)
   - Trạng thái hoạt động (có/không → 1/0)
   - Website, tọa độ
4. Parse thành phố và quận từ địa chỉ:
   - Format: "địa chỉ, quận/huyện, thành phố, Việt Nam"
   - Tự động extract `cityName` và `districtName`

**Kết quả**: Danh sách các club objects với cấu trúc JSON

#### Bước 6: Lọc Clubs Đang Hoạt Động

**File**: `backend/rag/club_rag.py` → `build_club_index()`

```python
clubs = [c for c in clubs if c.get("isActive") == 1][:MAX_CLUBS_TO_EMBED]
```

- Chỉ lấy các club có `isActive == 1`
- Giới hạn tối đa `MAX_CLUBS_TO_EMBED` (mặc định: 2000)

#### Bước 7: Xây Dựng Text Chunks

**File**: `backend/rag/club_rag.py` → `_build_text_from_club()`

Với mỗi club, tạo một text chunk chứa:

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

**Ví dụ**:

```
Chi nhánh: Hoàng Văn Thụ
Địa chỉ: 431A Hoàng Văn Thụ, Phường 4, Tân Bình, Hồ Chí Minh, Việt Nam
Khu vực: Tân Bình, Hồ Chí Minh
Trang web: https://thenewgym.vn/hoang-van-thu/
Trạng thái: Đang hoạt động
```

#### Bước 8: Tạo Embeddings

**File**: `backend/rag/club_rag.py` → `FastEmbedFunction`

Với mỗi text chunk:

1. Gọi `_embedding_model.embed([text])`
2. Nhận về vector 384 dimensions (List[List[float]])
3. Vector này đại diện cho ngữ nghĩa của text chunk

**FastEmbedFunction** là adapter để tuân thủ ChromaDB embedding function API:

- `embed_documents()`: Embed nhiều documents
- `embed_query()`: Embed một query string

#### Bước 9: Lưu Vào ChromaDB

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
  "raw": "{toàn bộ JSON của club, serialized}"
}
```

**Collection Name**: `club_documents`
**Distance Metric**: Cosine similarity (`hnsw:space: cosine`)

**Lưu ý về force_refresh**:

- Nếu `force_refresh=True`: Xóa collection cũ và tạo mới hoàn toàn
- Nếu `force_refresh=False`: Cập nhật collection hiện có (thêm documents mới, không xóa cũ)

### Kết Quả

Sau khi hoàn thành ingest pipeline:

- ✅ Vector database được lưu trong `backend/data/rag/chroma/` (SQLite)
- ✅ Sẵn sàng cho giai đoạn serving
- ✅ Mỗi lần chạy `run.sh`, hệ thống sẽ kiểm tra:
  - Nếu `FORCE_RAG_REBUILD=true` → Rebuild toàn bộ
  - Nếu file `data/rag/chroma/chroma.sqlite3` chưa tồn tại → Rebuild toàn bộ
  - Ngược lại → Cập nhật incremental

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

```python
def is_club_related_query(_: str) -> bool:
    """Dự án chỉ phục vụ thông tin chi nhánh → mọi câu đều xử lý bằng RAG."""
    return True
```

**Lưu ý**: Hiện tại, dự án chỉ tập trung vào thông tin chi nhánh, nên mọi câu hỏi đều được xử lý bằng RAG pipeline.

**Kết quả**:

- ✅ `is_club_query = True` → Chuyển sang xử lý club
- ❌ `is_club_query = False` → Chuyển sang LLM tổng quát (hiếm khi xảy ra)

#### Bước 3: Xử Lý Câu Hỏi Club

**File**: `backend/services/club_service.py` → `generate_club_response()`

##### 3.1. Chuẩn Bị Dữ Liệu

```python
clubs = clubs_client.get_active_clubs()
```

- Lấy danh sách clubs đang hoạt động từ API (có cache 5 phút)
- Nếu không có dữ liệu → Trả về thông báo lỗi

##### 3.2. Tìm Kiếm Theo Keyword (Bước Đầu Tiên)

**File**: `backend/services/club_service.py` → `search_clubs_by_keyword()`

**Logic**:

1. Chuyển message về lowercase
2. Duyệt qua từng club và kiểm tra các field:
   - `nameVi`, `nameEn`
   - `location`, `address`
   - `district.districtName`
   - `city.cityName`
3. Nếu bất kỳ field nào chứa từ khóa trong message (hoặc ngược lại) → Thêm vào kết quả

**Ví dụ**:

- Message: "Gò Vấp" → Tìm thấy clubs có "Gò Vấp" trong `district.districtName` hoặc `address`
- Message: "Hoàng Văn Thụ" → Tìm thấy club có tên "Hoàng Văn Thụ"

**Nếu tìm thấy keyword matches**:

1. Xây dựng context từ các clubs tìm được
2. Thêm thống kê số lượng clubs trong khu vực
3. Gọi LLM với context và trả về kết quả

##### 3.3. Semantic Search (RAG) - Nếu Không Có Keyword Match

**Chỉ chạy khi**: Không tìm thấy kết quả từ keyword search

**File**: `backend/rag/club_rag.py` → `semantic_search()`

```python
semantic_results = semantic_search(message, top_k=MAX_CONTEXT_CLUBS)
```

**Trình tự**:

1. Lấy collection từ ChromaDB (`_get_collection()`)
2. Nếu collection không tồn tại → Tự động rebuild index
3. Tạo embedding cho câu hỏi của người dùng:
   ```python
   query_embedding = _embedding_model.embed([query])
   ```
4. Query ChromaDB với `collection.query(query_texts=[query], n_results=top_k)`
5. ChromaDB trả về top-k documents có embedding gần nhất (cosine similarity)
6. Parse kết quả và trả về danh sách clubs với:
   - `id`: ID của document
   - `score`: Distance score (càng nhỏ càng giống)
   - `document`: Text chunk gốc
   - `raw`: Raw club data (JSON)

**Ví dụ**:

- Câu hỏi: "chi nhánh gym có hồ bơi ở khu trung tâm"
- Semantic search tìm các club có mô tả/địa chỉ liên quan đến "hồ bơi", "trung tâm" dựa trên ngữ nghĩa

**Nếu tìm thấy semantic results**:

1. Extract raw club data từ kết quả
2. Xây dựng context từ các clubs
3. Gọi LLM với context và trả về kết quả

##### 3.4. Fallback: Overall Context + No Data Message

**Chỉ chạy khi**: Không tìm thấy kết quả từ cả keyword search và semantic search

**File**: `backend/services/club_service.py` → `build_overall_context()` + `build_no_data_message()`

1. **Overall Context**: Thống kê tổng quan số chi nhánh theo thành phố
2. **No Data Message**: Thông báo không tìm thấy + gợi ý 3 chi nhánh khác

**Format no data message**:

```
Mình chưa tìm thấy chi nhánh nào ở {khu vực}.
Bạn có thể tham khảo một số chi nhánh đang hoạt động gần khu vực khác:
- [Tên Club](URL) – Địa chỉ
- ...
```

##### 3.5. Xây Dựng Context

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
Địa chỉ: 431A Hoàng Văn Thụ, Phường 4, Tân Bình, Hồ Chí Minh, Việt Nam
Quận/Huyện: Tân Bình
Thành phố: Hồ Chí Minh
Link: https://thenewgym.vn/hoang-van-thu/

[Đoạn 2] Tên: Nguyễn Chí Thanh
...
```

Nếu có nhiều clubs (từ keyword search), thêm context thống kê:

**File**: `backend/services/club_service.py` → `build_counts_context()`

```
Tổng quan khu vực {label}:
- Chi nhánh đang hoạt động: {count}
```

##### 3.6. Tạo Câu Trả Lời Từ Context

**File**: `backend/services/club_service.py` → `generate_answer_from_context()`

**Prompt được xây dựng**:

```
Ngữ cảnh:
[Đoạn 1] Tên: Hoàng Văn Thụ
...

Hướng dẫn:
- QUAN TRỌNG: BẠN PHẢI TUYỆT ĐỐI CHỈ sử dụng thông tin trong các đoạn ngữ cảnh bên trên.
- TUYỆT ĐỐI KHÔNG được tự tạo, bịa đặt, hoặc suy đoán thông tin về chi nhánh, địa chỉ, tên, hoặc bất kỳ thông tin nào khác.
- Nếu ngữ cảnh không chứa thông tin về chi nhánh được hỏi, bạn PHẢI nói rõ 'Mình chưa tìm thấy chi nhánh nào ở [khu vực]' và KHÔNG được liệt kê các chi nhánh không có trong ngữ cảnh.
- Liệt kê tối đa 3 chi nhánh phù hợp nhất, mỗi chi nhánh gồm tên, địa chỉ, link (nếu có) - CHỈ khi thông tin này có trong ngữ cảnh.
- Dùng Markdown để hiển thị link dạng [Tên](URL).
- Nếu chỉ có 1 chi nhánh phù hợp thì CHỈ nêu chi nhánh đó, KHÔNG thêm câu như 'không có chi nhánh nào khác'.
- Giữ giọng điệu mềm mại, gần gũi, dùng đại từ 'mình'/'bạn', tránh nhắc lặp lại cùng một câu.

Câu hỏi của khách: {message}

LƯU Ý CUỐI CÙNG: Nếu câu hỏi về một khu vực cụ thể (ví dụ: Thủ Đức, Quận X) nhưng trong ngữ cảnh không có chi nhánh nào ở khu vực đó, bạn PHẢI trả lời 'Mình chưa tìm thấy chi nhánh nào ở [khu vực đó]' và KHÔNG được liệt kê các chi nhánh ở khu vực khác như thể chúng ở khu vực được hỏi.
```

**System Prompt** (`RAG_SYSTEM_PROMPT`):

```
Bạn là AI Assistant của The New Gym với phong cách trò chuyện tự nhiên, thân thiện, giống như một tư vấn viên đang nói chuyện trực tiếp với khách.
QUAN TRỌNG: BẠN PHẢI TUYỆT ĐỐI CHỈ sử dụng thông tin trong ngữ cảnh được cung cấp.
TUYỆT ĐỐI KHÔNG được tự tạo, bịa đặt, hoặc suy đoán thông tin về chi nhánh, địa chỉ, tên, hoặc bất kỳ thông tin nào khác.
Nếu ngữ cảnh không chứa thông tin về chi nhánh được hỏi, bạn PHẢI nói rõ 'Mình chưa tìm thấy chi nhánh nào ở [khu vực]' và KHÔNG được liệt kê các chi nhánh không có trong ngữ cảnh.
Luôn trả lời bằng tiếng Việt, dùng đại từ thân mật (ví dụ: 'mình', 'bạn'), câu văn mềm mại, ngắn gọn, hạn chế lặp lại.
Mỗi chi nhánh nên bao gồm tên (ưu tiên tiếng Việt), địa chỉ và link ở dạng [Tên](URL) - CHỈ khi thông tin này có trong ngữ cảnh.
```

##### 3.7. Gọi LLM

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

##### 3.8. Trả Về Response

**File**: `backend/main.py` → `@app.post("/chat")`

```python
return ChatResponse(
    response=club_response_text,  # Từ LLM
    session_id=session_id
)
```

#### Bước 4: Xử Lý Câu Hỏi Không Liên Quan Club

Nếu `is_club_query = False` (hiếm khi xảy ra):

**File**: `backend/main.py` → `@app.post("/chat")`

```python
# Load system prompt tổng quát
system_prompt = load_system_prompt()  # Từ prompt_system.txt

# Gọi LLM trực tiếp (không có context)
ai_response = get_ai_response(messages, system_prompt)
```

**System Prompt**: Từ `backend/prompt_system.txt`

- Hướng dẫn AI về thông tin chung về The New Gym

---

## Chi Tiết Các Thành Phần

### 1. ClubsClient (`backend/utils/clubs_client.py`)

**Vai trò**: Client để lấy dữ liệu từ API (dùng cho serving, không dùng cho ingest)

**Tính năng**:

- Cache dữ liệu (TTL = 5 phút)
- Lấy tất cả clubs hoặc chỉ active clubs
- Tìm kiếm theo từ khóa

**Methods chính**:

- `fetch_clubs()`: Lấy tất cả clubs từ API
- `get_active_clubs()`: Lấy chỉ clubs đang hoạt động
- `search_clubs()`: Tìm kiếm theo từ khóa

### 2. ClubService (`backend/services/club_service.py`)

**Vai trò**: Xử lý logic liên quan đến club queries

**Tính năng**:

- Phát hiện intent club-related (hiện tại luôn trả về `True`)
- Tìm kiếm keyword-based
- Xây dựng context từ clubs
- Tạo câu trả lời từ context

**Functions chính**:

- `is_club_related_query()`: Phát hiện câu hỏi về club (luôn `True`)
- `search_clubs_by_keyword()`: Tìm kiếm clubs theo từ khóa trực tiếp
- `generate_club_response()`: Tạo câu trả lời cho câu hỏi về club
- `generate_answer_from_context()`: Gọi LLM với context
- `build_context_from_clubs()`: Xây dựng context từ danh sách clubs
- `build_no_data_message()`: Tạo thông báo không tìm thấy + gợi ý

### 3. ClubRAG (`backend/rag/club_rag.py`)

**Vai trò**: Quản lý vector database và semantic search

**Tính năng**:

- Parse dữ liệu từ file Markdown
- Xây dựng index từ clubs (ingest)
- Semantic search với embeddings
- Quản lý ChromaDB collection

**Functions chính**:

- `_parse_clubs_from_markdown()`: Parse clubs từ file Markdown
- `_build_text_from_club()`: Xây dựng text chunk từ club data
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

### Ví Dụ 1: Câu Hỏi Về Quận Cụ Thể (Keyword Match)

**Input**: "Bạn có chi nhánh nào ở Gò Vấp không?"

**Luồng xử lý**:

1. ✅ `is_club_related_query()` → `True`

2. ✅ `generate_club_response()` được gọi

3. ✅ `search_clubs_by_keyword("Bạn có chi nhánh nào ở Gò Vấp không?", clubs)` → Tìm thấy clubs có "Gò Vấp" trong `district.districtName` hoặc `address`

4. ✅ `build_context_from_clubs()` → Tạo context cho các clubs tìm được

5. ✅ `build_counts_context("Gò Vấp", keyword_matches)` → Thêm thống kê

6. ✅ `generate_answer_from_context()` → Gọi LLM với context

7. ✅ LLM trả về: "Mình tìm thấy X chi nhánh ở Gò Vấp: ..."

8. ✅ Response được trả về cho frontend

**Kết quả**: Không cần dùng RAG (semantic search) vì đã tìm thấy bằng keyword search.

---

### Ví Dụ 2: Câu Hỏi Semantic (Cần RAG)

**Input**: "Chi nhánh gym có hồ bơi ở khu trung tâm"

**Luồng xử lý**:

1. ✅ `is_club_related_query()` → `True`

2. ✅ `generate_club_response()` được gọi

3. ❌ `search_clubs_by_keyword()` → Không tìm thấy keyword match trực tiếp

4. ✅ `semantic_search(message, top_k=4)` được gọi

   - Tạo embedding cho câu hỏi
   - Query ChromaDB
   - Trả về top-4 clubs có embedding gần nhất

5. ✅ `build_context_from_clubs()` → Tạo context từ 4 clubs

6. ✅ `generate_answer_from_context()` → Gọi LLM với context

7. ✅ LLM trả về: "Mình gợi ý một vài chi nhánh phù hợp nhất: ..."

8. ✅ Response được trả về cho frontend

**Kết quả**: Sử dụng RAG (semantic search) để tìm clubs phù hợp với ngữ nghĩa của câu hỏi.

---

### Ví Dụ 3: Câu Hỏi Không Tìm Thấy Kết Quả

**Input**: "Bạn có chi nhánh nào ở Thủ Đức không?"

**Luồng xử lý**:

1. ✅ `is_club_related_query()` → `True`

2. ✅ `generate_club_response()` được gọi

3. ❌ `search_clubs_by_keyword()` → Không tìm thấy

4. ❌ `semantic_search()` → Không tìm thấy clubs ở Thủ Đức

5. ✅ `build_overall_context()` → Tạo context tổng quan

6. ✅ `build_no_data_message("Thủ Đức", "city", clubs)` → Tạo thông báo không tìm thấy + gợi ý 3 chi nhánh khác

7. ✅ `generate_answer_from_context()` → Gọi LLM với context tổng quan + no data message

8. ✅ LLM trả về: "Mình chưa tìm thấy chi nhánh nào ở Thủ Đức. Bạn có thể tham khảo một số chi nhánh đang hoạt động gần khu vực khác: ..."

9. ✅ Response được trả về cho frontend

**Kết quả**: Trả về thông báo không tìm thấy kèm gợi ý các chi nhánh khác.

---

### Ví Dụ 4: Câu Hỏi Không Liên Quan Club (Hiếm)

**Input**: "Tôi muốn biết về dịch vụ của The New Gym"

**Luồng xử lý**:

1. ❌ `is_club_related_query()` → `False` (hiếm khi xảy ra)

2. ✅ Chuyển sang LLM tổng quát

3. ✅ `load_system_prompt()` → Load `prompt_system.txt`

4. ✅ `get_ai_response(messages, system_prompt)` → Gọi LLM trực tiếp

5. ✅ LLM trả về câu trả lời về dịch vụ

6. ✅ Response được trả về cho frontend

**Kết quả**: Không sử dụng RAG, chỉ dùng LLM tổng quát.

---

## Tóm Tắt

### Ưu Tiên Xử Lý Câu Hỏi Club

1. **Keyword search** → Tìm kiếm trực tiếp theo từ khóa trong các field của club
2. **Semantic search (RAG)** → Fallback khi không tìm thấy keyword match
3. **Fallback: Overall context + No data message** → Khi không tìm thấy gì, trả về thông báo + gợi ý

### Khi Nào Index Được Rebuild?

- **Force rebuild**: Khi chạy `bash run.sh` với `FORCE_RAG_REBUILD=true` hoặc chạy `python backend/scripts/build_club_index.py --force`
- **Incremental update**: Khi chạy `bash run.sh` bình thường (nếu DB đã tồn tại)
- **Auto rebuild**: Khi `semantic_search()` phát hiện collection không tồn tại (tự động rebuild)

### Lưu Ý

- Index chỉ chứa **active clubs** (`isActive == 1`)
- Dữ liệu nguồn: File Markdown `backend/data/clubs.md` (không phải API)
- Vector database được lưu persistent trên disk (SQLite)
- Metadata được lưu trong ChromaDB (không còn file JSON riêng)
- ChromaDB sẽ không tạo folder mới mỗi lần chạy nếu dùng incremental update
