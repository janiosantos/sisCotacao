// pages/cotacoes/modal-add-item.tsx - módulo Cotações (ModalAddItem).

import { api } from "../../api/client";
import { ProductSearch } from "../../ui/product-search";
import { Button, Modal } from "../../ui/ui";

export function ModalAddItem({
  cotacaoId,
  open,
  onClose,
  onSaved,
}: {
  cotacaoId: number;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const adicionar = async (id: number) => {
    await api.adicionarItem(cotacaoId, { produto_id: id, quantidade: 1 });
    onSaved();
  };

  return (
    <Modal open={open} onClose={onClose} title="Adicionar item" wide footer={<Button onClick={onClose}>Fechar</Button>}>
      <ProductSearch autoFocus clearOnSelect onSelect={(produto) => void adicionar(produto.id)} />
    </Modal>
  );
}


