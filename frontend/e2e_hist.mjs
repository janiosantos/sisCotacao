import puppeteer from "puppeteer-core";
const browser = await puppeteer.launch({ executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", headless: "new" });
const page = await browser.newPage();
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 300)));

await page.goto("http://localhost:5173/#/historico", { waitUntil: "networkidle0", timeout: 45000 });
await new Promise((r) => setTimeout(r, 1500));
await page.type("#fBusca", "cabo");
await new Promise((r) => setTimeout(r, 700));
const sug = await page.$$eval("#fSugestoes [data-id]", (els) => els.length);
console.log("SUGESTOES:", sug);
if (sug) {
  await page.click("#fSugestoes [data-id]:first-child");
  await new Promise((r) => setTimeout(r, 2500));
  const res = await page.evaluate(() => ({
    temSvg: !!document.querySelector("#resultado svg"),
    temTabela: !!document.querySelector("#resultado table"),
    rows: document.querySelectorAll("#resultado tbody tr").length,
    text: document.querySelector("#resultado")?.textContent?.slice(0, 100),
  }));
  console.log("RESULTADO:", JSON.stringify(res, null, 1));
}
await browser.close();