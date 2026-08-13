import "../styles/pdv.css";
import { api, type Cliente, type OrcamentoItemPayload, type ProdutoResumo } from "../api/client";
import { escapeHtml, fmtDate, fmtMoney } from "../ui/format";
import { closeModal, confirmDialog, openModal, toast } from "../ui/dom";
import { usuarioCorrente } from "./login";

interface LinhaPdv {
  produto_id: number | null;
  sku: string;
  nome: string;
  marca: string;
  especificacao: string;
  unidade: string;
  ncm: string;
  quantidade: number;
  preco_unitario: number;
  desconto_percentual: number;
  desconto_modo: "pct" | "valor";
  subtotal: number;
}

const VALIDADE_PADRAO = 7;

let currentApp: HTMLElement | null = null;
let linhas: LinhaPdv[] = [];
let sugestoes: ProdutoResumo[] = [];
let focoLista = -1;
let qtdDigitada = 1;

let clientesSug: Cliente[] = [];
let focoCliente = -1;

let vCliente = "";
let vClienteId: number | null = null;
let vContato = "";
let vValidade = String(VALIDADE_PADRAO);
let vObs = "";
let vDesconto = "";
let vDescModo: "pct" | "valor" = "valor";
let editandoId: number | null = null;
let editandoNumero = "";

// Quando o PDV é montado dentro do shell legacy (PdvPage), o cabeçalho
// próprio (.page-head) é omitido — o título/sidebar vêm do chrome externo.
let ocultarCabecalho = false;
export function setOcultarCabecalho(v: boolean): void {
  ocultarCabecalho = v;
}

const STATUS_EDITAVEIS = new Set(["rascunho", "ativo", "em_analise", "liberado"]);

export async function render($app: HTMLElement): Promise<void> {
  currentApp = $app;
  vCliente = sessionStorage.getItem("pdv_cliente") || "";
  linhas = [];
  paint();
  await carregarRecentes($app);
  try {
    const conds = await api.listarCondicoes();
    const sel = document.querySelector<HTMLSelectElement>("#pdvCondicao");
    if (sel) {
      conds.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = String(c.id); opt.textContent = c.nome;
        sel.appendChild(opt);
      });
    }
  } catch { /* */ }
  setTimeout(focoInicial, 0);
}

function focoInicial(): void {
  const c = currentApp?.querySelector<HTMLInputElement>("#pdvCliente");
  c?.focus();
}

function parseBusca(v: string): { qtd: number; termo: string } {
  const m = v.trim().match(/^(\d+(?:[.,]\d+)?)\s*\*+\s*([\s\S]*)$/);
  if (!m) return { qtd: 1, termo: v.trim() };
  const n = parseFloat(m[1].replace(",", "."));
  return { qtd: n > 0 ? n : 1, termo: m[2].trim() };
}

function sugestoesHtml(): string {
  if (!sugestoes.length) return "";
  return sugestoes
    .map(
      (p, i) => `
      <button type="button" class="pdv-sug ${i === focoLista ? "is-foco" : ""}" data-sug="${i}">
        <span class="pdv-sug-corpo">
          <span class="pdv-sug-nome">${qtdDigitada > 1 ? `<span class="pdv-badge-qtd">${qtdDigitada}x</span> ` : ""}${escapeHtml(p.name)}</span>
          ${p.spec ? `<span class="pdv-sug-spec">${escapeHtml(p.spec)}</span>` : ""}
          <span class="pdv-sug-meta">${escapeHtml(p.sku || "")}${p.brand ? " · " + escapeHtml(p.brand) : ""}${p.unidade_venda ? " · " + escapeHtml(p.unidade_venda) : ""}${p.embalagem_qtd ? " · " + p.embalagem_qtd + "/cx" : ""}${p.ncm ? " · NCM " + escapeHtml(p.ncm) : ""}</span>
        </span>
        <span class="pdv-sug-preco">${fmtMoney(p.price)}</span>
      </button>`
    )
    .join("");
}

function fmtNum(n: number): string {
  return String(Math.round(n * 100) / 100).replace(".", ",");
}

function fmtNum2(n: number): string {
  return n.toFixed(2).replace(".", ",");
}

function fmtDescInput(l: LinhaPdv, v: number): string {
  return l.desconto_modo === "valor" ? fmtNum2(v) : fmtNum(v);
}

function descExibicao(l: LinhaPdv): number {
  if (l.desconto_modo === "pct") return l.desconto_percentual;
  return (l.preco_unitario * l.quantidade) * (l.desconto_percentual / 100);
}

function renderLinha(l: LinhaPdv, i: number): string {
  return `
    <tr>
      <td class="pdv-idx">${i + 1}</td>
      <td class="pdv-prod">
        <div class="pdv-prod-in">
          <div class="pdv-nome">${escapeHtml(l.nome)}</div>
          <div class="pdv-meta">${escapeHtml([l.sku, l.marca, l.especificacao, l.unidade ? "un. " + l.unidade : "", l.ncm ? "NCM " + l.ncm : ""].filter(Boolean).join(" · "))}</div>
        </div>
      </td>
      <td class="pdv-cell-num"><input class="pdv-qtd" type="number" min="0" step="any" data-i="${i}" value="${l.quantidade}" inputmode="decimal" title="Quantidade — ENTER confirma"></td>
      <td class="pdv-cell-num pdv-preco"><strong>${fmtMoney(l.preco_unitario)}</strong></td>
      <td class="pdv-cell-num pdv-desc-cell">
        <span class="pdv-desc-inline">
          <input class="pdv-desc" type="text" inputmode="decimal" data-i="${i}" value="${fmtDescInput(l, descExibicao(l))}" title="Desconto — P = %, R = R$ · ENTER confirma">
          <span class="pdv-desc-modo pdv-desc-modo--row" data-modo-i="${i}">${l.desconto_modo === "pct" ? "%" : "R$"}</span>
        </span>
      </td>
      <td class="pdv-sub"><strong>${fmtMoney(l.subtotal)}</strong></td>
      <td class="pdv-rm-td"><button type="button" class="icon-btn pdv-rm" data-i="${i}" title="Remover item">×</button></td>
    </tr>`;
}

