import { useEffect, useState } from "react";
import { CircleUserRound, Clock3, Database, ShieldCheck } from "lucide-react";
import { api, encerrarSessaoExpirada, tokenExpiration, type UsuarioAtual } from "../api/client";

function formatarRestante(ms: number): string {
  if (ms <= 0) return "expirada";
  const total = Math.floor(ms / 1000);
  const dias = Math.floor(total / 86400);
  const horas = Math.floor((total % 86400) / 3600);
  const minutos = Math.floor((total % 3600) / 60);
  const segundos = total % 60;
  if (dias > 0) return `${dias}d ${String(horas).padStart(2, "0")}h`;
  return `${String(horas).padStart(2, "0")}:${String(minutos).padStart(2, "0")}:${String(segundos).padStart(2, "0")}`;
}

export function OperationalStatusBar({ usuario }: { usuario: UsuarioAtual | null }) {
  const [agora, setAgora] = useState(Date.now());
  const [expiraEm, setExpiraEm] = useState(() =>
    usuario?.sessao_expira_em ? usuario.sessao_expira_em * 1000 : tokenExpiration(),
  );
  const [versao, setVersao] = useState(usuario?.app_version || "dev");
  const [online, setOnline] = useState(true);

  useEffect(() => {
    const relogio = window.setInterval(() => setAgora(Date.now()), 1000);
    const validar = async () => {
      try {
        const atual = await api.usuarioAtual();
        setOnline(true);
        if (atual.sessao_expira_em) setExpiraEm(atual.sessao_expira_em * 1000);
        if (atual.app_version) setVersao(atual.app_version);
      } catch (error) {
        if ((error as { status?: number }).status !== 401) setOnline(false);
      }
    };
    const monitor = window.setInterval(() => void validar(), 30000);
    void validar();
    return () => {
      window.clearInterval(relogio);
      window.clearInterval(monitor);
    };
  }, []);

  useEffect(() => {
    if (expiraEm !== null && expiraEm <= agora) encerrarSessaoExpirada();
  }, [agora, expiraEm]);

  return (
    <footer className="flex h-8 flex-none items-center gap-3 border-t border-slate-200 bg-slate-900 px-3 text-[11px] text-slate-200 sm:px-5" aria-label="Status operacional">
      <span className="flex min-w-0 items-center gap-1.5" title={usuario?.login || "Usuário autenticado"}>
        <CircleUserRound size={13} aria-hidden="true" />
        <span className="max-w-20 truncate font-medium sm:max-w-32">{usuario?.nome || "Usuário"}</span>
      </span>
      <span className={`flex items-center gap-1.5 ${online ? "text-emerald-300" : "text-red-300"}`} title="Comunicação autenticada com API e banco de dados">
        <Database size={13} aria-hidden="true" />
        <span className="hidden sm:inline">API/BD {online ? "online" : "indisponível"}</span>
      </span>
      <span className="ml-auto hidden items-center gap-1.5 text-slate-400 sm:flex" title="Versão implantada">
        <ShieldCheck size={13} aria-hidden="true" />
        <span>{versao}</span>
      </span>
      <span className="flex items-center gap-1.5 font-mono text-slate-300" title="Tempo restante da sessão">
        <Clock3 size={13} aria-hidden="true" />
        <span>Sessão {expiraEm === null ? "—" : formatarRestante(expiraEm - agora)}</span>
      </span>
    </footer>
  );
}
