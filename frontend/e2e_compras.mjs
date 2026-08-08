import puppeteer from "puppeteer-core";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new" });
const page = await browser.newPage();
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 300)));
page.on("console", (m) => { if (m.type() === "error") console.log("[console]", m.text().slice(0, 200)); });

// --- Compras: abrir cotação 17 direto (compras_cotacao sessionStorage) ---
await page.goto("http://localhost:5173/#/compras", { waitUntil: "networkidle0", timeout: 45000 });
await page.evaluate(() => sessionStorage.setItem("compras_cotacao", "17"));
await page.reload({ waitUntil: "networkidle0" });
await new Promise((r) => setTimeout(r, 2500));

const compras = await page.evaluate(() => ({
  etapa: document.querySelector("#cprStepper .cpr-step.is-cur")?.textContent?.trim() || "",
  body: document.querySelector("#cprBody")?.textContent?.slice(0, 150) || "",
}));
console.log("COMPRAS com cotacao 17:", JSON.stringify(compras, null, 1));

// Tenta avançar etapas conforme botões visíveis
const botoes = await page.evaluate(() => [...document.querySelectorAll("#cprBody button")].map((b) => ({ id: b.id, txt: b.textContent.trim().slice(0, 40) })));
console.log("BOTOES COMPRAS:", JSON.stringify(botoes, null, 1));
await browser.close();