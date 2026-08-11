import puppeteer from "puppeteer-core";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
import { login } from "./e2e_auth.mjs";

const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
page.on("console", (msg) => { if (msg.type() === "error") console.log("[CONSOLE]", msg.text().slice(0, 300)); });
page.on("pageerror", (err) => console.log("[PAGE_ERROR]", err.message.slice(0, 300)));
await page.setViewport({ width: 1280, height: 900 });
await login(page);

// Financeiro - Condições
await page.goto("http://localhost:5173/#/financeiro", { waitUntil: "networkidle0", timeout: 30000 });
await new Promise((r) => setTimeout(r, 1500));
// Clica na aba Condições
const btns = await page.$$(".tab-btn");
for (const btn of btns) {
  const text = await page.evaluate((el) => el.textContent, btn);
  if (text.includes("Condições")) { await btn.click(); break; }
}
await new Promise((r) => setTimeout(r, 2000));
let html = await page.evaluate(() => document.querySelector("#finContent")?.innerHTML?.slice(0, 1000) || "");
console.log("CONDICOES:", html.substring(0, 500));

// Fiscal - NF-e
await page.goto("http://localhost:5173/#/fiscal", { waitUntil: "networkidle0", timeout: 30000 });
await new Promise((r) => setTimeout(r, 1500));
const fiscBtns = await page.$$(".tab-btn");
for (const btn of fiscBtns) {
  const text = await page.evaluate((el) => el.textContent, btn);
  if (text.includes("NF-e")) { await btn.click(); break; }
}
await new Promise((r) => setTimeout(r, 2000));
html = await page.evaluate(() => document.querySelector("#fiscContent")?.innerHTML?.slice(0, 1000) || "");
console.log("NFE:", html.substring(0, 500));

await browser.close();
