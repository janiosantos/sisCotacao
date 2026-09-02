// App.tsx — shell do ERP (sidebar + topbar + conteúdo) em React + Tailwind.

import { Component, lazy, Suspense, useEffect, useMemo, useRef, useState, type ErrorInfo, type ReactNode } from "react";
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  FileText,
  ShoppingBag,
  Users,
  Handshake,
  Truck,
  Boxes,
  UserCheck,
  Tags,
  Scale,
  SearchCheck,
  Wallet,
  DollarSign,
  Landmark,
  BookOpen,
  Banknote,
  Warehouse,
  Webhook,
  Receipt,
  RotateCcw,
  RefreshCw,
  History,
  ShieldCheck,
  Settings,
  LogOut,
  Menu,
  X,
  BarChart3,
  CircleHelp,
  type LucideIcon,
} from "lucide-react";
import { ROUTES } from "./routes";
import { carregarSessao, entrar, sair, usuarioCorrente } from "./pages/login";
import { startupAuth } from "./auth";
import { Manutencao, estaOffline } from "./manutencao";
import { countItens, injectOverlay as injectCartOverlay, toggle as toggleCart } from "./cart";
import { Button } from "./ui/ui";
import { podeVisualizar } from "./perm";

const ManualPage = lazy(() => import("./pages/manual"));

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  recurso: string;
}
interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV: NavGroup[] = [
  {
    label: "Operação",
    items: [
      { href: "#/dashboard", label: "Painel", icon: LayoutDashboard, recurso: "dashboard" },
      { href: "#/pre-venda", label: "Pré-venda", icon: ShoppingCart, recurso: "pre-venda" },
      { href: "#/orcamentos", label: "Orçamentos", icon: FileText, recurso: "orcamentos" },
      { href: "#/caixa", label: "Caixa", icon: Banknote, recurso: "caixa" },
      { href: "#/posvenda", label: "Pós-venda", icon: RotateCcw, recurso: "posvenda" },
    ],
  },
  {
    label: "Comercial",
    items: [
      { href: "#/catalogo", label: "Catálogo", icon: Package, recurso: "catalogo" },
      { href: "#/produtos", label: "Produtos", icon: Boxes, recurso: "produtos" },
      { href: "#/clientes", label: "Clientes", icon: Users, recurso: "clientes" },
      { href: "#/parceiros", label: "Parceiros", icon: Handshake, recurso: "parceiros" },
      { href: "#/vendedores", label: "Vendedores", icon: UserCheck, recurso: "vendedores" },
      { href: "#/categorias", label: "Categorias", icon: Tags, recurso: "categorias" },
      { href: "#/unidades", label: "Unidades", icon: Scale, recurso: "unidades" },
    ],
  },
  {
    label: "Compras",
    items: [
      { href: "#/compras", label: "Compras", icon: ShoppingBag, recurso: "compras" },
      { href: "#/fornecedores", label: "Fornecedores", icon: Truck, recurso: "fornecedores" },
      { href: "#/estoque", label: "Estoque", icon: Warehouse, recurso: "estoque" },
      { href: "#/diagnostico-variacoes", label: "Qualidade", icon: SearchCheck, recurso: "qualidade" },
    ],
  },
  {
    label: "Financeiro",
    items: [
      { href: "#/financeiro", label: "Financeiro", icon: Wallet, recurso: "financeiro" },
      { href: "#/precos", label: "Preços", icon: DollarSign, recurso: "precos" },
      { href: "#/historico", label: "Hist. preços", icon: History, recurso: "historico" },
      { href: "#/bancos", label: "Bancos", icon: Landmark, recurso: "bancos" },
      { href: "#/plano-contas", label: "Plano de contas", icon: BookOpen, recurso: "plano_contas" },
      { href: "#/webhooks", label: "Webhooks", icon: Webhook, recurso: "financeiro" },
    ],
  },
  {
    label: "Fiscal",
    items: [
      { href: "#/fiscal", label: "Fiscal", icon: Receipt, recurso: "fiscal" },
    ],
  },
  {
    label: "Relatórios",
    items: [
      { href: "#/relatorios", label: "Relatórios", icon: BarChart3, recurso: "relatorios" },
    ],
  },
  {
    label: "Administração",
    items: [
      { href: "#/usuarios", label: "Usuários", icon: ShieldCheck, recurso: "usuarios" },
      { href: "#/perfis", label: "Perfis e permissões", icon: ShieldCheck, recurso: "perfis" },
      { href: "#/configuracoes", label: "Configurações", icon: Settings, recurso: "configuracoes" },
      { href: "#/atualizacoes", label: "Atualizações", icon: RefreshCw, recurso: "atualizacoes" },
    ],
  },
];

