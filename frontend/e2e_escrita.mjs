// E2E fluxos de escrita: produtos (novo/salvar), famílias, URL.
import puppeteer from "puppeteer-core";
import { login } from "./e2e_auth.mjs";

const BASE = "http://localhost:5173";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const results = [];
const ok = (n, cond) => results.push({ name: n, pass: !!cond });
const fail = (n, e) => results.push({ name: n, pass: false, err: String(e).slice(0, 300) });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
await login(page);
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 250)));
page.on("console", (m) => { if (m.type() === "error") console.log("[console.error]", m.text().slice(0, 200)); });

try {
  // --- Famílias: abrir modal e criar uma família simples ---
  await page.goto(BASE + "/#/produtos", { waitUntil: "networkidle0", timeout: 45000 });
  await page.waitForSelector("#btnFamilias", { timeout: 15000 });
  await page.click("#btnFamilias");
  await page.waitForSelector("#btnNovaFamilia", { timeout: 8000 });
  ok("produtos: modal de famílias abre", true);

  await page.click("#btnNovaFamilia");
  await page.waitForSelector("#faNome", { timeout: 6000 });
  await page.type("#faNome", "E2E Teste Familia");
  await page.click("#faSalvar");
  await sleep(800);
  const famText = await page.evaluate(() => document.querySelector("#famLista")?.textContent || "");
  ok(`produtos: família criada aparece na lista (${famText.includes("E2E Teste Familia")})`, famText.includes("E2E Teste Familia"));
  await page.evaluate(() => document.querySelector(".modal [data-close]")?.click());
  await sleep(400);

  // --- Novo produto via editor ---
  await page.evaluate(() => { location.hash = "#/produtos/novo"; });
  await page.waitForSelector("#eNome", { timeout: 15000 });
  await sleep(400);
  await page.type("#eNome", "E2E Produto Teste Cabo 10mm");
  await page.type("#eCategoria", "Fios e Cabos");
  await page.click("#btnSalvar");
  await sleep(2500);
  const salvo = await page.evaluate(() => ({ hash: location.hash, toast: document.querySelector("#toast")?.textContent || "" }));
  ok(`produtos: salvar produto cria e redireciona (${salvo.hash})`, /#\/produtos\/\d+/.test(salvo.hash));
  ok(`produtos: toast de sucesso (${salvo.toast.trim()})`, /sucesso|criado|salvo/i.test(salvo.toast));

  // --- Novo via URL: abre modal ---
  await page.evaluate(() => { location.hash = "#/produtos"; });
  await page.waitForSelector("#btnNovoUrl", { timeout: 15000 });
  await page.click("#btnNovoUrl");
  await page.waitForSelector("#iuUrl", { timeout: 6000 });
  const urlModal = await page.evaluate(() => ({
    url: !!document.querySelector("#iuUrl"),
    analisar: !!document.querySelector("#iuAnalisar"),
  }));
  ok(`produtos: modal "Novo via URL" abre (url=${urlModal.url}, analisar=${urlModal.analisar})`, urlModal.url && urlModal.analisar);
  await page.evaluate(() => document.querySelector(".modal [data-close]")?.click());
  await sleep(300);
} catch (e) {
  console.log("### FALHA GERAL ###", e);
  fail("SCRIPT-EXEC", e);
} finally {
  await browser.close();
}

console.log("\n=== RESULTADOS ESCRITA PRODUTOS ===");
let fails = 0;
for (const r of results) { console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.pass ? "" : " — " + r.err}`); if (!r.pass) fails++; }
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);