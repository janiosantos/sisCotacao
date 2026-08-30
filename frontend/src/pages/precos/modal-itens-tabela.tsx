// pages/precos/modal-itens-tabela.tsx - módulo Preços (ModalItensTabela).

import { useEffect, useState } from "react";
import { api, type TabelaPreco, type TabelaPrecoItemMargem } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { Button, Cell, EmptyRow, Input, Loading, Modal, Table, TBody, THead } from "../../ui/ui";

export function ModalItensTabela({ tab, onClose }: { tab: TabelaPreco | null; onClose: () => void }) {
  const [termo, setTermo] = useState("");
  const [itens, setItens] = useState<TabelaPrecoItemMargem[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (!tab) return;
    setTermo("");
    setCarregando(true);
    void api
      .listarItensTabelaMargem(tab.id, undefined)
      .then(setItens)
      .catch(() => {})
      .finally(() => setCarregando(false));
  }, [tab]);

  useEffect(() => {
    if (!tab) return;
    const timer = setTimeout(() => {
      void api
        .listarItensTabelaMargem(tab.id, termo.trim() || undefined)
        .then(setItens)
        .catch(() => {});
    }, 200);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [termo]);

  return (
    <Modal open={tab !== null} onClose={onClose} title={`${tab?.nome ?? ""} — Itens`} wide footer={<Button onClick={onClose}>Fechar</Button>}>
      <div className="space-y-4">
        <Input placeholder="Buscar produto…" value={termo} onChange={(e) => setTermo(e.target.value)} />
        {carregando ? (
          <Loading />
        ) : (
          <Table>
            <THead cols={["Produto", "SKU", "Preço", "Custo", "Margem %"]} />
            <TBody>
              {itens.length === 0 ? (
                <EmptyRow colSpan={5} message="Nenhum item" />
              ) : (
                itens.map((i) => (
                  <tr key={i.id} className="hover:bg-gray-50">
                    <Cell>
                      <span className="font-medium">{i.produto_nome}</span>
                      {i.marca ? <div className="text-xs text-gray-400">{i.marca}</div> : null}
                    </Cell>
                    <Cell className="font-mono text-xs">{i.sku}</Cell>
                    <Cell>{fmtMoney(i.preco)}</Cell>
                    <Cell>{i.custo_unitario ? fmtMoney(i.custo_unitario) : "—"}</Cell>
                    <Cell className="font-medium">{i.margem_pct != null ? i.margem_pct.toFixed(1) + "%" : "—"}</Cell>
                  </tr>
                ))
              )}
            </TBody>
          </Table>
        )}
      </div>
    </Modal>
  );
}