function renderHtml(): string {
  const linhasHtml = linhas.map((l, i) => renderLinha(l, i)).join("");

  const c = calculosPdv();

  return `
    <div class="pdv-layout">
      <section class="pdv-cab">
        <div class="field pdv-campo pdv-campo--cliente pdv-campo-cliente-w">
          <label class="pdv-rotulo">Cliente <kbd>F6</kbd> busca</label>
          <input id="pdvCliente" type="text" autocomplete="off" data-next="pdvContato" placeholder="Nome do cliente (digite 3+ para buscar)" value="${escapeHtml(vCliente)}">
          <div id="pdvClienteSug" class="pdv-cli-sug"></div>
        </div>
        <div class="field pdv-campo pdv-campo--contato">
          <label class="pdv-rotulo">Contato</label>
          <input id="pdvContato" type="text" autocomplete="off" data-next="pdvValidade" placeholder="WhatsApp / e-mail" value="${escapeHtml(vContato)}">
        </div>
        <div class="field pdv-campo pdv-campo--validade">
          <label class="pdv-rotulo">Validade (dias)</label>
          <input id="pdvValidade" type="number" min="1" data-next="pdvBusca" value="${escapeHtml(vValidade)}">
        </div>
      </section>

      <section class="pdv-busca">
        <label class="pdv-rotulo" for="pdvBusca">Produto — digite <kbd>N*</kbd>nome com quantidade, ou só o nome; tecle <kbd>ENTER</kbd> (↑/↓ navega)</label>
        <div class="pdv-busca-wrap">
          <span class="pdv-busca-icone">⌕</span>
          <input id="pdvBusca" type="text" autocomplete="off" placeholder="Ex.: 3*Cabo Flex, ou só Cabo…">
        </div>
        <div id="pdvSugestoes" class="pdv-sugestoes">${sugestoesHtml()}</div>
      </section>

      <section class="pdv-itens-wrap">
        ${linhas.length === 0
          ? `<div class="pdv-vazio"><p>Nenhum item ainda.</p><p class="pdv-vazio-sub">Digite um produto na busca e tecle ENTER para adicionar.</p></div>`
          : `<div class="table-wrap"><table class="pdv-table">
              <thead><tr>
                <th class="pdv-col-idx">#</th>
                <th>Produto</th>
                <th class="pdv-col-qtd">Qtd</th>
                <th class="pdv-col-preco">Preço unit.</th>
                <th class="pdv-col-desc">Desconto</th>
                <th class="pdv-col-sub">Subtotal</th>
                <th></th>
              </tr></thead>
              <tbody>${linhasHtml}</tbody>
            </table></div>`}
      </section>

      <div class="pdv-footer">
        <div class="pdv-extra">
          <div class="field pdv-campo pdv-campo--desc" style="width:170px;">
            <label class="pdv-rotulo">Desconto <span class="pdv-desc-modo" id="pdvDescModoBadge">R$</span></label>
            <input id="pdvDesconto" type="text" inputmode="decimal" data-next="pdvCondicao" placeholder="0,00" value="${escapeHtml(vDesconto ? fmtNum2(parseNum(vDesconto)) : "")}">
            <small class="pdv-desc-hint"><kbd>P</kbd> = % &nbsp;·&nbsp; <kbd>R</kbd> = R$</small>
          </div>
          <div class="field pdv-campo" style="width:180px;">
            <label class="pdv-rotulo">Condição de pagamento</label>
            <select id="pdvCondicao" data-next="pdvObs"><option value="">Selecione</option></select>
          </div>
          <div class="field pdv-campo pdv-campo--obs">
            <label class="pdv-rotulo">Observações</label>
            <textarea id="pdvObs" rows="2" data-next="pdvSalvar">${escapeHtml(vObs)}</textarea>
          </div>
        </div>
        <div class="pdv-totais">
          <div class="pdv-total-linha"><span>Subtotal</span><strong id="pdvSubtotal">${fmtMoney(c.base)}</strong></div>
          <div class="pdv-total-linha"><span id="pdvDescRotulo">${c.descontoTotal > 0 ? `Desconto (${fmtNum(c.pct)}%)` : "Desconto"}</span><strong id="pdvDescontoV">${c.descontoTotal > 0 ? "-" + fmtMoney(c.descontoTotal) : fmtMoney(0)}</strong></div>
          <div class="pdv-total-linha pdv-total-linha--final"><span>Total</span><strong id="pdvTotal">${fmtMoney(c.total)}</strong></div>
        </div>
        <div id="pdvDescResumo" class="pdv-desc-wrap">${resumoDescontoHtml()}</div>
      </div>

      <div class="pdv-acoes">
        ${editandoId ? `<button type="button" class="btn btn--ghost" id="pdvCancelarEdit">Cancelar edição</button>` : ""}
        <button type="button" class="btn btn--ghost" id="pdvLimpar">Limpar <kbd>F5</kbd></button>
        <button type="button" class="btn btn--ghost" id="pdvSalvarParcial">Salvar rascunho <kbd>F4</kbd></button>
        <button type="button" class="btn btn--ghost" id="pdvVisualizar" ${linhas.length === 0 ? "disabled" : ""}>Visualizar / Imprimir</button>
        <button type="button" class="btn btn--accent" id="pdvSalvar" ${linhas.length === 0 ? "disabled" : ""}>${editandoId ? "Salvar alterações" : "Salvar orçamento"}</button>
      </div>

      <div class="pdv-at">
        <span><kbd>F1</kbd> Imprimir</span>
        <span><kbd>F2</kbd> Visualizar</span>
        <span><kbd>F3</kbd> Finalizar</span>
        <span><kbd>F4</kbd> Salvar rasc</span>
        <span><kbd>F5</kbd> Novo</span>
        <span><kbd>F6</kbd> Cliente</span>
        <span><kbd>F7</kbd> Impressora</span>
        <span><kbd>F8</kbd> Lista</span>
        <span><kbd>F9</kbd> Foco busca</span>
      </div>
    </div>
  `;
}

function paint(): void {
  if (!currentApp) return;
  currentApp.innerHTML = `
    ${ocultarCabecalho
      ? ""
      : `<div class="page-head">
      <div>
        <h1 class="page-title">PDV · Orçamentos${editandoId ? ` <span class="badge badge--ativo">Editando ${escapeHtml(editandoNumero)}</span>` : ""}</h1>
        <p class="page-sub">Teclado: n<b>*</b>produto + ENTER adiciona; F1 a F9 comandam a tela.</p>
      </div>
      <button class="btn btn--ghost" id="btnAbrirLista">Ver orçamentos salvos</button>
      <button class="btn btn--ghost" id="btnConfigImp">Config impressora</button>
    </div>`}
    ${renderHtml()}
    <div id="pdvRecentes"></div>
  `;
  bind();
}

function focoCampo(id: string): void {
  currentApp?.querySelector<HTMLElement>("#" + id)?.focus();
}

