// Reproduz criar cotação preenchendo célula LIVRE (sem variante) -> o fluxo que você disse falhar.
import puppeteer from "puppeteer-core";

const BASE = process.env.E2E_BASE || "http://localhost:5173";
const CHROME = process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const results = [];
const ok = (n, c) => results.push({ name: n, pass: !!c });
const fail = (n, e) => results.push({ name: n, pass: false, err: String(e).slice(0, 400) });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
const errs = [];
page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
page.on("pageerror", (e) => errs.push("PAGEERR " + String(e).slice(0, 300)));
page.on("response", (r) => { if (r.status() >= 400) errs.push(`HTTP ${r.status()} ${r.url()}`); });

try {
  await page.goto(BASE + "/#/catalogo", { waitUntil: "networkidle0", timeout: 45000 });
  await page.waitForSelector(".catalog-layout", { timeout: 20000 });
  await page.evaluate(() => { localStorage.removeItem("cotacao_draft_v1"); location.reload(); });
  await page.waitForSelector(".catalog-layout", { timeout: 20000 });

  await page.type("#fSearch", "lampada");
  await sleep(1500);
  await page.waitForSelector('.p-card[data-group] .p-pick', { timeout: 20000 });
  await page.click('.p-card[data-group] .p-pick');
  await page.waitForSelector("#mmMatriz", { timeout: 10000 });

  const freeInfo = await page.evaluate(() => {
    const f = document.querySelector("#mmMatriz .m-qty--free");
    return { exists: !!f, key: f ? f.dataset.key : "" };
  });
  ok(`célula livre presente (key=${freeInfo.key})`, freeInfo.exists);

  // preenche célula livre
  await page.evaluate(() => {
    const f = document.querySelector("#mmMatriz .m-qty--free");
    f.value = "3";
    f.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await sleep(300);

  // captura toast de erro antes do add
  page.evaluate(() => {
    window.__toastLast = null;
    const obs = new MutationObserver(() => {
      const toasts = [...document.querySelectorAll(".toast, .toast-item")]
        .map((t) => t.textContent.trim())
        .filter(Boolean);
      if (toasts.length) window.__toastLast = toasts[toasts.length - 1];
    });
    obs.observe(document.body, { childList: true, subtree: true });
  });

  await page.click("#mmAdd");
  await sleep(600);
  const toastAdd = await page.evaluate(() => window.__toastLast || "none");
  console.log("TOAST ADD:", toastAdd);

  const draft = await page.evaluate(() => {
    const d = JSON.parse(localStorage.getItem("cotacao_draft_v1") || '{"itens":{}}');
    return { itens: Object.keys(d.itens || {}).length, detalhes: Object.keys(d.detalhes || {}).length };
  });
  ok(`item livre no draft: itens=${draft.itens} detalhes=${draft.detalhes}`, draft.detalhes >= 1);

  // cria a cotação
  await page.click("#sbCriar");
  await page.waitForSelector("#btnConfirmarCriar", { timeout: 8000 });
  await page.click("#btnConfirmarCriar");
  await sleep(2500);

  const estado = await page.evaluate(() => ({ hash: location.hash, body: document.body.innerText.slice(0, 500) }));
  ok(`cotacao criada (hash=${estado.hash})`, /#\/cotacoes\/\d+/.test(estado.hash));
  if (!/#\/cotacoes\/\d+/.test(estado.hash)) {
    console.log("TOAST FINAL:", toastAdd, "\nBODY:\n", estado.body);
  }

  // renderiza o detalhe -> onde pode aparecer "Produto não existe"
  await page.waitForSelector(".compare-wrap, .empty-box", { timeout: 8000 }).catch(() => {});
  const detErrs = await page.evaluate(() => document.body.innerText.match(/Produto não .{0,30}|não existe.{0,30}/gi) || []);
  ok(`sem msg de produto inexistente no detalhe (${JSON.stringify(detErrs)})`, detErrs.length === 0);

  console.log("CONSOLE ERRS:\n" + errs.join("\n"));
  ok("sem erros de console/HTTP>=400", !errs.some((e) => e.includes("400") && !e.includes("favicon")));
} catch (e) {
  fail("SCRIPT", e);
} finally {
  await browser.close();
}

console.log("\n=== RESULTADOS ===");
let fails = 0;
for (const r of results) { console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.pass ? "" : "  (" + (r.err || "") + ")"}`); if (!r.pass) fails++; }
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);