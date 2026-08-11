// Varre busca de produtos para achar um grupo com células vazias (sem variante).
import puppeteer from "puppeteer-core";

const BASE = process.env.E2E_BASE || "http://localhost:5173";
const CHROME = process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const termos = ["cabo flexivel 750v", "cabo flexivel", "cabos"];

try {
  await page.goto(BASE + "/#/catalogo", { waitUntil: "networkidle0", timeout: 45000 });
  await page.waitForSelector(".catalog-layout", { timeout: 20000 });

  let foundVazia = false;
  for (const t of termos) {
    await page.evaluate(() => { const i = document.querySelector("#fSearch"); if (i) { i.value = ""; } });
    await sleep(400);
    await page.type("#fSearch", t);
    await sleep(1500);
    const n = await page.$$eval(".p-card", (els) => els.length);
    const groups = await page.$$eval('.p-card[data-group]', (els) => els.map((e) => ({ id: e.dataset.group, txt: (e.querySelector(".p-name")||{}).textContent })));
    for (const g of groups) {
      await page.click(`.p-card[data-group="${g.id}"] .p-pick`);
      await sleep(1500);
      const info = await page.evaluate(() => {
        const cnt = document.querySelectorAll(".m-qty--free").length;
        const tabs = [...document.querySelectorAll(".m-brand-tab")].map((b) => b.textContent);
        const rows = [...document.querySelectorAll("#mmMatriz tbody tr")].map((tr) => [...tr.querySelectorAll("td")].map((td) => td.textContent.trim()).join(" | ")).join("\n");
        const hasOutro = !!document.querySelector("#mmMatriz .m-outro");
        const freeVals = [...document.querySelectorAll(".m-qty--free")].map((i) => i.closest("td")?.textContent.trim());
        return { cnt, tabs, hasOutro, rows, freeVals };
      });
      console.log(`\n>>> termo="${t}" grupo=${g.id} free=${info.cnt} outro=${info.hasOutro}\n  tabs=${JSON.stringify(info.tabs)}\n  linhas:\n` + info.rows.split("\n").map((l) => "    " + l).join("\n"));
      await page.click("[data-close]");
      await sleep(500);
      if (info.cnt > 0 || info.hasOutro) { foundVazia = true; }
    }
    await page.evaluate(() => { const i = document.querySelector("#fSearch"); i.value=""; i.dispatchEvent(new Event("input", {bubbles:true})); });
    await sleep(400);
  }
  console.log("found=" + foundVazia);
} finally {
  await browser.close();
}