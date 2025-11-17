## Kiến trúc RAG (The New Gym Chatbot)

```
┌───────────────┐    ┌───────────────────────┐    ┌────────────────────────────┐
│ Người dùng hỏi│ ─▶ │ Bộ định tuyến intent  │ ─▶ │ Pipeline RAG cho chi nhánh │
└───────────────┘    │ (từ khóa + alias      │    │ (chỉ kích hoạt nếu liên    │
                      │  quận/thành phố)      │    │ quan chi nhánh)            │
                      └──────────┬────────────┘    └──────────────┬────────────┘
                                 │                                │
                                 │                                ▼
                                 │                      ┌────────────────────┐
                                 │                      │ Xây context         │
                                 │                      │ - Match chính xác   │
                                 │                      │ - Thống kê city/quận│
                                 │                      │ - Top‑k Chroma      │
                                 │                      └─────────┬──────────┘
                                 │                                │
                                 │                ┌────────────────┴────────────────┐
                                 │                │ Prompt RAG + hướng dẫn hệ thống │
                                 │                └────────────────┬────────────────┘
                                 │                                 │
                                 │                           ┌─────▼─────┐
                                 │                           │ Lớp LLM   │
                                 │                           │ (Ollama / │
                                 │                           │  DeepSeek)│
                                 │                           └─────┬─────┘
                                 │                                 │
         ┌───────────────────────▼────────────────────┐            │
Câu hỏi │ Luồng LLM chung (không dùng context RAG)    │◀──────────┘
khác    │ (dinh dưỡng, Q&A tổng quát)                 │
         └───────────────────────┬────────────────────┘
                                 │
                                 ▼
                          ┌────────────┐
                          │ Phản hồi   │
                          └────────────┘
```

### Thu thập dữ liệu & Vector Store

```
scripts/build_club_index.py
        │ (gọi API lấy các chi nhánh đang hoạt động)
        ▼
┌───────────────────────────────┐
│ utils.clubs_client            │
└──────────────┬───────────────┘
               │ Chuẩn hóa & tạo mô tả
               ▼
┌───────────────────────────────┐
│ rag/club_rag.py               │
│ - FastEmbed MiniLM đa ngôn ngữ│
│ - Vector store Chroma (cosine)│
│ - Cache metadata JSON         │
└───────────────────────────────┘
```

### Luồng trả lời (câu hỏi chi nhánh)

1. `generate_club_response()`:

   - Nếu phát hiện tên/địa phương cụ thể → lấy dữ liệu chính xác.
   - Ngược lại chạy `semantic_search()` để lấy top‑k câu trả lời từ Chroma.

2. `build_context_from_clubs` + `build_counts_context` tạo các khối ngữ cảnh (tối đa 3 chi nhánh + thống kê khu vực).

3. `generate_answer_from_context()`:

   - Prompt hệ thống yêu cầu “chỉ dùng ngữ cảnh, link dạng Markdown, báo không tìm thấy nếu thiếu dữ liệu”.
   - Gọi `get_ai_response()` (Ollama/DeepSeek) để sinh câu trả lời có kiểm chứng.

4. Nếu câu hỏi không liên quan chi nhánh → chuyển sang luồng LLM chung để xử lý dinh dưỡng/Q&A khác.
