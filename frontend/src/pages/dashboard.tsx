// pages/dashboard.tsx — painel de indicadores (React + Tailwind).

import { useEffect, useState } from "react";
import { api } from "../api/client";
import { fmtMoney } from "../ui/format";
import { Badge, Button, Cell, EmptyRow, ErrorState, Loading, PageHeader, StatCard, Table, TBody, THead } from "../ui/ui";
import { Section } from "./dashboard/section";

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
  estoque_baixo: { produto_id: number; nome: string; sku: string; quantidade: number; estoque_minimo: number; deposito: string }[];
  top_vendas: { nome: string; sku: string; qtd: number; receita: number }[];
}

type Reposicao = {
  produto_id: number;
  nome: string;
  sku: string;
  unidade_venda: string;
  quantidade: number;
  estoque_minimo: number;
  estoque_maximo: number;
  custo: number | null;
  sugestao_qtd: number;
  custo_total: number;
};

type Comissao = {
  id: number;
  nome: string;
  comissao_pct: number;
  n_vendas: number;
  total_vendas: number;
  comissao: number;
};

export default function Dashboard() {
  const [d, setD] = useState<DashboardData | null>(null);
  const [reposicao, setReposicao] = useState<Reposicao[]>([]);
  const [comissoes, setComissoes] = useState<Comissao[]>([]);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    setErro("");
    try {
      const data = await api.requestDashboard();
      const [rep, com] = await Promise.all([
        api.reposicaoSugerida() as Promise<Reposicao[]>,
        api.comissoes() as Promise<Comissao[]>,
      ]);
      setD(data);
      setReposicao(rep);
      setComissoes(com);
    } catch (e) {
      setErro((e as Error).message || "Servidor indisponível");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => { void carregar(); }, []);

  if (erro) {
    return <ErrorState message={`Erro ao carregar o painel: ${erro}`} onRetry={() => void carregar()} />;
  }
  if (carregando || !d) return <Loading message="Carregando painel…" />;

  const r = d.resumo;

  return (
    <div>
      <PageHeader
        title="Painel"
        subtitle={`Indicadores do negócio — atualizados em ${r.hoje}.`}
        actions={
          <a href="#/pre-venda">
            <Button variant="primary">+ Nova pré-venda</Button>
          </a>
        }
      />

      <section className="erp-dashboard-hero" aria-labelledby="dashboard-foco">
        <div>
          <div className="erp-eyebrow">Visão operacional</div>
          <h2 id="dashboard-foco">Decida o próximo movimento da loja</h2>
          <p>Use os alertas de estoque, vendas e financeiro para priorizar a operação sem abrir vários módulos.</p>
          <div className="erp-dashboard-actions">
            <a href="#/relatorios"><Button variant="primary" size="sm">Abrir relatórios</Button></a>
            <a href="#/compras"><Button variant="ghost" size="sm">Planejar compras</Button></a>
          </div>
        </div>
        <div className="erp-dashboard-summary" aria-label="Resumo da operação">
          <span>Hoje</span>
          <strong>{r.vendas_hoje.n} pedido(s)</strong>
          <div><span>Estoque baixo</span><b className={r.estoque_baixo ? "is-alert" : ""}>{r.estoque_baixo}</b></div>
          <div><span>Vencido a receber</span><b className={r.receber_vencidas ? "is-alert" : ""}>{fmtMoney(r.receber_vencidas)}</b></div>
        </div>
      </section>

      <div className="erp-kpi-grid grid grid-cols-2 gap-4 lg:grid-cols-3 2xl:grid-cols-6">
        <StatCard label="Vendas hoje" value={fmtMoney(r.vendas_hoje.total)} sub={`${r.vendas_hoje.n} pedido(s)`} />
        <StatCard label="Vendas no mês" value={fmtMoney(r.vendas_mes.total)} sub={`${r.vendas_mes.n} pedido(s)`} tone="highlight" />
        <StatCard label="A receber (a vencer)" value={fmtMoney(r.receber_a_vencer)} />
        <StatCard label="A receber (vencido)" value={fmtMoney(r.receber_vencidas)} tone={r.receber_vencidas > 0 ? "danger" : "default"} />
        <StatCard label="A pagar (a vencer)" value={fmtMoney(r.pagar_a_vencer)} />
        <StatCard label="Valor em estoque" value={fmtMoney(r.valor_estoque)} />
      </div>

      {r.estoque_baixo > 0 ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800" role="status">
          <Badge tone="amber">Estoque</Badge>
          {r.estoque_baixo} produto(s) abaixo do estoque mínimo.
          <a href="#/estoque" className="ml-auto font-semibold text-amber-900 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-700">Ver estoque</a>
          <a href="#/compras" className="font-semibold text-amber-900 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-700">Abrir compras</a>
        </div>
      ) : null}

      {r.receber_vencidas > 0 ? (
        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800" role="alert">
          <Badge tone="red">Financeiro</Badge>
          Há {fmtMoney(r.receber_vencidas)} vencido a receber.
          <a href="#/financeiro" className="ml-auto font-semibold text-red-900 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700">Revisar títulos</a>
        </div>
      ) : null}

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Section title="Mais vendidos (30 dias)">
          <Table>
            <THead cols={["#", "Produto", <span className="text-right">Qtd</span>, <span className="text-right">Receita</span>]} />
            <TBody>
              {d.top_vendas.length === 0 ? (
                <EmptyRow colSpan={4} message="Sem vendas no período" />
              ) : (
                d.top_vendas.map((t, i) => (
                  <tr key={i}>
                    <Cell>{i + 1}</Cell>
                    <Cell>
                      <span className="font-medium">{t.nome}</span>
                      {t.sku ? <div className="font-mono text-xs text-gray-400">{t.sku}</div> : null}
                    </Cell>
                    <Cell className="text-right">{t.qtd}</Cell>
                    <Cell className="text-right">{fmtMoney(t.receita)}</Cell>
                  </tr>
                ))
              )}
            </TBody>
          </Table>
        </Section>

        <Section title="Estoque abaixo do mínimo">
          <Table>
            <THead cols={["Produto", <span className="text-right">Atual</span>, <span className="text-right">Mínimo</span>, "Depósito"]} />
            <TBody>
              {d.estoque_baixo.length === 0 ? (
                <EmptyRow colSpan={4} message="Nenhum produto abaixo do mínimo" />
              ) : (
                d.estoque_baixo.map((s) => (
                  <tr key={s.produto_id}>
                    <Cell>
                      <span className="font-medium">{s.nome}</span>
                      {s.sku ? <div className="font-mono text-xs text-gray-400">{s.sku}</div> : null}
                    </Cell>
                    <Cell className="text-right">{s.quantidade}</Cell>
                    <Cell className="text-right">{s.estoque_minimo}</Cell>
                    <Cell>{s.deposito || "—"}</Cell>
                  </tr>
                ))
              )}
            </TBody>
          </Table>
        </Section>

        <Section title="Reposição sugerida (compras)">
          <Table>
            <THead cols={["Produto", <span className="text-right">Atual</span>, <span className="text-right">Mínimo</span>, <span className="text-right">Sugerido</span>, <span className="text-right">Custo est.</span>]} />
            <TBody>
              {reposicao.length === 0 ? (
                <EmptyRow colSpan={5} message="Nada a repor" />
              ) : (
                reposicao.map((p) => (
                  <tr key={p.produto_id}>
                    <Cell>
                      <span className="font-medium">{p.nome}</span>
                      {p.sku ? <div className="font-mono text-xs text-gray-400">{p.sku}</div> : null}
                    </Cell>
                    <Cell className="text-right">{p.quantidade}</Cell>
                    <Cell className="text-right">{p.estoque_minimo}</Cell>
                    <Cell className="text-right">{p.sugestao_qtd}</Cell>
                    <Cell className="text-right">{p.custo != null ? fmtMoney(p.custo_total) : "—"}</Cell>
                  </tr>
                ))
              )}
            </TBody>
          </Table>
        </Section>

        <Section title="Comissões de vendedores (30 dias)">
          <Table>
            <THead cols={["Vendedor", <span className="text-right">Vendas</span>, <span className="text-right">Total</span>, <span className="text-right">%</span>, <span className="text-right">Comissão</span>]} />
            <TBody>
              {comissoes.length === 0 ? (
                <EmptyRow colSpan={5} message="Sem comissões no período" />
              ) : (
                comissoes.map((c) => (
                  <tr key={c.id}>
                    <Cell>{c.nome}</Cell>
                    <Cell className="text-right">{c.n_vendas}</Cell>
                    <Cell className="text-right">{fmtMoney(c.total_vendas)}</Cell>
                    <Cell className="text-right">{c.comissao_pct}%</Cell>
                    <Cell className="text-right font-medium">{fmtMoney(c.comissao)}</Cell>
                  </tr>
                ))
              )}
            </TBody>
          </Table>
        </Section>
      </div>
    </div>
  );
}

