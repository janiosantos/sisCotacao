// pages/precos/modal-aplicar-promocao.tsx - módulo Preços (ModalAplicarPromocao).

import { useEffect, useState } from "react";
import { api, type ProdutoResumo, type Promocao } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { ProductSearch } from "../../ui/product-search";
import { Button, Modal } from "../../ui/ui";

export function ModalAplicarPromocao({ promocao, onClose }: { promocao: Promocao | null; onClose: () => void }) {
  const [produtos, setProdutos] = useState<ProdutoResumo[]>([]);

  useEffect(() => {
    if (promocao) setProdutos([]);
  }, [promocao]);

  const aplicar = async () => {
    if (!promocao) return;
    if (!produtos.length) {
      toast("Selecione ao menos um produto", "error");
      return;
    }
    const lista = produtos.map((produto) => produto.id);
    try {
      const res = await api.aplicarPromocao(promocao.id, lista);
      toast(`${res.aplicados} itens aplicados`, "success");
      onClose();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={promocao !== null}
      onClose={onClose}
      title={`Aplicar — ${promocao?.nome ?? ""}`}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void aplicar()}>
            Aplicar
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">
        Bipe ou pesquise os produtos que receberão a promoção.{" "}
        {promocao?.tipo === "percentual"
          ? `Desconto de ${promocao.valor}% sobre o preço base.`
          : `Preço fixo de ${fmtMoney(promocao?.valor ?? 0)}.`}
      </p>
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


