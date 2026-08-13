// App.tsx — shell React do ERP legado (Protheus/TOTVS).
// Desktop cinza + menubar de navegação + janela com titlebar/sidebar por rota.

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import {
  Sidebar,
  SubHeader,
  TitleBar,
  ctrlLetter,
  useGlobalShortcuts,
  type SidebarAction,
} from "./legacy-kit";
import { ROUTES, type PageRenderer, type SidebarActionDef } from "./routes";
import { carregarSessao, entrar, sair, usuarioCorrente } from "./pages/login";
import { startupAuth } from "./auth";
import { countItens, injectOverlay as injectCartOverlay, toggle as toggleCart } from "./cart";

interface NavItem {
  href: string;
  label: string;
}
interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV: NavGroup[] = [
  {
    label: "Vendas",
    items: [
      { href: "#/dashboard", label: "Painel" },
      { href: "#/prevenda", label: "Pré-Venda" },
      { href: "#/catalogo", label: "Catálogo" },
      { href: "#/pdv", label: "PDV" },
      { href: "#/orcamentos", label: "Orçamentos" },
      { href: "#/cotacoes", label: "Cotações" },
      { href: "#/compras", label: "Compras" },
    ],
  },
  {
    label: "Cadastros",
    items: [
      { href: "#/clientes", label: "Clientes" },
      { href: "#/fornecedores", label: "Fornecedores" },
      { href: "#/produtos", label: "Produtos" },
      { href: "#/vendedores", label: "Vendedores" },
      { href: "#/categorias", label: "Categorias" },
      { href: "#/unidades", label: "Unidades" },
      { href: "#/diagnostico-variacoes", label: "Qualidade do catálogo" },
    ],
  },
  {
    label: "Financeiro",
    items: [
      { href: "#/financeiro", label: "Financeiro" },
      { href: "#/precos", label: "Preços" },
      { href: "#/bancos", label: "Bancos" },
      { href: "#/plano-contas", label: "Plano de contas" },
    ],
  },
  {
    label: "Logística",
    items: [
      { href: "#/estoque", label: "Estoque" },
      { href: "#/fiscal", label: "Fiscal" },
    ],
  },
  {
    label: "Admin",
    items: [
      { href: "#/posvenda", label: "Pós-venda" },
      { href: "#/solicitacoes", label: "Solic. Compra" },
      { href: "#/historico", label: "Hist. preços" },
      { href: "#/usuarios", label: "Usuários" },
    ],
  },
];

