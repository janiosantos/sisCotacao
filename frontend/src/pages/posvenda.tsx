// pages/posvenda.tsx — pós-venda (React + Tailwind).

import { useEffect, useState } from "react";
import { api } from "../api/client";
import { fmtDate } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, PageHeader, Select, Table, TBody, THead, Textarea } from "../ui/ui";

type Aba = "acompanhamento" | "garantia" | "devolucao";

export default function PosVenda() {
  const [aba, setAba] = useState<Aba>("acompanhamento");

  return (
    <div>
      <PageHeader title="Pós-venda" subtitle="Acompanhamento de clientes e garantia." />
      <div className="mb-5 flex gap-2 border-b border-gray-200">
        {(["acompanhamento", "garantia", "devolucao"] as Aba[]).map((a) => (
          <button
            key={a}
            onClick={() => setAba(a)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              aba === a ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {a === "acompanhamento" ? "Acompanhamento" : a === "garantia" ? "Garantia" : "Devolução / Troca"}
          </button>
        ))}
      </div>
      {aba === "acompanhamento" ? <Acompanhamento /> : aba === "garantia" ? <Garantia /> : <Devolucao />}
    </div>
  );
}

interface Interacao {
  id: number;
  cliente_nome: string;
  tipo: string;
  descricao: string;
  data_contato: string;
  data_proximo_contato: string | null;
}

function Acompanhamento() {
  const [rows, setRows] = useState<Interacao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [filtroCliId, setFiltroCliId] = useState("");
  const [pendentes, setPendentes] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ cliente: "", tipo: "ligacao", data: "", desc: "", prox: "", orc: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarInteracoes({ cliente_id: filtroCliId ? Number(filtroCliId) : undefined, pendentes }));
    } catch {
      toast("Erro ao carregar interações", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const salvar = async () => {
    try {
      await api.criarInteracao({
        cliente_nome: form.cliente.trim(),
        tipo: form.tipo,
        data_contato: form.data,
        descricao: form.desc.trim(),
        data_proximo_contato: form.prox || undefined,
        orcamento_id: Number(form.orc) || undefined,
      });
      setModalOpen(false);
      toast("Interação registrada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Nova interação
        </Button>
        <Field label="Cliente ID">
          <Input type="number" value={filtroCliId} onChange={(e) => setFiltroCliId(e.target.value)} className="w-32" />
        </Field>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" className="h-4 w-4 rounded border-gray-300" checked={pendentes} onChange={(e) => setPendentes(e.target.checked)} />
          Pendentes
        </label>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Data", "Cliente", "Tipo", "Descrição", "Próx. contato"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={5} message="Nenhuma interação" />
            ) : (
              rows.map((i) => (
                <tr key={i.id} className="hover:bg-gray-50">
                  <Cell className="text-xs text-gray-500">{fmtDate(i.data_contato)}</Cell>
                  <Cell className="font-medium">{i.cliente_nome}</Cell>
                  <Cell>
                    <Badge tone="gray">{i.tipo}</Badge>
                  </Cell>
                  <Cell>{i.descricao}</Cell>
                  <Cell className="text-xs text-gray-500">{i.data_proximo_contato ? fmtDate(i.data_proximo_contato) : "—"}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nova interação"
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Cliente">
            <Input placeholder="Nome" value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })} autoFocus />
          </Field>
          <Field label="Tipo">
            <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              {["ligacao", "visita", "email", "whatsapp", "follow_up", "outro"].map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Data do contato">
            <Input type="date" value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} />
          </Field>
          <Field label="Descrição">
            <Textarea value={form.desc} onChange={(e) => setForm({ ...form, desc: e.target.value })} />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Próximo contato">
              <Input type="date" value={form.prox} onChange={(e) => setForm({ ...form, prox: e.target.value })} />
            </Field>
            <Field label="Orçamento ID">
              <Input type="number" value={form.orc} onChange={(e) => setForm({ ...form, orc: e.target.value })} />
            </Field>
          </div>
        </div>
      </Modal>
    </div>
  );
}

interface GarantiaRow {
  id: number;
  cliente_nome: string;
  produto_nome: string;
  data_inicio: string;
  data_fim: string;
  dias: number;
  status: string;
}

function Garantia() {
  const [rows, setRows] = useState<GarantiaRow[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ cliente: "", produto: "", inicio: "", fim: "", dias: "90", desc: "", obs: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarGarantias());
    } catch {
      toast("Erro ao carregar garantias", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    try {
      await api.criarGarantia({
        cliente_nome: form.cliente.trim(),
        produto_nome: form.produto.trim(),
        data_inicio: form.inicio,
        data_fim: form.fim,
        dias: parseInt(form.dias, 10) || 90,
        descricao: form.desc.trim() || undefined,
        observacao: form.obs.trim() || undefined,
      });
      setModalOpen(false);
      toast("Garantia registrada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alterarStatus = async (g: GarantiaRow) => {
    const novos: Record<string, string> = { ativa: "acionada", acionada: "cancelada", cancelada: "ativa", vencida: "ativa" };
    const novo = novos[g.status] || "ativa";
    try {
      await api.atualizarStatusGarantia(g.id, novo);
      toast(`Status alterado para ${novo}`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const statusTone = (s: string) => (s === "ativa" ? "green" : s === "vencida" ? "gray" : "red");

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Nova garantia
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Cliente", "Produto", "Início", "Fim", "Dias", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={7} message="Nenhuma garantia" />
            ) : (
              rows.map((g) => (
                <tr key={g.id} className="hover:bg-gray-50">
                  <Cell className="font-medium">{g.cliente_nome}</Cell>
                  <Cell>{g.produto_nome}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(g.data_inicio)}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(g.data_fim)}</Cell>
                  <Cell>{g.dias}</Cell>
                  <Cell>
                    <Badge tone={statusTone(g.status)}>{g.status}</Badge>
                  </Cell>
                  <Cell>
                    <Button size="sm" variant="ghost" onClick={() => alterarStatus(g)}>
                      Alterar status
                    </Button>
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nova garantia"
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Cliente">
            <Input value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })} autoFocus />
          </Field>
          <Field label="Produto">
            <Input value={form.produto} onChange={(e) => setForm({ ...form, produto: e.target.value })} />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Data início">
              <Input type="date" value={form.inicio} onChange={(e) => setForm({ ...form, inicio: e.target.value })} />
            </Field>
            <Field label="Data fim">
              <Input type="date" value={form.fim} onChange={(e) => setForm({ ...form, fim: e.target.value })} />
            </Field>
          </div>
          <Field label="Dias">
            <Input type="number" value={form.dias} onChange={(e) => setForm({ ...form, dias: e.target.value })} />
          </Field>
          <Field label="Descrição">
            <Textarea value={form.desc} onChange={(e) => setForm({ ...form, desc: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.obs} onChange={(e) => setForm({ ...form, obs: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

interface DevolucaoRow {
  id: number;
  orcamento_id: number | null;
  produto_nome: string;
  sku: string;
  quantidade: number;
  motivo: string;
  tipo: string;
  status: string;
  criado_em: string;
}

function Devolucao() {
  const [rows, setRows] = useState<DevolucaoRow[]>([]);
  const [form, setForm] = useState({ orc: "", var: "", qtd: "1", tipo: "devolucao", motivo: "" });

  const carregar = async () => {
    try {
      setRows((await api.listarDevolucoes()) as DevolucaoRow[]);
    } catch {
      toast("Erro ao carregar devoluções", "error");
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const registrar = async () => {
    const variante_id = parseInt(form.var, 10);
    const quantidade = parseFloat(form.qtd);
    if (!variante_id || quantidade <= 0) {
      toast("Informe produto e quantidade", "error");
      return;
    }
    try {
      await api.registrarDevolucao({
        orcamento_id: parseInt(form.orc, 10) || undefined,
        variante_id,
        quantidade,
        tipo: form.tipo,
        motivo: form.motivo.trim(),
      });
      toast("Devolução registrada (estoque atualizado)", "success");
      setForm({ orc: "", var: "", qtd: "1", tipo: "devolucao", motivo: "" });
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Orçamento (ID)">
          <Input type="number" placeholder="opcional" value={form.orc} onChange={(e) => setForm({ ...form, orc: e.target.value })} className="w-28" />
        </Field>
        <Field label="Produto (ID)">
          <Input type="number" value={form.var} onChange={(e) => setForm({ ...form, var: e.target.value })} className="w-28" />
        </Field>
        <Field label="Quantidade">
          <Input type="number" step="any" value={form.qtd} onChange={(e) => setForm({ ...form, qtd: e.target.value })} className="w-24" />
        </Field>
        <Field label="Tipo">
          <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} className="w-40">
            <option value="devolucao">Devolução</option>
            <option value="troca">Troca</option>
          </Select>
        </Field>
        <Field label="Motivo">
          <Input value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })} className="w-48" />
        </Field>
        <Button variant="primary" onClick={() => void registrar()}>
          Registrar devolução
        </Button>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhuma devolução.
        </div>
      ) : (
        <Table>
          <THead cols={["Produto", "Qtd", "Tipo", "Motivo", "Status", "Data"]} />
          <TBody>
            {rows.map((d) => (
              <tr key={d.id} className="hover:bg-gray-50">
                <Cell>
                  <span className="font-medium">{d.produto_nome}</span>
                  {d.sku ? <div className="font-mono text-xs text-gray-400">{d.sku}</div> : null}
                </Cell>
                <Cell>{d.quantidade}</Cell>
                <Cell>
                  <Badge tone="gray">{d.tipo}</Badge>
                </Cell>
                <Cell>{d.motivo || "—"}</Cell>
                <Cell>
                  <Badge tone={d.status === "estornada" ? "green" : "gray"}>{d.status}</Badge>
                </Cell>
                <Cell className="text-xs text-gray-500">{fmtDate(d.criado_em)}</Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
