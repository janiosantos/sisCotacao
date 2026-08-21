// manutencao.tsx — modo manutenção: overlay global quando backend/banco estão
// fora do ar (deploy, manutenção de banco, rede). Detecta via erros de conexão
// reportados pelo client e reconecta consultando /api/pronto periodicamente.
// Funciona com serviços em servidores diferentes (probe é HTTP puro).

import { useEffect, useState } from "react";

type Ouvinte = () => void;

const ouvintes = new Set<Ouvinte>();
let offline = false;
let ultimaTentativa: Date | null = null;
let timer: number | null = null;

export function estaOffline(): boolean {
  return offline;
}

function notificar(): void {
  for (const f of ouvintes) f();
}

/** Chamado pelo client quando uma chamada falha por infraestrutura. */
export function sinalizarFalhaConexao(): void {
  ultimaTentativa = new Date();
  if (!offline) {
    offline = true;
    notificar();
    iniciarPolling();
  }
}

/** Chamado pelo client em qualquer resposta válida do backend. */
export function sinalizarSucesso(): void {
  if (!offline) return;
  offline = false;
  pararPolling();
  notificar();
  // Recuperação automática: recarrega para revalidar sessão e dados.
  location.reload();
}

function iniciarPolling(): void {
  if (timer !== null) return;
  timer = window.setInterval(() => void verificar(), 10000);
  void verificar();
}

function pararPolling(): void {
  if (timer !== null) {
    window.clearInterval(timer);
    timer = null;
  }
}

async function verificar(): Promise<void> {
  try {
    const r = await fetch("/api/pronto", { cache: "no-store" });
    if (r.ok) sinalizarSucesso();
    else ultimaTentativa = new Date();
  } catch {
    ultimaTentativa = new Date();
  }
}

export function Manutencao() {
  const [mostrar, setMostrar] = useState(estaOffline());

  useEffect(() => {
    const f = () => setMostrar(estaOffline());
    ouvintes.add(f);
    return () => {
      ouvintes.delete(f);
    };
  }, []);

  if (!mostrar) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-gray-900/80">
      <div className="mx-4 max-w-md rounded-lg bg-white p-6 text-center shadow-xl">
        <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
        <h2 className="text-lg font-semibold text-gray-900">Sistema em manutenção</h2>
        <p className="mt-2 text-sm text-gray-500">
          Não estamos conseguindo falar com o servidor agora. A reconexão é
          automática (tentativas a cada 10 segundos) — assim que voltar, o
          sistema recarrega sozinho.
        </p>
        {ultimaTentativa && (
          <p className="mt-3 text-xs text-gray-400">
            Última tentativa: {ultimaTentativa.toLocaleTimeString("pt-BR")}
          </p>
        )}
      </div>
    </div>
  );
}
