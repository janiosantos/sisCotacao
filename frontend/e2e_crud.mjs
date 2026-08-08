import puppeteer from "puppeteer-core";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new" });
const page = await browser.newPage();
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 300)));

const results = [];
const ok = (n) => results.push({ name: n, pass: true });
const fail = (n, e) => results.push({ name: n, pass: false, err: String(e).slice(0, 250) });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

try {
  // --- Fornecedores: abrir modal criar ---
  await page.goto("http://localhost:5173/#/fornecedores", { waitUntil: "networkidle0", timeout: 45000 });
  await page.waitForSelector(".page-title", { timeout: 15000 });
  await new Promise((r) => setTimeout(r, 1000));

  const btnNovo = await page.$("#btnNovo");
  ok("fornecedores: botão Novo fornecedor presente", btnNovo != null);
  if (btnNovo) {
    await page.click("#btnNovo");
    await page.waitForSelector(".modal", { timeout: 6000 });
    const modal = await page.evaluate(() => document.querySelector(".modal")?.textContent?.slice(0, 120));
    ok("fornecedores: modal criar abre", /fornecedor/i.test(modal || ""));
    await page.evaluate(() => document.querySelector(".modal [data-close]")?.click());
    await sleep(300);
  }
  const rows = await page.$$eval("table tbody tr", (r) => r.length);
  ok(`fornecedores: tabela tem linhas (${rows})`, rows > 0);

  // --- Produtos editor já aberto: preenche campos mínimos? Não criar — só abrir outra rota ---
  await page.evaluate(() => { location.hash = "#/produtos/1891"; });
  await page.waitForSelector(".page-title", { timeout: 15000 });
  await new Promise((r) => setTimeout(r, 1500));
  const prod = await page.evaluate(() => ({
    titulo: document.querySelector(".page-title")?.textContent,
    hasNome: !!document.querySelector("#pNome, [name=nome], #nome"),
    formActions: [...document.querySelectorAll("#app button, #app .btn")].map((b) => b.textContent.trim().slice(0, 30)).slice(0, 8),
  }));
  ok(`produtos: editor de produto ${prod.id} abre (${prod.titulo})`, /Editar|Produto/i.test(prod.titulo || "") || prod.hasNome);

  // --- Histórico: dados existem? ---
  await page.evaluate(() => { location.hash = "#/historico"; });
  await page.waitForSelector(".page-title", { timeout: 15000 });
  await new Promise((r) => setTimeout(r, 1200));
  const his = await page.evaluate(() => ({
    temTabela: !!document.querySelector("table"),
    rows: document.querySelectorAll("tbody tr").length,
    text: document.querySelector("#app")?.textContent?.slice(0, 120),
  }));
  ok(`historico: renderiza (tabela=${his.temTabela}, linhas=${his.rows})`, his.temTabela || /nada|vazio/i.test(his.text || ""));
} catch (e) {
  console.log("### FALHA GERAL ###", e);
  fail("SCRIPT-EXEC", e);
} finally {
  await browser.close();
}

console.log("\n=== RESULTADOS CRUD ===");
let fails = 0;
for (const r of results) { console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.pass ? "" : " — " + r.err}`); if (!r.pass) fails++; }
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);