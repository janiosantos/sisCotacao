// pages/financeiro.tsx — financeiro (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type CobrancaResultado, type CondicaoPagamento, type ContaPayload, type ContaPagar, type ContaReceber } from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, PageHeader, Select, Table, TBody, THead, Textarea } from "../ui/ui";

type Aba = "caixa" | "receber" | "pagar" | "condicoes" | "centros" | "adiantamentos";

const ABAS: { key: Aba; label: string }[] = [
  { key: "caixa", label: "Caixa" },
  { key: "receber", label: "Receber" },
  { key: "pagar", label: "Pagar" },
  { key: "condicoes", label: "Condições" },
  { key: "centros", label: "Centros Custo" },
  { key: "adiantamentos", label: "Adiantamentos" },
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
  const [form, setForm] = useState({ cliente: "", desc: "", valor: "", venc: "", doc: "", obs: "" });
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

  const salvarConta = async () => {
    const payload: ContaPayload = {
      cliente: form.cliente.trim(),
      valor: parseFloat(form.valor.replace(",", ".")),
      data_vencimento: form.venc,
      descricao: form.desc.trim(),
      documento: form.doc.trim() || undefined,
      observacao: form.obs.trim() || undefined,
    };
    if (!payload.valor || !payload.data_vencimento || !payload.cliente) {
      toast("Preencha nome, valor e vencimento", "error");
      return;
    }
    try {
      await api.criarReceber(payload);
      setModalConta(false);
      toast("Conta criada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

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
          <THead cols={["Cliente", "Descrição", "Valor", "Saldo", "Vencimento", "Status", "Cobrança", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={8} message="Nenhuma conta" />
            ) : (
              rows.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <Cell className="font-medium">{c.cliente}</Cell>
                  <Cell>{c.descricao}</Cell>
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

      <Modal
        open={modalConta}
        onClose={() => setModalConta(false)}
        title="Nova conta a Receber"
        footer={
          <>
            <Button onClick={() => setModalConta(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvarConta()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Cliente">
            <Input value={form.cliente} onChange={(e) => setForm({ ...form, cliente: e.target.value })} autoFocus />
          </Field>
          <Field label="Descrição">
            <Input value={form.desc} onChange={(e) => setForm({ ...form, desc: e.target.value })} />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Valor">
              <Input type="number" step="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} />
            </Field>
            <Field label="Vencimento">
              <Input type="date" value={form.venc} onChange={(e) => setForm({ ...form, venc: e.target.value })} />
            </Field>
          </div>
          <Field label="Documento">
            <Input value={form.doc} onChange={(e) => setForm({ ...form, doc: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.obs} onChange={(e) => setForm({ ...form, obs: e.target.value })} />
          </Field>
        </div>
      </Modal>

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
                        <Button size="sm" className="mt-2" onClick={() => void navigator.clipboard.writeText(cobranca.payload_pix || "").then(() => toast("Copia e cola copiado!"))}>
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
  const [form, setForm] = useState({ fornecedor: "", desc: "", valor: "", venc: "", doc: "", obs: "" });
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

  const salvarConta = async () => {
    const payload: ContaPayload = {
      fornecedor: form.fornecedor.trim(),
      valor: parseFloat(form.valor.replace(",", ".")),
      data_vencimento: form.venc,
      descricao: form.desc.trim(),
      documento: form.doc.trim() || undefined,
      observacao: form.obs.trim() || undefined,
    };
    if (!payload.valor || !payload.data_vencimento || !payload.fornecedor) {
      toast("Preencha nome, valor e vencimento", "error");
      return;
    }
    try {
      await api.criarPagar(payload);
      setModalConta(false);
      toast("Conta criada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

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
          <THead cols={["Fornecedor", "Descrição", "Valor", "Saldo", "Vencimento", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={7} message="Nenhuma conta" />
            ) : (
              rows.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <Cell className="font-medium">{c.fornecedor}</Cell>
                  <Cell>{c.descricao}</Cell>
                  <Cell>{fmtMoney(c.valor)}</Cell>
                  <Cell className="font-medium">{fmtMoney(c.saldo)}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(c.data_vencimento)}</Cell>
                  <Cell>
                    <Badge tone={c.status === "pago" ? "green" : c.status === "aberto" ? "amber" : "red"}>{c.status}</Badge>
                  </Cell>
                  <Cell>
                    {c.status !== "pago" ? (
                      <Button size="sm" onClick={() => { setModalPagar(c); setPag({ valor: String(c.saldo), data: "" }); }}>
                        Pagar
                      </Button>
                    ) : null}
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalConta}
        onClose={() => setModalConta(false)}
        title="Nova conta a Pagar"
        footer={
          <>
            <Button onClick={() => setModalConta(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvarConta()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Fornecedor">
            <Input value={form.fornecedor} onChange={(e) => setForm({ ...form, fornecedor: e.target.value })} autoFocus />
          </Field>
          <Field label="Descrição">
            <Input value={form.desc} onChange={(e) => setForm({ ...form, desc: e.target.value })} />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Valor">
              <Input type="number" step="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} />
            </Field>
            <Field label="Vencimento">
              <Input type="date" value={form.venc} onChange={(e) => setForm({ ...form, venc: e.target.value })} />
            </Field>
          </div>
          <Field label="Documento">
            <Input value={form.doc} onChange={(e) => setForm({ ...form, doc: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.obs} onChange={(e) => setForm({ ...form, obs: e.target.value })} />
          </Field>
        </div>
      </Modal>

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

function Condicoes() {
  const [rows, setRows] = useState<CondicaoPagamento[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<CondicaoPagamento | null>(null);
  const [form, setForm] = useState({ nome: "", descricao: "", parcelas: "" });
  const [parcelasModal, setParcelasModal] = useState<CondicaoPagamento | null>(null);

  const carregar = async () => {
    try {
      setRows(await api.listarCondicoes());
    } catch {
      toast("Erro ao carregar condições", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = async (c: CondicaoPagamento | null) => {
    setEditando(c);
    setForm({ nome: c?.nome ?? "", descricao: c?.descricao ?? "", parcelas: "" });
    setModalOpen(true);
    if (c) {
      try {
        const det = await api.getCondicao(c.id);
        setForm((f) => ({ ...f, parcelas: (det.parcelas || []).map((p) => `${p.sequencia}:${p.dias},${p.percentual}`).join("\n") }));
      } catch {
        /* segue */
      }
    }
  };

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome", "error");
      return;
    }
    try {
      let cond = editando;
      if (editando) {
        await api.atualizarCondicao(editando.id, { nome: form.nome.trim(), descricao: form.descricao.trim() });
      } else {
        const r = await api.criarCondicao({ nome: form.nome.trim(), descricao: form.descricao.trim() });
        cond = { id: r.id, nome: form.nome.trim(), descricao: form.descricao.trim(), ativo: true };
      }
      const parcelas = form.parcelas
        .split("\n")
        .map((linha) => {
          const [seq, resto] = linha.split(":");
          const [dias, pct] = (resto || "").split(",");
          return { sequencia: parseInt(seq, 10), dias: parseInt(dias, 10), percentual: parseFloat(pct.replace(",", ".")) };
        })
        .filter((p) => p.sequencia > 0);
      if (cond && parcelas.length) await api.salvarParcelas(cond.id, parcelas);
      setModalOpen(false);
      toast(editando ? "Condição atualizada" : "Condição criada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => void abrir(null)}>
          Nova condição
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Nome", "Parcelas", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={4} message="Nenhuma condição" />
            ) : (
              rows.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{c.nome}</span>
                    {c.descricao ? <div className="text-xs text-gray-500">{c.descricao}</div> : null}
                  </Cell>
                  <Cell>
                    <Button size="sm" variant="ghost" onClick={async () => setParcelasModal(await api.getCondicao(c.id))}>
                      Ver parcelas
                    </Button>
                  </Cell>
                  <Cell>
                    <Badge tone={c.ativo ? "green" : "red"}>{c.ativo ? "Ativa" : "Inativa"}</Badge>
                  </Cell>
                  <Cell>
                    <Button size="sm" onClick={() => void abrir(c)}>
                      Editar
                    </Button>
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editando ? "Editar condição" : "Nova condição"}
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Nome *">
            <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus />
          </Field>
          <Field label="Descrição">
            <Input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
          </Field>
          <Field label="Parcelas (sequência: dias,%) — uma por linha">
            <Textarea
              rows={4}
              placeholder={"Ex.:\n1:0,100\n2:30,50\n3:60,50"}
              value={form.parcelas}
              onChange={(e) => setForm({ ...form, parcelas: e.target.value })}
            />
          </Field>
        </div>
      </Modal>

      <Modal open={parcelasModal != null} onClose={() => setParcelasModal(null)} title={parcelasModal ? `${parcelasModal.nome} — Parcelas` : ""} footer={<Button onClick={() => setParcelasModal(null)}>Fechar</Button>}>
        <Table>
          <THead cols={["#", "Dias", "%"]} />
          <TBody>
            {(parcelasModal?.parcelas || []).map((p) => (
              <tr key={p.sequencia} className="hover:bg-gray-50">
                <Cell>{p.sequencia}</Cell>
                <Cell>{p.dias}</Cell>
                <Cell>{p.percentual}%</Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      </Modal>
    </div>
  );
}

interface CentroCusto {
  id: number;
  codigo: string;
  nome: string;
  ativo: number | boolean;
}

function Centros() {
  const [rows, setRows] = useState<CentroCusto[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ codigo: "", nome: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarCentrosCusto());
    } catch {
      toast("Erro ao carregar centros", "error");
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    try {
      await api.criarCentroCusto({ codigo: form.codigo.trim(), nome: form.nome.trim() });
      setModalOpen(false);
      toast("Centro criado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Novo centro
        </Button>
      </div>
      <Table>
        <THead cols={["Código", "Nome", "Status"]} />
        <TBody>
          {rows.length === 0 ? (
            <EmptyRow colSpan={3} message="Nenhum centro" />
          ) : (
            rows.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <Cell className="font-mono font-semibold">{c.codigo}</Cell>
                <Cell>{c.nome}</Cell>
                <Cell>
                  <Badge tone={c.ativo ? "green" : "red"}>{c.ativo ? "Ativo" : "Inativo"}</Badge>
                </Cell>
              </tr>
            ))
          )}
        </TBody>
      </Table>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Novo centro de custo"
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Código">
            <Input value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} autoFocus />
          </Field>
          <Field label="Nome">
            <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

interface Adiantamento {
  id: number;
  tipo: string;
  pessoa_nome: string;
  valor: number;
  saldo: number;
  data_adiantamento: string;
}

function Adiantamentos() {
  const [rows, setRows] = useState<Adiantamento[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ tipo: "cliente", nome: "", valor: "", data: "", obs: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarAdiantamentos());
    } catch {
      toast("Erro ao carregar adiantamentos", "error");
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    try {
      await api.criarAdiantamento({
        tipo: form.tipo,
        pessoa_nome: form.nome.trim(),
        valor: parseFloat(form.valor.replace(",", ".")),
        data_adiantamento: form.data,
        observacao: form.obs.trim() || undefined,
      });
      setModalOpen(false);
      toast("Adiantamento criado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Novo adiantamento
        </Button>
      </div>
      <Table>
        <THead cols={["Tipo", "Pessoa", "Valor", "Saldo", "Data"]} />
        <TBody>
          {rows.length === 0 ? (
            <EmptyRow colSpan={5} message="Nenhum" />
          ) : (
            rows.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50">
                <Cell>
                  <Badge tone="gray">{a.tipo}</Badge>
                </Cell>
                <Cell className="font-medium">{a.pessoa_nome}</Cell>
                <Cell>{fmtMoney(a.valor)}</Cell>
                <Cell className="font-medium">{fmtMoney(a.saldo)}</Cell>
                <Cell className="text-xs text-gray-500">{fmtDate(a.data_adiantamento)}</Cell>
              </tr>
            ))
          )}
        </TBody>
      </Table>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Novo adiantamento"
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Tipo">
            <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              <option value="cliente">Cliente</option>
              <option value="fornecedor">Fornecedor</option>
            </Select>
          </Field>
          <Field label="Nome">
            <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus />
          </Field>
          <Field label="Valor">
            <Input type="number" step="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} />
          </Field>
          <Field label="Data">
            <Input type="date" value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.obs} onChange={(e) => setForm({ ...form, obs: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}
