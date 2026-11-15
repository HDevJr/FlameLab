// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { api, type Analysis, type GuidedJourney } from "./api";
import GuidedReview, { GuidedModal } from "./GuidedReview";
import { AnalysisSummary } from "./pages/Analysis";
import payload from "./fixtures/guided_review_m1.json";

afterEach(()=>{cleanup();vi.restoreAllMocks();localStorage.clear();});
const fixture=()=>structuredClone(payload) as unknown as GuidedJourney;
function mockServer(){
  let data=fixture();
  vi.spyOn(api,"guidedReview").mockImplementation(async()=>structuredClone(data));
  const save=vi.spyOn(api,"guidedDecision").mockImplementation(async(_id,gap,req)=>{
    expect(req.expected_revision).toBe(data.revision);
    data=structuredClone(data);data.revision++;
    const t=data.tasks.find(t=>t.gap_id===gap)!;
    t.state=req.action==="SOURCE" ? "SOURCE_SUBMITTED":req.action==="ASSUMPTION" ? "ASSUMPTION_PROPOSED":"IN_PROGRESS";
    t.current={revision:data.revision,action:req.action,state:t.state,at:"2026-11-15T12:00:00Z",sha256:"hash",proposal:req.proposal,draft:req.draft,author:req.author};
    data.recorded=data.tasks.filter(t=>t.current).length;
    return structuredClone(data);
  });
  const cursor=vi.spyOn(api,"guidedCursor").mockImplementation(async(_id,gap,revision)=>{
    expect(revision).toBe(data.revision);data=structuredClone(data);data.revision++;data.cursor=gap;return structuredClone(data);
  });
  return {save,cursor};
}
async function open(){
  render(<MemoryRouter><GuidedReview experimentId="BASS2-M1" documentId="NASA-TM-20210011385" count={12}/></MemoryRouter>);
  await screen.findByText(/Gerador sem aprovação/);
  fireEvent.click(screen.getByRole("button",{name:"Resolver 12 pendências"}));
  const modal=await screen.findByRole("dialog");
  fireEvent.click(within(modal).getByRole("button",{name:"Registrar informação científica"}));
  return modal;
}
function fill(label:string,value:string){fireEvent.change(screen.getByLabelText(label),{target:{value}});}

