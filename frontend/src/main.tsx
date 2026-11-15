import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components";
import AnalysisPage from "./pages/Analysis";
import AuditPage from "./pages/Audit";
import DemoFds from "./pages/DemoFds";
import Enrichment from "./pages/Enrichment";
import Import from "./pages/Import";
import Library from "./pages/Library";
import Result, { RunList } from "./pages/Result";
import Review from "./pages/Review";
import RunPage from "./pages/RunPage";
import Scenario from "./pages/Scenario";
import Prepare from "./pages/Prepare";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Library />} />
          <Route path="/importar" element={<Import />} />
          <Route path="/documentos/:id/analise" element={<AnalysisPage />} />
          <Route path="/documentos/:id/enriquecimento" element={<Enrichment />} />
          <Route path="/experimentos/:id" element={<Review />} />
          <Route path="/experimentos/:id/alterar" element={<Scenario />} />
          <Route path="/experimentos/:id/preparar" element={<Prepare />} />
          <Route path="/preparar-simulacao" element={<Prepare />} />
          <Route path="/demonstracao-fds" element={<DemoFds />} />
          <Route path="/simulacao/:scenarioId" element={<RunPage />} />
          <Route path="/auditoria" element={<AuditPage />} />
          <Route path="/execucoes" element={<RunList />} />
          <Route path="/execucoes/:runId" element={<Result />} />
          <Route path="*" element={<p>Página não encontrada. <a href="/">Voltar</a></p>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  </StrictMode>,
);
