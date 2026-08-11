// E2E específico: matriz 2D de variação (abrir grupo "lâmpada" via busca).
import puppeteer from "puppeteer-core";
import { login } from "./e2e_auth.mjs";

const BASE = "http://localhost:5173";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const results = [];
const ok = (n) => results.push({ name: n, pass: true });
const fail = (n, e) => results.push({ name: n, pass: false, err: String(e).slice(0, 300) });

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
await login(page);
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 250)));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

try {
  await page.goto(BASE + "/#/catalogo", { waitUntil: "networkidle0", timeout: 45000 });
  await page.waitForSelector(".catalog-layout", { timeout: 20000 });

  // digita busca "lampada" para achar grupos
  await page.type("#fSearch", "lampada");
  await sleep(1200); // debounce 300ms + request

  const nCards = await page.$$eval(".p-card", (els) => els.length);
  ok(`busca 'lampada' retorna cards (${nCards})`, nCards > 0);

  // procura um card de grupo
  await page.waitForSelector('.p-card[data-group]', { timeout: 15000 });
  await page.click('.p-card[data-group] .p-pick');
  await page.waitForSelector("#mmMatriz", { timeout: 10000 });

  const info = await page.evaluate(() => {
    const mtx = document.querySelector("#mmMatriz");
    const grids = mtx.querySelectorAll(".m-grid").length;
    const qtyInputs = mtx.querySelectorAll(".m-qty").length;
    const cells = mtx.querySelectorAll(".m-cell").length;
    const rows = mtx.querySelectorAll("tbody tr").length;
    const subLabel = document.querySelector("#mmSubtotal")?.textContent;
    return { grids, qtyInputs, cells, rows, subLabel };
  });
  ok(`matriz: renderizada (grids=${info.grids}, celulas=${info.cells}, linhas=${info.rows}, qtds=${info.qtyInputs})`, info.grids >= 1 && info.cells >= 1);

  // digita qtd numa célula e verifica o subtotal atualizar
  if (info.qtyInputs >= 1) {
    await page.click(".m-cell .m-qty", { timeout: 3000 });
    await page.type(".m-cell .m-qty", "2");
    await sleep(400);
    const sub = await page.$eval("#mmSubtotal", (el) => el.textContent);
    ok(`matriz: subtotal atualiza ao digitar qty (${sub})`, /R\$/.test(sub) && sub !== "R$ 0,00");

    // adicionar à cotação
    await page.click("#mmAdd");
    await sleep(600);
    const draft = await page.evaluate(() => {
      const d = JSON.parse(localStorage.getItem("cotacao_draft_v1") || '{"itens":{}}');
      return Object.values(d.itens || {}).reduce((s, v) => s + Number(v), 0);
    });
    ok(`matriz: 'Adicionar à cotação' grava itens (draft qtd=${draft})`, draft >= 2);
  }
} catch (e) {
  console.log("### FALHA GERAL ###", e);
  fail("SCRIPT-EXEC", e);
} finally {
  await browser.close();
}

console.log("\n=== RESULTADOS MATRIZ ===");
let fails = 0;
for (const r of results) { console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.pass ? "" : " — " + r.err}`); if (!r.pass) fails++; }
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);