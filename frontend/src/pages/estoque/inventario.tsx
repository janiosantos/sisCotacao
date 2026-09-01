// pages/estoque/inventario.tsx - módulo Estoque (Inventario).

import { useEffect, useState } from "react";
import { api, type Deposito } from "../../api/client";
import { fmtDate } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, Field, Input, Modal, Select, Table, TBody, THead } from "../../ui/ui";
import { InventarioCiclo as InventarioCicloView } from "./inventario-ciclo";

interface InventarioRow {
  id: number;
  nome: string;
  data: string;
  status: string;
  deposito_nome: string | null;
}
interface InventarioItem {
  id: number;
  produto_id: number;
  produto_nome: string;
  sku: string;
  localizacao: string;
  quantidade_sistema: number;
  quantidade_contada: number | null;
}

export function Inventario({ depositos }: { depositos: Deposito[] }) {
  const [modo, setModo] = useState<"simples" | "ciclos">("simples");
  if (modo === "ciclos") {
    return (
      <div>
        <div className="mb-3 flex items-center justify-end">
          <Button size="sm" variant="ghost" onClick={() => setModo("simples")}>← Inventário simples</Button>
        </div>
        <InventarioCicloView depositos={depositos} />
      </div>
    );
  }
  return <InventarioSimples depositos={depositos} onCiclos={() => setModo("ciclos")} />;
}

function InventarioSimples({ depositos, onCiclos }: { depositos: Deposito[]; onCiclos: () => void }) {
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
        <Button variant="secondary" onClick={onCiclos}>
          Ciclos de contagem
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

