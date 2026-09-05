import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { Barcode, Search, X } from "lucide-react";
import { api, type ProdutoResumo } from "../api/client";
import { fmtMoney } from "./format";
import { produtoDaBuscaRapida, resolverBuscaAoEnter, rotuloProduto } from "./product-search-utils";

interface ProductSearchProps {
  onSelect: (produto: ProdutoResumo) => void;
  selected?: ProdutoResumo | null;
  onClear?: () => void;
  depositoId?: number;
  excludeIds?: number[];
  placeholder?: string;
  ariaLabel?: string;
  autoFocus?: boolean;
  disabled?: boolean;
  clearOnSelect?: boolean;
  className?: string;
}

export function ProductSearch({
  onSelect,
  selected = null,
  onClear,
  depositoId,
  excludeIds = [],
  placeholder = "Bipe ou pesquise por código, descrição ou marca",
  ariaLabel = "Pesquisar produto por código ou descrição",
  autoFocus = false,
  disabled = false,
  clearOnSelect = false,
  className = "",
}: ProductSearchProps) {
  const [query, setQuery] = useState(() => selected ? rotuloProduto(selected) : "");
  const [resultados, setResultados] = useState<ProdutoResumo[]>([]);
  const [ativo, setAtivo] = useState(-1);
  const [carregando, setCarregando] = useState(false);
  const [mensagem, setMensagem] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const requestRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const preservarEdicaoRef = useRef(false);
  const listId = useId();

  useEffect(() => {
    if (!selected && preservarEdicaoRef.current) {
      preservarEdicaoRef.current = false;
      return;
    }
    preservarEdicaoRef.current = false;
    setQuery(selected ? rotuloProduto(selected) : "");
  }, [selected?.id]);

  const filtrar = (itens: ProdutoResumo[]) =>
    itens.filter((item) => !excludeIds.includes(item.id));

  const selecionar = (produto: ProdutoResumo) => {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    onSelect(produto);
    setResultados([]);
    setAtivo(-1);
    setMensagem("");
    setQuery(clearOnSelect ? "" : rotuloProduto(produto));
    if (clearOnSelect) window.setTimeout(() => inputRef.current?.focus(), 0);
  };

  const pesquisarAgora = async (termo: string, selecionarExato: boolean) => {
    const consulta = termo.trim();
    if (!consulta) return;
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    const requestId = ++requestRef.current;
    setCarregando(true);
    setMensagem("");
    try {
      const resposta = await api.buscaRapida(consulta, depositoId, 20);
      if (requestId !== requestRef.current) return;
      const permitidos = resposta.produtos.filter((item) => !excludeIds.includes(item.id));
      if (selecionarExato) {
        const resolvido = resolverBuscaAoEnter(permitidos);
        if (resolvido.produto) {
          selecionar(resolvido.produto);
          return;
        }
        setResultados(resolvido.sugestoes);
        setAtivo(resolvido.sugestoes.length ? 0 : -1);
        setMensagem(resolvido.sugestoes.length ? "" : "Nenhum produto encontrado.");
      } else {
        const itens = filtrar(permitidos.map(produtoDaBuscaRapida));
        setResultados(itens);
        setAtivo(-1);
        setMensagem(itens.length ? "" : "Nenhum produto encontrado.");
      }
    } catch {
      if (requestId === requestRef.current) {
        setResultados([]);
        setAtivo(-1);
        setMensagem("Não foi possível pesquisar. Verifique a conexão e tente novamente.");
      }
    } finally {
      if (requestId === requestRef.current) setCarregando(false);
    }
  };

  useEffect(() => {
    const termo = query.trim();
    const rotuloSelecionado = selected ? rotuloProduto(selected) : "";
    if (!termo || termo === rotuloSelecionado) {
      setResultados([]);
      setAtivo(-1);
      setMensagem("");
      return;
    }
    const requestId = ++requestRef.current;
    setResultados([]);
    timerRef.current = window.setTimeout(() => {
      if (requestId !== requestRef.current) return;
      setCarregando(true);
      void api.buscaRapida(termo, depositoId, 20).then((resposta) => {
        if (requestId !== requestRef.current) return;
        const itens = filtrar(resposta.produtos.map(produtoDaBuscaRapida));
        setResultados(itens);
        setAtivo(-1);
        setMensagem(itens.length ? "" : "Nenhum produto encontrado.");
      }).catch(() => {
        if (requestId === requestRef.current) {
          setResultados([]);
          setMensagem("Não foi possível pesquisar. Verifique a conexão e tente novamente.");
        }
      }).finally(() => {
        if (requestId === requestRef.current) setCarregando(false);
      });
    }, 180);
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [query, depositoId, selected?.id, excludeIds.join(",")]);

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!resultados.length) return;
      event.preventDefault();
      const delta = event.key === "ArrowDown" ? 1 : -1;
      setAtivo((atual) => (atual + delta + resultados.length) % resultados.length);
      return;
    }
    if (event.key === "Home" && resultados.length) {
      event.preventDefault();
      setAtivo(0);
      return;
    }
    if (event.key === "End" && resultados.length) {
      event.preventDefault();
      setAtivo(resultados.length - 1);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      ++requestRef.current;
      setResultados([]);
      setAtivo(-1);
      setMensagem("");
      setQuery(selected ? rotuloProduto(selected) : "");
      return;
    }
    if (event.key !== "Enter") return;
    event.preventDefault();
    if (ativo >= 0 && resultados[ativo]) {
      selecionar(resultados[ativo]);
      return;
    }
    void pesquisarAgora(query, true);
  };

  const limpar = () => {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    ++requestRef.current;
    setQuery("");
    setResultados([]);
    setAtivo(-1);
    setMensagem("");
    preservarEdicaoRef.current = false;
    onClear?.();
    inputRef.current?.focus();
  };

  return (
    <div className={`relative ${className}`}>
      <div className="relative">
        <Barcode className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-brand-600" size={17} aria-hidden="true" />
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setMensagem("");
            if (selected && onClear) {
              preservarEdicaoRef.current = true;
              onClear();
            }
          }}
          onKeyDown={onKeyDown}
          onFocus={() => {
            if (query.trim() && !selected) void pesquisarAgora(query, false);
          }}
          placeholder={placeholder}
          aria-label={ariaLabel}
          aria-autocomplete="list"
          aria-controls={resultados.length ? listId : undefined}
          aria-expanded={resultados.length > 0}
          aria-activedescendant={ativo >= 0 ? `${listId}-${ativo}` : undefined}
          role="combobox"
          autoFocus={autoFocus}
          disabled={disabled}
          className="w-full rounded-md border border-slate-300 bg-white py-2 pl-10 pr-10 text-sm shadow-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 disabled:bg-slate-100"
        />
        {query ? (
          <button type="button" onClick={limpar} aria-label="Limpar produto" className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
            <X size={15} />
          </button>
        ) : (
          <Search className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" size={15} aria-hidden="true" />
        )}
      </div>
      {resultados.length ? (
        <div id={listId} role="listbox" className="absolute z-50 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-slate-200 bg-white p-1 shadow-xl">
          {resultados.map((produto, index) => (
            <button
              id={`${listId}-${index}`}
              key={produto.id}
              type="button"
              role="option"
              aria-selected={index === ativo}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => selecionar(produto)}
              className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left ${index === ativo ? "bg-brand-50 text-brand-900" : "hover:bg-slate-50"}`}
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold">{produto.name}</div>
                <div className="truncate font-mono text-[11px] text-slate-500">{produto.sku || "Sem SKU"}{produto.brand ? ` · ${produto.brand}` : ""}</div>
              </div>
              {produto.price > 0 ? <span className="text-xs font-semibold text-slate-700">{fmtMoney(produto.price)}</span> : null}
            </button>
          ))}
        </div>
      ) : query.trim() && carregando ? (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 shadow-lg" role="status">
          Pesquisando produto…
        </div>
      ) : query.trim() && mensagem ? (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 shadow-lg" role="status">
          {mensagem}
        </div>
      ) : null}
      <p className="mt-1 text-[11px] text-slate-500">Leitor: bipe e Enter. Teclado: ↑↓ para navegar, Enter para selecionar, Esc para limpar.</p>
    </div>
  );
}
