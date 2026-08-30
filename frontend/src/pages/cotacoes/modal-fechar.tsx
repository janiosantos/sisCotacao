// pages/cotacoes/modal-fechar.tsx - módulo Cotações (ModalFechar).

import { useEffect, useState, useMemo } from "react";
import { api, type CotacaoFornecedor, type ItemCotacao, type Preco } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Modal, Select } from "../../ui/ui";

export function ModalFechar({
  cotacaoId,
  itens,
  fornecedores,
  precoMap,
  open,
  onClose,
  onSaved,
}: {
  cotacaoId: number;
  itens: ItemCotacao[];
  fornecedores: CotacaoFornecedor[];
  precoMap: Record<string, Preco>;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const fornecedorNome: Record<number, string> = {};
  for (const f of fornecedores) fornecedorNome[f.fornecedor_id] = f.nome;

  const rows = useMemo(
    () =>
      itens.map((it) => {
        const options = fornecedores
          .map((f) => precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`])
          .filter(Boolean)
          .sort((a, b) => a.preco_unitario - b.preco_unitario);
        return { item: it, options };
      }),
    [itens, fornecedores, precoMap]
  );

  const [escolhas, setEscolhas] = useState<Record<number, string>>({});

  useEffect(() => {
    if (open) {
      const init: Record<number, string> = {};
      for (const r of rows) {
        if (r.options.length) init[r.item.cotacao_item_id] = `${r.options[0].fornecedor_id}|${r.options[0].preco_unitario}`;
      }
      setEscolhas(init);
    }
  }, [open, rows]);

  const semPreco = rows.filter((r) => r.options.length === 0);

  const confirmar = async () => {
    const escolhasArr = rows
      .filter((r) => r.options.length > 0)
      .map((r) => {
        const [fornecedor_id, preco_unitario] = (escolhas[r.item.cotacao_item_id] || "").split("|");
        return {
          cotacao_item_id: r.item.cotacao_item_id,
          fornecedor_id: Number(fornecedor_id),
          preco_unitario: Number(preco_unitario),
          quantidade: r.item.quantidade,
        };
      });
    try {
      await api.fecharCotacao(cotacaoId, escolhasArr);
      toast("Cotação fechada", "success");
      onSaved();
    } catch (e) {
      toast("Erro ao fechar: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Fechar cotação"
      wide
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" disabled={rows.every((r) => r.options.length === 0)} onClick={() => void confirmar()}>
            Confirmar fechamento
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">
        Confirme o fornecedor vencedor de cada item (pré-selecionado o menor preço). Itens sem nenhum preço lançado ficam de
        fora do pedido fechado.
      </p>
      <div className="flex max-h-[340px] flex-col gap-2 overflow-y-auto">
        {rows
          .filter((r) => r.options.length > 0)
          .map((r) => (
            <div key={r.item.cotacao_item_id} className="rounded-md border border-gray-200 p-2.5">
              <div className="mb-1.5 text-xs">
                <span className="font-semibold">{r.item.sku || "#" + r.item.produto_id}</span> — {r.item.name} (qtd. {r.item.quantidade})
              </div>
              <Select
                value={escolhas[r.item.cotacao_item_id] || ""}
                onChange={(e) => setEscolhas({ ...escolhas, [r.item.cotacao_item_id]: e.target.value })}
              >
                {r.options.map((p) => (
                  <option key={p.fornecedor_id} value={`${p.fornecedor_id}|${p.preco_unitario}`}>
                    {fornecedorNome[p.fornecedor_id]} — {fmtMoney(p.preco_unitario)}
                  </option>
                ))}
              </Select>
            </div>
          ))}
        {semPreco.length ? (
          <p className="text-xs text-gray-400">{semPreco.length} item(ns) sem preço lançado não entrarão no pedido.</p>
        ) : null}
      </div>
    </Modal>
  );
}

