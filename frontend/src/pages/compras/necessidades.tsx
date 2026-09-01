// pages/compras/necessidades.tsx — Sugestões de compra (COM-006): motor de reposição + ABC/XYZ + fornecedor.
import { useEffect, useMemo, useState } from "react";
import { api, type ReposicaoResultado, type SugestaoReposicao } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Cell, EmptyRow, Field, Input, Loading, Select, Table, TBody, THead } from "../../ui/ui";

export function Necessidades({ depositos }: { depositos: { id: number; nome: string }[] }) {
  const [resultado, setResultado] = useState<ReposicaoResultado | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [dep, setDep] = useState(depositos[0] ? String(depositos[0].id) : "");
  const [fAbc, setFAbc] = useState("");
  const [fXyz, setFXyz] = useState("");
  const [fFornec, setFFornec] = useState("");
  const [fRuptura, setFRuptura] = useState("");
  const [sel, setSel] = useState<Record<number, boolean>>({});
  const [ajuste, setAjuste] = useState<Record<number, number>>({});
  const [just, setJust] = useState<Record<number, string>>({});
  const [expanded, setExpanded] = useState<number | null>(null);
  const [gerando, setGerando] = useState(false);

  const carregar = async () => {
    setCarregando(true);
    try {
      setResultado(await api.calcularReposicao(undefined, dep ? Number(dep) : undefined));
    } catch (e) {
      toast("Erro ao calcular: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);

  const linhas = useMemo(() => {
    const base = resultado?.sugestoes ?? [];
    return base.filter((s) => {
      if (fAbc && s.classe_abc !== fAbc) return false;
      if (fXyz && s.classe_xyz !== fXyz) return false;
      if (fFornec && s.fornecedor_nome !== fFornec) return false;
      if (fRuptura === "sim" && !s.ruptura_provavel) return false;
      if (fRuptura === "nao" && s.ruptura_provavel) return false;
      return true;
    });
  }, [resultado, fAbc, fXyz, fFornec, fRuptura]);

  const fornecedores = useMemo(() => [...new Set((resultado?.sugestoes ?? []).map((s) => s.fornecedor_nome).filter(Boolean))] as string[], [resultado]);

  const selecionarNecessidade = () => {
    const next: Record<number, boolean> = {};
    for (const s of linhas) if (s.sugestao > 0) next[s.produto_id] = true;
    setSel(next);
  };

  const qtdFinal = (s: SugestaoReposicao) => (ajuste[s.produto_id] != null && ajuste[s.produto_id] >= 0 ? ajuste[s.produto_id] : s.sugestao);

  const gerarSolicitacao = async () => {
    const escolhidos = linhas.filter((s) => sel[s.produto_id] && qtdFinal(s) > 0);
    if (escolhidos.length === 0) {
      toast("Selecione ao menos um item com quantidade", "error");
      return;
    }
    setGerando(true);
    try {
      const codigo = `SOL-${Date.now().toString().slice(-6)}`;
      const sol = await api.criarSolicitacaoCompra({ codigo, descricao: `Sugestões de reposição (${fmtDate(new Date().toISOString())})` });
      for (const s of escolhidos) {
        await api.addItemSolicitacao(sol.id, {
          produto_id: s.produto_id,
          quantidade: qtdFinal(s),
          justificativa: just[s.produto_id] || s.justificativa,
        });
      }
      toast(`Solicitação ${codigo} gerada (${escolhidos.length} itens)`, "success");
      setSel({});
    } catch (e) {
      toast("Erro ao gerar solicitação: " + (e as Error).message, "error");
    } finally {
      setGerando(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Depósito">
          <Select value={dep} onChange={(e) => setDep(e.target.value)} className="w-44">
            {depositos.map((d) => (
              <option key={d.id} value={d.id}>{d.nome}</option>
            ))}
          </Select>
        </Field>
        <Field label="ABC">
          <Select value={fAbc} onChange={(e) => setFAbc(e.target.value)} className="w-28">
            <option value="">Todas</option><option>A</option><option>B</option><option>C</option>
          </Select>
        </Field>
        <Field label="XYZ">
          <Select value={fXyz} onChange={(e) => setFXyz(e.target.value)} className="w-28">
            <option value="">Todos</option><option>X</option><option>Y</option><option>Z</option>
          </Select>
        </Field>
        <Field label="Fornecedor">
          <Select value={fFornec} onChange={(e) => setFFornec(e.target.value)} className="w-44">
            <option value="">Todos</option>
            {fornecedores.map((f) => <option key={f} value={f}>{f}</option>)}
          </Select>
        </Field>
        <Field label="Ruptura">
          <Select value={fRuptura} onChange={(e) => setFRuptura(e.target.value)} className="w-32">
            <option value="">Todas</option><option value="sim">Com ruptura</option><option value="nao">Sem ruptura</option>
          </Select>
        </Field>
        <Button variant="secondary" onClick={() => void carregar()}>Recalcular</Button>
        <Button variant="ghost" onClick={selecionarNecessidade}>Selecionar necessidades</Button>
        <Button variant="primary" onClick={() => void gerarSolicitacao()} disabled={gerando}>
          {gerando ? "Gerando…" : "Gerar solicitação"}
        </Button>
      </div>

      {resultado && (
        <p className="text-xs text-gray-500">
          {resultado.resumo.com_necessidade} produto(s) com necessidade · total sugerido{" "}
          <span className="font-semibold">{resultado.resumo.total_sugerido}</span> · cálculo em {fmtDate(resultado.data)}
        </p>
      )}

      {carregando ? (
        <Loading />
      ) : (
        <Table>
          <THead cols={["", "Produto", "Dep.", "ABC", "XYZ", "Disp.", "Trânsito", "Necess.", "Sugestão", "Fornecedor", "Ruptura", "Política", ""]} />
          <TBody>
            {linhas.length === 0 && <EmptyRow colSpan={13} message="Nenhuma sugestão" />}
            {linhas.map((s) => (
              <>
                <tr key={s.produto_id} className="hover:bg-gray-50">
                  <Cell>
                    <input type="checkbox" aria-label={`selecionar ${s.nome}`} checked={!!sel[s.produto_id]}
                      onChange={(e) => setSel((p) => ({ ...p, [s.produto_id]: e.target.checked }))} />
                  </Cell>
                  <Cell>
                    <span className="font-medium">{s.nome}</span>
                    <div className="text-xs text-gray-400">{s.sku}</div>
                  </Cell>
                  <Cell className="text-xs">{s.deposito_id}</Cell>
                  <Cell><Badge tone={s.classe_abc === "A" ? "green" : s.classe_abc === "B" ? "amber" : "gray"}>{s.classe_abc || "—"}</Badge></Cell>
                  <Cell><Badge tone={s.classe_xyz === "Z" ? "red" : s.classe_xyz === "Y" ? "amber" : "blue"}>{s.classe_xyz || "—"}</Badge></Cell>
                  <Cell>{s.disponivel_projetado}</Cell>
                  <Cell className="text-xs text-gray-500">{s.transito}</Cell>
                  <Cell className="font-semibold">{s.necessidade}</Cell>
                  <Cell className="font-semibold text-emerald-700">
                    <Input className="w-20" inputMode="decimal" value={ajuste[s.produto_id] ?? s.sugestao}
                      onChange={(e) => setAjuste((p) => ({ ...p, [s.produto_id]: Number(e.target.value.replace(",", ".")) }))}
                      aria-label={`ajuste ${s.nome}`} />
                  </Cell>
                  <Cell className="text-xs">{s.fornecedor_nome ?? "—"}</Cell>
                  <Cell className="text-xs">{s.ruptura_provavel ? <span className="text-red-600">{fmtDate(s.ruptura_provavel)}</span> : "—"}</Cell>
                  <Cell className="text-xs">{s.politica}</Cell>
                  <Cell>
                    <button className="text-blue-600 hover:underline" onClick={() => setExpanded(expanded === s.produto_id ? null : s.produto_id)}>
                      {expanded === s.produto_id ? "−" : "+"}
                    </button>
                  </Cell>
                </tr>
                {expanded === s.produto_id && (
                  <tr key={`d-${s.produto_id}`} className="bg-gray-50">
                    <td colSpan={13} className="bg-gray-50 px-4 py-2 text-xs text-gray-600">
                      <div className="flex flex-wrap gap-4">
                        <span>Físico {s.fisico}</span><span>Reservado {s.reservado}</span>
                        <span>Bloqueado {s.bloqueado}</span><span>Disponível {s.disponivel}</span>
                        <span>Demanda aberta {s.demanda_aberta}</span><span>Alvo {s.estoque_alvo}</span>
                        <span>Segurança {s.estoque_seguranca}</span><span>Demanda lead {s.demanda_lead_time}</span>
                        <span>Lead {s.lead_time_dias}d</span>
                        {s.ultimo_preco != null && <span>Preço {fmtMoney(s.ultimo_preco)}</span>}
                      </div>
                      <div className="mt-1">Motivo: {s.justificativa}</div>
                      <Input className="mt-1 w-full" value={just[s.produto_id] ?? ""}
                        onChange={(e) => setJust((p) => ({ ...p, [s.produto_id]: e.target.value }))}
                        placeholder="Justificativa do ajuste…" aria-label={`justificativa ${s.nome}`} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}