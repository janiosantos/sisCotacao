// pages/dashboard.ts — painel de indicadores do ERP.
import { api } from "../api/client";
import { escapeHtml, fmtMoney } from "../ui/format";

interface DashboardData {
  resumo: {
    hoje: string;
    vendas_hoje: { n: number; total: number };
    vendas_mes: { n: number; total: number };
    receber_a_vencer: number;
    receber_vencidas: number;
    pagar_a_vencer: number;
    estoque_baixo: number;
    valor_estoque: number;
  };
  estoque_baixo: { variante_id: number; nome: string; sku: string; quantidade: number; estoque_minimo: number; deposito: string }[];
  top_vendas: { nome: string; sku: string; qtd: number; receita: number }[];
}

function card(titulo: string, valor: string, extra = "", tom = ""): string {
  return `
    <div class="dash-card ${tom}">
      <span class="dash-card-titulo">${titulo}</span>
      <span class="dash-card-valor">${valor}</span>
      ${extra ? `<span class="dash-card-extra">${extra}</span>` : ""}
    </div>`;
}

export async function render($app: HTMLElement): Promise<void> {
  $app.innerHTML = `<div class="loading">Carregando painel…</div>`;
  let d: DashboardData;
  let reposicao: { variante_id: number; nome: string; sku: string; unidade_venda: string; quantidade: number; estoque_minimo: number; estoque_maximo: number; custo: number | null; sugestao_qtd: number; custo_total: number }[] = [];
  let comissoes: { id: number; nome: string; comissao_pct: number; n_vendas: number; total_vendas: number; comissao: number }[] = [];
  try {
    d = await api.requestDashboard();
    [reposicao, comissoes] = await Promise.all([
      api.reposicaoSugerida() as Promise<typeof reposicao>,
      api.comissoes() as Promise<typeof comissoes>,
    ]);
  } catch (e) {
    $app.innerHTML = `<div class="empty-box"><p>Erro ao carregar o painel: ${escapeHtml((e as Error).message)}</p></div>`;
    return;
  }
  const r = d.resumo;
  const top = d.top_vendas.map((t, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${escapeHtml(t.nome)}</strong>${t.sku ? `<div style="font-size:11px;color:var(--ink-faint);font-family:var(--font-mono);">${escapeHtml(t.sku)}</div>` : ""}</td>
      <td class="num">${t.qtd}</td>
      <td class="num">${fmtMoney(t.receita)}</td>
    </tr>`).join("");
  const baixo = d.estoque_baixo.map((s) => `
    <tr>
      <td><strong>${escapeHtml(s.nome)}</strong>${s.sku ? `<div style="font-size:11px;color:var(--ink-faint);font-family:var(--font-mono);">${escapeHtml(s.sku)}</div>` : ""}</td>
      <td class="num">${s.quantidade}</td>
      <td class="num">${s.estoque_minimo}</td>
      <td>${escapeHtml(s.deposito || "—")}</td>
    </tr>`).join("");
  const rep = reposicao.map((p) => `
    <tr>
      <td><strong>${escapeHtml(p.nome)}</strong>${p.sku ? `<div style="font-size:11px;color:var(--ink-faint);font-family:var(--font-mono);">${escapeHtml(p.sku)}</div>` : ""}</td>
      <td class="num">${p.quantidade}</td>
      <td class="num">${p.estoque_minimo}</td>
      <td class="num">${p.sugestao_qtd}</td>
      <td class="num">${p.custo != null ? fmtMoney(p.custo_total) : "—"}</td>
    </tr>`).join("");
  const com = comissoes.map((c) => `
    <tr>
      <td>${escapeHtml(c.nome)}</td>
      <td class="num">${c.n_vendas}</td>
      <td class="num">${fmtMoney(c.total_vendas)}</td>
      <td class="num">${c.comissao_pct}%</td>
      <td class="num"><strong>${fmtMoney(c.comissao)}</strong></td>
    </tr>`).join("");

  $app.innerHTML = `
    <div class="page-head">
      <div>
        <h1 class="page-title">Painel</h1>
        <p class="page-sub">Indicadores do negócio — atualizados em ${escapeHtml(r.hoje)}.</p>
      </div>
      <a class="btn btn--accent" href="#/pdv">+ Venda no PDV</a>
    </div>

    <div class="dash-grid">
      ${card("Vendas hoje", fmtMoney(r.vendas_hoje.total), `${r.vendas_hoje.n} pedido(s)`)}
      ${card("Vendas no mês", fmtMoney(r.vendas_mes.total), `${r.vendas_mes.n} pedido(s)`, "dash-card--destaque")}
      ${card("A receber (a vencer)", fmtMoney(r.receber_a_vencer))}
      ${card("A receber (vencido)", fmtMoney(r.receber_vencidas), "", r.receber_vencidas > 0 ? "dash-card--alerta" : "")}
      ${card("A pagar (a vencer)", fmtMoney(r.pagar_a_vencer))}
      ${card("Valor em estoque", fmtMoney(r.valor_estoque))}
    </div>

    ${r.estoque_baixo > 0 ? `<p class="dash-alerta">⚠ ${r.estoque_baixo} produto(s) abaixo do estoque mínimo.</p>` : ""}

    <div class="dash-colunas">
      <section class="dash-sec">
        <h3>Mais vendidos (30 dias)</h3>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>#</th><th>Produto</th><th class="num">Qtd</th><th class="num">Receita</th></tr></thead>
          <tbody>${top || `<tr><td colspan="4" class="pdv-sem-res">Sem vendas no período</td></tr>`}</tbody>
        </table></div>
      </section>
      <section class="dash-sec">
        <h3>Estoque abaixo do mínimo</h3>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>Produto</th><th class="num">Atual</th><th class="num">Mínimo</th><th>Depósito</th></tr></thead>
          <tbody>${baixo || `<tr><td colspan="4" class="pdv-sem-res">Nenhum produto abaixo do mínimo</td></tr>`}</tbody>
        </table></div>
      </section>
    </div>

    <div class="dash-colunas" style="margin-top:16px;">
      <section class="dash-sec">
        <h3>Reposição sugerida (compras)</h3>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>Produto</th><th class="num">Atual</th><th class="num">Mínimo</th><th class="num">Sugerido</th><th class="num">Custo est.</th></tr></thead>
          <tbody>${rep || `<tr><td colspan="5" class="pdv-sem-res">Nada a repor</td></tr>`}</tbody>
        </table></div>
      </section>
      <section class="dash-sec">
        <h3>Comissões de vendedores (30 dias)</h3>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>Vendedor</th><th class="num">Vendas</th><th class="num">Total</th><th class="num">%</th><th class="num">Comissão</th></tr></thead>
          <tbody>${com || `<tr><td colspan="5" class="pdv-sem-res">Sem comissões no período</td></tr>`}</tbody>
        </table></div>
      </section>
    </div>
  `;
}
