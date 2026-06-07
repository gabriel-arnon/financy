import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2933",
        mint: "#16a085",
        coral: "#e76f51",
        paper: "#f7f7f2"
      }
    }
  },
  plugins: []
};

export default config;
