// Runner E2E: executa todos os e2e*.mjs em ordem, abortando na 1ª falha.
import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const scripts = readdirSync(here)
  .filter((f) => /^e2e[a-z0-9_]*\.mjs$/.test(f) && f !== "e2e_runner.mjs")
  .sort();

console.log(`\n>>> Suite E2E (${scripts.length} scripts)\n`);
let failed = 0;
for (const s of scripts) {
  const t0 = Date.now();
  console.log(`── ▶ ${s}`);
  try {
    execFileSync(process.execPath, [join(here, s)], { stdio: "inherit", cwd: here });
    console.log(`✔ ${s} · ${((Date.now() - t0) / 1000).toFixed(1)}s\n`);
  } catch (e) {
    failed++;
    console.log(`✘ ${s} FALHOU (${((Date.now() - t0) / 1000).toFixed(1)}s)\n`);
    process.exit(1);
  }
}
console.log(`\nTODOS OS ${scripts.length} SCRIPTS PASSARAM${failed ? "" : ""} ✔`);
process.exit(failed ? 1 : 0);