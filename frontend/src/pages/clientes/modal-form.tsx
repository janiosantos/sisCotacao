// pages/clientes/modal-form.tsx — formulário completo do cliente (abas dados/endereços/contatos/comercial/fiscal/interações).
import { useEffect, useState } from "react";
import {
  api,
  type Cliente,
  type ClienteApoioComercial,
  type ClienteApoioFiscal,
  type ClienteContato,
  type ClienteEndereco,
  type ClienteInteracao,
  type ClientePayload,
  type ContextoCliente,
  type Vendedor,
} from "../../api/client";
import { fmtDate, maskCep, maskDoc, maskFone, maskIe, soDigitos, validarCnpj, validarCpf } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal, Select, Textarea } from "../../ui/ui";

type Aba = "dados" | "enderecos" | "contatos" | "comercial" | "fiscal" | "interacoes";

interface Form {
  nome: string;
  tipo_pessoa: string;
  doc: string;
  contribuinte: string;
  ie: string;
  email: string;
  whatsapp: string;
  telefone: string;
  vendedor_id: string;
  limite_credito: string;
  observacoes: string;
  segmento: string;
  categoria: string;
}

const EMPTY_FORM: Form = {
  nome: "",
  tipo_pessoa: "f",
  doc: "",
  contribuinte: "",
  ie: "",
  email: "",
  whatsapp: "",
  telefone: "",
  vendedor_id: "",
  limite_credito: "",
  observacoes: "",
  segmento: "consumidor_final",
  categoria: "",
};

const TIPO_INTERACAO_LABEL: Record<string, string> = {
  ligacao: "Ligação",
  visita: "Visita",
  email: "E-mail",
  whatsapp: "WhatsApp",
  follow_up: "Follow-up",
  outro: "Outro",
};

