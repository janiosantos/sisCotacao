// pages/bancos.tsx — contas bancárias e extrato (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type ContaBancaria, type ContaBancariaPayload, type MovimentoBancario, type MovimentoBancarioPayload } from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, PageHeader, Select, Table, TBody, THead } from "../ui/ui";

type Aba = "contas" | "extrato";

export default function Bancos() {
  const [aba, setAba] = useState<Aba>("contas");

  return (
    <div>
      <PageHeader title="Bancos" subtitle="Contas bancárias, extrato e conciliação." />
      <div className="mb-5 flex gap-2 border-b border-gray-200">
        {(["contas", "extrato"] as Aba[]).map((a) => (
          <button
            key={a}
            onClick={() => setAba(a)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              aba === a ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {a === "contas" ? "Contas" : "Extrato"}
          </button>
        ))}
      </div>
      {aba === "contas" ? <Contas /> : <Extrato />}
    </div>
  );
}

function Contas() {
  const [contas, setContas] = useState<ContaBancaria[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<ContaBancaria | null>(null);
  const [form, setForm] = useState({ nome: "", banco: "000", agencia: "", conta: "", digito: "", saldo_inicial: "0" });

  const carregar = async () => {
    try {
      setContas(await api.listarContasBancarias());
    } catch {
      toast("Erro ao carregar contas", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = (c: ContaBancaria | null) => {
    setEditando(c);
    setForm({
      nome: c?.nome ?? "",
      banco: c?.banco ?? "000",
      agencia: c?.agencia ?? "",
      conta: c?.conta ?? "",
      digito: c?.digito ?? "",
      saldo_inicial: "0",
    });
    setModalOpen(true);
  };

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome", "error");
      return;
    }
    const payload: ContaBancariaPayload = {
      nome: form.nome.trim(),
      banco: form.banco,
      agencia: form.agencia,
      conta: form.conta,
      digito: form.digito,
      ...(editando ? {} : { saldo_inicial: parseFloat(form.saldo_inicial.replace(",", ".")) || 0 }),
    };
    try {
      if (editando) await api.atualizarContaBancaria(editando.id, payload);
      else await api.criarContaBancaria(payload);
      setModalOpen(false);
      toast(editando ? "Conta atualizada" : "Conta criada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alternar = async (c: ContaBancaria) => {
    try {
      await api.alternarAtivoContaBancaria(c.id, !c.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => abrir(null)}>
          Nova conta bancária
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Nome", "Banco", "Agência", "Conta", "Saldo", "Status", ""]} />
          <TBody>
            {contas.length === 0 ? (
              <EmptyRow colSpan={7} message="Nenhuma conta" />
            ) : (
              contas.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <Cell className="font-medium">{c.nome}</Cell>
                  <Cell className="font-mono text-xs">{c.banco}</Cell>
                  <Cell>{c.agencia}</Cell>
                  <Cell className="font-mono text-xs">
                    {c.conta}-{c.digito}
                  </Cell>
                  <Cell className="font-medium">{fmtMoney(c.saldo_atual)}</Cell>
                  <Cell>
                    <Badge tone={c.ativo ? "green" : "red"}>{c.ativo ? "Ativa" : "Inativa"}</Badge>
                  </Cell>
                  <Cell>
                    <div className="flex justify-end gap-2">
                      <Button size="sm" onClick={() => abrir(c)}>
                        Editar
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => alternar(c)}>
                        {c.ativo ? "Desat." : "Ativar"}
                      </Button>
                    </div>
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
        title={editando ? "Editar conta bancária" : "Nova conta bancária"}
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
          <Field label="Nome">
            <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Banco (código)">
              <Input maxLength={3} value={form.banco} onChange={(e) => setForm({ ...form, banco: e.target.value })} />
            </Field>
            <Field label="Agência">
              <Input maxLength={10} value={form.agencia} onChange={(e) => setForm({ ...form, agencia: e.target.value })} />
            </Field>
            <Field label="Conta">
              <Input maxLength={15} value={form.conta} onChange={(e) => setForm({ ...form, conta: e.target.value })} />
            </Field>
            <Field label="Dígito">
              <Input maxLength={2} value={form.digito} onChange={(e) => setForm({ ...form, digito: e.target.value })} />
            </Field>
          </div>
          {!editando && (
            <Field label="Saldo inicial">
              <Input type="number" step="0.01" value={form.saldo_inicial} onChange={(e) => setForm({ ...form, saldo_inicial: e.target.value })} />
            </Field>
          )}
        </div>
      </Modal>
    </div>
  );
}

function Extrato() {
  const [contas, setContas] = useState<ContaBancaria[]>([]);
  const [movimentos, setMovimentos] = useState<MovimentoBancario[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [filtroConta, setFiltroConta] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ conta_id: "", tipo: "credito", valor: "", data_movimento: "", descricao: "", documento: "", categoria: "" });

  const carregar = async () => {
    try {
      setContas(await api.listarContasBancarias());
      const res = await api.listarMovimentosBancarios({ conta_id: filtroConta ? Number(filtroConta) : undefined });
      setMovimentos(res);
    } catch {
      toast("Erro ao carregar extrato", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const salvar = async () => {
    const payload: MovimentoBancarioPayload = {
      conta_id: Number(form.conta_id),
      tipo: form.tipo,
      valor: parseFloat(form.valor.replace(",", ".")),
      data_movimento: form.data_movimento,
      descricao: form.descricao.trim() || undefined,
      documento: form.documento.trim() || undefined,
      categoria: form.categoria.trim() || undefined,
    };
    if (!payload.conta_id || payload.valor <= 0 || !payload.data_movimento) {
      toast("Preencha conta, valor e data", "error");
      return;
    }
    try {
      const r = await api.criarMovimentoBancario(payload);
      toast(`Movimento registrado. Saldo: ${fmtMoney(r.saldo_atual)}`, "success");
      setModalOpen(false);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const conciliar = async (m: MovimentoBancario) => {
    try {
      await api.toggleConciliado(m.id);
      toast("Conciliado alternado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Novo movimento
        </Button>
        <Field label="Conta">
          <Select value={filtroConta} onChange={(e) => setFiltroConta(e.target.value)} className="w-56">
            <option value="">Todas</option>
            {contas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome} ({c.banco})
              </option>
            ))}
          </Select>
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Data", "Conta", "Tipo", "Descrição", "Valor", "Doc", "Conc.", ""]} />
          <TBody>
            {movimentos.length === 0 ? (
              <EmptyRow colSpan={8} message="Nenhum movimento" />
            ) : (
              movimentos.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <Cell className="text-xs text-gray-500">{fmtDate(m.data_movimento)}</Cell>
                  <Cell>{m.conta_nome}</Cell>
                  <Cell>
                    <Badge tone={m.tipo === "credito" ? "green" : "red"}>{m.tipo}</Badge>
                  </Cell>
                  <Cell>{m.descricao}</Cell>
                  <Cell className="font-medium">{fmtMoney(m.valor)}</Cell>
                  <Cell className="font-mono text-xs">{m.documento || ""}</Cell>
                  <Cell>{m.conciliado ? "✓" : "—"}</Cell>
                  <Cell>
                    <Button size="sm" variant="ghost" onClick={() => conciliar(m)}>
                      {m.conciliado ? "Desconc." : "Conciliar"}
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
        title="Novo movimento bancário"
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Registrar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Conta">
            <Select value={form.conta_id} onChange={(e) => setForm({ ...form, conta_id: e.target.value })}>
              {contas.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </Select>
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Tipo">
              <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
                <option value="credito">Crédito</option>
                <option value="debito">Débito</option>
                <option value="transferencia">Transferência</option>
              </Select>
            </Field>
            <Field label="Valor">
              <Input type="number" step="0.01" min="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} />
            </Field>
          </div>
          <Field label="Data">
            <Input type="date" value={form.data_movimento} onChange={(e) => setForm({ ...form, data_movimento: e.target.value })} />
          </Field>
          <Field label="Descrição">
            <Input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
          </Field>
          <Field label="Documento">
            <Input value={form.documento} onChange={(e) => setForm({ ...form, documento: e.target.value })} />
          </Field>
          <Field label="Categoria">
            <Input value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}