function bind(): void {
  const $app = currentApp;
  if (!$app) return;

  ligarAtalhos();

  // ── Cliente: busca rápida (antes de [data-next] para stopImmediatePropagation) ──
  const $cliente = $app.querySelector<HTMLInputElement>("#pdvCliente")!;
  let clTimer: ReturnType<typeof setTimeout> | undefined;
  $cliente.addEventListener("input", () => {
    clearTimeout(clTimer);
    const v = $cliente.value.trim();
    if (v.length < 3) { fecharClienteSug(); return; }
    clTimer = setTimeout(() => void buscarCliente(v), 220);
  });
  $cliente.addEventListener("keydown", (e) => {
    const sugOpen = clientesSug.length > 0;
    if (e.key === "ArrowDown" && sugOpen) { e.preventDefault(); moverFocoCliente(1); }
    else if (e.key === "ArrowUp" && sugOpen) { e.preventDefault(); moverFocoCliente(-1); }
    else if (e.key === "Enter") {
      if (sugOpen) {
        e.preventDefault();
        e.stopImmediatePropagation();
        confirmarCliente();
      }
      // sem sugestões: deixa o handler [data-next] avançar normalmente
    }
    else if (e.key === "Escape") { fecharClienteSug(); }
  });

  // ENTER avança ao próximo campo (data-next)
  $app.querySelectorAll<HTMLElement>("[data-next]").forEach((el) => {
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const next = el.getAttribute("data-next") || "";
        if (next === "pdvSalvar") {
          document.querySelector<HTMLButtonElement>("#pdvSalvar")?.click();
        } else {
          focoCampo(next);
        }
      }
    });
  });

  const guardar = (id: string, set: (v: string) => void) => {
    const el = $app.querySelector<HTMLInputElement | HTMLTextAreaElement>("#" + id);
    if (!el) return;
    el.addEventListener("input", () => set(el.value));
    el.addEventListener("blur", () => set(el.value));
  };
  guardar("pdvCliente", (v) => (vCliente = v));
  guardar("pdvContato", (v) => (vContato = v));
  guardar("pdvValidade", (v) => (vValidade = v || String(VALIDADE_PADRAO)));
  guardar("pdvObs", (v) => (vObs = v));
  const $desc = $app.querySelector<HTMLInputElement>("#pdvDesconto");
  if ($desc) {
    $desc.addEventListener("input", () => {
      let raw = $desc.value;
      if (/%/.test(raw)) {
        vDescModo = "pct";
        raw = raw.replace(/%/g, "").trim();
        $desc.value = raw;
        const b = $app.querySelector<HTMLElement>("#pdvDescModoBadge");
        if (b) b.textContent = "%";
      }
      vDesconto = raw;
      atualizarTotais();
    });
    $desc.addEventListener("blur", () => {
      if ($desc.value.trim() === "") {
        vDesconto = "";
        $desc.value = "";
      } else {
        vDesconto = fmtNum2(parseNum($desc.value));
        $desc.value = vDesconto;
      }
      atualizarTotais();
    });
    $desc.addEventListener("keydown", (e) => {
      const k = e.key.toLowerCase();
      if (k === "p") { e.preventDefault(); setDescModo("pct"); }
      else if (k === "r") { e.preventDefault(); setDescModo("valor"); }
    });
  }

  // ── Busca produto ──
  const $busca = $app.querySelector<HTMLInputElement>("#pdvBusca")!;
  let timer: ReturnType<typeof setTimeout> | undefined;
  $busca.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => void buscar($busca.value), 180);
  });
  $busca.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      limparSugestoes();
      const qtds = currentApp?.querySelectorAll<HTMLInputElement>(".pdv-qtd") || [];
      if (qtds.length) {
        const ult = qtds[qtds.length - 1];
        ult.focus();
        ult.select();
      }
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (sugestoes.length > 0) {
        confirmarSugestao();
      } else {
        focoCampo("pdvDesconto");
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      moverFoco(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      moverFoco(-1);
    } else if (e.key === "Escape") {
      limparSugestoes();
    }
  });

  $app.querySelectorAll<HTMLElement>("[data-sug]").forEach((b) => {
    b.addEventListener("click", () => {
      const p = sugestoes[Number(b.dataset.sug)];
      if (p) adicionar(p);
    });
  });
  $app.querySelectorAll<HTMLElement>("[data-cli]").forEach((b) => {
    b.addEventListener("click", () => {
      const c = clientesSug[Number(b.dataset.cli)];
      if (c) selecionarCliente(c);
    });
  });

  // ── Qtd / desconto na tabela ──
  $app.querySelectorAll<HTMLInputElement>(".pdv-qtd").forEach((i) => {
    i.addEventListener("change", () => recalcular(Number(i.dataset.i)));
    i.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const idx = Number(i.dataset.i);
        if (e.key === "ArrowUp" && idx === 0) {
          focoCampo("pdvBusca");
        } else {
          moverFocoLinha(idx, e.key === "ArrowDown" ? 1 : -1, ".pdv-qtd");
        }
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        recalcular(Number(i.dataset.i));
        moverFocoLinha(Number(i.dataset.i), 0, ".pdv-desc");
      }
    });
  });
  $app.querySelectorAll<HTMLInputElement>(".pdv-desc").forEach((i) => {
    i.addEventListener("change", () => recalcular(Number(i.dataset.i)));
    i.addEventListener("keydown", (e) => {
      const k = e.key.toLowerCase();
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const idx = Number(i.dataset.i);
        if (e.key === "ArrowUp" && idx === 0) {
          focoCampo("pdvBusca");
        } else {
          moverFocoLinha(idx, e.key === "ArrowDown" ? 1 : -1, ".pdv-desc");
        }
        return;
      }
      if (e.key === "Tab") {
        e.preventDefault();
        focoCampo("pdvBusca");
        return;
      }
      if (k === "p" || k === "r") {
        e.preventDefault();
        alternarModoItem(Number(i.dataset.i), k === "p" ? "pct" : "valor");
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        recalcular(Number(i.dataset.i));
        const idx = Number(i.dataset.i);
        if (idx >= linhas.length - 1) {
          focoCampo("pdvBusca");
        } else {
          moverFocoLinha(idx, 1, ".pdv-qtd");
        }
      }
    });
  });

  // ── Remover ──
  $app.querySelectorAll<HTMLElement>(".pdv-rm").forEach((b) => {
    b.addEventListener("click", () => {
      linhas.splice(Number(b.dataset.i), 1);
      paint();
      limparSugestoes();
      focoCampo("pdvBusca");
    });
  });

  $app.querySelector<HTMLElement>("#pdvLimpar")!.addEventListener("click", async () => {
    if (!linhas.length) return;
    if (!(await confirmDialog("Limpar todos os itens?"))) return;
    linhas = [];
    vClienteId = null;
    limparSugestoes();
    paint();
  });

  $app.querySelector<HTMLElement>("#pdvCancelarEdit")?.addEventListener("click", () => {
    editandoId = null;
    editandoNumero = "";
    linhas = [];
    vDesconto = "";
    vObs = "";
    paint();
    void carregarRecentes($app);
  });

  $app.querySelector<HTMLElement>("#pdvSalvar")!.addEventListener("click", () => void salvar(false, true));
  $app.querySelector<HTMLElement>("#pdvSalvarParcial")!.addEventListener("click", () => void salvar(false, false));
  $app.querySelector<HTMLElement>("#pdvVisualizar")!.addEventListener("click", () => void visualizarImprimir());

  $app.querySelector<HTMLElement>("#btnAbrirLista")?.addEventListener("click", () => {
    location.hash = "#/orcamentos";
  });
  $app.querySelector<HTMLElement>("#btnConfigImp")?.addEventListener("click", () => void abrirConfigImpressora());
}

// ──────────────────────────────────────────────────────────
//  Cliente
// ──────────────────────────────────────────────────────────

async function buscarCliente(q: string): Promise<void> {
  const $box = document.querySelector<HTMLElement>("#pdvClienteSug");
  if (!$box) return;
  try {
    const res = await api.buscarClientes(q);
    if ((document.querySelector<HTMLInputElement>("#pdvCliente")?.value || "").trim() !== q) return;
    clientesSug = res;
    focoCliente = -1;
    $box.innerHTML = clienteSugHtml();
    $box.style.display = "block";
    bindClienteSug();
  } catch {
    $box.innerHTML = `<div class="pdv-sem-res">Erro na busca</div>`;
  }
}

function clienteSugHtml(): string {
  const itens = clientesSug.map(
    (c, i) => `
    <button type="button" class="pdv-sug ${i === focoCliente ? "is-foco" : ""}" data-cli="${i}">
      <span class="pdv-sug-corpo">
        <span class="pdv-sug-nome">${escapeHtml(c.nome)}</span>
        <span class="pdv-sug-meta">${[c.doc, c.cidade && c.cidade].filter(Boolean).join(" · ") || ""}</span>
      </span>
    </button>`
  ).join("");
  const cadBtn = `<button type="button" class="pdv-sug ${clientesSug.length === 0 ? "" : ""}" data-novo-cli="1" style="color:var(--accent-ink);font-weight:600;border-top:${clientesSug.length ? "1px solid var(--line)" : "none"}">+ Cadastrar cliente</button>`;
  return itens + cadBtn;
}

