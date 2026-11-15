// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { api, type Analysis, type GuidedJourney, type GuidedPreview, type Tier } from "./api";
import GuidedReview, { GuidedModal } from "./GuidedReview";
import { AnalysisSummary } from "./pages/Analysis";
import { resetWorkMode } from "./workMode";
import payload from "./fixtures/guided_review_m1.json";

afterEach(()=>{cleanup();vi.restoreAllMocks();localStorage.clear();resetWorkMode();});
const fixture=()=>structuredClone(payload) as unknown as GuidedJourney;
const okPreview=(over:Partial<GuidedPreview>={}):GuidedPreview=>({ok:true,errors:[],warnings:[],conversions:[],summary_pt:"",completeness:null,revises_revision:null,diff:[],
  will_be_state:"SOURCE_SUBMITTED",tier:"EVIDENCE_SUBMITTED",tier_pt:"Evidência complementar submetida",checks:[],mode:"SCIENTIFIC",
  consequences:{saved_as_pt:"Evidência complementar submetida — ainda não revisada.",requirement_pt:"Pode atender ao requisito «Comprimento da amostra»",fds_use_pt:"Não pode ser usado como entrada FDS agora",original_pt:"Os dados publicados e conferidos permanecem inalterados.",pending:[]},...over});
const TIER:Record<string,[Tier,string]>={SOURCE:["EVIDENCE_SUBMITTED","Evidência complementar submetida"],ASSUMPTION:["HYPOTHESIS_PROPOSED","Hipótese computacional proposta"],EXPLORATORY_DRAFT:["EXPLORATORY_DRAFT","Rascunho exploratório não aprovado"]};
function mockServer(start=fixture()){
  let data=start;
  vi.spyOn(api,"guidedReview").mockImplementation(async(_id,_p,mode)=>({...structuredClone(data),mode:mode ?? "SCIENTIFIC"}));
  const preview=vi.spyOn(api,"guidedPreview").mockResolvedValue(okPreview());
  const save=vi.spyOn(api,"guidedDecision").mockImplementation(async(_id,gap,req,_p,mode)=>{
    expect(req.expected_revision).toBe(data.revision);
    data=structuredClone(data);data.revision++;
    const t=data.tasks.find(t=>t.gap_id===gap)!;
    t.state=req.action==="SOURCE" ? "SOURCE_SUBMITTED":req.action==="ASSUMPTION" ? "ASSUMPTION_PROPOSED":req.action==="EXPLORATORY_DRAFT" ? "EXPLORATORY_DRAFT":"IN_PROGRESS";
    [t.tier,t.tier_pt]=TIER[req.action] ?? ["DRAFT","Rascunho de formulário (não enviado)"];
    t.current={revision:data.revision,action:req.action,state:t.state,at:"2026-11-15T12:00:00Z",sha256:"hash",proposal:req.proposal,draft:req.draft,author:req.author,mode:mode ?? "SCIENTIFIC",
      proposal_kind:TIER[req.action] ? req.action as "SOURCE":undefined};
    data.recorded=data.tasks.filter(t=>t.current).length;
    return {...structuredClone(data),mode:mode ?? "SCIENTIFIC"};
  });
  const cursor=vi.spyOn(api,"guidedCursor").mockImplementation(async(_id,gap,revision,_p,mode)=>{
    expect(revision).toBe(data.revision);data=structuredClone(data);data.revision++;data.cursor=gap;return {...structuredClone(data),mode:mode ?? "SCIENTIFIC"};
  });
  return {save,cursor,preview};
}
async function open(path="Registrar evidência científica"){
  render(<MemoryRouter><GuidedReview experimentId="BASS2-M1" documentId="NASA-TM-20210011385" count={12}/></MemoryRouter>);
  await screen.findByText(/Gerador sem aprovação/);
  fireEvent.click(screen.getByRole("button",{name:"Resolver 12 pendências"}));
  const modal=await screen.findByRole("dialog");
  fireEvent.click(within(modal).getByRole("button",{name:path}));
  return modal;
}
function fill(label:string|RegExp,value:string){fireEvent.change(screen.getByLabelText(label),{target:{value}});}
const length=/^Comprimento da amostra/;
function fillProvenance(){
  fill("Responsável pelo registro","Pessoa Autora");
  fill("Fonte científica ou referência bibliográfica","Referência científica completa para o ensaio");fill("Página ou localização","p. 55");fill("Evidência da fonte","Trecho que identifica explicitamente o comprimento de M1");
}
function modalAt(index:number,edit?:(j:GuidedJourney)=>void){
  const j=fixture();j.cursor=j.tasks[index].gap_id;edit?.(j);
  render(<MemoryRouter><GuidedModal initial={j} onChange={()=>{}} onClose={()=>{}}/></MemoryRouter>);
  return j;
}

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
  for(const path of ["Registrar evidência científica","Preparar hipótese exploratória","Manter pendência em aberto"])expect(within(modal).getByRole("button",{name:path})).toBeTruthy();
  expect(within(modal).getAllByRole("link").some(a=>a.getAttribute("href")?.includes("#page="))).toBe(true);
  expect(within(modal).getByRole("progressbar").getAttribute("value")).toBe("0");
  expect(within(modal).getAllByText(/Valor do PDF — não é alterado/).length).toBeGreaterThan(0);
});

