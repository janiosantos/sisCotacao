import { useEffect, useState } from "react";
import { api, type ApuracaoCompetencia, type CompetenciaFinanceira, type ContaPagar, type ContaPlano, type CentroCusto, type ContaRateioPayload } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Card, Cell, EmptyRow, Field, Input, Loading, Modal, Select, Table, TBody, THead } from "../../ui/ui";

const hojeCompetencia = () => new Date().toISOString().slice(0, 7);

export function ClassificacaoDespesas() {
  const [pendencias, setPendencias] = useState<ContaPagar[]>([]);
  const [totalPendencias, setTotalPendencias] = useState(0);
  const [contas, setContas] = useState<ContaPlano[]>([]);
  const [centros, setCentros] = useState<CentroCusto[]>([]);
  const [competencias, setCompetencias] = useState<CompetenciaFinanceira[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [selecionada, setSelecionada] = useState<ContaPagar | null>(null);
  const [form, setForm] = useState({ plano: "", competencia: hojeCompetencia(), centro: "", observacao: "" });
  const [usarRateio, setUsarRateio] = useState(false);
  const [linhasRateio, setLinhasRateio] = useState([{ centro: "", percentual: "100", valor: "", elegivel: true }]);
  const [novaCompetencia, setNovaCompetencia] = useState({ competencia: hojeCompetencia(), faturamento: "", fonte: "realizado" });
  const [apuracao, setApuracao] = useState<ApuracaoCompetencia | null>(null);

  const carregar = async () => {
    setCarregando(true);
    try {
      const [p, c, cc, comps] = await Promise.all([
        api.listarPendenciasClassificacao({ limit: 100 }),
        api.listarPlanoContas("despesa", true),
        api.listarCentrosCusto(),
        api.listarCompetenciasFinanceiras(),
      ]);
      setPendencias(p.items); setTotalPendencias(p.total); setContas(c); setCentros(cc); setCompetencias(comps);
    } catch (e) { toast("Erro ao carregar classificação financeira: " + (e as Error).message, "error"); }
    finally { setCarregando(false); }
  };

  useEffect(() => { void carregar(); }, []);

  const abrir = (row: ContaPagar) => {
    setSelecionada(row);
    setForm({ plano: row.plano_conta_id ? String(row.plano_conta_id) : "", competencia: row.competencia || hojeCompetencia(), centro: row.centro_custo_id ? String(row.centro_custo_id) : "", observacao: "" });
    setUsarRateio(false);
    setLinhasRateio([{ centro: row.centro_custo_id ? String(row.centro_custo_id) : "", percentual: "100", valor: String(row.valor || ""), elegivel: Boolean(row.elegivel_precificacao) }]);
  };

  const salvar = async () => {
    if (!selecionada || !form.plano) return;
    if (usarRateio && Math.abs(linhasRateio.reduce((total, linha) => total + (Number(linha.percentual.replace(",", ".")) || 0), 0) - 100) > 0.001) {
      toast("O rateio deve totalizar 100%", "error");
      return;
    }
    try {
      await api.classificarContaPagar(selecionada.id, { plano_conta_id: Number(form.plano), competencia: form.competencia, centro_custo_id: form.centro ? Number(form.centro) : undefined, observacao_classificacao: form.observacao || undefined });
      if (usarRateio) {
        const items: ContaRateioPayload[] = linhasRateio.map((linha) => ({
          centro_custo_id: linha.centro ? Number(linha.centro) : undefined,
          percentual: Number(linha.percentual.replace(",", ".")) || 0,
          valor: linha.valor ? Number(linha.valor.replace(",", ".")) : Number(selecionada.valor || 0) * (Number(linha.percentual.replace(",", ".")) || 0) / 100,
          competencia: form.competencia,
          politica_rateio: contas.find((conta) => conta.id === Number(form.plano))?.politica_rateio || "apropriar_direto",
          elegivel_precificacao: linha.elegivel,
        }));
        await api.criarRateioContaPagar(selecionada.id, items);
      }
      setSelecionada(null); toast("Conta classificada", "success"); await carregar();
    } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  };

  const criarCompetencia = async () => {
    try {
      await api.criarCompetenciaFinanceira({ competencia: novaCompetencia.competencia, faturamento_base: Number(novaCompetencia.faturamento.replace(",", ".")) || 0, faturamento_fonte: novaCompetencia.fonte, criterio_apuracao: "competencia" });
      toast("Competência salva", "success"); await carregar();
    } catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  };

  const mudarStatus = async (comp: string, status: string) => {
    try { await api.alterarStatusCompetenciaFinanceira(comp, status); toast(`Competência ${status}`, "success"); await carregar(); }
    catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  };

  const verApuracao = async (comp: string) => {
    try { setApuracao(await api.apurarCompetenciaFinanceira(comp)); }
    catch (e) { toast("Erro: " + (e as Error).message, "error"); }
  };

  return (
    <div className="space-y-5">
      <Card className="border-amber-200 bg-amber-50/50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold text-slate-900">Classificação financeira</h2><p className="mt-1 text-sm text-slate-600">Toda despesa deve ter conta, competência e origem antes de alimentar relatórios ou precificação.</p></div><Badge tone={totalPendencias ? "amber" : "green"}>{totalPendencias} pendência(s)</Badge></div>
      </Card>

      <Card className="overflow-hidden p-0">
        <div className="border-b border-slate-100 p-4"><h3 className="font-semibold text-slate-900">Pendências de classificação</h3><p className="mt-1 text-xs text-slate-500">Lançamentos antigos ou sem regra ficam pendentes e não entram no rateio aprovado.</p></div>
        {carregando ? <Loading /> : <Table><THead cols={["Fornecedor", "Descrição", "Valor", "Vencimento", "Competência", "Status", ""]} /><TBody>{pendencias.length === 0 ? <EmptyRow colSpan={7} message="Nenhuma pendência de classificação" /> : pendencias.map((row) => <tr key={row.id}><Cell className="font-medium">{row.fornecedor}</Cell><Cell>{row.descricao || "—"}</Cell><Cell>{fmtMoney(row.valor)}</Cell><Cell className="text-xs">{fmtDate(row.data_vencimento)}</Cell><Cell className="font-mono text-xs">{row.competencia || "—"}</Cell><Cell><Badge tone={row.status_classificacao === "rejeitada" ? "red" : "amber"}>{row.status_classificacao || "pendente"}</Badge></Cell><Cell><Button size="sm" onClick={() => abrir(row)}>Classificar</Button></Cell></tr>)}</TBody></Table>}
      </Card>

      <Card className="p-4"><div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><h3 className="font-semibold text-slate-900">Competências para precificação</h3><p className="mt-1 text-xs text-slate-500">Somente competências aprovadas ou fechadas podem alimentar o motor.</p></div><div className="grid grid-cols-1 gap-2 sm:grid-cols-3"><Field label="Competência"><Input type="month" value={novaCompetencia.competencia} onChange={(e) => setNovaCompetencia({ ...novaCompetencia, competencia: e.target.value })} /></Field><Field label="Faturamento base"><Input type="number" min="0" step="0.01" value={novaCompetencia.faturamento} onChange={(e) => setNovaCompetencia({ ...novaCompetencia, faturamento: e.target.value })} /></Field><Button variant="primary" onClick={() => void criarCompetencia()}>Salvar competência</Button></div></div><Table><THead cols={["Competência", "Faturamento", "Fonte", "Status", "Ações"]} /><TBody>{competencias.length === 0 ? <EmptyRow colSpan={5} message="Nenhuma competência cadastrada" /> : competencias.map((c) => <tr key={c.id}><Cell className="font-mono font-medium">{c.competencia}</Cell><Cell>{fmtMoney(c.faturamento_base)}</Cell><Cell>{c.faturamento_fonte}</Cell><Cell><Badge tone={c.status === "fechada" || c.status === "aprovada" ? "green" : "amber"}>{c.status}</Badge></Cell><Cell><div className="flex flex-wrap justify-end gap-2"><Button size="sm" onClick={() => void verApuracao(c.competencia)}>Apurar</Button>{c.status === "aberta" || c.status === "reaberta" ? <Button size="sm" onClick={() => void mudarStatus(c.competencia, "aprovada")}>Aprovar</Button> : null}{c.status === "aprovada" ? <Button size="sm" variant="primary" onClick={() => void mudarStatus(c.competencia, "fechada")}>Fechar</Button> : null}</div></Cell></tr>)}</TBody></Table>{apuracao ? <div className="mt-4 grid gap-3 rounded-lg bg-slate-50 p-4 text-sm sm:grid-cols-4"><div><span className="block text-xs text-slate-500">Fixas elegíveis</span><strong>{fmtMoney(apuracao.despesas_fixas)} ({apuracao.despesa_fixa_pct == null ? "—" : `${apuracao.despesa_fixa_pct}%`})</strong></div><div><span className="block text-xs text-slate-500">Variáveis elegíveis</span><strong>{fmtMoney(apuracao.despesas_variaveis)} ({apuracao.despesa_variavel_pct == null ? "—" : `${apuracao.despesa_variavel_pct}%`})</strong></div><div><span className="block text-xs text-slate-500">Custos diretos</span><strong>{fmtMoney(apuracao.custos_diretos)}</strong></div><div><span className="block text-xs text-slate-500">Pendências</span><strong>{apuracao.pendencias_classificacao}</strong></div></div> : null}</Card>

      <Modal open={selecionada != null} onClose={() => setSelecionada(null)} title={selecionada ? `Classificar conta #${selecionada.id}` : "Classificar conta"} footer={<><Button onClick={() => setSelecionada(null)}>Cancelar</Button><Button variant="primary" onClick={() => void salvar()} disabled={!form.plano}>Salvar classificação</Button></>}>
        <div className="space-y-4"><p className="text-sm text-slate-600">{selecionada?.fornecedor} · {fmtMoney(selecionada?.valor || 0)} · {selecionada?.descricao || "Sem descrição"}</p><Field label="Plano de contas *"><Select value={form.plano} onChange={(e) => setForm({ ...form, plano: e.target.value })}><option value="">Selecione…</option>{contas.map((c) => <option key={c.id} value={c.id}>{c.codigo} · {c.nome} ({c.natureza_custo || "fora"})</option>)}</Select></Field><div className="grid gap-3 sm:grid-cols-2"><Field label="Competência *"><Input type="month" value={form.competencia} onChange={(e) => setForm({ ...form, competencia: e.target.value })} /></Field><Field label="Centro de custo"><Select value={form.centro} onChange={(e) => setForm({ ...form, centro: e.target.value })}><option value="">Sem centro</option>{centros.map((c) => <option key={c.id} value={c.id}>{c.codigo} · {c.nome}</option>)}</Select></Field></div><Field label="Observação da classificação"><Input value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} placeholder="Motivo ou referência da classificação" /></Field>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3"><label className="flex items-center gap-2 text-sm font-medium text-slate-800"><input type="checkbox" checked={usarRateio} onChange={(e) => setUsarRateio(e.target.checked)} /> Distribuir esta despesa por centro de custo</label>{usarRateio ? <div className="mt-3 space-y-2">{linhasRateio.map((linha, index) => <div key={index} className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_100px_120px_auto]"><Select aria-label={`Centro do rateio ${index + 1}`} value={linha.centro} onChange={(e) => setLinhasRateio(linhasRateio.map((item, i) => i === index ? { ...item, centro: e.target.value } : item))}><option value="">Sem centro</option>{centros.map((c) => <option key={c.id} value={c.id}>{c.codigo} · {c.nome}</option>)}</Select><Input aria-label={`Percentual do rateio ${index + 1}`} type="number" min="0" max="100" step="0.01" value={linha.percentual} onChange={(e) => setLinhasRateio(linhasRateio.map((item, i) => i === index ? { ...item, percentual: e.target.value } : item))} /><Input aria-label={`Valor do rateio ${index + 1}`} type="number" min="0" step="0.01" value={linha.valor} onChange={(e) => setLinhasRateio(linhasRateio.map((item, i) => i === index ? { ...item, valor: e.target.value } : item))} /><Button size="sm" variant="ghost" disabled={linhasRateio.length === 1} onClick={() => setLinhasRateio(linhasRateio.filter((_, i) => i !== index))}>Remover</Button></div>)}<Button size="sm" onClick={() => setLinhasRateio([...linhasRateio, { centro: "", percentual: "0", valor: "", elegivel: true }])}>+ Linha</Button><p className="text-xs text-slate-500">Percentuais devem totalizar 100%. O valor pode ser calculado pelo percentual quando deixado vazio.</p></div> : null}</div>
        </div>
      </Modal>
    </div>
  );
}
