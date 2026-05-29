import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Trading terminal palette
        bg:       "#0f1117",
        surface:  "#1a1d27",
        border:   "#2d3142",
        muted:    "#4a5068",
        text:     "#e2e8f0",
        subtle:   "#94a3b8",
        bull:     "#22c55e",  // green — bullish / profit
        bear:     "#ef4444",  // red   — bearish / loss
        gold:     "#f59e0b",  // amber — warning / neutral
        accent:   "#6366f1",  // indigo — brand accent
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
