// pages/precos/tabelas.tsx - módulo Preços (Tabelas).

import { useEffect, useState } from "react";
import { api, type TabelaPreco } from "../../api/client";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Loading, Table, TBody, THead } from "../../ui/ui";
import { ModalTabela } from "./modal-tabela";
import { ModalItensTabela } from "./modal-itens-tabela";
import { ModalGerarPrecos } from "./modal-gerar-precos";

export function Tabelas() {
  const [rows, setRows] = useState<TabelaPreco[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalTabela, setModalTabela] = useState<{ editando: TabelaPreco | null } | null>(null);
  const [itensDe, setItensDe] = useState<TabelaPreco | null>(null);
  const [gerarDe, setGerarDe] = useState<TabelaPreco | null>(null);

  const carregar = async () => {
    try {
      setRows(await api.listarTabelasPreco());
    } catch {
      toast("Erro ao carregar tabelas", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const alternar = async (t: TabelaPreco) => {
    try {
      await api.alternarAtivoTabelaPreco(t.id, !t.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalTabela({ editando: null })}>
          Nova tabela
        </Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Nome", "Tipo", "Margem", "Markup", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={6} message="Nenhuma tabela" />
            ) : (
              rows.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <Cell className="font-medium">{t.nome}</Cell>
                  <Cell>
                    <Badge>{t.tipo}</Badge>
                  </Cell>
                  <Cell>{t.margem_padrao ? `${t.margem_padrao}%` : "—"}</Cell>
                  <Cell>{t.markup ? `${t.markup}%` : "—"}</Cell>
                  <Cell>
                    <Badge tone={t.ativo ? "green" : "gray"}>{t.ativo ? "Ativo" : "Inativo"}</Badge>
                  </Cell>
                  <Cell>
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="ghost" onClick={() => setItensDe(t)}>
                        Itens
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setGerarDe(t)}>
                        Gerar
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setModalTabela({ editando: t })}>
                        Editar
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => void alternar(t)}>
                        {t.ativo ? "Desat." : "Ativar"}
                      </Button>
                    </div>
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <ModalTabela
        editando={modalTabela?.editando ?? null}
        open={modalTabela !== null}
        onClose={() => setModalTabela(null)}
        onSaved={carregar}
      />
      <ModalItensTabela tab={itensDe} onClose={() => setItensDe(null)} />
      <ModalGerarPrecos tab={gerarDe} onClose={() => setGerarDe(null)} onApplied={carregar} />
    </div>
  );
}


