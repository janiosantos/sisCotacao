// pages/pre-venda/modal-busca-parceiro.tsx — seleção do parceiro que indicou (PDV).
import { useEffect, useState } from "react";
import { api, type ParceiroIndicacao } from "../../api/client";
import { SearchModal } from "../../ui/search-modal";

export function ModalBuscaParceiro({
  onClose,
  onSelect,
}: {
  onClose: () => void;
  onSelect: (p: ParceiroIndicacao) => void;
}) {
  const [parceiros, setParceiros] = useState<ParceiroIndicacao[]>([]);

  useEffect(() => {
    void api
      .listarParceirosIndicacao()
      .then((res) => setParceiros(res.parceiros || []))
      .catch(() => setParceiros([]));
  }, []);

  return (
    <SearchModal
      open
      title="Indicado por (parceiro)"
      columns={[
        { key: "nome", label: "Parceiro", render: (p) => p.nome_exibicao },
        { key: "codigo", label: "Código", render: (p) => p.codigo },
      ]}
      data={parceiros}
      searchText={(p) => [p.nome_exibicao, p.apelido, p.nome, p.codigo].filter(Boolean).join(" ")}
      onClose={onClose}
      onSelect={(p) => {
        onSelect(p);
        onClose();
      }}
    />
  );
}