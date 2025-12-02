# The New Gym Chatbot - RAG System

Chatbot tư vấn thông tin về chi nhánh và bài tập của The New Gym sử dụng RAG (Retrieval-Augmented Generation) với Ollama và vector search.

## ✨ Tính năng

- 🤖 **AI Chatbot**: Tư vấn thông tin chi nhánh và bài tập bằng tiếng Việt
- 🔍 **Semantic Search**: Tìm kiếm thông minh dựa trên ngữ nghĩa (RAG)
- 📍 **Thông tin chi nhánh**: Tìm kiếm và tư vấn về các chi nhánh The New Gym
- 💪 **Thông tin bài tập**: Tư vấn về các bài tập thể hình
- 🎯 **Query Classification**: Tự động phân loại câu hỏi (clubs, exercises, general)
- 📱 **Giao diện web**: React + Tailwind CSS
- 🚀 **Chạy local**: Không cần API key, hoàn toàn miễn phí với Ollama

## 🛠️ Công nghệ

### Backend

- **FastAPI**: Web framework
- **Ollama**: Local AI inference
- **ChromaDB**: Vector database cho RAG
- **Sentence Transformers**: Vietnamese embedding model (`dangvantuan/vietnamese-embedding`)
- **Python 3.8+**

### Frontend

- **React**: UI framework
- **Tailwind CSS**: Styling
- **Axios**: HTTP client

## 🏗️ Kiến trúc

### Unified RAG System

Hệ thống sử dụng **Unified RAG System** với topic registry, cho phép dễ dàng thêm các topics mới:

```
backend/rag/
├── base_rag.py          # Base class chung cho tất cả topics
├── unified_rag.py       # Unified RAG system với topic registry
├── club_rag.py          # Wrapper cho clubs topic (backward compatibility)
├── exercise_rag.py      # Wrapper cho exercises topic (backward compatibility)
└── topics/
    ├── clubs.py         # Configuration cho clubs topic
    └── exercises.py     # Configuration cho exercises topic
```

### Topics hiện có

1. **Clubs**: Thông tin về các chi nhánh The New Gym
2. **Exercises**: Thông tin về các bài tập thể hình

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

### 3. Tải model Llama 3

```bash
ollama pull llama3:8b
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
# Build index cho clubs và exercises
python scripts/build_club_index.py --force

# Hoặc chỉ build clubs
python scripts/build_club_index.py --force --skip-exercises
```

### 7. Cấu hình Environment

```bash
cp env.example .env
# Chỉnh sửa .env nếu cần
```

### 8. Chạy Backend

```bash
python main.py
```

### 9. Cài đặt Frontend

```bash
cd ../frontend
npm install
```

### 10. Chạy Frontend

```bash
npm start
```

## 📖 Sử dụng

1. Mở trình duyệt tại `http://localhost:3000`
2. Chat với bot về:
   - Thông tin chi nhánh: "Bạn có chi nhánh nào ở Gò Vấp không?"
   - Thông tin bài tập: "Bài tập nào tốt cho ngực?"
   - Câu hỏi chung về The New Gym

## 🔧 Cấu hình

### Environment Variables

