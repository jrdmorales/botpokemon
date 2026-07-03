import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#f0f4ff",
        surface: "#ffffff",
        elevated: "#eef1ff",
        "border-dim": "#dde3f0",
        "border-mid": "#c5cfe8",
        ink: "#1a1a3e",
        "ink-2": "#4a5270",
        "ink-3": "#94a3b8",
        violet: { DEFAULT: "#3B4CCA", dark: "#2d3aad", light: "#6370e0" },
        holo: "#16a34a",
        preorder: "#0ea5e9",
        warn: "#dc2626",
        yellow: "#FFDE00",
      },
      fontFamily: {
        display: ["var(--font-bebas)", "Impact", "sans-serif"],
        body: ["var(--font-space)", "system-ui", "sans-serif"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pop-in": {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.4s cubic-bezier(0.16,1,0.3,1) both",
        "pop-in": "pop-in 0.3s cubic-bezier(0.16,1,0.3,1) both",
      },
    },
  },
  plugins: [],
} satisfies Config;
