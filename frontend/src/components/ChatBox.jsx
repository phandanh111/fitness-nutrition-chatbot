import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Bot,
  User,
  Activity,
  Target,
  Zap,
  TrendingUp,
} from "lucide-react";
import { chatAPI } from "../api";

const ChatBox = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(
    () => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  );
  const [nutritionInfo, setNutritionInfo] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Tin nhắn chào mừng
    const welcomeMessage = {
      id: Date.now(),
      type: "bot",
      content:
        "Xin chào! Tôi là chuyên gia dinh dưỡng thể hình AI của bạn! 💪\n\nĐể có thể tư vấn chính xác nhất, hãy cho tôi biết:\n• Chiều cao (cm)\n• Cân nặng (kg)\n• Tuổi và giới tính\n• Mục tiêu (tăng cơ, giảm mỡ, giữ cân)\n• Số buổi tập/tuần\n\nBạn có thể chia sẻ thông tin này trong một tin nhắn hoặc từng phần nhé!",
      timestamp: new Date(),
    };
    setMessages([welcomeMessage]);
  }, []);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: "user",
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);

    try {
      const response = await chatAPI.sendMessage(inputMessage, sessionId);

      const botMessage = {
        id: Date.now() + 1,
        type: "bot",
        content: response.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);

      // Cập nhật thông tin dinh dưỡng nếu có
      if (response.nutrition_info) {
        setNutritionInfo(response.nutrition_info);
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: "bot",
        content: "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại sau.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const NutritionCard = ({ nutritionInfo }) => {
    if (!nutritionInfo) return null;

    const { macros, goal_calories, tdee, user_info } = nutritionInfo;

    return (
      <div className="nutrition-card mt-4">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-5 h-5 text-fitness-600 dark:text-fitness-400" />
          <h3 className="font-semibold text-gray-800 dark:text-white">
            Thông tin dinh dưỡng của bạn
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">
                Calo mục tiêu:
              </span>
              <span className="font-semibold text-fitness-600 dark:text-fitness-400">
                {goal_calories} kcal
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">TDEE:</span>
              <span className="text-gray-800 dark:text-gray-200">
                {tdee} kcal
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Mục tiêu:{" "}
              <span className="font-semibold text-fitness-600 dark:text-fitness-400">
                {user_info.goal}
              </span>
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Tập luyện:{" "}
              <span className="font-semibold text-gray-800 dark:text-gray-200">
                {user_info.workout_days_per_week} buổi/tuần
              </span>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <h4 className="font-medium text-gray-800 dark:text-white">
            Macronutrients:
          </h4>

          {/* Protein */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-red-600 dark:text-red-400 font-medium">
                Protein
              </span>
              <span className="text-gray-800 dark:text-gray-200">
                {macros.protein.grams}g ({macros.protein.percentage}%)
              </span>
            </div>
            <div className="macro-bar">
              <div
                className="macro-fill macro-protein"
                style={{ width: `${macros.protein.percentage}%` }}
              ></div>
            </div>
          </div>

          {/* Carb */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-blue-600 dark:text-blue-400 font-medium">
                Carbohydrate
              </span>
              <span className="text-gray-800 dark:text-gray-200">
                {macros.carb.grams}g ({macros.carb.percentage}%)
              </span>
            </div>
            <div className="macro-bar">
              <div
                className="macro-fill macro-carb"
                style={{ width: `${macros.carb.percentage}%` }}
              ></div>
            </div>
          </div>

          {/* Fat */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-yellow-600 dark:text-yellow-400 font-medium">
                Fat
              </span>
              <span className="text-gray-800 dark:text-gray-200">
                {macros.fat.grams}g ({macros.fat.percentage}%)
              </span>
            </div>
            <div className="macro-bar">
              <div
                className="macro-fill macro-fat"
                style={{ width: `${macros.fat.percentage}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-gradient-to-r from-fitness-500 to-primary-500 text-white p-4 rounded-t-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Fitness Nutrition AI</h1>
            <p className="text-sm opacity-90">Chuyên gia dinh dưỡng thể hình</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-hide">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.type === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`flex gap-3 max-w-xs lg:max-w-md ${
                message.type === "user" ? "flex-row-reverse" : "flex-row"
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  message.type === "user"
                    ? "bg-primary-500 text-white"
                    : "bg-fitness-100 dark:bg-fitness-900/30 text-fitness-600 dark:text-fitness-400"
                }`}
              >
                {message.type === "user" ? (
                  <User className="w-4 h-4" />
                ) : (
                  <Bot className="w-4 h-4" />
                )}
              </div>

              <div className="flex flex-col">
                <div
                  className={`chat-bubble ${
                    message.type === "user"
                      ? "chat-bubble-user"
                      : "chat-bubble-bot"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
                <span
                  className={`text-xs text-gray-500 dark:text-gray-400 mt-1 ${
                    message.type === "user" ? "text-right" : "text-left"
                  }`}
                >
                  {formatTime(message.timestamp)}
                </span>
              </div>
            </div>
          </div>
        ))}

        {/* Nutrition Info Card */}
        {nutritionInfo && <NutritionCard nutritionInfo={nutritionInfo} />}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-fitness-100 dark:bg-fitness-900/30 text-fitness-600 dark:text-fitness-400 flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div className="chat-bubble chat-bubble-bot">
                <div className="flex items-center gap-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"></div>
                    <div
                      className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"
                      style={{ animationDelay: "0.1s" }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                  </div>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    Đang suy nghĩ...
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Nhập tin nhắn của bạn..."
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
              rows="1"
              disabled={isLoading}
            />
          </div>
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="px-6 py-3 bg-gradient-to-r from-fitness-500 to-primary-500 text-white rounded-xl hover:from-fitness-600 hover:to-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline">Gửi</span>
          </button>
        </div>

        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
          Nhấn Enter để gửi, Shift+Enter để xuống dòng
        </div>
      </div>
    </div>
  );
};

export default ChatBox;
