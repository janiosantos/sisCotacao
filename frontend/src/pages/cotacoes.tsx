// pages/cotacoes.tsx — lista de cotações e tela de comparação/fechamento.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type CotacaoDetalhe,
  type CotacaoFornecedor,
  type CotacaoLista,
  type Fornecedor,
  type ItemCotacao,
  type Preco,
  type ProdutoResumo,
  type Vencedor,
} from "../api/client";
import { fmtDate, fmtDateTime, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { abrir as abrirImportia } from "./importia";
import { Badge, Button, Cell, Field, Input, Loading, Modal, PageHeader, Select, Table, TBody, THead, Textarea } from "../ui/ui";

const STATUS_LABELS: Record<string, string> = {
  aberta: "Aberta",
  fechada: "Fechada",
  cancelada: "Cancelada",
  pendente: "Pendente",
  analise: "Pronta para Analisar",
  finalizada: "Finalizada",
  respondido: "Respondido",
};

function statusLabel(status: string): string {
  return STATUS_LABELS[status] || status;
}

function statusTone(status: string): "green" | "red" | "gray" {
  if (status === "fechada" || status === "finalizada") return "green";
  if (status === "cancelada") return "red";
  return "gray";
}

// ------------------------------------------------------------
// LISTA
// ------------------------------------------------------------

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

function CompareTable({
  cotacaoId,
  itens,
  fornecedores,
  precoMap,
  vencedorMap,
  isFechada,
  onRegistrado,
}: {
  cotacaoId: number;
  itens: ItemCotacao[];
  fornecedores: CotacaoFornecedor[];
  precoMap: Record<string, Preco>;
  vencedorMap: Record<number, Vencedor>;
  isFechada: boolean;
  onRegistrado: () => void;
}) {
  if (itens.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
        <p>Sem itens</p>
        <p>Adicione produtos a esta cotação.</p>
      </div>
    );
  }
  if (fornecedores.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
        <p>Sem fornecedores convidados</p>
        <p>Adicione ao menos um fornecedor para lançar preços.</p>
      </div>
    );
  }

  const registrar = async (itemId: number, fornecedorId: number, raw: string) => {
    const val = parseFloat(raw.replace(",", "."));
    if (isNaN(val) || val < 0) {
      toast("Preço inválido", "error");
      return;
    }
    try {
      await api.registrarPreco(cotacaoId, { cotacao_item_id: itemId, fornecedor_id: fornecedorId, preco_unitario: val });
      toast("Preço registrado", "success");
      onRegistrado();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const remover = async (itemId: number) => {
    if (!window.confirm("Remover este item da cotação?")) return;
    await api.removerItem(cotacaoId, itemId);
    onRegistrado();
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="min-w-[220px] px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Produto</th>
            <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Qtd.</th>
            {fornecedores.map((f) => (
              <th key={f.fornecedor_id} className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                {f.nome}
                <div className="mt-1">
                  <Badge tone={statusTone(f.status)}>{statusLabel(f.status)}</Badge>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {itens.map((it) => {
            const rowPrecos = fornecedores
              .map((f) => precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`])
              .filter(Boolean);
            const best = rowPrecos.length ? Math.min(...rowPrecos.map((p) => p.preco_unitario)) : null;
            const vencedor = vencedorMap[it.cotacao_item_id];
            return (
              <tr key={it.cotacao_item_id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    {it.imagem_url ? (
                      <img src={it.imagem_url} alt="" className="h-8 w-8 object-contain" />
                    ) : (
                      <span className="w-8" />
                    )}
                    <div>
                      <div className="font-mono text-xs text-gray-500">{it.sku || "#" + it.produto_id}</div>
                      <div className="font-medium">{it.name}</div>
                    </div>
                    {!isFechada && (
                      <button
                        className="ml-auto rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-600"
                        title="Remover item"
                        onClick={() => void remover(it.cotacao_item_id)}
                      >
                        ×
                      </button>
                    )}
                  </div>
                </td>
                <td className="px-4 py-2.5">{it.quantidade}</td>
                {fornecedores.map((f) => {
                  const p = precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`];
                  const isBest = p != null && best !== null && p.preco_unitario === best;
                  const isWinner = vencedor && vencedor.fornecedor_id === f.fornecedor_id;
                  const delta =
                    p != null && best !== null && !isBest ? (((p.preco_unitario - best) / best) * 100).toFixed(1) : null;
                  const pack =
                    p && p.fator_conversao && p.fator_conversao > 1 && p.unidade_compra ? (
                      <span className="block text-[11px] text-gray-400">
                        {p.unidade_compra} · {p.fator_conversao} un · {qtdEmbalagens(it.quantidade, p.fator_conversao)} emb. ≈{" "}
                        {fmtMoney(p.preco_unitario * p.fator_conversao)}/emb.
                      </span>
                    ) : null;
                  return (
                    <td key={f.fornecedor_id} className={`px-4 py-2.5 ${isWinner || isBest ? "bg-brand-50" : ""}`}>
                      {isFechada ? (
                        <>
                          {p ? fmtMoney(p.preco_unitario) : "—"}
                          {pack}
                          {isWinner ? <span className="mt-1 inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">✓ vencedor</span> : null}
                        </>
                      ) : (
                        <>
                          <input
                            className="w-24 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none"
                            inputMode="decimal"
                            defaultValue={p != null ? String(p.preco_unitario) : ""}
                            placeholder="R$"
                            onBlur={(e) => void registrar(it.cotacao_item_id, f.fornecedor_id, e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                            }}
                          />
                          {pack}
                          {isBest ? (
                            <span className="mt-1 inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">✓ melhor preço</span>
                          ) : null}
                          {delta ? <span className="ml-1 text-xs text-red-500">+{delta}%</span> : null}
                        </>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function qtdEmbalagens(quantidade: number, fator: number): number {
  if (!fator || fator <= 0) return 1;
  return Math.ceil(quantidade / fator);
}

function Summary({ itens, vencedores, fornecedores }: { itens: ItemCotacao[]; vencedores: Vencedor[]; fornecedores: CotacaoFornecedor[] }) {
  const fornecedorNome: Record<number, string> = {};
  for (const f of fornecedores) fornecedorNome[f.fornecedor_id] = f.nome;
  let total = 0;
  const porFornecedor: Record<number, number> = {};
  for (const v of vencedores) {
    total += v.preco_unitario * v.quantidade;
    porFornecedor[v.fornecedor_id] = (porFornecedor[v.fornecedor_id] || 0) + v.preco_unitario * v.quantidade;
  }
  return (
    <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="text-xs font-medium uppercase tracking-wide text-gray-500">Total do pedido</div>
        <div className="mt-1 text-xl font-semibold text-gray-900">{fmtMoney(total)}</div>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="text-xs font-medium uppercase tracking-wide text-gray-500">Itens fechados</div>
        <div className="mt-1 text-xl font-semibold text-gray-900">
          {vencedores.length} / {itens.length}
        </div>
      </div>
      {Object.entries(porFornecedor).map(([fid, val]) => (
        <div key={fid} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-gray-500">{fornecedorNome[Number(fid)] || "—"}</div>
          <div className="mt-1 text-xl font-semibold text-gray-900">{fmtMoney(val)}</div>
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------
// MODAIS
// ------------------------------------------------------------

function ModalEditar({
  cotacao,
  open,
  onClose,
  onSaved,
}: {
  cotacao: CotacaoLista;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [titulo, setTitulo] = useState("");
  const [cliente, setCliente] = useState("");
  const [obs, setObs] = useState("");

  useEffect(() => {
    if (open) {
      setTitulo(cotacao.titulo || "");
      setCliente(cotacao.cliente || "");
      setObs(cotacao.observacoes || "");
    }
  }, [open, cotacao]);

  const salvar = async () => {
    await api.atualizarCotacao(cotacao.id, { titulo: titulo.trim(), cliente: cliente.trim(), observacoes: obs.trim() });
    onSaved();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Editar cotação"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void salvar()}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Título">
          <Input value={titulo} onChange={(e) => setTitulo(e.target.value)} />
        </Field>
        <Field label="Cliente">
          <Input value={cliente} onChange={(e) => setCliente(e.target.value)} />
        </Field>
        <Field label="Observações">
          <Textarea value={obs} onChange={(e) => setObs(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}

function ModalAddFornecedor({
  cotacaoId,
  jaConvidados,
  todosFornecedores,
  open,
  onClose,
  onSaved,
}: {
  cotacaoId: number;
  jaConvidados: CotacaoFornecedor[];
  todosFornecedores: Fornecedor[];
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState("");
  const [whats, setWhats] = useState("");
  const [email, setEmail] = useState("");

  const jaIds = new Set(jaConvidados.map((f) => f.fornecedor_id));
  const disponiveis = useMemo(() => todosFornecedores.filter((f) => !jaIds.has(f.id)), [todosFornecedores, jaIds]);

  useEffect(() => {
    if (open) {
      setNome("");
      setWhats("");
      setEmail("");
    }
  }, [open]);

  const convidar = async (fid: number) => {
    try {
      await api.convidarFornecedor(cotacaoId, fid);
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const cadastrarConvidar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome do fornecedor", "error");
      return;
    }
    try {
      const res = await api.criarFornecedor({
        nome: nome.trim(),
        whatsapp: whats.trim() || null,
        email: email.trim() || null,
      });
      await api.convidarFornecedor(cotacaoId, res.id);
      toast("Fornecedor cadastrado e convidado", "success");
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Convidar fornecedor"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          {disponiveis.length ? (
            <Button variant="primary" onClick={onClose}>
              Fechar
            </Button>
          ) : (
            <Button variant="primary" onClick={() => void cadastrarConvidar()}>
              Cadastrar e convidar
            </Button>
          )}
        </>
      }
    >
      {disponiveis.length ? (
        <div className="flex max-h-[260px] flex-col gap-1 overflow-y-auto">
          {disponiveis.map((f) => (
            <button
              key={f.id}
              onClick={() => void convidar(f.id)}
              className="rounded-md border border-gray-200 px-3 py-2 text-left text-sm hover:bg-gray-50"
            >
              {f.nome}
            </button>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            Nenhum fornecedor ativo disponível para convidar. Cadastre um novo abaixo — ele já será convidado para esta cotação:
          </p>
          <Field label="Nome *">
            <Input placeholder="Nome da empresa / contato" value={nome} onChange={(e) => setNome(e.target.value)} />
          </Field>
          <Field label="WhatsApp">
            <Input placeholder="55DDNÚMERO (só dígitos)" value={whats} onChange={(e) => setWhats(e.target.value)} />
          </Field>
          <Field label="E-mail">
            <Input value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
        </div>
      )}
    </Modal>
  );
}

function ModalAddItem({
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

function ModalFechar({
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
