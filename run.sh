#!/bin/bash

# LƯU Ý: Script này dành cho FastAPI server + React frontend (đã deprecated)
# Khuyến nghị: Sử dụng run_streamlit.sh để chạy Streamlit app (đơn giản hơn)
# 
# Script này vẫn hoạt động nếu bạn muốn chạy FastAPI server riêng,
# nhưng frontend React đã được xóa. Chỉ dùng script này nếu bạn cần API server.

echo "🚀 Khởi động Fitness Nutrition Chatbot (FastAPI + React - DEPRECATED)..."

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
# Kiểm tra cross-platform: pgrep hoạt động trên cả macOS và Linux
if ! pgrep -x "ollama" > /dev/null 2>&1; then
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
# Lưu thư mục gốc để quay lại sau (tương thích với cả macOS và Linux)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "🔧 Tạo virtual environment..."
    python3 -m venv venv
fi

# Sử dụng đường dẫn tuyệt đối đến python và pip trong venv
# Tương thích với cả macOS và Linux (cả hai đều dùng venv/bin/)
BACKEND_DIR="$(pwd)"
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"
VENV_PIP="$BACKEND_DIR/venv/bin/pip"

# Kiểm tra venv đã được tạo đúng chưa
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment chưa được tạo đúng cách."
    exit 1
fi

echo "🔧 Kích hoạt virtual environment..."
source venv/bin/activate

# Upgrade pip trước khi cài đặt dependencies (tránh lỗi resolver)
echo "⬆️  Nâng cấp pip..."
$VENV_PIP install --upgrade pip setuptools wheel

# Cài đặt dependencies
echo "📥 Cài đặt Python packages..."
if ! $VENV_PIP install -r requirements.txt; then
    echo "❌ Lỗi khi cài đặt dependencies. Đang thử cài đặt lại..."
    # Thử cài đặt lại với --no-cache-dir
    if ! $VENV_PIP install --no-cache-dir -r requirements.txt; then
        echo "❌ Không thể cài đặt dependencies. Vui lòng kiểm tra requirements.txt và thử lại."
        exit 1
    fi
fi

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
    $VENV_PYTHON scripts/build_club_index.py --force
else
    echo "   → Cập nhật RAG index hiện có..."
    $VENV_PYTHON scripts/build_club_index.py
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

# Lấy IP public và thêm vào .env nếu chưa có
echo "🌐 Lấy IP public..."
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "")
if [ -n "$PUBLIC_IP" ]; then
    echo "   → IP Public: $PUBLIC_IP"
    # Kiểm tra xem PUBLIC_IP đã có trong .env chưa
    if ! grep -q "^PUBLIC_IP=" .env 2>/dev/null; then
        echo "PUBLIC_IP=$PUBLIC_IP" >> .env
        echo "   ✅ Đã thêm PUBLIC_IP vào .env"
    else
        # Cập nhật IP nếu đã có (tương thích với cả macOS và Linux)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^PUBLIC_IP=.*|PUBLIC_IP=$PUBLIC_IP|" .env
        else
            # Linux
            sed -i "s|^PUBLIC_IP=.*|PUBLIC_IP=$PUBLIC_IP|" .env
        fi
        echo "   ✅ Đã cập nhật PUBLIC_IP trong .env"
    fi
    # Cập nhật CORS_ORIGINS nếu chưa có
    if ! grep -q "^CORS_ORIGINS=" .env 2>/dev/null; then
        CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://$PUBLIC_IP:3000"
        echo "CORS_ORIGINS=$CORS_ORIGINS" >> .env
        echo "   ✅ Đã thêm CORS_ORIGINS vào .env"
    fi
else
    echo "   ⚠️  Không thể lấy IP public. Bạn có thể set thủ công trong .env"
fi

# Khởi động backend
echo "🚀 Khởi động backend..."
$VENV_PYTHON main.py &
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

# Hiển thị thông tin truy cập
echo ""
echo "🎉 Chatbot đã khởi động thành công!"
echo ""
echo "📍 Truy cập local:"
echo "   📱 Frontend: http://localhost:3000"
echo "   🔧 Backend: http://localhost:8000"
echo "   🦙 Ollama: http://localhost:11434"
echo ""
if [ -n "$PUBLIC_IP" ]; then
    echo "🌐 Truy cập từ bên ngoài (IP Public: $PUBLIC_IP):"
    echo "   📱 Frontend: http://$PUBLIC_IP:3000"
    echo "   🔧 Backend API: http://$PUBLIC_IP:8000"
    echo "   📖 API Docs: http://$PUBLIC_IP:8000/docs"
    echo ""
    echo "⚠️  Lưu ý: Đảm bảo firewall/security group đã mở port 3000 và 8000"
fi
echo ""
echo "Để dừng chatbot, nhấn Ctrl+C"

# Chờ user dừng
trap 'echo "🛑 Đang dừng chatbot..."; kill $BACKEND_PID $FRONTEND_PID $OLLAMA_PID 2>/dev/null; exit' INT
wait