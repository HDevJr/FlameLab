import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components";
import Enrichment from "./pages/Enrichment";
import Import from "./pages/Import";
import Library from "./pages/Library";
import Result, { RunList } from "./pages/Result";
import Review from "./pages/Review";
import RunPage from "./pages/RunPage";
import Scenario from "./pages/Scenario";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Library />} />
          <Route path="/importar" element={<Import />} />
          <Route path="/documentos/:id/enriquecimento" element={<Enrichment />} />
          <Route path="/experimentos/:id" element={<Review />} />
          <Route path="/experimentos/:id/alterar" element={<Scenario />} />
          <Route path="/simulacao/:scenarioId" element={<RunPage />} />
          <Route path="/execucoes" element={<RunList />} />
          <Route path="/execucoes/:runId" element={<Result />} />
          <Route path="*" element={<p>Página não encontrada. <a href="/">Voltar à biblioteca</a></p>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  </StrictMode>,
);
