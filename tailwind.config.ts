import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        bokumo: {
          bg: "#FFF5F5",
          ink: "#7B2D3B",
          sub: "#B5636F",
          line: "#F5BFC7",
          accent: "#E8607A",
          pink: "#FCD5CE",
          "pink-light": "#FEE8E4",
        }
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Hiragino Sans",
          "Hiragino Kaku Gothic ProN",
          "Noto Sans JP",
          "sans-serif"
        ],
        serif: ["\"Noto Serif JP\"", "\"Hiragino Mincho ProN\"", "serif"],
        display: ["\"Rounded Mplus 1c\"", "\"Hiragino Maru Gothic ProN\"", "sans-serif"]
      },
      boxShadow: {
        card: "0 1px 3px rgba(123,45,59,0.06), 0 1px 2px rgba(123,45,59,0.04)",
        hover: "0 12px 24px -12px rgba(232,96,122,0.25)"
      }
    }
  },
  plugins: []
};

export default config;
