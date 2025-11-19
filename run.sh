#!/bin/bash

echo "🚀 Khởi động Fitness Nutrition Chatbot..."

# Kiểm tra Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama chưa được cài đặt. Vui lòng cài đặt Ollama trước:"
    echo "   macOS: brew install ollama"
    echo "   Linux: curl -fsSL https://ollama.ai/install.sh | sh"
    exit 1
fi

# Kiểm tra model Llama 3
if ! ollama list | grep -q "llama3:8b"; then
    echo "📥 Tải model Llama 3:8b..."
    ollama pull llama3:8b
    if [ $? -ne 0 ]; then
        echo "❌ Lỗi khi tải model. Vui lòng kiểm tra kết nối internet."
        exit 1
    fi
fi

# Khởi động Ollama service
if ! pgrep -x "ollama" > /dev/null; then
    echo "🔄 Khởi động Ollama service..."
    ollama serve &
    OLLAMA_PID=$!
    echo "🦙 Ollama PID: $OLLAMA_PID"
    sleep 5
else
    echo "✅ Ollama service đã chạy."
fi

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 chưa được cài đặt."
    exit 1
fi

# Cài đặt backend dependencies
echo "📦 Cài đặt backend dependencies..."
cd backend

if [ ! -d "venv" ]; then
    echo "🔧 Tạo virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

# Cập nhật semantic index cho clubs
echo "🧠 Cập nhật dữ liệu tìm kiếm (RAG)..."
NEED_FORCE_REBUILD=false
CHROMA_DB_PATH="data/rag/chroma/chroma.sqlite3"

if [ "$FORCE_RAG_REBUILD" = "true" ]; then
    NEED_FORCE_REBUILD=true
elif [ ! -f "$CHROMA_DB_PATH" ]; then
    echo "ℹ️  ChromaDB chưa tồn tại, sẽ build mới."
    NEED_FORCE_REBUILD=true
fi

if [ "$NEED_FORCE_REBUILD" = "true" ]; then
    echo "   → Rebuild toàn bộ RAG index..."
    python scripts/build_club_index.py --force
else
    echo "   → Cập nhật RAG index hiện có..."
    python scripts/build_club_index.py
fi

if [ $? -ne 0 ]; then
    echo "❌ Lỗi khi xây dựng RAG index. Vui lòng kiểm tra kết nối internet và thử lại."
    deactivate
    exit 1
fi

# Kiểm tra .env
if [ ! -f ".env" ]; then
    echo "📝 Tạo file .env từ template..."
    cp env.example .env
fi

# Khởi động backend
echo "🚀 Khởi động backend..."
python main.py &
BACKEND_PID=$!
echo "🔧 Backend PID: $BACKEND_PID"

# Đợi backend khởi động
sleep 3

# Kiểm tra Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js chưa được cài đặt."
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Cài đặt frontend dependencies
echo "📦 Cài đặt frontend dependencies..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "🔧 Cài đặt npm packages..."
    npm install
fi

# Khởi động frontend
echo "🚀 Khởi động frontend..."
npm start &
FRONTEND_PID=$!
echo "🎨 Frontend PID: $FRONTEND_PID"

echo ""
echo "🎉 Chatbot đã khởi động thành công!"
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend: http://localhost:8000"
echo "🦙 Ollama: http://localhost:11434"
echo ""
echo "Để dừng chatbot, nhấn Ctrl+C"

# Chờ user dừng
trap 'echo "🛑 Đang dừng chatbot..."; kill $BACKEND_PID $FRONTEND_PID $OLLAMA_PID 2>/dev/null; exit' INT
wait