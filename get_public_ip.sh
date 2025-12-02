#!/bin/bash
# Script để lấy IP public của server

echo "🌐 Đang lấy IP public..."

# Thử nhiều service để lấy IP
PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || \
            curl -s --max-time 5 icanhazip.com 2>/dev/null || \
            curl -s --max-time 5 ipinfo.io/ip 2>/dev/null || \
            curl -s --max-time 5 api.ipify.org 2>/dev/null || \
            echo "")

if [ -n "$PUBLIC_IP" ]; then
    echo "✅ IP Public: $PUBLIC_IP"
    echo ""
    echo "📍 URLs để truy cập:"
    echo "   Frontend: http://$PUBLIC_IP:3000"
    echo "   Backend API: http://$PUBLIC_IP:8000"
    echo "   API Docs: http://$PUBLIC_IP:8000/docs"
    echo ""
    echo "⚠️  Đảm bảo firewall/security group đã mở port 3000 và 8000"
else
    echo "❌ Không thể lấy IP public. Kiểm tra kết nối internet."
    exit 1
fi

