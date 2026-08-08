import puppeteer from "puppeteer-core";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new" });
const page = await browser.newPage();
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 300)));

await page.goto("http://localhost:5173/#/cotacoes/17", { waitUntil: "networkidle0", timeout: 45000 });
await new Promise((r) => setTimeout(r, 1500));

await page.click("#btnImportarIA");
await page.waitForSelector(".modal", { timeout: 8000 }).catch(() => {});
const ia = await page.evaluate(() => ({
  modal: !!document.querySelector(".modal"),
  text: document.querySelector(".modal")?.textContent?.slice(0, 200),
}));
console.log("MODAL IA:", JSON.stringify(ia, null, 1));

await page.evaluate(() => document.querySelector(".modal [data-close]")?.click());
await new Promise((r) => setTimeout(r, 400));

const hasEdit = await page.$("#btnEditar");
if (hasEdit) {
  await page.click("#btnEditar");
  await page.waitForSelector(".modal", { timeout: 5000 }).catch(() => {});
  const ed = await page.evaluate(() => ({
    modal: !!document.querySelector(".modal"),
    txt: document.querySelector(".modal")?.textContent?.slice(0, 150),
  }));
  console.log("MODAL EDITAR:", JSON.stringify(ed, null, 1));
} else {
  console.log("SEM BOTAO EDITAR");
}
await browser.close();