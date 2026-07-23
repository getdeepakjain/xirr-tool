import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend runs on :8000. During dev we proxy /api to it so the SPA and
// API share an origin (keeps cookies / CORS simple).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
