import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, documentFileUrl, type GuidedAction, type GuidedJourney, type GuidedProposal, type GuidedTask, type ResolutionState } from "./api";
import { Async, Badge, useLoad } from "./components";
import { formatValue } from "./lib";

export const RESOLUTION_LABEL: Record<ResolutionState,string> = {OPEN:"Ainda não tratada",IN_PROGRESS:"Registro iniciado",SOURCE_SUBMITTED:"Evidência enviada",ASSUMPTION_PROPOSED:"Hipótese proposta",UNDER_REVIEW:"Aguardando revisão e avaliação do perfil",RESOLVED_FOR_PROFILE:"Satisfeita para este perfil",BLOCKED:"Sem solução permitida no momento"};
const ACTION_LABEL: Record<string,string> = {DRAFT:"Rascunho salvo",SOURCE:"Evidência enviada",ASSUMPTION:"Hipótese proposta",NOT_FOUND:"Informação não encontrada",DEFER:"Revisão adiada",REQUEST_REVIEW:"Revisão solicitada",ACCEPT:"Parecer favorável",REJECT:"Parecer com correções"};
const REQUIREMENT_LABEL: Record<string,string> = {material:"Material",thickness:"Espessura",width:"Largura",airflow_velocity:"Velocidade do ar",o2_initial:"Oxigênio inicial",gravity_vector:"Vetor de gravidade",mesh_convergence:"Convergência de malha",reaction_model:"Modelo de reação",material_model_review:"Revisão do modelo de material"};
const reqLabel = (key:string,j:GuidedJourney) => j.tasks.find(t=>t.parameter===key)?.label_pt ?? REQUIREMENT_LABEL[key] ?? "Requisito físico a revisar";

export function ModelReadiness({journey:j}:{journey:GuidedJourney}) {
  return <section className="card model-readiness" aria-label="Prontidão do modelo">
    <div className="row"><h3 className="grow">Perfil físico: {j.profile.title_pt}</h3><Badge tone={j.readiness.generator_approved ? "ok":"bad"}>{j.readiness.generator_approved ? "Gerador aprovado":"Gerador sem aprovação"}</Badge></div>
    <p className="box warn">{j.readiness.message_pt}</p>
    <p><strong>{j.readiness.satisfied.length}</strong> requisitos de dados satisfeitos · <strong>{j.readiness.pending.length}</strong> pendentes · Execução {j.readiness.can_execute ? "permitida":"bloqueada"}.</p>
    <details><summary>Entender requisitos do modelo</summary>
      <p>Satisfeitos: {j.readiness.satisfied.map(k=>reqLabel(k,j)).join(", ") || "nenhum"}.</p>
      <p>Pendentes: {j.readiness.pending.map(k=>reqLabel(k,j)).join(", ") || "nenhum"}.</p>
      <p>Verificações físicas adicionais: {j.readiness.additional.map(k=>reqLabel(k,j)).join(", ") || "consultar o contrato do perfil"}.</p>
      <p>Concluir a revisão documental não aprova o gerador. O caso técnico de propano é independente do M1.</p>
    </details>
  </section>;
}

export function DecisionSummary({journey:j}:{journey:GuidedJourney}) {
  return <details className="card"><summary>Resumo das decisões — {j.recorded} de {j.tasks.length} com registro</summary>
    <p>{j.resolved} satisfeitas para o perfil. Registros enviados continuam sujeitos à revisão independente e às regras físicas.</p>
    <ul className="decision-list">{j.tasks.map(t=><li key={t.gap_id}><strong>{t.label_pt}</strong> · {RESOLUTION_LABEL[t.state]}
      {t.current?.proposal && <div className="detail">{t.current.proposal.value !== null ? `${t.current.proposal.value} ${t.current.proposal.unit}`:t.current.proposal.details} · {t.current.proposal.source} · {t.current.proposal.location} · registrado por {t.current.proposal.author}</div>}
      {t.current?.draft && <div className="detail">Rascunho: {t.current.draft.value || t.current.draft.details || "registro parcial"} {t.current.draft.unit==="n/a" ? "":t.current.draft.unit} · {t.current.draft.author}</div>}
      {t.current?.notes && <p className="detail">{t.current.notes}</p>}
      {t.current?.review_state==="ACCEPTED" && <p className="detail">Parecer favorável registrado; uso ainda depende do perfil.</p>}
    </li>)}</ul>
  </details>;
}

