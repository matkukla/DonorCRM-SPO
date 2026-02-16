import { createContext, useContext, useState, useEffect } from "react"
import type { ReactNode } from "react"

export type Theme = "light" | "dark" | "system"

interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
  resolvedTheme: "light" | "dark"
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

const THEME_STORAGE_KEY = "donorcrm-theme"

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  // Initialize from localStorage or default to "system"
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored
    }
    return "system"
  })

  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light")

  // Resolve "system" theme to actual light/dark
  const getResolvedTheme = (currentTheme: Theme): "light" | "dark" => {
    if (currentTheme === "system") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
    }
    return currentTheme
  }

  // Apply theme to DOM
  const applyTheme = (resolved: "light" | "dark") => {
    const root = document.documentElement
    if (resolved === "dark") {
      root.classList.add("dark")
    } else {
      root.classList.remove("dark")
    }
    setResolvedTheme(resolved)
  }

  // Set theme and persist to localStorage
  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem(THEME_STORAGE_KEY, newTheme)
  }

  // Apply theme on mount and when theme changes
  useEffect(() => {
    const resolved = getResolvedTheme(theme)
    applyTheme(resolved)
  }, [theme])

  // Listen for system preference changes when theme is "system"
  useEffect(() => {
    if (theme !== "system") return

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
    const handleChange = () => {
      const resolved = getResolvedTheme("system")
      applyTheme(resolved)
    }

    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [theme])

  const value: ThemeContextType = {
    theme,
    setTheme,
    resolvedTheme,
  }

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider")
  }
  return context
}
