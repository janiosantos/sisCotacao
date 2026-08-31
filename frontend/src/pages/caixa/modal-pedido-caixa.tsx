// pages/caixa/modal-pedido-caixa.tsx — recebimento do pedido no caixa (ECF) + NFC-e.
import { useEffect, useRef, useState } from "react";
import { api, type DocumentoFiscal, type OrcamentoDetalhe } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Field, Input, Modal } from "../../ui/ui";
import { fmtNum2, parseNum } from "./helpers";
import { FORMAS_CAIXA } from "./labels";

type EtapaRecebimento = "recebimento" | "emitindo" | "aguardando" | "autorizada" | "erro";

export function ModalPedidoCaixa({ d, onSair }: { d: OrcamentoDetalhe; onSair: () => void }) {
  const total = d.total;
  const [etapa, setEtapa] = useState<EtapaRecebimento>("recebimento");
  const [forma, setForma] = useState("dinheiro");
  const [valor, setValor] = useState("");
  const [bandeira, setBandeira] = useState("");
  const [codigoAutorizacao, setCodigoAutorizacao] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [doc, setDoc] = useState<DocumentoFiscal | { status: "nao_emitido" } | null>(null);
  const [erroMsg, setErroMsg] = useState("");
  const [imprimindo, setImprimindo] = useState(false);
  const valorRef = useRef<HTMLInputElement>(null);
  const bandeiraRef = useRef<HTMLInputElement>(null);
  const codigoRef = useRef<HTMLInputElement>(null);
  const imprimirRef = useRef<HTMLButtonElement>(null);
  const retryRef = useRef<HTMLButtonElement>(null);
  const confirmarRef = useRef<HTMLButtonElement>(null);

  const valorNum = parseNum(valor);
  const troco = forma === "dinheiro" ? Math.max(0, valorNum - total) : 0;
  const ehCartao = forma === "cartao_credito" || forma === "cartao_debito";

  const mudarForma = (f: string) => {
    setForma(f);
    // Dinheiro: operador digita o recebido. Demais formas: valor exato (total).
    setValor(f === "dinheiro" ? "" : fmtNum2(total));
    valorRef.current?.focus();
    valorRef.current?.select();
  };

  const emitirNfceAuto = async () => {
    setErroMsg("");
    setEtapa("emitindo");
    try {
      const res = await api.emitirNfce(d.id);
      setDoc(res);
      if (res.status === "autorizado") {
        setEtapa("autorizada");
      } else if (res.status === "rejeitado" || res.status === "erro") {
        setErroMsg(res.motivo || "Falha na emissão da NFC-e");
        setEtapa("erro");
      } else {
        setEtapa("aguardando");
      }
    } catch (e) {
      setErroMsg((e as Error).message);
      setEtapa("erro");
    }
  };

  const confirmar = async () => {
    if (valorNum <= 0) {
      toast("Informe o valor recebido", "error");
      return;
    }
    setEnviando(true);
    try {
      const res = await api.receberOrcamento(d.id, {
        forma_pagamento: forma,
        valor_recebido: valorNum,
        bandeira: ehCartao ? bandeira.trim() || undefined : undefined,
        codigo_autorizacao: ehCartao ? codigoAutorizacao.trim() || undefined : undefined,
      });
      setEnviando(false);
      if (res.recebido) toast(res.troco > 0 ? `Recebido · troco ${fmtMoney(res.troco)}` : "Recebimento registrado", "success");
      else toast(`Recebimento parcial de ${fmtMoney(res.valor_recebido)}`, "success");
      // Emissão da NFC-e é automática após concluir o recebimento.
      void emitirNfceAuto();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      setEnviando(false);
    }
  };

  const imprimir = async () => {
    if (imprimindo) return;
    setImprimindo(true);
    try {
      await api.imprimirOrcamento(d.id);
      toast("Cupom enviado à impressora", "success");
      onSair();
    } catch (e) {
      toast("Impressão falhou: " + (e as Error).message, "error");
      setImprimindo(false);
      setTimeout(() => imprimirRef.current?.focus(), 0);
    }
  };

  // Polling do status enquanto a NFC-e fica "processando" (emissão assíncrona).
  useEffect(() => {
    if (etapa !== "aguardando") return;
    const t = setInterval(() => {
      void api
        .statusNfce(d.id)
        .then((res) => {
          setDoc(res);
          if (res.status === "autorizado") setEtapa("autorizada");
          else if (res.status === "rejeitado" || res.status === "erro") {
            setErroMsg(res.motivo || "Falha na emissão da NFC-e");
            setEtapa("erro");
          }
        })
        .catch(() => {});
    }, 3000);
    return () => clearInterval(t);
  }, [etapa, d.id]);

  // Foco no botão de impressão / nova tentativa conforme a etapa.
  useEffect(() => {
    if (etapa === "autorizada") imprimirRef.current?.focus();
    else if (etapa === "erro") retryRef.current?.focus();
  }, [etapa]);

  // Atalhos da etapa de recebimento: F1..F7 trocam a forma, F9 preenche com o
  // total, Ctrl+Enter confirma.
  useEffect(() => {
    if (etapa !== "recebimento") return;
    const onKey = (e: KeyboardEvent) => {
      const idx = FORMAS_CAIXA.findIndex((f) => f.tecla === e.key.toUpperCase());
      if (idx >= 0) {
        e.preventDefault();
        mudarForma(FORMAS_CAIXA[idx].valor);
        return;
      }
      if (e.key === "F9") {
        e.preventDefault();
        setValor(fmtNum2(total));
        valorRef.current?.focus();
        valorRef.current?.select();
        return;
      }
      if (e.key === "Enter" && e.ctrlKey) {
        e.preventDefault();
        void confirmar();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etapa, forma, valorNum, bandeira, codigoAutorizacao, total]);

  const titulo = etapa === "recebimento" ? `Recebimento — Pedido ${d.numero}` : `NFC-e — Pedido ${d.numero}`;

  return (
    <Modal
      open
      onClose={onSair}
      title={titulo}
      wide
      footer={
        etapa === "autorizada" ? (
          <>
            <Button variant="ghost" onClick={onSair}>
              ← Voltar para o Caixa <kbd className="ml-1 rounded bg-white px-1 text-[10px] shadow-sm">ESC</kbd>
            </Button>
            <Button ref={imprimirRef} variant="primary" permission={{ recurso: "impressao", acao: "imprimir" }} onClick={() => void imprimir()} disabled={imprimindo}>
              {imprimindo ? "Imprimindo…" : "Imprimir"}
              <kbd className="ml-2 rounded bg-white/20 px-1 text-[10px]">ENTER</kbd>
            </Button>
          </>
        ) : etapa === "erro" ? (
          <>
            <Button variant="ghost" onClick={onSair}>
              ← Voltar <kbd className="ml-1 rounded bg-white px-1 text-[10px] shadow-sm">ESC</kbd>
            </Button>
            <Button ref={retryRef} variant="primary" permission={{ recurso: "fiscal", acao: "emitir" }} onClick={() => void emitirNfceAuto()}>
              Tentar novamente <kbd className="ml-2 rounded bg-white/20 px-1 text-[10px]">ENTER</kbd>
            </Button>
          </>
        ) : etapa === "recebimento" ? (
          <>
            <Button variant="ghost" onClick={onSair}>
              ← Voltar para o Caixa <kbd className="ml-1 rounded bg-white px-1 text-[10px] shadow-sm">ESC</kbd>
            </Button>
            <Button ref={confirmarRef} variant="primary" permission={{ recurso: "caixa", acao: "cadastrar" }} onClick={() => void confirmar()} disabled={enviando}>
              {enviando ? "Registrando…" : "Confirmar recebimento"}
              <kbd className="ml-2 rounded bg-white/20 px-1 text-[10px]">Ctrl+Enter</kbd>
            </Button>
          </>
        ) : (
          <Button variant="ghost" onClick={onSair}>
            ← Voltar <kbd className="ml-1 rounded bg-white px-1 text-[10px] shadow-sm">ESC</kbd>
          </Button>
        )
      }
    >
      {etapa === "recebimento" && (
        <>
          <p className="mb-3 text-sm text-gray-500">
            {d.cliente || "Sem cliente"} · Vendedor: {d.usuario_nome || "—"} · {fmtDate(d.criado_em)}
          </p>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl bg-orange-50 p-4 text-center">
              <div className="text-xs font-medium uppercase text-orange-700">Valor a Receber</div>
              <div className="mt-1 text-3xl font-bold text-orange-600">{fmtMoney(total)}</div>
            </div>

            <div className="rounded-xl bg-white p-4 text-center ring-1 ring-gray-200">
              <div className="text-xs font-medium uppercase text-gray-500">Valor Recebido</div>
              <input
                ref={valorRef}
                inputMode="decimal"
                value={valor}
                onChange={(e) => setValor(e.target.value)}
                autoFocus
                placeholder="0,00"
                className="mt-1 w-full bg-transparent text-center text-3xl font-bold text-black outline-none"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    if (ehCartao) {
                      bandeiraRef.current?.focus();
                    } else {
                      // Dinheiro: não finaliza ainda — mostra o troco e move o
                      // foco para "Confirmar recebimento"; um 2º ENTER finaliza.
                      confirmarRef.current?.focus();
                    }
                  }
                }}
              />
            </div>

            <div className="rounded-xl bg-white p-4 text-center ring-1 ring-gray-200">
              <div className="text-xs font-medium uppercase text-gray-500">Troco</div>
              <div className="mt-1 text-3xl font-bold text-emerald-600">{fmtMoney(troco)}</div>
            </div>
          </div>

          <div className="mt-4">
            <label className="mb-1 block text-xs font-semibold text-gray-600">Forma de pagamento</label>
            <div className="flex flex-wrap gap-1.5">
              {FORMAS_CAIXA.map((f) => (
                <button
                  key={f.valor}
                  onClick={() => mudarForma(f.valor)}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
                    forma === f.valor ? "border-orange-500 bg-orange-500 text-white" : "border-gray-300 bg-white text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  {f.label}
                  <kbd className={`rounded px-1 text-[10px] ${forma === f.valor ? "bg-white/25" : "bg-gray-100 text-gray-400"}`}>
                    {f.tecla}
                  </kbd>
                </button>
              ))}
              <button
                onClick={() => {
                  setValor(fmtNum2(total));
                  valorRef.current?.focus();
                  valorRef.current?.select();
                }}
                className="flex items-center gap-1.5 rounded-full border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
              >
                Total <kbd className="rounded bg-gray-100 px-1 text-[10px] text-gray-400">F9</kbd>
              </button>
            </div>
          </div>

          {ehCartao && (
            <div className="mt-4 grid grid-cols-2 gap-3">
              <Field label="Bandeira do cartão">
                <Input
                  ref={bandeiraRef}
                  value={bandeira}
                  onChange={(e) => setBandeira(e.target.value)}
                  placeholder="VISA / MASTER / ELO…"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      codigoRef.current?.focus();
                    }
                  }}
                />
              </Field>
              <Field label="Código de autorização">
                <Input
                  ref={codigoRef}
                  value={codigoAutorizacao}
                  onChange={(e) => setCodigoAutorizacao(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void confirmar();
                    }
                  }}
                />
              </Field>
            </div>
          )}
        </>
      )}

      {(etapa === "emitindo" || etapa === "aguardando") && (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <div className="h-9 w-9 animate-spin rounded-full border-4 border-gray-200 border-t-orange-500" />
          <p className="mt-4 text-lg font-bold text-gray-700">
            {etapa === "emitindo" ? "Emitindo NFC-e…" : "Aguardando NFC-e…"}
          </p>
          <p className="mt-1 text-xs text-gray-500">Aguarde a autorização da SEFAZ.</p>
        </div>
      )}

      {etapa === "autorizada" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Badge tone="green">NFC-e autorizada</Badge>
          </div>
          {doc && "chave_acesso" in doc && doc.chave_acesso && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
              <div className="mb-1 text-xs font-medium uppercase text-gray-500">Chave de acesso</div>
              <div className="break-all font-mono text-xs">{doc.chave_acesso}</div>
              {doc.protocolo && <div className="mt-2 text-xs text-gray-500">Protocolo: {doc.protocolo}</div>}
            </div>
          )}
          <p className="text-sm text-gray-600">
            Pressione <b>ENTER</b> para imprimir o cupom ou <b>ESC</b> para voltar ao caixa.
          </p>
        </div>
      )}

      {etapa === "erro" && (
        <div className="space-y-3">
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{erroMsg || "Falha na emissão da NFC-e."}</p>
          <p className="text-sm text-gray-600">
            Pressione <b>ENTER</b> para tentar novamente ou <b>ESC</b> para voltar ao caixa.
          </p>
        </div>
      )}
    </Modal>
  );
}
