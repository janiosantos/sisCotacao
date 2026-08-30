// pages/pre-venda/modal-busca-cliente.tsx — busca de cliente no PDV.
import { useEffect, useState } from "react";
import { api, type Cliente } from "../../api/client";
import { SearchModal } from "../../ui/search-modal";

export function ModalBuscaCliente({
  onClose,
  onSaved,
  onNovoCliente,
}: {
  onClose: () => void;
  onSaved: (c: Cliente) => void;
  onNovoCliente: () => void;
}) {
  const [clientes, setClientes] = useState<Cliente[]>([]);

  useEffect(() => {
    void api.listarClientes(true).then(setClientes).catch(() => setClientes([]));
  }, []);

  return (
    <SearchModal
      open
      title="Buscar cliente"
      columns={[
        { key: "id", label: "Código", align: "right", render: (c) => String(c.id).padStart(6, "0") },
        { key: "nome", label: "Nome", render: (c) => c.nome },
        { key: "doc", label: "CPF/CNPJ", render: (c) => c.doc || "—" },
        { key: "cidade", label: "Cidade", render: (c) => [c.cidade, c.uf].filter(Boolean).join(" - ") || "—" },
      ]}
      data={clientes}
      searchText={(c) => [c.nome, c.doc, c.cidade, c.telefone, c.whatsapp, String(c.id)].join(" ")}
      extra={
        <div className="mt-3 flex justify-end">
          <button onClick={onNovoCliente} className="rounded-md bg-[#6a84a6] px-3 py-1.5 text-sm font-bold text-white hover:bg-[#587291]">
            + Novo cliente
          </button>
        </div>
      }
      onClose={onClose}
      onSelect={(c) => {
        onSaved(c);
        onClose();
      }}
    />
  );
}