// pages/relatorios.tsx — central analítica com estados explícitos e navegação acessível.
import { useEffect, useState, type KeyboardEvent } from "react";
import { api, type DashboardExecutivo } from "../api/client";
import { fmtMoney } from "../ui/format";
import { Badge, Button, EmptyRow, ErrorState, Loading, PageHeader, Select, StatCard, Table, TBody, THead, Cell } from "../ui/ui";

type Aba = "dashboard" | "vendas" | "compras" | "estoque" | "financeiro";
const ABAS: { key: Aba; label: string }[] = [
  { key: "dashboard", label: "Dashboard" }, { key: "vendas", label: "Vendas" },
  { key: "compras", label: "Compras" }, { key: "estoque", label: "Estoque" },
  { key: "financeiro", label: "Financeiro / DRE" },
];

export function Relatorios() {
  const [aba, setAba] = useState<Aba>("dashboard");
  const [dash, setDash] = useState<DashboardExecutivo | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregarDashboard = async () => {
    setCarregando(true); setErro(null);
    try { setDash(await api.dashboardExecutivo()); }
    catch { setDash(null); setErro("Verifique sua conexão e tente novamente."); }
    finally { setCarregando(false); }
  };
  useEffect(() => { if (aba === "dashboard") void carregarDashboard(); }, [aba]);

  const mudarAbaComTeclado = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? ABAS.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + ABAS.length) % ABAS.length;
    setAba(ABAS[next].key); document.getElementById(`relatorio-tab-${ABAS[next].key}`)?.focus();
  };

  return <div className="space-y-4">
    <PageHeader contexto="Gestão · Indicadores" title="Relatórios" subtitle="Acompanhe exceções, desempenho e resultado sem alterar os fatos de origem" actions={<Button type="button" variant="secondary" size="sm" onClick={() => void carregarDashboard()} disabled={carregando}>Atualizar</Button>} />
    <div role="tablist" aria-label="Relatórios por área" className="flex gap-1 overflow-x-auto border-b border-slate-200">
      {ABAS.map((item, index) => <button key={item.key} id={`relatorio-tab-${item.key}`} type="button" role="tab" aria-selected={aba === item.key} aria-controls="relatorio-panel" tabIndex={aba === item.key ? 0 : -1} onClick={() => setAba(item.key)} onKeyDown={(event) => mudarAbaComTeclado(event, index)} className={`whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 focus-visible:ring-offset-1 ${aba === item.key ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800"}`}>{item.label}</button>)}
    </div>
    <div id="relatorio-panel" role="tabpanel" aria-label={ABAS.find((item) => item.key === aba)?.label} tabIndex={0} className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30">
      {aba === "dashboard" ? <Dashboard dash={dash} carregando={carregando} erro={erro} onRetry={carregarDashboard} /> : null}
      {aba === "vendas" ? <Vendas /> : null}{aba === "compras" ? <Compras /> : null}
      {aba === "estoque" ? <Estoque /> : null}{aba === "financeiro" ? <Financeiro /> : null}
    </div>
  </div>;
}

function Dashboard({ dash, carregando, erro, onRetry }: { dash: DashboardExecutivo | null; carregando: boolean; erro: string | null; onRetry: () => Promise<void> }) {
  if (carregando) return <Loading message="Carregando indicadores..." />;
  if (erro || !dash) return <ErrorState message={erro ?? "Nenhum indicador disponível."} onRetry={() => void onRetry()} />;
  return <div className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-base font-semibold text-slate-900">Resumo executivo</h2><p className="text-sm text-slate-500">Use os números para localizar a exceção e corrija o fato no módulo de origem.</p></div><Badge tone="blue">Atualizado agora</Badge></div>
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <StatCard label="Pedidos" value={String(dash.kpis.pedidos)} /><StatCard label="Receita líquida" value={fmtMoney(dash.kpis.receita_liquida)} tone="highlight" /><StatCard label="CMV" value={fmtMoney(dash.kpis.cmv)} /><StatCard label="Margem" value={`${dash.kpis.margem_pct}%`} tone="success" /><StatCard label="Ticket médio" value={fmtMoney(dash.kpis.ticket_medio)} /><StatCard label="Caixa" value={fmtMoney(dash.kpis.caixa)} tone="highlight" /><StatCard label="Inadimplência" value={fmtMoney(dash.kpis.inadimplencia)} tone="danger" /><StatCard label="Estoque valorizado" value={fmtMoney(dash.kpis.estoque_valorizado)} /><StatCard label="Compras em aberto" value={fmtMoney(dash.kpis.compras_abertas)} /><StatCard label="Desconto" value={fmtMoney(dash.kpis.desconto)} />
    </div>
  </div>;
}

