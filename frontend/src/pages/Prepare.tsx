import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, type CaseAssumption, type CaseDiagnostic, type ScientificCase } from "../api";
import { Async, UnitCell, useLoad } from "../components";
import { formatValue, reviewStateView } from "../lib";
import GuidedReview from "../GuidedReview";

function ScientificPreparation({id}:{id:string}) {
  const experiment=useLoad(()=>api.experiment(id),[id]);
  const profiles=useLoad(api.profiles,[]);
  const [profileId,setProfileId]=useState("");
  return <><h1>Preparar modelo</h1><p>As evidências, hipóteses e decisões da revisão guiada já fazem parte da preparação: não é preciso preencher de novo. Abra um requisito para complementar ou editar o registro.</p>
    <Async state={experiment}>{e=><>
      <div className="crumbs"><Link to={`/documentos/${e.document_id}/analise`}>Resumo da análise</Link> › {e.label}</div>
      <p>{e.review.reviewed} parâmetros conferidos · {e.gaps.length} pendências registradas na fonte.</p>
      <Async state={profiles}>{all=><label>Perfil físico<select value={profileId || all.find(p=>!p.independent_only)?.model_id || ""} onChange={event=>setProfileId(event.target.value)}>{all.filter(p=>!p.independent_only).map(p=><option key={p.model_id} value={p.model_id}>{p.title_pt}{p.approved ? "":" — sem aprovação"}</option>)}</select></label>}</Async>
      <GuidedReview key={profileId} experimentId={id} documentId={e.document_id} count={e.gaps.length} profileId={profileId || undefined} showRequirements/>
      <section className="card"><button disabled>Executar simulação deste experimento</button>
        <p className="detail">Bloqueado: o perfil físico deste experimento não tem gerador FDS implementado e aprovado. Nenhuma combustão prescrita de propano substitui o modelo de PMMA.</p></section>
      <details className="card"><summary>Consultar os {e.parameters.length} parâmetros da fonte</summary>{e.parameters.map(p=><p key={p.record_id}><strong>{p.label_pt}</strong> · {formatValue(p)} · {reviewStateView(p).text}</p>)}</details>
      <Link className="btn" to={`/experimentos/${id}#parametros`}>Revisar parâmetros na fonte</Link>
      <p className="detail">O caso técnico de propano tem configuração independente e não recebe estes dados.</p>
      <Link to="/preparar-simulacao">Abrir caso técnico independente, sem transferir dados NASA</Link>
    </>}</Async>
  </>;
}

const STEPS = ["Dados disponíveis", "Informações necessárias", "Modelo e hipóteses", "Executar e visualizar"];
const MESSAGES: Record<string,string> = {INDEPENDENT_REVIEW_REQUIRED:"Revisão independente e aceitação dos defaults pendentes",EXECUTOR_UNAVAILABLE:"FDS/Smokeview/FFmpeg indisponíveis",MODEL_NOT_APPROVED:"Modelo físico ainda não aprovado",EXPERIMENT_PROFILE_NOT_EXECUTABLE:"Experimento sem perfil físico executável"};

export default function Prepare() {
  const {id}=useParams();
  return id ? <ScientificPreparation id={id}/>:<IndependentPreparation/>;
}

