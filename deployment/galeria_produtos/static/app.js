const state = {
  page: 1,
  limit: 48,
  total: 0,
  items: [],
  selected: new Map(),
  token: "",
  returnOrigin: location.origin,
  maxSelection: 12,
};
const basePath = location.pathname.replace(/\/(?:index\.html)?$/, "");
const $ = (id) => document.getElementById(id);

function bootSession() {
  const params = new URLSearchParams(location.search);
  const fromUrl = params.get("session");
  state.returnOrigin = params.get("return_origin") || location.origin;
  const requestedLimit = Number(params.get("max_selection"));
  if (Number.isInteger(requestedLimit) && requestedLimit > 0 && requestedLimit <= 100) {
    state.maxSelection = requestedLimit;
  }
  if (fromUrl) sessionStorage.setItem("siscom-gallery-session", fromUrl);
  state.token = fromUrl || sessionStorage.getItem("siscom-gallery-session") || "";
  params.delete("session");
  params.delete("return_origin");
  history.replaceState(null, "", `${location.pathname}${params.size ? `?${params}` : ""}`);
}

async function api(path) {
  const response = await fetch(`${basePath}/api/${path}`, {
    headers: { Authorization: `Bearer ${state.token}` },
    cache: "no-store",
  });
  if (response.status === 401) {
    $("auth-error").hidden = false;
    throw new Error("Sessão expirada");
  }
  if (!response.ok) throw new Error((await response.json()).error || "Falha ao consultar a galeria");
  return response.json();
}

function addOptions(id, items) {
  const select = $(id);
  for (const item of items) {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = `${item.value} (${item.total})`;
    select.append(option);
  }
}

async function loadFilters() {
  const filters = await api("filters");
  addOptions("category", filters.category);
  addOptions("subcategory", filters.subcategory);
  addOptions("brand", filters.brand);
}

function currentQuery() {
  const params = new URLSearchParams({ page: state.page, limit: state.limit });
  for (const [key, id] of [["q", "query"], ["category", "category"], ["subcategory", "subcategory"], ["brand", "brand"]]) {
    const value = $(id).value.trim();
    if (value) params.set(key, value);
  }
  return params;
}

function updateSelection() {
  const count = state.selected.size;
  $("selection-count").textContent = `${count} selecionada${count === 1 ? "" : "s"}`;
  $("confirm-selection").disabled = count === 0;
}

function toggle(item, card) {
  if (state.selected.has(item.id)) state.selected.delete(item.id);
  else if (state.selected.size < state.maxSelection) state.selected.set(item.id, item);
  else {
    $("selection-count").textContent = `Limite de ${state.maxSelection} imagens atingido`;
    return;
  }
  card.setAttribute("aria-pressed", String(state.selected.has(item.id)));
  updateSelection();
}

function cardFor(item, index) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "card";
  card.dataset.index = String(index);
  card.setAttribute("aria-pressed", String(state.selected.has(item.id)));
  card.setAttribute("aria-label", `Selecionar ${item.product_name}, ${item.brand || "sem marca"}`);

  const image = document.createElement("img");
  image.src = item.media_url;
  image.alt = item.product_name;
  image.loading = "lazy";
  const copy = document.createElement("span");
  copy.className = "card-copy";
  const title = document.createElement("strong");
  title.textContent = item.product_name;
  const meta = document.createElement("small");
  meta.textContent = [item.category, item.subcategory, item.brand].filter(Boolean).join(" · ") || "Sem classificação";
  const check = document.createElement("span");
  check.className = "check";
  check.setAttribute("aria-hidden", "true");
  check.textContent = "✓";
  copy.append(title, meta);
  card.append(image, copy, check);
  card.addEventListener("click", () => toggle(item, card));
  card.addEventListener("keydown", (event) => navigateGrid(event, index));
  return card;
}

function navigateGrid(event, index) {
  const cards = [...document.querySelectorAll(".card")];
  const columns = Math.max(1, Math.round($("gallery").clientWidth / cards[0].clientWidth));
  const moves = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -columns, ArrowDown: columns };
  if (event.key === "Enter" && state.selected.size) {
    event.preventDefault();
    confirmSelection();
    return;
  }
  if (!(event.key in moves)) return;
  event.preventDefault();
  cards[Math.min(cards.length - 1, Math.max(0, index + moves[event.key]))]?.focus();
}

async function loadImages() {
  $("gallery").setAttribute("aria-busy", "true");
  const result = await api(`images?${currentQuery()}`);
  state.items = result.items;
  state.total = result.total;
  const gallery = $("gallery");
  gallery.replaceChildren(...state.items.map(cardFor));
  gallery.setAttribute("aria-busy", "false");
  $("empty").hidden = state.items.length > 0;
  const first = state.total ? (state.page - 1) * state.limit + 1 : 0;
  const last = Math.min(state.total, state.page * state.limit);
  $("result-summary").textContent = `${state.total.toLocaleString("pt-BR")} imagens · exibindo ${first}–${last}`;
  $("page-label").textContent = `Página ${state.page} de ${Math.max(1, Math.ceil(state.total / state.limit))}`;
  $("previous").disabled = state.page <= 1;
  $("next").disabled = state.page * state.limit >= state.total;
}

function confirmSelection() {
  const payload = { type: "siscom-gallery-selection", imageIds: [...state.selected.keys()] };
  if (window.opener) {
    window.opener.postMessage(payload, state.returnOrigin);
    window.close();
    return;
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "selecao-galeria.json";
  link.click();
  URL.revokeObjectURL(link.href);
}

$("filters").addEventListener("submit", (event) => {
  event.preventDefault();
  state.page = 1;
  loadImages().catch((error) => { $("result-summary").textContent = error.message; });
});
$("previous").addEventListener("click", () => { state.page -= 1; loadImages(); });
$("next").addEventListener("click", () => { state.page += 1; loadImages(); });
$("confirm-selection").addEventListener("click", confirmSelection);

bootSession();
Promise.all([loadFilters(), loadImages()]).catch((error) => { $("result-summary").textContent = error.message; });
