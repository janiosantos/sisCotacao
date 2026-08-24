// pages/fornecedores.tsx — cadastro de fornecedores (React + Tailwind).
// v2.19.0: CRUD completo com endereço, contatos, condições comerciais,
// categoria, avaliação e busca.

import { useEffect, useMemo, useState } from "react";
import {
  api,
  type ContextoFornecedor,
  type Fornecedor,
  type FornecedorContato,
  type FornecedorPayload,
} from "../api/client";
import { maskCep, maskDoc, maskFone, soDigitos } from "../ui/format";
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

type Aba = "dados" | "endereco" | "contatos" | "comercial";

interface Form {
  nome: string;
  razao_social: string;
  cnpj_cpf: string;
  representante: string;
  whatsapp: string;
  telefone: string;
  email: string;
  endereco: string;
  numero: string;
  bairro: string;
  cidade: string;
  uf: string;
  cep: string;
  categoria: string;
  condicao_pagamento_id: string;
  prazo_entrega_dias: string;
  nota: string;
  observacoes: string;
}

const EMPTY_FORM: Form = {
  nome: "",
  razao_social: "",
  cnpj_cpf: "",
  representante: "",
  whatsapp: "",
  telefone: "",
  email: "",
  endereco: "",
  numero: "",
  bairro: "",
  cidade: "",
  uf: "",
  cep: "",
  categoria: "geral",
  condicao_pagamento_id: "",
  prazo_entrega_dias: "30",
  nota: "5.0",
  observacoes: "",
};

