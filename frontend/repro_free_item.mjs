// Reprodução: fluxo real de criar cotação com item livre (célula sem variante).
import puppeteer from "puppeteer-core";

const BASE = process.env.E2E_BASE || "http://localhost:5173";
const CHROME = process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const results = [];
const ok = (n, c) => results.push({ name: n, pass: !!c, err: c ? "" : "check fail" });
const fail = (n, e) => results.push({ name: n, pass: false, err: String(e).slice(0, 400) });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
const consoleErrs = [];
page.on("console", (msg) => { if (msg.type() === "error") consoleErrs.push(msg.text()); });
page.on("pageerror", (e) => consoleErrs.push(String(e).slice(0, 400)));
page.on("requestfailed", (r) => consoleErrs.push("REQFAIL " + r.url() + " :: " + r.failure()?.errorText));
page.on("response", (r) => {
  if (r.status() >= 400) consoleErrs.push(`HTTP ${r.status()} ${r.url()}`);
});

try {
  // limpa carrinho
  await page.goto(BASE + "/#/catalogo", { waitUntil: "networkidle0", timeout: 45000 });
  await page.waitForSelector(".catalog-layout", { timeout: 20000 });
  await page.evaluate(() => {
    localStorage.removeItem("cotacao_draft_v1");
    location.reload();
  });
  await page.waitForSelector(".catalog-layout", { timeout: 20000 });

  // acha grupo com busca
  await page.type("#fSearch", "lampada");
  await sleep(1500);
  await page.waitForSelector('.p-card[data-group] .p-pick', { timeout: 20000 });
  await page.click('.p-card[data-group] .p-pick');
  await page.waitForSelector("#mmMatriz", { timeout: 10000 });

  // lista células e quantos inputs livres existem
  const mtx = await page.evaluate(() => {
    const q = [...document.querySelectorAll("#mmMatriz .m-qty")];
    const cells = [...document.querySelectorAll("#mmMatriz .m-cell")];
    const freeInputs = q.filter((i) => i.dataset.free !== undefined || i.classList.contains('m-qty--free'));
    return { inputs: q.length, freeInputs: freeInputs.length, cells: cells.length, hasOutro: !!document.querySelector("#mmMatriz .m-outro") };
  });
  ok(`matriz: inputs=${mtx.inputs} livres=${mtx.freeInputs} outro=${mtx.hasOutro}`, mtx.hasOutro);

  // preenche célula livre (sem variante) — pega o 1º input livre; senão usa outro
  const filled = await page.evaluate(() => {
    const free = document.querySelector("#mmMatriz .m-qty--free");
    if (free) {
      free.value = "3";
      free.dispatchEvent(new Event("input", { bubbles: true }));
      return "cell";
    }
    // formulário outro valor
    const row = document.querySelector('#mmMatriz [data-outro="row"]');
    const qty = document.querySelector('#mmMatriz [data-outro="qty"]');
    if (row && qty) {
       row.value = "16mm";
       row.dispatchEvent(new Event("input", { bubbles: true }));
       qty.value = "2";
       qty.dispatchEvent(new Event("input", { bubbles: true }));
       return "outro";
    }
    return "none";
  });
  ok(`preenchi modo=${filled}`, filled !== "none");
  await sleep(300);

await page.click("#mmAdd");
await sleep(500);

  // cria a cotação via sidebar
  await page.click("#sbCriar");
  await page.waitForSelector("#btnConfirmarCriar", { timeout: 8000 });
  await page.click("#btnConfirmarCriar");
  await sleep(2500);

  const estado = await page.evaluate(() => ({ hash: location.hash, body: document.body.innerText.slice(0, 400) }));
  const okCriou = /#\/cotacoes\/\d+/.test(estado.hash);
  ok(`cotacao criada (hash=${estado.hash})`, okCriou);
  if (!okCriou) {
    fail("erros de console", errorsErrsStr(consoleErrs));
    console.log("BODY:", estado.body);
  }
  for (const e of consoleErrs) console.log("[console.error]", e);
  ok("sem erros no console", consoleErrs.length === 0);

} catch (e) {
  console.log("### FALHA GERAL ###", e);
  console.log("CONSOLE ERRS:", consoleErrs.join("\n"));
  fail("SCRIPT-EXEC", e);
} finally {
  await browser.close();
}

function errorsErrsStr(a){ return a.join("\n"); }

console.log("\n=== RESULTADOS ===");
let fails = 0;
for (const r of results) {
  console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.pass ? "" : "  (" + r.err + ")"}`);
  if (!r.pass) fails++;
}
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);