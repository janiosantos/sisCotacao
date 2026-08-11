// E2E compras: fluxo completo 1→4 (busca, lista, cotação, respostas, matriz, pedidos).
import puppeteer from "puppeteer-core";
import { login } from "./e2e_auth.mjs";

const BASE = "http://localhost:5173";
const API = "http://localhost:8000";
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
  await page.goto(BASE + "/#/compras", { waitUntil: "networkidle0", timeout: 45000 });
  await page.waitForSelector("#cprBody", { timeout: 15000 });

  // limpa estado e inicia nova compra
  await page.click("#cprNova");
  await sleep(600);
  await page.waitForSelector("#cprQ", { timeout: 10000 });
  ok("compras: etapa 1 renderiza busca", true);

  // busca + adiciona 2 itens do resultado
  await page.type("#cprQ", "cabo");
  await page.waitForSelector("#cprResult [data-add]", { timeout: 15000 });
  const n1 = await page.$$eval("#cprResult [data-add]", (els) => els.length);
  if (n1 > 0) {
    await page.click("#cprResult [data-add]");
    await sleep(400);
  }
  const badges = await page.$eval("#cprNItens", (el) => el.textContent);
  ok(`compras: item adicionado à lista (${badges})`, Number(badges) >= 1);

  // avança para etapa 2
  await page.click("#cprProx1");
  await sleep(800);
  const etapa2 = await page.$eval("#cprStepper .cpr-step.is-cur", (el) => el.textContent).then((t) => t.includes("Cotando"));
  ok("compras: avança para etapa 2 (cotando)", etapa2);

  // seleciona um fornecedor e dispara
  const fornCheck = await page.$$("#cprForn input[type=checkbox]");
  if (fornCheck.length > 0) {
    await page.click("#cprForn input[type=checkbox]:first-child");
    await page.click("#cprDisparar");
    await sleep(2500);
  }
  const links = await page.evaluate(() => {
    const box = document.querySelector("#cprLinks");
    if (!box) return [];
    return [...box.querySelectorAll(".cpr-linkcard")].map((a) => a.textContent.trim().slice(0, 40));
  }).catch(() => []);
  const disparou = links.length > 0;
  ok(`compras: dispara cotação e mostra links (${links.length})`, disparou);

  // pega o token do portal nos dados retornados (via API)
  const cotId = await page.evaluate(() => sessionStorage.getItem("compras_cotacao"));
  ok(`compras: cotação criada (id=${cotId})`, !!cotId);

  // obtém invites/tokens via API
  let token = null;
  let itemIds = [];
  if (cotId) {
    const invites = await (await fetch(API + `/api/compras/cotacoes/${cotId}/invites`)).json();
    token = invites[0]?.token || null;
    const ctx = await (await fetch(API + "/api/fornecedor/" + token)).json();
    itemIds = (ctx.itens || []).map((i) => i.cotacao_item_id);
  }
  ok(`compras: invite/token disponível (${!!token}, ${itemIds.length} itens)`, !!token && itemIds.length > 0);

  // simula resposta do fornecedor via portal
  if (token && itemIds.length) {
    const okApi = await (await fetch(API + `/api/fornecedor/${token}/proposta`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ precos: itemIds.map((cii) => ({ cotacao_item_id: cii, preco_unitario: 12.5, prazo_entrega_dias: 7 })) }),
    })).json();
    ok(`fornecedor responde proposta (${okApi.ok})`, !!okApi.ok);

    // volta pra UI, recarrega a matriz
    await page.reload({ waitUntil: "networkidle0" });
    await sleep(3000);
    const etapa3 = await page.evaluate(() => {
      const step = document.querySelector("#cprStepper .cpr-step.is-cur");
      if (step && step.textContent.includes("Comparando")) {
        return { etapa: 3, temMatriz: !!document.querySelector(".cpr-matriz"), temGerar: !!document.querySelector("#cprGerarPedidos") };
      }
      return { etapa: -1, temMatriz: false, temGerar: false };
    });
    ok(`compras: etapa 3 matriz (etapa=${etapa3.etapa}, matriz=${etapa3.temMatriz}, gerar=${etapa3.temGerar})`, etapa3.etapa === 3 && etapa3.temMatriz && etapa3.temGerar);

    // gera pedidos → etapa 4
    if (etapa3.temGerar) {
      await page.click("#cprGerarPedidos");
      await sleep(3000);
      const ped = await page.evaluate(() => ({
        etapa: document.querySelector("#cprStepper .cpr-step.is-cur")?.textContent || "",
        temPedidos: !!document.querySelector("#cprPedidos"),
        pedidos: document.querySelectorAll("#cprPedidos .cpr-pedido").length,
      }));
      ok(`compras: gera pedidos → etapa 4 (${ped.etapa.trim().slice(0, 20)}, ${ped.pedidos} pedidos)`, /Pedido/.test(ped.etapa) && ped.pedidos >= 1);
    }
  }
} catch (e) {
  console.log("### FALHA GERAL ###", e);
  fail("SCRIPT-EXEC", e);
} finally {
  await browser.close();
}

console.log("\n=== RESULTADOS COMPRAS 1→4 ===");
let fails = 0;
for (const r of results) { console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.pass ? "" : " — " + r.err}`); if (!r.pass) fails++; }
console.log(`\nTOTAL ${results.length} · FALHAS ${fails}`);
process.exit(fails ? 1 : 0);