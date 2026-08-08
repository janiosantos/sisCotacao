// pages/historico.ts — histórico e evolução de preços por produto.

import { api, type HistoricoPreco, type ProdutoComHistorico } from "../api/client";
import { escapeHtml, fmtDate, fmtDateTime, fmtMoney } from "../ui/format";

const CORES = ["#C6871E", "#3C5468", "#35553B", "#A8432A", "#6B4A8F", "#1B7A8C", "#8F5F13", "#556B2F"];

export async function render($app: HTMLElement): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando…</div>`;
  let codigos: ProdutoComHistorico[] = [];
  try {
    codigos = await api.produtosComHistorico();
  } catch {
    /* página segue vazia se a API falhar */
  }

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Histórico de preços</h1>
        <p class="page-sub">Evolução de preço por fornecedor ao longo do tempo, com base nas cotações lançadas.</p>
      </div>
    </div>

    ${codigos.length === 0 ? `
      <div class="empty-box"><p>Ainda sem histórico</p><p>Assim que preços forem lançados em cotações, eles aparecem aqui.</p></div>
    ` : `
      <div class="toolbar">
        <div class="field" style="flex:1;min-width:260px;position:relative;">
          <label>Produto</label>
          <input id="fBusca" type="text" placeholder="Buscar por código ou descrição…" autocomplete="off">
          <div id="fSugestoes" style="position:absolute;top:100%;left:0;right:0;background:var(--bg-panel);border:1px solid var(--line);border-radius:0 0 3px 3px;max-height:260px;overflow-y:auto;z-index:10;display:none;"></div>
        </div>
      </div>
      <div id="resultado"></div>
    `}
  `;

  if (codigos.length === 0) return;

  const $busca = $app.querySelector<HTMLInputElement>("#fBusca")!;
  const $sug = $app.querySelector<HTMLElement>("#fSugestoes")!;
  $busca.addEventListener("input", () => {
    const q = $busca.value.trim().toLowerCase();
    if (!q) {
      $sug.style.display = "none";
      return;
    }
    const matches = codigos
      .filter((c) => (c.sku + " " + c.name).toLowerCase().includes(q))
      .slice(0, 20);
    $sug.innerHTML =
      matches
        .map(
          (c) => `
            <div class="sug-item" data-id="${c.id}" style="padding:8px 10px;font-size:12.5px;cursor:pointer;border-bottom:1px solid var(--line);">
              <span style="font-family:var(--font-mono);color:var(--steel);">${escapeHtml(c.sku || "#" + c.id)}</span> — ${escapeHtml(c.name)}
            </div>`
        )
        .join("") || `<div style="padding:8px 10px;font-size:12.5px;color:var(--ink-faint);">Nada encontrado</div>`;
    $sug.style.display = "block";
    $sug.querySelectorAll<HTMLElement>("[data-id]").forEach((el) => {
      el.addEventListener("mouseenter", () => (el.style.background = "var(--bg)"));
      el.addEventListener("mouseleave", () => (el.style.background = ""));
      el.addEventListener("click", () => {
        $busca.value = el.dataset.id!;
        $sug.style.display = "none";
        void carregarProduto($app, Number(el.dataset.id));
      });
    });
  });
  document.addEventListener("click", (e) => {
    if (!$sug.contains(e.target as Node) && e.target !== $busca) $sug.style.display = "none";
  });
}

