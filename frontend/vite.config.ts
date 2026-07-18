import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: proxy /api to the FastAPI server. Build: emit ./dist, which FastAPI serves.
export default defineConfig({
  plugins: [react()],
  base: "/",
  server: { proxy: { "/api": "http://localhost:8000" } },
});
