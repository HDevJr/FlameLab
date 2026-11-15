import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, documentFileUrl, type GuidedAction, type GuidedJourney, type GuidedPreview, type GuidedProposal, type GuidedTask, type ProposalAction, type ResolutionState, type WorkMode } from "./api";
import { Async, Badge, useLoad } from "./components";
import { formatValue } from "./lib";
import StructuredForm, { emptyPayload, syntheticPayload, toWire, type Payload } from "./StructuredForm";
import { ChecksList, Flags, MaturityLadder, RequirementsTable, Stages, TIER_TONE } from "./RequirementsPanel";
import { useWorkMode } from "./workMode";

export const RESOLUTION_LABEL: Record<ResolutionState,string> = {OPEN:"Ainda não tratada",IN_PROGRESS:"Registro iniciado",SOURCE_SUBMITTED:"Evidência enviada",ASSUMPTION_PROPOSED:"Hipótese proposta",EXPLORATORY_DRAFT:"Rascunho exploratório não aprovado",UNDER_REVIEW:"Aguardando revisão e avaliação do perfil",RESOLVED_FOR_PROFILE:"Satisfeita para este perfil",BLOCKED:"Sem solução permitida no momento"};
const ACTION_LABEL: Record<string,string> = {DRAFT:"Rascunho salvo",SOURCE:"Evidência enviada",ASSUMPTION:"Hipótese proposta",EXPLORATORY_DRAFT:"Rascunho exploratório salvo",NOT_FOUND:"Informação não encontrada",DEFER:"Revisão adiada",REQUEST_REVIEW:"Revisão solicitada",ACCEPT:"Parecer favorável",REJECT:"Parecer com correções"};
const ROLE_LABEL = {CONSTRUCTION_INPUT:"Necessária para construir o modelo",COMPARISON_ONLY:"Só para comparação quantitativa — não é entrada FDS",FIDELITY_CONTEXT:"Limita a fidelidade — não é requisito de construção"} as const;
const SUBMIT_LABEL: Record<ProposalAction,string> = {SOURCE:"Enviar evidência complementar",ASSUMPTION:"Enviar proposta de hipótese",EXPLORATORY_DRAFT:"Salvar rascunho exploratório não aprovado"};
const PROPOSAL_ACTIONS: ProposalAction[] = ["SOURCE","ASSUMPTION","EXPLORATORY_DRAFT"];

export function ModeSwitch() {
  const [mode,setMode]=useWorkMode();
  return <fieldset className="mode-switch"><legend>Modo de trabalho</legend>
    <label><input type="radio" name="flamelab-mode" checked={mode==="SCIENTIFIC"} onChange={()=>setMode("SCIENTIFIC")}/> Modo científico</label>
    <label><input type="radio" name="flamelab-mode" checked={mode==="TEST"} onChange={()=>setMode("TEST")}/> Modo de teste da interface</label>
  </fieldset>;
}

export function TestBanner({mode}:{mode:WorkMode}) {
  if(mode!=="TEST")return null;
  return <p className="test-banner" role="note"><strong>MODO DE TESTE</strong> · dados sintéticos em armazenamento isolado; nada vira dado NASA, fonte bibliográfica ou aprovação científica. Tipos e unidades continuam verificados.</p>;
}

