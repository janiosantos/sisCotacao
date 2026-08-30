// pages/bancos/contas.tsx — aba de contas bancárias.
import { useEffect, useState } from "react";
import { api, type ContaBancaria, type ContaBancariaPayload } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, Table, TBody, THead } from "../../ui/ui";

export function Contas() {
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