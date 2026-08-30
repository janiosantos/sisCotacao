// pages/diagnostico_variacoes/modal-detalhe.tsx — detalhe do produto no diagnóstico.
import { fmtMoney } from "../../ui/format";
import { Button, Cell, Modal, Table, TBody, THead } from "../../ui/ui";

export interface Detalhe {
  produto: { id: number; nome: string; marca: string; familia_id: number | null } | null;
  sku?: string;
  ean?: string;
  preco?: number;
  atributos?: string | null;
}

export function ModalDetalheVariacao({
  detalhe,
  onClose,
}: {
  detalhe: Detalhe | null;
  onClose: () => void;
}) {
  return (
    <Modal
      open={detalhe != null}
      onClose={onClose}
      title={detalhe?.produto?.nome || "Produto"}
      footer={<Button onClick={onClose}>Fechar</Button>}
    >
      <p className="mb-3 text-sm text-gray-500">
        Dados do produto (cada antiga variante é agora um produto independente).
      </p>
      <Table>
        <THead cols={["ID", "SKU", "EAN", "Preço", "Atributos"]} />
        <TBody>
          {detalhe ? (
            <tr className="hover:bg-gray-50">
              <Cell>{detalhe.produto?.id ?? "—"}</Cell>
              <Cell className="font-mono text-xs">{detalhe.sku || "—"}</Cell>
              <Cell className="font-mono text-xs">{detalhe.ean || "—"}</Cell>
              <Cell>{detalhe.preco != null ? fmtMoney(detalhe.preco) : "—"}</Cell>
              <Cell className="text-xs">{detalhe.atributos || "—"}</Cell>
            </tr>
          ) : null}
        </TBody>
      </Table>
    </Modal>
  );
}