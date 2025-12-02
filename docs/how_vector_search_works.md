# Cách Vector Search Hoạt Động - Từ Documents Đến Câu Trả Lời

Tài liệu này giải thích chi tiết cách mà documents và câu hỏi được vectorize và tìm thấy nhau trong hệ thống RAG của The New Gym.

---

## 📋 Tổng Quan

Vector search hoạt động dựa trên nguyên lý: **Văn bản có ngữ nghĩa tương tự sẽ có vector embeddings gần nhau trong không gian vector**.

```
Document: "Chi nhánh: Hoàng Văn Thụ, Địa chỉ: 431A Hoàng Văn Thụ, Tân Bình, Hồ Chí Minh"
    ↓ [Vectorize với Vietnamese Embedding Model]
Vector: [0.123, -0.456, 0.789, ..., 0.234] (384 dimensions)
    ↓ [Lưu vào ChromaDB]
ChromaDB Collection: club_documents

Query: "Bạn có chi nhánh nào ở Tân Bình không?"
    ↓ [Vectorize với cùng model]
Vector: [0.125, -0.458, 0.791, ..., 0.236] (384 dimensions)
    ↓ [Tìm kiếm bằng Cosine Similarity]
Tìm thấy Document trên vì vectors gần nhau!
```

---

## 🔄 Quy Trình Hoàn Chỉnh

### Bước 1: Vectorize Documents (Ingest Phase)

**File**: `rag/base_rag.py` → `BaseRAG.build_index()`

#### 1.1. Xây dựng Text Chunks

**Clubs** (`rag/topics/clubs.py` → `ClubsTextBuilder`):

```python
# Ví dụ: Club data
club = {
    "nameVi": "Hoàng Văn Thụ",
    "address": "431A Hoàng Văn Thụ, Tân Bình, Hồ Chí Minh",
    "city": {"cityName": "Hồ Chí Minh"},
    "district": {"districtName": "Tân Bình"}
}

# Chuyển thành text chunk
text = """
Chi nhánh: Hoàng Văn Thụ
Địa chỉ: 431A Hoàng Văn Thụ, Tân Bình, Hồ Chí Minh
Khu vực: Tân Bình, Hồ Chí Minh
Trang web: https://thenewgym.vn/hoang-van-thu/
Trạng thái: Đang hoạt động
"""
```

**Exercises** (`rag/topics/exercises.py` → `ExercisesTextBuilder`):

```python
# Ví dụ: Exercise data
exercise = {
    "nameVi": "Hít đất",
    "nameEn": "Push-up",
    "muscleGroup": "Ngực",
    "difficulty": "Dễ",
    "calories": "50-100 kcal"
}

# Chuyển thành text chunk
text = """
Bài tập: Hít đất
Tên tiếng Anh: Push-up
Nhóm cơ: Ngực
Độ khó: Dễ
Kcal tiêu thụ: 50-100 kcal
"""
```

#### 1.2. Tokenize (Tiếng Việt)

**File**: `rag/base_rag.py` → `VietnameseEmbeddingFunction._tokenize_texts()`

```python
from pyvi.ViTokenizer import tokenize

# Tokenize text tiếng Việt
tokenized = tokenize(text)
# Kết quả: "Chi nhánh : Hoàng_Văn_Thụ Địa_chỉ : 431A Hoàng_Văn_Thụ , Tân_Bình , Hồ_Chí_Minh ..."
```

**Tại sao cần tokenize?**

- Tiếng Việt không có khoảng trắng giữa các từ
- Tokenize giúp model hiểu đúng cấu trúc từ
- Ví dụ: "Hoàng Văn Thụ" → "Hoàng_Văn_Thụ" (một từ ghép)

#### 1.3. Tạo Embeddings

