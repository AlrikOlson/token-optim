import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./fonts";
import "./tokens.css";
import { App } from "./App";

import { InkBleedDefs } from "./components/InkBleedDefs";
import { DeskMaterial } from "./material/DeskMaterial";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <DeskMaterial />
    <InkBleedDefs />
    <App />
  </StrictMode>,
);