export function ModelReadiness({journey:j,onOpen}:{journey:GuidedJourney;onOpen?:(gap:string)=>void}) {
  const pendingWithGap=j.requirements.filter(r=>r.category==="DATA_INPUT" && !r.satisfied && r.gap_id);
  return <section className="card model-readiness" aria-label="Prontidão do modelo">
    <div className="row"><h3 className="grow">Perfil físico: {j.profile.title_pt}</h3><Badge tone={j.readiness.generator_approved ? "ok":"bad"}>{j.readiness.generator_approved ? "Gerador aprovado":"Gerador sem aprovação"}</Badge></div>
    <TestBanner mode={j.mode}/>
    <p className="box warn">{j.readiness.message_pt}</p>
    <p><strong>{j.summary.gaps_handled} de {j.summary.gaps_total}</strong> pendências tratadas (com evidência, hipótese, rascunho exploratório ou registro de não encontrada) · <strong>{j.summary.requirements_satisfied} de {j.summary.requirements_total}</strong> requisitos de dados satisfeitos para o perfil · Execução {j.readiness.can_execute ? "permitida":"bloqueada"}.</p>
    <p className="detail">Tratar uma pendência não a torna um requisito satisfeito: isso exige revisão independente e um perfil físico implementado e aprovado.</p>
    <p className="box info"><strong>Próximo passo:</strong> {j.next_step.text_pt}{j.next_step.gap_id && onOpen && <> <button onClick={()=>onOpen(j.next_step.gap_id!)}>Abrir esta pendência</button></>}</p>
    <Stages summary={j.summary}/>
    {pendingWithGap.length>0 && <details><summary>Abrir um requisito pendente ({pendingWithGap.length})</summary>
      <ul className="req-links">{pendingWithGap.map(r=><li key={r.parameter}>{onOpen ? <button onClick={()=>onOpen(r.gap_id!)}>{r.label_pt}</button>:<strong>{r.label_pt}</strong>} — {r.tier_pt}. {r.reason_pt}</li>)}</ul></details>}
    <details><summary>Entender requisitos do modelo</summary>
      <p>Satisfeitos: {j.requirements.filter(r=>r.satisfied).map(r=>r.label_pt).join(", ") || "nenhum"}.</p>
      <p>Pendentes: {j.requirements.filter(r=>r.category==="DATA_INPUT" && !r.satisfied).map(r=>r.label_pt).join(", ") || "nenhum"}.</p>
      <p>Verificações físicas adicionais: {j.requirements.filter(r=>r.category==="MODEL_DEVELOPMENT").map(r=>r.label_pt).join(", ") || "consultar o contrato do perfil"}.</p>
      <p>Concluir a revisão documental não aprova o gerador. O caso técnico de propano é independente do M1.</p>
    </details>
  </section>;
}

export function DecisionSummary({journey:j}:{journey:GuidedJourney}) {
  return <details className="card"><summary>Resumo das decisões — {j.summary.gaps_handled} de {j.tasks.length} pendências tratadas · {j.summary.requirements_satisfied} de {j.summary.requirements_total} requisitos satisfeitos</summary>
    <MaturityLadder summary={j.summary}/>
    <p>{j.resolved} pendências satisfeitas para o perfil. {j.summary.gaps_drafts} com rascunho de formulário não enviado; {j.summary.gaps_untouched} ainda não tratadas{j.summary.gaps_test_content ? `; ${j.summary.gaps_test_content} com conteúdo de teste na área científica (não contam)`:""}.</p>
    <ul className="decision-list">{j.tasks.map(t=><li key={t.gap_id}><strong>{t.label_pt}</strong> · <Badge tone={TIER_TONE[t.tier]}>{t.tier_pt}</Badge>
      {t.current?.proposal && <div className="detail">{t.current.normalized?.summary_pt || (t.current.proposal.value !== null ? `${t.current.proposal.value} ${t.current.proposal.unit}`:t.current.proposal.details)} · {t.current.proposal.source} · {t.current.proposal.location} · registrado por {t.current.proposal.author}</div>}
      {t.current?.draft && !t.current.proposal && <div className="detail">Rascunho de formulário de {t.current.draft.author}, ainda não enviado.</div>}
      {t.current?.notes && <p className="detail">{t.current.notes}</p>}
      {t.current?.review_state==="ACCEPTED" && <p className="detail">Parecer favorável registrado; uso ainda depende do perfil.</p>}
    </li>)}</ul>
  </details>;
}

type Form = Record<string,string>;
type State = {form:Form;payload:Payload};
const blank = ():Form => ({action:"",author:"",source:"",location:"",evidence:"",justification:"",limitations:"",basis:"EXTERNAL_LITERATURE",change_reason:"",notes:""});
function payloadFromTask(t:GuidedTask):Payload {
  const p=t.current?.proposal;
  if(p?.structured)return structuredClone(p.structured) as Payload;
  if(p && t.contract.kind==="QUANTITY" && p.value!==null)return {quantity:{value:String(p.value),unit:p.unit}};
  return emptyPayload(t.contract);
}
function initialState(t:GuidedTask, key:string):State {
  let local:State|null=null; try {local=JSON.parse(localStorage.getItem(key) || "null");} catch { /* optional local recovery */ }
  if(local?.form && local.payload)return local;
  const p=t.current?.proposal; const d=t.current?.draft;
  const form={...blank(),...(p ? {author:p.author,source:p.source,location:p.location,evidence:p.evidence,justification:p.justification,limitations:p.limitations,basis:p.basis ?? "EXTERNAL_LITERATURE"}:{}),notes:t.current?.notes ?? ""};
  let payload=payloadFromTask(t);
  if(d){Object.assign(form,Object.fromEntries(Object.entries(d).filter(([k])=>k!=="structured_json")));try{if(d.structured_json)payload=JSON.parse(d.structured_json);}catch{/* rascunho ilegível: mantém o formulário */}}
  return {form,payload};
}

