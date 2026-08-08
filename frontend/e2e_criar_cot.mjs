import puppeteer from "puppeteer-core";
const browser = await puppeteer.launch({ executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", headless: "new" });
const page = await browser.newPage();
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 300)));
page.on("console", (m) => { if (m.type() === "error") console.log("[console]", m.text().slice(0, 200)); });

// monta carrinho no localStorage antes de carregar
await page.goto("http://localhost:5173/#/catalogo", { waitUntil: "networkidle0", timeout: 45000 });
await page.evaluate(() => {
  localStorage.setItem("cotacao_draft_v1", JSON.stringify({
    itens: { 1891: 2, 1894: 1 },
    detalhes: {
      1891: { id: 1891, name: "Cavalete 3T", price: 303.53 },
      1894: { id: 1894, name: "Cavalete 5T", price: 254.44 },
    },
  }));
});
await page.reload({ waitUntil: "networkidle0" });
await new Promise((r) => setTimeout(r, 1500));

const sidebar = await page.evaluate(() => ({
  total: document.querySelector("#sbTotal")?.textContent,
  count: document.querySelector("#sbInfo")?.textContent,
}));
console.log("SIDEBAR:", JSON.stringify(sidebar));

// clica em Criar cotação
await page.click("#sbCriar");
await page.waitForSelector(".modal", { timeout: 8000 });
const modal = await page.evaluate(() => ({
  temTitulo: !!document.querySelector("#mTitulo"),
  temCliente: !!document.querySelector("#mCliente"),
  temObs: !!document.querySelector("#mObs"),
  fornecedores: document.querySelectorAll('.modal input[name="fornecedor"]').length,
  confirmar: !!document.querySelector("#btnConfirmarCriar"),
  texto: document.querySelector(".modal")?.textContent?.slice(0, 120),
}));
console.log("MODAL CRIAR:", JSON.stringify(modal, null, 1));

if (modal.fornecedores > 0) {
  // seleciona o primeiro fornecedor e cria
  await page.click('.modal input[name="fornecedor"]:first-child');
  await page.type("#mTitulo", "E2E via carrinho");
  await page.click("#btnConfirmarCriar");
  await new Promise((r) => setTimeout(r, 3000));
  const res = await page.evaluate(() => ({
    hash: location.hash,
    emptyDraft: JSON.parse(localStorage.getItem("cotacao_draft_v1") || "{}").itens,
  }));
  console.log("APOS CRIAR:", JSON.stringify(res, null, 1));
}
await browser.close();