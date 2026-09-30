import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // strictPort: fail loudly if 5173 is taken instead of silently moving to
  // another port, which the backend's CORS settings would then block.
  server: { port: 5173, strictPort: true },
});
