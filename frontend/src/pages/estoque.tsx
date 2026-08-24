// pages/estoque.tsx — estoque (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type Deposito, type Expedicao, type LoteItem, type LotePayload, type MovimentoItem, type MovimentoPayload, type SaldoItem } from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Modal, PageHeader, Select, Table, TBody, THead, Textarea } from "../ui/ui";

type Aba = "saldo" | "depositos" | "movimentos" | "lotes" | "expedicao" | "inventario";

export default function Estoque() {
  const [aba, setAba] = useState<Aba>("saldo");
  const [depositos, setDepositos] = useState<Deposito[]>([]);

  const carregarDepositos = async () => {
    try {
      setDepositos(await api.listarDepositos());
    } catch {
      /* silêncio */
    }
  };

  useEffect(() => {
    void carregarDepositos();
  }, []);

  const TABS: { key: Aba; label: string }[] = [
    { key: "saldo", label: "Saldo" },
    { key: "depositos", label: "Depósitos" },
    { key: "movimentos", label: "Movimentos" },
    { key: "lotes", label: "Lotes" },
    { key: "expedicao", label: "Expedição" },
    { key: "inventario", label: "Inventário" },
  ];

  return (
    <div>
      <PageHeader title="Estoque" subtitle="Saldo, depósitos, movimentos e lotes." />
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
      {aba === "saldo" && <Saldo depositos={depositos} />}
      {aba === "depositos" && <Depositos depositos={depositos} onUpdate={carregarDepositos} />}
      {aba === "movimentos" && <Movimentos depositos={depositos} />}
      {aba === "lotes" && <Lotes depositos={depositos} />}
      {aba === "expedicao" && <Expedicao />}
      {aba === "inventario" && <Inventario depositos={depositos} />}
    </div>
  );
}

function Saldo({ depositos }: { depositos: Deposito[] }) {
  const [rows, setRows] = useState<SaldoItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [dep, setDep] = useState("");
  const [q, setQ] = useState("");
  const [familia, setFamilia] = useState("");

  const [familias, setFamilias] = useState<{ id: number; nome: string }[]>([]);
  useEffect(() => {
    void api.listarFamilias().then(setFamilias).catch(() => {});
  }, []);

  const buscar = async () => {
    setCarregando(true);
    try {
      setRows(
        await api.saldoEstoque({ deposito_id: dep || undefined, familia_id: familia || undefined, q: q || undefined })
      );
    } catch {
      toast("Erro ao carregar saldo", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void buscar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Depósito">
          <Select value={dep} onChange={(e) => setDep(e.target.value)} className="w-48">
            {depositos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Família">
          <Select value={familia} onChange={(e) => setFamilia(e.target.value)} className="w-48">
            <option value="">Todas</option>
            {familias.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Busca">
          <Input placeholder="Produto, SKU, marca…" value={q} onChange={(e) => setQ(e.target.value)} className="w-64" />
        </Field>
        <Button variant="primary" onClick={() => void buscar()}>
          Filtrar
        </Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Produto", "SKU", "Família", "Depósito", "Unid.", "Emb.", "Qtd.", "Preço", "NCM", "Localização", "Atualizado"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={11} message="Nenhum saldo encontrado" />
            ) : (
              rows.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{s.produto_nome}</span>
                    {s.marca ? <div className="text-xs text-gray-400">{s.marca}</div> : null}
                  </Cell>
                  <Cell className="font-mono text-xs">{s.sku}</Cell>
                  <Cell className="text-xs text-gray-500">{s.familia_nome || "—"}</Cell>
                  <Cell>{s.deposito_nome}</Cell>
                  <Cell className="text-xs">{s.unidade_venda || "UN"}</Cell>
                  <Cell className="text-xs">{s.embalagem ? `${s.embalagem}/cx` : "—"}</Cell>
                  <Cell className="font-medium">{s.quantidade}</Cell>
                  <Cell>{fmtMoney(s.preco)}</Cell>
                  <Cell className="font-mono text-xs">{s.ncm || "—"}</Cell>
                  <Cell className="text-xs text-gray-500">{s.localizacao || "—"}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(s.atualizado_em)}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}
    </div>
  );
}

function Depositos({ depositos, onUpdate }: { depositos: Deposito[]; onUpdate: () => void }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Deposito | null>(null);
  const [nome, setNome] = useState("");

  const abrir = (d: Deposito | null) => {
    setEditando(d);
    setNome(d?.nome ?? "");
    setModalOpen(true);
  };

  const salvar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome", "error");
      return;
    }
    try {
      if (editando) await api.atualizarDeposito(editando.id, nome.trim());
      else await api.criarDeposito(nome.trim());
      setModalOpen(false);
      toast(editando ? "Depósito atualizado" : "Depósito criado", "success");
      onUpdate();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alternar = async (d: Deposito) => {
    try {
      await api.alternarAtivoDeposito(d.id, !d.ativo);
      onUpdate();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => abrir(null)}>
          Novo depósito
        </Button>
      </div>
      <Table>
        <THead cols={["Nome", "Ativo", "Criado em", ""]} />
        <TBody>
          {depositos.map((d) => (
            <tr key={d.id} className="hover:bg-gray-50">
              <Cell className="font-medium">{d.nome}</Cell>
              <Cell>
                <Badge tone={d.ativo ? "green" : "red"}>{d.ativo ? "Ativo" : "Inativo"}</Badge>
              </Cell>
              <Cell className="text-xs text-gray-500">{fmtDate(d.criado_em)}</Cell>
              <Cell>
                <div className="flex justify-end gap-2">
                  <Button size="sm" onClick={() => abrir(d)}>
                    Editar
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => alternar(d)}>
                    {d.ativo ? "Desativar" : "Ativar"}
                  </Button>
                </div>
              </Cell>
            </tr>
          ))}
        </TBody>
      </Table>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editando ? "Editar depósito" : "Novo depósito"}
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <Field label="Nome">
          <Input value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
      </Modal>
    </div>
  );
}