function useHashRoute(): string {
  const [hash, setHash] = useState(() => location.hash || "#/dashboard");
  useEffect(() => {
    const onHash = () => {
      setHash(location.hash || "#/dashboard");
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return hash;
}

function isActive(hash: string, href: string): boolean {
  return hash === href || hash.startsWith(href + "/");
}

class RouteErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Falha ao carregar módulo da rota", error, info);
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="rounded-lg border border-dashed border-red-200 bg-white py-16 text-center text-sm text-gray-500">
          <p className="text-base font-medium text-gray-700">Não foi possível carregar esta tela</p>
          <p className="mt-1">Atualize a página ou tente novamente.</p>
          <Button variant="outline" className="mt-4" onClick={() => location.reload()}>
            Tentar novamente
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}

function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const loginRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loginRef.current?.focus();
  }, []);

  const tentar = async () => {
    const ok = await entrar(login.trim(), senha);
    if (ok) onLogin();
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-100 px-4 py-8">
      <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-brand-100/70 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-28 -right-20 h-80 w-80 rounded-full bg-blue-100/70 blur-3xl" />
      <div className="login-box relative w-full max-w-sm rounded-2xl border border-white/80 bg-white/95 p-6 shadow-[0_20px_50px_rgb(16_24_40/12%)] backdrop-blur sm:p-7">
        <div className="mb-4 flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm shadow-brand-600/30">
            <ShoppingBag size={18} />
          </div>
          <div>
            <div className="text-base font-semibold text-gray-900">ERP Comercial</div>
            <div className="text-xs text-gray-500">Entre com seu usuário</div>
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Login</label>
            <input
              id="lgLogin"
              ref={loginRef}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              value={login}
              autoComplete="username"
              onChange={(e) => setLogin(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void tentar()}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Senha</label>
            <input
              id="lgSenha"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              type="password"
              value={senha}
              autoComplete="current-password"
              onChange={(e) => setSenha(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void tentar()}
            />
          </div>
          <Button id="lgEntrar" variant="primary" className="w-full" onClick={() => void tentar()}>
            Entrar
          </Button>
          <a href="#/manual" className="block text-center text-xs font-semibold text-brand-700 hover:underline">
            Consultar manual do sistema
          </a>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const hash = useHashRoute();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [cartCount, setCartCount] = useState(0);
  const [menuAberto, setMenuAberto] = useState(false);

  useEffect(() => {
    injectCartOverlay();
    const upd = () => setCartCount(countItens());
    upd();
    document.addEventListener("cart:updated", upd);
    return () => document.removeEventListener("cart:updated", upd);
  }, []);

  useEffect(() => {
    let alive = true;
    void (async () => {
      const ok = await carregarSessao();
      if (!alive) return;
      setAuthed(ok);
      // Backend fora do ar: o overlay de manutenção assume; não abre o fluxo
      // de primeiro acesso nem a tela de login por cima do banner.
      if (!ok && !estaOffline()) startupAuth();
    })();
    return () => {
      alive = false;
    };
  }, []);

  const route = useMemo(() => {
    for (const r of ROUTES) {
      const m = hash.match(r.pattern);
      if (m) return { def: r, m };
    }
    return null;
  }, [hash]);

  // Gate de permissão: rota mapeada para um recurso exige "visualizar".
  const rotaLiberada =
    !route || !route.def.recurso || podeVisualizar(route.def.recurso);

  useEffect(() => {
    if (authed && !route && hash !== "#/dashboard") {
      location.hash = "#/dashboard";
    }
  }, [authed, route, hash]);

  // Ao trocar de rota no mobile, fecha o menu lateral.
  useEffect(() => {
    setMenuAberto(false);
  }, [hash]);

  if (authed === null) {
    return (
      <>
        <div className="min-h-screen bg-gray-100" />
        <Manutencao />
      </>
    );
  }

  if (!authed) {
    if (hash === "#/manual") {
      return (
        <>
          <div className="min-h-screen bg-slate-100 p-3 sm:p-6">
            <Suspense fallback={<div className="py-16 text-center text-sm text-slate-500">Carregando manual…</div>}>
              <ManualPage />
            </Suspense>
          </div>
        </>
      );
    }
    return (
      <>
        <LoginScreen onLogin={() => setAuthed(true)} />
        <Manutencao />
      </>
    );
  }

  const usuario = usuarioCorrente();
  const RouteComponent = route?.def.component ?? null;

  const SidebarNav = (
    <nav className="erp-scrollbar flex-1 space-y-5 overflow-y-auto px-3 py-4" aria-label="Navegação principal">
      {NAV.map((g) => {
        const visiveis = g.items.filter((it) => podeVisualizar(it.recurso));
        if (visiveis.length === 0) return null;
        return (
          <div key={g.label}>
            <div className="px-2 pb-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
              {g.label}
            </div>
            <div className="space-y-1">
              {visiveis.map((it) => {
                const active = isActive(hash, it.href);
                const Icon = it.icon;
                return (
                  <a
                    key={it.href}
                    href={it.href}
                    aria-current={active ? "page" : undefined}
                    className={`group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium ${
                      active
                        ? "bg-brand-50 text-brand-800 shadow-sm ring-1 ring-brand-100"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    <Icon size={16} strokeWidth={active ? 2.2 : 1.8} className={active ? "text-brand-600" : "text-slate-400 group-hover:text-slate-600"} />
                    {it.label}
                  </a>
                );
              })}
            </div>
          </div>
        );
      })}
    </nav>
  );

  const SidebarBrand = (
    <div className="flex h-16 items-center gap-2.5 border-b border-slate-200 px-4">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm shadow-brand-600/25">
        <ShoppingBag size={18} />
      </div>
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold leading-tight text-gray-900">ERP Comercial</div>
        <div className="text-[11px] text-gray-400">Gestão de varejo</div>
      </div>
    </div>
  );

  return (
    <>
      <Manutencao />
      <div className="flex h-dvh overflow-hidden bg-slate-100">
      {/* Sidebar — desktop/tablet: fixa; mobile: drawer (off-canvas) */}
      <aside className="hidden md:flex md:w-64 md:flex-none md:flex-col md:border-r md:border-slate-200 md:bg-white">
        {SidebarBrand}
        {SidebarNav}
      </aside>

      {/* Overlay + drawer mobile */}
      {menuAberto && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMenuAberto(false)} />
          <aside className="absolute left-0 top-0 flex h-full w-72 max-w-[85vw] flex-col border-r border-slate-200 bg-white shadow-xl">
            <div className="flex items-center justify-between pr-2">
              {SidebarBrand}
              <button className="p-2 text-gray-500 hover:text-gray-800" onClick={() => setMenuAberto(false)} title="Fechar menu">
                <X size={20} />
              </button>
            </div>
            {SidebarNav}
          </aside>
        </div>
      )}

      {/* Conteúdo */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="z-20 flex h-16 flex-none items-center gap-2 border-b border-slate-200 bg-white/95 px-3 shadow-[0_1px_3px_rgb(16_24_40/4%)] backdrop-blur sm:gap-4 sm:px-6">
          <button
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 md:hidden"
            onClick={() => setMenuAberto(true)}
            title="Menu"
            aria-label="Abrir menu"
          >
            <Menu size={20} />
          </button>
          <h1 className="min-w-0 flex-1 truncate text-base font-bold tracking-[-0.02em] text-slate-900 sm:flex-none sm:text-lg">
            {route?.def.title ?? "ERP"}
          </h1>
          <div className="ml-auto flex flex-none items-center gap-1.5 sm:gap-3">
            <a
              href="#/manual"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-2 text-sm font-medium text-slate-600 hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
              title="Consultar manual e atalhos"
              aria-label="Abrir manual do sistema"
            >
              <CircleHelp size={17} />
              <span className="hidden lg:inline">Ajuda</span>
            </a>
            <button
              onClick={() => toggleCart()}
              aria-label="Abrir carrinho"
              className="relative rounded-lg border border-slate-200 p-2 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
              title="Carrinho"
            >
              <ShoppingCart size={18} />
              {cartCount > 0 ? (
                <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-semibold text-white">
                  {cartCount}
                </span>
              ) : null}
            </button>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700 ring-2 ring-white">
                {(usuario?.nome || "?").charAt(0).toUpperCase()}
              </div>
              <span className="hidden max-w-40 truncate text-sm font-medium text-slate-700 sm:inline">{usuario?.nome ?? ""}</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="!px-2 sm:!px-2.5"
              onClick={async () => {
                await sair();
                setAuthed(false);
              }}
              title="Sair"
            >
              <LogOut size={16} /> <span className="hidden sm:inline">Sair</span>
            </Button>
          </div>
        </header>

        <main id="main-content" className="erp-scrollbar flex-1 overflow-auto p-3 sm:p-4 md:p-5 lg:p-6">
          {!rotaLiberada ? (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
              <p className="text-base font-medium text-gray-600">Sem acesso</p>
              <p className="mt-1">Seu perfil não permite visualizar este módulo.</p>
              <Button variant="outline" className="mt-4" onClick={() => (location.hash = "#/dashboard")}>
                Ir para o painel
              </Button>
            </div>
          ) : (
            <RouteErrorBoundary>
              <Suspense fallback={<div className="py-16 text-center text-sm text-gray-400">Carregando…</div>}>
                {route && RouteComponent ? <RouteComponent key={route.m[0]} /> : null}
              </Suspense>
            </RouteErrorBoundary>
          )}
        </main>
      </div>
    </div>
    </>
  );
}
