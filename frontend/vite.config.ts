import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// GitHub Pages is the only deployment that serves from /RuangKampus/.
// Railway and local development publish the app at the domain root.
export default defineConfig(() => ({
  base: process.env.GITHUB_PAGES === "true" ? "/RuangKampus/" : "/",
  plugins: [react()],
  server: { host: "0.0.0.0", port: 5173, strictPort: true },
  preview: { host: "0.0.0.0", port: 4173 },
}));
