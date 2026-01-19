#!/bin/bash

echo "🚀 Khởi động The New Gym Chatbot với Streamlit..."

# Kiểm tra Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama chưa được cài đặt. Vui lòng cài đặt Ollama trước:"
    echo "   macOS: brew install ollama"
    echo "   Linux: curl -fsSL https://ollama.ai/install.sh | sh"
    exit 1
fi

# Kiểm tra model DeepSeek R1
if ! ollama list | grep -q "deepseek-r1:7b"; then
    echo "📥 Tải model DeepSeek R1:14b..."
    ollama pull deepseek-r1:7b
    if [ $? -ne 0 ]; then
        echo "❌ Lỗi khi tải model. Vui lòng kiểm tra kết nối internet."
        exit 1
    fi
fi

# Khởi động Ollama service
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "🔧 Tạo virtual environment..."
    python3 -m venv venv
fi

BACKEND_DIR="$(pwd)"
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"
VENV_PIP="$BACKEND_DIR/venv/bin/pip"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment chưa được tạo đúng cách."
    exit 1
fi

echo "🔧 Kích hoạt virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Nâng cấp pip..."
$VENV_PIP install --upgrade pip setuptools wheel

# Cài đặt dependencies
echo "📥 Cài đặt Python packages..."
if ! $VENV_PIP install -r requirements.txt; then
    echo "❌ Lỗi khi cài đặt dependencies. Đang thử cài đặt lại..."
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
    $VENV_PYTHON scripts/build_exercise_index.py --force
else
    echo "   → Cập nhật RAG index hiện có..."
    $VENV_PYTHON scripts/build_exercise_index.py
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
fi

# Khởi động Streamlit
echo "🚀 Khởi động Streamlit app..."
echo ""
echo "🎉 Chatbot đã khởi động thành công!"
echo ""
echo "📍 Truy cập ứng dụng:"
echo "   🌐 Local: http://localhost:8501"
if [ -n "$PUBLIC_IP" ]; then
    echo "   🌐 Public: http://$PUBLIC_IP:8501"
    echo ""
    echo "⚠️  Lưu ý: Đảm bảo firewall/security group đã mở port 8501"
fi
echo ""
echo "Để dừng chatbot, nhấn Ctrl+C"
echo ""

# Chạy Streamlit
$VENV_PYTHON -m streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0

# Cleanup khi dừng
trap 'echo "🛑 Đang dừng chatbot..."; kill $OLLAMA_PID 2>/dev/null; exit' INT
wait

