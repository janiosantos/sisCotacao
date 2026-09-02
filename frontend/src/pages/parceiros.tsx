// pages/parceiros.tsx — operação da rede de profissionais parceiros.

import { useEffect, useMemo, useState } from "react";
import { Handshake, Plus, RefreshCw, WalletCards } from "lucide-react";
import { api, type Cliente, type ParceiroBonus, type ParceiroLedger, type ParceiroProfissional } from "../api/client";
import { toast } from "../ui/dom";
import { Badge, Button, Card, Cell, Field, Input, Loading, Modal, PageHeader, Select, StatCard, Table, TBody, THead, Textarea } from "../ui/ui";

const categorias = [
  ["eletricista", "Eletricista"], ["encanador", "Encanador"], ["instalador", "Instalador"],
  ["construtor", "Construtor"], ["arquiteto", "Arquiteto"], ["engenheiro", "Engenheiro"],
  ["revenda", "Revenda"], ["outro", "Outro"],
] as const;
const statusLabel: Record<string, string> = { pendente: "Pendente", ativo: "Ativo", suspenso: "Suspenso", bloqueado: "Bloqueado", inativo: "Inativo" };
const statusTone: Record<string, "gray" | "green" | "red" | "amber" | "blue"> = { pendente: "amber", ativo: "green", suspenso: "red", bloqueado: "red", inativo: "gray" };
const categoriaLabel = (value: string) => categorias.find(([key]) => key === value)?.[1] || value;
const money = (value: number) => value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const date = (value?: string | null) => value ? new Date(value).toLocaleDateString("pt-BR") : "—";

