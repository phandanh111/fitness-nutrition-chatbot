import React from "react";
import ChatBox from "./components/ChatBox";
import ThemeSwitcher from "./components/ThemeSwitcher";
import { Target } from "lucide-react";

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-fitness-50 via-primary-50 to-fitness-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors duration-200">
      {/* Header */}
      <header className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-r from-fitness-500 to-primary-500 rounded-xl flex items-center justify-center">
                <Target className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  The New Gym AI
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Chuyên gia tư vấn The New Gym
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <ThemeSwitcher />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex items-start justify-center min-h-[calc(100vh-80px)] px-4 sm:px-6 lg:px-8 pt-4 pb-8">
        <div className="w-full max-w-4xl">
          <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 h-[750px] lg:h-[900px] transition-colors duration-200">
            <ChatBox />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
