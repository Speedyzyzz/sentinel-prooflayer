import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sentinel: {
          bg: "#080C15",
          card: "#0E1526",
          elevated: "#141E34",
          border: "#1E2C48",
          muted: "#64748B",
          text: "#F8FAFC",
        },
        paypal: {
          blue: "#0070BA",
          dark: "#003087",
          cyan: "#00CFDE",
        },
        status: {
          approved: "#10B981",
          review: "#F59E0B",
          blocked: "#EF4444",
          executing: "#3B82F6",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
