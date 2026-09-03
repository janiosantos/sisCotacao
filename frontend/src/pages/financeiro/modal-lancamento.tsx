// pages/financeiro/modal-lancamento.tsx — nova conta a pagar/receber com
// parcelamento por condição, manual, datas ou recorrência (v2.25.0).
import { useEffect, useState } from "react";
import { api, type CondicaoPagamento, type ContaPlano, type CentroCusto, type ParcelaCalculada } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal, Select, Textarea } from "../../ui/ui";

export function ModalLancamento({
  open,
  tabela,
  pessoaLabel,
  onClose,
  onSalvo,
}: {
  open: boolean;
  tabela: "pagar" | "receber";
  pessoaLabel: string;
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [pessoa, setPessoa] = useState("");
  const [desc, setDesc] = useState("");
  const [valor, setValor] = useState("");
  const [doc, setDoc] = useState("");
  const [emissao, setEmissao] = useState(() => new Date().toISOString().slice(0, 10));
  const [obs, setObs] = useState("");
  const [modo, setModo] = useState<"avista" | "condicao" | "manual" | "datas" | "recorrente">("avista");
  const [condicoes, setCondicoes] = useState<CondicaoPagamento[]>([]);
  const [condId, setCondId] = useState("");
  const [nParcelas, setNParcelas] = useState("3");
  const [intervalo, setIntervalo] = useState("30");
  const [frequencia, setFrequencia] = useState("mensal");
  const [nOcorrencias, setNOcorrencias] = useState("12");
  const [dia, setDia] = useState("");
  const [preview, setPreview] = useState<{ parcelas: ParcelaCalculada[]; total: number; n: number } | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [contasPlano, setContasPlano] = useState<ContaPlano[]>([]);
  const [centros, setCentros] = useState<CentroCusto[]>([]);
  const [planoContaId, setPlanoContaId] = useState("");
  const [centroCustoId, setCentroCustoId] = useState("");
  const [competencia, setCompetencia] = useState(() => new Date().toISOString().slice(0, 7));

  useEffect(() => {
    if (!open) return;
    setPessoa(""); setDesc(""); setValor(""); setDoc(""); setObs("");
    setModo("avista"); setCondId(""); setPreview(null);
    setPlanoContaId(""); setCentroCustoId(""); setCompetencia(new Date().toISOString().slice(0, 7));
    setEmissao(new Date().toISOString().slice(0, 10));
    void Promise.all([
      api.listarCondicoes(),
      tabela === "pagar" ? api.listarPlanoContas("despesa", true) : Promise.resolve([] as ContaPlano[]),
      tabela === "pagar" ? api.listarCentrosCusto() : Promise.resolve([] as CentroCusto[]),
    ]).then(([cs, ps, centrosAtivos]) => { setCondicoes(cs); setContasPlano(ps); setCentros(centrosAtivos); }).catch(() => {});
  }, [open]);

  const payloadBase = () => ({
    [tabela === "pagar" ? "fornecedor" : "cliente"]: pessoa.trim(),
    descricao: desc.trim(),
    valor: parseFloat(valor.replace(",", ".")) || 0,
    documento: doc.trim() || undefined,
    data_emissao: emissao,
    observacao: obs.trim() || undefined,
    modo,
    data_base: emissao,
    condicao_pagamento_id: modo === "condicao" ? Number(condId) || undefined : undefined,
    n_parcelas: modo === "manual" ? Number(nParcelas) || 1 : undefined,
    intervalo_dias: modo === "manual" ? Number(intervalo) || 30 : undefined,
    recorrencia: modo === "recorrente" ? "1" : undefined,
    frequencia: modo === "recorrente" ? frequencia : undefined,
    primeira: modo === "recorrente" ? emissao : undefined,
    n_ocorrencias: modo === "recorrente" ? Number(nOcorrencias) || 1 : undefined,
    dia: modo === "recorrente" && dia ? Number(dia) : undefined,
    plano_conta_id: tabela === "pagar" ? Number(planoContaId) || undefined : undefined,
    centro_custo_id: tabela === "pagar" ? Number(centroCustoId) || undefined : undefined,
    competencia: tabela === "pagar" ? competencia : undefined,
    exigir_classificacao: tabela === "pagar",
  });

  const calcularPreview = async () => {
    try {
      const r = await api.previewLote(payloadBase());
      setPreview(r);
    } catch (e) {
      setPreview(null);
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const salvar = async () => {
    if (!pessoa.trim()) {
      toast(`Informe o ${pessoaLabel.toLowerCase()}`, "error");
      return;
    }
    if ((parseFloat(valor.replace(",", ".")) || 0) <= 0) {
      toast("Informe o valor", "error");
      return;
    }
    if (tabela === "pagar" && !planoContaId) {
      toast("Selecione o plano de contas da despesa", "error");
      return;
    }
    if (modo === "condicao" && !condId) {
      toast("Escolha a condição de pagamento", "error");
      return;
    }
    setSalvando(true);
    try {
      const payload = payloadBase();
      if (modo === "avista") {
        const body = {
          [tabela === "pagar" ? "fornecedor" : "cliente"]: pessoa.trim(),
          valor: payload.valor,
          data_vencimento: emissao,
          descricao: desc.trim(),
          documento: doc.trim() || undefined,
          observacao: obs.trim() || undefined,
          plano_conta_id: tabela === "pagar" ? Number(planoContaId) : undefined,
          centro_custo_id: tabela === "pagar" && centroCustoId ? Number(centroCustoId) : undefined,
          competencia: tabela === "pagar" ? competencia : undefined,
          exigir_classificacao: tabela === "pagar",
        };
        if (tabela === "pagar") await api.criarPagar(body);
        else await api.criarReceber(body);
      } else if (tabela === "pagar") {
        await api.criarPagarLote(payload);
      } else {
        await api.criarReceberLote(payload);
      }
      toast(modo === "avista" ? "Conta criada" : "Lançamento parcelado criado", "success");
      onSalvo();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={tabela === "pagar" ? "Nova conta a pagar" : "Nova conta a receber"}
      wide
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          {modo !== "avista" ? (
            <Button onClick={() => void calcularPreview()}>Calcular parcelas</Button>
          ) : null}
          <Button variant="primary" onClick={() => void salvar()} disabled={salvando}>
            {salvando ? "Salvando…" : modo === "avista" ? "Salvar" : `Salvar ${modo === "recorrente" ? "recorrência" : "parcelado"}`}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label={pessoaLabel}>
          <Input value={pessoa} onChange={(e) => setPessoa(e.target.value)} autoFocus />
        </Field>
        <Field label="Descrição">
          <Input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder={tabela === "pagar" ? "Ex.: Nota fiscal 1234 — materiais" : "Ex.: Aluguel do galpão"} />
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="Valor total (R$)">
            <Input type="number" step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} />
          </Field>
          <Field label="Documento (nota)">
            <Input value={doc} onChange={(e) => setDoc(e.target.value)} />
          </Field>
          <Field label="Data de emissão">
            <Input type="date" value={emissao} onChange={(e) => setEmissao(e.target.value)} />
          </Field>
        </div>

        {tabela === "pagar" ? (
          <div className="grid grid-cols-1 gap-3 rounded-lg border border-amber-200 bg-amber-50/60 p-4 sm:grid-cols-3">
            <Field label="Plano de contas *">
              <Select value={planoContaId} onChange={(e) => setPlanoContaId(e.target.value)}>
                <option value="">Selecione a classificação…</option>
                {contasPlano.map((c) => <option key={c.id} value={c.id}>{c.codigo} · {c.nome}</option>)}
              </Select>
            </Field>
            <Field label="Competência *">
              <Input type="month" value={competencia} onChange={(e) => setCompetencia(e.target.value)} />
            </Field>
            <Field label="Centro de custo">
              <Select value={centroCustoId} onChange={(e) => setCentroCustoId(e.target.value)}>
                <option value="">Sem centro de custo</option>
                {centros.map((c) => <option key={c.id} value={c.id}>{c.codigo} · {c.nome}</option>)}
              </Select>
            </Field>
            {planoContaId ? (() => { const conta = contasPlano.find((c) => c.id === Number(planoContaId)); return conta ? <p className="sm:col-span-3 text-xs text-slate-600">Natureza: <strong>{conta.natureza_custo || "não classificada"}</strong> · Rateio: <strong>{conta.politica_rateio || "não incluir"}</strong></p> : null; })() : null}
          </div>
        ) : null}

        <div className="rounded-md border border-gray-200 p-3">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Parcelamento</div>
          <div className="mb-3 flex flex-wrap gap-2">
            {([
              ["avista", "À vista"],
              ["condicao", "Por condição"],
              ["manual", "Parcelado"],
              ["recorrente", "Recorrente"],
            ] as const).map(([k, l]) => (
              <button
                key={k}
                onClick={() => { setModo(k); setPreview(null); }}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${modo === k ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-100"}`}
              >
                {l}
              </button>
            ))}
          </div>

          {modo === "condicao" ? (
            <Field label="Condição de pagamento">
              <Select value={condId} onChange={(e) => { setCondId(e.target.value); setPreview(null); }}>
                <option value="">Selecione…</option>
                {condicoes.map((c) => (
                  <option key={c.id} value={c.id}>{c.nome}</option>
                ))}
              </Select>
            </Field>
          ) : null}

          {modo === "manual" ? (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Nº de parcelas">
                <Input type="number" min={1} value={nParcelas} onChange={(e) => { setNParcelas(e.target.value); setPreview(null); }} />
              </Field>
              <Field label="Intervalo entre parcelas (dias)">
                <Input type="number" min={0} value={intervalo} onChange={(e) => { setIntervalo(e.target.value); setPreview(null); }} />
              </Field>
            </div>
          ) : null}

          {modo === "recorrente" ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field label="Frequência">
                <Select value={frequencia} onChange={(e) => { setFrequencia(e.target.value); setPreview(null); }}>
                  <option value="mensal">Mensal</option>
                  <option value="semanal">Semanal</option>
                  <option value="anual">Anual</option>
                </Select>
              </Field>
              <Field label="Nº de ocorrências">
                <Input type="number" min={1} value={nOcorrencias} onChange={(e) => { setNOcorrencias(e.target.value); setPreview(null); }} />
              </Field>
              <Field label="Dia do vencimento (opcional)">
                <Input type="number" min={1} max={28} value={dia} onChange={(e) => { setDia(e.target.value); setPreview(null); }} placeholder="ex.: 10" />
              </Field>
            </div>
          ) : null}

          {preview ? (
            <div className="mt-3 rounded-md bg-gray-50 p-3">
              <div className="mb-2 text-xs font-semibold text-gray-500">
                {preview.n} parcela(s) · total {fmtMoney(preview.total)}
              </div>
              <div className="space-y-1">
                {preview.parcelas.map((p, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">{i + 1}ª · venc. {fmtDate(p.vencimento)}</span>
                    <span className="font-medium">{fmtMoney(p.valor)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : modo !== "avista" ? (
            <p className="mt-3 text-xs text-gray-400">Clique em "Calcular parcelas" para conferir antes de salvar.</p>
          ) : null}
        </div>

        <Field label="Observação">
          <Textarea value={obs} onChange={(e) => setObs(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}
