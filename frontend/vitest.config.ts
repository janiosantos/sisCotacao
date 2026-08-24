import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Configuração de testes unitários do frontend (vitest).
// - Ambiente jsdom (DOM disponível para testes de componentes React).
// - Não reusa o vite.config.ts de dev/build: os plugins de build (tailwind,
//   buildInfo) não são necessários aqui.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/**/*.test.{ts,tsx}", "src/**/*.test.{ts,tsx}"],
  },
});