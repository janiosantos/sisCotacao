import { defineConfig, type PluginOption } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const BACKEND_HOST = process.env["BACKEND_HOST"] || "localhost";
const PORT_BACKEND = parseInt(process.env["BACKEND_PORT"] || "8000", 10);
const FRONTEND_DIR = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  base: "/",
  plugins: [react(), buildInfo()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(FRONTEND_DIR, "index.html"),
    },
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: `http://${BACKEND_HOST}:${PORT_BACKEND}`,
        changeOrigin: true,
      },
      "/images": {
        target: `http://${BACKEND_HOST}:${PORT_BACKEND}`,
        changeOrigin: true,
      },
      // Páginas renderizadas pelo Flask (fora da SPA): impressão de
      // pedidos de compra e de orçamentos. Sem isso, em dev (porta 5173)
      // o clique em "PDF"/"Imprimir" cai na SPA em vez do backend.
      "/compras/pedidos": {
        target: `http://${BACKEND_HOST}:${PORT_BACKEND}`,
        changeOrigin: true,
      },
      "/orcamentos": {
        target: `http://${BACKEND_HOST}:${PORT_BACKEND}`,
        changeOrigin: true,
      },
      "/fornecedor": {
        target: `http://${BACKEND_HOST}:${PORT_BACKEND}`,
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