function PathCards({task,action,choose}:{task:GuidedTask;action:string;choose:(a:string)=>void}) {
  const hyp=task.policy.mode;
  const hypAction:ProposalAction=hyp==="DRAFT_ONLY" ? "EXPLORATORY_DRAFT":"ASSUMPTION";
  return <div className="paths" role="group" aria-label="Como resolver esta pendência">
    <div className="path"><button onClick={()=>choose("SOURCE")} aria-pressed={action==="SOURCE"}>Registrar evidência científica</button>
      <small>Para informação encontrada em fonte verificável (referência, página e trecho).</small></div>
    <div className={`path ${hyp==="NOT_AVAILABLE" ? "disabled":""}`}><button disabled={hyp==="NOT_AVAILABLE"} onClick={()=>choose(hypAction)} aria-pressed={action===hypAction}>Preparar hipótese exploratória</button>
      <small>{hyp==="ALLOWED" ? "Monta uma variante com valores declarados; começa sem aprovação.":hyp==="DRAFT_ONLY" ? "Salva somente como rascunho exploratório NÃO APROVADO, que nunca é entrada FDS.":`Indisponível para este perfil. ${task.assumption_reason_pt || ""}`.trim()}</small></div>
    <div className="path"><button onClick={()=>choose("KEEP_OPEN")} aria-pressed={action==="KEEP_OPEN"}>Manter pendência em aberto</button>
      <small>Quando a informação não está disponível ou não há suporte técnico para usá-la.</small></div>
  </div>;
}

function PreviewPanel({preview,error}:{preview:GuidedPreview|null;error:string}) {
  if(error)return <section className="card preview" aria-label="O que será salvo"><h4>O que será salvo</h4><p className="box warn">Validação ao vivo indisponível: {error}. O servidor ainda valida ao enviar.</p></section>;
  if(!preview)return <section className="card preview" aria-label="O que será salvo"><h4>O que será salvo</h4><p className="detail">Validando…</p></section>;
  const required=preview.errors.filter(e=>e.code==="REQUIRED");
  const others=preview.errors.filter(e=>e.code!=="REQUIRED");
  return <section className="card preview" aria-label="O que será salvo" aria-live="polite"><h4>O que será salvo</h4>
    <p><Badge tone={preview.ok ? "info":"warn"}>{preview.ok ? "Pronto para enviar":"Ainda não pode ser enviado"}</Badge> {preview.consequences.saved_as_pt}</p>
    {preview.summary_pt && <p><strong>Conteúdo:</strong> {preview.summary_pt}</p>}
    {preview.conversions.length>0 && <ul className="conversions">{preview.conversions.map(c=><li key={c.field}>{c.label_pt}: {c.original} = <strong>{c.si}</strong></li>)}</ul>}
    {preview.completeness && preview.completeness.missing.length>0 && <p className="box warn">Propriedades ainda ausentes para o modelo escolhido: {preview.completeness.missing_pt.join(", ")}.</p>}
    {others.length>0 && <ul className="field-errors">{others.map((e,i)=><li key={i}>{e.message_pt}</li>)}</ul>}
    {required.length>0 && <p className="detail">Falta preencher: {required.map(e=>e.message_pt.replace(/ é obrigatório\.$/,"").replace(/: mínimo de .*$/,"")).join("; ")}.</p>}
    {preview.warnings.map((w,i)=><p key={i} className="box warn">{w.message_pt}</p>)}
    <p><strong>Requisito:</strong> {preview.consequences.requirement_pt}</p>
    <p><strong>Uso no FDS:</strong> {preview.consequences.fds_use_pt}</p>
    {preview.revises_revision && <p className="detail">Edição do registro da revisão {preview.revises_revision}: {preview.diff.length} campo(s) alterado(s). O registro anterior permanece no histórico.</p>}
    <p className="detail">{preview.consequences.original_pt}</p>
  </section>;
}

