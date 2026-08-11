// E2E ERP: testa páginas administrativas do sistema.
import puppeteer from "puppeteer-core";
import { login } from "./e2e_auth.mjs";

const BASE = "http://localhost:5173";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const results = [];
const ok = (n, cond) => results.push({ name: n, pass: !!cond });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900 });
await login(page);

try {
  // ── Clientes ──
  await page.goto(`${BASE}/#/clientes`, { waitUntil: "networkidle0", timeout: 30000 });
  await page.waitForSelector(".page-title", { timeout: 10000 });
  const cliTitle = await page.$eval(".page-title", (el) => el.textContent);
  ok("clientes: página carrega", /clientes/i.test(cliTitle));

  // ── Vendedores ──
  await page.goto(`${BASE}/#/vendedores`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector("table", { timeout: 10000 });
  ok("vendedores: tabela renderiza", true);

  // ── Plano de Contas ──
  await page.goto(`${BASE}/#/plano-contas`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector("table", { timeout: 10000 });
  ok("plano-contas: tabela renderiza", true);

  // ── Usuários ──
  await page.goto(`${BASE}/#/usuarios`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector("table", { timeout: 10000 });
  ok("usuarios: tabela renderiza", true);

  // ── Estoque ──
  await page.goto(`${BASE}/#/estoque`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector(".tab-bar", { timeout: 10000 });
  const tabs = await page.$$eval(".tab-btn", (els) => els.length);
  ok(`estoque: ${tabs} abas disponíveis`, tabs >= 4);

  // ── Preços ──
  await page.goto(`${BASE}/#/precos`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector(".tab-bar", { timeout: 10000 });
  ok("precos: abas carregam", true);

  // ── Financeiro ──
  await page.goto(`${BASE}/#/financeiro`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector(".tab-bar", { timeout: 10000 });
  const finTabs = await page.$$eval(".tab-btn", (els) => els.length);
  ok(`financeiro: ${finTabs} abas`, finTabs >= 6);

  // ── Caixa ──
  await page.waitForSelector(".fin-saldo-valor", { timeout: 10000 });
  const saldo = await page.$eval(".fin-saldo-valor", (el) => el.textContent);
  ok("caixa: saldo visível", /R\$/.test(saldo));

  // ── Bancos ──
  await page.goto(`${BASE}/#/bancos`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector(".tab-bar", { timeout: 10000 });
  ok("bancos: página carrega", true);

  // ── Fiscal ──
  await page.goto(`${BASE}/#/fiscal`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector(".tab-bar", { timeout: 10000 });
  const fiscTabs = await page.$$eval(".tab-btn", (els) => els.length);
  ok(`fiscal: ${fiscTabs} abas`, fiscTabs >= 6);

  // ── CFOP ──
  await page.goto(`${BASE}/#/fiscal`, { waitUntil: "networkidle0", timeout: 15000 });
  await sleep(1000);
  const cfopRows = await page.$$eval("table tbody tr", (els) => els.length);
  ok("fiscal cfop: linhas na tabela", cfopRows > 0);

  // ── PDV ──
  await page.goto(`${BASE}/#/pdv`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector("#pdvBusca", { timeout: 10000 });
  ok("pdv: campo busca presente", true);
  const pdvFooter = await page.$(".pdv-at");
  ok("pdv: barra de atalhos visível", !!pdvFooter);

  // ── Orçamentos ──
  await page.goto(`${BASE}/#/orcamentos`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector(".page-title", { timeout: 10000 });
  ok("orcamentos: página carrega", true);

  // ── Pós-venda ──
  await page.goto(`${BASE}/#/posvenda`, { waitUntil: "networkidle0", timeout: 15000 });
  await page.waitForSelector(".tab-bar", { timeout: 10000 });
  ok("posvenda: página carrega", true);

  // ── Categorias ──
  await page.goto(`${BASE}/#/categorias`, { waitUntil: "networkidle0", timeout: 15000 });
  await sleep(1000);
  ok("categorias: página carrega", true);

  // ── Relatórios (via API) ──
  const api = await page.evaluate(() => fetch("/api/relatorios/aging-receber").then((r) => r.json()));
  ok("relatorios aging-receber: API responde", Array.isArray(api));

} catch (e) {
  console.log("FALHA GERAL:", e.message);
  results.push({ name: "SCRIPT-EXEC", pass: false, err: e.message.slice(0, 200) });
} finally {
  await browser.close();
}

console.log("\n=== RESULTADOS E2E ERP ===");
let fails = 0;
for (const r of results) {
  console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.err ? " — " + r.err : ""}`);
  if (!r.pass) fails++;
}
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);