it("resumo distingue pendências tratadas de requisitos satisfeitos para execução",async()=>{
  mockServer();
  render(<MemoryRouter><GuidedReview experimentId="BASS2-M1" count={12}/></MemoryRouter>);
  await screen.findByText(/Gerador sem aprovação/);
  expect(screen.getAllByText(/pendências tratadas/).length).toBeGreaterThan(0);
  expect(screen.getByText(/requisitos de dados satisfeitos para o perfil/)).toBeTruthy();
  for(const stage of ["Preparação documental","Construção de hipóteses","Validação do modelo de material","Validação do gerador FDS","Autorização de execução"])expect(screen.getByText(stage)).toBeTruthy();
  expect(screen.getByText(/Tratar uma pendência não a torna um requisito satisfeito/)).toBeTruthy();
});

it("salva rascunho estruturado ao navegar, retorna com valor e retoma o cursor após encerrar",async()=>{
  const {save,cursor}=mockServer();await open();
  fill("Responsável pelo registro","Pessoa Autora");fill(length,"15");fill("Unidade (comprimento)","cm");
  fireEvent.click(screen.getByRole("button",{name:"Salvar e continuar"}));
  await screen.findByText("Pendência 2/12");
  const call=save.mock.calls[0];
  expect(call[2].action).toBe("DRAFT");
  expect(JSON.parse(call[2].draft!.structured_json)).toEqual({quantity:{value:"15",unit:"cm"}});
  fireEvent.click(screen.getByRole("button",{name:"Anterior"}));await screen.findByText("Pendência 1/12");
  fireEvent.click(screen.getByRole("button",{name:"Registrar evidência científica"}));
  expect((screen.getByLabelText(length) as HTMLInputElement).value).toBe("15");
  fireEvent.click(screen.getByRole("button",{name:"Próxima"}));await screen.findByText("Pendência 2/12");
  fireEvent.click(screen.getByRole("button",{name:"Voltar ao resumo"}));
  await waitFor(()=>expect(screen.queryByRole("dialog")).toBeNull());
  fireEvent.click(screen.getByRole("button",{name:"Retomar revisão"}));
  await screen.findByText("Pendência 2/12");expect(cursor).toHaveBeenCalledTimes(3);
});

