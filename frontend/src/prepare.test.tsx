// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { api, type CaseProfile, type ScientificCase } from "./api";
import Prepare from "./pages/Prepare";
import guidedFixture from "./fixtures/guided_review_m1.json";
import type { GuidedJourney, Experiment } from "./api";

afterEach(()=>{cleanup();vi.restoreAllMocks();});
const profile: CaseProfile={model_id:"fds-integration-simple-fire",version:"1.0.0",title_pt:"Combustão prescrita",approved:true,independent_only:true,limitations:["Sem previsão PMMA"],parameters:[{name:"t_end",label_pt:"Duração",default:5,min:5,max:30,unit:"s"}]};
const saved: ScientificCase={content_sha256:"hash",content:{case_id:"CASE-1",version:1,title:"Teste",profile_id:profile.model_id,profile_version:profile.version,values:{t_end:5,hrrpua:1000,soot_yield:0.01},assumptions:[],label_pt:"Independente"}};
function mount(path="/preparar-simulacao") {
 vi.spyOn(api,"runs").mockResolvedValue([]);
 vi.spyOn(api,"profiles").mockResolvedValue([profile,{...profile,model_id:"pmma",independent_only:false,approved:false}]);
 render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/preparar-simulacao" element={<Prepare/>}/><Route path="/experimentos/:id/preparar" element={<Prepare/>}/></Routes></MemoryRouter>);
}
it("apresenta etapas e defaults com unidade sem associar dados NASA",async()=>{
 mount();await screen.findByText(/Não há dados NASA/);
 expect(screen.getByRole("navigation",{name:"Etapas de preparação"})).toBeTruthy();
 fireEvent.click(screen.getByRole("button",{name:"2. Informações necessárias"}));
 expect(screen.getByText(/Duração: 5 s/)).toBeTruthy();
 fireEvent.click(screen.getByRole("button",{name:"3. Modelo e hipóteses"}));
 expect(screen.getByText(/SOFTWARE_DEFAULT/)).toBeTruthy();
});
it("restaura preparação e bloqueia execução sem revisão",async()=>{
 vi.spyOn(api,"case").mockResolvedValue({state:"EXPLORATORY_READY",blockers:["INDEPENDENT_REVIEW_REQUIRED"],approval:null,case:saved});
 mount("/preparar-simulacao?case=CASE-1&version=1");
 await screen.findByText(/Caso CASE-1/);
 expect((screen.getByRole("button",{name:"Executar caso independente"}) as HTMLButtonElement).disabled).toBe(true);
 expect(screen.getByText(/Revisão independente e aceitação/)).toBeTruthy();
});
it("habilita execução apenas com prontidão devolvida pelo servidor",async()=>{
 vi.spyOn(api,"case").mockResolvedValue({state:"EXECUTION_READY",blockers:[],approval:{},case:saved});
 mount("/preparar-simulacao?case=CASE-1&version=1");
 await waitFor(()=>expect((screen.getByRole("button",{name:"Executar caso independente"}) as HTMLButtonElement).disabled).toBe(false));
});
it("mantém experimento bloqueado e apresenta lacunas da fonte",async()=>{
 vi.spyOn(api,"experiment").mockResolvedValue({experiment_id:"BASS2-M1",label:"M1",document_id:"NASA-TM-20210011385",review:{total:9,reviewed:9,pending:0,gaps:12},gaps:guidedFixture.tasks,parameters:[]} as unknown as Experiment);
 vi.spyOn(api,"guidedReview").mockResolvedValue(guidedFixture as unknown as GuidedJourney);
 mount("/experimentos/BASS2-M1/preparar");await screen.findByText(/Os dados podem ser preparados/);
 expect(screen.getByText(/Gerador sem aprovação/)).toBeTruthy();
 expect(screen.getByRole("button",{name:"Resolver 12 pendências"})).toBeTruthy();
 expect(screen.queryByRole("navigation",{name:"Etapas de preparação"})).toBeNull();
 expect(screen.queryByRole("button",{name:"Executar caso independente"})).toBeNull();
 expect(screen.getByRole("link",{name:/Abrir caso técnico independente/}).getAttribute("href")).toBe("/preparar-simulacao");
 expect((screen.getByRole("button",{name:"Executar simulação deste experimento"}) as HTMLButtonElement).disabled).toBe(true);
});
it("preparação mostra cada requisito com original, proposta e motivo, e abre o requisito no assistente",async()=>{
 const j=structuredClone(guidedFixture) as unknown as GuidedJourney;
 const row=j.requirements.find(r=>r.parameter==="duct_geometry")!;
 row.tier="EVIDENCE_SUBMITTED";row.tier_pt="Evidência complementar submetida";
 row.proposal={revision:4,action:"SOURCE",kind:"SOURCE",state:"SOURCE_SUBMITTED",author:"Pessoa Autora",at:"2026-11-15T12:00:00Z",mode:"SCIENTIFIC",summary_pt:"Forma da seção do duto: Retangular",origin_pt:"Evidência complementar",source:"Relatório complementar"};
 row.reason_pt="Aguardando parecer de outra pessoa.";
 vi.spyOn(api,"experiment").mockResolvedValue({experiment_id:"BASS2-M1",label:"M1",document_id:"NASA-TM-20210011385",review:{total:9,reviewed:9,pending:0,gaps:12},gaps:j.tasks,parameters:[]} as unknown as Experiment);
 vi.spyOn(api,"guidedReview").mockResolvedValue(j);
 vi.spyOn(api,"guidedCursor").mockImplementation(async()=>j);
 mount("/experimentos/BASS2-M1/preparar");
 await screen.findByText("Requisitos do perfil, campo a campo");
 expect(screen.getByText(/Forma da seção do duto: Retangular/)).toBeTruthy();
 expect(screen.getAllByText(/Ausente na fonte publicada/).length).toBeGreaterThan(0);
 expect(screen.getByText("Aguardando parecer de outra pessoa.")).toBeTruthy();
 fireEvent.click(screen.getByRole("button",{name:"Abrir requisito: Dimensões efetivas do duto"}));
 expect(await screen.findByText("Pendência 3/12")).toBeTruthy();
});
