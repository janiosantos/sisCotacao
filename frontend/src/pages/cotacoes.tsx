// pages/cotacoes.tsx — lista de cotações e tela de comparação/fechamento.

import { useEffect, useState } from "react";
import {
  api,
  type CotacaoDetalhe,
  type CotacaoLista,
  type Fornecedor,
  type Preco,
  type Vencedor,
} from "../api/client";
import { fmtDate, fmtDateTime } from "../ui/format";
import { toast } from "../ui/dom";
import { abrir as abrirImportia } from "./importia";
import { Badge, Button, Cell, Field, Loading, PageHeader, Select, Table, TBody, THead } from "../ui/ui";
import { statusLabel, statusTone } from "./cotacoes/helpers";
import { CompareTable } from "./cotacoes/compare-table";
import { Summary } from "./cotacoes/summary";
import { ModalEditar } from "./cotacoes/modal-editar";
import { ModalAddFornecedor } from "./cotacoes/modal-add-fornecedor";
import { ModalAddItem } from "./cotacoes/modal-add-item";
import { ModalFechar } from "./cotacoes/modal-fechar";


export default function Cotacoes() {
  const [filtro, setFiltro] = useState("");
  const [cotacoes, setCotacoes] = useState<CotacaoLista[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      setCotacoes(await api.listarCotacoes(filtro));
    } catch (e) {
      toast("Erro ao carregar cotações: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtro]);

  const abrirComprar = (id: number) => {
    sessionStorage.setItem("compras_cotacao", String(id));
    location.hash = "#/compras";
  };

  return (
    <div>
      <PageHeader
        title="Cotações"
        subtitle="Solicitações de preço enviadas a fornecedores."
        actions={
          <a
            href="#/catalogo"
            className="inline-flex items-center justify-center gap-1.5 rounded-md bg-brand-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700"
          >
            + Nova cotação
          </a>
        }
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Status">
          <Select value={filtro} onChange={(e) => setFiltro(e.target.value)} className="w-48">
            <option value="">Todas</option>
            <option value="pendente">Pendente</option>
            <option value="analise">Pronta para Analisar</option>
            <option value="finalizada">Finalizada</option>
            <option value="aberta">Abertas</option>
            <option value="fechada">Fechadas</option>
            <option value="cancelada">Canceladas</option>
          </Select>
        </Field>
        <span className="mb-2 text-sm text-gray-500">{cotacoes.length} cotações</span>
      </div>

      {carregando ? (
        <Loading />
      ) : cotacoes.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          <p>Nenhuma cotação ainda</p>
          <p>Vá até o Catálogo, selecione produtos e crie sua primeira cotação.</p>
        </div>
      ) : (
        <Table>
          <THead cols={["Nº", "Título", "Cliente", "Status", "Itens", "Respostas", "Criada em", ""]} />
          <TBody>
            {cotacoes.map((c) => (
              <tr key={c.id} className="cursor-pointer hover:bg-gray-50" onClick={() => (location.hash = `#/cotacoes/${c.id}`)}>
                <Cell className="font-mono">{c.numero}</Cell>
                <Cell>{c.titulo || "—"}</Cell>
                <Cell>{c.cliente || "—"}</Cell>
                <Cell>
                  <Badge tone={statusTone(c.status)}>{statusLabel(c.status)}</Badge>
                </Cell>
                <Cell>{c.n_itens}</Cell>
                <Cell>
                  {c.n_respostas} / {c.n_fornecedores}
                </Cell>
                <Cell className="text-xs">{fmtDate(c.criado_em)}</Cell>
                <Cell>
                  <div onClick={(e) => e.stopPropagation()}>
                    {(c.status === "pendente" || c.status === "analise" || c.status === "finalizada") && (
                      <Button size="sm" onClick={() => abrirComprar(c.id)}>
                        Abrir no Comprar
                      </Button>
                    )}
                  </div>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}

// ------------------------------------------------------------
// DETALHE / COMPARAÇÃO
// ------------------------------------------------------------

export function CotacoesDetalhe() {
  const cotacaoId = Number((location.hash.match(/^#\/cotacoes\/(\d+)$/) || [])[1]);

  const [data, setData] = useState<CotacaoDetalhe | null>(null);
  const [todosFornecedores, setTodosFornecedores] = useState<Fornecedor[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  const [modalEditar, setModalEditar] = useState(false);
  const [modalAddFornecedor, setModalAddFornecedor] = useState(false);
  const [modalAddItem, setModalAddItem] = useState(false);
  const [modalFechar, setModalFechar] = useState(false);

  const carregar = async () => {
    setCarregando(true);
    setErro("");
    try {
      const [d, f] = await Promise.all([api.detalharCotacao(cotacaoId), api.listarFornecedores(true)]);
      setData(d);
      setTodosFornecedores(f);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cotacaoId]);

  if (carregando) return <Loading />;
  if (erro || !data)
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
        <p>Erro</p>
        <p>{erro}</p>
      </div>
    );

  const { cotacao, itens, fornecedores, precos, vencedores } = data;
  const precoMap: Record<string, Preco> = {};
  for (const p of precos) precoMap[`${p.cotacao_item_id}:${p.fornecedor_id}`] = p;
  const vencedorMap: Record<number, Vencedor> = {};
  for (const v of vencedores) vencedorMap[v.cotacao_item_id] = v;
  const isFechada = cotacao.status === "fechada";

  const reabrir = async () => {
    if (!window.confirm("Reabrir esta cotação para novos lançamentos de preço?")) return;
    await api.reabrirCotacao(cotacaoId);
    await carregar();
  };

  return (
    <div>
      <PageHeader
        title={`Cotação nº ${cotacao.numero}`}
        subtitle={`${cotacao.titulo || "Sem título"} · criada em ${fmtDateTime(cotacao.criado_em)}${
          cotacao.cliente ? " · cliente " + cotacao.cliente : ""
        }`}
        actions={
          <>
            <Badge tone={statusTone(cotacao.status)}>{statusLabel(cotacao.status)}</Badge>
            <a
              className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              href={`/orcamentos/${cotacao.id}/imprimir`}
              target="_blank"
              rel="noreferrer"
            >
              Imprimir
            </a>
            <Button size="sm" variant="ghost" onClick={() => setModalEditar(true)}>
              Editar
            </Button>
            {isFechada ? (
              <Button size="sm" onClick={() => void reabrir()}>
                Reabrir
              </Button>
            ) : (
              <Button size="sm" variant="primary" onClick={() => setModalFechar(true)}>
                Fechar cotação
              </Button>
            )}
          </>
        }
      />

      <div className="mb-2">
        <a href="#/cotacoes" className="text-xs text-gray-500 hover:underline">
          ← Todas as cotações
        </a>
      </div>

      {cotacao.observacoes ? <p className="mb-4 text-sm text-gray-500">Obs.: {cotacao.observacoes}</p> : null}

      <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-gray-900">Comparação de preços</h3>
        {!isFechada && (
          <div className="flex gap-2">
            <Button size="sm" onClick={() => abrirImportia({ cotacaoId, fornecedores, titulo: "Cotação nº " + cotacao.numero, onAplicado: () => void carregar() })}>
              ⚡ Importar retorno
            </Button>
            <Button size="sm" onClick={() => setModalAddFornecedor(true)}>
              + Fornecedor
            </Button>
            <Button size="sm" onClick={() => setModalAddItem(true)}>
              + Item
            </Button>
          </div>
        )}
      </div>

      <CompareTable
        cotacaoId={cotacaoId}
        itens={itens}
        fornecedores={fornecedores}
        precoMap={precoMap}
        vencedorMap={vencedorMap}
        isFechada={isFechada}
        onRegistrado={() => void carregar()}
      />

      {isFechada && <Summary itens={itens} vencedores={vencedores} fornecedores={fornecedores} />}

      <ModalEditar
        cotacao={cotacao}
        open={modalEditar}
        onClose={() => setModalEditar(false)}
        onSaved={() => {
          setModalEditar(false);
          void carregar();
        }}
      />
      <ModalAddFornecedor
        cotacaoId={cotacaoId}
        jaConvidados={fornecedores}
        todosFornecedores={todosFornecedores}
        open={modalAddFornecedor}
        onClose={() => setModalAddFornecedor(false)}
        onSaved={() => {
          setModalAddFornecedor(false);
          void carregar();
        }}
      />
      <ModalAddItem
        cotacaoId={cotacaoId}
        open={modalAddItem}
        onClose={() => setModalAddItem(false)}
        onSaved={() => {
          setModalAddItem(false);
          void carregar();
        }}
      />
      <ModalFechar
        cotacaoId={cotacaoId}
        itens={itens}
        fornecedores={fornecedores}
        precoMap={precoMap}
        open={modalFechar}
        onClose={() => setModalFechar(false)}
        onSaved={() => {
          setModalFechar(false);
          void carregar();
        }}
      />
    </div>
  );
}

