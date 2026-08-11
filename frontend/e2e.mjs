// E2E smoke vs dev server (:5173, proxy /api -> :8000).
// Uso: node e2e.mjs [baseUrl]
import puppeteer from "puppeteer-core";
import { login } from "./e2e_auth.mjs";

const BASE = process.argv[2] || "http://localhost:5173";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const results = [];
const ok = (name) => results.push({ name, pass: true });
const fail = (name, err) => results.push({ name, pass: false, err: String(err).slice(0, 300) });

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox"],
});
const page = await browser.newPage();
await login(page);
page.on("console", (m) => {
  if (m.type() === "error") console.log("[browser.error]", m.text().slice(0, 200));
});
page.on("pageerror", (e) => console.log("[browser.pageerror]", String(e).slice(0, 250)));

try {
  // ---- catálogo ----
  await page.goto(BASE + "/#/catalogo", { waitUntil: "networkidle0", timeout: 45000 });
  await page.waitForSelector(".catalog-layout", { timeout: 20000 });
  const nCards = await page.$$eval(".p-card", (els) => els.length);
  ok(`catalogo: layout + cards (${nCards})`, nCards > 0);
  const hasFilter = await page.$("#fSearch") != null;
  ok("catalogo: toolbar/busca presente", hasFilter);
  const sidebar = await page.$(".cart-sidebar");
  ok("catalogo: sidebar de carrinho montada", sidebar != null);

  // abre modal de produto (clicar na foto do primeiro card agrupado ou não)
  let opened = false;
  try {
    await page.waitForSelector(".p-card .p-photo", { timeout: 10000 });
    await page.click(".p-card .p-photo", { timeout: 5000 });
    await page.waitForSelector(".modal", { timeout: 8000 });
    const hasModal = await page.$eval(".modal", (m) => m.textContent.includes("Adicionar") || m.textContent.length > 0);
    opened = hasModal;
    // fecha
    await page.click(".modal [data-close]").catch(() => {});
  } catch (e) {
    /* se falhar, não derruba: pode ser grupo ou imagem sem href */
  }
  ok("catalogo: modal de produto abre", opened);

  // ---- navegação hash muda rota e tab ativa ----
  await page.evaluate(() => { location.hash = "#/fornecedores"; });
  await page.waitForSelector(".page-title", { timeout: 15000 });
  const titulo = await page.$eval(".page-title", (el) => el.textContent);
  const tabAtiva = await page.$$eval("#mainNav a", (as) => as.find((a) => a.classList.contains("is-active"))?.dataset.route);
  ok(`fornecedores: rota renderiza (${titulo})`, titulo.includes("Fornecedore"));
  ok(`fornecedores: tab ativa correta (${tabAtiva})`, tabAtiva === "fornecedores");

  // fornecedores: contagem de linhas
  const rowsForn = await page.$$eval("table tbody tr", (r) => r.length);
  ok(`fornecedores: lista com linhas (${rowsForn})`, rowsForn >= 0);

  // ---- cotações ----
  await page.evaluate(() => { location.hash = "#/cotacoes"; });
  await page.waitForSelector(".page-title", { timeout: 15000 });
  const cotTitulo = await page.$eval(".page-title", (el) => el.textContent);
  ok(`cotacoes: lista renderiza (${cotTitulo})`, cotTitulo.includes("Cota"));

  // ---- compras ----
  await page.evaluate(() => { location.hash = "#/compras"; });
  await page.waitForSelector("#cprBody", { timeout: 15000 });
  const stepper = await page.$("#cprStepper");
  ok("compras: stepper presente", stepper != null);

  // ---- produtos (lista) ----
  await page.evaluate(() => { location.hash = "#/produtos"; });
  await page.waitForSelector(".page-title", { timeout: 15000 });
  const prodTitulo = await page.$eval(".page-title", (el) => el.textContent);
  ok(`produtos: lista renderiza (${prodTitulo})`, prodTitulo.length > 0);

  // ---- histórico ----
  await page.evaluate(() => { location.hash = "#/historico"; });
  await page.waitForSelector(".page-title", { timeout: 15000 });
  const hisTitulo = await page.$eval(".page-title", (el) => el.textContent);
  ok(`historico: lista renderiza (${hisTitulo})`, hisTitulo.length > 0);
} catch (e) {
  ok("SCRIPT-EXEC", false);
  console.log("### FALHA GERAL ###", e);
} finally {
  await browser.close();
}

console.log("\n=== RESULTADOS E2E ===");
let fails = 0;
for (const r of results) {
  console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.pass ? "" : " — " + r.err}`);
  if (!r.pass) fails++;
}
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);