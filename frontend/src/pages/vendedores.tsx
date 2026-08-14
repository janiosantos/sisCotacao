// pages/vendedores.tsx — cadastro de vendedores (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type Vendedor, type VendedorPayload } from "../api/client";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Field, Input, Loading, Modal, PageHeader, Table, TBody, THead } from "../ui/ui";

export default function Vendedores() {
  const [vendedores, setVendedores] = useState<Vendedor[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Vendedor | null>(null);
  const [nome, setNome] = useState("");
  const [comissao, setComissao] = useState("");

  const carregar = async () => {
    try {
      setVendedores(await api.listarVendedores());
    } catch (e) {
      toast("Erro ao carregar vendedores: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = (v: Vendedor | null) => {
    setEditando(v);
    setNome(v?.nome ?? "");
    setComissao(v ? String(v.comissao_pct) : "");
    setModalOpen(true);
  };

  const salvar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome do vendedor", "error");
      return;
    }
    const payload: VendedorPayload = { nome: nome.trim(), comissao_pct: Number(comissao) || 0 };
    try {
      if (editando) await api.atualizarVendedor(editando.id, payload);
      else await api.criarVendedor(payload);
      setModalOpen(false);
      toast("Vendedor salvo", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alternar = async (v: Vendedor) => {
    try {
      await api.alternarAtivoVendedor(v.id, !v.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <PageHeader
        title="Vendedores"
        subtitle="Cadastro usado para vincular clientes e medir comissão sobre vendas."
        actions={
          <Button variant="primary" onClick={() => abrir(null)}>
            + Novo vendedor
          </Button>
        }
      />
      {carregando ? (
        <Loading />
      ) : vendedores.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhum vendedor cadastrado.
        </div>
      ) : (
        <Table>
          <THead cols={["Nome", "Comissão", "Status", ""]} />
          <TBody>
            {vendedores.map((v) => (
              <tr key={v.id} className="hover:bg-gray-50">
                <Cell className="font-medium">{v.nome}</Cell>
                <Cell>{v.comissao_pct}%</Cell>
                <Cell>
                  <Badge tone={v.ativo ? "green" : "red"}>{v.ativo ? "Ativo" : "Inativo"}</Badge>
                </Cell>
                <Cell>
                  <div className="flex justify-end gap-2">
                    <Button size="sm" onClick={() => abrir(v)}>
                      Editar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => alternar(v)}>
                      {v.ativo ? "Desativar" : "Ativar"}
                    </Button>
                  </div>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editando ? "Editar vendedor" : "Novo vendedor"}
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
            <Input value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
          </Field>
          <Field label="Comissão (%)">
            <Input type="number" min={0} step="0.01" value={comissao} onChange={(e) => setComissao(e.target.value)} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}
