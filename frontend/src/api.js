import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// API functions
export const chatAPI = {
  // Gửi tin nhắn đến chatbot
  sendMessage: async (message, sessionId) => {
    try {
      const response = await api.post("/chat", {
        message,
        session_id: sessionId,
      });
      return response.data;
    } catch (error) {
      console.error("Error sending message:", error);
      throw error;
    }
  },

  // Cập nhật thông tin người dùng
  updateUserInfo: async (userInfo) => {
    try {
      const response = await api.post("/user-info", userInfo);
      return response.data;
    } catch (error) {
      console.error("Error updating user info:", error);
      throw error;
    }
  },

  // Lấy thông tin dinh dưỡng
  getNutritionInfo: async (sessionId) => {
    try {
      const response = await api.get(`/nutrition/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error("Error getting nutrition info:", error);
      throw error;
    }
  },

  // Xóa session
  clearSession: async (sessionId) => {
    try {
      const response = await api.delete(`/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error("Error clearing session:", error);
      throw error;
    }
  },
};

export default api;
