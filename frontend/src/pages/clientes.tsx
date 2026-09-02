// pages/clientes.tsx — cadastro de clientes (React + Tailwind).
// v2.19.0: combos reais de apoio comercial/fiscal, histórico de interações,
// segmentação, máscaras/validação de CPF-CNPJ/fone/CEP e grid rico.

import { useEffect, useMemo, useState } from "react";
import {
  api,
  type Cliente,
  type ContextoCliente,
  type Vendedor,
} from "../api/client";
import { fmtMoney, maskDoc, normalizarTipoPessoa } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Input, Loading, PageHeader, Table, TBody, THead } from "../ui/ui";
import { ModalClienteForm } from "./clientes/modal-form";
import { ModalCredito } from "./clientes/modal-credito";

export default function Clientes() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [vendedores, setVendedores] = useState<Vendedor[]>([]);
  const [ctx, setCtx] = useState<ContextoCliente | null>(null);
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Cliente | null>(null);
  const [creditoDe, setCreditoDe] = useState<Cliente | null>(null);

  const carregar = async () => {
    try {
      const [c, contexto] = await Promise.all([api.listarClientes(), api.contextoCliente()]);
      setClientes(c);
      setVendedores(contexto.vendedores);
      setCtx(contexto);
    } catch (e) {
      toast("Erro ao carregar clientes: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = (c: Cliente | null) => {
    setEditando(c);
    setModalOpen(true);
  };

  const alternar = async (c: Cliente) => {
    try {
      await api.alternarAtivoCliente(c.id, !c.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const filtrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (!q) return clientes;
    return clientes.filter((c) =>
      [c.nome, c.doc, c.email, c.telefone, c.whatsapp, c.cidade, c.uf, c.vendedor_nome, c.segmento, c.categoria]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [clientes, busca]);

  const segLabel = (v?: string) => ctx?.segmentos.find((s) => s.valor === v)?.label || v || "—";

  return (
    <div>
      <PageHeader
        title="Clientes"
        contexto="Comercial · Cadastros"
        subtitle="Cadastro completo: dados, endereços, contatos, apoio comercial/fiscal e histórico de interações."
        actions={
          <Button variant="primary" onClick={() => void abrir(null)}>
            + Novo cliente
          </Button>
        }
      />

      {carregando ? (
        <Loading message="Carregando clientes…" />
      ) : (
        <>
          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center">
            <Input
              placeholder="Buscar por nome, CPF/CNPJ, cidade, vendedor…"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="max-w-sm"
            />
            <div className="text-xs text-gray-400">{filtrados.length} cliente(s)</div>
          </div>
          {filtrados.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
              Nenhum cliente encontrado.
            </div>
          ) : (
            <Table>
              <THead cols={["Nome", "Documento", "Cidade/UF", "Vendedor", "Segmento", "Limite", "Status", ""]} />
              <TBody>
                {filtrados.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <Cell>
                      <span className="font-medium">{c.nome}</span>
                      {c.email ? <div className="text-xs text-gray-400">{c.email}</div> : null}
                    </Cell>
                    <Cell className="font-mono text-xs">{c.doc ? maskDoc(c.doc, normalizarTipoPessoa(c.tipo_pessoa)) : "—"}</Cell>
                    <Cell className="text-xs">{[c.cidade, c.uf].filter(Boolean).join(" - ") || "—"}</Cell>
                    <Cell className="text-xs">{c.vendedor_nome || "—"}</Cell>
                    <Cell className="text-xs">{segLabel(c.segmento)}</Cell>
                    <Cell>{c.limite_credito ? fmtMoney(c.limite_credito) : "—"}</Cell>
                    <Cell>
                      <Badge tone={c.ativo ? "green" : "red"}>{c.ativo ? "Ativo" : "Inativo"}</Badge>
                    </Cell>
                    <Cell>
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="outline" onClick={() => setCreditoDe(c)}>
                          Crediário
                        </Button>
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
        </>
      )}

      {modalOpen && (
        <ModalClienteForm
          cliente={editando}
          ctx={ctx}
          vendedores={vendedores}
          onClose={() => setModalOpen(false)}
          onSaved={carregar}
        />
      )}
      {creditoDe && <ModalCredito cliente={creditoDe} onClose={() => setCreditoDe(null)} onSaved={carregar} />}
    </div>
  );
}
