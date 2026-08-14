// main.tsx — bootstrap React (ERP).

import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("#root não encontrado");

createRoot(rootEl).render(<App />);
