# Fitness Nutrition Chatbot

Chatbot tư vấn dinh dưỡng thể hình sử dụng Ollama và Llama 3, hoàn toàn miễn phí và chạy local.

## ✨ Tính năng

- 🤖 **AI Chatbot**: Tư vấn dinh dưỡng bằng tiếng Việt
- 🧮 **Tính toán dinh dưỡng**: BMR, TDEE, macro nutrients
- 📱 **Giao diện web**: React + Tailwind CSS
- 🚀 **Chạy local**: Không cần API key, hoàn toàn miễn phí
- 🎯 **Tùy chỉnh**: Hỗ trợ nhiều mục tiêu (tăng cơ, giảm mỡ, giữ cân)

## 🛠️ Công nghệ

### Backend

- **FastAPI**: Web framework
- **Ollama**: Local AI inference
- **Llama 3:8b**: Language model
- **Python 3.8+**

### Frontend

- **React**: UI framework
- **Tailwind CSS**: Styling
- **Axios**: HTTP client

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

### 6. Cấu hình Environment

```bash
cp env.example .env
# Chỉnh sửa .env nếu cần
```

### 7. Chạy Backend

```bash
python main.py
```

### 8. Cài đặt Frontend

```bash
cd ../frontend
npm install
```

### 9. Chạy Frontend

```bash
npm start
```

## 📖 Sử dụng

1. Mở trình duyệt tại `http://localhost:3000`
2. Chat với bot về dinh dưỡng thể hình
3. Cung cấp thông tin: chiều cao, cân nặng, tuổi, giới tính, mục tiêu, tần suất tập
4. Nhận tư vấn dinh dưỡng và kế hoạch ăn uống

## 🔧 Cấu hình

### Environment Variables

```bash
# AI Provider
AI_PROVIDER=ollama

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### API Endpoints

- `GET /`: Health check
- `GET /ai-status`: Kiểm tra trạng thái AI
- `POST /chat`: Chat với bot
- `POST /user-info`: Cập nhật thông tin user
- `GET /nutrition-plan/{session_id}`: Lấy kế hoạch dinh dưỡng

## 📁 Cấu trúc Project

```
chat-bot/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── requirements.txt     # Python dependencies
│   ├── env.example         # Environment template
│   ├── prompt_system.txt   # AI system prompt
│   └── utils/
│       ├── calculator.py    # Nutrition calculations
│       ├── formatter.py     # Response formatting
│       └── ollama_client.py # Ollama integration
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main React component
│   │   ├── api.js          # API client
│   │   └── components/
│   │       └── ChatBox.jsx # Chat interface
│   ├── package.json        # Node dependencies
│   └── tailwind.config.js  # Tailwind config
├── run.sh                  # Quick start script
└── README.md              # This file
```

## 🎯 Ví dụ sử dụng

### Chat với bot:

```
User: "Xin chào, tôi cao 1m75, nặng 68kg, 25 tuổi, nam, muốn tăng cơ, tập 4 buổi/tuần. Nên ăn gì?"

Bot: "Chào anh! Dựa trên thông tin của anh, tôi sẽ tính toán kế hoạch dinh dưỡng phù hợp..."
```

### API Response:

```json
{
  "response": "Tư vấn dinh dưỡng...",
  "session_id": "user123",
  "nutrition_info": {
    "bmr": 1185.0,
    "tdee": 1836.75,
    "goal_calories": 2020.43,
    "macros": {
      "protein": { "grams": 151.5, "percentage": 30.0 },
      "carb": { "grams": 227.3, "percentage": 45.0 },
      "fat": { "grams": 56.1, "percentage": 25.0 }
    }
  }
}
```

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