**File**: `rag/base_rag.py` → `VietnameseEmbeddingFunction._embed()`

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("dangvantuan/vietnamese-embedding")
embeddings = model.encode(tokenized_texts, convert_to_numpy=True)
# Kết quả: numpy array shape (n_documents, 384)
# Ví dụ: [[0.123, -0.456, 0.789, ..., 0.234], ...]
```

**Model**: `dangvantuan/vietnamese-embedding`

- Input: Text đã tokenize
- Output: Vector 384 dimensions
- Mỗi dimension là một số thực (float)
- Vector này đại diện cho **ngữ nghĩa** của text
- Được train đặc biệt cho tiếng Việt

**Ví dụ vector của document:**

```
Document: "Chi nhánh: Hoàng Văn Thụ, Địa chỉ: 431A Hoàng Văn Thụ, Tân Bình, Hồ Chí Minh"
Vector: [0.123, -0.456, 0.789, 0.234, -0.567, ..., 0.890] (384 số)
```

#### 1.4. Lưu Vào ChromaDB

**File**: `rag/base_rag.py` → `BaseRAG.build_index()`

```python
collection.add(
    ids=["hoang_van_thu"],
    documents=[text_chunk],
    metadatas=[{"name": "Hoàng Văn Thụ", "city": "Hồ Chí Minh", ...}],
    # ChromaDB tự động lưu embeddings vào
)
```

**ChromaDB làm gì?**

1. Nhận embeddings từ `embed_documents()`
2. Lưu embeddings vào vector database (SQLite)
3. Tạo index (HNSW - Hierarchical Navigable Small World) để tìm kiếm nhanh
4. Lưu metadata và document text

**Cấu trúc trong ChromaDB:**

```
Collection: club_documents (hoặc exercise_documents)
├── ID: "hoang_van_thu"
├── Document: "Chi nhánh: Hoàng Văn Thụ..."
├── Metadata: {"name": "Hoàng Văn Thụ", ...}
└── Embedding: [0.123, -0.456, ..., 0.890] (384 dims)
```

---

### Bước 2: Vectorize Query (Serving Phase)

**File**: `rag/base_rag.py` → `BaseRAG.semantic_search()`

#### 2.1. Nhận Câu Hỏi

```python
query = "Bạn có chi nhánh nào ở Tân Bình không?"
```

#### 2.2. Tokenize Query

**File**: `rag/base_rag.py` → `VietnameseEmbeddingFunction.embed_query()`

```python
# Cùng hàm tokenize như documents
tokenized_query = tokenize(query)
# Kết quả: "Bạn có chi_nhánh nào ở Tân_Bình không ?"
```

#### 2.3. Tạo Embedding Cho Query

```python
# Cùng model, cùng cách encode
query_embedding = model.encode([tokenized_query], convert_to_numpy=True)
# Kết quả: [[0.125, -0.458, 0.791, ..., 0.236]] (1 query, 384 dims)
```

**Ví dụ vector của query:**

```
Query: "Bạn có chi nhánh nào ở Tân Bình không?"
Vector: [0.125, -0.458, 0.791, 0.238, -0.569, ..., 0.892] (384 số)
```

**Quan trọng**: Query và Documents dùng **cùng một model** để vectorize!

---

### Bước 3: Tìm Kiếm (Similarity Search)

**File**: `rag/base_rag.py` → `BaseRAG.semantic_search()`

#### 3.1. ChromaDB Query

```python
collection.query(
    query_texts=[query],  # ChromaDB sẽ tự động gọi embed_query()
    n_results=top_k       # Lấy top 5 kết quả gần nhất
)
```

**ChromaDB làm gì bên trong:**

1. Gọi `embed_query(query)` để vectorize query
2. So sánh query vector với tất cả document vectors
3. Tính **Cosine Similarity** (hoặc distance)
4. Trả về top-k documents có similarity cao nhất

#### 3.2. Cosine Similarity

**Công thức:**

```
similarity = cos(θ) = (A · B) / (||A|| × ||B||)

Trong đó:
- A = query vector
- B = document vector
- · = dot product
- ||A|| = magnitude (độ dài) của vector A
```

**Ví dụ:**

```
Query vector:    [0.125, -0.458, 0.791, ...]
Document vector: [0.123, -0.456, 0.789, ...]

Cosine Similarity ≈ 0.98 (rất gần!)
Distance = 1 - similarity ≈ 0.02 (rất nhỏ = rất giống)
```

**Tại sao Cosine Similarity?**

- Không phụ thuộc vào độ dài văn bản
- Chỉ so sánh **hướng** của vectors (ngữ nghĩa)
- Văn bản dài hay ngắn đều được xử lý công bằng

#### 3.3. Kết Quả

```python
results = {
    "ids": [["hoang_van_thu", "dien_bien_phu", ...]],
    "documents": [["Chi nhánh: Hoàng Văn Thụ...", ...]],
    "metadatas": [[{"name": "Hoàng Văn Thụ", ...}, ...]],
    "distances": [[0.02, 0.15, 0.23, ...]]  # Distance càng nhỏ càng giống
}
```

**Distance scores:**

- `0.02` → Rất giống (Tân Bình trong query, Tân Bình trong document)
- `0.15` → Khá giống (cùng thành phố Hồ Chí Minh)
- `0.23` → Ít giống hơn (khác khu vực)

---

## 🔑 Điểm Quan Trọng

### 1. Cùng Model, Cùng Không Gian Vector

```
Documents: Model A → Vector Space A
Query:     Model A → Vector Space A
           ✅ Cùng không gian → Có thể so sánh!

Documents: Model A → Vector Space A
Query:     Model B → Vector Space B
           ❌ Khác không gian → Không thể so sánh!
```

**Trong code:**

- Documents: `VietnameseEmbeddingFunction.embed_documents()`
- Query: `VietnameseEmbeddingFunction.embed_query()`
- **Cùng model**: `SentenceTransformer("dangvantuan/vietnamese-embedding")`

### 2. Tokenization Nhất Quán

```
Document: tokenize("Hoàng Văn Thụ") → "Hoàng_Văn_Thụ"
Query:    tokenize("Hoàng Văn Thụ") → "Hoàng_Văn_Thụ"
          ✅ Cùng tokenization → Vectors giống nhau!
```

### 3. Embeddings Capture Semantics

**Ví dụ:**

```
Document: "Chi nhánh ở Tân Bình"
Query:    "Có club nào ở quận Tân Bình không?"

