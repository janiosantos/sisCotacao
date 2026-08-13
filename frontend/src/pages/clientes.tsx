// pages/clientes.tsx — cadastro de clientes (React + Tailwind).

import { useEffect, useState } from "react";
import {
  api,
  type Cliente,
  type ClienteApoioComercial,
  type ClienteApoioFiscal,
  type ClienteContato,
  type ClienteEndereco,
  type ClientePayload,
  type Vendedor,
} from "../api/client";
import { fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import {
  Badge,
  Button,
  Cell,
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

type Aba = "dados" | "enderecos" | "contatos" | "comercial" | "fiscal";

interface Form {
  nome: string;
  tipo_pessoa: string;
  doc: string;
  contribuinte: string;
  ie: string;
  email: string;
  whatsapp: string;
  vendedor_id: string;
  limite_credito: string;
  observacoes: string;
}

const EMPTY_FORM: Form = {
  nome: "",
  tipo_pessoa: "f",
  doc: "",
  contribuinte: "",
  ie: "",
  email: "",
  whatsapp: "",
  vendedor_id: "",
  limite_credito: "",
  observacoes: "",
};

export default function Clientes() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [vendedores, setVendedores] = useState<Vendedor[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Cliente | null>(null);
  const [aba, setAba] = useState<Aba>("dados");
  const [form, setForm] = useState<Form>(EMPTY_FORM);
  const [enderecos, setEnderecos] = useState<ClienteEndereco[]>([]);
  const [contatos, setContatos] = useState<ClienteContato[]>([]);
  const [apoioComercial, setApoioComercial] = useState<ClienteApoioComercial | null>(null);
  const [apoioFiscal, setApoioFiscal] = useState<ClienteApoioFiscal | null>(null);
  const [novoEnd, setNovoEnd] = useState({ tipo: "Entrega", logradouro: "", numero: "", bairro: "", cidade: "", uf: "", cep: "" });
  const [novoCtt, setNovoCtt] = useState({ nome: "", cargo: "", telefone: "", email: "" });

  const carregar = async () => {
    try {
      const [c, ctx] = await Promise.all([api.listarClientes(), api.contextoCliente()]);
      setClientes(c);
      setVendedores(ctx.vendedores);
    } catch (e) {
      toast("Erro ao carregar clientes: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = async (c: Cliente | null) => {
    setEditando(c);
    setAba("dados");
    setEnderecos([]);
    setContatos([]);
    setApoioComercial(null);
    setApoioFiscal(null);
    setForm(
      c
        ? {
            nome: c.nome,
            tipo_pessoa: c.tipo_pessoa || "f",
            doc: c.doc || "",
            contribuinte: c.contribuinte || "",
            ie: c.ie || "",
            email: c.email || "",
            whatsapp: c.whatsapp || "",
            vendedor_id: c.vendedor_id ? String(c.vendedor_id) : "",
            limite_credito: c.limite_credito ? String(c.limite_credito) : "",
            observacoes: c.observacoes || "",
          }
        : EMPTY_FORM
    );
    setModalOpen(true);
    if (c) {
      try {
        const [ends, ctts, com, fis] = await Promise.all([
          api.listarEnderecosCliente(c.id),
          api.listarContatosCliente(c.id),
          api.getApoioComercial(c.id),
          api.getApoioFiscal(c.id),
        ]);
        setEnderecos(ends);
        setContatos(ctts);
        setApoioComercial(com);
        setApoioFiscal(fis);
      } catch {
        /* dados secundários opcionais */
      }
    }
  };

  const salvarDados = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome do cliente", "error");
      return;
    }
    const payload: ClientePayload = {
      nome: form.nome.trim(),
      tipo_pessoa: form.tipo_pessoa,
      doc: form.doc.trim() || null,
      email: form.email.trim() || null,
      whatsapp: form.whatsapp.trim() || null,
      vendedor_id: Number(form.vendedor_id) || null,
      limite_credito: Number(form.limite_credito) || 0,
      observacoes: form.observacoes.trim() || null,
      contribuinte: form.contribuinte || undefined,
      ie: form.ie.trim() || undefined,
    };
    try {
      if (editando) await api.atualizarCliente(editando.id, payload);
      else await api.criarCliente(payload);
      setModalOpen(false);
      toast("Cliente salvo", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alternar = async (c: Cliente) => {
    try {
      await api.alternarAtivoCliente(c.id, !c.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const addEndereco = async () => {
    if (!editando) return;
    try {
      await api.criarEnderecoCliente(editando.id, novoEnd);
      setNovoEnd({ tipo: "Entrega", logradouro: "", numero: "", bairro: "", cidade: "", uf: "", cep: "" });
      setEnderecos(await api.listarEnderecosCliente(editando.id));
      toast("Endereço salvo", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const removerEndereco = async (id: number) => {
    try {
      await api.excluirEnderecoCliente(id);
      setEnderecos(enderecos.filter((e) => e.id !== id));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const addContato = async () => {
    if (!editando) return;
    try {
      await api.criarContatoCliente(editando.id, novoCtt);
      setNovoCtt({ nome: "", cargo: "", telefone: "", email: "" });
      setContatos(await api.listarContatosCliente(editando.id));
      toast("Contato salvo", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const removerContato = async (id: number) => {
    try {
      await api.excluirContatoCliente(id);
      setContatos(contatos.filter((c) => c.id !== id));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const salvarApoio = async () => {
    if (!editando) return;
    try {
      if (apoioComercial) await api.upsertApoioComercial(editando.id, apoioComercial as unknown as Record<string, unknown>);
      if (apoioFiscal) await api.upsertApoioFiscal(editando.id, apoioFiscal as unknown as Record<string, unknown>);
      toast("Apoio salvo", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const TABS: { key: Aba; label: string }[] = [
    { key: "dados", label: "Dados" },
    { key: "enderecos", label: `Endereços (${enderecos.length})` },
    { key: "contatos", label: `Contatos (${contatos.length})` },
    { key: "comercial", label: "Apoio Comercial" },
    { key: "fiscal", label: "Apoio Fiscal" },
  ];

  return (
    <div>
      <PageHeader
        title="Clientes"
        subtitle="Cadastro completo: dados, endereços, contatos, apoio comercial e fiscal."
        actions={
          <Button variant="primary" onClick={() => void abrir(null)}>
            + Novo cliente
          </Button>
        }
      />

      {carregando ? (
        <Loading message="Carregando clientes…" />
      ) : clientes.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhum cliente cadastrado.
        </div>
      ) : (
        <Table>
          <THead cols={["Nome", "Documento", "E-mail", "Vendedor", "Limite", "Status", ""]} />
          <TBody>
            {clientes.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <Cell>
                  <span className="font-medium">{c.nome}</span>
                </Cell>
                <Cell className="font-mono text-xs">{c.doc || "—"}</Cell>
                <Cell className="text-xs">{c.email || "—"}</Cell>
                <Cell className="text-xs">{c.vendedor_nome || "—"}</Cell>
                <Cell>{c.limite_credito ? fmtMoney(c.limite_credito) : "—"}</Cell>
                <Cell>
                  <Badge tone={c.ativo ? "green" : "red"}>{c.ativo ? "Ativo" : "Inativo"}</Badge>
                </Cell>
                <Cell>
                  <div className="flex justify-end gap-2">
                    <Button size="sm" onClick={() => void abrir(c)}>
                      Editar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => alternar(c)}>
                      {c.ativo ? "Desativar" : "Ativar"}
                    </Button>
                  </div>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editando ? "Editar cliente" : "Novo cliente"}
        wide
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            {aba === "dados" ? (
              <Button variant="primary" onClick={() => void salvarDados()}>
                Salvar
              </Button>
            ) : aba === "comercial" || aba === "fiscal" ? (
              <Button variant="primary" onClick={() => void salvarApoio()}>
                Salvar apoio
              </Button>
            ) : null}
          </>
        }
      >
        <div className="mb-4 flex flex-wrap gap-2 border-b border-gray-200 pb-3">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setAba(t.key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                aba === t.key ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {aba === "dados" && (
          <div className="space-y-4">
            <Field label="Nome *">
              <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Tipo de pessoa">
                <Select value={form.tipo_pessoa} onChange={(e) => setForm({ ...form, tipo_pessoa: e.target.value })}>
                  <option value="f">Pessoa Física</option>
                  <option value="j">Pessoa Jurídica</option>
                </Select>
              </Field>
              <Field label="CPF/CNPJ">
                <Input value={form.doc} onChange={(e) => setForm({ ...form, doc: e.target.value })} />
              </Field>
              <Field label="Condição de contribuinte">
                <Select value={form.contribuinte} onChange={(e) => setForm({ ...form, contribuinte: e.target.value })}>
                  <option value="">Não definido</option>
                  <option value="contribuinte">Contribuinte ICMS</option>
                  <option value="nao_contribuinte">Não contribuinte</option>
                </Select>
              </Field>
              <Field label="Inscrição Estadual">
                <Input value={form.ie} onChange={(e) => setForm({ ...form, ie: e.target.value })} />
              </Field>
              <Field label="E-mail">
                <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </Field>
              <Field label="WhatsApp">
                <Input value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Vendedor">
                <Select value={form.vendedor_id} onChange={(e) => setForm({ ...form, vendedor_id: e.target.value })}>
                  <option value="">—</option>
                  {vendedores.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.nome}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Limite de crédito (R$)">
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.limite_credito}
                  onChange={(e) => setForm({ ...form, limite_credito: e.target.value })}
                />
              </Field>
            </div>
            <Field label="Observações">
              <Textarea value={form.observacoes} onChange={(e) => setForm({ ...form, observacoes: e.target.value })} />
            </Field>
          </div>
        )}

        {aba === "enderecos" && (
          <div className="space-y-4">
            <div className="space-y-2">
              {enderecos.length === 0 ? (
                <div className="py-6 text-center text-sm text-gray-400">Nenhum endereço cadastrado</div>
              ) : (
                enderecos.map((e) => (
                  <div key={e.id} className="flex items-center justify-between rounded-md border border-gray-200 px-3 py-2 text-sm">
                    <span>
                      <span className="font-medium">{e.tipo}</span>: {e.logradouro}, {e.numero}
                      {e.bairro ? ` - ${e.bairro}` : ""}
                      {e.cidade ? ` - ${e.cidade}` : ""}
                    </span>
                    <Button size="sm" variant="ghost" onClick={() => void removerEndereco(e.id)}>
                      ×
                    </Button>
                  </div>
                ))
              )}
            </div>
            {editando ? (
              <div className="rounded-md border border-dashed border-gray-300 p-3">
                <div className="mb-2 text-xs font-semibold text-gray-500">Novo endereço</div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Tipo">
                    <Select value={novoEnd.tipo} onChange={(e) => setNovoEnd({ ...novoEnd, tipo: e.target.value })}>
                      <option>Entrega</option>
                      <option>Cobrança</option>
                      <option>Outro</option>
                    </Select>
                  </Field>
                  <Field label="CEP">
                    <Input value={novoEnd.cep} onChange={(e) => setNovoEnd({ ...novoEnd, cep: e.target.value })} />
                  </Field>
                  <Field label="Logradouro">
                    <Input value={novoEnd.logradouro} onChange={(e) => setNovoEnd({ ...novoEnd, logradouro: e.target.value })} />
                  </Field>
                  <Field label="Número">
                    <Input value={novoEnd.numero} onChange={(e) => setNovoEnd({ ...novoEnd, numero: e.target.value })} />
                  </Field>
                  <Field label="Bairro">
                    <Input value={novoEnd.bairro} onChange={(e) => setNovoEnd({ ...novoEnd, bairro: e.target.value })} />
                  </Field>
                  <Field label="Cidade">
                    <Input value={novoEnd.cidade} onChange={(e) => setNovoEnd({ ...novoEnd, cidade: e.target.value })} />
                  </Field>
                  <Field label="UF">
                    <Input value={novoEnd.uf} onChange={(e) => setNovoEnd({ ...novoEnd, uf: e.target.value })} />
                  </Field>
                </div>
                <div className="mt-3">
                  <Button size="sm" variant="primary" onClick={() => void addEndereco()}>
                    + Adicionar
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-400">Salve o cliente para adicionar endereços.</div>
            )}
          </div>
        )}

        {aba === "contatos" && (
          <div className="space-y-4">
            <div className="space-y-2">
              {contatos.length === 0 ? (
                <div className="py-6 text-center text-sm text-gray-400">Nenhum contato cadastrado</div>
              ) : (
                contatos.map((c) => (
                  <div key={c.id} className="flex items-center justify-between rounded-md border border-gray-200 px-3 py-2 text-sm">
                    <span>
                      <span className="font-medium">{c.nome}</span>
                      {c.cargo ? ` (${c.cargo})` : ""}
                      {c.telefone ? ` - ${c.telefone}` : ""}
                    </span>
                    <Button size="sm" variant="ghost" onClick={() => void removerContato(c.id)}>
                      ×
                    </Button>
                  </div>
                ))
              )}
            </div>
            {editando ? (
              <div className="rounded-md border border-dashed border-gray-300 p-3">
                <div className="mb-2 text-xs font-semibold text-gray-500">Novo contato</div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Nome">
                    <Input value={novoCtt.nome} onChange={(e) => setNovoCtt({ ...novoCtt, nome: e.target.value })} />
                  </Field>
                  <Field label="Cargo">
                    <Input value={novoCtt.cargo} onChange={(e) => setNovoCtt({ ...novoCtt, cargo: e.target.value })} />
                  </Field>
                  <Field label="Telefone">
                    <Input value={novoCtt.telefone} onChange={(e) => setNovoCtt({ ...novoCtt, telefone: e.target.value })} />
                  </Field>
                  <Field label="E-mail">
                    <Input value={novoCtt.email} onChange={(e) => setNovoCtt({ ...novoCtt, email: e.target.value })} />
                  </Field>
                </div>
                <div className="mt-3">
                  <Button size="sm" variant="primary" onClick={() => void addContato()}>
                    + Adicionar
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-400">Salve o cliente para adicionar contatos.</div>
            )}
          </div>
        )}

        {aba === "comercial" && (
          <div className="space-y-4">
            {apoioComercial ? (
              <div className="grid grid-cols-2 gap-3">
                <Field label="Condição de pagamento (ID)">
                  <Input
                    type="number"
                    value={apoioComercial.condicao_pagamento_id ?? ""}
                    onChange={(e) =>
                      setApoioComercial({ ...apoioComercial, condicao_pagamento_id: Number(e.target.value) || null })
                    }
                  />
                </Field>
                <Field label="Tabela de preço (ID)">
                  <Input
                    type="number"
                    value={apoioComercial.tabela_preco_id ?? ""}
                    onChange={(e) =>
                      setApoioComercial({ ...apoioComercial, tabela_preco_id: Number(e.target.value) || null })
                    }
                  />
                </Field>
                <Field label="Limite de crédito">
                  <Input
                    type="number"
                    value={apoioComercial.limite_credito ?? ""}
                    onChange={(e) => setApoioComercial({ ...apoioComercial, limite_credito: Number(e.target.value) || 0 })}
                  />
                </Field>
                <Field label="Transportadora">
                  <Input
                    value={apoioComercial.transportadora || ""}
                    onChange={(e) => setApoioComercial({ ...apoioComercial, transportadora: e.target.value })}
                  />
                </Field>
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-gray-400">Salve o cliente para editar o apoio comercial.</div>
            )}
          </div>
        )}

        {aba === "fiscal" && (
          <div className="space-y-4">
            {apoioFiscal ? (
              <div className="grid grid-cols-2 gap-3">
                <Field label="CFOP padrão">
                  <Input
                    value={apoioFiscal.cfop_padrao || ""}
                    onChange={(e) => setApoioFiscal({ ...apoioFiscal, cfop_padrao: e.target.value })}
                  />
                </Field>
                <Field label="CST ICMS">
                  <Input
                    value={apoioFiscal.cst_icms || ""}
                    onChange={(e) => setApoioFiscal({ ...apoioFiscal, cst_icms: e.target.value })}
                  />
                </Field>
                <Field label="CST PIS">
                  <Input
                    value={apoioFiscal.cst_pis || ""}
                    onChange={(e) => setApoioFiscal({ ...apoioFiscal, cst_pis: e.target.value })}
                  />
                </Field>
                <Field label="CST COFINS">
                  <Input
                    value={apoioFiscal.cst_cofins || ""}
                    onChange={(e) => setApoioFiscal({ ...apoioFiscal, cst_cofins: e.target.value })}
                  />
                </Field>
                <Field label="Alíq. ICMS">
                  <Input
                    type="number"
                    step="0.01"
                    value={apoioFiscal.aliquota_icms ?? ""}
                    onChange={(e) => setApoioFiscal({ ...apoioFiscal, aliquota_icms: Number(e.target.value) || 0 })}
                  />
                </Field>
                <Field label="Alíq. PIS">
                  <Input
                    type="number"
                    step="0.01"
                    value={apoioFiscal.aliquota_pis ?? ""}
                    onChange={(e) => setApoioFiscal({ ...apoioFiscal, aliquota_pis: Number(e.target.value) || 0 })}
                  />
                </Field>
                <Field label="Alíq. COFINS">
                  <Input
                    type="number"
                    step="0.01"
                    value={apoioFiscal.aliquota_cofins ?? ""}
                    onChange={(e) => setApoioFiscal({ ...apoioFiscal, aliquota_cofins: Number(e.target.value) || 0 })}
                  />
                </Field>
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-gray-400">Salve o cliente para editar o apoio fiscal.</div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