function CurrentRecord({task,onEdit}:{task:GuidedTask;onEdit:()=>void}) {
  const c=task.current;
  if(!c?.proposal)return null;
  return <section className="card current-record" aria-label="Registro atual">
    <div className="row"><h4 className="grow">Registro atual</h4>{c.mode==="TEST" && <Badge tone="bad">TESTE</Badge>}<Badge tone={TIER_TONE[task.tier]}>{task.tier_pt}</Badge></div>
    <p><strong>Registro enviado:</strong> {c.normalized?.summary_pt || (c.proposal.value!==null ? `${c.proposal.value} ${c.proposal.unit}`:c.proposal.details)}</p>
    <p className="detail">{c.proposal.source} · {c.proposal.location} · {c.proposal.author} · revisão {c.revision}</p>
    {c.conversions?.map(x=><p key={x.field} className="detail">{x.label_pt}: {x.original} = {x.si}</p>)}
    {c.warnings?.map((w,i)=><p key={i} className="detail">Aviso registrado: {w}</p>)}
    <Flags flags={task.quality_flags}/>
    {task.consequences && <dl className="kv"><dt>O que foi salvo</dt><dd>{task.consequences.saved_as_pt}</dd><dt>Requisito</dt><dd>{task.consequences.requirement_pt}</dd><dt>Uso no FDS</dt><dd>{task.consequences.fds_use_pt}</dd></dl>}
    <details><summary>Evidência complementar registrada</summary><blockquote>{c.proposal.evidence}</blockquote></details>
    <ChecksList checks={task.checks} title="Verificações do registro"/>
    <button onClick={onEdit}>Editar proposta</button>
  </section>;
}