it("abre direto no resumo, com nove conferidos e uma pendência por etapa",async()=>{
  mockServer();
  const a={totals:{experiments:1,parameters:9,reviewed:9,pending:0,gaps:12},document:{document_id:"NASA-TM-20210011385"},provenance:{state:"VERIFIED",label_pt:"NASA verificada",reasons_pt:[]},coverage:{summary_pt:"Dataset curado"},sources:[],not_validated_pt:[],experiments:[{experiment_id:"BASS2-M1",label:"M1",reviewed:9,gaps:12,fds:{can_simulate:false,reasons_pt:[]}}]} as unknown as Analysis;
  render(<MemoryRouter><AnalysisSummary a={a}/></MemoryRouter>);
  await screen.findByText(/Gerador sem aprovação/);
  expect(screen.getByText(/9 parâmetros conferidos/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Resolver 12 pendências"}));
  const modal=await screen.findByRole("dialog");
  expect(within(modal).getByText("Pendência 1/12")).toBeTruthy();
  expect(within(modal).getByRole("heading",{name:"Comprimento da amostra"})).toBeTruthy();
  expect(within(modal).queryByRole("heading",{name:"Dimensões efetivas do duto"})).toBeNull();
  for(const title of ["A. O que está faltando?","B. Por que precisamos disso?","C. O que já sabemos?","D. Como resolver?","E. Qual é o impacto?"])expect(within(modal).getByText(title)).toBeTruthy();
  expect(within(modal).getAllByRole("link").some(a=>a.getAttribute("href")?.includes("#page="))).toBe(true);
  expect(within(modal).getByRole("progressbar").getAttribute("value")).toBe("0");
});

it("salva rascunho ao navegar, retorna com valor e retoma o cursor após encerrar",async()=>{
  const {save,cursor}=mockServer();await open();
  fill("Responsável pelo registro","Pessoa Autora");fill("Valor","15");fill("Unidade","cm");
  fireEvent.click(screen.getByRole("button",{name:"Salvar e continuar"}));
  await screen.findByText("Pendência 2/12");
  expect(save).toHaveBeenCalledWith("BASS2-M1",fixture().tasks[0].gap_id,expect.objectContaining({action:"DRAFT",draft:expect.objectContaining({value:"15",unit:"cm"})}),fixture().profile.model_id);
  fireEvent.click(screen.getByRole("button",{name:"Anterior"}));await screen.findByText("Pendência 1/12");
  expect((screen.getByLabelText("Valor") as HTMLInputElement).value).toBe("15");
  fireEvent.click(screen.getByRole("button",{name:"Próxima"}));await screen.findByText("Pendência 2/12");
  fireEvent.click(screen.getByRole("button",{name:"Voltar ao resumo"}));
  await waitFor(()=>expect(screen.queryByRole("dialog")).toBeNull());
  fireEvent.click(screen.getByRole("button",{name:"Retomar revisão"}));
  await screen.findByText("Pendência 2/12");expect(cursor).toHaveBeenCalledTimes(3);
});

it("envia fonte complementar sem marcar como resolvida ou habilitar o modelo",async()=>{
  const {save}=mockServer();const modal=await open();
  fill("Responsável pelo registro","Pessoa Autora");fill("Valor","15");fill("Unidade","cm");
  fill("Fonte científica ou referência bibliográfica","Referência científica completa para o ensaio");fill("Página ou localização","p. 55");fill("Evidência da fonte","Trecho que identifica explicitamente o comprimento de M1");
  fireEvent.click(screen.getByRole("button",{name:"Enviar evidência complementar"}));
  await within(modal).findByText("Evidência enviada");
  expect(save).toHaveBeenCalledWith("BASS2-M1",fixture().tasks[0].gap_id,expect.objectContaining({action:"SOURCE",proposal:expect.objectContaining({value:15,unit:"cm",author:"Pessoa Autora"})}),fixture().profile.model_id);
  expect(within(modal).getByRole("progressbar").getAttribute("value")).toBe("0");
  expect(screen.getByText(/Os dados podem ser preparados/)).toBeTruthy();
});

it("explica a proibição de hipóteses para pirólise antes do preenchimento",()=>{
  const j=fixture();j.cursor=j.tasks[8].gap_id;
  render(<MemoryRouter><GuidedModal initial={j} onChange={()=>{}} onClose={()=>{}}/></MemoryRouter>);
  expect(screen.getByText("Pendência 9/12")).toBeTruthy();
  expect((screen.getByRole("button",{name:"Propor hipótese exploratória"}) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText(/falta contrato físico validado/)).toBeTruthy();
  expect(screen.queryByLabelText("Valor")).toBeNull();
  fireEvent.click(screen.getByRole("button",{name:"Registrar informação científica"}));
  expect(screen.getByText(/validação física especializada/)).toBeTruthy();
});

it("falha ao salvar mantém os dados e a etapa, com erro legível",async()=>{
  mockServer();vi.mocked(api.guidedDecision).mockRejectedValue(new Error("Conexão indisponível; tente novamente"));await open();
  fill("Responsável pelo registro","Pessoa Autora");fill("Valor","15");
  fireEvent.click(screen.getByRole("button",{name:"Próxima"}));
  await screen.findByRole("alert");expect(screen.getByText("Pendência 1/12")).toBeTruthy();
  expect((screen.getByLabelText("Valor") as HTMLInputElement).value).toBe("15");
});

it("encerrar sem autor preserva o rascunho local e permite fechar pelo teclado",async()=>{
  mockServer();await open();fill("Valor","15");
  fireEvent.keyDown(document,{key:"Escape"});await waitFor(()=>expect(screen.queryByRole("dialog")).toBeNull());
  fireEvent.click(screen.getByRole("button",{name:"Resolver 12 pendências"}));await screen.findByRole("dialog");
  expect((screen.getByLabelText("Valor") as HTMLInputElement).value).toBe("15");
});

it("hipótese exige referência, justificativa e limites antes do envio",async()=>{
  mockServer();await open();fireEvent.click(screen.getByRole("button",{name:"Propor hipótese exploratória"}));
  const reference=screen.getByLabelText("Fonte científica ou referência bibliográfica") as HTMLInputElement;
  expect(reference.required && !reference.checkValidity()).toBe(true);
  for(const name of ["Justificativa da hipótese","Limites de validade"]){
    const input=screen.getByLabelText(name) as HTMLTextAreaElement;
    expect(input.required && !input.checkValidity()).toBe(true);
  }
  expect(screen.getByText(/Estado inicial: proposta sem aprovação/)).toBeTruthy();
});

it("lacuna de comparação é exibida sem ser promovida a entrada do modelo",()=>{
  const j=fixture();j.cursor=j.tasks[10].gap_id;
  render(<MemoryRouter><GuidedModal initial={j} onChange={()=>{}} onClose={()=>{}}/></MemoryRouter>);
  expect(screen.getByText(/Impede comparação quantitativa; não é uma entrada de execução/)).toBeTruthy();
  expect(screen.getByRole("progressbar").getAttribute("value")).toBe("0");
});

it("recusa de revisão independente mantém proposta e apresenta o motivo",async()=>{
  const j=fixture();j.tasks[0].state="UNDER_REVIEW";
  j.tasks[0].current={action:"REQUEST_REVIEW",state:"UNDER_REVIEW",at:"2026-11-15",revision:1,sha256:"hash",proposal:{value:15,unit:"cm",source:"Fonte científica",location:"p. 55",evidence:"Trecho da fonte científica",author:"Pessoa Autora",details:"",justification:"",limitations:""}};
  vi.spyOn(api,"guidedDecision").mockRejectedValue(new Error("A revisão deve ser feita por outra pessoa, independente do autor."));
  render(<MemoryRouter><GuidedModal initial={j} onChange={()=>{}} onClose={()=>{}}/></MemoryRouter>);
  fireEvent.click(screen.getByText("Revisão independente da proposta"));
  fill("Nome de quem registra o parecer","Pessoa Autora");fill("Parecer","Conferi as evidências na fonte");
  fireEvent.click(screen.getByRole("button",{name:"Registrar parecer favorável"}));
  await screen.findByRole("alert");expect(screen.getByText(/A revisão deve ser feita por outra pessoa/)).toBeTruthy();
  expect(screen.getByRole("progressbar").getAttribute("value")).toBe("0");
});
