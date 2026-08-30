// pages/fornecedores.tsx — cadastro de fornecedores (React + Tailwind).
// v2.19.0: CRUD completo com endereço, contatos, condições comerciais,
// categoria, avaliação e busca.

import { useEffect, useMemo, useState } from "react";
import {
  api,
  type ContextoFornecedor,
  type Fornecedor,
} from "../api/client";
import { maskDoc } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Input, Loading, PageHeader, Table, TBody, THead } from "../ui/ui";
import { ModalFornecedorForm } from "./fornecedores/modal-form";

export default function Fornecedores() {
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [ctx, setCtx] = useState<ContextoFornecedor | null>(null);
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Fornecedor | null>(null);

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

  const abrir = (f?: Fornecedor) => {
    setEditando(f ?? null);
    setModalOpen(true);
  };

  const alternar = async (f: Fornecedor) => {
    try {
      await api.alternarAtivoFornecedor(f.id, !f.ativo);
      await carregar();
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

      {modalOpen && (
        <ModalFornecedorForm
          fornecedor={editando}
          ctx={ctx}
          onClose={() => setModalOpen(false)}
          onSaved={carregar}
        />
      )}
    </div>
  );
}