export function GuidedModal({initial,documentId,onClose,onChange,startGap}:{initial:GuidedJourney;documentId?:string|null;onClose:()=>void;onChange:(j:GuidedJourney)=>void;startGap?:string|null}) {
  const mode=initial.mode ?? "SCIENTIFIC";
  const [j,setJ]=useState(initial);
  const [index,setIndex]=useState(Math.max(0,initial.tasks.findIndex(t=>t.gap_id===(startGap ?? initial.cursor))));
  const task=j.tasks[index];
  const keyFor=(t?:GuidedTask)=>`flamelab.guided.${mode}.${j.experiment_id}.${j.profile.model_id}.${t?.gap_id}`;
  const key=keyFor(task);
  const [st,setSt]=useState<State>(()=>task ? initialState(task,key):{form:blank(),payload:{}});
  const form=st.form;
  const [dirty,setDirty]=useState(false); const [busy,setBusy]=useState(false); const [error,setError]=useState("");
  const [status,setStatus]=useState("Registros carregados"); const [reviewer,setReviewer]=useState("");
  const [summary,setSummary]=useState(false);
  const [preview,setPreview]=useState<GuidedPreview|null>(null); const [previewError,setPreviewError]=useState("");
  const dialog=useRef<HTMLDivElement>(null); const closeRef=useRef<()=>void>(()=>{});
  useEffect(()=>{
    const previous=document.activeElement as HTMLElement|null; const overflow=document.body.style.overflow;
    document.body.style.overflow="hidden"; dialog.current?.focus();
    const trap=(e:KeyboardEvent)=>{
      if(e.key==="Escape") {e.preventDefault();closeRef.current();}
      if(e.key!=="Tab") return;
      const focusables=Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input, select, textarea, summary, [tabindex="0"]') ?? []).filter(el=>!el.closest("details:not([open])") || el.tagName==="SUMMARY");
      const first=focusables[0],last=focusables[focusables.length-1];
      if(e.shiftKey && (document.activeElement===first || document.activeElement===dialog.current)){e.preventDefault();last?.focus();}
      else if(!e.shiftKey && document.activeElement===last){e.preventDefault();first?.focus();}
    };
    document.addEventListener("keydown",trap);
    return ()=>{document.removeEventListener("keydown",trap);document.body.style.overflow=overflow;previous?.focus();};
  },[]);
  const proposalAction=PROPOSAL_ACTIONS.includes(form.action as ProposalAction) ? form.action as ProposalAction:null;
  const buildProposal=():GuidedProposal=>{
    const structured=toWire(task.contract,st.payload);
    const q=task.contract.kind==="QUANTITY" ? structured.quantity as {value:number|null;unit:string}|undefined:undefined;
    return {value:q?.value ?? null,unit:q?.unit || "n/a",details:"",structured,source:form.source,location:form.location,evidence:form.evidence,author:form.author,
      justification:form.justification,limitations:form.limitations,basis:form.basis==="ENGINEERING_ASSUMPTION" ? "ENGINEERING_ASSUMPTION":"EXTERNAL_LITERATURE"};
  };
  useEffect(()=>{
    if(!proposalAction || !task)return;
    let alive=true;
    const timer=setTimeout(()=>{
      api.guidedPreview(j.experiment_id,task.gap_id,{action:proposalAction,proposal:buildProposal() as unknown as Record<string,unknown>,change_reason:form.change_reason},j.profile.model_id,mode)
        .then(p=>{if(alive){setPreview(p);setPreviewError("");}}).catch((e:Error)=>{if(alive)setPreviewError(e.message);});
    },300);
    return ()=>{alive=false;clearTimeout(timer);};
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[st,proposalAction,task?.gap_id,j.revision]);
  const adopt=(next:GuidedJourney)=>{setJ(next);onChange(next);return next;};
  const save=(next:State)=>{setSt(next);setStatus("Rascunho neste navegador; ainda não enviado");try {localStorage.setItem(key,JSON.stringify(next));} catch {setStatus("Rascunho em memória; salve antes de sair");}};
  const edit=(field:string,value:string)=>{save({...st,form:{...st.form,[field]:value}});if(field!=="action")setDirty(true);};
  const editPayload=(payload:Payload)=>{save({...st,payload});setDirty(true);};
  const choose=(a:string)=>{setPreview(null);edit("action",a);};
  async function perform(work:()=>Promise<void>){if(busy)return;setBusy(true);setError("");try{await work();}catch(e){setError((e as Error).message);setStatus("Não salvo no servidor");}finally{setBusy(false);}}
  async function draft(){
    if(!dirty)return j;
    if((form.author ?? "").trim().length<2) throw new Error("Informe seu nome para salvar e retomar o rascunho no servidor.");
    const flat=Object.fromEntries(Object.entries(form).filter(([,v])=>v!==""));
    const next=adopt(await api.guidedDecision(j.experiment_id,task.gap_id,{action:"DRAFT",expected_revision:j.revision,author:form.author,draft:{...flat,structured_json:JSON.stringify(st.payload)}},j.profile.model_id,mode));
    setDirty(false);setStatus("Rascunho salvo no servidor");return next;
  }
  async function move(i:number,saveFirst=false){await perform(async()=>{
    const next=saveFirst || dirty ? await draft():j;
    if(i<0 || i>=j.tasks.length) {setSummary(true);return;}
    const updated=adopt(await api.guidedCursor(j.experiment_id,j.tasks[i].gap_id,next.revision,j.profile.model_id,mode));
    setIndex(i);setSt(initialState(updated.tasks[i],keyFor(updated.tasks[i])));setDirty(false);setError("");setPreview(null);
    dialog.current?.querySelector<HTMLElement>(".guided-body")?.scrollTo?.(0,0);
  });}
  async function close(){await perform(async()=>{if(!dirty || (form.author ?? "").trim().length>=2)await draft();onClose();});}
  closeRef.current=()=>{if(!busy)void close();};
  async function submit(action:GuidedAction){await perform(async()=>{
    const review=["REQUEST_REVIEW","ACCEPT","REJECT"].includes(action);
    const isProposal=PROPOSAL_ACTIONS.includes(action as ProposalAction);
    const next=adopt(await api.guidedDecision(j.experiment_id,task.gap_id,{expected_revision:j.revision,action,author:review ? reviewer:form.author,notes:form.notes,
      ...(isProposal ? {proposal:buildProposal(),change_reason:form.change_reason}:{})},j.profile.model_id,mode));
    try{localStorage.removeItem(key);}catch{/* optional local cache */}
    const t=next.tasks[index];
    setSt(initialState(t,key));setDirty(false);setPreview(null);
    setStatus(isProposal ? `Registro salvo no servidor como “${t.tier_pt}” — sem aprovação científica automática`:"Registro salvo no servidor");
  });}
  if(!task)return null;
  const isRevision=!!task.current?.proposal && !!task.current?.normalized;
  const reviewable=["SOURCE_SUBMITTED","ASSUMPTION_PROPOSED","EXPLORATORY_DRAFT"].includes(task.state);
  return <div className="guided-backdrop"><div className={`guided-modal ${mode==="TEST" ? "test-mode":""}`} role="dialog" aria-modal="true" aria-labelledby="guided-title" tabIndex={-1} ref={dialog}>
    <header className="guided-header"><div className="row"><div className="grow"><small>REVISÃO GUIADA{mode==="TEST" ? " · MODO DE TESTE":""}</small><h2 id="guided-title">{j.title}</h2></div><button disabled={busy} onClick={()=>void close()}>Voltar ao resumo</button></div>
      <TestBanner mode={mode}/>
      <div className="row"><strong>Pendência {index+1}/{j.tasks.length}</strong><span>{j.summary.gaps_handled} de {j.tasks.length} tratadas · {j.resolved} satisfeitas para o perfil{j.summary.requirements_total>0 ? ` · ${j.summary.requirements_satisfied}/${j.summary.requirements_total} requisitos de dados`:""}</span></div>
      <progress aria-label="Requisitos de pendências satisfeitos para o perfil" max={j.tasks.length} value={j.resolved}/>
      <details className="tech"><summary>Como ler a barra</summary><p className="detail">A barra mede pendências satisfeitas para o perfil, não telas visitadas nem registros enviados. O perfil físico tem aprovação separada.</p></details>
    </header>
    <div className="guided-body" aria-busy={busy}>
      {error && <p className="box bad" role="alert">{error}</p>}
      {summary ? <><h2>Decisões registradas</h2><DecisionSummary journey={j}/><ModelReadiness journey={j} onOpen={gap=>{const i=j.tasks.findIndex(t=>t.gap_id===gap);setSummary(false);void move(i);}}/><RequirementsTable journey={j}/><button onClick={()=>setSummary(false)}>Voltar à pendência</button><Link className="btn" to={`/experimentos/${j.experiment_id}/preparar`}>Preparar modelo com os registros salvos</Link></> : <>
        <div className="row"><Badge tone={TIER_TONE[task.tier]}>{task.tier_pt}</Badge><Badge tone="muted">{ROLE_LABEL[task.role]}</Badge><Badge tone="muted">{task.contract.kind_pt}</Badge></div>
        <h3>A. O que está faltando?</h3><h2 className="task-title">{task.label_pt}</h2><p>{task.explanation_pt}</p>
        <h3>B. Por que precisamos disso?</h3><p>{task.why_pt}</p>
        <h3>C. O que já sabemos?</h3>
        {task.known.length ? task.known.map(p=><article className="evidence-card" key={p.record_id}><strong>{p.label_pt}: {formatValue(p)}</strong> <Badge tone="ok">Valor do PDF — não é alterado</Badge>
          {p.evidence.map((e,i)=><div key={i}><a href={documentFileUrl(e.document_id ?? documentId ?? "",e.page_pdf ?? undefined)} target="_blank" rel="noreferrer">{e.locator_pt || "Abrir fonte científica"}</a>{e.quote && <details><summary>Trecho da evidência</summary><blockquote>{e.quote}</blockquote></details>}</div>)}
        </article>):<p className="muted">Não há valor diretamente relacionado conferido para esta informação.</p>}
        {documentId && <a href={documentFileUrl(documentId)} target="_blank" rel="noreferrer">Consultar artigo original</a>}
        <h3>D. Como resolver?</h3>
        <CurrentRecord task={task} onEdit={()=>choose(task.current?.proposal_kind ?? "SOURCE")}/>
        <PathCards task={task} action={form.action} choose={choose}/>
        {task.policy.mode!=="NOT_AVAILABLE" && task.assumption_reason_pt && <p className="detail">{task.assumption_reason_pt}</p>}
        {task.policy.mode!=="ALLOWED" && <details><summary>O que falta desenvolver para usar esta informação</summary><ul>{task.policy.development_needed_pt.map(d=><li key={d}>{d}</li>)}</ul></details>}
        {documentId && <Link to={`/documentos/${documentId}/enriquecimento`} target="_blank">Consultar fontes relacionadas disponíveis</Link>}
        {task.possible_sources_pt && <p className="box info">Onde procurar: {task.possible_sources_pt}</p>}
        {!form.action && <p className="detail">As informações anteriores estão preservadas.</p>}
        {proposalAction && <form onSubmit={e=>{e.preventDefault();void submit(proposalAction);}}>
          <div className="form">
            {proposalAction==="EXPLORATORY_DRAFT" && <p className="box warn wide">Rascunho exploratório: será salvo como NÃO APROVADO e nunca poderá ser entrada FDS neste perfil.</p>}
            {mode==="TEST" && <div className="wide"><button type="button" onClick={()=>{save({form:{...form,author:form.author || "Pessoa de teste",source:"TESTE — referência sintética da interface",location:"TESTE — sem página",evidence:"TESTE — evidência sintética para verificar a interface",justification:"TESTE — justificativa sintética",limitations:"TESTE — sem validade científica"},payload:syntheticPayload(task.contract)});setDirty(true);}}>Preencher com valores sintéticos (TESTE)</button></div>}
            <label>Responsável pelo registro<input required minLength={2} value={form.author} onChange={e=>edit("author",e.target.value)}/></label>
            <StructuredForm contract={task.contract} value={st.payload} onChange={editPayload} errors={(preview?.errors ?? []).filter(e=>e.code!=="REQUIRED")} conversions={preview?.conversions ?? []}/>
            <label className="wide">{proposalAction==="SOURCE" ? "Fonte científica ou referência bibliográfica":"Fonte científica ou referência bibliográfica (base da hipótese)"}<input required minLength={10} value={form.source} onChange={e=>edit("source",e.target.value)}/></label>
            <label>Página ou localização<input required minLength={2} value={form.location} onChange={e=>edit("location",e.target.value)}/></label>
            <label className="wide">Evidência da fonte<textarea required minLength={10} value={form.evidence} onChange={e=>edit("evidence",e.target.value)}/></label>
            {proposalAction!=="SOURCE" && <><label>Base da hipótese<select value={form.basis} onChange={e=>edit("basis",e.target.value)}><option value="EXTERNAL_LITERATURE">Literatura externa</option><option value="ENGINEERING_ASSUMPTION">Hipótese de engenharia (sem valor publicado)</option></select></label>
              <label className="wide">Justificativa da hipótese<textarea required minLength={5} value={form.justification} onChange={e=>edit("justification",e.target.value)}/></label><label className="wide">Limites de validade<textarea required minLength={5} value={form.limitations} onChange={e=>edit("limitations",e.target.value)}/></label><p className="wide">Aplicável somente ao perfil {j.profile.title_pt}. Estado inicial: proposta sem aprovação.</p></>}
            {isRevision && <label className="wide">Motivo da alteração (obrigatório: o registro atual já existe e será preservado no histórico)<textarea required minLength={5} value={form.change_reason} onChange={e=>edit("change_reason",e.target.value)}/></label>}
          </div>
          <PreviewPanel preview={preview} error={previewError}/>
          <button className="primary" disabled={busy || (preview!==null && !preview.ok)}>{SUBMIT_LABEL[proposalAction]}</button>
          {preview!==null && !preview.ok && <p className="detail">Envio desabilitado: corrija os itens indicados em “O que será salvo”.</p>}
        </form>}
        {form.action==="KEEP_OPEN" && <section className="card" aria-label="Manter pendência em aberto"><h4>Manter pendência em aberto</h4>
          <label>Responsável pelo registro<input value={form.author} onChange={e=>edit("author",e.target.value)}/></label>
          <label>Motivo e fontes consultadas<textarea value={form.notes} onChange={e=>edit("notes",e.target.value)}/></label>
          <div className="row"><button disabled={busy || form.notes.trim().length<5} onClick={()=>void submit("NOT_FOUND")}>Marcar como não encontrada</button><button disabled={busy || form.notes.trim().length<5} onClick={()=>void submit("DEFER")}>Adiar revisão</button></div>
          {form.notes.trim().length<5 && <p className="detail">Botões desabilitados até registrar onde procurou ou o motivo (mín. 5 caracteres).</p>}
        </section>}
        <h3>E. Qual é o impacto?</h3><p className="box warn">{task.impact_pt}</p>
        <p className="box info"><strong>Próximo passo:</strong> {task.next_step.text_pt}</p>
        {task.current?.proposal && <details className="card"><summary>Revisão independente da proposta</summary><p>Autor: {task.current.proposal.author}. Parecer favorável não aprova o perfil físico.</p><label>Nome de quem registra o parecer<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label>Parecer<textarea value={form.notes} onChange={e=>edit("notes",e.target.value)}/></label>
          <div className="row"><button disabled={busy || !reviewable} onClick={()=>void submit("REQUEST_REVIEW")}>Solicitar revisão</button><button disabled={busy || task.state!=="UNDER_REVIEW"} onClick={()=>void submit("ACCEPT")}>Registrar parecer favorável</button><button disabled={busy || task.state!=="UNDER_REVIEW"} onClick={()=>void submit("REJECT")}>Solicitar correções</button></div>
          {!reviewable && task.state!=="UNDER_REVIEW" && <p className="detail">Solicitar revisão fica disponível depois de enviar uma evidência, hipótese ou rascunho exploratório.</p>}
          {task.state!=="UNDER_REVIEW" && <p className="detail">Parecer favorável e correções ficam disponíveis depois que a revisão for solicitada.</p>}
        </details>}
        <details className="tech big"><summary>Detalhes técnicos e histórico ({task.history.length})</summary><p>Parâmetro: <code>{task.parameter}</code> · Perfil v{j.profile.version} · Contrato {task.contract.kind} v{task.contract.version} ({task.contract.physical_validation})</p><p>Locais já consultados: {task.searched_in?.join("; ") || "ver fonte original"}</p>
          <ol>{task.history.map(h=><li key={h.revision}>{h.mode==="TEST" && "[TESTE] "}{ACTION_LABEL[h.action] ?? h.action} · {h.author} · {new Date(h.at).toLocaleString("pt-BR")} · {h.notes}
            {h.change_reason && <><br/><small>Motivo da alteração: {h.change_reason} (edita a revisão {h.revises_revision})</small></>}
            {h.diff && h.diff.length>0 && <ul className="diff">{h.diff.map((d,i)=><li key={i}><code>{d.field}</code>: {JSON.stringify(d.before)} → {JSON.stringify(d.after)}</li>)}</ul>}
            <br/><small>Versão do caso {h.case_version} · {h.sha256.slice(0,12)}</small></li>)}</ol>
        </details>
      </>}
    </div>
    <footer className="guided-footer">{(busy || status!=="Registros carregados") ? <p role="status" aria-live="polite">{busy ? "Salvando…":status}</p> : <p className="sr-only" role="status" aria-live="polite">{status}</p>}<div className="row"><button disabled={busy || index===0 || summary} onClick={()=>void move(index-1)}>Anterior</button><button disabled={busy || summary} onClick={()=>void move(index+1)}>Próxima</button><button className="primary" disabled={busy || summary} onClick={()=>void move(index+1,true)}>Salvar e continuar</button><button disabled={busy} onClick={()=>void perform(async()=>{await draft();setSummary(!summary);})}>{summary ? "Revisar pendência":"Consultar resumo das decisões"}</button></div></footer>
  </div></div>;
}

export default function GuidedReview({experimentId,documentId,count,showReadiness=true,showRequirements=false,profileId,openSignal=0}:{experimentId:string;documentId?:string|null;count:number;showReadiness?:boolean;showRequirements?:boolean;profileId?:string;openSignal?:number}) {
  const [mode]=useWorkMode();
  const load=useLoad(()=>api.guidedReview(experimentId,profileId,mode),[experimentId,profileId,mode]);
  const [updated,setUpdated]=useState<GuidedJourney|null>(null); const [open,setOpen]=useState(false); const [startGap,setStartGap]=useState<string|null>(null);
  useEffect(()=>{if(openSignal)setOpen(true);},[openSignal]);
  useEffect(()=>{setUpdated(null);},[mode,experimentId,profileId]);
  const candidate=updated ?? load.data;
  const j=candidate && (candidate.mode ?? "SCIENTIFIC")===mode ? candidate:null; // nunca exibir dados de outro modo
  const openAt=(gap:string|null)=>{setStartGap(gap);setOpen(true);};
  return <>
    <ModeSwitch/>
    {count>0 && <button className="primary" onClick={()=>openAt(null)}>{j?.recorded ? "Retomar revisão":`Resolver ${count} pendências`}</button>}
    {load.error && <p className="box bad" role="alert">Não foi possível carregar a revisão: {load.error.message}<button onClick={load.reload}>Tentar novamente</button></p>}
    {j && showReadiness && <><ModelReadiness journey={j} onOpen={openAt}/><DecisionSummary journey={j}/></>}
    {j && showRequirements && <RequirementsTable journey={j} onOpen={openAt}/>}
    {open && <Async state={load}>{()=>j && <GuidedModal key={`${mode}-${startGap ?? ""}`} initial={j} startGap={startGap} documentId={documentId} onChange={setUpdated} onClose={()=>{setOpen(false);setStartGap(null);}}/>}</Async>}
  </>;
}
