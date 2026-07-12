"use client";

import { useEffect } from "react";

const preferencesKey = "financy_user_preferences";

export function ThemeInitializer() {
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(preferencesKey);
      const preferences = raw ? JSON.parse(raw) : {};
      document.documentElement.dataset.theme = preferences.theme === "dark" ? "dark" : "light";
      document.documentElement.dataset.density = preferences.density === "compact" ? "compact" : "comfortable";
      document.documentElement.dataset.reduceMotion = preferences.reduceMotion ? "true" : "false";
    } catch {
      document.documentElement.dataset.theme = "light";
      document.documentElement.dataset.density = "comfortable";
      document.documentElement.dataset.reduceMotion = "false";
    }
  }, []);

  return null;
}
