// App.tsx — shell do ERP (sidebar + topbar + conteúdo) em React + Tailwind.

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  FileText,
  Gavel,
  ShoppingBag,
  Users,
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
  Receipt,
  RotateCcw,
  ClipboardList,
  History,
  ShieldCheck,
  Settings,
  LogOut,
  type LucideIcon,
} from "lucide-react";
import { ROUTES } from "./routes";
import { carregarSessao, entrar, sair, usuarioCorrente } from "./pages/login";
import { startupAuth } from "./auth";
import { countItens, injectOverlay as injectCartOverlay, toggle as toggleCart } from "./cart";
import { Button } from "./ui/ui";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}
interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV: NavGroup[] = [
  {
    label: "Vendas",
    items: [
      { href: "#/dashboard", label: "Painel", icon: LayoutDashboard },
      { href: "#/catalogo", label: "Catálogo", icon: Package },
      { href: "#/pre-venda", label: "Pré-venda", icon: ShoppingCart },
      { href: "#/orcamentos", label: "Orçamentos", icon: FileText },
      { href: "#/cotacoes", label: "Cotações", icon: Gavel },
      { href: "#/compras", label: "Compras", icon: ShoppingBag },
    ],
  },
  {
    label: "Cadastros",
    items: [
      { href: "#/clientes", label: "Clientes", icon: Users },
      { href: "#/fornecedores", label: "Fornecedores", icon: Truck },
      { href: "#/produtos", label: "Produtos", icon: Boxes },
      { href: "#/vendedores", label: "Vendedores", icon: UserCheck },
      { href: "#/categorias", label: "Categorias", icon: Tags },
      { href: "#/unidades", label: "Unidades", icon: Scale },
      { href: "#/diagnostico-variacoes", label: "Qualidade", icon: SearchCheck },
    ],
  },
  {
    label: "Financeiro",
    items: [
      { href: "#/financeiro", label: "Financeiro", icon: Wallet },
      { href: "#/caixa", label: "Caixa", icon: Banknote },
      { href: "#/precos", label: "Preços", icon: DollarSign },
      { href: "#/bancos", label: "Bancos", icon: Landmark },
      { href: "#/plano-contas", label: "Plano de contas", icon: BookOpen },
    ],
  },
  {
    label: "Logística",
    items: [
      { href: "#/estoque", label: "Estoque", icon: Warehouse },
      { href: "#/fiscal", label: "Fiscal", icon: Receipt },
    ],
  },
  {
    label: "Admin",
    items: [
      { href: "#/posvenda", label: "Pós-venda", icon: RotateCcw },
      { href: "#/solicitacoes", label: "Solic. Compra", icon: ClipboardList },
      { href: "#/historico", label: "Hist. preços", icon: History },
      { href: "#/usuarios", label: "Usuários", icon: ShieldCheck },
      { href: "#/configuracoes", label: "Configurações", icon: Settings },
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
    <div className="flex min-h-screen items-center justify-center bg-gray-100 px-4">
      <div className="login-box w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
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
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
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
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
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
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const hash = useHashRoute();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [cartCount, setCartCount] = useState(0);

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
      if (!ok) startupAuth();
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

  useEffect(() => {
    if (authed && !route && hash !== "#/dashboard") {
      location.hash = "#/dashboard";
    }
  }, [authed, route, hash]);

  if (authed === null) {
    return <div className="min-h-screen bg-gray-100" />;
  }

  if (!authed) {
    return <LoginScreen onLogin={() => setAuthed(true)} />;
  }

  const usuario = usuarioCorrente();
  const RouteComponent = route?.def.component ?? null;

  return (
    <div className="flex h-screen overflow-hidden bg-gray-100">
      {/* Sidebar */}
      <aside className="flex w-60 flex-none flex-col border-r border-gray-200 bg-white">
        <div className="flex h-16 items-center gap-2 border-b border-gray-200 px-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
            <ShoppingBag size={18} />
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight text-gray-900">ERP Comercial</div>
            <div className="text-[11px] text-gray-400">Gestão de varejo</div>
          </div>
        </div>
        <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
          {NAV.map((g) => (
            <div key={g.label}>
              <div className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                {g.label}
              </div>
              <div className="space-y-0.5">
                {g.items.map((it) => {
                  const active = isActive(hash, it.href);
                  const Icon = it.icon;
                  return (
                    <a
                      key={it.href}
                      href={it.href}
                      className={`flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm font-medium ${
                        active
                          ? "bg-brand-50 text-brand-700"
                          : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                      }`}
                    >
                      <Icon size={16} className={active ? "text-brand-600" : "text-gray-400"} />
                      {it.label}
                    </a>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      {/* Conteúdo */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 flex-none items-center gap-4 border-b border-gray-200 bg-white px-6">
          <h1 className="text-lg font-semibold text-gray-900">{route?.def.title ?? "ERP"}</h1>
          <div className="ml-auto flex items-center gap-3">
            <button
              onClick={() => toggleCart()}
              className="relative rounded-md border border-gray-200 p-2 text-gray-600 hover:bg-gray-50"
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
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
                {(usuario?.nome || "?").charAt(0).toUpperCase()}
              </div>
              <span className="text-sm text-gray-700">{usuario?.nome ?? ""}</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                await sair();
                setAuthed(false);
              }}
            >
              <LogOut size={16} /> Sair
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6">
          <Suspense fallback={<div className="py-16 text-center text-sm text-gray-400">Carregando…</div>}>
            {route && RouteComponent ? <RouteComponent key={route.m[0]} /> : null}
          </Suspense>
        </main>
      </div>
    </div>
  );
}
