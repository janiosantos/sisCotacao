// pages/diagnostico_variacoes.tsx — qualidade do catálogo (React + Tailwind).

import { useEffect, useState } from "react";
import { api } from "../api/client";

import { toast } from "../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, PageHeader, Select, Table, TBody, THead } from "../ui/ui";
import { ModalDetalheVariacao, type Detalhe } from "./diagnostico_variacoes/modal-detalhe";

interface Resumo {
  classificacao: string;
  produtos: number;
  variantes: number;
}
interface Row {
  produto_id: number;
  nome: string;
  marca: string;
  classificacao: string;
  n_variantes: number;
  n_eans: number;
  observacao: string;
}

export default function DiagnosticoVariacoes() {
  const [resumo, setResumo] = useState<Resumo[]>([]);
  const [rows, setRows] = useState<Row[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [tipo, setTipo] = useState("");
  const [q, setQ] = useState("");
  const [detalhe, setDetalhe] = useState<Detalhe | null>(null);

  const carregar = async () => {
    try {
      setRows(await api.listarDiagnosticoVariacoes({ classificacao: tipo || undefined, q: q.trim() || undefined, limit: 200 }));
    } catch {
      toast("Erro ao carregar diagnóstico", "error");
    }
  };

  useEffect(() => {
    void (async () => {
      try {
        setResumo(await api.resumoDiagnosticoVariacoes());
      } catch {
        /* segue vazio */
      }
      await carregar();
      setCarregando(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const abrirDetalhe = async (id: number) => {
    try {
      setDetalhe(await api.detalhesDiagnosticoVariacao(id));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const classTone = (c: string) => (c === "variacao_real" ? "green" : c === "oferta_duplicada" ? "amber" : "red");

  return (
    <div>
      <PageHeader title="Qualidade do Catálogo" subtitle="Revise variantes reais, ofertas duplicadas e cadastros incompletos." />

      {resumo.length > 0 ? (
        <div className="mb-4 flex flex-wrap gap-2">
          {resumo.map((r) => (
            <Badge key={r.classificacao} tone="gray">
              {r.classificacao}: <b>{r.produtos}</b> produtos / {r.variantes} variantes
            </Badge>
          ))}
        </div>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Buscar produto, marca, SKU ou EAN">
          <Input placeholder="Ex.: Cabo Flexível…" value={q} onChange={(e) => setQ(e.target.value)} className="w-72" />
        </Field>
        <Select value={tipo} onChange={(e) => setTipo(e.target.value)} className="w-48">
          <option value="">Todos</option>
          <option value="oferta_duplicada">Oferta duplicada</option>
          <option value="variacao_real">Variação real</option>
          <option value="cadastro_incompleto">Cadastro incompleto</option>
        </Select>
        <Button onClick={() => void carregar()}>Filtrar</Button>
      </div>

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["Produto", "Classificação", "Variantes", "EANs", "Observação", ""]} />
          <TBody>
            {rows.length === 0 ? (
              <EmptyRow colSpan={6} message="Nenhum caso" />
            ) : (
              rows.map((r) => (
                <tr key={r.produto_id} className="hover:bg-gray-50">
                  <Cell>
                    <span className="font-medium">{r.nome}</span>
                    {r.marca ? <div className="text-xs text-gray-400">{r.marca}</div> : null}
                  </Cell>
                  <Cell>
                    <Badge tone={classTone(r.classificacao)}>{r.classificacao}</Badge>
                  </Cell>
                  <Cell>{r.n_variantes}</Cell>
                  <Cell>{r.n_eans}</Cell>
                  <Cell className="text-xs">{r.observacao}</Cell>
                  <Cell>
                    <Button size="sm" variant="ghost" onClick={() => void abrirDetalhe(r.produto_id)}>
                      Detalhes
                    </Button>
                  </Cell>
                </tr>
              ))
            )}
          </TBody>
        </Table>
      )}

      <ModalDetalheVariacao
        detalhe={detalhe}
        onClose={() => setDetalhe(null)}
      />
    </div>
  );
}