it("envia evidência estruturada com unidade e mostra o que foi salvo, sem resolver nem habilitar o modelo",async()=>{
  const {save,preview}=mockServer();const modal=await open();
  fillProvenance();fill(length,"15");fill("Unidade (comprimento)","cm");
  await waitFor(()=>expect(preview).toHaveBeenCalled());
  await within(modal).findByText(/Pronto para enviar/);
  expect(within(modal).getByText(/Uso no FDS:/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Enviar evidência complementar"}));
  await within(modal).findByText(/Registro salvo no servidor como “Evidência complementar submetida”/);
  expect(save).toHaveBeenCalledWith("BASS2-M1",fixture().tasks[0].gap_id,expect.objectContaining({action:"SOURCE",proposal:expect.objectContaining({value:15,unit:"cm",author:"Pessoa Autora",structured:{quantity:{value:15,unit:"cm"}}})}),fixture().profile.model_id,"SCIENTIFIC");
  expect(within(modal).getByRole("progressbar").getAttribute("value")).toBe("0");
});

it("validação ao vivo mostra conversão, erro de unidade no campo e explica o envio desabilitado",async()=>{
  const {preview}=mockServer();
  preview.mockResolvedValue(okPreview({ok:false,errors:[{field:"quantity",code:"UNIT_DIMENSION",message_pt:"Comprimento da amostra: “s” é tempo, mas o campo exige comprimento."}],conversions:[]}));
  const modal=await open();
  fill(length,"15");
  expect(await within(modal).findAllByText(/“s” é tempo/)).toHaveLength(2);
  expect((screen.getByRole("button",{name:"Enviar evidência complementar"}) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText(/Envio desabilitado: corrija os itens/)).toBeTruthy();
  preview.mockResolvedValue(okPreview({conversions:[{field:"quantity",label_pt:"Comprimento da amostra",original:"15 cm",si:"0,15 m"}]}));
  fill(length,"15.0");
  expect(await within(modal).findAllByText(/0,15 m/)).not.toHaveLength(0);
  await waitFor(()=>expect((screen.getByRole("button",{name:"Enviar evidência complementar"}) as HTMLButtonElement).disabled).toBe(false));
});

it("pirólise: hipótese vira rascunho exploratório NÃO APROVADO, com formulário de propriedades",()=>{
  vi.spyOn(api,"guidedPreview").mockResolvedValue(okPreview());
  modalAt(8);
  expect(screen.getByText("Pendência 9/12")).toBeTruthy();
  expect(screen.getAllByText(/NÃO APROVADO/).length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button",{name:"Preparar hipótese exploratória"}));
  expect(screen.getByRole("button",{name:"Salvar rascunho exploratório não aprovado"})).toBeTruthy();
  expect(screen.getByText(/O nome do material não determina suas propriedades/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Adicionar linha"}));
  expect(screen.getByText("Linha 1")).toBeTruthy();
  fill(/^Propriedade/,"density");
  expect((screen.getByLabelText(/^Unidade/) as HTMLSelectElement).value).toBe("kg/m³");
});

it("geometria do suporte: campos condicionais, posição x/y/z e sistema de coordenadas",()=>{
  vi.spyOn(api,"guidedPreview").mockResolvedValue(okPreview());
  modalAt(1);
  fireEvent.click(screen.getByRole("button",{name:"Preparar hipótese exploratória"}));
  expect(screen.queryByLabelText(/^Comprimento do suporte/)).toBeNull();
  fill(/^Forma geométrica do suporte/,"flat_plate");
  expect(screen.getByLabelText(/^Comprimento do suporte/)).toBeTruthy();
  expect(screen.getByLabelText(/^Sistema de coordenadas/)).toBeTruthy();
  for(const axis of ["x","y","z"])expect(screen.getAllByLabelText(axis).length).toBeGreaterThan(0);
  expect(screen.getByText(/O nome do material não define propriedades/)).toBeTruthy();
});

it("falha ao salvar mantém os dados e a etapa, com erro legível",async()=>{
  mockServer();vi.mocked(api.guidedDecision).mockRejectedValue(new Error("Conexão indisponível; tente novamente"));await open();
  fill("Responsável pelo registro","Pessoa Autora");fill(length,"15");
  fireEvent.click(screen.getByRole("button",{name:"Próxima"}));
  await screen.findByRole("alert");expect(screen.getByText("Pendência 1/12")).toBeTruthy();
  expect((screen.getByLabelText(length) as HTMLInputElement).value).toBe("15");
});

it("encerrar sem autor preserva o rascunho local e permite fechar pelo teclado",async()=>{
  mockServer();await open();fill(length,"15");
  fireEvent.keyDown(document,{key:"Escape"});await waitFor(()=>expect(screen.queryByRole("dialog")).toBeNull());
  fireEvent.click(screen.getByRole("button",{name:"Resolver 12 pendências"}));await screen.findByRole("dialog");
  expect((screen.getByLabelText(length) as HTMLInputElement).value).toBe("15");
});

it("hipótese exige referência, justificativa e limites antes do envio",async()=>{
  mockServer();await open("Preparar hipótese exploratória");
  const reference=screen.getByLabelText(/^Fonte científica ou referência bibliográfica/) as HTMLInputElement;
  expect(reference.required && !reference.checkValidity()).toBe(true);
  for(const name of ["Justificativa da hipótese","Limites de validade"]){
    const input=screen.getByLabelText(name) as HTMLTextAreaElement;
    expect(input.required && !input.checkValidity()).toBe(true);
  }
  expect(screen.getByLabelText("Base da hipótese")).toBeTruthy();
  expect(screen.getByText(/Estado inicial: proposta sem aprovação/)).toBeTruthy();
});

it("editar uma proposta existente exige motivo e preserva o histórico",async()=>{
  vi.spyOn(api,"guidedPreview").mockResolvedValue(okPreview({revises_revision:3,diff:[{field:"value",before:15,after:16}]}));
  modalAt(0,j=>{j.tasks[0].state="SOURCE_SUBMITTED";j.tasks[0].tier="EVIDENCE_SUBMITTED";j.tasks[0].tier_pt="Evidência complementar submetida";
    j.tasks[0].current={action:"SOURCE",state:"SOURCE_SUBMITTED",at:"2026-11-15",revision:3,sha256:"hash",proposal_kind:"SOURCE",normalized:{kind:"SCALAR",value:.15,unit:"m",physical_validation:"BASIC_DOMAIN_ONLY",summary_pt:"15 cm"},
      proposal:{value:15,unit:"cm",source:"Fonte científica",location:"p. 55",evidence:"Trecho da fonte científica",author:"Pessoa Autora",details:"",justification:"",limitations:"",structured:{quantity:{value:15,unit:"cm"}}}};});
  expect(screen.getByText(/Registro enviado:/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Editar proposta"}));
  expect((screen.getByLabelText(length) as HTMLInputElement).value).toBe("15");
  const reason=screen.getByLabelText(/^Motivo da alteração/) as HTMLTextAreaElement;
  expect(reason.required).toBe(true);
  fill(length,"16");
  expect(await screen.findByText(/Edição do registro da revisão 3: 1 campo/)).toBeTruthy();
});

it("modo de teste: aviso, dados sintéticos tipados e envio isolado",async()=>{
  const {save}=mockServer();
  render(<MemoryRouter><GuidedReview experimentId="BASS2-M1" count={12}/></MemoryRouter>);
  await screen.findByText(/Gerador sem aprovação/);
  fireEvent.click(screen.getByLabelText("Modo de teste da interface"));
  await waitFor(()=>expect(api.guidedReview).toHaveBeenLastCalledWith("BASS2-M1",undefined,"TEST"));
  expect((await screen.findAllByText(/MODO DE TESTE/)).length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button",{name:"Resolver 12 pendências"}));
  const modal=await screen.findByRole("dialog");
  fireEvent.click(within(modal).getByRole("button",{name:"Registrar evidência científica"}));
  fireEvent.click(within(modal).getByRole("button",{name:"Preencher com valores sintéticos (TESTE)"}));
  expect((screen.getByLabelText(length) as HTMLInputElement).value).toBe("1");
  expect((screen.getByLabelText("Unidade (comprimento)") as HTMLSelectElement).value).toBe("m");
  await act(async()=>{await new Promise(r=>setTimeout(r,350));});
  fireEvent.click(within(modal).getByRole("button",{name:"Enviar evidência complementar"}));
  await waitFor(()=>expect(save).toHaveBeenCalled());
  expect(save.mock.calls[0][4]).toBe("TEST");
  expect(save.mock.calls[0][2].proposal?.source).toMatch(/^TESTE/);
});

it("registros legados com conteúdo de teste são sinalizados",()=>{
  modalAt(5,j=>{const t=j.tasks[5];t.state="SOURCE_SUBMITTED";t.tier="TEST_CONTENT";t.tier_pt="Registro com conteúdo de teste (não conta)";
    t.quality_flags=[{code:"TEST_LIKE_CONTENT",severity:"warning",message_pt:"Texto típico de preenchimento de teste na área científica (ex.: “ambiente de teste”)."}];
    t.current={action:"SOURCE",state:"SOURCE_SUBMITTED",at:"2026-11-15",revision:4,sha256:"hash",proposal_kind:"SOURCE",normalized:{kind:"DOCUMENT",details:"Ambiente de teste",physical_validation:"REQUIRES_SPECIALIST_SCHEMA"},
      proposal:{value:null,unit:"n/a",source:"ambiente de teste",location:"pagina 45",evidence:"ambiente de teste",author:"Junior",details:"Ambiente de teste",justification:"",limitations:""}};});
  expect(screen.getAllByText(/Registro com conteúdo de teste/).length).toBeGreaterThan(0);
  expect(screen.getByText(/Texto típico de preenchimento de teste/)).toBeTruthy();
});

it("lacuna de comparação é exibida sem ser promovida a entrada do modelo",()=>{
  modalAt(10);
  expect(screen.getByText(/Impede comparação quantitativa; não é uma entrada de execução/)).toBeTruthy();
  expect(screen.getByText(/Só para comparação quantitativa — não é entrada FDS/)).toBeTruthy();
  expect(screen.getByRole("progressbar").getAttribute("value")).toBe("0");
});

it("manter em aberto explica por que os botões estão desabilitados",()=>{
  modalAt(0);
  fireEvent.click(screen.getByRole("button",{name:"Manter pendência em aberto"}));
  expect((screen.getByRole("button",{name:"Marcar como não encontrada"}) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText(/Botões desabilitados até registrar onde procurou/)).toBeTruthy();
  fill("Motivo e fontes consultadas","Consultei o capítulo 5 e a tese relacionada");
  expect((screen.getByRole("button",{name:"Marcar como não encontrada"}) as HTMLButtonElement).disabled).toBe(false);
});

it("recusa de revisão independente mantém proposta e apresenta o motivo",async()=>{
  vi.spyOn(api,"guidedDecision").mockRejectedValue(new Error("A revisão deve ser feita por outra pessoa, independente do autor."));
  modalAt(0,j=>{j.tasks[0].state="UNDER_REVIEW";
    j.tasks[0].current={action:"REQUEST_REVIEW",state:"UNDER_REVIEW",at:"2026-11-15",revision:1,sha256:"hash",proposal:{value:15,unit:"cm",source:"Fonte científica",location:"p. 55",evidence:"Trecho da fonte científica",author:"Pessoa Autora",details:"",justification:"",limitations:""}};});
  fireEvent.click(screen.getByText("Revisão independente da proposta"));
  fill("Nome de quem registra o parecer","Pessoa Autora");fill("Parecer","Conferi as evidências na fonte");
  fireEvent.click(screen.getByRole("button",{name:"Registrar parecer favorável"}));
  await screen.findByRole("alert");expect(screen.getByText(/A revisão deve ser feita por outra pessoa/)).toBeTruthy();
  expect(screen.getByRole("progressbar").getAttribute("value")).toBe("0");
});
