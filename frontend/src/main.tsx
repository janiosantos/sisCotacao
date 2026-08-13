// main.tsx — bootstrap React (ERP legado).

import { createRoot } from "react-dom/client";
import App from "./App";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("#root não encontrado");

createRoot(rootEl).render(<App />);