export default function Fornecedores() {
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [ctx, setCtx] = useState<ContextoFornecedor | null>(null);
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Fornecedor | null>(null);
  const [aba, setAba] = useState<Aba>("dados");
  const [form, setForm] = useState<Form>(EMPTY_FORM);
  const [contatos, setContatos] = useState<FornecedorContato[]>([]);
  const [novoCtt, setNovoCtt] = useState({ nome: "", cargo: "", telefone: "", email: "" });

  const carregar = async () => {
    try {
      const [f, c] = await Promise.all([api.listarFornecedores(), api.contextoFornecedor()]);
      setFornecedores(f);
      setCtx(c);
    } catch (e) {
      toast("Erro ao carregar fornecedores: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = async (f?: Fornecedor) => {
    setEditando(f ?? null);
    setAba("dados");
    setContatos([]);
    setForm(
      f
        ? {
            nome: f.nome ?? "",
            razao_social: f.razao_social ?? "",
            cnpj_cpf: f.cnpj_cpf ?? "",
            representante: f.representante ?? "",
            whatsapp: f.whatsapp ?? "",
            telefone: f.telefone ?? "",
            email: f.email ?? "",
            endereco: f.endereco ?? "",
            numero: f.numero ?? "",
            bairro: f.bairro ?? "",
            cidade: f.cidade ?? "",
            uf: f.uf ?? "",
            cep: f.cep ?? "",
            categoria: f.categoria || "geral",
            condicao_pagamento_id: f.condicao_pagamento_id ? String(f.condicao_pagamento_id) : "",
            prazo_entrega_dias: f.prazo_entrega_dias != null ? String(f.prazo_entrega_dias) : "30",
            nota: f.nota != null ? String(f.nota) : "5.0",
            observacoes: f.observacoes ?? "",
          }
        : EMPTY_FORM
    );
    setModalOpen(true);
    if (f) {
      try {
        setContatos(await api.listarContatosFornecedor(f.id));
      } catch {
        /* opcional */
      }
    }
  };

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome do fornecedor", "error");
      return;
    }
    const payload: FornecedorPayload = {
      nome: form.nome.trim(),
      razao_social: form.razao_social.trim() || null,
      cnpj_cpf: soDigitos(form.cnpj_cpf) || null,
      representante: form.representante.trim() || null,
      whatsapp: soDigitos(form.whatsapp) || null,
      telefone: soDigitos(form.telefone) || null,
      email: form.email.trim() || null,
      endereco: form.endereco.trim() || null,
      numero: form.numero.trim() || null,
      bairro: form.bairro.trim() || null,
      cidade: form.cidade.trim() || null,
      uf: form.uf.trim().toUpperCase() || null,
      cep: soDigitos(form.cep) || null,
      categoria: form.categoria || "geral",
      condicao_pagamento_id: Number(form.condicao_pagamento_id) || null,
      prazo_entrega_dias: Number(form.prazo_entrega_dias) || 30,
      nota: Number(form.nota) || 5,
      observacoes: form.observacoes.trim() || null,
    };
    try {
      if (editando) await api.atualizarFornecedor(editando.id, payload);
      else await api.criarFornecedor(payload);
      setModalOpen(false);
      toast("Fornecedor salvo", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alternar = async (f: Fornecedor) => {
    try {
      await api.alternarAtivoFornecedor(f.id, !f.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const addContato = async () => {
    if (!editando) return;
    try {
      await api.criarContatoFornecedor(editando.id, novoCtt);
      setNovoCtt({ nome: "", cargo: "", telefone: "", email: "" });
      setContatos(await api.listarContatosFornecedor(editando.id));
      toast("Contato salvo", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const removerContato = async (id: number) => {
    try {
      await api.excluirContatoFornecedor(id);
      setContatos(contatos.filter((c) => c.id !== id));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const filtrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (!q) return fornecedores;
    return fornecedores.filter((f) =>
      [f.nome, f.razao_social, f.cnpj_cpf, f.cidade, f.categoria, f.representante]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [fornecedores, busca]);

  const TABS: { key: Aba; label: string }[] = [
    { key: "dados", label: "Dados" },
    { key: "endereco", label: "Endereço" },
    { key: "contatos", label: `Contatos (${contatos.length})` },
    { key: "comercial", label: "Comercial" },
  ];

  const catLabel = (v?: string) => ctx?.categorias.find((c) => c.valor === v)?.label || v || "—";

  return (
    <div>
      <PageHeader
        title="Fornecedores"
        subtitle="Cadastro completo: dados, endereço, contatos, condições comerciais e avaliação."
        actions={
          <Button variant="primary" onClick={() => abrir()}>
            + Novo fornecedor
          </Button>
        }
      />

      {carregando ? (
        <Loading message="Carregando fornecedores…" />
      ) : (
        <>
          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center">
            <Input
              placeholder="Buscar por nome, CNPJ, cidade, categoria…"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="max-w-sm"
            />
            <div className="text-xs text-gray-400">{filtrados.length} fornecedor(es)</div>
          </div>
          {filtrados.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
              Nenhum fornecedor encontrado.
            </div>
          ) : (
            <Table>
              <THead cols={["Nome", "CNPJ/CPF", "Cidade/UF", "Categoria", "Prazo (dias)", "Nota", "Status", ""]} />
              <TBody>
                {filtrados.map((f) => (
                  <tr key={f.id} className="hover:bg-gray-50">
                    <Cell>
                      <span className="font-medium">{f.nome}</span>
                      {f.representante ? <div className="text-xs text-gray-400">Rep.: {f.representante}</div> : null}
                    </Cell>
                    <Cell className="font-mono text-xs">
                      {f.cnpj_cpf ? maskDoc(f.cnpj_cpf, f.cnpj_cpf.length > 11 ? "j" : "f") : "—"}
                    </Cell>
                    <Cell className="text-xs">{[f.cidade, f.uf].filter(Boolean).join(" - ") || "—"}</Cell>
                    <Cell className="text-xs">{catLabel(f.categoria ?? undefined)}</Cell>
                    <Cell className="text-xs">{f.prazo_entrega_dias ?? "—"}</Cell>
                    <Cell className="text-xs">
                      {f.nota != null ? (
                        <span className="text-amber-600">{"★".repeat(Math.round(f.nota))}</span>
                      ) : (
                        "—"
                      )}
                    </Cell>
                    <Cell>
                      <Badge tone={f.ativo ? "green" : "red"}>{f.ativo ? "Ativo" : "Inativo"}</Badge>
                    </Cell>
                    <Cell>
                      <div className="flex justify-end gap-2">
                        <Button size="sm" onClick={() => abrir(f)}>
                          Editar
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => alternar(f)}>
                          {f.ativo ? "Desativar" : "Ativar"}
                        </Button>
                      </div>
                    </Cell>
                  </tr>
                ))}
              </TBody>
            </Table>
          )}
        </>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editando ? "Editar fornecedor" : "Novo fornecedor"}
        wide
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
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
              <Field label="Razão social">
                <Input value={form.razao_social} onChange={(e) => setForm({ ...form, razao_social: e.target.value })} />
              </Field>
              <Field label="CNPJ/CPF">
                <Input
                  value={maskDoc(form.cnpj_cpf, form.cnpj_cpf.length > 11 ? "j" : "f")}
                  onChange={(e) => setForm({ ...form, cnpj_cpf: e.target.value })}
                  placeholder="00.000.000/0000-00"
                />
              </Field>
              <Field label="Representante">
                <Input value={form.representante} onChange={(e) => setForm({ ...form, representante: e.target.value })} />
              </Field>
              <Field label="Telefone">
                <Input value={maskFone(form.telefone)} onChange={(e) => setForm({ ...form, telefone: e.target.value })} />
              </Field>
              <Field label="WhatsApp">
                <Input value={maskFone(form.whatsapp)} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} />
              </Field>
              <Field label="E-mail">
                <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </Field>
            </div>
            <Field label="Observações">
              <Textarea value={form.observacoes} onChange={(e) => setForm({ ...form, observacoes: e.target.value })} />
            </Field>
          </div>
        )}

        {aba === "endereco" && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Logradouro">
              <Input value={form.endereco} onChange={(e) => setForm({ ...form, endereco: e.target.value })} />
            </Field>
            <Field label="Número">
              <Input value={form.numero} onChange={(e) => setForm({ ...form, numero: e.target.value })} />
            </Field>
            <Field label="Bairro">
              <Input value={form.bairro} onChange={(e) => setForm({ ...form, bairro: e.target.value })} />
            </Field>
            <Field label="Cidade">
              <Input value={form.cidade} onChange={(e) => setForm({ ...form, cidade: e.target.value })} />
            </Field>
            <Field label="UF">
              <Input
                value={form.uf.toUpperCase().slice(0, 2)}
                onChange={(e) => setForm({ ...form, uf: e.target.value.toUpperCase().slice(0, 2) })}
              />
            </Field>
            <Field label="CEP">
              <Input value={maskCep(form.cep)} onChange={(e) => setForm({ ...form, cep: e.target.value })} />
            </Field>
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
            {editando ? (
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
              <div className="text-xs text-gray-400">Salve o fornecedor para adicionar contatos.</div>
            )}
          </div>
        )}

        {aba === "comercial" && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Categoria">
              <Select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}>
                {(ctx?.categorias || []).map((c) => (
                  <option key={c.valor} value={c.valor}>
                    {c.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Condição de pagamento padrão">
              <Select
                value={form.condicao_pagamento_id}
                onChange={(e) => setForm({ ...form, condicao_pagamento_id: e.target.value })}
              >
                <option value="">—</option>
                {(ctx?.condicoes_pagamento || []).map((cp) => (
                  <option key={cp.id} value={cp.id}>
                    {cp.nome}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Prazo médio de entrega (dias)">
              <Input
                type="number"
                min={0}
                value={form.prazo_entrega_dias}
                onChange={(e) => setForm({ ...form, prazo_entrega_dias: e.target.value })}
              />
            </Field>
            <Field label="Avaliação (1–5)">
              <Input
                type="number"
                min={1}
                max={5}
                step="0.5"
                value={form.nota}
                onChange={(e) => setForm({ ...form, nota: e.target.value })}
              />
            </Field>
          </div>
        )}
      </Modal>
    </div>
  );
}