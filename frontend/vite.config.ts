import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  // GitHub Pages publishes this repository under /RuangKampus/.
  // Local Vite development continues to use the root path.
  base: command === "serve" ? "/" : "/RuangKampus/",
  plugins: [react()],
  server: { host: "0.0.0.0", port: 5173, strictPort: true },
  preview: { host: "0.0.0.0", port: 4173 },
}));
