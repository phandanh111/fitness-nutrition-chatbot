import React, { createContext, useContext, useState, useEffect } from "react";

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    // Lấy theme từ localStorage hoặc mặc định là 'system'
    const savedTheme = localStorage.getItem("theme");
    return savedTheme || "system";
  });

  const [effectiveTheme, setEffectiveTheme] = useState(() => {
    // Xác định theme hiệu quả dựa trên theme đã chọn và system preference
    if (theme === "system") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    return theme;
  });

  useEffect(() => {
    // Lưu theme vào localStorage khi thay đổi
    localStorage.setItem("theme", theme);

    // Xác định theme hiệu quả
    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const updateEffectiveTheme = (e) => {
        setEffectiveTheme(e.matches ? "dark" : "light");
      };

      setEffectiveTheme(mediaQuery.matches ? "dark" : "light");
      mediaQuery.addEventListener("change", updateEffectiveTheme);

      return () =>
        mediaQuery.removeEventListener("change", updateEffectiveTheme);
    } else {
      setEffectiveTheme(theme);
    }
  }, [theme]);

  useEffect(() => {
    // Áp dụng theme vào document root
    const root = document.documentElement;
    if (effectiveTheme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [effectiveTheme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, effectiveTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
