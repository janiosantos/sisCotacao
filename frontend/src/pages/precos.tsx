// pages/precos.tsx — preços (React + Tailwind).

import { useEffect, useRef, useState } from "react";
import {
  api,
  type CalculoPreco,
  type HistoricoPrecoItem,
  type ItemPreviaReajuste,
  type PreviaReajuste,
  type ProdutoResumo,
  type Promocao,
  type PromocaoPayload,
  type ReajusteResultado,
  type RevisaoPreco,
  type TabelaPreco,
  type TabelaPrecoItemMargem,
  type TabelaPrecoPayload,
} from "../api/client";
import { fmtDate, fmtDateTime, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import {
  Badge,
  Button,
  Cell,
  EmptyRow,
  Field,
  Input,
  Loading,
  Modal,
  PageHeader,
  Select,
  Table,
  TBody,
  THead,
  Textarea,
} from "../ui/ui";

type Aba = "tabelas" | "promocoes" | "revisoes" | "simulador" | "historico";

function pct(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(2).replace(".", ",") + "%";
}

export default function Precos() {
  const [aba, setAba] = useState<Aba>("tabelas");

  const TABS: { key: Aba; label: string }[] = [
    { key: "tabelas", label: "Tabelas" },
    { key: "promocoes", label: "Promoções" },
    { key: "revisoes", label: "Revisões" },
    { key: "simulador", label: "Simulador" },
    { key: "historico", label: "Histórico" },
  ];

  return (
    <div>
      <PageHeader title="Preços" subtitle="Tabelas de preço e promoções." />
      <div className="mb-5 flex gap-2 overflow-x-auto border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setAba(t.key)}
            className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${
              aba === t.key ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {aba === "tabelas" && <Tabelas />}
      {aba === "promocoes" && <Promocoes />}
      {aba === "revisoes" && <Revisoes />}
      {aba === "simulador" && <Simulador />}
      {aba === "historico" && <Historico />}
    </div>
  );
}

// ──────────────────────────────────────────────────────────
//  Tabelas de Preço
// ──────────────────────────────────────────────────────────

function Tabelas() {
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

function ModalTabela({
  editando,
  open,
  onClose,
  onSaved,
}: {
  editando: TabelaPreco | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState("");
  const [tipo, setTipo] = useState("varejo");
  const [margem, setMargem] = useState("0");
  const [markup, setMarkup] = useState("0");

  useEffect(() => {
    if (open) {
      setNome(editando?.nome ?? "");
      setTipo(editando?.tipo ?? "varejo");
      setMargem(String(editando?.margem_padrao ?? 0));
      setMarkup(String(editando?.markup ?? 0));
    }
  }, [open, editando]);

  const salvar = async () => {
    const payload: TabelaPrecoPayload = {
      nome: nome.trim(),
      tipo,
      margem_padrao: parseFloat(margem.replace(",", ".")),
      markup: parseFloat(markup.replace(",", ".")),
    };
    if (!payload.nome) {
      toast("Informe o nome", "error");
      return;
    }
    try {
      if (editando) await api.atualizarTabelaPreco(editando.id, payload);
      else await api.criarTabelaPreco(payload);
      toast(editando ? "Tabela atualizada" : "Tabela criada", "success");
      onClose();
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editando ? "Editar tabela" : "Nova tabela"}
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
        <Field label="Nome">
          <Input value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
        <Field label="Tipo">
          <Select value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="varejo">varejo</option>
            <option value="atacado">atacado</option>
            <option value="contrato">contrato</option>
            <option value="promocional">promocional</option>
          </Select>
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Margem % (custo)">
            <Input type="number" step="0.1" value={margem} onChange={(e) => setMargem(e.target.value)} />
          </Field>
          <Field label="Markup % (custo)">
            <Input type="number" step="0.1" value={markup} onChange={(e) => setMarkup(e.target.value)} />
          </Field>
        </div>
      </div>
    </Modal>
  );
}

function ModalItensTabela({ tab, onClose }: { tab: TabelaPreco | null; onClose: () => void }) {
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

function ModalGerarPrecos({
  tab,
  onClose,
  onApplied,
}: {
  tab: TabelaPreco | null;
  onClose: () => void;
  onApplied: () => void;
}) {
  const [margem, setMargem] = useState("0");
  const [markup, setMarkup] = useState("0");
  const [previa, setPrevia] = useState<PreviaReajuste | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [aplicando, setAplicando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (tab) {
      setMargem(String(tab.margem_padrao || 0));
      setMarkup(String(tab.markup || 0));
      setPrevia(null);
      setErro("");
    }
  }, [tab]);

  const verPrevia = async () => {
    if (!tab) return;
    const params: Record<string, unknown> = {};
    const m = parseFloat(margem.replace(",", "."));
    const k = parseFloat(markup.replace(",", "."));
    if (!isNaN(m)) params.margem = m;
    if (!isNaN(k)) params.markup = k;
    setCarregando(true);
    setErro("");
    setPrevia(null);
    try {
      const r = await api.previaReajusteTabela(tab.id, params);
      setPrevia(r);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  const aplicar = async () => {
    if (!tab) return;
    const params: Record<string, unknown> = { confirmado: true };
    const m = parseFloat(margem.replace(",", "."));
    const k = parseFloat(markup.replace(",", "."));
    if (!isNaN(m)) params.margem = m;
    if (!isNaN(k)) params.markup = k;
    setAplicando(true);
    try {
      const res: ReajusteResultado = await api.reajustarTabela(tab.id, params);
      toast(`${res.aplicados} preços aplicados (${res.sem_custo} sem custo)`, "success");
      onClose();
      onApplied();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setAplicando(false);
    }
  };

  return (
    <Modal
      open={tab !== null}
      onClose={onClose}
      title={`Reajustar preços — ${tab?.nome ?? ""}`}
      wide
      footer={<Button onClick={onClose}>Fechar</Button>}
    >
      <div className="space-y-4">
        <p className="text-sm text-gray-500">
          Calcula o preço sugerido pelo motor (custo líquido do Fiscal → margem/markup), mostra a prévia e, após
          confirmação, aplica e registra o histórico.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Margem % (preço = custo ÷ (1 − margem))">
            <Input type="number" step="0.1" value={margem} onChange={(e) => setMargem(e.target.value)} />
          </Field>
          <Field label="Markup % (preço = custo × (1 + markup))">
            <Input type="number" step="0.1" value={markup} onChange={(e) => setMarkup(e.target.value)} />
          </Field>
        </div>
        <div className="flex justify-end gap-2">
          <Button onClick={() => void verPrevia()} disabled={carregando}>
            Ver prévia
          </Button>
          <Button variant="primary" onClick={() => void aplicar()} disabled={!previa || !previa.itens.length || aplicando}>
            {aplicando ? "Aplicando…" : "Aplicar (aprovar)"}
          </Button>
        </div>

        {carregando ? <Loading message="Calculando prévia…" /> : null}
        {erro ? <div className="py-4 text-center text-sm text-gray-400">Erro: {erro}</div> : null}
        {previa && previa.itens.length === 0 && !carregando ? (
          <div className="py-4 text-center text-sm text-gray-400">Nenhum produto com custo para reajustar.</div>
        ) : null}
        {previa && previa.itens.length > 0 ? (
          <div>
            <p className="mb-2 text-xs text-gray-500">
              {previa.total} item(ns) · margem {previa.margem}% · markup {previa.markup}%
            </p>
            <Table>
              <THead cols={["Produto", "Custo líquido", "Atual", "Sugerido", "Margem"]} />
              <TBody>
                {previa.itens.slice(0, 60).map((i: ItemPreviaReajuste) => (
                  <tr key={i.produto_id} className="hover:bg-gray-50">
                    <Cell>
                      <span className="font-medium">{i.produto_nome}</span>
                      {i.sku ? <div className="font-mono text-xs text-gray-400">{i.sku}</div> : null}
                    </Cell>
                    <Cell>{i.custo_liquido != null ? fmtMoney(i.custo_liquido) : "—"}</Cell>
                    <Cell>{fmtMoney(i.preco_atual)}</Cell>
                    <Cell className="font-medium">{i.preco_sugerido != null ? fmtMoney(i.preco_sugerido) : "—"}</Cell>
                    <Cell>{i.margem_efetiva_pct != null ? i.margem_efetiva_pct.toFixed(2).replace(".", ",") + "%" : "—"}</Cell>
                  </tr>
                ))}
              </TBody>
            </Table>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}

// ──────────────────────────────────────────────────────────
//  Revisões
// ──────────────────────────────────────────────────────────

function Revisoes() {
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

function ModalCriarRevisao({
  tabelas,
  open,
  onClose,
  onSaved,
}: {
  tabelas: TabelaPreco[];
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [tabelaId, setTabelaId] = useState("");
  const [codigo, setCodigo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [cliente, setCliente] = useState("");
  const [validade, setValidade] = useState("");

  useEffect(() => {
    if (open) {
      setTabelaId(tabelas[0] ? String(tabelas[0].id) : "");
      setCodigo("");
      setDescricao("");
      setCliente("");
      setValidade("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const salvar = async () => {
    try {
      await api.criarRevisaoPreco({
        tabela_id: parseInt(tabelaId, 10),
        codigo: codigo.trim(),
        descricao: descricao.trim() || undefined,
        cliente_id: parseInt(cliente, 10) || undefined,
        data_validade: validade || undefined,
      });
      toast("Revisão criada", "success");
      onClose();
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Nova revisão"
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
        <Field label="Tabela">
          <Select value={tabelaId} onChange={(e) => setTabelaId(e.target.value)}>
            {tabelas.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Código">
          <Input placeholder="Ex.: REV-001" value={codigo} onChange={(e) => setCodigo(e.target.value)} />
        </Field>
        <Field label="Descrição">
          <Input placeholder="Ex.: Preços Iniciais" value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        </Field>
        <Field label="Cliente (ID, opcional)">
          <Input type="number" min={1} placeholder="ID do cliente" value={cliente} onChange={(e) => setCliente(e.target.value)} />
        </Field>
        <Field label="Data validade (opcional)">
          <Input type="date" value={validade} onChange={(e) => setValidade(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}

// ──────────────────────────────────────────────────────────
//  Promoções
// ──────────────────────────────────────────────────────────

function Promocoes() {
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

function ModalPromocao({
  editando,
  open,
  onClose,
  onSaved,
}: {
  editando: Promocao | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState("");
  const [tipo, setTipo] = useState("percentual");
  const [valor, setValor] = useState("0");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");

  useEffect(() => {
    if (open) {
      setNome(editando?.nome ?? "");
      setTipo(editando?.tipo ?? "percentual");
      setValor(String(editando?.valor ?? 0));
      setInicio(editando?.data_inicio ?? "");
      setFim(editando?.data_fim ?? "");
    }
  }, [open, editando]);

  const salvar = async () => {
    const payload: PromocaoPayload = {
      nome: nome.trim(),
      tipo,
      valor: parseFloat(valor.replace(",", ".")),
      data_inicio: inicio || undefined,
      data_fim: fim || undefined,
    };
    if (!payload.nome) {
      toast("Informe o nome", "error");
      return;
    }
    try {
      if (editando) await api.atualizarPromocao(editando.id, payload);
      else await api.criarPromocao(payload);
      toast(editando ? "Promoção atualizada" : "Promoção criada", "success");
      onClose();
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editando ? "Editar promoção" : "Nova promoção"}
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
        <Field label="Nome">
          <Input value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Tipo">
            <Select value={tipo} onChange={(e) => setTipo(e.target.value)}>
              <option value="percentual">Percentual (%)</option>
              <option value="valor_fixo">Valor fixo (R$)</option>
            </Select>
          </Field>
          <Field label="Valor">
            <Input type="number" step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} />
          </Field>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Início">
            <Input type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} />
          </Field>
          <Field label="Fim">
            <Input type="date" value={fim} onChange={(e) => setFim(e.target.value)} />
          </Field>
        </div>
      </div>
    </Modal>
  );
}

function ModalItensPromocao({ promocao, onClose }: { promocao: Promocao | null; onClose: () => void }) {
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

function ModalAplicarPromocao({ promocao, onClose }: { promocao: Promocao | null; onClose: () => void }) {
  const [ids, setIds] = useState("");

  useEffect(() => {
    if (promocao) setIds("");
  }, [promocao]);

  const aplicar = async () => {
    if (!promocao) return;
    const texto = ids.trim();
    if (!texto) {
      toast("Informe ao menos um ID", "error");
      return;
    }
    const lista = texto
      .split(",")
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n) && n > 0);
    if (!lista.length) {
      toast("IDs inválidos", "error");
      return;
    }
    try {
      const res = await api.aplicarPromocao(promocao.id, lista);
      toast(`${res.aplicados} itens aplicados`, "success");
      onClose();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={promocao !== null}
      onClose={onClose}
      title={`Aplicar — ${promocao?.nome ?? ""}`}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void aplicar()}>
            Aplicar
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">
        Aplica a promoção a produtos por ID do produto. Informe os IDs separados por vírgula.{" "}
        {promocao?.tipo === "percentual"
          ? `Desconto de ${promocao.valor}% sobre o preço base.`
          : `Preço fixo de ${fmtMoney(promocao?.valor ?? 0)}.`}
      </p>
      <Field label="IDs dos produtos (separados por vírgula)">
        <Textarea rows={3} placeholder="Ex.: 1, 2, 3, 10, 15" value={ids} onChange={(e) => setIds(e.target.value)} />
      </Field>
    </Modal>
  );
}

// ──────────────────────────────────────────────────────────
//  Simulador de preço (Fiscal → Custo → Precificação)
// ──────────────────────────────────────────────────────────

function Simulador() {
  const [busca, setBusca] = useState("");
  const [canal, setCanal] = useState("");
  const [margem, setMargem] = useState("");
  const [markup, setMarkup] = useState("");
  const [comissao, setComissao] = useState("");
  const [despesas, setDespesas] = useState("");
  const [taxas, setTaxas] = useState("");
  const [sugestoes, setSugestoes] = useState<ProdutoResumo[]>([]);
  const [selecionada, setSelecionada] = useState<ProdutoResumo | null>(null);
  const [resultado, setResultado] = useState<CalculoPreco | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    clearTimeout(timer.current);
    if (!busca.trim()) {
      setSugestoes([]);
      return;
    }
    timer.current = setTimeout(() => {
      void api
        .listarProdutos({ q: busca.trim(), limit: 8, agrupado: 0 })
        .then((res) => {
          setSugestoes(res.items.filter((i): i is ProdutoResumo => "price" in i));
        })
        .catch(() => setSugestoes([]));
    }, 200);
    return () => clearTimeout(timer.current);
  }, [busca]);

  const calcular = async () => {
    if (!selecionada) {
      toast("Selecione um produto na busca", "error");
      return;
    }
    const num = (v: string) => (v === "" ? undefined : parseFloat(v.replace(",", ".")));
    const params: Record<string, unknown> = { canal: canal || undefined };
    const m = num(margem);
    const k = num(markup);
    const c = num(comissao);
    const d = num(despesas);
    const t = num(taxas);
    if (m !== undefined) params.margem = m;
    if (k !== undefined) params.markup = k;
    if (c !== undefined) params.comissao = c;
    if (d !== undefined) params.despesas = d;
    if (t !== undefined) params.taxas = t;

    setCarregando(true);
    setErro("");
    setResultado(null);
    try {
      setResultado(await api.calcularPreco(selecionada.id, params));
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  const f = resultado?.fiscal;
  const linha = (rot: string, val: string) => (
    <tr>
      <td className="px-4 py-2 text-xs text-gray-500">{rot}</td>
      <td className="px-4 py-2 text-right font-medium">{val}</td>
    </tr>
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Produto" className="min-w-[280px]">
          <Input placeholder="Nome, SKU, marca…" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </Field>
        <Field label="Canal">
          <Select value={canal} onChange={(e) => setCanal(e.target.value)} className="w-36">
            <option value="">—</option>
            <option value="varejo">Varejo</option>
            <option value="atacado">Atacado</option>
            <option value="contrato">Contrato</option>
            <option value="promocional">Promocional</option>
          </Select>
        </Field>
        <Field label="Margem %">
          <Input type="number" step="0.1" value={margem} onChange={(e) => setMargem(e.target.value)} className="w-24" />
        </Field>
        <Field label="Markup %">
          <Input type="number" step="0.1" value={markup} onChange={(e) => setMarkup(e.target.value)} className="w-24" />
        </Field>
        <Field label="Comissão %">
          <Input type="number" step="0.1" value={comissao} onChange={(e) => setComissao(e.target.value)} className="w-24" />
        </Field>
        <Field label="Despesas %">
          <Input type="number" step="0.1" value={despesas} onChange={(e) => setDespesas(e.target.value)} className="w-24" />
        </Field>
        <Field label="Taxas %">
          <Input type="number" step="0.1" value={taxas} onChange={(e) => setTaxas(e.target.value)} className="w-24" />
        </Field>
        <Button variant="primary" onClick={() => void calcular()}>
          Calcular
        </Button>
      </div>

      {sugestoes.length > 0 ? (
        <div className="mb-4 divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
          {sugestoes.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setSelecionada(p);
                setSugestoes([]);
                setResultado(null);
              }}
              className="flex w-full items-center justify-between px-4 py-2 text-left text-sm hover:bg-gray-50"
            >
              <span>
                <span className="font-medium">{p.name}</span>
                {p.sku ? <span className="ml-2 font-mono text-xs text-gray-400">{p.sku}</span> : null}
              </span>
              <span className="text-xs text-gray-500">
                {p.brand ? p.brand + " · " : ""}
                {fmtMoney(p.price)}
              </span>
            </button>
          ))}
        </div>
      ) : null}

      {selecionada ? (
        <p className="mb-4 text-sm text-gray-600">
          Selecionado: <span className="font-medium">{selecionada.name}</span>
          {selecionada.sku ? <span className="ml-2 font-mono text-xs text-gray-400">{selecionada.sku}</span> : null} (produto #{selecionada.id})
        </p>
      ) : null}

      {carregando ? <Loading message="Calculando…" /> : null}
      {erro ? <div className="py-4 text-center text-sm text-gray-400">Erro: {erro}</div> : null}

      {resultado && selecionada ? (
        <div className="max-w-xl rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="mb-3 font-semibold text-gray-900">
            {selecionada.name}
            {selecionada.sku ? <span className="ml-2 font-mono text-xs text-gray-400">{selecionada.sku}</span> : null}
          </h3>
          <Table>
            <TBody>
              {linha("Custo base", resultado.custo_base != null ? fmtMoney(resultado.custo_base) : "—")}
              {linha("Custo líquido", resultado.custo_liquido != null ? fmtMoney(resultado.custo_liquido) : "—")}
              {linha("Despesas + comissão + taxas", pct(resultado.despesas_pct.total))}
              {linha("Preço mínimo", resultado.preco_minimo != null ? fmtMoney(resultado.preco_minimo) : "—")}
              <tr className="bg-brand-50">
                <td className="px-4 py-2 text-sm font-semibold text-brand-700">Preço sugerido</td>
                <td className="px-4 py-2 text-right text-sm font-semibold text-brand-700">
                  {resultado.preco_sugerido != null ? fmtMoney(resultado.preco_sugerido) : "—"}
                </td>
              </tr>
              {linha("Margem efetiva", pct(resultado.margem_efetiva_pct))}
              {linha("Markup efetivo", pct(resultado.markup_efetivo_pct))}
            </TBody>
          </Table>
          {resultado.observacao ? <p className="mt-2 text-xs text-gray-500">{resultado.observacao}</p> : null}

          {f ? (
            <details className="mt-3">
              <summary className="cursor-pointer text-sm font-medium text-gray-600">Detalhamento fiscal</summary>
              <div className="mt-2 grid grid-cols-2 gap-2 rounded-md bg-gray-50 p-3 text-sm">
                <div>
                  <span className="text-xs text-gray-400">Regime</span>
                  <div className="font-medium">{f.regime}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">NCM</span>
                  <div className="font-medium">{f.ncm || "—"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">CEST</span>
                  <div className="font-medium">{f.cest || "—"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">CSOSN</span>
                  <div className="font-medium">{f.csosn || "—"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">ICMS</span>
                  <div className="font-medium">{pct(f.aliquota_icms)}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">ICMS-ST</span>
                  <div className="font-medium">{f.icms_st.aplica ? pct(f.icms_st.aliquota) + " · MVA " + pct(f.icms_st.mva) : "não"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">DIFAL</span>
                  <div className="font-medium">{f.difal.aplica ? `${f.difal.uf_origem}→${f.difal.uf_dest || ""}` : "não"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">Créditos</span>
                  <div className="font-medium">{pct(f.creditos.total_pct)}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">Benefício</span>
                  <div className="font-medium">{f.beneficio ? f.beneficio.descricao : "—"}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-400">IBPT (referência)</span>
                  <div className="font-medium">{f.ibpt ? pct(f.ibpt.federal + f.ibpt.estadual + f.ibpt.municipal) : "—"}</div>
                </div>
              </div>
            </details>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

// ──────────────────────────────────────────────────────────
//  Histórico de preços (auditoria)
// ──────────────────────────────────────────────────────────

function Historico() {
  const [tabelas, setTabelas] = useState<TabelaPreco[]>([]);
  const [filtroTab, setFiltroTab] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<HistoricoPrecoItem[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = async () => {
    setCarregando(true);
    try {
      const tabela_id = parseInt(filtroTab, 10) || undefined;
      setRows(await api.listarHistoricoPrecos({ tabela_id, q: q.trim() || undefined }));
    } catch {
      setRows([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void api
      .listarTabelasPreco()
      .then(setTabelas)
      .catch(() => {});
  }, []);

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
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
        <Field label="Busca">
          <Input
            placeholder="Produto, SKU, tabela…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void carregar();
            }}
            className="w-64"
          />
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Data", "Produto", "Tabela", "Anterior", "Novo", "Margem", "Origem", "Aprovado por"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={8} message="Nenhum registro" />
            ) : (
              rows.map((h) => (
                <tr key={h.id} className="hover:bg-gray-50">
                  <Cell className="text-xs text-gray-500">{fmtDateTime(h.criado_em)}</Cell>
                  <Cell>
                    <span className="font-medium">{h.produto_nome}</span>
                    {h.sku ? <div className="font-mono text-xs text-gray-400">{h.sku}</div> : null}
                  </Cell>
                  <Cell>{h.tabela_nome}</Cell>
                  <Cell>{fmtMoney(h.preco_anterior)}</Cell>
                  <Cell className="font-medium">{fmtMoney(h.preco_novo)}</Cell>
                  <Cell>{h.margem_pct != null ? h.margem_pct.toFixed(2).replace(".", ",") + "%" : "—"}</Cell>
                  <Cell>
                    <Badge>{h.origem || h.tipo}</Badge>
                  </Cell>
                  <Cell>{h.usuario_nome ?? "—"}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}
