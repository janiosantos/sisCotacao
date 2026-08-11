// E2E IA: importar retorno de fornecedor por texto, extrair, associar e aplicar preços.
import puppeteer from "puppeteer-core";
import { login } from "./e2e_auth.mjs";

const BASE = "http://localhost:5173";
const API = "http://localhost:8000";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const results = [];
const ok = (n, cond) => results.push({ name: n, pass: !!cond });
const fail = (n, e) => results.push({ name: n, pass: false, err: String(e).slice(0, 300) });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// pega uma cotação aberta (status != fechada)
const cotacoes = await (await fetch(API + "/api/cotacoes?status=aberta")).json();
const lista = Array.isArray(cotacoes) ? cotacoes : cotacoes.cotacoes || [];
const aberta = lista.find((c) => c.status !== "fechada") || lista[0];
if (!aberta) { console.log("### sem cotação aberta p/ teste IA"); process.exit(1); }
const cotId = aberta.id;

// busca os itens reais da cotação para montar um retorno de fornecedor coerente
const detalhe = await (await fetch(API + `/api/cotacoes/${cotId}`)).json();
const detalheItens = Array.isArray(detalhe) ? detalhe : detalhe.itens || [];
const precoBase = 10 + Math.round(Math.random() * 90);
if (!detalheItens.length) { console.log("### cotação sem itens p/ teste IA"); process.exit(1); }
const texto = detalheItens
  .slice(0, 2)
  .map((it, idx) => `${it.name} — R$ ${precoBase + idx},50 /un`)
  .join("\n");

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
await login(page);
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 250)));
page.on("console", (m) => { if (m.type() === "error") console.log("[console.error]", m.text().slice(0, 200)); });

try {
  await page.goto(`${BASE}/#/cotacoes/${cotId}`, { waitUntil: "networkidle0", timeout: 45000 });
  await page.waitForSelector("#btnImportarIA", { timeout: 15000 });
  ok(`cotação aberta com botão Importar retorno (id=${cotId})`, true);

  await page.click("#btnImportarIA");
  await page.waitForSelector("#iaTexto", { timeout: 10000 });
  ok("modal IA abre com textarea", true);

  // verifica fornecedor pré-selecionado (select só existe quando >1 fornecedor)
  const temSel = await page.evaluate(() => !!document.querySelector("#iaFornecedor"));
  let fornSel = null;
  if (temSel) fornSel = await page.$eval("#iaFornecedor", (el) => el.value);
  ok(`fornecedor ${temSel ? "selecionado (" + fornSel + ")" : "único (sem select)"}`, !temSel || !!fornSel);

  // cola um retorno simples e extrai
  await page.type("#iaTexto", texto);
  await page.click("#btnExtrair");
  await page.waitForSelector(".ia-cand", { timeout: 120000 });
  const rows = await page.$$eval(".ia-cand", (els) => els.length);
  const preco1 = await page.$eval(".ia-preco", (el) => el.textContent.trim()).catch(() => "—");
  ok(`extração retorna ${rows} item(ns) com candidatos (preço "${preco1}")`, rows >= 1 && /R\$/.test(preco1));

  // o melhor candidato já vem pré-selecionado (não mostra "Sem correspondência")
  const selVal = await page.$eval(".ia-cand[data-row='0']", (el) => el.value).catch(() => "");
  const selTxt = await page.$eval(".ia-cand[data-row='0']", (el) => el.selectedOptions[0]?.textContent.trim() || "").catch(() => "");
  ok(`melhor candidato pré-selecionado (${selVal} — ${selTxt.slice(0, 40)})`, !!selVal);

  // aplica
  const btnEnabled = await page.$eval("#iaAplicar", (el) => !el.disabled);
  ok(`botão Aplicar habilitado (${btnEnabled})`, btnEnabled);
  if (btnEnabled) {
    await page.click("#iaAplicar");
    await sleep(1500);
    const toastText = await page.evaluate(() => document.querySelector("#toast")?.textContent || document.querySelector(".toast")?.textContent || "");
    const modalFechou = await page.evaluate(() => !document.querySelector("#iaTexto"));
    ok(`aplica e fecha modal — toast "${toastText.slice(0, 60)}"`, /IA aplicada/i.test(toastText) && modalFechou);
  }
} catch (e) {
  console.log("### FALHA GERAL ###", e);
  fail("SCRIPT-EXEC", e);
} finally {
  await browser.close();
}

console.log("\n=== RESULTADOS IA ===");
let fails = 0;
for (const r of results) { console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.pass ? "" : " — " + r.err}`); if (!r.pass) fails++; }
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);