```bash
# AI Provider
AI_PROVIDER=ollama  # hoặc deepseek

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b

# DeepSeek Configuration (nếu dùng)
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

# RAG Configuration
EMBED_MODEL=dangvantuan/vietnamese-embedding
CLUB_EMBED_LIMIT=2000
EXERCISE_EMBED_LIMIT=500
CLUB_CONTEXT_LIMIT=4
EXERCISE_CONTEXT_LIMIT=4

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### API Endpoints

- `GET /`: Health check
- `GET /ai-status`: Kiểm tra trạng thái AI
- `POST /chat`: Chat với bot
- `GET /clubs`: Lấy danh sách clubs
- `GET /clubs/active`: Lấy clubs đang hoạt động
- `GET /clubs/search`: Tìm kiếm clubs
- `DELETE /sessions/{session_id}`: Xóa lịch sử hội thoại

## 📁 Cấu trúc Project

```
chat-bot/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── requirements.txt           # Python dependencies
│   ├── env.example               # Environment template
│   ├── prompt_system.txt         # AI system prompt
│   ├── data/
│   │   ├── clubs.md              # Dữ liệu clubs (markdown)
│   │   ├── exercise.md           # Dữ liệu exercises (markdown)
│   │   └── rag/
│   │       ├── chroma/           # ChromaDB storage
│   │       └── hf_cache/         # HuggingFace model cache
│   ├── rag/
│   │   ├── base_rag.py           # Base RAG class
│   │   ├── unified_rag.py        # Unified RAG system
│   │   ├── club_rag.py           # Clubs wrapper
│   │   ├── exercise_rag.py       # Exercises wrapper
│   │   └── topics/
│   │       ├── clubs.py          # Clubs topic config
│   │       └── exercises.py      # Exercises topic config
│   ├── services/
│   │   ├── club_service.py       # Club query handling
│   │   ├── exercise_service.py   # Exercise query handling
│   │   ├── llm_service.py        # LLM integration
│   │   └── conversation_service.py # Conversation history
│   ├── utils/
│   │   ├── query_classifier.py   # Query classification
│   │   ├── clubs_client.py       # Clubs data client
│   │   └── ollama_client.py      # Ollama integration
│   ├── constants/
│   │   └── rag_prompts.py        # RAG prompts
│   └── scripts/
│       └── build_club_index.py   # Build RAG index script
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Main React component
│   │   ├── api.js                # API client
│   │   └── components/
│   │       └── ChatBox.jsx       # Chat interface
│   ├── package.json              # Node dependencies
│   └── tailwind.config.js        # Tailwind config
├── docs/
│   ├── rag_processing_flow.md    # RAG flow documentation
│   └── how_vector_search_works.md # Vector search explanation
├── run.sh                        # Quick start script
└── README.md                     # This file
```

## 🎯 Ví dụ sử dụng

### Chat với bot về chi nhánh:

```
User: "Bạn có chi nhánh nào ở Gò Vấp không?"

Bot: "Mình tìm thấy X chi nhánh ở Gò Vấp:
- [Chi nhánh A](link) - Địa chỉ...
- [Chi nhánh B](link) - Địa chỉ..."
```

### Chat với bot về bài tập:

```
User: "Bài tập nào tốt cho ngực?"

Bot: "Mình gợi ý một số bài tập cho ngực:
- [Bài tập 1] - Nhóm cơ: Ngực, Độ khó: Trung bình
- [Bài tập 2] - Nhóm cơ: Ngực, Độ khó: Dễ..."
```

## 🔍 Query Classification

Hệ thống tự động phân loại câu hỏi bằng semantic search:

1. **Clubs**: Câu hỏi về chi nhánh, địa điểm, khu vực
2. **Exercises**: Câu hỏi về bài tập, nhóm cơ, tập luyện
3. **General**: Câu hỏi chung về The New Gym

## 🚀 Script tự động

Sử dụng `run.sh` để khởi động nhanh:

```bash
chmod +x run.sh
./run.sh
```

## 🔍 Troubleshooting

### Ollama không chạy

```bash
# Kiểm tra Ollama
ollama list

# Khởi động Ollama
ollama serve

# Kiểm tra model
ollama pull llama3:8b
```

### RAG Index chưa được build

```bash
# Build index
cd backend
python scripts/build_club_index.py --force
```

### Backend lỗi

```bash
# Kiểm tra dependencies
pip install -r requirements.txt

# Kiểm tra environment
cat .env
```

### Frontend lỗi

```bash
# Cài đặt lại dependencies
rm -rf node_modules package-lock.json
npm install
```

## 📚 Tài liệu

- [RAG Processing Flow](docs/rag_processing_flow.md): Chi tiết về luồng xử lý RAG
- [How Vector Search Works](docs/how_vector_search_works.md): Giải thích cách vector search hoạt động

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