async function carregarProduto($app: HTMLElement, produtoId: number): Promise<void> {
  const $resultado = $app.querySelector<HTMLElement>("#resultado");
  if (!$resultado) return;
  $resultado.innerHTML = `<div class="loading">Carregando histórico…</div>`;
  let rows: HistoricoPreco[] = [];
  try {
    rows = await api.historicoPrecos(produtoId);
  } catch {
    /* tabela vazia abaixo */
  }
  if (rows.length === 0) {
    $resultado.innerHTML = `<div class="empty-box"><p>Sem lançamentos</p><p>Esse produto ainda não tem preços registrados.</p></div>`;
    return;
  }

  const porFornecedor: Record<string, HistoricoPreco[]> = {};
  for (const r of rows) {
    (porFornecedor[r.fornecedor_nome] ??= []).push(r);
  }
  const fornecedorNomes = Object.keys(porFornecedor);
  const cores = Object.fromEntries(fornecedorNomes.map((n, i) => [n, CORES[i % CORES.length]]));

  $resultado.innerHTML = `
    <div class="chart-wrap">
      ${buildChart(porFornecedor, cores)}
      <div class="chart-legend">
        ${fornecedorNomes
          .map(
            (n) => `
              <div class="chart-legend-item">
                <span class="chart-legend-swatch" style="background:${cores[n]};"></span>
                ${escapeHtml(n)}
                ${variacaoLabel(porFornecedor[n])}
              </div>`
          )
          .join("")}
      </div>
    </div>

    <div class="table-wrap" style="margin-top:16px;">
      <table class="data-table">
        <thead><tr><th>Data</th><th>Fornecedor</th><th>Cotação</th><th>Preço</th><th>Prazo</th></tr></thead>
        <tbody>
          ${rows
            .slice()
            .reverse()
            .map(
              (r) => `
                <tr>
                  <td>${fmtDateTime(r.registrado_em)}</td>
                  <td>${escapeHtml(r.fornecedor_nome)}</td>
                  <td><a href="#/cotacoes/${r.cotacao_id}" style="font-family:var(--font-mono);">${r.cotacao_numero}</a></td>
                  <td style="font-family:var(--font-mono);">${fmtMoney(r.preco_unitario)}</td>
                  <td>${r.prazo_entrega_dias ? r.prazo_entrega_dias + " dias" : "—"}</td>
                </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function variacaoLabel(pontos: HistoricoPreco[]): string {
  if (pontos.length < 2) return "";
  const primeiro = pontos[0].preco_unitario;
  const ultimo = pontos[pontos.length - 1].preco_unitario;
  const delta = ((ultimo - primeiro) / primeiro) * 100;
  const sinal = delta > 0 ? "+" : "";
  const cor = delta > 0 ? "var(--danger)" : delta < 0 ? "var(--green)" : "var(--ink-faint)";
  return `<span style="color:${cor};font-family:var(--font-mono);font-size:11px;margin-left:4px;">(${sinal}${delta.toFixed(1)}%)</span>`;
}

function buildChart(porFornecedor: Record<string, HistoricoPreco[]>, cores: Record<string, string>): string {
  const W = 760,
    H = 260,
    PAD_L = 55,
    PAD_B = 30,
    PAD_T = 16,
    PAD_R = 16;
  const allPontos = Object.values(porFornecedor).flat();
  const precos = allPontos.map((p) => p.preco_unitario);
  let min = Math.min(...precos),
    max = Math.max(...precos);
  if (min === max) {
    min *= 0.9;
    max *= 1.1;
  }
  const pad = (max - min) * 0.1;
  min -= pad;
  max += pad;

  const datas = [...new Set(allPontos.map((p) => p.registrado_em))].sort();
  const xFor = (data: string) => {
    const idx = datas.indexOf(data);
    const n = Math.max(datas.length - 1, 1);
    return PAD_L + (idx / n) * (W - PAD_L - PAD_R);
  };
  const yFor = (preco: number) => PAD_T + (1 - (preco - min) / (max - min)) * (H - PAD_T - PAD_B);

  const gridLines = 4;
  let gridHtml = "";
  for (let i = 0; i <= gridLines; i++) {
    const v = min + ((max - min) * i) / gridLines;
    const y = yFor(v);
    gridHtml += `<line x1="${PAD_L}" y1="${y}" x2="${W - PAD_R}" y2="${y}" stroke="var(--line)" stroke-width="1"/>`;
    gridHtml += `<text x="${PAD_L - 8}" y="${y + 4}" text-anchor="end" font-size="10" font-family="var(--font-mono)" fill="var(--ink-faint)">${v.toFixed(2)}</text>`;
  }

  let linesHtml = "";
  for (const [nome, pontos] of Object.entries(porFornecedor)) {
    const sorted = pontos.slice().sort((a, b) => (a.registrado_em > b.registrado_em ? 1 : -1));
    const pts = sorted.map((p) => `${xFor(p.registrado_em)},${yFor(p.preco_unitario)}`).join(" ");
    linesHtml += `<polyline points="${pts}" fill="none" stroke="${cores[nome]}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    for (const p of sorted) {
      linesHtml += `<circle cx="${xFor(p.registrado_em)}" cy="${yFor(p.preco_unitario)}" r="3.5" fill="${cores[nome]}"><title>${escapeHtml(nome)}: ${fmtMoney(p.preco_unitario)}</title></circle>`;
    }
  }

  const xLabels = datas.length <= 6 ? datas : [datas[0], datas[Math.floor(datas.length / 2)], datas[datas.length - 1]];
  const xLabelsHtml = xLabels
    .map(
      (d) => `<text x="${xFor(d)}" y="${H - 8}" text-anchor="middle" font-size="10" font-family="var(--font-mono)" fill="var(--ink-faint)">${fmtDate(d)}</text>`
    )
    .join("");

  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;" role="img" aria-label="Gráfico de evolução de preços">
    ${gridHtml}
    ${linesHtml}
    ${xLabelsHtml}
  </svg>`;
}