type Form = Record<string,string>;
const empty = (t:GuidedTask):Form => ({action:"",value:"",unit:t.schema.unit,source:"",location:"",evidence:"",author:"",justification:"",limitations:"",details:"",notes:""});
function initialForm(t:GuidedTask, key:string):Form {
  let local:Form|null=null; try {local=JSON.parse(localStorage.getItem(key) || "null");} catch { /* optional local recovery */ }
  const p=t.current?.proposal;
  return {...empty(t),...(p ? {...p,value:p.value===null ? "":String(p.value)}:{}),notes:t.current?.notes ?? "",...t.current?.draft,...local};
}

export function GuidedModal({initial,documentId,onClose,onChange}:{initial:GuidedJourney;documentId?:string|null;onClose:()=>void;onChange:(j:GuidedJourney)=>void}) {
  const [j,setJ]=useState(initial);
  const [index,setIndex]=useState(Math.max(0,initial.tasks.findIndex(t=>t.gap_id===initial.cursor)));
  const task=j.tasks[index];
  const key=`flamelab.guided.${j.experiment_id}.${j.profile.model_id}.${task?.gap_id}`;
  const [form,setForm]=useState<Form>(()=>task ? initialForm(task,key):{});
  const [dirty,setDirty]=useState(false); const [busy,setBusy]=useState(false); const [error,setError]=useState("");
  const [status,setStatus]=useState("Registros carregados"); const [notes,setNotes]=useState(form.notes ?? ""); const [reviewer,setReviewer]=useState("");
  const [summary,setSummary]=useState(false);
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
  const adopt=(next:GuidedJourney)=>{setJ(next);onChange(next);return next;};
  const edit=(field:string,value:string)=>{
    const next={...form,[field]:value};setForm(next);if(field!=="action")setDirty(true);setStatus("Rascunho neste navegador; ainda não enviado");
    try {localStorage.setItem(key,JSON.stringify(next));} catch {setStatus("Rascunho em memória; salve antes de sair");}
  };
  async function perform(work:()=>Promise<void>){if(busy)return;setBusy(true);setError("");try{await work();}catch(e){setError((e as Error).message);setStatus("Não salvo no servidor");}finally{setBusy(false);}}
  async function draft(){
    if(!dirty)return j;
    if((form.author ?? "").trim().length<2) throw new Error("Informe seu nome para salvar e retomar o rascunho no servidor.");
    const next=adopt(await api.guidedDecision(j.experiment_id,task.gap_id,{action:"DRAFT",expected_revision:j.revision,author:form.author,draft:form},j.profile.model_id));
    setDirty(false);setStatus("Rascunho salvo no servidor");return next;
  }
  async function move(i:number,save=false){await perform(async()=>{
    const next=save || dirty ? await draft():j;
    if(i<0 || i>=j.tasks.length) {setSummary(true);return;}
    const updated=adopt(await api.guidedCursor(j.experiment_id,j.tasks[i].gap_id,next.revision,j.profile.model_id));
    const nextForm=initialForm(updated.tasks[i],`flamelab.guided.${j.experiment_id}.${j.profile.model_id}.${updated.tasks[i].gap_id}`);
    setIndex(i);setForm(nextForm);setDirty(false);setNotes(nextForm.notes ?? "");setError("");
    dialog.current?.querySelector<HTMLElement>(".guided-body")?.scrollTo?.(0,0);
  });}
  async function close(){await perform(async()=>{if(!dirty || (form.author ?? "").trim().length>=2)await draft();onClose();});}
  closeRef.current=()=>{if(!busy)void close();};
  async function submit(action:GuidedAction){await perform(async()=>{
    const review=["REQUEST_REVIEW","ACCEPT","REJECT"].includes(action);
    const proposal:GuidedProposal={value:task.schema.kind==="SCALAR" && form.value!=="" ? Number(form.value):null,unit:form.unit,source:form.source,location:form.location,evidence:form.evidence,author:form.author,details:form.details,justification:form.justification,limitations:form.limitations};
    const next=adopt(await api.guidedDecision(j.experiment_id,task.gap_id,{expected_revision:j.revision,action,author:review ? reviewer:form.author,notes,...(action==="SOURCE" || action==="ASSUMPTION" ? {proposal}:{})},j.profile.model_id));
    try{localStorage.removeItem(key);}catch{/* optional local cache */}
    setForm(initialForm(next.tasks[index],key));setDirty(false);setStatus("Registro salvo no servidor — sem aprovação científica automática");
  });}
  if(!task)return null;
  return <div className="guided-backdrop"><div className="guided-modal" role="dialog" aria-modal="true" aria-labelledby="guided-title" tabIndex={-1} ref={dialog}>
    <header className="guided-header"><div className="row"><div className="grow"><small>REVISÃO GUIADA</small><h2 id="guided-title">{j.title}</h2></div><button disabled={busy} onClick={()=>void close()}>Voltar ao resumo</button></div>
      <div className="row"><strong>Pendência {index+1}/{j.tasks.length}</strong><span>{j.recorded} com registro · {j.resolved} satisfeitas para o perfil</span></div>
      <progress aria-label="Requisitos de pendências satisfeitos para o perfil" max={j.tasks.length} value={j.resolved}/>
      <p className="detail">A barra mede requisitos satisfeitos, não telas visitadas. O perfil físico tem aprovação separada.</p>
    </header>
    <div className="guided-body" aria-busy={busy}>
      {error && <p className="box bad" role="alert">{error}</p>}
      {summary ? <><h2>Decisões registradas</h2><DecisionSummary journey={j}/><ModelReadiness journey={j}/><button onClick={()=>setSummary(false)}>Voltar à pendência</button><Link className="btn" to={`/experimentos/${j.experiment_id}/preparar`}>Preparar modelo com os registros salvos</Link></> : <>
        <Badge tone={task.state==="RESOLVED_FOR_PROFILE" ? "ok":task.state==="BLOCKED" ? "bad":"warn"}>{RESOLUTION_LABEL[task.state]}</Badge>
        <h3>A. O que está faltando?</h3><h2 className="task-title">{task.label_pt}</h2><p>{task.explanation_pt}</p>
        <h3>B. Por que precisamos disso?</h3><p>{task.why_pt}</p>
        <h3>C. O que já sabemos?</h3>
        {task.known.length ? task.known.map(p=><article className="evidence-card" key={p.record_id}><strong>{p.label_pt}: {formatValue(p)}</strong>
          {p.evidence.map((e,i)=><div key={i}><a href={documentFileUrl(e.document_id ?? documentId ?? "",e.page_pdf ?? undefined)} target="_blank" rel="noreferrer">{e.locator_pt || "Abrir fonte científica"}</a>{e.quote && <details><summary>Trecho da evidência</summary><blockquote>{e.quote}</blockquote></details>}</div>)}
        </article>):<p className="muted">Não há valor diretamente relacionado conferido para esta informação.</p>}
        {documentId && <a href={documentFileUrl(documentId)} target="_blank" rel="noreferrer">Consultar artigo original</a>}
        <h3>D. Como resolver?</h3>
        <p className="detail">{task.assumption_reason_pt}</p>
        <div className="row"><button onClick={()=>edit("action","SOURCE")} aria-pressed={form.action==="SOURCE"}>Registrar informação científica</button><button disabled={!task.assumption_allowed} onClick={()=>edit("action","ASSUMPTION")} aria-pressed={form.action==="ASSUMPTION"}>Propor hipótese exploratória</button>
          {documentId && <Link to={`/documentos/${documentId}/enriquecimento`} target="_blank">Consultar fontes relacionadas disponíveis</Link>}</div>
        {task.possible_sources_pt && <p className="box info">Onde procurar: {task.possible_sources_pt}</p>}
        {task.current?.proposal && <div className="evidence-card"><strong>Registro enviado: {task.current.proposal.value!==null ? `${task.current.proposal.value} ${task.current.proposal.unit}`:task.current.proposal.details}</strong><p>{task.current.proposal.source} · {task.current.proposal.location} · {task.current.proposal.author}</p><details><summary>Evidência complementar registrada</summary><blockquote>{task.current.proposal.evidence}</blockquote></details></div>}
        {!form.action && <p className="detail">Escolha uma ação para abrir o registro. As informações anteriores estão preservadas.</p>}
        {form.action && <form onSubmit={e=>{e.preventDefault();void submit(form.action as GuidedAction);}}>
          <div className="form">
            <label>Responsável pelo registro<input required minLength={2} value={form.author} onChange={e=>edit("author",e.target.value)}/></label>
            {task.schema.kind==="SCALAR" ? <><label>Valor<input type="number" step="any" required value={form.value} onChange={e=>edit("value",e.target.value)}/></label><label>Unidade<input required value={form.unit} onChange={e=>edit("unit",e.target.value)}/></label></> : <label className="wide">Descrição estruturada do método, geometria ou propriedades<textarea required minLength={10} rows={3} value={form.details} onChange={e=>edit("details",e.target.value)}/><small>Registro documental. A validação física especializada ainda não está implementada; não libera entradas FDS.</small></label>}
            <label className="wide">Fonte científica ou referência bibliográfica<input required minLength={10} value={form.source} onChange={e=>edit("source",e.target.value)}/></label>
            <label>Página ou localização<input required minLength={2} value={form.location} onChange={e=>edit("location",e.target.value)}/></label>
            <label className="wide">Evidência da fonte<textarea required minLength={10} value={form.evidence} onChange={e=>edit("evidence",e.target.value)}/></label>
            {form.action==="ASSUMPTION" && <><label className="wide">Justificativa da hipótese<textarea required minLength={5} value={form.justification} onChange={e=>edit("justification",e.target.value)}/></label><label className="wide">Limites de validade<textarea required minLength={5} value={form.limitations} onChange={e=>edit("limitations",e.target.value)}/></label><p className="wide">Aplicável somente ao perfil {j.profile.title_pt}. Estado inicial: proposta sem aprovação.</p></>}
          </div>
          <button className="primary" disabled={busy}>{form.action==="ASSUMPTION" ? "Enviar proposta de hipótese":"Enviar evidência complementar"}</button>
        </form>}
        <details className="card"><summary>Não encontrei ou preciso adiar</summary>{!form.action && <label>Responsável pelo registro<input value={form.author} onChange={e=>edit("author",e.target.value)}/></label>}<label>Motivo e fontes consultadas<textarea value={notes} onChange={e=>{setNotes(e.target.value);edit("notes",e.target.value);}}/></label><div className="row"><button disabled={busy} onClick={()=>void submit("NOT_FOUND")}>Marcar como não encontrada</button><button disabled={busy} onClick={()=>void submit("DEFER")}>Adiar revisão</button></div></details>
        <h3>E. Qual é o impacto?</h3><p className="box warn">{task.impact_pt}</p>
        {task.current?.proposal && <details className="card"><summary>Revisão independente da proposta</summary><p>Autor: {task.current.proposal.author}. Parecer favorável não aprova o perfil físico.</p><label>Nome de quem registra o parecer<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label>Parecer<textarea value={notes} onChange={e=>setNotes(e.target.value)}/></label>
          <div className="row"><button disabled={busy || !["SOURCE_SUBMITTED","ASSUMPTION_PROPOSED"].includes(task.state)} onClick={()=>void submit("REQUEST_REVIEW")}>Solicitar revisão</button><button disabled={busy || task.state!=="UNDER_REVIEW"} onClick={()=>void submit("ACCEPT")}>Registrar parecer favorável</button><button disabled={busy || task.state!=="UNDER_REVIEW"} onClick={()=>void submit("REJECT")}>Solicitar correções</button></div></details>}
        <details className="tech big"><summary>Detalhes técnicos e histórico ({task.history.length})</summary><p>Parâmetro: <code>{task.parameter}</code> · Perfil v{j.profile.version}</p><p>Locais já consultados: {task.searched_in?.join("; ") || "ver fonte original"}</p>
          <ol>{task.history.map(h=><li key={h.revision}>{ACTION_LABEL[h.action] ?? h.action} · {h.author} · {new Date(h.at).toLocaleString("pt-BR")} · {h.notes}<br/><small>Versão do caso {h.case_version} · {h.sha256.slice(0,12)}</small></li>)}</ol>
        </details>
      </>}
    </div>
    <footer className="guided-footer"><p role="status" aria-live="polite">{busy ? "Salvando…":status}</p><div className="row"><button disabled={busy || index===0 || summary} onClick={()=>void move(index-1)}>Anterior</button><button disabled={busy || summary} onClick={()=>void move(index+1)}>Próxima</button><button className="primary" disabled={busy || summary} onClick={()=>void move(index+1,true)}>Salvar e continuar</button><button disabled={busy} onClick={()=>void perform(async()=>{await draft();setSummary(!summary);})}>{summary ? "Revisar pendência":"Consultar resumo das decisões"}</button></div></footer>
  </div></div>;
}

export default function GuidedReview({experimentId,documentId,count,showReadiness=true,profileId,openSignal=0}:{experimentId:string;documentId?:string|null;count:number;showReadiness?:boolean;profileId?:string;openSignal?:number}) {
  const load=useLoad(()=>api.guidedReview(experimentId,profileId),[experimentId,profileId]);
  const [updated,setUpdated]=useState<GuidedJourney|null>(null); const [open,setOpen]=useState(false);
  useEffect(()=>{if(openSignal)setOpen(true);},[openSignal]);
  const j=updated ?? load.data;
  return <>
    {count>0 && <button className="primary" onClick={()=>setOpen(true)}>{j?.recorded ? "Retomar revisão":`Resolver ${count} pendências`}</button>}
    {load.error && <p className="box bad" role="alert">Não foi possível carregar a revisão: {load.error.message}<button onClick={load.reload}>Tentar novamente</button></p>}
    {j && showReadiness && <><ModelReadiness journey={j}/><DecisionSummary journey={j}/></>}
    {open && <Async state={load}>{()=>j && <GuidedModal initial={j} documentId={documentId} onChange={setUpdated} onClose={()=>setOpen(false)}/>}</Async>}
  </>;
}
