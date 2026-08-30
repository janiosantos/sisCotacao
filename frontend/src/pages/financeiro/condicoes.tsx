// pages/financeiro/condicoes.tsx — condições de pagamento (CRUD + parcelas).
import { useEffect, useState } from "react";
import { api, type CondicaoPagamento } from "../../api/client";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, Table, TBody, THead, Textarea } from "../../ui/ui";

export function Condicoes() {
  const [rows, setRows] = useState<CondicaoPagamento[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<CondicaoPagamento | null>(null);
  const [form, setForm] = useState({ nome: "", descricao: "", parcelas: "" });
  const [parcelasModal, setParcelasModal] = useState<CondicaoPagamento | null>(null);

  const carregar = async () => {
    try {
      setRows(await api.listarCondicoes());
    } catch {
      toast("Erro ao carregar condições", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = async (c: CondicaoPagamento | null) => {
    setEditando(c);
    setForm({ nome: c?.nome ?? "", descricao: c?.descricao ?? "", parcelas: "" });
    setModalOpen(true);
    if (c) {
      try {
        const det = await api.getCondicao(c.id);
        setForm((f) => ({ ...f, parcelas: (det.parcelas || []).map((p) => `${p.sequencia}:${p.dias},${p.percentual}`).join("\n") }));
      } catch {
        /* segue */
      }
    }
  };

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome", "error");
      return;
    }
    try {
      let cond = editando;
      if (editando) {
        await api.atualizarCondicao(editando.id, { nome: form.nome.trim(), descricao: form.descricao.trim() });
      } else {
        const r = await api.criarCondicao({ nome: form.nome.trim(), descricao: form.descricao.trim() });
        cond = { id: r.id, nome: form.nome.trim(), descricao: form.descricao.trim(), ativo: true };
      }
      const parcelas = form.parcelas
        .split("\n")
        .map((linha) => {
          const [seq, resto] = linha.split(":");
          const [dias, pct] = (resto || "").split(",");
          return { sequencia: parseInt(seq, 10), dias: parseInt(dias, 10), percentual: parseFloat(pct.replace(",", ".")) };
        })
        .filter((p) => p.sequencia > 0);
      if (cond && parcelas.length) await api.salvarParcelas(cond.id, parcelas);
      setModalOpen(false);
      toast(editando ? "Condição atualizada" : "Condição criada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => void abrir(null)}>
          Nova condição
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Nome", "Parcelas", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={4} message="Nenhuma condição" />
            ) : (
              rows.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{c.nome}</span>
                    {c.descricao ? <div className="text-xs text-gray-500">{c.descricao}</div> : null}
                  </Cell>
                  <Cell>
                    <Button size="sm" variant="ghost" onClick={async () => setParcelasModal(await api.getCondicao(c.id))}>
                      Ver parcelas
                    </Button>
                  </Cell>
                  <Cell>
                    <Badge tone={c.ativo ? "green" : "red"}>{c.ativo ? "Ativa" : "Inativa"}</Badge>
                  </Cell>
                  <Cell>
                    <Button size="sm" onClick={() => void abrir(c)}>
                      Editar
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
        title={editando ? "Editar condição" : "Nova condição"}
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
          <Field label="Nome *">
            <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus />
          </Field>
          <Field label="Descrição">
            <Input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
          </Field>
          <Field label="Parcelas (sequência: dias,%) — uma por linha">
            <Textarea
              rows={4}
              placeholder={"Ex.:\n1:0,100\n2:30,50\n3:60,50"}
              value={form.parcelas}
              onChange={(e) => setForm({ ...form, parcelas: e.target.value })}
            />
          </Field>
        </div>
      </Modal>

      <Modal open={parcelasModal != null} onClose={() => setParcelasModal(null)} title={parcelasModal ? `${parcelasModal.nome} — Parcelas` : ""} footer={<Button onClick={() => setParcelasModal(null)}>Fechar</Button>}>
        <Table>
          <THead cols={["#", "Dias", "%"]} />
          <TBody>
            {(parcelasModal?.parcelas || []).map((p) => (
              <tr key={p.sequencia} className="hover:bg-gray-50">
                <Cell>{p.sequencia}</Cell>
                <Cell>{p.dias}</Cell>
                <Cell>{p.percentual}%</Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      </Modal>
    </div>
  );
}