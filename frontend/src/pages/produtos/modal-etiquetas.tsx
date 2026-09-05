// pages/produtos/modal-etiquetas.tsx — geração de etiquetas de preço.
import { useEffect, useState } from "react";
import type { ProdutoResumo } from "../../api/client";
import { toast } from "../../ui/dom";
import { ProductSearch } from "../../ui/product-search";
import { Button, Modal } from "../../ui/ui";

export function ModalEtiquetas({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [produtos, setProdutos] = useState<ProdutoResumo[]>([]);

  useEffect(() => {
    if (open) setProdutos([]);
  }, [open]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Etiquetas de preço"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button
            variant="primary"
            onClick={() => {
              if (!produtos.length) {
                toast("Selecione ao menos um produto", "error");
                return;
              }
              const idList = produtos.map((produto) => produto.id).join(",");
              window.open(`/etiquetas/imprimir?ids=${idList}`, "_blank");
            }}
          >
            Gerar etiquetas
          </Button>
        </>
      }
    >
      <p className="mb-3 text-sm text-gray-500">Bipe ou pesquise cada produto que deve entrar na folha de etiquetas.</p>
      <ProductSearch
        clearOnSelect
        excludeIds={produtos.map((produto) => produto.id)}
        onSelect={(produto) => setProdutos((atuais) => [...atuais, produto])}
      />
      <div className="mt-3 space-y-1">
        {produtos.map((produto) => (
          <div key={produto.id} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
            <span><span className="font-mono text-xs text-slate-500">{produto.sku}</span> {produto.name}</span>
            <button type="button" className="rounded px-2 text-slate-400 hover:bg-red-50 hover:text-red-600" onClick={() => setProdutos((atuais) => atuais.filter((item) => item.id !== produto.id))} aria-label={`Remover ${produto.name}`}>×</button>
          </div>
        ))}
      </div>
    </Modal>
  );
}
