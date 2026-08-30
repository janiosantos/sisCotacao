// pages/unidades.tsx — unidades de compra (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type UnidadeCompra } from "../api/client";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Loading, PageHeader, Table, TBody, THead } from "../ui/ui";
import { ModalUnidadeForm } from "./unidades/modal-form";

export default function Unidades() {
  const [unidades, setUnidades] = useState<UnidadeCompra[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<UnidadeCompra | null>(null);

  const carregar = async () => {
    try {
      setUnidades(await api.listarUnidadesCompra());
    } catch (e) {
      toast("Erro ao carregar unidades: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = (u: UnidadeCompra | null) => {
    setEditando(u);
    setModalOpen(true);
  };

  const alternar = async (u: UnidadeCompra) => {
    try {
      await api.atualizarUnidadeCompra(u.id, u.sigla, u.descricao, !u.ativo);
      toast(u.ativo ? "Unidade desativada" : "Unidade ativada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const excluir = async (u: UnidadeCompra) => {
    if (!window.confirm(`Excluir a unidade "${u.sigla}"?`)) return;
    try {
      await api.excluirUnidadeCompra(u.id);
      toast("Unidade excluída", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const ativas = unidades.filter((u) => u.ativo).length;

  return (
    <div>
      <PageHeader
        title="Unidades de compra"
        subtitle={'Unidades disponíveis para "Unid. compra" no cadastro de produtos por fornecedor.'}
        actions={
          <Button variant="primary" onClick={() => abrir(null)}>
            + Nova unidade
          </Button>
        }
      />
      <p className="mb-4 text-sm text-gray-500">
        {unidades.length} unidades ({ativas} ativas)
      </p>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Sigla", "Descrição", "Status", ""]} />
          <TBody>
            {unidades.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <Cell className="font-mono font-semibold">{u.sigla}</Cell>
                <Cell>{u.descricao || "—"}</Cell>
                <Cell>
                  <Badge tone={u.ativo ? "green" : "red"}>{u.ativo ? "Ativa" : "Inativa"}</Badge>
                </Cell>
                <Cell>
                  <div className="flex justify-end gap-2">
                    <Button size="sm" variant="ghost" onClick={() => abrir(u)}>
                      Editar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => alternar(u)}>
                      {u.ativo ? "Desativar" : "Ativar"}
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => excluir(u)}>
                      Excluir
                    </Button>
                  </div>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      {modalOpen && (
        <ModalUnidadeForm
          unidade={editando}
          onClose={() => setModalOpen(false)}
          onSaved={carregar}
        />
      )}
    </div>
  );
}
