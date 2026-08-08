import { defineConfig, type PluginOption } from "vite";
import { resolve } from "node:path";
import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const PORT_BACKEND = 8000;
const FRONTEND_DIR = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  base: "/",
  plugins: [buildInfo()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(FRONTEND_DIR, "index.html"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: `http://localhost:${PORT_BACKEND}`,
        changeOrigin: true,
      },
    },
  },
});

// Grava o timestamp de build em dist/build.txt.
function buildInfo(): PluginOption {
  return {
    name: "catalog-build-info",
    closeBundle() {
      mkdirSync(resolve(FRONTEND_DIR, "dist"), { recursive: true });
      writeFileSync(
        resolve(FRONTEND_DIR, "dist", "build.txt"),
        new Date().toISOString() + "\n"
      );
    },
  };
}