function Movimentos({ depositos }: { depositos: Deposito[] }) {
  const [rows, setRows] = useState<MovimentoItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [dep, setDep] = useState("");
  const [tipo, setTipo] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ deposito_id: "", tipo: "entrada", variante_id: "", quantidade: "", documento: "", observacao: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarMovimentos({ deposito_id: dep || undefined, tipo: tipo || undefined }));
    } catch {
      toast("Erro ao carregar movimentos", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const registrar = async () => {
    const payload: MovimentoPayload = {
      deposito_id: Number(form.deposito_id),
      tipo: form.tipo as MovimentoPayload["tipo"],
      variante_id: Number(form.variante_id),
      quantidade: parseFloat(form.quantidade.replace(",", ".")),
      documento: form.documento.trim() || undefined,
      observacao: form.observacao.trim() || undefined,
    };
    if (!payload.deposito_id || !payload.variante_id || payload.quantidade <= 0) {
      toast("Preencha depósito, produto e quantidade", "error");
      return;
    }
    try {
      await api.registrarMovimento(payload);
      setModalOpen(false);
      toast("Movimento registrado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Registrar movimento
        </Button>
        <Field label="Depósito">
          <Select value={dep} onChange={(e) => setDep(e.target.value)} className="w-44">
            <option value="">Todos</option>
            {depositos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Tipo">
          <Select value={tipo} onChange={(e) => setTipo(e.target.value)} className="w-36">
            <option value="">Todos</option>
            <option value="entrada">Entrada</option>
            <option value="saida">Saída</option>
            <option value="ajuste">Ajuste</option>
          </Select>
        </Field>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Data", "Produto", "Depósito", "Tipo", "Qtd", "Saldo ant.", "Saldo novo", "Doc"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={8} message="Nenhum movimento" />
            ) : (
              rows.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <Cell className="text-xs text-gray-500">{fmtDate(m.criado_em)}</Cell>
                  <Cell>
                    <span className="font-medium">{m.produto_nome}</span>
                    <div className="text-xs text-gray-400">{m.sku}</div>
                  </Cell>
                  <Cell>{m.deposito_nome}</Cell>
                  <Cell>
                    <Badge tone={m.tipo === "entrada" ? "green" : m.tipo === "saida" ? "red" : "gray"}>{m.tipo}</Badge>
                  </Cell>
                  <Cell className="font-medium">{m.quantidade}</Cell>
                  <Cell className="text-xs text-gray-500">{m.saldo_anterior}</Cell>
                  <Cell className="text-xs text-gray-500">{m.saldo_posterior}</Cell>
                  <Cell className="font-mono text-xs">{m.documento || ""}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Registrar movimento"
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void registrar()}>
              Registrar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Depósito">
            <Select value={form.deposito_id} onChange={(e) => setForm({ ...form, deposito_id: e.target.value })}>
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Tipo">
            <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              <option value="entrada">Entrada</option>
              <option value="saida">Saída</option>
              <option value="ajuste">Ajuste</option>
            </Select>
          </Field>
          <Field label="Produto (ID da variante)">
            <Input type="number" min={1} value={form.variante_id} onChange={(e) => setForm({ ...form, variante_id: e.target.value })} />
          </Field>
          <Field label="Quantidade">
            <Input type="number" min="0.01" step="any" value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: e.target.value })} />
          </Field>
          <Field label="Documento">
            <Input value={form.documento} onChange={(e) => setForm({ ...form, documento: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

function Lotes({ depositos }: { depositos: Deposito[] }) {
  const [rows, setRows] = useState<LoteItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ deposito_id: "", variante_id: "", codigo: "", quantidade: "", fabricacao: "", validade: "" });

  const carregar = async () => {
    try {
      setRows(await api.listarLotes());
    } catch {
      toast("Erro ao carregar lotes", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    const payload: LotePayload = {
      deposito_id: Number(form.deposito_id),
      variante_id: Number(form.variante_id),
      codigo: form.codigo.trim(),
      quantidade: parseFloat(form.quantidade.replace(",", ".")),
      data_fabricacao: form.fabricacao || undefined,
      data_validade: form.validade || undefined,
    };
    if (!payload.deposito_id || !payload.variante_id || !payload.codigo) {
      toast("Preencha depósito, produto e código do lote", "error");
      return;
    }
    try {
      await api.criarLote(payload);
      setModalOpen(false);
      toast("Lote criado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Novo lote
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Produto", "Lote", "Depósito", "Qtd", "Fabricação", "Validade"]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={6} message="Nenhum lote" />
            ) : (
              rows.map((l) => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{l.produto_nome}</span>
                    <div className="text-xs text-gray-400">{l.sku}</div>
                  </Cell>
                  <Cell className="font-mono text-xs">{l.codigo}</Cell>
                  <Cell>{l.deposito_nome}</Cell>
                  <Cell className="font-medium">{l.quantidade}</Cell>
                  <Cell className="text-xs text-gray-500">{l.data_fabricacao ? fmtDate(l.data_fabricacao) : "—"}</Cell>
                  <Cell className="text-xs text-gray-500">{l.data_validade ? fmtDate(l.data_validade) : "—"}</Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Novo lote"
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
          <Field label="Depósito">
            <Select value={form.deposito_id} onChange={(e) => setForm({ ...form, deposito_id: e.target.value })}>
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Produto (ID da variante)">
            <Input type="number" min={1} value={form.variante_id} onChange={(e) => setForm({ ...form, variante_id: e.target.value })} />
          </Field>
          <Field label="Código do lote">
            <Input value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} />
          </Field>
          <Field label="Quantidade">
            <Input type="number" min={0} step="any" value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: e.target.value })} />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Fabricação">
              <Input type="date" value={form.fabricacao} onChange={(e) => setForm({ ...form, fabricacao: e.target.value })} />
            </Field>
            <Field label="Validade">
              <Input type="date" value={form.validade} onChange={(e) => setForm({ ...form, validade: e.target.value })} />
            </Field>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function Expedicao() {
  const [rows, setRows] = useState<Expedicao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ codigo: "", deposito_id: "", transportadora: "", observacao: "" });
  const [depositos, setDepositos] = useState<Deposito[]>([]);

  const carregar = async () => {
    try {
      setRows(await api.listarExpedicao());
      setDepositos(await api.listarDepositos());
    } catch {
      /* silêncio */
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const salvar = async () => {
    try {
      await api.criarExpedicao({
        codigo: form.codigo.trim(),
        deposito_id: Number(form.deposito_id),
        transportadora: form.transportadora.trim() || undefined,
        observacao: form.observacao.trim() || undefined,
      });
      setModalOpen(false);
      toast("Expedição criada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const statusTone = (s: string) => (s === "finalizado" ? "green" : "gray");

  return (
    <div>
      <div className="mb-4">
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Nova expedição
        </Button>
      </div>
      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Código", "Depósito", "Data", "Transportadora", "Status", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={6} message="Nenhuma" />
            ) : (
              rows.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50">
                  <Cell className="font-mono font-semibold">{e.codigo}</Cell>
                  <Cell>{e.deposito_nome}</Cell>
                  <Cell className="text-xs text-gray-500">{fmtDate(e.data_expedicao)}</Cell>
                  <Cell>{e.transportadora || "—"}</Cell>
                  <Cell>
                    <Badge tone={statusTone(e.status)}>{e.status}</Badge>
                  </Cell>
                  <Cell>
                    <Select
                      value={e.status}
                      onChange={(ev) => void api.atualizarStatusExpedicao(e.id, ev.target.value).then(carregar)}
                      className="w-36 py-1 text-xs"
                    >
                      {["pendente", "separando", "conferido", "carregado", "finalizado"].map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </Select>
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
        title="Nova expedição"
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
            <Input placeholder="EXP-001" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} autoFocus />
          </Field>
          <Field label="Depósito">
            <Select value={form.deposito_id} onChange={(e) => setForm({ ...form, deposito_id: e.target.value })}>
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Transportadora">
            <Input value={form.transportadora} onChange={(e) => setForm({ ...form, transportadora: e.target.value })} />
          </Field>
          <Field label="Observação">
            <Textarea value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

interface InventarioRow {
  id: number;
  nome: string;
  data: string;
  status: string;
  deposito_nome: string | null;
}
interface InventarioItem {
  id: number;
  variante_id: number;
  produto_nome: string;
  sku: string;
  localizacao: string;
  quantidade_sistema: number;
  quantidade_contada: number | null;
}

function Inventario({ depositos }: { depositos: Deposito[] }) {
  const [rows, setRows] = useState<InventarioRow[]>([]);
  const [nome, setNome] = useState("");
  const [dep, setDep] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [invId, setInvId] = useState<number | null>(null);
  const [itens, setItens] = useState<InventarioItem[]>([]);
  const [contados, setContados] = useState<Record<number, string>>({});

  const carregar = async () => {
    try {
      setRows((await api.listarInventarios()) as InventarioRow[]);
    } catch {
      toast("Erro ao carregar inventários", "error");
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const criar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome", "error");
      return;
    }
    try {
      await api.criarInventario({ nome: nome.trim(), deposito_id: Number(dep) || undefined });
      setNome("");
      toast("Inventário criado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const abrirContagem = async (id: number) => {
    setInvId(id);
    setModalOpen(true);
    try {
      const it = (await api.itensInventario(id)) as InventarioItem[];
      setItens(it);
      setContados(Object.fromEntries(it.map((i) => [i.id, String(i.quantidade_contada ?? i.quantidade_sistema)])));
    } catch {
      toast("Erro ao carregar itens", "error");
    }
  };

  const salvarContagem = async (itemId: number) => {
    if (invId == null) return;
    try {
      await api.contarInventario(invId, itemId, parseFloat(contados[itemId] || "0"));
      toast("Contagem salva", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const finalizar = async (id: number) => {
    try {
      const r = await api.finalizarInventario(id);
      toast(`Inventário finalizado (${r.ajustados} ajustes)`, "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Nome do inventário">
          <Input placeholder="Ex.: Contagem mensal" value={nome} onChange={(e) => setNome(e.target.value)} className="w-56" />
        </Field>
        <Field label="Depósito">
          <Select value={dep} onChange={(e) => setDep(e.target.value)} className="w-44">
            <option value="">Todos</option>
            {depositos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome}
              </option>
            ))}
          </Select>
        </Field>
        <Button variant="primary" onClick={() => void criar()}>
          + Novo inventário
        </Button>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhum inventário.
        </div>
      ) : (
        <Table>
          <THead cols={["Nome", "Data", "Depósito", "Status", ""]} />
          <TBody>
            {rows.map((i) => (
              <tr key={i.id} className="hover:bg-gray-50">
                <Cell className="font-medium">{i.nome}</Cell>
                <Cell className="text-xs text-gray-500">{fmtDate(i.data)}</Cell>
                <Cell>{i.deposito_nome || "Todos"}</Cell>
                <Cell>
                  <Badge tone={i.status === "finalizado" ? "green" : "gray"}>{i.status}</Badge>
                </Cell>
                <Cell>
                  {i.status === "aberto" ? (
                    <div className="flex justify-end gap-2">
                      <Button size="sm" onClick={() => void abrirContagem(i.id)}>
                        Contar
                      </Button>
                      <Button size="sm" variant="primary" onClick={() => void finalizar(i.id)}>
                        Finalizar
                      </Button>
                    </div>
                  ) : null}
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={`Contagem — Inventário #${invId ?? ""}`}
        wide
        footer={<Button onClick={() => setModalOpen(false)}>Fechar</Button>}
      >
        <Table>
          <THead cols={["Produto", "Localização", "Sistema", "Contado", ""]} />
          <TBody>
            {itens.slice(0, 100).map((i) => (
              <tr key={i.id} className="hover:bg-gray-50">
                <Cell>
                  <span className="font-medium">{i.produto_nome}</span>
                  {i.sku ? <div className="font-mono text-xs text-gray-400">{i.sku}</div> : null}
                </Cell>
                <Cell className="text-xs">{i.localizacao || "—"}</Cell>
                <Cell>{i.quantidade_sistema}</Cell>
                <Cell>
                  <Input
                    type="number"
                    step="any"
                    value={contados[i.id] ?? ""}
                    onChange={(e) => setContados({ ...contados, [i.id]: e.target.value })}
                    className="w-24"
                  />
                </Cell>
                <Cell>
                  <Button size="sm" onClick={() => void salvarContagem(i.id)}>
                    Salvar
                  </Button>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      </Modal>
    </div>
  );
}
