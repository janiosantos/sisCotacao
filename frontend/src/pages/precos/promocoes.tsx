// pages/precos/promocoes.tsx - módulo Preços (Promocoes).

import { useEffect, useState } from "react";
import { api, type Promocao } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Loading, Table, TBody, THead } from "../../ui/ui";
import { ModalPromocao } from "./modal-promocao";
import { ModalItensPromocao } from "./modal-itens-promocao";
import { ModalAplicarPromocao } from "./modal-aplicar-promocao";

export function Promocoes() {
  const [rows, setRows] = useState<Promocao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalPromo, setModalPromo] = useState<{ editando: Promocao | null } | null>(null);
  const [itensDe, setItensDe] = useState<Promocao | null>(null);
  const [aplicarDe, setAplicarDe] = useState<Promocao | null>(null);

  const carregar = async () => {
    try {
      setRows(await api.listarPromocoes());
    } catch {
      toast("Erro ao carregar promoções", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const alternar = async (p: Promocao) => {
    try {
      await api.atualizarPromocao(p.id, {
        nome: p.nome,
        tipo: p.tipo,
        valor: p.valor,
        data_inicio: p.data_inicio ?? undefined,
        data_fim: p.data_fim ?? undefined,
        ativo: p.ativo ? 0 : 1,
      });
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalPromo({ editando: null })}>
          Nova promoção
        </Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Nome", "Tipo", "Valor", "Início", "Fim", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={7} message="Nenhuma promoção" />
            ) : (
              rows.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <Cell className="font-medium">{p.nome}</Cell>
                  <Cell>
                    <Badge>{p.tipo === "percentual" ? "%" : "R$"}</Badge>
                  </Cell>
                  <Cell>{p.tipo === "percentual" ? p.valor + "%" : fmtMoney(p.valor)}</Cell>
                  <Cell className="text-xs text-gray-500">{p.data_inicio ? fmtDate(p.data_inicio) : "—"}</Cell>
                  <Cell className="text-xs text-gray-500">{p.data_fim ? fmtDate(p.data_fim) : "—"}</Cell>
                  <Cell>
                    <Badge tone={p.ativo ? "green" : "gray"}>{p.ativo ? "Ativa" : "Inativa"}</Badge>
                  </Cell>
                  <Cell>
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="ghost" onClick={() => setAplicarDe(p)}>
                        Aplicar
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setItensDe(p)}>
                        Itens
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setModalPromo({ editando: p })}>
                        Editar
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => void alternar(p)}>
                        {p.ativo ? "Desat." : "Ativar"}
                      </Button>
                    </div>
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <ModalPromocao
        editando={modalPromo?.editando ?? null}
        open={modalPromo !== null}
        onClose={() => setModalPromo(null)}
        onSaved={carregar}
      />
      <ModalItensPromocao promocao={itensDe} onClose={() => setItensDe(null)} />
      <ModalAplicarPromocao promocao={aplicarDe} onClose={() => setAplicarDe(null)} />
    </div>
  );
}


