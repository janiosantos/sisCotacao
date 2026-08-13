// dom.ts — helpers de UI compartilhados (porta de ui.js).

import { escapeHtml } from "./format";

let toastTimer: ReturnType<typeof setTimeout> | undefined;
let escHandler: ((e: KeyboardEvent) => void) | null = null;

export function toast(msg: string, type: "error" | "success" | "warn" | "" = ""): void {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className = "toast" + (type ? ` toast--${type}` : "");
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 3200);
}

export function openModal(
  innerHtml: string,
  {
    onMount,
    modalClass,
    fecharClickFora = true,
  }: {
    onMount?: (modal: HTMLElement) => void;
    modalClass?: string;
    fecharClickFora?: boolean;
  } = {}
): HTMLElement {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `<div class="modal${modalClass ? " " + modalClass : ""}">${innerHtml}</div>`;
  if (fecharClickFora) {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal();
    });
  }
  escHandler = (e: KeyboardEvent) => {
    if (e.key === "Escape") closeModal();
  };
  window.addEventListener("keydown", escHandler);
  document.body.appendChild(overlay);
  document.body.style.overflow = "hidden";
  const modalEl = overlay.querySelector<HTMLElement>(".modal")!;
  // Fecha/fechar automático: qualquer [data-close] fecha o modal, mesmo que o
  // chamador esqueça de ligar manualmente (bug de modais sem onMount).
  modalEl.querySelectorAll<HTMLElement>("[data-close]").forEach((b) => ((b as HTMLElement).onclick = closeModal));
  if (onMount) onMount(modalEl);
  return overlay;
}

export function closeModal(): void {
  if (escHandler) { window.removeEventListener("keydown", escHandler); escHandler = null; }
  document.querySelectorAll(".modal-overlay").forEach((el) => el.remove());
  document.body.style.overflow = "";
}

export function confirmDialog(message: string): Promise<boolean> {
  return new Promise((resolve) => {
    openModal(
      `<div class="modal-head"><h3>Confirmar</h3></div>
       <p style="font-size:14px;color:var(--ink-soft);">${escapeHtml(message)}</p>
       <div class="modal-actions">
         <button class="btn" data-cancel>Cancelar</button>
         <button class="btn btn--danger" data-ok>Confirmar</button>
       </div>`,
      {
        onMount(modal) {
          modal.querySelector<HTMLButtonElement>("[data-cancel]")!.onclick = () => {
            closeModal();
            resolve(false);
          };
          modal.querySelector<HTMLButtonElement>("[data-ok]")!.onclick = () => {
            closeModal();
            resolve(true);
          };
        },
      }
    );
  });
}