function IndependentPreparation() {
  const { id } = useParams(); const nav = useNavigate(); const [query,setQuery] = useSearchParams();
  const cid = query.get("case"); const version = Number(query.get("version") || 1);
  const profiles = useLoad(api.profiles, []);
  const preparation = useLoad(() => id ? api.preparation(id) : Promise.resolve(null), [id]);
  const [step,setStep] = useState(cid ? 3 : 0);
  const [saved,setSaved] = useState<ScientificCase | null>(null);
  const current = useLoad(() => cid ? api.case(cid,version) : Promise.resolve(null), [cid,version,saved]);
  const runs = useLoad(() => cid ? api.runs() : Promise.resolve([]), [cid,version]);
  const [diagnostic,setDiagnostic] = useState<CaseDiagnostic | null>(null);
  const [reviewer,setReviewer] = useState(""); const [notes,setNotes] = useState(""); const [accepted,setAccepted] = useState(false);
  const [assumptions,setAssumptions] = useState<CaseAssumption[]>([]);
  const [error,setError] = useState(""); const [busy,setBusy] = useState(false);
  useEffect(()=>{
    const previous=current.data?.case.content.assumptions;
    if (previous) setAssumptions(previous.filter(a=>a.source_type!=="SOFTWARE_DEFAULT").map(a=>({parameter:a.parameter,value:a.value,unit:a.unit,source:a.source,source_type:a.source_type,justification:a.justification,author:a.author,limitations:a.limitations})));
  },[current.data?.case.content_sha256]);
  const c = saved || current.data?.case;
  const candidate = diagnostic || current.data;
  const d = candidate?.case.content.case_id===cid && candidate?.case.content.version===version ? candidate : null;
  async function act(fn:()=>Promise<void>) { setBusy(true);setError("");try { await fn(); } catch(e) {setError((e as Error).message);}finally{setBusy(false);} }
  return <>
    <h1>Preparar simulação</h1>
    <p className="box warn">{id ? "Experimento NASA: diagnóstico científico. Execução depende de perfil físico aprovado." : "Exploração técnica independente — não é reprodução de experimento NASA."}</p>
    <nav aria-label="Etapas de preparação">{STEPS.map((s,i)=><button key={s} aria-current={step===i ? "step" : undefined} onClick={()=>setStep(i)}>{i+1}. {s}</button>)}</nav>
    {error && <p role="alert" className="box bad">{error}</p>}
    <h2>{step+1}. {STEPS[step]}</h2>
    <Async state={profiles}>{all=>{
      const profile = all.find(p=>id ? !p.independent_only : p.independent_only);
      if (!profile) return <p>Perfil indisponível.</p>;
      return <>
        {step===0 && (id ? <Async state={preparation}>{p=>p && <>
          {[...p.conditions,...p.ambiguous,...p.observables].map(x=><article className="card" key={x.record_id}><strong>{x.label_pt}</strong> · {formatValue(x)} · <UnitCell p={x}/><p>{reviewStateView(x).text} · {x.role}</p><small>{x.evidence.map(e=>e.locator_pt).join("; ")}</small></article>)}
        </>}</Async> : <p>Não há dados NASA neste caso. Geometria, reação e entradas vêm do perfil técnico controlado; seus defaults devem ser revisados explicitamente.</p>)}
        {step===1 && (id ? <Async state={preparation}>{p=>p && <>{p.gaps.map(g=><article className="card" key={g.gap_id}><strong>{g.label_pt}</strong><p>{g.explanation_pt}</p><p>{g.required ? "Necessária para construção do modelo" : "Limita fidelidade ou comparação"} · {g.assumption_allowed ? "Hipótese exige revisão" : "Base física e revisão de material obrigatórias"}</p><p>{g.impact_pt}</p></article>)}</>}</Async> : <><p>O perfil precisa de uma fonte de calor prescrita, rendimento de fuligem e duração. Não representa pirólise de PMMA.</p>{profile.parameters.map(p=><p key={p.name}>{p.label_pt}: {p.default} {p.unit} (default explícito do perfil)</p>)}</>)}
        {step===2 && <>
          <label>Modelo<select value={profile.model_id} disabled><option>{profile.title_pt} — {profile.version}{!profile.approved ? " (bloqueado)" : ""}</option></select></label>
          {profile.limitations.map(t=><p key={t}>{t}</p>)}
          {!id && <>
            {profile.parameters.map(p=>{const a=assumptions.find(a=>a.parameter===p.name);return <details className="card" key={p.name}><summary>{p.label_pt}: {a?.value ?? p.default} {p.unit} · {a ? "hipótese de engenharia" : "SOFTWARE_DEFAULT"}</summary>
              {!a ? <button onClick={()=>setAssumptions([...assumptions,{parameter:p.name,value:p.default,unit:p.unit,source:"",source_type:"ENGINEERING_ASSUMPTION",justification:"",author:"",limitations:"Sem fidelidade experimental NASA"}])}>Definir hipótese</button> : <>
                {(["value","source","justification","author","limitations"] as const).map(k=><label key={k}>{({value:"Valor",source:"Fonte",justification:"Justificativa",author:"Autor",limitations:"Limitações"})[k]}<input type={k==="value" ? "number" : "text"} value={a[k]} onChange={e=>setAssumptions(assumptions.map(x=>x===a ? {...x,[k]:k==="value" ? Number(e.target.value):e.target.value}:x))}/></label>)}
                <button onClick={()=>setAssumptions(assumptions.filter(x=>x!==a))}>Usar default explícito</button>
              </>}
            </details>;})}
            <button disabled={busy} onClick={()=>act(async()=>{const body={profile_id:profile.model_id,profile_version:profile.version,title:"Exploração técnica independente",assumptions};const result=cid ? await api.caseVersion(cid,body):await api.createCase(body);setSaved(result);setDiagnostic(null);setQuery({case:result.content.case_id,version:String(result.content.version)});setStep(3);})}>{cid ? "Salvar nova versão" : "Salvar preparação"}</button>
          </>}
          {id && <p className="box bad">Perfil PMMA não aprovado. As hipóteses não substituem um modelo físico validado.</p>}
        </>}
        {step===3 && <>
          {id ? <><p className="box bad">{preparation.data?.state ?? "Avaliando"} — {preparation.data?.blockers.join("; ")}. Execução bloqueada.</p><Link to="/preparar-simulacao">Abrir caso técnico independente, sem transferir dados NASA</Link></> : !c ? <p>Salve a preparação na etapa 3.</p> : <>
            <p>Caso {c.content.case_id} · versão {c.content.version}</p><p>Malha fixa: 36 × 24 × 24 (20.736 células); 4 threads; teto de 900 s de execução. Sem estimativa de custo.</p>
            {runs.data?.filter(r=>r.case_id===cid && r.case_version===version).map(r=><p key={r.run_id}><Link to={r.state==="COMPLETED" ? `/execucoes/${r.run_id}` : `/simulacao/${r.scenario_id}`}>Retomar execução {r.run_id} — {r.state}</Link></p>)}
            <p>Tempo simulado: {c.content.values.t_end} s. HRRPUA: {c.content.values.hrrpua} kW/m². Fuligem: {c.content.values.soot_yield} kg/kg.</p>
            {c.content.assumptions.map(a=><p key={a.parameter}>{a.parameter}: {a.value} {a.unit} · {a.source_type} · {a.source} · autor {a.author}</p>)}
            <p role="status">{d?.state ?? "Avaliando"}</p>{d?.blockers.map(b=><p key={b}>{MESSAGES[b] ?? b}</p>)}
            {!d?.approval && <fieldset><legend>Revisão independente</legend><label>Revisor<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label>Notas de revisão<input value={notes} onChange={e=>setNotes(e.target.value)}/></label><label><input type="checkbox" checked={accepted} onChange={e=>setAccepted(e.target.checked)}/>Aceito os defaults e revisei fontes, hipóteses e limitações; sou independente dos autores.</label><button disabled={busy || !accepted || reviewer.trim().length<2 || notes.trim().length<5} onClick={()=>act(async()=>{await api.reviewCase(c.content.case_id,version,reviewer,notes);setDiagnostic(await api.validateCase(c.content.case_id,version));})}>Registrar revisão e validar</button></fieldset>}
            <button disabled={busy || d?.state!=="EXECUTION_READY"} onClick={()=>act(async()=>{const r=await api.submitCase(c.content.case_id,version);nav(`/simulacao/${r.scenario_id}`);})}>Executar caso independente</button>
          </>}
          <p>Comparação quantitativa não disponível para este perfil.</p>
        </>}
      </>;
    }}</Async>
    {step<3 && <button onClick={()=>setStep(step+1)}>Próxima etapa</button>}
  </>;
}
