// pages/vendedores.tsx — cadastro de vendedores (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type Vendedor } from "../api/client";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Loading, PageHeader, Table, TBody, THead } from "../ui/ui";
import { ModalVendedorForm } from "./vendedores/modal-form";

export default function Vendedores() {
  const [vendedores, setVendedores] = useState<Vendedor[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Vendedor | null>(null);

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
    setModalOpen(true);
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

      {modalOpen && (
        <ModalVendedorForm
          vendedor={editando}
          onClose={() => setModalOpen(false)}
          onSaved={carregar}
        />
      )}
    </div>
  );
}