export default function Parceiros() {
  const [parceiros, setParceiros] = useState<ParceiroProfissional[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [busca, setBusca] = useState("");
  const [status, setStatus] = useState("");
  const [categoria, setCategoria] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [cadastroAberto, setCadastroAberto] = useState(false);
  const [ledger, setLedger] = useState<ParceiroLedger | null>(null);
  const [selecionado, setSelecionado] = useState<ParceiroProfissional | null>(null);
  const [indicacaoParceiro, setIndicacaoParceiro] = useState<ParceiroProfissional | null>(null);
  const [indicacaoClienteId, setIndicacaoClienteId] = useState("");
  const [criandoIndicacao, setCriandoIndicacao] = useState(false);
  const [clienteId, setClienteId] = useState("");
  const [categoriaForm, setCategoriaForm] = useState("eletricista");
  const [observacao, setObservacao] = useState("");

  const carregar = async () => {
    try {
      const [resultado, listaClientes] = await Promise.all([
        api.listarParceiros({ status: status || undefined, categoria: categoria || undefined, q: busca || undefined }),
        clientes.length ? Promise.resolve(clientes) : api.listarClientes(true),
      ]);
      setParceiros(resultado.parceiros);
      if (!clientes.length) setClientes(listaClientes);
    } catch (error) {
      toast("Erro ao carregar parceiros: " + (error as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => void carregar(), 180);
    return () => window.clearTimeout(timer);
  }, [status, categoria, busca]);

  const resumo = useMemo(() => ({
    total: parceiros.length,
    ativos: parceiros.filter((p) => p.status === "ativo").length,
    pendentes: parceiros.filter((p) => p.status === "pendente").length,
    bloqueados: parceiros.filter((p) => p.status === "bloqueado" || p.status === "suspenso").length,
  }), [parceiros]);

  const salvar = async () => {
    if (!clienteId) { toast("Selecione o cliente que será vinculado ao parceiro.", "error"); return; }
    setSalvando(true);
    try {
      const result = await api.criarParceiro({ cliente_id: Number(clienteId), categoria: categoriaForm, observacao: observacao.trim() || undefined });
      toast(result.duplicado ? "Cliente já estava cadastrado como parceiro." : "Parceiro cadastrado.", "success");
      setCadastroAberto(false); setClienteId(""); setObservacao(""); await carregar();
    } catch (error) {
      toast("Erro ao cadastrar parceiro: " + (error as Error).message, "error");
    } finally { setSalvando(false); }
  };

  const alterarStatus = async (parceiro: ParceiroProfissional, novoStatus: string) => {
    try {
      await api.alterarStatusParceiro(parceiro.id, novoStatus);
      toast(`Parceiro ${novoStatus === "ativo" ? "ativado" : "atualizado"}.`, "success");
      await carregar();
    } catch (error) { toast("Erro ao alterar status: " + (error as Error).message, "error"); }
  };

  const abrirLedger = async (parceiro: ParceiroProfissional) => {
    try { setSelecionado(parceiro); setLedger(await api.ledgerParceiro(parceiro.id)); }
    catch (error) { toast("Erro ao consultar extrato: " + (error as Error).message, "error"); }
  };

  const criarIndicacao = async () => {
    if (!indicacaoParceiro) return;
    setCriandoIndicacao(true);
    try {
      const result = await api.criarIndicacaoParceiro(indicacaoParceiro.id, indicacaoClienteId ? Number(indicacaoClienteId) : undefined);
      toast(`Indicação ${result.codigo} criada.`, "success");
      setIndicacaoParceiro(null);
      setIndicacaoClienteId("");
    } catch (error) { toast("Erro ao criar indicação: " + (error as Error).message, "error"); }
    finally { setCriandoIndicacao(false); }
  };

  const aprovarBonus = async (bonus: ParceiroBonus) => {
    try {
      await api.aprovarBonusParceiro(bonus.id);
      toast("Bônus aprovado para pagamento.", "success");
      if (selecionado) setLedger(await api.ledgerParceiro(selecionado.id));
    } catch (error) { toast("Erro ao aprovar bônus: " + (error as Error).message, "error"); }
  };

  const pagarBonus = async (bonus: ParceiroBonus) => {
    try {
      await api.pagarBonusParceiro(bonus.id);
      toast("Bônus marcado como pago.", "success");
      if (selecionado) setLedger(await api.ledgerParceiro(selecionado.id));
    } catch (error) { toast("Erro ao pagar bônus: " + (error as Error).message, "error"); }
  };

  return <div>
    <PageHeader title="Parceiros profissionais" subtitle="Controle indicações, relacionamento e recompensas com rastreabilidade por venda." actions={<div className="flex gap-2"><Button aria-label="Atualizar lista" onClick={() => void carregar()}><RefreshCw size={15} /></Button><Button variant="primary" onClick={() => setCadastroAberto(true)}><Plus size={16} /> Novo parceiro</Button></div>} />

    <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Parceiros encontrados" value={String(resumo.total)} sub="Resultado dos filtros atuais" />
      <StatCard label="Ativos" value={String(resumo.ativos)} sub="Aptos a indicar clientes" tone="success" />
      <StatCard label="Aguardando aprovação" value={String(resumo.pendentes)} sub="Requer análise operacional" tone="highlight" />
      <StatCard label="Suspensos ou bloqueados" value={String(resumo.bloqueados)} sub="Fora do programa" tone="danger" />
    </div>

    <Card className="mb-4 p-3"><div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_180px_auto] md:items-end">
      <Field label="Pesquisar"><Input value={busca} onChange={(event) => setBusca(event.target.value)} placeholder="Nome, documento ou código" /></Field>
      <Field label="Status"><Select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Todos</option>{Object.entries(statusLabel).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Select></Field>
      <Field label="Categoria"><Select value={categoria} onChange={(event) => setCategoria(event.target.value)}><option value="">Todas</option>{categorias.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Select></Field>
      <div className="pb-0.5 text-right text-xs text-slate-500">{parceiros.length} registro(s)</div>
    </div></Card>

    {carregando ? <Loading message="Carregando rede de parceiros…" /> : parceiros.length === 0 ? <div className="rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center text-sm text-slate-500"><Handshake className="mx-auto mb-3 text-slate-300" size={30} />Nenhum parceiro encontrado com os filtros atuais.</div> : <Table>
      <THead cols={["Parceiro", "Categoria", "Nível", "Status", "Cadastro", "Ações"]} />
      <TBody>{parceiros.map((parceiro) => <tr key={parceiro.id} className="hover:bg-slate-50">
        <Cell><div className="font-semibold text-slate-900">{parceiro.cliente_nome}</div><div className="font-mono text-[11px] text-slate-500">{parceiro.codigo} · {parceiro.cliente_doc || "sem documento"}</div></Cell>
        <Cell>{categoriaLabel(parceiro.categoria)}</Cell><Cell><Badge tone="blue">{parceiro.nivel}</Badge></Cell>
        <Cell><Badge tone={statusTone[parceiro.status] || "gray"}>{statusLabel[parceiro.status] || parceiro.status}</Badge></Cell><Cell className="text-xs text-slate-500">{date(parceiro.criado_em)}</Cell>
        <Cell><div className="flex flex-wrap justify-end gap-1.5"><Button size="sm" onClick={() => void abrirLedger(parceiro)}><WalletCards size={14} /> Extrato</Button>{parceiro.status === "ativo" ? <Button size="sm" variant="outline" onClick={() => setIndicacaoParceiro(parceiro)}>Nova indicação</Button> : null}{parceiro.status === "pendente" ? <Button size="sm" variant="primary" onClick={() => void alterarStatus(parceiro, "ativo")}>Aprovar</Button> : null}{parceiro.status === "ativo" ? <Button size="sm" variant="ghost" onClick={() => void alterarStatus(parceiro, "suspenso")}>Suspender</Button> : null}{parceiro.status === "suspenso" ? <Button size="sm" variant="outline" onClick={() => void alterarStatus(parceiro, "ativo")}>Reativar</Button> : null}</div></Cell>
      </tr>)}</TBody>
    </Table>}

    <Modal open={cadastroAberto} title="Cadastrar parceiro profissional" onClose={() => setCadastroAberto(false)} footer={<div className="flex justify-end gap-2"><Button onClick={() => setCadastroAberto(false)}>Cancelar</Button><Button variant="primary" disabled={salvando} onClick={() => void salvar()}>{salvando ? "Salvando…" : "Cadastrar parceiro"}</Button></div>}>
      <div className="space-y-4 p-4 sm:p-5"><Field label="Cliente vinculado" hint="O parceiro precisa existir no cadastro de clientes."><Select value={clienteId} onChange={(event) => setClienteId(event.target.value)}><option value="">Selecione um cliente</option>{clientes.map((cliente) => <option key={cliente.id} value={cliente.id}>{cliente.nome}{cliente.doc ? ` · ${cliente.doc}` : ""}</option>)}</Select></Field><Field label="Categoria profissional"><Select value={categoriaForm} onChange={(event) => setCategoriaForm(event.target.value)}>{categorias.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Select></Field><Field label="Observação"><Textarea value={observacao} onChange={(event) => setObservacao(event.target.value)} placeholder="Região de atendimento, especialidades ou acordo comercial" /></Field></div>
    </Modal>

    <Modal open={Boolean(indicacaoParceiro)} title="Nova indicação" onClose={() => { setIndicacaoParceiro(null); setIndicacaoClienteId(""); }} footer={<div className="flex justify-end gap-2"><Button onClick={() => setIndicacaoParceiro(null)}>Cancelar</Button><Button variant="primary" disabled={criandoIndicacao} onClick={() => void criarIndicacao()}>{criandoIndicacao ? "Gerando…" : "Gerar código"}</Button></div>}>
      <div className="space-y-4 p-4 sm:p-5"><p className="text-sm text-slate-600">O código será vinculado ao parceiro <strong>{indicacaoParceiro?.cliente_nome}</strong> e poderá ser associado a uma venda concluída.</p><Field label="Cliente indicado (opcional)" hint="Deixe em branco para permitir a vinculação no atendimento."><Select value={indicacaoClienteId} onChange={(event) => setIndicacaoClienteId(event.target.value)}><option value="">Sem cliente definido</option>{clientes.map((cliente) => <option key={cliente.id} value={cliente.id}>{cliente.nome}{cliente.doc ? ` · ${cliente.doc}` : ""}</option>)}</Select></Field></div>
    </Modal>

    <Modal open={Boolean(ledger && selecionado)} title={`Extrato · ${selecionado?.cliente_nome || "Parceiro"}`} wide onClose={() => { setLedger(null); setSelecionado(null); }}>
      {ledger ? <div className="space-y-5 p-4 sm:p-5"><div className="grid gap-3 sm:grid-cols-3"><StatCard label="Saldo de pontos" value={ledger.saldo_pontos.toLocaleString("pt-BR")} sub="Calculado pelo ledger" tone="highlight" /><StatCard label="Movimentações" value={String(ledger.pontos.length)} /><StatCard label="Bônus registrados" value={String(ledger.bonus.length)} /></div><section aria-labelledby="bonus-title"><h3 id="bonus-title" className="mb-2 text-sm font-semibold text-slate-800">Bônus</h3><Table><THead cols={["Valor", "Status", "Origem", "Data", "Ações"]} /><TBody>{ledger.bonus.length ? ledger.bonus.map((bonus) => <tr key={bonus.id}><Cell className="font-semibold">{money(Number(bonus.valor))}</Cell><Cell><Badge tone={bonus.status === "pendente" ? "amber" : bonus.status === "pago" ? "green" : "gray"}>{bonus.status}</Badge></Cell><Cell>Indicação #{bonus.indicacao_id || "—"}</Cell><Cell>{date(bonus.criado_em)}</Cell><Cell>{bonus.status === "pendente" ? <Button size="sm" variant="primary" onClick={() => void aprovarBonus(bonus)}>Aprovar</Button> : bonus.status === "aprovado" ? <Button size="sm" variant="primary" onClick={() => void pagarBonus(bonus)}>Marcar pago</Button> : null}</Cell></tr>) : <tr><Cell>Nenhum bônus registrado.</Cell></tr>}</TBody></Table></section><section aria-labelledby="points-title"><h3 id="points-title" className="mb-2 text-sm font-semibold text-slate-800">Movimentações de pontos</h3><Table><THead cols={["Tipo", "Pontos", "Origem", "Data"]} /><TBody>{ledger.pontos.map((ponto) => <tr key={ponto.id}><Cell>{ponto.tipo}</Cell><Cell className={ponto.tipo === "debito" || ponto.tipo === "expiracao" ? "text-red-600" : "text-emerald-600"}>{ponto.tipo === "debito" || ponto.tipo === "expiracao" ? "-" : "+"}{Number(ponto.pontos).toLocaleString("pt-BR")}</Cell><Cell>{ponto.origem_tipo || "Ajuste operacional"}</Cell><Cell>{date(ponto.criado_em)}</Cell></tr>)}</TBody></Table></section></div> : <Loading />}
    </Modal>
  </div>;
}
