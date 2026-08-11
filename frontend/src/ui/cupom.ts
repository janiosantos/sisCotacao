// ui/cupom.ts — cupom de orçamento para impressora térmica (58/80mm) via window.print().
import type { OrcamentoDetalhe, OrcamentoItemPayload } from "../api/client";
import { escapeHtml, fmtDateTime, fmtMoney } from "./format";

function linhasItem(i: OrcamentoItemPayload): string {
  const sub = i.subtotal ?? i.preco_unitario * i.quantidade;
  const nome = escapeHtml(i.nome || "Item");
  const extra = [i.sku, i.marca, i.especificacao].filter(Boolean).map(escapeHtml).join(" · ");
  return `
    <div class="ck-item">
      <div class="ck-item-nome">
        <span>${i.quantidade} x ${nome}</span>
        <span class="ck-preco">${fmtMoney(sub)}</span>
      </div>
      ${extra ? `<div class="ck-item-extra">${extra}</div>` : ""}
    </div>`;
}

export function gerarCupomHtml(d: OrcamentoDetalhe): string {
  const itens = d.itens.map(linhasItem).join("");
  return `
    <div class="ck-cupom">
      <div class="ck-central">COTAÇÕES</div>
      <div class="ck-central ck-negrito">ORÇAMENTO ${escapeHtml(d.numero)}</div>
      <hr class="ck-hr">
      <div><span class="ck-r">Cliente:</span> <b>${escapeHtml(d.cliente || "—")}</b></div>
      ${d.contato ? `<div><span class="ck-r">Contato:</span> ${escapeHtml(d.contato)}</div>` : ""}
      <div><span class="ck-r">Data:</span> ${fmtDateTime(d.criado_em)}</div>
      <div><span class="ck-r">Validade:</span> ${d.validade_dias} dia(s)</div>
      <hr class="ck-hr">
      ${itens}
      <hr class="ck-hr">
      <div class="ck-total-linha"><span>Subtotal</span><span>${fmtMoney(d.subtotal)}</span></div>
      <div class="ck-total-linha"><span>Desconto</span><span>-${fmtMoney(d.desconto)}</span></div>
      <div class="ck-total-linha ck-grande"><b>TOTAL</b><b>${fmtMoney(d.total)}</b></div>
      ${d.observacoes ? `<hr class="ck-hr"><div class="ck-obs">${escapeHtml(d.observacoes)}</div>` : ""}
      <hr class="ck-hr">
      <div class="ck-rodape ck-central">Obrigado pela preferência!</div>
    </div>`;
}

export function imprimirCupom(d: OrcamentoDetalhe): void {
  const antigo = document.getElementById("print-area");
  if (antigo) antigo.remove();
  const el = document.createElement("div");
  el.id = "print-area";
  el.className = "print-area";
  el.innerHTML = gerarCupomHtml(d);
  document.body.appendChild(el);
  window.focus();
  window.print();
  el.remove();
}