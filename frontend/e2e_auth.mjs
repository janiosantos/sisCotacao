// e2e_auth.mjs — helper: autentica a página no gateway de login do app.
// Uso: import { login } from "./e2e_auth.mjs"; await login(page);
export async function login(page, { base = "http://localhost:5173", login: usu = "admin", senha = "admin123" } = {}) {
  await page.goto(base + "/#/catalogo", { waitUntil: "networkidle0", timeout: 45000 });
  const gate = await page.$(".login-box").catch(() => null);
  if (!gate) return; // já autenticado
  await page.waitForSelector("#lgLogin", { timeout: 15000 });
  await page.type("#lgLogin", usu);
  await page.type("#lgSenha", senha);
  await page.click("#lgEntrar");
  await page.waitForFunction(() => !document.querySelector(".login-box"), { timeout: 20000 });
  await new Promise((r) => setTimeout(r, 1200));
}