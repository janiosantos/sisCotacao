// pages/cotacoes/modal-add-item.tsx - módulo Cotações (ModalAddItem).

import { useEffect, useRef, useState } from "react";
import { api, type ProdutoResumo } from "../../api/client";
import { Button, Field, Input, Modal } from "../../ui/ui";

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
  const [busca, setBusca] = useState("");
  const [resultados, setResultados] = useState<ProdutoResumo[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    if (open) {
      setBusca("");
      setResultados([]);
    }
  }, [open]);

  useEffect(() => {
    clearTimeout(timer.current);
    if (busca.trim().length < 2) {
      setResultados([]);
      return;
    }
    timer.current = setTimeout(() => {
      void api
        .listarProdutos({ q: busca.trim(), limit: 30, agrupado: 0 })
        .then((res) => setResultados(res.items.map((p) => p as ProdutoResumo)))
        .catch(() => setResultados([]));
    }, 200);
    return () => clearTimeout(timer.current);
  }, [busca]);

  const adicionar = async (id: number) => {
    await api.adicionarItem(cotacaoId, { produto_id: id, quantidade: 1 });
    onSaved();
  };

  return (
    <Modal open={open} onClose={onClose} title="Adicionar item" wide footer={<Button onClick={onClose}>Fechar</Button>}>
      <div className="space-y-3">
        <Field label="Buscar produto">
          <Input placeholder="Nome, código, marca…" value={busca} onChange={(e) => setBusca(e.target.value)} autoFocus />
        </Field>
        <div className="max-h-[260px] overflow-y-auto">
          {resultados.length === 0 && busca.trim().length >= 2 ? (
            <div className="py-6 text-center text-sm text-gray-400">Nada encontrado</div>
          ) : (
            resultados.map((p) => (
              <div key={p.id} className="flex items-center gap-3 border-b border-gray-100 py-2">
                {p.imagem_url ? (
                  <img src={p.imagem_url} className="h-8 w-8 object-contain" alt="" />
                ) : (
                  <span className="w-8" />
                )}
                <div className="flex-1 text-xs">
                  <div className="font-mono text-[11px] text-gray-500">{p.sku || "#" + p.id}</div>
                  <div className="font-medium">{p.name}</div>
                  {p.spec ? <div className="text-[11px] text-gray-400">{p.spec}</div> : null}
                </div>
                <Button size="sm" onClick={() => void adicionar(p.id)}>
                  Adicionar
                </Button>
              </div>
            ))
          )}
        </div>
      </div>
    </Modal>
  );
}