function bindClienteSug(): void {
  document.querySelectorAll<HTMLElement>("[data-cli]").forEach((b) => {
    if (b.dataset.ligado) return;
    b.dataset.ligado = "1";
    b.addEventListener("click", () => {
      const c = clientesSug[Number(b.dataset.cli)];
      if (c) selecionarCliente(c);
    });
  });
  document.querySelector<HTMLElement>("[data-novo-cli]")?.addEventListener("click", () => {
    const nome = document.querySelector<HTMLInputElement>("#pdvCliente")?.value.trim() || "";
    abrirModalCadastroCliente(nome, selecionarCliente);
  });
}

function moverFocoCliente(delta: number): void {
  if (!clientesSug.length) return;
  focoCliente = (focoCliente + delta + clientesSug.length) % clientesSug.length;
  const $box = document.querySelector<HTMLElement>("#pdvClienteSug");
  if ($box) {
    $box.innerHTML = clienteSugHtml();
    bindClienteSug();
  }
}

function confirmarCliente(): void {
  const idx = focoCliente >= 0 ? focoCliente : 0;
  if (clientesSug[idx]) selecionarCliente(clientesSug[idx]);
}

function selecionarCliente(c: Cliente): void {
  vCliente = c.nome;
  vClienteId = c.id;
  if (!vContato && c.whatsapp) vContato = c.whatsapp;
  fecharClienteSug();
  paint();
  setTimeout(() => focoCampo("pdvContato"), 0);
}

function fecharClienteSug(): void {
  clientesSug = [];
  focoCliente = -1;
  const $box = document.querySelector<HTMLElement>("#pdvClienteSug");
  if ($box) $box.style.display = "none";
}

