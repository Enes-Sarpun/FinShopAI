import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
        },
        success: "#22c55e",
        warning: "#f59e0b",
        danger: "#ef4444",
        income: {
          DEFAULT: "#10b981",
          dark: "#059669",
        },
        expense: {
          DEFAULT: "#ef4444",
          dark: "#dc2626",
        },
        available: {
          DEFAULT: "#6366f1",
          dark: "#4f46e5",
        },
        savings: {
          DEFAULT: "#a855f7",
          dark: "#7c3aed",
        },
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "Inter", "system-ui", "sans-serif"],
        mono: ["Space Grotesk", "monospace"],
      },
      keyframes: {
        wave: {
          "0%, 100%": { transform: "rotate(0deg)" },
          "25%": { transform: "rotate(20deg)" },
          "75%": { transform: "rotate(-15deg)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        wave: "wave 2s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
        "slide-up": "slide-up 0.4s ease-out forwards",
      },
      backgroundImage: {
        "mesh-light": "linear-gradient(135deg, #fafbff 0%, #f5f7ff 50%, #fef8ff 100%)",
        "income-gradient": "linear-gradient(135deg, #10b981, #059669)",
        "expense-gradient": "linear-gradient(135deg, #ef4444, #dc2626)",
        "available-gradient": "linear-gradient(135deg, #6366f1, #4f46e5)",
        "savings-gradient": "linear-gradient(135deg, #a855f7, #7c3aed)",
        "brand-gradient": "linear-gradient(135deg, #2563eb, #7c3aed)",
      },
      boxShadow: {
        glass: "0 8px 32px rgba(31, 38, 135, 0.08), 0 2px 8px rgba(31, 38, 135, 0.04)",
        "glass-hover": "0 16px 40px rgba(31, 38, 135, 0.14), 0 4px 12px rgba(31, 38, 135, 0.08)",
        "card-income": "0 4px 20px rgba(16, 185, 129, 0.15)",
        "card-expense": "0 4px 20px rgba(239, 68, 68, 0.15)",
        "card-available": "0 4px 20px rgba(99, 102, 241, 0.15)",
        "card-savings": "0 4px 20px rgba(168, 85, 247, 0.15)",
      },
    },
  },
  plugins: [],
};

export default config;
