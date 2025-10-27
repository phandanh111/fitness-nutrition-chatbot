import React from "react";
import ChatBox from "./components/ChatBox";
import { Target, Zap, TrendingUp, Heart } from "lucide-react";

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-fitness-50 via-primary-50 to-fitness-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-r from-fitness-500 to-primary-500 rounded-xl flex items-center justify-center">
                <Target className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Fitness Nutrition AI
                </h1>
                <p className="text-sm text-gray-600">
                  Chuyên gia dinh dưỡng thể hình thông minh
                </p>
              </div>
            </div>

            <div className="hidden md:flex items-center gap-6 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-fitness-500" />
                <span>Tư vấn cá nhân hóa</span>
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary-500" />
                <span>Tính toán chính xác</span>
              </div>
              <div className="flex items-center gap-2">
                <Heart className="w-4 h-4 text-red-500" />
                <span>Miễn phí</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar - Features */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-sm border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Tính năng chính
              </h2>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-fitness-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Target className="w-4 h-4 text-fitness-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">
                      Tư vấn cá nhân
                    </h3>
                    <p className="text-sm text-gray-600">
                      Dựa trên thông tin cá nhân của bạn
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <TrendingUp className="w-4 h-4 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">
                      Tính toán TDEE
                    </h3>
                    <p className="text-sm text-gray-600">
                      Sử dụng công thức khoa học chính xác
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Zap className="w-4 h-4 text-yellow-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">
                      Thực đơn chi tiết
                    </h3>
                    <p className="text-sm text-gray-600">
                      Gợi ý bữa ăn với calo và macro
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-r from-fitness-500 to-primary-500 rounded-2xl p-6 text-white">
              <h3 className="font-semibold mb-2">Bắt đầu ngay!</h3>
              <p className="text-sm opacity-90 mb-4">
                Chia sẻ thông tin cơ bản để nhận tư vấn dinh dưỡng phù hợp nhất.
              </p>
              <div className="text-xs space-y-1 opacity-80">
                <p>• Chiều cao & cân nặng</p>
                <p>• Tuổi & giới tính</p>
                <p>• Mục tiêu tập luyện</p>
                <p>• Số buổi tập/tuần</p>
              </div>
            </div>
          </div>

          {/* Chat Interface */}
          <div className="lg:col-span-3">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-200 h-[600px] lg:h-[700px]">
              <ChatBox />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white/60 backdrop-blur-sm border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-gray-600">
            <p className="mb-2">
              <strong>Fitness Nutrition AI</strong> - Chuyên gia dinh dưỡng thể
              hình thông minh
            </p>
            <p className="text-xs">
              ⚠️ Lưu ý: Thông tin chỉ mang tính chất tham khảo. Vui lòng tham
              khảo ý kiến chuyên gia y tế cho các vấn đề sức khỏe cụ thể.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