function abrirModalCadastroCliente(nomePrefill: string, onSave: (c: Cliente) => void): void {
  openModal(
    `<div class="modal-head"><h3>Cadastrar cliente</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field-row" style="flex-direction:column;gap:10px;">
       <div class="field"><label>Nome *</label><input id="ccNome" value="${escapeHtml(nomePrefill)}" autocomplete="off"></div>
       <div class="field"><label>CPF *</label><input id="ccCpf" placeholder="000.000.000-00" autocomplete="off"></div>
       <div class="field"><label>Telefone</label><input id="ccTel" autocomplete="off"></div>
       <div class="field"><label>WhatsApp</label><input id="ccWpp" autocomplete="off"></div>
       <div class="field"><label>E-mail</label><input id="ccEmail" type="email" autocomplete="off"></div>
       <div class="field-row">
         <div class="field" style="flex:3"><label>Endereço</label><input id="ccEnd" autocomplete="off"></div>
         <div class="field" style="flex:1"><label>Cidade</label><input id="ccCid" autocomplete="off"></div>
         <div class="field" style="flex:0.4"><label>UF</label><input id="ccUf" maxlength="2" autocomplete="off"></div>
       </div>
       <div class="field"><label>Observações</label><textarea id="ccObs" rows="2"></textarea></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--accent" data-salvar-cli>Salvar</button>
       <button class="btn" data-close>Cancelar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLElement>("[data-salvar-cli]")!.onclick = async () => {
          const nome = (modal.querySelector<HTMLInputElement>("#ccNome")?.value || "").trim();
          const doc = (modal.querySelector<HTMLInputElement>("#ccCpf")?.value || "").trim();
          if (!nome) { toast("Informe o nome", "error"); return; }
          if (!doc) { toast("CPF obrigatório", "error"); return; }
          try {
            const res = await api.criarCliente({
              nome,
              doc,
              tipo_pessoa: "f",
              telefone: (modal.querySelector<HTMLInputElement>("#ccTel")?.value || "").trim() || undefined,
              whatsapp: (modal.querySelector<HTMLInputElement>("#ccWpp")?.value || "").trim() || undefined,
              email: (modal.querySelector<HTMLInputElement>("#ccEmail")?.value || "").trim() || undefined,
              endereco: (modal.querySelector<HTMLInputElement>("#ccEnd")?.value || "").trim() || undefined,
              cidade: (modal.querySelector<HTMLInputElement>("#ccCid")?.value || "").trim() || undefined,
              uf: (modal.querySelector<HTMLInputElement>("#ccUf")?.value || "").trim().toUpperCase() || undefined,
              observacoes: (modal.querySelector<HTMLInputElement>("#ccObs")?.value || "").trim() || undefined,
            });
            toast("Cliente cadastrado", "success");
            closeModal();
            onSave({ id: res.id, nome, doc, tipo_pessoa: "f", email: "", telefone: "", whatsapp: "", endereco: "", cidade: "", uf: "", cep: "", vendedor_id: null, vendedor_nome: null, limite_credito: 0, observacoes: "", ativo: true });
          } catch (e) {
            toast("Erro: " + (e as Error).message, "error");
          }
        };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Busca e sugestões
// ──────────────────────────────────────────────────────────

async function buscar(v: string): Promise<void> {
  const $sug = currentApp?.querySelector<HTMLElement>("#pdvSugestoes");
  if (!$sug) return;
  const { qtd, termo } = parseBusca(v);
  qtdDigitada = qtd;
  if (!termo) {
    limparSugestoes();
    return;
  }
  try {
    const res = await api.listarProdutos({ q: termo, limit: 8, agrupado: 0 });
    if ((currentApp?.querySelector<HTMLInputElement>("#pdvBusca")?.value || "").trim() !== v) return;
    sugestoes = res.items.map((i) => i as ProdutoResumo);
    focoLista = -1;
    $sug.innerHTML = sugestoesHtml();
    bindSugestoes();
  } catch {
    $sug.innerHTML = `<div class="pdv-sem-res">Erro na busca</div>`;
  }
}

function limparSugestoes(): void {
  sugestoes = [];
  focoLista = -1;
  const $sug = currentApp?.querySelector<HTMLElement>("#pdvSugestoes");
  if ($sug) $sug.innerHTML = "";
}

function bindSugestoes(): void {
  currentApp?.querySelectorAll<HTMLElement>("[data-sug]").forEach((b) => {
    if (b.dataset.ligado) return;
    b.dataset.ligado = "1";
    b.addEventListener("click", () => {
      const p = sugestoes[Number(b.dataset.sug)];
      if (p) adicionar(p);
    });
  });
}

function moverFoco(delta: number): void {
  if (!sugestoes.length) return;
  focoLista = (focoLista + delta + sugestoes.length) % sugestoes.length;
  const $sug = currentApp?.querySelector<HTMLElement>("#pdvSugestoes");
  if ($sug) {
    $sug.innerHTML = sugestoesHtml();
    bindSugestoes();
  }
}

function moverFocoLinha(atual: number, delta: number, sel: string): void {
  if (!currentApp) return;
  const campos = currentApp.querySelectorAll<HTMLInputElement>(sel);
  const alvo = Math.min(campos.length - 1, Math.max(0, atual + delta));
  const el = campos[alvo];
  if (el) {
    el.focus();
    el.select();
  }
}

function confirmarSugestao(): void {
  if (!sugestoes.length) return;
  const idx = focoLista >= 0 ? focoLista : 0;
  adicionar(sugestoes[idx]);
}

function adicionar(p: ProdutoResumo): void {
  const qtd = qtdDigitada;
  const existente = linhas.find((l) => l.produto_id != null && l.produto_id === p.id);
  if (existente) {
    existente.quantidade += qtd;
    existente.subtotal = existente.preco_unitario * existente.quantidade;
  } else {
    linhas.push({
      produto_id: p.id,
      sku: p.sku || "",
      nome: p.name || "",
      marca: p.brand || "",
      especificacao: p.spec || "",
      unidade: p.unidade_venda || "",
      ncm: p.ncm || "",
      quantidade: qtd,
      preco_unitario: p.price || 0,
      desconto_percentual: 0,
      desconto_modo: "pct",
      subtotal: (p.price || 0) * qtd,
    });
  }
  qtdDigitada = 1;
  limparSugestoes();
  const $busca = currentApp?.querySelector<HTMLInputElement>("#pdvBusca");
  if ($busca) $busca.value = "";
  paint();
  setTimeout(() => focoCampo("pdvBusca"), 0);
  void aplicarPrecoEfetivo(p.id);
}

async function aplicarPrecoEfetivo(varianteId: number): Promise<void> {
  try {
    const ef = await api.precoEfetivo(varianteId);
    const idx = linhas.findIndex((l) => l.produto_id === varianteId);
    if (idx < 0 || !currentApp) return;
    const l = linhas[idx];
    if (!ef || !(ef.preco > 0) || ef.preco === l.preco_unitario) return;
    l.preco_unitario = ef.preco;
    l.subtotal = l.preco_unitario * l.quantidade * (1 - l.desconto_percentual / 100);
    const tr = currentApp.querySelector<HTMLInputElement>(`.pdv-qtd[data-i="${idx}"]`)?.closest("tr");
    if (tr) {
      const $preco = tr.querySelector<HTMLElement>(".pdv-preco strong");
      if ($preco) $preco.textContent = fmtMoney(l.preco_unitario);
      const $sub = tr.querySelector<HTMLElement>(".pdv-sub strong");
      if ($sub) $sub.textContent = fmtMoney(l.subtotal);
    }
    atualizarTotais();
  } catch { /* mantém o preço base */ }
}

// ──────────────────────────────────────────────────────────
//  Cálculos
// ──────────────────────────────────────────────────────────

function parseNum(v: string): number {
  const n = parseFloat(String(v || "").replace(",", "."));
  return isNaN(n) ? 0 : n;
}

function calculosPdv(): {
  base: number;
  subtotal: number;
  descontoItens: number;
  descontoGeral: number;
  descontoTotal: number;
  pct: number;
  total: number;
} {
  const base = linhas.reduce((s, l) => s + l.preco_unitario * l.quantidade, 0);
  const subtotal = linhas.reduce((s, l) => s + l.subtotal, 0);
  const descontoGeral = vDescModo === "pct" ? subtotal * (parseNum(vDesconto) / 100) : parseNum(vDesconto);
  const descontoItens = Math.max(0, base - subtotal);
  const descontoTotal = Math.max(0, descontoItens + descontoGeral);
  const pct = base > 0 ? (descontoTotal / base) * 100 : 0;
  return {
    base,
    subtotal,
    descontoItens,
    descontoGeral,
    descontoTotal,
    pct,
    total: Math.max(0, subtotal - descontoGeral),
  };
}

function limiteDescontoUsuario(): number {
  const u = usuarioCorrente();
  if (!u) return 100;
  if (u.perfil === "admin") return 100;
  return Number(u.desconto_limite_pct ?? 0);
}

function setDescModo(m: "pct" | "valor"): void {
  vDescModo = m;
  const b = currentApp?.querySelector<HTMLElement>("#pdvDescModoBadge");
  if (b) b.textContent = m === "pct" ? "%" : "R$";
  const f = currentApp?.querySelector<HTMLInputElement>("#pdvDesconto");
  if (f) {
    f.placeholder = m === "pct" ? "0,00 %" : "0,00";
    f.focus();
  }
  atualizarTotais();
}

function resumoDescontoHtml(): string {
  const c = calculosPdv();
  if (c.descontoTotal <= 0) return "";
  const limite = limiteDescontoUsuario();
  const acima = c.pct > limite + 1e-9;
  const linhaLimite = acima
    ? `<span class="pdv-desc-aviso">Desconto de <b>${c.pct.toFixed(2).replace(".", ",")}%</b> acima do seu limite (${limite}%) — finalizar exigirá autorização do gerente.</span>`
    : `<span>Desconto de <b>${c.pct.toFixed(2).replace(".", ",")}%</b>${limite < 100 ? ` · limite: ${limite}%` : ""}</span>`;
  return `
    <div class="pdv-desc-resumo">
      <span>Itens: ${fmtMoney(c.descontoItens)}</span>
      <span>Geral: ${fmtMoney(c.descontoGeral)}${vDescModo === "pct" ? " (% )" : " (R$)"}</span>
      <span>Total: ${fmtMoney(c.descontoTotal)}</span>
      ${linhaLimite}
    </div>`;
}

function alternarModoItem(idx: number, novo: "pct" | "valor"): void {
  const l = linhas[idx];
  if (!l || !currentApp) return;
  const $input = currentApp.querySelector<HTMLInputElement>(`.pdv-desc[data-i="${idx}"]`);
  const base = l.preco_unitario * l.quantidade;
  const raw = parseNum($input?.value || "0");
  const amt = l.desconto_modo === "pct" ? base * (raw / 100) : raw;
  l.desconto_modo = novo;
  const novoRaw = novo === "pct" ? (base > 0 ? (amt / base) * 100 : 0) : amt;
  if ($input) $input.value = fmtDescInput(l, novoRaw);
  const b = currentApp.querySelector<HTMLElement>(`.pdv-desc-modo--row[data-modo-i="${idx}"]`);
  if (b) b.textContent = novo === "pct" ? "%" : "R$";
  recalcular(idx);
}

function recalcular(idx: number): void {
  const l = linhas[idx];
  if (!l || !currentApp) return;
  const qtd = parseNum(currentApp.querySelector<HTMLInputElement>(`.pdv-qtd[data-i="${idx}"]`)?.value || "0");
  const raw = parseNum(currentApp.querySelector<HTMLInputElement>(`.pdv-desc[data-i="${idx}"]`)?.value || "0");
  l.quantidade = Math.max(0, qtd);
  const base = l.preco_unitario * l.quantidade;
  const pct = l.desconto_modo === "pct" ? raw : (base > 0 ? (raw / base) * 100 : 0);
  l.desconto_percentual = Math.min(100, Math.max(0, pct));
  l.subtotal = l.preco_unitario * l.quantidade * (1 - l.desconto_percentual / 100);
  const $cell = currentApp.querySelector<HTMLInputElement>(`.pdv-qtd[data-i="${idx}"]`)?.closest("tr")?.querySelector<HTMLElement>(".pdv-sub");
  if ($cell) $cell.textContent = fmtMoney(l.subtotal);
  const $desc = currentApp.querySelector<HTMLInputElement>(`.pdv-desc[data-i="${idx}"]`);
  if ($desc) $desc.value = fmtDescInput(l, descExibicao(l));
  atualizarTotais();
}

function atualizarTotais(): void {
  if (!currentApp) return;
  const c = calculosPdv();
  const set = (id: string, v: number) => {
    const el = currentApp!.querySelector<HTMLElement>("#" + id);
    if (el) el.textContent = fmtMoney(v);
  };
  set("pdvSubtotal", c.base);
  set("pdvTotal", c.total);
  const $descRot = currentApp.querySelector<HTMLElement>("#pdvDescRotulo");
  if ($descRot) $descRot.textContent = c.descontoTotal > 0 ? `Desconto (${fmtNum(c.pct)}%)` : "Desconto";
  const $descVal = currentApp.querySelector<HTMLElement>("#pdvDescontoV");
  if ($descVal) $descVal.textContent = c.descontoTotal > 0 ? `-${fmtMoney(c.descontoTotal)}` : fmtMoney(0);
  const $resumo = currentApp.querySelector<HTMLElement>("#pdvDescResumo");
  if ($resumo) $resumo.innerHTML = resumoDescontoHtml();
  const salvar = currentApp!.querySelector<HTMLButtonElement>("#pdvSalvar");
  if (salvar) salvar.disabled = linhas.length === 0;
}

// ──────────────────────────────────────────────────────────
//  Salvar / Finalizar / Visualizar / Imprimir
// ──────────────────────────────────────────────────────────

async function salvar(finalizado = false, imprimir = true): Promise<{ id: number; numero: string } | null> {
  const $app = currentApp;
  if (!$app) return null;
  if (!linhas.length) {
    toast("Adicione ao menos um item", "error");
    return null;
  }
  const cliente = vCliente.trim();
  const contato = vContato.trim();
  const validade = parseInt(vValidade, 10) || VALIDADE_PADRAO;
  const desconto = calculosPdv().descontoGeral;
  const obs = vObs.trim();

  if (!cliente) {
    toast("Informe o nome do cliente", "error");
    focoCampo("pdvCliente");
    return null;
  }

  const itens: OrcamentoItemPayload[] = linhas.map((l) => ({
    produto_id: l.produto_id,
    nome: l.nome,
    sku: l.sku,
    marca: l.marca,
    especificacao: l.especificacao,
    quantidade: l.quantidade,
    preco_unitario: l.preco_unitario,
    desconto_percentual: l.desconto_percentual,
  }));

  try {
    const condSel = document.querySelector<HTMLSelectElement>("#pdvCondicao");
    const condId = condSel ? parseInt(condSel.value, 10) || undefined : undefined;

    let res: { id: number; numero: string };
    if (editandoId != null) {
      const patch: Record<string, unknown> = { cliente, contato, validade_dias: validade, observacoes: obs, desconto };
      if (condId !== undefined) patch.condicao_pagamento_id = condId;
      await api.atualizarOrcamento(editandoId, patch);
      await api.substituirItensOrcamento(editandoId, itens);
      res = { id: editandoId, numero: editandoNumero };
    } else {
      res = await api.criarOrcamento({
        cliente,
        contato,
        validade_dias: validade,
        observacoes: obs,
        desconto,
        itens,
        condicao_pagamento_id: condId,
        cliente_id: vClienteId ?? undefined,
      });
    }
    sessionStorage.setItem("pdv_cliente", cliente);

    if (finalizado) {
      const ok = await finalizarOrcamento(res.id);
      toast(
        ok
          ? `${res.numero} finalizado`
          : `${res.numero} salvo — finalização requer autorização de desconto`,
        ok ? "success" : "error"
      );
    } else {
      toast(editandoId == null ? `${res.numero} salvo` : `${res.numero} atualizado`, "success");
    }

    if (imprimir) {
      void api.imprimirOrcamento(res.id).catch(() =>
        toast("Orçamento salvo, mas a impressão falhou", "error")
      );
    }

    editandoId = null;
    editandoNumero = "";
    linhas = [];
    vDesconto = "";
    vObs = "";
    paint();
    await carregarRecentes($app);
    focoCampo("pdvCliente");
    return res;
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
    return null;
  }
}

async function imprimirPedido(): Promise<void> {
  if (!linhas.length) {
    toast("Adicione itens antes de imprimir", "error");
    return;
  }
  await salvar(false, true);
}

async function finalizarOrcamento(id: number): Promise<boolean> {
  try {
    await api.atualizarOrcamento(id, { status: "faturado" });
    return true;
  } catch (e) {
    const err = e as Error & { code?: string };
    if (err.code === "desconto_exige_autorizacao") {
      const ok = await solicitarAutorizacaoDesconto(id);
      if (!ok) return false;
      try {
        await api.atualizarOrcamento(id, { status: "faturado" });
        return true;
      } catch (e2) {
        toast("Erro ao finalizar após autorização: " + (e2 as Error).message, "error");
        return false;
      }
    }
    toast("Erro ao finalizar: " + err.message, "error");
    return false;
  }
}

function solicitarAutorizacaoDesconto(id: number): Promise<boolean> {
  return new Promise((resolve) => {
    openModal(
      `<div class="modal-head"><h3>Autorizar desconto</h3><button class="icon-btn" data-close>×</button></div>
       <p style="font-size:13px;color:var(--ink-soft);margin:0 0 12px;">O desconto aplicado está acima da alçada do vendedor. Informe as credenciais do gerente para autorizar e finalizar.</p>
       <div style="display:flex;flex-direction:column;gap:12px;">
         <div class="field"><label>Login do gerente</label><input id="autLogin" autocomplete="username"></div>
         <div class="field"><label>Senha</label><input id="autSenha" type="password" autocomplete="current-password"></div>
       </div>
       <div class="modal-actions">
         <button class="btn" data-cancelar>Cancelar</button>
         <button class="btn btn--accent" id="autConfirmar">Autorizar e finalizar</button>
       </div>`,
      {
        onMount(modal) {
          const fechar = () => closeModal();
          modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = fechar));
          modal.querySelector<HTMLElement>("[data-cancelar]")!.onclick = () => {
            closeModal();
            resolve(false);
          };
          const $login = modal.querySelector<HTMLInputElement>("#autLogin");
          const $senha = modal.querySelector<HTMLInputElement>("#autSenha");
          const $btn = modal.querySelector<HTMLButtonElement>("#autConfirmar")!;
          const tentar = async () => {
            const login = ($login?.value || "").trim();
            const senha = $senha?.value || "";
            if (!login || !senha) {
              toast("Informe login e senha do gerente", "error");
              return;
            }
            $btn.disabled = true;
            $btn.textContent = "Autorizando…";
            try {
              await api.autorizarDescontoOrcamento(id, { login, senha });
              toast("Desconto autorizado", "success");
              closeModal();
              resolve(true);
            } catch (e) {
              toast("Falha na autorização: " + (e as Error).message, "error");
              $btn.disabled = false;
              $btn.textContent = "Autorizar e finalizar";
            }
          };
          $btn.addEventListener("click", () => void tentar());
          $senha?.addEventListener("keydown", (e) => { if (e.key === "Enter") void tentar(); });
          setTimeout(() => $login?.focus(), 0);
        },
      }
    );
  });
}

async function visualizarImprimir(): Promise<void> {
  if (!linhas.length) {
    toast("Adicione itens antes de visualizar", "error");
    return;
  }
  const res = await salvar(false, false);
  if (res) window.open(`/orcamentos/venda/${res.id}/imprimir`, "_blank");
}

async function finalizarPedido(): Promise<void> {
  if (!linhas.length) {
    toast("Adicione ao menos um item", "error");
    return;
  }
  await salvar(true, true);
}

function visualizarPedido(): void {
  if (!linhas.length) {
    toast("Nenhum item para visualizar", "error");
    return;
  }
  const c = calculosPdv();
  openModal(
    `<div class="modal-head"><h3>Pedido</h3><button class="icon-btn" data-close>×</button></div>
     <p style="margin:-4px 0 12px;font-size:13px;color:var(--ink-soft);">${escapeHtml(vCliente || "—")}${vContato ? " · " + escapeHtml(vContato) : ""}</p>
     <div class="table-wrap">
       <table class="data-table">
         <thead><tr><th>Produto</th><th>Qtd.</th><th>Preço</th><th>Subtotal</th></tr></thead>
         <tbody>
           ${linhas.map((l) => `
             <tr>
               <td>${escapeHtml(l.nome)}${l.sku ? `<div style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">${escapeHtml(l.sku)}</div>` : ""}</td>
               <td>${l.quantidade}</td>
               <td>${fmtMoney(l.preco_unitario)}</td>
               <td><strong>${fmtMoney(l.subtotal)}</strong></td>
             </tr>`).join("")}
         </tbody>
       </table>
     </div>
     <div style="display:flex;justify-content:flex-end;gap:16px;margin-top:14px;font-size:13.5px;">
       <div>Subtotal: <strong>${fmtMoney(c.base)}</strong></div>
       ${c.descontoTotal > 0 ? `<div>Desconto (${fmtNum(c.pct)}%): <strong>-${fmtMoney(c.descontoTotal)}</strong></div>` : ""}
       <div>Total: <strong>${fmtMoney(c.total)}</strong></div>
     </div>
     <div class="modal-actions">
       <button class="btn btn--ghost" data-salvar>Salvar</button>
       <button class="btn btn--accent" data-finalizar>Finalizar</button>
       <button class="btn" data-close>Fechar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLElement>("[data-salvar]")!.onclick = () => { closeModal(); void salvar(false, true); };
        modal.querySelector<HTMLElement>("[data-finalizar]")!.onclick = () => { closeModal(); void finalizarPedido(); };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Atalhos F1–F9
// ──────────────────────────────────────────────────────────

let atalhosLigados = false;

function ligarAtalhos(): void {
  if (atalhosLigados) return;
  atalhosLigados = true;
  window.addEventListener("keydown", (e) => {
    if (!currentApp || !document.body.contains(currentApp)) return;
    if (e.ctrlKey && e.key === "F5") {
      e.preventDefault();
      abrirBuscaCliente();
      return;
    }
    if (e.ctrlKey && e.key === "F6") {
      e.preventDefault();
      focoCampo("pdvBusca");
      return;
    }
    const m = e.key?.toUpperCase().match(/^F([1-9])$/);
    if (!m) return;
    e.preventDefault();
    e.stopPropagation();
    void acaoAtalho(Number(m[1]));
  });
}

async function acaoAtalho(f: number): Promise<void> {
  switch (f) {
    case 1:
      await imprimirPedido();
      break;
    case 2:
      visualizarPedido();
      break;
    case 3:
      await finalizarPedido();
      break;
    case 4:
      await salvar(false, false);
      break;
    case 5:
      document.querySelector<HTMLElement>("#pdvLimpar")?.click();
      break;
    case 6:
      abrirBuscaCliente();
      break;
    case 7:
      await abrirConfigImpressora();
      break;
    case 8:
      location.hash = "#/orcamentos";
      break;
    case 9:
      focoCampo("pdvBusca");
      break;
  }
}

// ──────────────────────────────────────────────────────────
//  Modal busca cliente (F6)
// ──────────────────────────────────────────────────────────

function abrirBuscaCliente(): void {
  openModal(
    `<div class="modal-head"><h3>Buscar cliente</h3><button class="icon-btn" data-close>×</button></div>
     <div class="field" style="margin-bottom:12px;">
       <input id="modCliBusca" type="text" autocomplete="off" placeholder="Nome, CPF, endereço, cidade… (3+ letras)">
     </div>
     <div id="modCliRes" style="max-height:320px;overflow:auto;"></div>
     <div style="text-align:center;margin-top:8px;"><button type="button" class="btn btn--ghost" id="modCliCadastrar">+ Cadastrar novo cliente</button></div>
     <div class="modal-actions"><button class="btn" data-close>Fechar</button></div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        const $input = modal.querySelector<HTMLInputElement>("#modCliBusca")!;
        const $res = modal.querySelector<HTMLElement>("#modCliRes")!;
        let moTimer: ReturnType<typeof setTimeout> | undefined;
        let moSug: Cliente[] = [];
        let moFoco = -1;

        $input.addEventListener("input", () => {
          clearTimeout(moTimer);
          const q = $input.value.trim();
          if (q.length < 3) { $res.innerHTML = ""; moSug = []; return; }
          moTimer = setTimeout(async () => {
            try {
              const r = await api.buscarClientes(q);
              moSug = r;
              moFoco = -1;
              $res.innerHTML = r.length
                ? r.map((c, i) =>
                    `<button type="button" class="pdv-sug ${i === moFoco ? "is-foco" : ""}" style="border-radius:0;" data-mcli="${i}">
                       <span class="pdv-sug-corpo">
                         <span class="pdv-sug-nome">${escapeHtml(c.nome)}</span>
                         <span class="pdv-sug-meta">${[c.doc, c.cidade && c.cidade].filter(Boolean).join(" · ") || ""}</span>
                       </span>
                     </button>`).join("")
                : `<div class="pdv-sem-res">Nenhum</div>`;
              modal.querySelectorAll<HTMLElement>("[data-mcli]").forEach((b) => {
                b.addEventListener("click", () => {
                  const cl = moSug[Number(b.dataset.mcli)];
                  if (cl) selecionarClienteModal(cl);
                });
              });
              $input.addEventListener("keydown", (ke) => {
                if (ke.key === "ArrowDown") { ke.preventDefault(); moFoco = Math.min(moFoco + 1, moSug.length - 1); destMcli(); }
                if (ke.key === "ArrowUp") { ke.preventDefault(); moFoco = Math.max(moFoco - 1, 0); destMcli(); }
                if (ke.key === "Enter" && moFoco >= 0 && moSug[moFoco]) {
                  ke.preventDefault();
                  selecionarClienteModal(moSug[moFoco]);
                }
              });
              function destMcli(): void {
                $res.querySelectorAll("[data-mcli]").forEach((b, i) => b.classList.toggle("is-foco", i === moFoco));
              }
            } catch { $res.innerHTML = `<div class="pdv-sem-res">Erro</div>`; }
          }, 200);
        });
        modal.querySelector<HTMLElement>("#modCliCadastrar")!.onclick = () => {
          abrirModalCadastroCliente($input.value.trim(), (c) => {
            selecionarClienteModal(c);
          });
        };
        setTimeout(() => $input.focus(), 0);
        function selecionarClienteModal(c: Cliente): void {
          vCliente = c.nome;
          vClienteId = c.id;
          if (!vContato && c.whatsapp) vContato = c.whatsapp;
          closeModal();
          paint();
          setTimeout(() => focoCampo("pdvContato"), 0);
        }
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Config impressora
// ──────────────────────────────────────────────────────────

async function abrirConfigImpressora(): Promise<void> {
  let cfg;
  try {
    cfg = await api.getConfigImpressao();
  } catch {
    toast("Não foi possível ler a config da impressora", "error");
    return;
  }
  openModal(
    `<div class="modal-head"><h3>Retaguarda de impressão</h3><button class="icon-btn" data-close>×</button></div>
     <p style="margin:-4px 0 12px;font-size:13px;color:var(--ink-soft);">O cupom é enviado direto (ESC/POS) a esta impressora, sem diálogo.</p>
     <div class="field-row">
       <div class="field"><label>Host</label><input id="cfgHost" value="${escapeHtml(cfg.host)}" autocomplete="off"></div>
       <div class="field"><label>Porta</label><input id="cfgPorta" type="number" value="${cfg.porta}" min="1" max="65535"></div>
       <div class="field"><label>Papel (mm)</label>
         <select id="cfgPapel">
           <option value="80" ${cfg.papel_mm >= 80 ? "selected" : ""}>80 mm</option>
           <option value="58" ${cfg.papel_mm < 80 ? "selected" : ""}>58 mm</option>
         </select>
       </div>
     </div>
     <label class="ck-line"><input id="cfgAuto" type="checkbox" ${cfg.auto_impressao ? "checked" : ""}> Imprimir automaticamente ao salvar</label>
     <div class="modal-actions">
       <button class="btn btn--ghost" data-teste>Testar</button>
       <button class="btn btn--accent" data-salvar>Salvar</button>
       <button class="btn" data-close>Fechar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLElement>("[data-teste]")!.onclick = () =>
          void api.imprimirTeste().catch((e) => toast("Teste falhou: " + (e as Error).message, "error"));
        modal.querySelector<HTMLElement>("[data-salvar]")!.onclick = async () => {
          const host = (modal.querySelector<HTMLInputElement>("#cfgHost")?.value || "").trim();
          const porta = parseInt(modal.querySelector<HTMLInputElement>("#cfgPorta")?.value || "9100", 10);
          const papel = parseInt(modal.querySelector<HTMLSelectElement>("#cfgPapel")?.value || "80", 10);
          const auto = modal.querySelector<HTMLInputElement>("#cfgAuto")?.checked ? 1 : 0;
          try {
            await api.setConfigImpressao({ host, porta, papel_mm: papel, auto_impressao: auto });
            toast("Config salva", "success");
            closeModal();
          } catch (e) {
            toast("Erro: " + (e as Error).message, "error");
          }
        };
      },
    }
  );
}

// ──────────────────────────────────────────────────────────
//  Lista de recentes
// ──────────────────────────────────────────────────────────

async function carregarRecentes($app: HTMLElement): Promise<void> {
  const $wrap = $app.querySelector<HTMLElement>("#pdvRecentes");
  if (!$wrap) return;
  let lista;
  try {
    lista = await api.listarOrcamentos("", true);
  } catch {
    $wrap.innerHTML = "";
    return;
  }
  if (!lista.length) {
    $wrap.innerHTML = "";
    return;
  }
  $wrap.innerHTML = `
    <div class="pdv-recentes">
      <h3>Orçamentos recentes</h3>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Nº</th><th>Cliente</th><th>Status</th><th>Itens</th><th>Total</th><th>Criado em</th></tr></thead>
          <tbody>
            ${lista.slice(0, 6).map((o) => `
              <tr class="row-link" data-id="${o.id}">
                <td style="font-family:var(--font-mono);">${escapeHtml(o.numero)}</td>
                <td>${escapeHtml(o.cliente || "—")}</td>
                <td><span class="badge badge--${escapeHtml(o.status)}">${escapeHtml(o.status)}</span></td>
                <td>${o.n_itens}</td>
                <td><strong>${fmtMoney(o.total)}</strong></td>
                <td>${fmtDate(o.criado_em)}</td>
              </tr>`).join("")}
          </tbody>
        </table>
        <p class="pdv-ver-mais"><a href="#/orcamentos">Ver todos →</a></p>
      </div>
    </div>
  `;
  $wrap.querySelectorAll<HTMLElement>("[data-id]").forEach((tr) => {
    tr.addEventListener("click", () => void abrirDetalhe(Number(tr.dataset.id)));
  });
}

async function abrirDetalhe(id: number): Promise<void> {
  let d;
  try {
    d = await api.detalharOrcamento(id);
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
    return;
  }
  const editavel = STATUS_EDITAVEIS.has(d.status);
  openModal(
    `<div class="modal-head"><h3>${escapeHtml(d.numero)}</h3><button class="icon-btn" data-close>×</button></div>
     <p style="margin:-4px 0 12px;font-size:13px;color:var(--ink-soft);">${escapeHtml(d.cliente || "Sem cliente")}${d.contato ? " · " + escapeHtml(d.contato) : ""} · criado em ${fmtDate(d.criado_em)}${d.desconto_autorizado ? " · <span class='badge badge--fechada'>desc. autorizado</span>" : ""}</p>
     <div class="table-wrap">
       <table class="data-table">
         <thead><tr><th>Produto</th><th>Qtd.</th><th>Preço</th><th>Subtotal</th></tr></thead>
         <tbody>
           ${d.itens.map((i) => `
             <tr>
               <td>${escapeHtml(i.nome)}${i.sku ? `<div style="font-family:var(--font-mono);font-size:11px;color:var(--ink-faint);">${escapeHtml(i.sku)}</div>` : ""}</td>
               <td>${i.quantidade}</td>
               <td>${fmtMoney(i.preco_unitario)}</td>
               <td><strong>${fmtMoney(i.subtotal)}</strong></td>
             </tr>`).join("")}
         </tbody>
       </table>
     </div>
     <div style="display:flex;justify-content:flex-end;gap:16px;margin-top:14px;font-size:13.5px;flex-wrap:wrap;">
       <div>Subtotal: <strong>${fmtMoney(d.subtotal)}</strong></div>
       <div>Desconto: <strong>${fmtMoney(d.desconto)}</strong></div>
       <div>Total: <strong>${fmtMoney(d.total)}</strong></div>
     </div>
     <div class="modal-actions">
       ${editavel ? `<button class="btn" data-editar>Editar</button>` : ""}
       <button class="btn btn--accent" data-imprimir>Imprimir</button>
       <button class="btn" data-close>Fechar</button>
     </div>`,
    {
      onMount(modal) {
        modal.querySelectorAll("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
        modal.querySelector<HTMLElement>("[data-imprimir]")!.onclick = () => {
          window.open(`/orcamentos/venda/${id}/imprimir`, "_blank");
        };
        modal.querySelector<HTMLElement>("[data-editar]")?.addEventListener("click", () => void carregarParaEdicao(id));
      },
    }
  );
}

async function carregarParaEdicao(id: number): Promise<void> {
  let d;
  try {
    d = await api.detalharOrcamento(id);
  } catch (e) {
    toast("Erro: " + (e as Error).message, "error");
    return;
  }
  if (!STATUS_EDITAVEIS.has(d.status)) {
    toast("Este orçamento está fechado/cancelado e não pode ser editado", "error");
    return;
  }
  closeModal();
  vCliente = d.cliente || "";
  vClienteId = d.cliente_id ?? null;
  vContato = d.contato || "";
  vValidade = String(d.validade_dias || VALIDADE_PADRAO);
  vObs = d.observacoes || "";
  vDesconto = String(d.desconto || "");
  vDescModo = "valor";
  linhas = (d.itens || []).map((it) => ({
    produto_id: it.produto_id ?? null,
    sku: it.sku || "",
    nome: it.nome || "",
    marca: it.marca || "",
    especificacao: it.especificacao || "",
    unidade: "",
    ncm: "",
    quantidade: it.quantidade,
    preco_unitario: it.preco_unitario,
    desconto_percentual: it.desconto_percentual || 0,
    desconto_modo: "pct",
    subtotal: it.subtotal ?? it.preco_unitario * it.quantidade,
  }));
  editandoId = id;
  editandoNumero = d.numero || "";
  paint();
  const condSel = document.querySelector<HTMLSelectElement>("#pdvCondicao");
  if (condSel && d.condicao_pagamento_id != null) condSel.value = String(d.condicao_pagamento_id);
  setTimeout(() => focoCampo("pdvCliente"), 0);
}

// ------------------------------------------------------------------
// API pública para o shell legacy (PdvPage): ações da Sidebar e atalhos.
// ------------------------------------------------------------------

export function pdvAtalho(f: number): Promise<void> {
  return acaoAtalho(f);
}

export function pdvBuscaCliente(): void {
  abrirBuscaCliente();
}

