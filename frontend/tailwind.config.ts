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
          bg: "#050507",
          surface0: "#050507",
          card: "#0B0C0E",
          surface1: "#0B0C0E",
          elevated: "#111317",
          surface2: "#111317",
          border: "rgba(255, 255, 255, 0.07)",
          muted: "#9CA3AF",
          telemetry: "#4B5563",
          text: "#F9FAFB",
        },
        tactical: {
          emerald: "#10B981",
          amber: "#F59E0B",
          crimson: "#EF4444",
          cyan: "#06B6D4",
        },
        paypal: {
          blue: "#0070BA",
          dark: "#003087",
          cyan: "#06B6D4",
        },
        status: {
          approved: "#10B981",
          review: "#F59E0B",
          blocked: "#EF4444",
          executing: "#06B6D4",
        },
      },
      fontFamily: {
        serif: ["'Instrument Serif'", "'Playfair Display'", "Georgia", "Cambria", "serif"],
        sans: ["'Geist Sans'", "'Inter'", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      boxShadow: {
        island: "0 20px 40px -15px rgba(0, 0, 0, 0.7)",
        bezel: "inset 0 1px 0 0 rgba(255, 255, 255, 0.08)",
        "glow-emerald": "0 0 28px -4px rgba(16, 185, 129, 0.22)",
        "glow-amber": "0 0 28px -4px rgba(245, 158, 11, 0.22)",
        "glow-crimson": "0 0 32px -4px rgba(239, 68, 68, 0.28)",
        "glow-cyan": "0 0 28px -4px rgba(6, 182, 212, 0.22)",
      },
    },
  },
  plugins: [],
};

export default config;