export function ModalClienteForm({
  cliente,
  ctx,
  vendedores,
  onClose,
  onSaved,
}: {
  cliente: Cliente | null;
  ctx: ContextoCliente | null;
  vendedores: Vendedor[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [aba, setAba] = useState<Aba>("dados");
  const [form, setForm] = useState<Form>(EMPTY_FORM);
  const [enderecos, setEnderecos] = useState<ClienteEndereco[]>([]);
  const [contatos, setContatos] = useState<ClienteContato[]>([]);
  const [interacoes, setInteracoes] = useState<ClienteInteracao[]>([]);
  const [apoioComercial, setApoioComercial] = useState<ClienteApoioComercial | null>(null);
  const [apoioFiscal, setApoioFiscal] = useState<ClienteApoioFiscal | null>(null);
  const [novoEnd, setNovoEnd] = useState({ tipo: "Entrega", logradouro: "", numero: "", bairro: "", cidade: "", uf: "", cep: "" });
  const [novoCtt, setNovoCtt] = useState({ nome: "", cargo: "", telefone: "", email: "" });
  const [novaInteracao, setNovaInteracao] = useState({ tipo: "ligacao", descricao: "", data_contato: "", data_proximo_contato: "" });

  useEffect(() => {
    setAba("dados");
    setEnderecos([]);
    setContatos([]);
    setInteracoes([]);
    setApoioComercial(null);
    setApoioFiscal(null);
    setForm(
      cliente
        ? {
            nome: cliente.nome,
            tipo_pessoa: cliente.tipo_pessoa || "f",
            doc: cliente.doc || "",
            contribuinte: cliente.contribuinte || "",
            ie: cliente.ie || "",
            email: cliente.email || "",
            whatsapp: cliente.whatsapp || "",
            telefone: cliente.telefone || "",
            vendedor_id: cliente.vendedor_id ? String(cliente.vendedor_id) : "",
            limite_credito: cliente.limite_credito ? String(cliente.limite_credito) : "",
            observacoes: cliente.observacoes || "",
            segmento: cliente.segmento || "consumidor_final",
            categoria: cliente.categoria || "",
          }
        : EMPTY_FORM
    );
    if (cliente) {
      void (async () => {
        try {
          const [ends, ctts, com, fis, inter] = await Promise.all([
            api.listarEnderecosCliente(cliente.id),
            api.listarContatosCliente(cliente.id),
            api.getApoioComercial(cliente.id),
            api.getApoioFiscal(cliente.id),
            api.listarInteracoesCliente(cliente.id),
          ]);
          setEnderecos(ends);
          setContatos(ctts);
          setApoioComercial(com);
          setApoioFiscal(fis);
          setInteracoes(inter);
        } catch {
          /* dados secundários opcionais */
        }
      })();
    }
  }, [cliente]);

  const validarDoc = (): string | null => {
    const tipo = form.tipo_pessoa;
    const d = soDigitos(form.doc);
    if (!d) return null; // documento opcional
    if (tipo === "j") {
      if (d.length !== 14) return "CNPJ deve ter 14 dígitos";
      if (!validarCnpj(d)) return "CNPJ inválido (dígitos verificadores)";
    } else {
      if (d.length !== 11) return "CPF deve ter 11 dígitos";
      if (!validarCpf(d)) return "CPF inválido (dígitos verificadores)";
    }
    return null;
  };

  const salvarDados = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome do cliente", "error");
      return;
    }
    const errDoc = validarDoc();
    if (errDoc) {
      toast(errDoc, "error");
      return;
    }
    const payload: ClientePayload = {
      nome: form.nome.trim(),
      tipo_pessoa: form.tipo_pessoa,
      doc: soDigitos(form.doc) || null,
      email: form.email.trim() || null,
      whatsapp: soDigitos(form.whatsapp) || null,
      telefone: soDigitos(form.telefone) || null,
      vendedor_id: Number(form.vendedor_id) || null,
      limite_credito: Number(form.limite_credito) || 0,
      observacoes: form.observacoes.trim() || null,
      contribuinte: form.contribuinte || undefined,
      ie: form.ie.trim() || undefined,
      segmento: form.segmento || undefined,
      categoria: form.categoria || undefined,
    };
    try {
      if (cliente) await api.atualizarCliente(cliente.id, payload);
      else await api.criarCliente(payload);
      onClose();
      toast("Cliente salvo", "success");
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const addEndereco = async () => {
    if (!cliente) return;
    try {
      await api.criarEnderecoCliente(cliente.id, novoEnd);
      setNovoEnd({ tipo: "Entrega", logradouro: "", numero: "", bairro: "", cidade: "", uf: "", cep: "" });
      setEnderecos(await api.listarEnderecosCliente(cliente.id));
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
    if (!cliente) return;
    try {
      await api.criarContatoCliente(cliente.id, novoCtt);
      setNovoCtt({ nome: "", cargo: "", telefone: "", email: "" });
      setContatos(await api.listarContatosCliente(cliente.id));
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

  const addInteracao = async () => {
    if (!cliente) return;
    if (!novaInteracao.data_contato) {
      toast("Informe a data do contato", "error");
      return;
    }
    try {
      await api.criarInteracaoCliente(cliente.id, {
        tipo: novaInteracao.tipo,
        descricao: novaInteracao.descricao.trim(),
        data_contato: novaInteracao.data_contato,
        data_proximo_contato: novaInteracao.data_proximo_contato || null,
      });
      setNovaInteracao({ tipo: "ligacao", descricao: "", data_contato: "", data_proximo_contato: "" });
      setInteracoes(await api.listarInteracoesCliente(cliente.id));
      toast("Interação registrada", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const salvarApoio = async () => {
    if (!cliente) return;
    try {
      if (apoioComercial) await api.upsertApoioComercial(cliente.id, apoioComercial as unknown as Record<string, unknown>);
      if (apoioFiscal) await api.upsertApoioFiscal(cliente.id, apoioFiscal as unknown as Record<string, unknown>);
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
    { key: "interacoes", label: `Interações (${interacoes.length})` },
  ];

  return (
    <Modal
      open
      onClose={onClose}
      title={cliente ? "Editar cliente" : "Novo cliente"}
      wide
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
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
      <div className="mb-4 flex gap-2 overflow-x-auto border-b border-gray-200 pb-3">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setAba(t.key)}
            className={`whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ${
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
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Tipo de pessoa">
              <Select value={form.tipo_pessoa} onChange={(e) => setForm({ ...form, tipo_pessoa: e.target.value })}>
                <option value="f">Pessoa Física</option>
                <option value="j">Pessoa Jurídica</option>
              </Select>
            </Field>
            <Field label="CPF/CNPJ">
              <Input
                value={maskDoc(form.doc, form.tipo_pessoa === "j" ? "j" : "f")}
                onChange={(e) => setForm({ ...form, doc: e.target.value })}
                placeholder={form.tipo_pessoa === "j" ? "00.000.000/0000-00" : "000.000.000-00"}
              />
            </Field>
            <Field label="Condição de contribuinte">
              <Select value={form.contribuinte} onChange={(e) => setForm({ ...form, contribuinte: e.target.value })}>
                <option value="">Não definido</option>
                <option value="contribuinte">Contribuinte ICMS</option>
                <option value="nao_contribuinte">Não contribuinte</option>
              </Select>
            </Field>
            <Field label="Inscrição Estadual">
              <Input value={maskIe(form.ie)} onChange={(e) => setForm({ ...form, ie: e.target.value })} />
            </Field>
            <Field label="Segmento">
              <Select value={form.segmento} onChange={(e) => setForm({ ...form, segmento: e.target.value })}>
                {(ctx?.segmentos || []).map((s) => (
                  <option key={s.valor} value={s.valor}>
                    {s.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Categoria (perfil)">
              <Select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}>
                <option value="">—</option>
                {(ctx?.categorias || []).map((c) => (
                  <option key={c.valor} value={c.valor}>
                    {c.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="E-mail">
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Telefone">
              <Input value={maskFone(form.telefone)} onChange={(e) => setForm({ ...form, telefone: e.target.value })} />
            </Field>
            <Field label="WhatsApp">
              <Input value={maskFone(form.whatsapp)} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} />
            </Field>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
                    {e.cep ? ` - ${maskCep(e.cep)}` : ""}
                  </span>
                  <Button size="sm" variant="ghost" onClick={() => void removerEndereco(e.id)}>
                    ×
                  </Button>
                </div>
              ))
            )}
          </div>
          {cliente ? (
            <div className="rounded-md border border-dashed border-gray-300 p-3">
              <div className="mb-2 text-xs font-semibold text-gray-500">Novo endereço</div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Tipo">
                  <Select value={novoEnd.tipo} onChange={(e) => setNovoEnd({ ...novoEnd, tipo: e.target.value })}>
                    <option>Entrega</option>
                    <option>Cobrança</option>
                    <option>Faturamento</option>
                  </Select>
                </Field>
                <Field label="CEP">
                  <Input value={maskCep(novoEnd.cep)} onChange={(e) => setNovoEnd({ ...novoEnd, cep: e.target.value })} />
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
                  <Input
                    value={novoEnd.uf.toUpperCase().slice(0, 2)}
                    onChange={(e) => setNovoEnd({ ...novoEnd, uf: e.target.value.toUpperCase().slice(0, 2) })}
                  />
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
                    {c.telefone ? ` - ${maskFone(c.telefone)}` : ""}
                    {c.email ? ` - ${c.email}` : ""}
                  </span>
                  <Button size="sm" variant="ghost" onClick={() => void removerContato(c.id)}>
                    ×
                  </Button>
                </div>
              ))
            )}
          </div>
          {cliente ? (
            <div className="rounded-md border border-dashed border-gray-300 p-3">
              <div className="mb-2 text-xs font-semibold text-gray-500">Novo contato</div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Nome">
                  <Input value={novoCtt.nome} onChange={(e) => setNovoCtt({ ...novoCtt, nome: e.target.value })} />
                </Field>
                <Field label="Cargo">
                  <Input value={novoCtt.cargo} onChange={(e) => setNovoCtt({ ...novoCtt, cargo: e.target.value })} />
                </Field>
                <Field label="Telefone">
                  <Input value={maskFone(novoCtt.telefone)} onChange={(e) => setNovoCtt({ ...novoCtt, telefone: e.target.value })} />
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
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Condição de pagamento">
                <Select
                  value={apoioComercial.condicao_pagamento_id ?? ""}
                  onChange={(e) =>
                    setApoioComercial({ ...apoioComercial, condicao_pagamento_id: Number(e.target.value) || null })
                  }
                >
                  <option value="">—</option>
                  {(ctx?.condicoes_pagamento || []).map((cp) => (
                    <option key={cp.id} value={cp.id}>
                      {cp.nome}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Tabela de preço">
                <Select
                  value={apoioComercial.tabela_preco_id ?? ""}
                  onChange={(e) =>
                    setApoioComercial({ ...apoioComercial, tabela_preco_id: Number(e.target.value) || null })
                  }
                >
                  <option value="">—</option>
                  {(ctx?.tabelas_preco || []).map((tp) => (
                    <option key={tp.id} value={tp.id}>
                      {tp.nome}
                    </option>
                  ))}
                </Select>
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
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="CFOP padrão">
                <Select value={apoioFiscal.cfop_padrao || ""} onChange={(e) => setApoioFiscal({ ...apoioFiscal, cfop_padrao: e.target.value })}>
                  <option value="">—</option>
                  {(ctx?.cfop || []).map((c) => (
                    <option key={c.codigo} value={c.codigo}>
                      {c.codigo} - {c.descricao}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="CFOP de entrada (compras)">
                <Select value={apoioFiscal.cfop_entrada || ""} onChange={(e) => setApoioFiscal({ ...apoioFiscal, cfop_entrada: e.target.value })}>
                  <option value="">—</option>
                  {(ctx?.cfop || []).filter((c) => c.tipo === "entrada").map((c) => (
                    <option key={c.codigo} value={c.codigo}>
                      {c.codigo} - {c.descricao}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="CFOP de saída (vendas)">
                <Select value={apoioFiscal.cfop_saida || ""} onChange={(e) => setApoioFiscal({ ...apoioFiscal, cfop_saida: e.target.value })}>
                  <option value="">—</option>
                  {(ctx?.cfop || []).filter((c) => c.tipo === "saida").map((c) => (
                    <option key={c.codigo} value={c.codigo}>
                      {c.codigo} - {c.descricao}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="CST ICMS">
                <Select value={apoioFiscal.cst_icms || ""} onChange={(e) => setApoioFiscal({ ...apoioFiscal, cst_icms: e.target.value })}>
                  <option value="">—</option>
                  {(ctx?.cst_icms || []).map((c) => (
                    <option key={c.codigo} value={c.codigo}>
                      {c.codigo} - {c.descricao}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="CST CSOSN">
                <Select value={apoioFiscal.cst_csosn || ""} onChange={(e) => setApoioFiscal({ ...apoioFiscal, cst_csosn: e.target.value })}>
                  <option value="">—</option>
                  {(ctx?.csosn || []).map((c) => (
                    <option key={c.codigo} value={c.codigo}>
                      {c.codigo} - {c.descricao}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="CEST">
                <Select value={apoioFiscal.cest || ""} onChange={(e) => setApoioFiscal({ ...apoioFiscal, cest: e.target.value })}>
                  <option value="">—</option>
                  {(ctx?.cest || []).map((c) => (
                    <option key={c.codigo} value={c.codigo}>
                      {c.codigo} - {c.descricao}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="CST PIS">
                <Select value={apoioFiscal.cst_pis || ""} onChange={(e) => setApoioFiscal({ ...apoioFiscal, cst_pis: e.target.value })}>
                  <option value="">—</option>
                  {(ctx?.cst_pis || []).map((c) => (
                    <option key={c.codigo} value={c.codigo}>
                      {c.codigo} - {c.descricao}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="CST COFINS">
                <Select value={apoioFiscal.cst_cofins || ""} onChange={(e) => setApoioFiscal({ ...apoioFiscal, cst_cofins: e.target.value })}>
                  <option value="">—</option>
                  {(ctx?.cst_cofins || []).map((c) => (
                    <option key={c.codigo} value={c.codigo}>
                      {c.codigo} - {c.descricao}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Alíq. ICMS (%)">
                <Input
                  type="number"
                  step="0.01"
                  value={apoioFiscal.aliquota_icms ?? ""}
                  onChange={(e) => setApoioFiscal({ ...apoioFiscal, aliquota_icms: Number(e.target.value) || 0 })}
                />
              </Field>
              <Field label="Alíq. ICMS-ST (%)">
                <Input
                  type="number"
                  step="0.01"
                  value={apoioFiscal.aliquota_icms_st ?? ""}
                  onChange={(e) => setApoioFiscal({ ...apoioFiscal, aliquota_icms_st: Number(e.target.value) || 0 })}
                />
              </Field>
              <Field label="Alíq. PIS (%)">
                <Input
                  type="number"
                  step="0.01"
                  value={apoioFiscal.aliquota_pis ?? ""}
                  onChange={(e) => setApoioFiscal({ ...apoioFiscal, aliquota_pis: Number(e.target.value) || 0 })}
                />
              </Field>
              <Field label="Alíq. COFINS (%)">
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

      {aba === "interacoes" && (
        <div className="space-y-4">
          <div className="space-y-2">
            {interacoes.length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-400">Nenhuma interação registrada</div>
            ) : (
              interacoes.map((i) => (
                <div key={i.id} className="rounded-md border border-gray-200 px-3 py-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{TIPO_INTERACAO_LABEL[i.tipo] || i.tipo}</span>
                    <span className="text-xs text-gray-400">{fmtDate(i.data_contato)}</span>
                  </div>
                  {i.descricao ? <div className="mt-1 text-gray-600">{i.descricao}</div> : null}
                  {i.data_proximo_contato ? (
                    <div className="mt-1 text-xs text-amber-600">Próximo contato: {fmtDate(i.data_proximo_contato)}</div>
                  ) : null}
                </div>
              ))
            )}
          </div>
          {cliente ? (
            <div className="rounded-md border border-dashed border-gray-300 p-3">
              <div className="mb-2 text-xs font-semibold text-gray-500">Nova interação</div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Tipo">
                  <Select value={novaInteracao.tipo} onChange={(e) => setNovaInteracao({ ...novaInteracao, tipo: e.target.value })}>
                    {Object.entries(TIPO_INTERACAO_LABEL).map(([k, l]) => (
                      <option key={k} value={k}>
                        {l}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Data do contato">
                  <Input
                    type="date"
                    value={novaInteracao.data_contato}
                    onChange={(e) => setNovaInteracao({ ...novaInteracao, data_contato: e.target.value })}
                  />
                </Field>
                <Field label="Próximo contato">
                  <Input
                    type="date"
                    value={novaInteracao.data_proximo_contato}
                    onChange={(e) => setNovaInteracao({ ...novaInteracao, data_proximo_contato: e.target.value })}
                  />
                </Field>
                <Field label="Descrição">
                  <Textarea
                    value={novaInteracao.descricao}
                    onChange={(e) => setNovaInteracao({ ...novaInteracao, descricao: e.target.value })}
                  />
                </Field>
              </div>
              <div className="mt-3">
                <Button size="sm" variant="primary" onClick={() => void addInteracao()}>
                  + Registrar
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-xs text-gray-400">Salve o cliente para registrar interações.</div>
          )}
        </div>
      )}
    </Modal>
  );
}