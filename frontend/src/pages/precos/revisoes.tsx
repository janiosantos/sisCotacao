// pages/precos/revisoes.tsx - módulo Preços (Revisoes).

import { useEffect, useState } from "react";
import { api, type RevisaoPreco, type TabelaPreco } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Loading, Select, Table, TBody, THead } from "../../ui/ui";
import { ModalCriarRevisao } from "./modal-criar-revisao";

export function Revisoes() {
  const [rows, setRows] = useState<RevisaoPreco[]>([]);
  const [tabelas, setTabelas] = useState<TabelaPreco[]>([]);
  const [filtroTab, setFiltroTab] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  const carregarTabelas = async () => {
    try {
      setTabelas(await api.listarTabelasPreco());
    } catch {
      /* silêncio */
    }
  };

  const carregar = async () => {
    setCarregando(true);
    try {
      const tabela_id = parseInt(filtroTab, 10) || undefined;
      setRows(await api.listarRevisoesPreco(tabela_id));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregarTabelas();
  }, []);

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fechar = async (id: number) => {
    try {
      await api.fecharRevisaoPreco(id);
      toast("Revisão fechada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Nova revisão
        </Button>
        <Field label="Tabela">
          <Select value={filtroTab} onChange={(e) => setFiltroTab(e.target.value)} className="w-48">
            <option value="">Todas</option>
            {tabelas.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Código", "Descrição", "Tabela", "Cliente", "Data", "Validade", "Situação", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={8} message="Nenhuma revisão" />
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <Cell className="font-mono font-semibold">{r.codigo}</Cell>
                  <Cell>{r.descricao}</Cell>
                  <Cell>{r.tabela_nome}</Cell>
                  <Cell>{r.cliente_nome ?? "—"}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(r.data_cadastro)}</Cell>
                  <Cell className="text-xs text-gray-500">{r.data_validade ? fmtDate(r.data_validade) : "—"}</Cell>
                  <Cell>
                    <Badge tone={r.situacao === "aberta" ? "gray" : "green"}>{r.situacao}</Badge>
                  </Cell>
                  <Cell>
                    {r.situacao === "aberta" ? (
                      <div className="flex justify-end">
                        <Button size="sm" variant="ghost" onClick={() => void fechar(r.id)}>
                          Fechar
                        </Button>
                      </div>
                    ) : null}
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <ModalCriarRevisao
        tabelas={tabelas}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSaved={() => void carregar()}
      />
    </div>
  );
}


