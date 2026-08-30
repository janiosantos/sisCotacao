// pages/precos/modal-itens-promocao.tsx - módulo Preços (ModalItensPromocao).

import { useEffect, useState } from "react";
import { api, type Promocao } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { Button, Cell, EmptyRow, Input, Loading, Modal, Table, TBody, THead } from "../../ui/ui";

export function ModalItensPromocao({ promocao, onClose }: { promocao: Promocao | null; onClose: () => void }) {
  const [termo, setTermo] = useState("");
  const [itens, setItens] = useState<{ id: number; produto_nome: string; sku: string; preco_base: number; preco_promocional: number }[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (!promocao) return;
    setTermo("");
    setCarregando(true);
    void api
      .listarItensPromocao(promocao.id, undefined)
      .then(setItens)
      .catch(() => {})
      .finally(() => setCarregando(false));
  }, [promocao]);

  useEffect(() => {
    if (!promocao) return;
    const timer = setTimeout(() => {
      void api
        .listarItensPromocao(promocao.id, termo.trim() || undefined)
        .then(setItens)
        .catch(() => {});
    }, 200);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [termo]);

  return (
    <Modal open={promocao !== null} onClose={onClose} title={`${promocao?.nome ?? ""} — Itens`} wide footer={<Button onClick={onClose}>Fechar</Button>}>
      <div className="space-y-4">
        <Input placeholder="Buscar produto…" value={termo} onChange={(e) => setTermo(e.target.value)} />
        {carregando ? (
          <Loading />
        ) : (
          <Table>
            <THead cols={["Produto", "SKU", "Preço base", "Preço promocional"]} />
            <TBody>
              {itens.length === 0 ? (
                <EmptyRow colSpan={4} message="Nenhum item" />
              ) : (
                itens.map((i) => (
                  <tr key={i.id} className="hover:bg-gray-50">
                    <Cell className="font-medium">{i.produto_nome}</Cell>
                    <Cell className="font-mono text-xs">{i.sku}</Cell>
                    <Cell>{fmtMoney(i.preco_base)}</Cell>
                    <Cell className="font-medium">{fmtMoney(i.preco_promocional)}</Cell>
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