function useHashRoute(): string {
  const [hash, setHash] = useState(() => location.hash || "#/catalogo");
  useEffect(() => {
    const onHash = () => {
      setHash(location.hash || "#/catalogo");
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return hash;
}

function focusSearch(container: HTMLElement | null): void {
  if (!container) return;
  const el = container.querySelector<HTMLElement>(
    'input[type="text"], input:not([type]), input[type="search"], input[type="number"]'
  );
  el?.focus();
}

function LegacyPage({
  title,
  render,
  match,
  actions,
}: {
  title: string;
  render: (el: HTMLElement, m: RegExpMatchArray) => void | Promise<void>;
  match: RegExpMatchArray;
  actions?: SidebarActionDef[];
}) {
  const contentRef = useRef<HTMLDivElement>(null);

  useGlobalShortcuts(
    [{ match: ctrlLetter("q"), label: "Pesquisar (Ctrl+Q)", action: () => focusSearch(contentRef.current) }],
    true
  );

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    el.innerHTML = "";
    Promise.resolve(render(el, match)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sidebarActions: SidebarAction[] = (actions || []).map((a) => ({
    icon: a.icon,
    label: a.label,
    shortcut: a.shortcut,
    onAction: a.action,
  }));

  return (
    <div className="lg-window">
      <TitleBar title={title} />
      <SubHeader
        title={title}
        meta={<span>Controle <b>PENDENTE</b></span>}
      />
      <div className="lg-body">
        <div className="lg-content" ref={contentRef} />
        <Sidebar brand="Sistema ERP" subBrand="GESTÃO COMERCIAL" actions={sidebarActions} />
      </div>
    </div>
  );
}

function LoadingWindow({ title }: { title: string }) {
  return (
    <div className="lg-window">
      <TitleBar title={title} />
      <div className="lg-content lg-hint">Carregando…</div>
    </div>
  );
}

function LazyVanillaPage({
  title,
  load,
  match,
  actions,
}: {
  title: string;
  load: () => Promise<PageRenderer>;
  match: RegExpMatchArray;
  actions?: SidebarActionDef[];
}) {
  const [renderFn, setRenderFn] = useState<PageRenderer | null>(null);

  useEffect(() => {
    let alive = true;
    load()
      .then((fn) => {
        if (alive) setRenderFn(() => fn);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!renderFn) return <LoadingWindow title={title} />;
  return <LegacyPage title={title} render={renderFn} match={match} actions={actions} />;
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
    <div className="lg-window" style={{ margin: "auto", maxWidth: 480, maxHeight: 320 }}>
      <TitleBar title="Acesso ao sistema" />
      <div className="login-box" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ fontSize: 14, fontWeight: 700 }}>Entre com seu usuário</div>
        <div>
          <div className="lg-fieldbox-label" style={{ marginBottom: 2 }}>Login</div>
          <input
            id="lgLogin"
            ref={loginRef}
            className="lg-input"
            style={{ width: "100%" }}
            value={login}
            autoComplete="username"
            onChange={(e) => setLogin(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void tentar()}
          />
        </div>
        <div>
          <div className="lg-fieldbox-label" style={{ marginBottom: 2 }}>Senha</div>
          <input
            id="lgSenha"
            className="lg-input"
            style={{ width: "100%" }}
            type="password"
            value={senha}
            autoComplete="current-password"
            onChange={(e) => setSenha(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void tentar()}
          />
        </div>
        <button id="lgEntrar" className="lg-btn lg-btn--primary" onClick={() => void tentar()}>
          Entrar
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const hash = useHashRoute();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [openMenu, setOpenMenu] = useState<number | null>(null);
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
    if (authed && !route && hash !== "#/catalogo") {
      location.hash = "#/catalogo";
    }
  }, [authed, route, hash]);

  if (authed === null) {
    return <div className="lg-desktop" />;
  }

  if (!authed) {
    return (
      <div className="lg-desktop" style={{ alignItems: "center", justifyContent: "center" }}>
        <LoginScreen onLogin={() => setAuthed(true)} />
      </div>
    );
  }

  const usuario = usuarioCorrente();

  const RouteComponent = route?.def.component ?? null;

  return (
    <div className="lg-desktop">
      <nav className="lg-menubar" id="mainNav">
        <span className="lg-brand">◆ ERP COMERCIAL</span>
        {NAV.map((g, i) => (
          <div className={`lg-menu${openMenu === i ? " is-open" : ""}`} key={g.label}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setOpenMenu(openMenu === i ? null : i);
              }}
            >
              {g.label}
            </button>
            {openMenu === i ? (
              <div className="lg-menu-dropdown">
                {g.items.map((it) => {
                  const active = hash === it.href || hash.startsWith(it.href + "/");
                  return (
                    <a
                      key={it.href}
                      href={it.href}
                      data-route={it.href.slice(2)}
                      className={active ? "is-active" : ""}
                      onClick={() => setOpenMenu(null)}
                    >
                      <span>{it.label}</span>
                    </a>
                  );
                })}
              </div>
            ) : null}
          </div>
        ))}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <button className="lg-btn" style={{ padding: "3px 10px", fontSize: 12 }} onClick={() => toggleCart()}>
            🛒 {cartCount}
          </button>
          <span style={{ fontSize: 12 }}>{usuario?.nome ?? ""}</span>
          <button
            className="lg-btn"
            style={{ padding: "3px 10px", fontSize: 12 }}
            onClick={async () => {
              await sair();
              setAuthed(false);
            }}
          >
            Sair
          </button>
        </div>
      </nav>

      {route ? (
        <Suspense fallback={<LoadingWindow title={route.def.title} />}>
          {RouteComponent ? (
            <RouteComponent key={route.m[0]} />
          ) : route.def.loader ? (
            <LazyVanillaPage
              key={route.m[0]}
              title={route.def.title}
              load={route.def.loader}
              match={route.m}
              actions={route.def.actions}
            />
          ) : null}
        </Suspense>
      ) : null}
    </div>
  );
}
