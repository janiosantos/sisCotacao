// pages/financeiro.tsx — financeiro (React + Tailwind).

import { useEffect, useState } from "react";
import {
  api,
  type CobrancaResultado,
  type ContaPagar,
  type ContaReceber,
} from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { copiarTexto, toast } from "../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, PageHeader, Select, Table, TBody, THead } from "../ui/ui";
import { Adiantamentos } from "./financeiro/adiantamentos";
import { AnexoButton } from "./financeiro/anexo-button";
import { Centros } from "./financeiro/centros";
import { Condicoes } from "./financeiro/condicoes";
import { ModalLancamento } from "./financeiro/modal-lancamento";
import { ClassificacaoDespesas } from "./financeiro/classificacao";

type Aba = "caixa" | "receber" | "pagar" | "condicoes" | "centros" | "adiantamentos" | "classificacao";

const ABAS: { key: Aba; label: string }[] = [
  { key: "caixa", label: "Caixa" },
  { key: "receber", label: "Receber" },
  { key: "pagar", label: "Pagar" },
  { key: "condicoes", label: "Condições" },
  { key: "centros", label: "Centros Custo" },
  { key: "adiantamentos", label: "Adiantamentos" },
  { key: "classificacao", label: "Classificação" },
];

export default function Financeiro() {
  const [aba, setAba] = useState<Aba>("caixa");

  return (
    <div>
      <PageHeader title="Financeiro" subtitle="Caixa, contas a receber e contas a pagar." />
      <div className="mb-5 flex gap-2 overflow-x-auto border-b border-gray-200">
        {ABAS.map((a) => (
          <button
            key={a.key}
            onClick={() => setAba(a.key)}
            className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${
              aba === a.key ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {a.label}
          </button>
        ))}
      </div>
      {aba === "caixa" && <Caixa />}
      {aba === "receber" && <Receber />}
      {aba === "pagar" && <Pagar />}
      {aba === "condicoes" && <Condicoes />}
      {aba === "centros" && <Centros />}
      {aba === "adiantamentos" && <Adiantamentos />}
      {aba === "classificacao" && <ClassificacaoDespesas />}
    </div>
  );
}

interface MovCaixa {
  id: number;
  tipo: string;
  descricao: string;
  valor: number;
  saldo_posterior: number;
  forma_pagamento: string;
  documento: string | null;
  criado_em: string;
}

function Caixa() {
  const [saldo, setSaldo] = useState(0);
  const [rows, setRows] = useState<MovCaixa[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [tipo, setTipo] = useState("entrada");
  const [form, setForm] = useState({ desc: "", valor: "", forma: "dinheiro", doc: "" });

  const carregar = async () => {
    try {
      const r = await api.saldoCaixa();
      setSaldo(r.saldo);
      setRows(await api.listarMovimentosCaixa({ limit: 50 }));
    } catch {
      toast("Erro ao carregar caixa", "error");
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = (t: string) => {
    setTipo(t);
    setForm({ desc: "", valor: "", forma: "dinheiro", doc: "" });
    setModalOpen(true);
  };

  const salvar = async () => {
    const valor = parseFloat(form.valor.replace(",", "."));
    if (!form.desc.trim() || valor <= 0) {
      toast("Preencha descrição e valor", "error");
      return;
    }
    try {
      await api.movimentarCaixa({ tipo, descricao: form.desc.trim(), valor, forma_pagamento: form.forma, documento: form.doc.trim() || undefined });
      setModalOpen(false);
      toast("Movimento registrado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const label = { entrada: "Entrada", saida: "Saída", suprimento: "Suprimento", sangria: "Sangria" }[tipo] || tipo;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="rounded-lg border border-gray-200 bg-white px-5 py-3">
          <div className="text-xs font-medium uppercase text-gray-500">Saldo do caixa</div>
          <div className="text-2xl font-semibold text-gray-900">{fmtMoney(saldo)}</div>
        </div>
        <Button variant="primary" onClick={() => abrir("entrada")}>
          + Entrada
        </Button>
        <Button variant="danger" onClick={() => abrir("saida")}>
          - Saída
        </Button>
        <Button onClick={() => abrir("suprimento")}>Suprimento</Button>
        <Button onClick={() => abrir("sangria")}>Sangria</Button>
      </div>

      <Table>
        <THead cols={["Data", "Tipo", "Descrição", "Valor", "Saldo", "Forma", "Doc"]} />
        <TBody>
          {rows.length === 0 ? (
            <EmptyRow colSpan={7} message="Nenhum movimento" />
          ) : (
            rows.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50">
                <Cell className="text-xs text-gray-500">{fmtDate(m.criado_em)}</Cell>
                <Cell>
                  <Badge tone={m.tipo === "entrada" || m.tipo === "abertura" || m.tipo === "suprimento" ? "green" : "red"}>{m.tipo}</Badge>
                </Cell>
                <Cell>{m.descricao}</Cell>
                <Cell className="font-medium">{fmtMoney(m.valor)}</Cell>
                <Cell className="text-xs text-gray-500">{fmtMoney(m.saldo_posterior)}</Cell>
                <Cell>{m.forma_pagamento}</Cell>
                <Cell className="font-mono text-xs">{m.documento || ""}</Cell>
              </tr>
            ))
          )}
        </TBody>
      </Table>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={label}
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Registrar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Descrição">
            <Input value={form.desc} onChange={(e) => setForm({ ...form, desc: e.target.value })} autoFocus />
          </Field>
          <Field label="Valor">
            <Input type="number" step="0.01" min="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} />
          </Field>
          <Field label="Forma de pagamento">
            <Select value={form.forma} onChange={(e) => setForm({ ...form, forma: e.target.value })}>
              {["dinheiro", "pix", "credito", "debito", "boleto", "cheque", "outro"].map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Documento">
            <Input value={form.doc} onChange={(e) => setForm({ ...form, doc: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

function Receber() {
  const [rows, setRows] = useState<ContaReceber[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalConta, setModalConta] = useState(false);
  const [modalReceber, setModalReceber] = useState<ContaReceber | null>(null);
  const [rec, setRec] = useState({ valor: "", data: "", forma: "dinheiro" });
  const [modalCobranca, setModalCobranca] = useState<ContaReceber | null>(null);
  const [cobranca, setCobranca] = useState<CobrancaResultado | null>(null);
  const [comprovante, setComprovante] = useState<File | null>(null);
  const [emitindo, setEmitindo] = useState(false);

  const carregar = async () => {
    try {
      setRows(await api.listarReceber());
    } catch {
      toast("Erro ao carregar contas a receber", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrirReceber = (c: ContaReceber) => {
    setModalReceber(c);
    setRec({ valor: String(c.saldo), data: "", forma: "dinheiro" });
    setComprovante(null);
  };

  const receber = async () => {
    if (!modalReceber) return;
    const valor = parseFloat(rec.valor.replace(",", "."));
    if (valor <= 0) {
      toast("Valor inválido", "error");
      return;
    }
    const precisaComprovante = rec.forma === "deposito_bancario" || rec.forma === "ted";
    if (precisaComprovante && !comprovante) {
      toast("Anexe o comprovante para depósito/TED", "error");
      return;
    }
    try {
      if (precisaComprovante && comprovante) {
        const fd = new FormData();
        fd.append("file", comprovante);
        fd.append("tipo", rec.forma);
        await api.anexarComprovante(modalReceber.id, fd);
      }
      await api.receberConta(modalReceber.id, {
        valor,
        data_recebimento: rec.data || undefined,
        forma_pagamento: rec.forma,
      });
      setModalReceber(null);
      toast("Recebimento registrado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const emitir = async (operacao: "boleto" | "pix") => {
    if (!modalCobranca) return;
    setEmitindo(true);
    try {
      const r = await api.emitirCobranca(modalCobranca.id, operacao);
      setCobranca(r);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setEmitindo(false);
    }
  };

  const atualizarStatus = async (c: ContaReceber) => {
    try {
      await api.statusCobranca(c.id);
      await carregar();
      toast("Status atualizado", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalConta(true)}>
          Nova conta a receber
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Cliente", "Descrição", "Parcela", "Valor", "Saldo", "Vencimento", "Status", "Cobrança", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={9} message="Nenhuma conta" />
            ) : (
              rows.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <Cell className="font-medium">{c.cliente}</Cell>
                  <Cell>{c.descricao}</Cell>
                  <Cell className="text-xs">
                    {c.total_parcelas && c.total_parcelas > 1 ? `${c.parcela}/${c.total_parcelas}` : "—"}
                    {c.recorrencia ? <Badge tone="blue">{c.recorrencia}</Badge> : null}
                  </Cell>
                  <Cell>{fmtMoney(c.valor)}</Cell>
                  <Cell className="font-medium">{fmtMoney(c.saldo)}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(c.data_vencimento)}</Cell>
                  <Cell>
                    <Badge tone={c.status === "pago" ? "green" : c.status === "aberto" ? "amber" : "red"}>{c.status}</Badge>
                  </Cell>
                  <Cell>
                    {c.status !== "pago" ? (
                      c.status_cobranca === "pago" ? (
                        <Badge tone="green">Pago</Badge>
                      ) : c.status_cobranca === "pendente" ? (
                        <Badge tone="blue">Pendente</Badge>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </Cell>
                  <Cell>
                    {c.status !== "pago" ? (
                      <div className="flex justify-end gap-2">
                        <AnexoButton tabela="receber" contaId={c.id} />
                        <Button size="sm" onClick={() => { setModalCobranca(c); setCobranca(null); }}>
                          Boleto / PIX
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => void atualizarStatus(c)} title="Consultar status">
                          ↻
                        </Button>
                        <Button size="sm" variant="primary" onClick={() => abrirReceber(c)}>
                          Receber
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

      <ModalLancamento
        open={modalConta}
        tabela="receber"
        pessoaLabel="Cliente"
        onClose={() => setModalConta(false)}
        onSalvo={() => { setModalConta(false); void carregar(); }}
      />

      {/* Modal de emissão de cobrança (boleto/PIX) */}
      <Modal
        open={modalCobranca != null}
        onClose={() => setModalCobranca(null)}
        title={modalCobranca ? `Cobrança — ${modalCobranca.cliente}` : ""}
        wide
        footer={
          <>
            <Button onClick={() => setModalCobranca(null)}>Fechar</Button>
            {modalCobranca && modalCobranca.status !== "pago" && (
              <>
                <Button variant="secondary" onClick={() => void emitir("boleto")} disabled={emitindo}>
                  {emitindo ? "…" : "Emitir boleto"}
                </Button>
                <Button variant="primary" onClick={() => void emitir("pix")} disabled={emitindo}>
                  {emitindo ? "…" : "Emitir PIX"}
                </Button>
              </>
            )}
          </>
        }
      >
        {modalCobranca ? (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              {modalCobranca.cliente} · Saldo: {fmtMoney(modalCobranca.saldo)} · Vencimento {fmtDate(modalCobranca.data_vencimento)}
            </p>
            {cobranca ? (
              <div className="rounded-md border border-gray-200 p-4">
                {cobranca.operacao === "boleto" ? (
                  <div className="space-y-2 text-sm">
                    {cobranca.url_boleto ? (
                      <a className="inline-flex items-center gap-1.5 rounded-md bg-brand-600 px-3 py-1.5 text-white hover:bg-brand-700" target="_blank" rel="noreferrer" href={cobranca.url_boleto}>
                        Abrir boleto
                      </a>
                    ) : null}
                    {cobranca.linha_digitavel ? (
                      <div className="rounded bg-gray-50 p-2 font-mono text-xs">{cobranca.linha_digitavel}</div>
                    ) : null}
                    {cobranca.nosso_numero ? <div className="text-xs text-gray-500">Nosso número: {cobranca.nosso_numero}</div> : null}
                    <div className="text-xs text-gray-400">Provider: {cobranca.provider}</div>
                  </div>
                ) : (
                  <div className="space-y-3 text-sm">
                    {cobranca.qr_code_base64 ? (
                      <img src={`data:image/png;base64,${cobranca.qr_code_base64}`} alt="QR Code PIX" className="mx-auto h-40 w-40 object-contain" />
                    ) : null}
                    {cobranca.payload_pix ? (
                      <div>
                        <div className="mb-1 text-xs font-medium text-gray-500">PIX Copia e Cola</div>
                        <div className="rounded bg-gray-50 p-2 font-mono text-xs break-all">{cobranca.payload_pix}</div>
                        <Button size="sm" className="mt-2" onClick={() => void copiarTexto(cobranca.payload_pix || "").then((ok) => toast(ok ? "Copia e cola copiado!" : "Não foi possível copiar", ok ? "" : "error"))}>
                          Copiar
                        </Button>
                      </div>
                    ) : null}
                    <div className="text-xs text-gray-400">Provider: {cobranca.provider}</div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-400">
                Escolha <b>Emitir boleto</b> ou <b>Emitir PIX</b> para gerar a cobrança na plataforma (Asaas / Mercado Pago).
              </p>
            )}
          </div>
        ) : null}
      </Modal>

      {/* Modal de recebimento com forma de pagamento */}
      <Modal
        open={modalReceber != null}
        onClose={() => setModalReceber(null)}
        title={modalReceber ? `Receber — ${modalReceber.cliente}` : ""}
        footer={
          <>
            <Button onClick={() => setModalReceber(null)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void receber()}>
              Confirmar recebimento
            </Button>
          </>
        }
      >
        {modalReceber ? (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Valor original: {fmtMoney(modalReceber.valor)} · Saldo: {fmtMoney(modalReceber.saldo)}
            </p>
            <Field label="Forma de pagamento">
              <Select value={rec.forma} onChange={(e) => setRec({ ...rec, forma: e.target.value })}>
                <option value="dinheiro">Dinheiro</option>
                <option value="pix">PIX</option>
                <option value="cheque">Cheque</option>
                <option value="deposito_bancario">Depósito bancário</option>
                <option value="ted">TED / transferência</option>
                <option value="transferencia">Transferência</option>
                <option value="cartao_debito">Cartão débito</option>
                <option value="cartao_credito">Cartão crédito</option>
                <option value="boleto">Boleto</option>
              </Select>
            </Field>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Valor a receber">
                <Input type="number" step="0.01" value={rec.valor} onChange={(e) => setRec({ ...rec, valor: e.target.value })} />
              </Field>
              <Field label="Data do recebimento">
                <Input type="date" value={rec.data} onChange={(e) => setRec({ ...rec, data: e.target.value })} />
              </Field>
            </div>
            {(rec.forma === "deposito_bancario" || rec.forma === "ted") && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
                <Field label="Comprovante (obrigatório)">
                  <input
                    type="file"
                    accept="image/*,.pdf"
                    onChange={(e) => setComprovante(e.target.files?.[0] ?? null)}
                    className="text-sm"
                  />
                </Field>
                <p className="mt-1 text-xs text-amber-700">
                  Anexe o comprovante para confirmar o depósito/TED. A baixa é manual.
                </p>
              </div>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

function Pagar() {
  const [rows, setRows] = useState<ContaPagar[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalConta, setModalConta] = useState(false);
  const [modalPagar, setModalPagar] = useState<ContaPagar | null>(null);
  const [pag, setPag] = useState({ valor: "", data: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarPagar());
    } catch {
      toast("Erro ao carregar contas a pagar", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const pagar = async () => {
    if (!modalPagar) return;
    const valor = parseFloat(pag.valor.replace(",", "."));
    if (valor <= 0) {
      toast("Valor inválido", "error");
      return;
    }
    try {
      await api.pagarConta(modalPagar.id, { valor, data_pagamento: pag.data || undefined });
      setModalPagar(null);
      toast("Pagamento registrado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const excluirGrupo = async (c: ContaPagar) => {
    if (!c.grupo_id) return;
    if (!window.confirm("Excluir todas as parcelas EM ABERTO deste lançamento?")) return;
    try {
      const r = await api.excluirLote("pagar", c.grupo_id);
      toast(`${r.excluidas} parcela(s) excluída(s)`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalConta(true)}>
          Nova conta a pagar
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Fornecedor", "Descrição", "Parcela", "Valor", "Saldo", "Vencimento", "Status", "Origem", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={9} message="Nenhuma conta" />
            ) : (
              rows.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <Cell className="font-medium">{c.fornecedor}</Cell>
                  <Cell>{c.descricao}</Cell>
                  <Cell className="text-xs">
                    {c.total_parcelas && c.total_parcelas > 1 ? `${c.parcela}/${c.total_parcelas}` : "—"}
                    {c.recorrencia ? <Badge tone="blue">{c.recorrencia}</Badge> : null}
                  </Cell>
                  <Cell>{fmtMoney(c.valor)}</Cell>
                  <Cell className="font-medium">{fmtMoney(c.saldo)}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(c.data_vencimento)}</Cell>
                  <Cell>
                    <Badge tone={c.status === "pago" ? "green" : c.status === "aberto" ? "amber" : "red"}>{c.status}</Badge>
                  </Cell>
                  <Cell className="text-xs">
                    {c.origem_tipo === "pedido_compra" ? (
                      <a className="text-brand-600 hover:underline" href="#/compras" title="Pedido de compra">
                        Pedido {c.documento || c.origem_id}
                      </a>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </Cell>
                  <Cell>
                    {c.status !== "pago" ? (
                      <div className="flex justify-end gap-2">
                        <AnexoButton tabela="pagar" contaId={c.id} />
                        <Button size="sm" onClick={() => { setModalPagar(c); setPag({ valor: String(c.saldo), data: "" }); }}>
                          Pagar
                        </Button>
                        {c.grupo_id && (c.total_parcelas ?? 1) > 1 && c.status !== "pago" ? (
                          <Button size="sm" variant="ghost" onClick={() => void excluirGrupo(c)} title="Excluir parcelas em aberto do grupo">
                            🗑
                          </Button>
                        ) : null}
                      </div>
                    ) : null}
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <ModalLancamento
        open={modalConta}
        tabela="pagar"
        pessoaLabel="Fornecedor"
        onClose={() => setModalConta(false)}
        onSalvo={() => { setModalConta(false); void carregar(); }}
      />

      <Modal
        open={modalPagar != null}
        onClose={() => setModalPagar(null)}
        title={modalPagar ? `Pagar — ${modalPagar.fornecedor}` : ""}
        footer={
          <>
            <Button onClick={() => setModalPagar(null)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void pagar()}>
              Pagar
            </Button>
          </>
        }
      >
        {modalPagar ? (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Valor original: {fmtMoney(modalPagar.valor)} · Saldo: {fmtMoney(modalPagar.saldo)}
              {modalPagar.total_parcelas && modalPagar.total_parcelas > 1 ? ` · Parcela ${modalPagar.parcela}/${modalPagar.total_parcelas}` : ""}
            </p>
            <Field label="Valor a pagar">
              <Input type="number" step="0.01" value={pag.valor} onChange={(e) => setPag({ ...pag, valor: e.target.value })} />
            </Field>
            <Field label="Data do pagamento">
              <Input type="date" value={pag.data} onChange={(e) => setPag({ ...pag, data: e.target.value })} />
            </Field>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