function Vendas() {
  const [rows, setRows] = useState<{ chave: number | string; receita_bruta: number; receita_liquida: number; pedidos: number }[] | null>(null);
  const [ag, setAg] = useState("produto"); const [erro, setErro] = useState(false);
  const carregar = async () => { setRows(null); setErro(false); try { setRows((await api.relatorioVendas(ag)).itens); } catch { setErro(true); } };
  useEffect(() => { void carregar(); }, [ag]);
  return <div className="space-y-3"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-base font-semibold text-slate-900">Vendas por agrupamento</h2><p className="text-sm text-slate-500">Compare receita bruta, líquida e pedidos.</p></div><label className="text-xs font-semibold text-slate-600">Agrupar por<Select value={ag} onChange={(e) => setAg(e.target.value)} className="mt-1 min-w-44" aria-label="Agrupamento de vendas"><option value="produto">Produto</option><option value="marca">Marca</option><option value="cliente">Cliente</option><option value="vendedor">Vendedor</option><option value="deposito">Depósito</option></Select></label></div>{rows === null && !erro ? <Loading message="Carregando vendas..." /> : null}{erro ? <ErrorState onRetry={() => void carregar()} /> : null}{rows ? <Table><THead cols={["Chave", "Receita bruta", "Receita líquida", "Pedidos"]} /><TBody>{rows.length ? rows.map((r, i) => <tr key={`${r.chave}-${i}`}><Cell>{String(r.chave)}</Cell><Cell>{fmtMoney(r.receita_bruta)}</Cell><Cell className="font-medium">{fmtMoney(r.receita_liquida)}</Cell><Cell>{r.pedidos}</Cell></tr>) : <EmptyRow colSpan={4} message="Nenhuma venda no período selecionado." />}</TBody></Table> : null}</div>;
}

function Compras() {
  const [r, setR] = useState<{ pedidos: number; recebidos: number; cancelados: number; lead_time_medio_dias: number; comprado: number } | null>(null); const [erro, setErro] = useState(false);
  const carregar = async () => { setR(null); setErro(false); try { setR(await api.relatorioCompras()); } catch { setErro(true); } }; useEffect(() => { void carregar(); }, []);
  if (erro) return <ErrorState onRetry={() => void carregar()} />; if (!r) return <Loading message="Carregando compras..." />;
  return <div className="space-y-3"><div><h2 className="text-base font-semibold text-slate-900">Compras e prazo</h2><p className="text-sm text-slate-500">Acompanhe pedidos, recebimento e lead time médio.</p></div><div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">{[["Pedidos", String(r.pedidos)], ["Recebidos", String(r.recebidos)], ["Cancelados", String(r.cancelados)], ["Lead time médio", `${r.lead_time_medio_dias} dias`], ["Comprado", fmtMoney(r.comprado)]].map(([label, value]) => <StatCard key={label} label={label} value={value} />)}</div></div>;
}

function Estoque() {
  const [r, setR] = useState<{ itens: { sku: string; nome: string; quantidade: number; valor: number }[]; totais: { produtos: number; unidades: number; valor: number; ruptura: number } } | null>(null); const [erro, setErro] = useState(false);
  const carregar = async () => { setR(null); setErro(false); try { setR(await api.relatorioEstoque()); } catch { setErro(true); } }; useEffect(() => { void carregar(); }, []);
  if (erro) return <ErrorState onRetry={() => void carregar()} />; if (!r) return <Loading message="Carregando estoque..." />;
  return <div className="space-y-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-base font-semibold text-slate-900">Estoque valorizado</h2><p className="text-sm text-slate-500">{r.totais.produtos} produtos · {r.totais.unidades} unidades · {fmtMoney(r.totais.valor)}</p></div><Badge tone={r.totais.ruptura ? "red" : "green"}>{r.totais.ruptura} em ruptura</Badge></div><Table><THead cols={["SKU", "Produto", "Qtd", "Valor"]} /><TBody>{r.itens.length ? r.itens.map((i) => <tr key={i.sku}><Cell>{i.sku}</Cell><Cell>{i.nome}</Cell><Cell>{i.quantidade}</Cell><Cell>{fmtMoney(i.valor)}</Cell></tr>) : <EmptyRow colSpan={4} message="Nenhum item disponível para o filtro atual." />}</TBody></Table></div>;
}

function Financeiro() {
  const [r, setR] = useState<{ fluxo_caixa: { entradas: number; saidas: number }; aging: { a_vencer: number; vencido: number }; dre: { receita_liquida: number; cmv: number; lucro_bruto: number } } | null>(null); const [erro, setErro] = useState(false);
  const carregar = async () => { setR(null); setErro(false); try { setR(await api.relatorioFinanceiro()); } catch { setErro(true); } }; useEffect(() => { void carregar(); }, []);
  if (erro) return <ErrorState onRetry={() => void carregar()} />; if (!r) return <Loading message="Carregando financeiro..." />;
  return <div className="space-y-3"><div><h2 className="text-base font-semibold text-slate-900">Financeiro e DRE</h2><p className="text-sm text-slate-500">Leia o resultado e investigue títulos na origem antes de baixar.</p></div><div className="grid grid-cols-1 gap-3 sm:grid-cols-3"><StatCard label="Fluxo de caixa" value={`+${fmtMoney(r.fluxo_caixa.entradas)} / −${fmtMoney(r.fluxo_caixa.saidas)}`} /><StatCard label="Aging a receber" value={`Vencido ${fmtMoney(r.aging.vencido)}`} tone={r.aging.vencido ? "danger" : "success"} sub={`A vencer ${fmtMoney(r.aging.a_vencer)}`} /><StatCard label="Lucro bruto" value={fmtMoney(r.dre.lucro_bruto)} tone="highlight" sub={`Receita ${fmtMoney(r.dre.receita_liquida)} · CMV ${fmtMoney(r.dre.cmv)}`} /></div></div>;
}

export default Relatorios;
