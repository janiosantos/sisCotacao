// ui.js — helpers compartilhados entre as páginas.
const UI = (() => {
  let toastTimer;
  function toast(msg, type = "") {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.className = "toast" + (type ? ` toast--${type}` : "");
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (el.hidden = true), 3200);
  }

  function fmtMoney(v) {
    if (v === null || v === undefined || v === "" || isNaN(Number(v))) return "—";
    return Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso.replace(" ", "T") + "Z");
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  function fmtDateTime(iso) {
    if (!iso) return "—";
    const d = new Date(iso.replace(" ", "T") + "Z");
    return d.toLocaleDateString("pt-BR") + " " + d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }

  function titleCase(s) {
    if (!s) return s;
    return s.toLowerCase().replace(/(^|\s|\/|\()([a-zà-ÿ])/g, (m, sep, c) => sep + c.toUpperCase());
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s == null ? "" : String(s);
    return div.innerHTML;
  }

  function statusLabel(status) {
    return {
      aberta: "Aberta",
      fechada: "Fechada",
      cancelada: "Cancelada",
      pendente: "Pendente",
      analise: "Pronta para Analisar",
      finalizada: "Finalizada",
      respondido: "Respondido",
    }[status] || status;
  }

  function openModal(innerHtml, { onMount, modalClass } = {}) {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `<div class="modal${modalClass ? " " + modalClass : ""}">${innerHtml}</div>`;
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal();
    });
    document.body.appendChild(overlay);
    document.body.style.overflow = "hidden";
    if (onMount) onMount(overlay.querySelector(".modal"));
    return overlay;
  }

  function closeModal() {
    document.querySelectorAll(".modal-overlay").forEach((el) => el.remove());
    document.body.style.overflow = "";
  }

  async function confirmDialog(message) {
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
            modal.querySelector("[data-cancel]").onclick = () => {
              closeModal();
              resolve(false);
            };
            modal.querySelector("[data-ok]").onclick = () => {
              closeModal();
              resolve(true);
            };
          },
        }
      );
    });
  }

  return { toast, fmtMoney, fmtDate, fmtDateTime, titleCase, escapeHtml, statusLabel, openModal, closeModal, confirmDialog };
})();