Mặc dù từ ngữ khác nhau:
- "Chi nhánh" vs "club"
- "Tân Bình" vs "quận Tân Bình"

Nhưng embeddings sẽ gần nhau vì:
- Cùng ngữ nghĩa (địa điểm, tên quận)
- Model đã học được từ training data
```

### 4. Vector Dimensions

**384 dimensions** có nghĩa là:

- Mỗi vector là một điểm trong không gian 384 chiều
- Mỗi dimension capture một khía cạnh ngữ nghĩa
- Ví dụ:
  - Dimension 0: Có thể liên quan đến "địa điểm"
  - Dimension 1: Có thể liên quan đến "tên riêng"
  - Dimension 2: Có thể liên quan đến "hoạt động"
  - ...

**Tại sao 384?**

- Model `dangvantuan/vietnamese-embedding` được train với 384 dims
- Đủ để capture ngữ nghĩa phức tạp
- Không quá lớn để tính toán nhanh

---

## 📊 Ví Dụ Cụ Thể

### Scenario: Tìm Chi Nhánh Ở Tân Bình

#### Step 1: Document Vectorization

```python
# Document 1
text1 = "Chi nhánh: Hoàng Văn Thụ\nĐịa chỉ: 431A Hoàng Văn Thụ, Tân Bình, Hồ Chí Minh"
vector1 = model.encode([tokenize(text1)])[0]
# vector1 = [0.123, -0.456, 0.789, ..., 0.234]

# Document 2
text2 = "Chi nhánh: Điện Biên Phủ\nĐịa chỉ: 256 Điện Biên Phủ, Quận 3, Hồ Chí Minh"
vector2 = model.encode([tokenize(text2)])[0]
# vector2 = [0.145, -0.432, 0.801, ..., 0.198]
```

#### Step 2: Query Vectorization

```python
query = "Bạn có chi nhánh nào ở Tân Bình không?"
query_vector = model.encode([tokenize(query)])[0]
# query_vector = [0.125, -0.458, 0.791, ..., 0.236]
```

#### Step 3: Similarity Calculation

```python
# Cosine similarity giữa query và document 1
similarity1 = cosine_similarity(query_vector, vector1)
# similarity1 ≈ 0.98 (rất cao vì có "Tân Bình")

# Cosine similarity giữa query và document 2
similarity2 = cosine_similarity(query_vector, vector2)
# similarity2 ≈ 0.65 (thấp hơn vì "Quận 3" khác "Tân Bình")
```

#### Step 4: Ranking

```python
results = [
    {"document": text1, "score": 0.98, "rank": 1},  # ✅ Match tốt nhất
    {"document": text2, "score": 0.65, "rank": 2},  # ❌ Không match
]
```

---

## 🎯 Tại Sao Nó Hoạt Động?

### 1. Pre-trained Model

Model `dangvantuan/vietnamese-embedding` đã được train trên:

- Hàng triệu câu văn tiếng Việt
- Học được mối quan hệ ngữ nghĩa
- Ví dụ: "Tân Bình" và "quận Tân Bình" → vectors gần nhau

### 2. Same Embedding Space

```
Tất cả documents và queries đều được map vào cùng một không gian vector
→ Có thể so sánh trực tiếp bằng cosine similarity
```

### 3. Semantic Understanding

```
Không chỉ match từ khóa, mà còn hiểu ngữ nghĩa:

"Chi nhánh ở Tân Bình" ≈ "Club tại quận Tân Bình"
"Bài tập cho ngực" ≈ "Exercise cho chest"
```

---

## 🔧 Code Flow Tóm Tắt

```python
# 1. BUILD INDEX (một lần)
documents = ["Chi nhánh: Hoàng Văn Thụ...", ...]
embeddings = model.encode(tokenize(documents))  # Vectorize documents
collection.add(documents=documents, embeddings=embeddings)  # Lưu vào DB

# 2. QUERY (mỗi lần user hỏi)
query = "Bạn có chi nhánh nào ở Tân Bình không?"
query_embedding = model.encode([tokenize(query)])  # Vectorize query
results = collection.query(query_embeddings=query_embedding)  # Tìm kiếm

# 3. ChromaDB tự động:
#    - Tính cosine similarity giữa query_embedding và tất cả document embeddings
#    - Sắp xếp theo similarity (cao → thấp)
#    - Trả về top-k documents
```

---

## 💡 Lưu Ý Quan Trọng

1. **Cùng Model**: Documents và queries PHẢI dùng cùng một embedding model
2. **Cùng Tokenization**: Tokenize nhất quán để vectors có ý nghĩa
3. **Normalization**: ChromaDB tự động normalize vectors cho cosine similarity
4. **Index**: ChromaDB dùng HNSW index để tìm kiếm nhanh (không phải brute force)
5. **Vietnamese Support**: Model `dangvantuan/vietnamese-embedding` được train đặc biệt cho tiếng Việt

---

## 📚 Tài Liệu Tham Khảo

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [Cosine Similarity](https://en.wikipedia.org/wiki/Cosine_similarity)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)
- [Vietnamese Embedding Model](https://huggingface.co/dangvantuan/vietnamese-embedding)
