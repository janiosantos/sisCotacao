// pages/relatorios.tsx — Central de relatórios (BI-007): dashboard executivo + vendas/compras/estoque/financeiro.
import { useEffect, useState } from "react";
import { api, type DashboardExecutivo } from "../api/client";
import { fmtMoney } from "../ui/format";
import { Loading, Table, TBody, THead, Cell } from "../ui/ui";

export function Relatorios() {
  const [aba, setAba] = useState<"dashboard" | "vendas" | "compras" | "estoque" | "financeiro">("dashboard");
  const [dash, setDash] = useState<DashboardExecutivo | null>(null);

  useEffect(() => {
    if (aba !== "dashboard") return;
    void api.dashboardExecutivo().then(setDash).catch(() => setDash(null));
  }, [aba]);

  const Card = ({ label, valor }: { label: string; valor: string }) => (
    <div className="rounded-md border border-gray-200 bg-white p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-bold text-gray-800">{valor}</div>
    </div>
  );

  const AbaButton = ({ k, l }: { k: typeof aba; l: string }) => (
    <button
      onClick={() => setAba(k)}
      className={`rounded px-3 py-1 text-sm ${aba === k ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-100"}`}
    >
      {l}
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <AbaButton k="dashboard" l="Dashboard" />
        <AbaButton k="vendas" l="Vendas" />
        <AbaButton k="compras" l="Compras" />
        <AbaButton k="estoque" l="Estoque" />
        <AbaButton k="financeiro" l="Financeiro/DRE" />
      </div>

      {aba === "dashboard" &&
        (dash ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <Card label="Pedidos" valor={String(dash.kpis.pedidos)} />
            <Card label="Receita líquida" valor={fmtMoney(dash.kpis.receita_liquida)} />
            <Card label="CMV" valor={fmtMoney(dash.kpis.cmv)} />
            <Card label="Margem" valor={`${dash.kpis.margem_pct}%`} />
            <Card label="Ticket médio" valor={fmtMoney(dash.kpis.ticket_medio)} />
            <Card label="Caixa" valor={fmtMoney(dash.kpis.caixa)} />
            <Card label="Inadimplência" valor={fmtMoney(dash.kpis.inadimplencia)} />
            <Card label="Estoque valorizado" valor={fmtMoney(dash.kpis.estoque_valorizado)} />
            <Card label="Compras em aberto" valor={fmtMoney(dash.kpis.compras_abertas)} />
            <Card label="Desconto" valor={fmtMoney(dash.kpis.desconto)} />
          </div>
        ) : (
          <Loading />
        ))}

      {aba === "vendas" && <Vendas />}
      {aba === "compras" && <Compras />}
      {aba === "estoque" && <Estoque />}
      {aba === "financeiro" && <Financeiro />}
    </div>
  );
}

export default Relatorios;

function Vendas() {
  const [rows, setRows] = useState<{ chave: number | string; receita_bruta: number; receita_liquida: number; pedidos: number }[] | null>(null);
  const [ag, setAg] = useState("produto");
  useEffect(() => {
    void api.relatorioVendas(ag).then((r) => setRows(r.itens)).catch(() => setRows([]));
  }, [ag]);
  return (
    <div>
      <select value={ag} onChange={(e) => setAg(e.target.value)} className="mb-2 rounded border px-2 py-1 text-sm" aria-label="agrupamento">
        <option value="produto">Produto</option><option value="marca">Marca</option>
        <option value="cliente">Cliente</option><option value="vendedor">Vendedor</option>
        <option value="deposito">Depósito</option>
      </select>
      {rows === null ? <Loading /> : (
        <Table>
          <THead cols={["Chave", "Receita bruta", "Receita líquida", "Pedidos"]} />
          <TBody>
            {rows.map((r, i) => (
              <tr key={i}><Cell>{String(r.chave)}</Cell><Cell>{fmtMoney(r.receita_bruta)}</Cell><Cell className="font-medium">{fmtMoney(r.receita_liquida)}</Cell><Cell>{r.pedidos}</Cell></tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}

function Compras() {
  const [r, setR] = useState<{ pedidos: number; recebidos: number; cancelados: number; lead_time_medio_dias: number; comprado: number } | null>(null);
  useEffect(() => { void api.relatorioCompras().then(setR).catch(() => setR(null)); }, []);
  if (!r) return <Loading />;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {[
        ["Pedidos", String(r.pedidos)], ["Recebidos", String(r.recebidos)], ["Cancelados", String(r.cancelados)],
        ["Lead time médio", `${r.lead_time_medio_dias} dias`], ["Comprado", fmtMoney(r.comprado)],
      ].map(([l, v]) => (
        <div key={l} className="rounded-md border border-gray-200 bg-white p-3">
          <div className="text-xs text-gray-500">{l}</div>
          <div className="text-lg font-bold">{v}</div>
        </div>
      ))}
    </div>
  );
}

function Estoque() {
  const [r, setR] = useState<{ itens: { sku: string; nome: string; quantidade: number; valor: number }[]; totais: { produtos: number; unidades: number; valor: number; ruptura: number } } | null>(null);
  useEffect(() => { void api.relatorioEstoque().then(setR).catch(() => setR(null)); }, []);
  if (!r) return <Loading />;
  return (
    <div>
      <p className="mb-2 text-sm text-gray-600">
        {r.totais.produtos} produtos · {r.totais.unidades} unidades · {fmtMoney(r.totais.valor)} · ruptura {r.totais.ruptura}
      </p>
      <Table>
        <THead cols={["SKU", "Produto", "Qtd", "Valor"]} />
        <TBody>
          {r.itens.map((i) => (
            <tr key={i.sku}><Cell>{i.sku}</Cell><Cell>{i.nome}</Cell><Cell>{i.quantidade}</Cell><Cell>{fmtMoney(i.valor)}</Cell></tr>
          ))}
        </TBody>
      </Table>
    </div>
  );
}

function Financeiro() {
  const [r, setR] = useState<{ fluxo_caixa: { entradas: number; saidas: number }; aging: { a_vencer: number; vencido: number }; dre: { receita_liquida: number; cmv: number; lucro_bruto: number } } | null>(null);
  useEffect(() => { void api.relatorioFinanceiro().then(setR).catch(() => setR(null)); }, []);
  if (!r) return <Loading />;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <div className="rounded-md border border-gray-200 bg-white p-3">
        <div className="text-xs text-gray-500">Fluxo de caixa</div>
        <div className="text-lg font-bold">+{fmtMoney(r.fluxo_caixa.entradas)} / −{fmtMoney(r.fluxo_caixa.saidas)}</div>
      </div>
      <div className="rounded-md border border-gray-200 bg-white p-3">
        <div className="text-xs text-gray-500">Aging receber</div>
        <div className="text-lg font-bold">vencido {fmtMoney(r.aging.vencido)}</div>
        <div className="text-xs text-gray-500">a vencer {fmtMoney(r.aging.a_vencer)}</div>
      </div>
      <div className="rounded-md border border-gray-200 bg-white p-3">
        <div className="text-xs text-gray-500">DRE</div>
        <div className="text-lg font-bold">{fmtMoney(r.dre.lucro_bruto)}</div>
        <div className="text-xs text-gray-500">receita {fmtMoney(r.dre.receita_liquida)} · cmv {fmtMoney(r.dre.cmv)}</div>
      </div>
    </div>
  );
}