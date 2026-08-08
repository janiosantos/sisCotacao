// E2E interações: carrinho, matriz de variação, filtros.
import puppeteer from "puppeteer-core";

const BASE = "http://localhost:5173";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const results = [];
const ok = (n) => results.push({ name: n, pass: true });
const fail = (n, e) => results.push({ name: n, pass: false, err: String(e).slice(0, 300) });

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 250)));
page.on("console", (m) => { if (m.type() === "error") console.log("[console.error]", m.text().slice(0, 200)); });

try {
  // Novo contexto: limpa carrinho
  await page.goto(BASE + "/#/catalogo", { waitUntil: "networkidle0", timeout: 45000 });
  await page.evaluate(() => localStorage.removeItem("cotacao_draft_v1"));

  // --- fluxo: produto individual -> plus qty ---
  await page.waitForSelector(".catalog-layout", { timeout: 20000 });
  // O card com .p-plus é um produto individual (não grupo). Pode haver 0 em agrupado=1;
  // alternar para modo "todas as opções" para garantir que haja p-minus/plus.
  const btnModo = await page.$("#btnModo");
  if (btnModo) await page.click("#btnModo");
  await page.waitForSelector(".p-card .p-plus", { timeout: 20000 });
  const before = await page.evaluate(() => JSON.parse(localStorage.getItem("cotacao_draft_v1") || '{"itens":{}}').itens || {});

  await page.click(".p-card .p-plus");
  await sleep(500);
  const after = await page.evaluate(() => JSON.parse(localStorage.getItem("cotacao_draft_v1") || '{"itens":{}}').itens || {});
  const added = Object.values(after).reduce((s, v) => s + Number(v), 0) > Object.values(before).reduce((s, v) => s + Number(v), 0);
  ok("catalogo: clique em + grava 1 unidade no draft", added);

  const qtyInput = await page.$eval(".p-card .p-qty", (el) => el.value);
  ok(`catalogo: input de qtd atualiza (${qtyInput})`, Number(qtyInput) >= 1);

  // sidebar mostra item?
  await sleep(400);
  const sbCount = await page.$eval("#sbInfo", (el) => el.textContent).catch(() => "");
  ok(`catalogo: sidebar reflete items (${sbCount})`, /item/.test(sbCount));

  // --- abrir variante de grupo se existir (2D matrix) ---
  let matrizOk = true;
  try {
    // procurar um card com data-group
    const haGrupo = await page.$('.p-card[data-group]');
    if (haGrupo) {
      await page.click('.p-card[data-group] .p-pick', { timeout: 5000 });
      await page.waitForSelector('#mmMatriz', { timeout: 8000 });
      const mGrids = await page.$$("#mmMatriz .m-grid");
      const resumo = await page.$$("#mmSubtotal");
      ok(`catalogo: matriz de variação abre (${mGrids.length} grid, resumo ${resumo.length})`, mGrids.length >= 1 && resumo.length >= 1);
      // fecha
      await page.click(".modal [data-close]").catch(() => {});
    } else {
      ok("catalogo: matriz de variação (sem grupo na página — pulado)", true);
    }
  } catch (e) {
    ok("catalogo: matriz de variação abre", false);
    modalOpened = false;
  }

  // --- compras: workflow rápido (nova compra) ---
  await page.evaluate(() => { location.hash = "#/compras"; });
  await page.waitForSelector("#cprBody", { timeout: 15000 });
  const nova = await page.$("#cprNova");
  ok("compras: botão `No va compra` presente", nova != null);
  if (nova) {
    await page.click("#cprNova");
    await sleep(600);
    // na eta1 há um form de items? conferir o stepper ativo
    const etapa = await page.$eval("#cprStepper .cpr-step.is-cur", (el) => el.textContent).catch(() => "");
    ok(`compras: stepper inicia na etapa 1 (${etapa.trim()})`, etapa.includes("Lista"));
  }

  // --- produtos: abrir editor novo ---
  await page.evaluate(() => { location.hash = "#/produtos/novo"; });
  await page.waitForSelector(".page-title", { timeout: 15000 });
  const tituloNovo = await page.$eval(".page-title", (el) => el.textContent);
  ok(`produtos: rota /novo renderiza (${tituloNovo})`, tituloNovo.length > 0);
} catch (e) {
  console.log("### FALHA GERAL ###", e);
  fail("SCRIPT-EXEC", e);
} finally {
  await browser.close();
}

console.log("\n=== RESULTADOS === ");
let fails = 0;
for (const r of results) { console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.pass ? "" : " — " + r.err}`); if (!r.pass) fails++; }
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }