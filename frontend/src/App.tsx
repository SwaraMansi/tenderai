import * as React from "react";
import { useEffect, useMemo, useState } from "react";
import {
  Activity, Building2, FileText, Search, ShieldCheck, ClipboardCheck,
  LogOut, Plus, UploadCloud, RefreshCw, ChevronRight, ExternalLink,
  AlertCircle, CheckCircle2, Clock3, BriefcaseBusiness, Menu
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
type Page = "dashboard" | "company" | "tenders" | "assessment";
type Tender = {
  id: string; title: string; source: string; external_id: string; category?: string;
  state?: string; procuring_entity?: string; submission_deadline?: string;
  estimated_value_inr?: number | string; source_url?: string; status: string;
  metadata_json?: Record<string, any>;
};
type Profile = {
  id: string; legal_name: string; business_type?: string; sectors: string[];
  udyam_number?: string; gstin?: string; pan_last_four?: string;
  registered_state?: string; annual_turnover_inr?: number; years_in_business?: number;
};

async function request(path: string, token: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}
const money = (v?: number | string) => v == null ? "Not disclosed" : new Intl.NumberFormat("en-IN", { style:"currency", currency:"INR", maximumFractionDigits:0 }).format(Number(v));
const dateText = (v?: string) => !v ? "Not specified" : /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : new Date(v).toLocaleString("en-IN");

function Field({label, children}: {label:string; children:React.ReactNode}) {
  return <label className="block"><span className="label">{label}</span>{children}</label>;
}
function Status({value}: {value:string}) {
  const cls = ["PASS","BID_CANDIDATE","pass","open"].includes(value) ? "pill-green" :
    ["FAIL","NO_BID","fail","closed"].includes(value) ? "pill-red" : "pill-yellow";
  return <span className={`pill ${cls}`}>{value.split("_").join(" ")}</span>;
}

export default function App() {
  const [token,setToken] = useState(localStorage.getItem("tenderai_token") || "");
  const [page,setPage] = useState<Page>("dashboard");
  const [authMode,setAuthMode] = useState<"login"|"register">("register");
  const [email,setEmail] = useState("");
  const [password,setPassword] = useState("");
  const [org,setOrg] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");
  const [profile,setProfile] = useState<Profile|null>(null);
  const [tenders,setTenders] = useState<Tender[]>([]);
  const [selectedTender,setSelectedTender] = useState("");
  const [assessment,setAssessment] = useState<any>(null);

  const loadCore = async () => {
    if (!token) return;
    try {
      const [p,t] = await Promise.all([
        request("/api/v1/companies/profile",token).catch(()=>null),
        request("/api/v1/tenders?limit=50",token)
      ]);
      setProfile(p);
      setTenders(t);
    } catch(e) { setError((e as Error).message); }
  };
  useEffect(()=>{ loadCore(); },[token]);

  const run = async (fn:()=>Promise<void>) => {
    setBusy(true); setError(""); setNotice("");
    try { await fn(); } catch(e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const authenticate = () => run(async()=>{
    const path = authMode === "register" ? "/api/v1/auth/register" : "/api/v1/auth/login";
    const payload = authMode === "register" ? {email,password,organization_name:org} : {email,password};
    const data = await request(path,"",{method:"POST",body:JSON.stringify(payload)});
    localStorage.setItem("tenderai_token",data.access_token);
    setToken(data.access_token);
  });
  const logout = () => { localStorage.removeItem("tenderai_token"); setToken(""); setProfile(null); setAssessment(null); };
  const saveProfile = (data:Record<string,unknown>) => run(async()=>{
    const p = await request("/api/v1/companies/profile",token,{method:profile?"PATCH":"POST",body:JSON.stringify(data)});
    setProfile(p); setNotice("Company profile saved.");
  });
  const createTender = (data:Record<string,unknown>) => run(async()=>{
    await request("/api/v1/tenders",token,{method:"POST",body:JSON.stringify(data)});
    await loadCore(); setNotice("Tender added to your discovery workspace.");
  });
  const uploadDocument = (tenderId:string,file:File,kind:"tender_document"|"corrigendum") => run(async()=>{
    const form = new FormData(); form.append("file",file);
    if (kind==="corrigendum") {
      const result = await request(`/api/v1/documents/tenders/${tenderId}/corrigenda`,token,{method:"POST",body:form});
      setNotice(`Corrigendum uploaded. ${result.changes?.length || 0} potential change(s) detected.`);
    } else {
      const result = await request(`/api/v1/documents/tenders/${tenderId}/upload`,token,{method:"POST",body:form});
      setNotice(`Document uploaded. ${result.page_count} page(s), ${result.table_count} table(s). ${result.indexing?.embedded?"Vector and keyword indexing ready.":"Keyword index saved; vector embedding is unavailable. "+(result.indexing?.reason||"")}`);
    }
  });
  const evaluate = (tenderId:string) => run(async()=>{
    if (!profile) throw new Error("Create a company profile before running eligibility.");
    const data = await request(`/api/v1/eligibility/tenders/${tenderId}/evaluate/${profile.id}`,token,{method:"POST"});
    setAssessment({id:data.assessment_id,tender_id:tenderId,report:data,checklist:data.checklist || []});
    setPage("assessment"); setNotice("Eligibility assessment generated.");
  });
  const openAssessment = (id:string) => run(async()=>{
    const data = await request(`/api/v1/eligibility/assessments/${id}`,token);
    setAssessment({id:data.id,report:data.report,checklist:data.checklist});
    setPage("assessment");
  });

  if (!token) return <AuthScreen mode={authMode} setMode={setAuthMode} email={email} setEmail={setEmail}
    password={password} setPassword={setPassword} org={org} setOrg={setOrg}
    onSubmit={authenticate} busy={busy} error={error}/>;

  const nav = [
    {id:"dashboard" as Page,label:"Overview",icon:Activity},
    {id:"company" as Page,label:"Company profile",icon:Building2},
    {id:"tenders" as Page,label:"Tender discovery",icon:Search},
    {id:"assessment" as Page,label:"Bid readiness",icon:ClipboardCheck}
  ];
  return <div className="min-h-screen bg-mist">
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-slate-200 bg-white p-5 lg:block">
      <Brand/>
      <div className="mt-10 space-y-2">{nav.map(n=><button key={n.id} onClick={()=>setPage(n.id)}
        className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold ${page===n.id?"bg-blue-50 text-brand":"text-slate-600 hover:bg-slate-50"}`}>
        <n.icon size={18}/>{n.label}</button>)}</div>
      <div className="absolute bottom-5 left-5 right-5 rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
        <div className="font-bold text-slate-700">India procurement workspace</div>
        Public-source metadata and company-specific bid readiness.
      </div>
    </aside>
    <main className="lg:pl-64">
      <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur md:px-8">
        <div><div className="text-xs font-semibold uppercase tracking-wider text-slate-400">TenderAI workspace</div>
          <div className="font-bold text-ink">{nav.find(n=>n.id===page)?.label || "Bid readiness"}</div></div>
        <div className="flex items-center gap-3"><span className="hidden text-xs text-slate-500 sm:block">{profile?.legal_name || "Company not configured"}</span>
          <button className="btn btn-light" onClick={logout}><LogOut size={15}/> Sign out</button></div>
      </header>
      <div className="mx-auto max-w-7xl p-5 md:p-8">
        {error && <Notice kind="error" text={error} onClose={()=>setError("")}/>}
        {notice && <Notice kind="success" text={notice} onClose={()=>setNotice("")}/>}
        {page==="dashboard" && <Dashboard profile={profile} tenders={tenders} go={setPage} refresh={loadCore}/>}
        {page==="company" && <CompanyPage token={token} profile={profile} save={saveProfile} run={run}/>}
        {page==="tenders" && <TenderPage token={token} tenders={tenders} refresh={loadCore} create={createTender}
          upload={uploadDocument} evaluate={evaluate} run={run} selectedTender={selectedTender} setSelectedTender={setSelectedTender}/>}
        {page==="assessment" && <AssessmentPage assessment={assessment} token={token} openAssessment={openAssessment} run={run}/>}
      </div>
    </main>
    <div className="fixed bottom-0 left-0 right-0 z-30 flex border-t bg-white p-2 lg:hidden">{nav.map(n=><button key={n.id} onClick={()=>setPage(n.id)} className={`flex flex-1 flex-col items-center gap-1 p-2 text-[10px] ${page===n.id?"text-brand":"text-slate-500"}`}><n.icon size={18}/>{n.label}</button>)}</div>
  </div>;
}

function Brand(){return <div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand text-white"><ShieldCheck size={22}/></div><div><div className="text-lg font-extrabold tracking-tight text-ink">TenderAI</div><div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Procurement intelligence</div></div></div>;}
function Notice({kind,text,onClose}:{kind:"error"|"success";text:string;onClose:()=>void}) {
  return <div className={`mb-5 flex items-center justify-between rounded-xl p-3 text-sm ${kind==="error"?"bg-red-50 text-red-700":"bg-emerald-50 text-emerald-700"}`}>
    <span className="flex items-center gap-2">{kind==="error"?<AlertCircle size={16}/>:<CheckCircle2 size={16}/ >}{text}</span>
    <button onClick={onClose}>×</button></div>;
}
function AuthScreen(props:any) {
  return <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-100 to-blue-100 p-5">
    <div className="grid w-full max-w-5xl overflow-hidden rounded-3xl bg-white shadow-xl md:grid-cols-2">
      <div className="hidden bg-ink p-12 text-white md:block"><Brand/><div className="mt-20">
        <div className="text-3xl font-extrabold leading-tight">Find the right tenders. Prepare with confidence.</div>
        <p className="mt-5 text-sm leading-7 text-slate-300">One workspace for public procurement discovery, tender document intelligence and evidence-backed bid readiness.</p>
        <div className="mt-10 space-y-4 text-sm text-slate-200"><div className="flex gap-3"><Search/> Discover opportunities across sectors</div><div className="flex gap-3"><FileText/> Understand clauses and amendments</div><div className="flex gap-3"><ClipboardCheck/> Track eligibility and compliance</div></div>
      </div></div>
      <div className="p-7 md:p-12">
        <div className="mb-8 md:hidden"><Brand/></div>
        <h1 className="text-2xl font-extrabold text-ink">{props.mode==="register"?"Create your workspace":"Welcome back"}</h1>
        <p className="mt-2 text-sm text-slate-500">India-first procurement intelligence for businesses and bid teams.</p>
        {props.error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{props.error}</div>}
        <form className="mt-7 space-y-4" onSubmit={e=>{e.preventDefault();props.onSubmit();}}>
          <Field label="Work email"><input type="email" required value={props.email} onChange={e=>props.setEmail(e.target.value)} placeholder="you@company.in"/></Field>
          {props.mode==="register" && <Field label="Organization name"><input required minLength={2} value={props.org} onChange={e=>props.setOrg(e.target.value)} placeholder="Your business name"/></Field>}
          <Field label="Password"><input type="password" required minLength={props.mode==="register"?12:1} value={props.password} onChange={e=>props.setPassword(e.target.value)} placeholder="At least 12 characters for registration"/></Field>
          <button disabled={props.busy} className="btn btn-primary w-full">{props.busy?"Please wait":props.mode==="register"?"Create account":"Sign in"} <ChevronRight size={16}/></button>
        </form>
        <button className="mt-5 w-full text-sm font-semibold text-brand" onClick={()=>props.setMode(props.mode==="register"?"login":"register")}>{props.mode==="register"?"Already registered? Sign in":"New to TenderAI? Create an account"}</button>
      </div>
    </div>
  </div>;
}
function PageHeading({eyebrow,title,description,action}:{eyebrow:string;title:string;description:string;action?:React.ReactNode}) {
  return <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><div className="text-xs font-bold uppercase tracking-widest text-brand">{eyebrow}</div><h1 className="mt-2 text-2xl font-extrabold tracking-tight text-ink md:text-3xl">{title}</h1><p className="mt-2 max-w-2xl text-sm text-slate-500">{description}</p></div>{action}</div>;
}
function Dashboard({profile,tenders,go,refresh}:{profile:Profile|null;tenders:Tender[];go:(p:Page)=>void;refresh:()=>void}) {
  const open = tenders.filter(t=>t.status==="open"||t.status==="discovered").length;
  return <><PageHeading eyebrow="Procurement overview" title="Your tender workspace" description="A clear view of your company profile, discovered opportunities and next bid-readiness actions." action={<button className="btn btn-light" onClick={refresh}><RefreshCw size={15}/> Refresh data</button>}/>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Metric icon={Search} label="Tender records" value={tenders.length.toString()} hint="In your catalogue"/>
      <Metric icon={Activity} label="Open / discovered" value={open.toString()} hint="Potential opportunities"/>
      <Metric icon={Building2} label="Company profile" value={profile?"Ready":"Incomplete"} hint={profile?.legal_name || "Add business details"}/>
      <Metric icon={ClipboardCheck} label="Next action" value={profile?"Review tenders":"Set up profile"} hint="Improve bid readiness"/>
    </div>
    {!profile && <div className="card mt-6 flex flex-col justify-between gap-4 border-blue-100 bg-blue-50/70 p-5 sm:flex-row sm:items-center"><div><div className="font-bold text-ink">Complete your company profile</div><p className="mt-1 text-sm text-slate-600">Turnover, certifications and project experience are needed for meaningful eligibility checks.</p></div><button className="btn btn-primary" onClick={()=>go("company")}>Set up profile <ChevronRight size={16}/></button></div>}
    <div className="mt-7 grid gap-5 xl:grid-cols-[1.5fr_1fr]">
      <div className="card p-5"><div className="flex items-center justify-between"><h2 className="font-bold text-ink">Recent tenders</h2><button className="text-sm font-semibold text-brand" onClick={()=>go("tenders")}>View all</button></div>
        <div className="mt-4 space-y-3">{tenders.slice(0,5).map(t=><TenderRow key={t.id} tender={t} onClick={()=>go("tenders")}/>)}
          {tenders.length===0 && <Empty text="No tender records yet. Add a tender manually or discover a public procurement page."/>}</div></div>
      <div className="card p-5"><h2 className="font-bold text-ink">Getting started</h2><div className="mt-4 space-y-4">
        <Step n="01" title="Create your company profile" detail="Add turnover, business registrations and past projects" done={!!profile}/>
        <Step n="02" title="Add tender opportunities" detail="Upload tender documents or discover a public listing" done={tenders.length>0}/>
        <Step n="03" title="Run bid-readiness analysis" detail="Extract requirements and compare against your profile" done={false}/>
      </div></div>
    </div></>;
}
function Metric({icon:Icon,label,value,hint}:{icon:any;label:string;value:string;hint:string}) {
  return <div className="card p-5"><div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-500">{label}</span><div className="rounded-lg bg-blue-50 p-2 text-brand"><Icon size={17}/></div></div><div className="mt-3 text-2xl font-extrabold text-ink">{value}</div><div className="mt-1 truncate text-xs text-slate-400">{hint}</div></div>;
}
function Step({n,title,detail,done}:{n:string;title:string;detail:string;done:boolean}) {
  return <div className="flex gap-3"><div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${done?"bg-emerald-100 text-emerald-700":"bg-slate-100 text-slate-500"}`}>{done?<CheckCircle2 size={16}/>:n}</div><div><div className="text-sm font-bold text-ink">{title}</div><div className="mt-1 text-xs leading-5 text-slate-500">{detail}</div></div></div>;
}
function Empty({text}:{text:string}) {return <div className="rounded-xl border border-dashed border-slate-200 p-7 text-center text-sm text-slate-500">{text}</div>;}
function TenderRow({tender,onClick}:{tender:Tender;onClick:()=>void}) {
  return <button onClick={onClick} className="flex w-full items-center justify-between gap-3 rounded-xl border border-slate-100 p-3 text-left hover:border-blue-200 hover:bg-blue-50/30"><div className="min-w-0"><div className="truncate text-sm font-bold text-ink">{tender.title}</div><div className="mt-1 truncate text-xs text-slate-500">{tender.external_id} · {tender.source.toUpperCase()} · {tender.category||"Unclassified"}</div></div><div className="shrink-0 text-right"><Status value={tender.status}/><div className="mt-1 text-[10px] text-slate-400">{dateText(tender.submission_deadline || tender.metadata_json?.extracted_submission_deadline)}</div></div></button>;
}

function CompanyPage({token,profile,save,run}:{token:string;profile:Profile|null;save:(x:Record<string,unknown>)=>void;run:any}) {
  const [form,setForm] = useState<any>({legal_name:"",business_type:"Private Limited",sectors:["IT"],udyam_number:"",dpiit_startup_number:"",gstin:"",pan_last_four:"",registered_state:"",annual_turnover_inr:"",years_in_business:""});
  const [certs,setCerts] = useState<any[]>([]);
  const [projects,setProjects] = useState<any[]>([]);
  const [turnoverUnit,setTurnoverUnit] = useState("lakhs");
  const unitFactor = turnoverUnit === "crores" ? 10000000 : turnoverUnit === "lakhs" ? 100000 : 1;
  const [cert,setCert] = useState({name:"",certificate_number:"",issuer:"",valid_until:""});
  const [project,setProject] = useState({title:"",client_name:"",sector:"",contract_value_inr:"",description:""});
  useEffect(()=>{if(profile)setForm({...profile,annual_turnover_inr:profile.annual_turnover_inr==null?"":Number(profile.annual_turnover_inr)/unitFactor,years_in_business:profile.years_in_business??""});},[profile]);
  const reload = async()=>{const [c,p]=await Promise.all([request("/api/v1/companies/certifications",token),request("/api/v1/companies/projects",token)]);setCerts(c);setProjects(p);};
  useEffect(()=>{reload().catch(()=>{});},[token,profile?.id]);
  const submitProfile = (e:React.FormEvent)=>{e.preventDefault();save({...form,udyam_number:form.udyam_number||null,dpiit_startup_number:form.dpiit_startup_number||null,gstin:form.gstin||null,pan_last_four:form.pan_last_four||null,registered_state:form.registered_state||null,annual_turnover_inr:form.annual_turnover_inr===""?null:Number(form.annual_turnover_inr)*unitFactor,years_in_business:form.years_in_business===""?null:Number(form.years_in_business),sectors:form.sectors});};
  const addCert = (e:React.FormEvent)=>{e.preventDefault();run(async()=>{await request("/api/v1/companies/certifications",token,{method:"POST",body:JSON.stringify({...cert,valid_until:cert.valid_until?new Date(cert.valid_until).toISOString():null})});setCert({name:"",certificate_number:"",issuer:"",valid_until:""});await reload();});};
  const addProject = (e:React.FormEvent)=>{e.preventDefault();run(async()=>{await request("/api/v1/companies/projects",token,{method:"POST",body:JSON.stringify({...project,contract_value_inr:project.contract_value_inr?Number(project.contract_value_inr):null})});setProject({title:"",client_name:"",sector:"",contract_value_inr:"",description:""});await reload();});};
  return <><PageHeading eyebrow="Business identity" title="Company profile" description="Maintain your verified business information. TenderAI uses these records as evidence during eligibility checks."/>
    <form onSubmit={submitProfile} className="card p-5 md:p-7"><div className="mb-5 font-bold text-ink">Organization details</div>
      <div className="grid gap-4 md:grid-cols-2"><Field label="Legal business name"><input required value={form.legal_name} onChange={e=>setForm({...form,legal_name:e.target.value})}/></Field>
      <Field label="Business type"><select value={form.business_type||""} onChange={e=>setForm({...form,business_type:e.target.value})}><option>Private Limited</option><option>LLP</option><option>Partnership</option><option>Sole Proprietorship</option><option>Public Limited</option><option>Other</option></select></Field>
      <Field label="Registered state"><input value={form.registered_state||""} onChange={e=>setForm({...form,registered_state:e.target.value})} placeholder="Uttar Pradesh"/></Field>
      <Field label="Business sectors (comma separated)"><input value={(form.sectors||[]).join(", ")} onChange={e=>setForm({...form,sectors:e.target.value.split(",").map((x:string)=>x.trim()).filter(Boolean)})} placeholder="IT, Construction, Goods, Services"/></Field>
      <div><span className="label">Annual turnover</span><div className="grid grid-cols-[1fr_110px] gap-2"><input type="number" min="0" value={form.annual_turnover_inr} onChange={e=>setForm({...form,annual_turnover_inr:e.target.value})} placeholder="250"/><select value={turnoverUnit} onChange={e=>{const next=e.target.value;const oldFactor=turnoverUnit==="crores"?10000000:turnoverUnit==="lakhs"?100000:1;const newFactor=next==="crores"?10000000:next==="lakhs"?100000:1;setForm({...form,annual_turnover_inr:form.annual_turnover_inr===""?"":String(Number(form.annual_turnover_inr)*oldFactor/newFactor)});setTurnoverUnit(next);}}><option value="inr">₹ INR</option><option value="lakhs">₹ Lakhs</option><option value="crores">₹ Crores</option></select></div><span className="mt-1 block text-[10px] text-slate-400">Stored in INR for deterministic eligibility calculations.</span></div>
      <Field label="Years in business"><input type="number" min="0" step="0.1" value={form.years_in_business} onChange={e=>setForm({...form,years_in_business:e.target.value})}/></Field>
      <Field label="Udyam registration number"><input value={form.udyam_number||""} onChange={e=>setForm({...form,udyam_number:e.target.value})}/></Field>
      <Field label="DPIIT Startup recognition number"><input value={form.dpiit_startup_number||""} onChange={e=>setForm({...form,dpiit_startup_number:e.target.value})}/></Field>
      <Field label="GSTIN"><input maxLength={15} value={form.gstin||""} onChange={e=>setForm({...form,gstin:e.target.value.toUpperCase()})}/></Field>
      <Field label="PAN last four characters"><input maxLength={4} value={form.pan_last_four||""} onChange={e=>setForm({...form,pan_last_four:e.target.value.toUpperCase()})}/></Field></div>
      <div className="mt-6 flex justify-end"><button className="btn btn-primary"><CheckCircle2 size={16}/> Save company profile</button></div>
    </form>
    <div className="mt-6 grid gap-5 xl:grid-cols-2">
      <section className="card p-5"><h2 className="font-bold">Certifications and registrations</h2><form onSubmit={addCert} className="mt-4 grid gap-3">
        <Field label="Certification name"><input required value={cert.name} onChange={e=>setCert({...cert,name:e.target.value})} placeholder="ISO 9001, BIS, NSIC"/></Field>
        <Field label="Certificate number"><input value={cert.certificate_number} onChange={e=>setCert({...cert,certificate_number:e.target.value})}/></Field>
        <Field label="Issuer"><input value={cert.issuer} onChange={e=>setCert({...cert,issuer:e.target.value})}/></Field>
        <Field label="Valid until"><input type="date" value={cert.valid_until} onChange={e=>setCert({...cert,valid_until:e.target.value})}/></Field>
        <button className="btn btn-light"><Plus size={15}/> Add certification</button></form>
        <div className="mt-4 space-y-2">{certs.map(c=><div key={c.id} className="rounded-lg bg-slate-50 p-3 text-sm"><b>{c.name}</b><div className="text-xs text-slate-500">{c.certificate_number||"No number"} · {c.issuer||"Issuer not entered"}</div></div>)}{certs.length===0&&<p className="text-xs text-slate-400">No additional certificates recorded.</p>}</div>
      </section>
      <section className="card p-5"><h2 className="font-bold">Past project experience</h2><form onSubmit={addProject} className="mt-4 grid gap-3">
        <Field label="Project title"><input required value={project.title} onChange={e=>setProject({...project,title:e.target.value})}/></Field>
        <Field label="Client name"><input value={project.client_name} onChange={e=>setProject({...project,client_name:e.target.value})}/></Field>
        <Field label="Sector"><input value={project.sector} onChange={e=>setProject({...project,sector:e.target.value})}/></Field>
        <Field label="Contract value (₹ INR)"><input type="number" min="0" value={project.contract_value_inr} onChange={e=>setProject({...project,contract_value_inr:e.target.value})}/></Field>
        <Field label="Project description"><textarea rows={2} value={project.description} onChange={e=>setProject({...project,description:e.target.value})}/></Field>
        <button className="btn btn-light"><Plus size={15}/> Add project</button></form>
        <div className="mt-4 space-y-2">{projects.map(p=><div key={p.id} className="rounded-lg bg-slate-50 p-3 text-sm"><b>{p.title}</b><div className="text-xs text-slate-500">{p.client_name||"Client not entered"} · {money(p.contract_value_inr)}</div></div>)}{projects.length===0&&<p className="text-xs text-slate-400">No past projects recorded.</p>}</div>
      </section>
    </div></>;
}

function TenderPage(props:any) {
  const [search,setSearch] = useState("");
  const [sourceUrl,setSourceUrl] = useState("");
  const [form,setForm] = useState<any>({source:"manual",external_id:"",title:"",description:"",procuring_entity:"",category:"Goods",state:"",estimated_value_inr:"",submission_deadline:"",source_url:"",status:"open"});
  const [uploadId,setUploadId] = useState("");
  const [file,setFile] = useState<File|null>(null);
  const [corrFile,setCorrFile] = useState<File|null>(null);
  const [question,setQuestion] = useState("");
  const [answer,setAnswer] = useState<any>(null);
  const visible = useMemo(()=>props.tenders.filter((t:Tender)=>`${t.title} ${t.external_id} ${t.category||""} ${t.state||""}`.toLowerCase().includes(search.toLowerCase())),[props.tenders,search]);
  const addTender = (e:React.FormEvent)=>{e.preventDefault();props.create({...form,estimated_value_inr:form.estimated_value_inr?Number(form.estimated_value_inr):null,submission_deadline:form.submission_deadline?new Date(form.submission_deadline).toISOString():null,source_url:form.source_url||null});};
  const discover = (e:React.FormEvent)=>{e.preventDefault();props.run(async()=>{const result=await request(`/api/v1/tenders/discover/sync?url=${encodeURIComponent(sourceUrl)}&limit=25`,localStorage.getItem("tenderai_token")||"",{method:"POST"});setSourceUrl("");await props.refresh();alert(`Discovery complete: ${result.created_count} new record(s), ${result.existing_count} already present.`);});};
  const doUpload = (kind:"tender_document"|"corrigendum")=>{const f=kind==="tender_document"?file:corrFile;if(!uploadId||!f)return;props.upload(uploadId,f,kind);if(kind==="tender_document")setFile(null);else setCorrFile(null);};
  const ask = (e:React.FormEvent)=>{e.preventDefault();props.run(async()=>{const data=await request(`/api/v1/tenders/${uploadId}/ask`,localStorage.getItem("tenderai_token")||"",{method:"POST",body:JSON.stringify({question})});setAnswer(data);});};
  return <><PageHeading eyebrow="Opportunity intelligence" title="Tender discovery" description="Add tender records, inspect public tender pages and upload original tender documents or corrigenda."/>
    <div className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
      <section className="card p-5"><div className="flex items-center justify-between"><h2 className="font-bold">Tender catalogue</h2><span className="pill pill-blue">{visible.length} records</span></div>
        <div className="relative mt-4"><Search className="absolute left-3 top-3 text-slate-400" size={16}/><input className="pl-9" placeholder="Search tender title, ID, category or state" value={search} onChange={e=>setSearch(e.target.value)}/></div>
        <div className="mt-4 space-y-3">{visible.map((t:Tender)=><div key={t.id} className={`rounded-xl border p-4 ${uploadId===t.id?"border-blue-300 bg-blue-50/30":"border-slate-100"}`}>
          <div className="flex flex-wrap items-start justify-between gap-2"><div className="min-w-0"><div className="font-bold text-ink">{t.title}</div><div className="mt-1 text-xs text-slate-500">{t.external_id} · {t.source.toUpperCase()} · {t.category||"Category not set"}</div></div><Status value={t.status}/></div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-500"><div>Deadline: {dateText(t.submission_deadline)}</div><div>Value: {money(t.estimated_value_inr)}</div></div>
          <div className="mt-3 flex flex-wrap gap-2"><button className="btn btn-light" onClick={()=>setUploadId(t.id)}><UploadCloud size={14}/> Select for upload</button><button className="btn btn-primary" onClick={()=>props.evaluate(t.id)}>Evaluate eligibility</button>{t.source_url&&<a className="btn btn-light" href={t.source_url} target="_blank" rel="noreferrer"><ExternalLink size={14}/> Source</a>}</div>
        </div>)}{visible.length===0&&<Empty text="No matching tender records. Add one manually or import a public page."/>}</div>
      </section>
      <div className="space-y-5">
        <section className="card p-5"><h2 className="font-bold">Discover public tender page</h2><p className="mt-1 text-xs text-slate-500">Fetches metadata from an allowed CPPP or GeM HTTPS public page. It does not bypass login, CAPTCHA or portal controls.</p>
          <form onSubmit={discover} className="mt-4 space-y-3"><Field label="Official tender page URL"><input type="url" required value={sourceUrl} onChange={e=>setSourceUrl(e.target.value)} placeholder="https://eprocure.gov.in/..."/></Field><button className="btn btn-primary w-full"><Search size={15}/> Discover metadata</button></form>
        </section>
        <section className="card p-5"><h2 className="font-bold">Create tender record</h2>
          <form onSubmit={addTender} className="mt-4 grid gap-3">
            <Field label="Source"><select value={form.source} onChange={e=>setForm({...form,source:e.target.value})}><option value="manual">Manual</option><option value="cppp">CPPP</option><option value="gem">GeM</option><option value="state_portal">State portal</option></select></Field>
            <Field label="Tender / bid ID"><input required value={form.external_id} onChange={e=>setForm({...form,external_id:e.target.value})}/></Field>
            <Field label="Tender title"><input required minLength={3} value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/></Field>
            <Field label="Category / procurement sector"><input value={form.category} onChange={e=>setForm({...form,category:e.target.value})} placeholder="Goods, Works, Services, IT, healthcare, etc."/></Field>
            <Field label="Procuring entity"><input value={form.procuring_entity} onChange={e=>setForm({...form,procuring_entity:e.target.value})}/></Field>
            <Field label="State / UT"><input value={form.state} onChange={e=>setForm({...form,state:e.target.value})}/></Field>
            <Field label="Estimated value (₹ INR)"><input type="number" min="0" value={form.estimated_value_inr} onChange={e=>setForm({...form,estimated_value_inr:e.target.value})}/></Field>
            <Field label="Submission deadline"><input type="datetime-local" value={form.submission_deadline} onChange={e=>setForm({...form,submission_deadline:e.target.value})}/></Field>
            <Field label="Official source URL"><input type="url" value={form.source_url} onChange={e=>setForm({...form,source_url:e.target.value})}/></Field>
            <Field label="Description"><textarea rows={2} value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></Field>
            <button className="btn btn-primary w-full"><Plus size={15}/> Add tender</button>
          </form>
        </section>
        <section className="card p-5"><h2 className="font-bold">Tender document ingestion</h2>
          <p className="mt-1 text-xs text-slate-500">Select a tender from the catalogue, then upload its PDF, DOCX, TXT or Markdown source file.</p>
          <Field label="Selected tender"><select value={uploadId} onChange={e=>setUploadId(e.target.value)}><option value="">Choose tender</option>{props.tenders.map((t:Tender)=><option key={t.id} value={t.id}>{t.external_id} – {t.title}</option>)}</select></Field>
          <div onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(f)setFile(f);}} className="mt-3 rounded-xl border border-dashed border-slate-300 p-3"><label className="label">Original tender document · drop file here</label><input type="file" accept=".pdf,.docx,.txt,.md" onChange={e=>setFile(e.target.files?.[0]||null)}/><div className="mt-1 text-xs text-slate-400">{file?.name||"PDF, DOCX, TXT or Markdown · max 20 MB"}</div><button disabled={!uploadId||!file} className="btn btn-primary mt-3 w-full" onClick={()=>doUpload("tender_document")}><UploadCloud size={15}/> Upload and index</button></div>
          <div onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(f)setCorrFile(f);}} className="mt-3 rounded-xl border border-dashed border-amber-300 p-3"><label className="label">Corrigendum / amendment · drop file here</label><input type="file" accept=".pdf,.docx,.txt,.md" onChange={e=>setCorrFile(e.target.files?.[0]||null)}/><div className="mt-1 text-xs text-slate-400">{corrFile?.name||"Upload a revised notice or amendment"}</div><button disabled={!uploadId||!corrFile} className="btn btn-light mt-3 w-full" onClick={()=>doUpload("corrigendum")}><RefreshCw size={15}/> Upload and compare</button></div>
        </section>
        <section className="card p-5"><h2 className="font-bold">Ask this tender</h2><p className="mt-1 text-xs text-slate-500">Ask a question about uploaded tender clauses. Answers are generated from retrieved passages and include page-level sources.</p><form onSubmit={ask} className="mt-3 space-y-3"><Field label="Select tender"><select value={uploadId} onChange={e=>{setUploadId(e.target.value);setAnswer(null);}}><option value="">Choose tender</option>{props.tenders.map((t:Tender)=><option key={t.id} value={t.id}>{t.external_id} – {t.title}</option>)}</select></Field><Field label="Question"><textarea required minLength={3} rows={3} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="What is the minimum annual turnover requirement?"/></Field><button disabled={!uploadId||!question.trim()} className="btn btn-primary w-full"><Search size={15}/> Ask with cited evidence</button></form>{answer&&<div className="mt-4 rounded-xl bg-slate-50 p-4"><div className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{answer.answer}</div><div className="mt-3 space-y-2">{answer.citations?.map((c:any)=><div key={c.source_id} className="rounded-lg border border-slate-200 bg-white p-3 text-xs"><b>[{c.source_id}] {c.filename}</b><div className="mt-1 text-slate-500">Page {c.page||"not available"} · {c.section||"Section not identified"}</div>{c.source_url&&<a className="mt-1 inline-block text-brand" href={c.source_url} target="_blank" rel="noreferrer">Open source <ExternalLink size={11} className="inline"/></a>}</div>)}</div></div>}</section>
      </div>
    </div></>;
}

function AssessmentPage({assessment,token,openAssessment,run}:{assessment:any;token:string;openAssessment:(id:string)=>void;run:any}) {
  const [id,setId] = useState("");
  const [diffs,setDiffs] = useState<any[]>([]);
  const [checklist,setChecklist] = useState<any[]>(assessment?.checklist || []);
  useEffect(()=>setChecklist(assessment?.checklist || []),[assessment?.id]);
  const loadDiffs = async(tenderId:string)=>{const d=await request(`/api/v1/documents/tenders/${tenderId}/corrigenda`,token);setDiffs(d);};
  const toggle = (item:any,checked:boolean)=>run(async()=>{
    await request(`/api/v1/eligibility/assessments/${assessment.id}/checklist/${item.id}`,token,{method:"PATCH",body:JSON.stringify({is_completed:checked})});
    const updated=await request(`/api/v1/eligibility/assessments/${assessment.id}`,token);
    setChecklist(updated.checklist);
  });
  const report=assessment?.report;
  return <><PageHeading eyebrow="Bid decision support" title="Bid readiness report" description="Review requirement-level evidence, missing information and the actionable compliance checklist."/>
    <div className="card mb-5 p-5"><div className="font-bold">Open a saved assessment</div><div className="mt-3 flex gap-2"><input value={id} onChange={e=>setId(e.target.value)} placeholder="Paste assessment UUID"/><button className="btn btn-light" onClick={()=>openAssessment(id)} disabled={!id}>Load</button></div></div>
    {!assessment && <Empty text="Run an eligibility evaluation from a tender to see its bid-readiness report here."/>}
    {assessment && <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-[1fr_2fr]">
        <div className="card flex flex-col items-center justify-center p-6"><div className="text-xs font-bold uppercase tracking-wider text-slate-400">Fit score</div><div className="my-4 flex h-36 w-36 items-center justify-center rounded-full" style={{background:`conic-gradient(#2458d3 ${(Number(report?.score)||0)*3.6}deg, #e9eef6 0deg)`}}><div className="flex h-28 w-28 flex-col items-center justify-center rounded-full bg-white"><div className="text-4xl font-black text-brand">{report?.score ?? "—"}</div><div className="text-[10px] font-bold text-slate-400">OUT OF 100</div></div></div><Status value={report?.recommendation||"REVIEW_REQUIRED"}/><p className="mt-3 text-center text-xs text-slate-500">A prioritization indicator, not a legal eligibility decision.</p></div>
        <div className="card p-5"><div className="font-bold text-ink">Assessment summary</div><div className="mt-3 mb-3 grid gap-2 rounded-lg bg-blue-50 p-3 text-xs text-slate-700 sm:grid-cols-2"><div><b>Estimated tender value</b><div className="mt-1">{money(report?.estimated_value_inr)}</div></div><div><b>Extracted submission deadline</b><div className="mt-1">{report?.submission_deadline||"Not found in indexed text"}</div></div></div><div className="space-y-2">{(report?.checks||[]).map((x:any,i:number)=><div key={i} className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 py-2 text-sm"><div className="font-medium">{x.requirement}<div className="text-xs font-normal text-slate-500">{x.detail}</div>{x.source_page&&<div className="text-xs text-brand">{x.source_document||"Tender document"} · page {x.source_page}{x.source_quote?` · “${x.source_quote}”`:""}</div>}</div><Status value={x.status}/></div>)}</div></div>
      </div>
      {(report?.checks||[]).some((x:any)=>/MSME|DPIIT|exemption|relaxation/i.test(x.detail||"")) && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><div className="font-bold">Tender-specific MSME / Startup concession needs verification</div><p className="mt-1 text-xs leading-5">The tender text appears to mention a relaxation or exemption. Confirm that the company's Udyam or DPIIT recognition, category, validity and tender-specific conditions meet the exact clause before relying on it.</p></div>}
      <div className="card p-5"><div className="flex items-center justify-between"><h2 className="font-bold">Bid-readiness checklist</h2><span className="pill pill-blue">{checklist.filter((x:any)=>x.is_completed).length}/{checklist.length} completed</span></div>
        <div className="mt-4 space-y-3">{checklist.map((item:any)=><label key={item.id||item.title} className="flex items-start gap-3 rounded-xl bg-slate-50 p-3"><input type="checkbox" className="mt-1 h-4 w-4" checked={!!item.is_completed} onChange={e=>toggle(item,e.target.checked)} disabled={!item.id}/><span className="flex-1"><span className="text-sm font-bold">{item.title}</span><span className="mt-1 block text-xs text-slate-500">{item.required_action}</span>{item.source_page&&<span className="mt-1 block text-xs text-brand">Source: page {item.source_page}</span>}</span><Status value={item.status}/></label>)}
          {checklist.length===0&&<Empty text="No outstanding checklist items were generated."/ >}</div>
      </div>
      <div className="card p-5"><h2 className="font-bold">Limitations and human review</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-600">{(report?.limitations||[]).map((x:string,i:number)=><li key={i}>{x}</li>)}</ul></div>
      <div className="card p-5"><h2 className="font-bold">Corrigendum comparison</h2><button className="btn btn-light mt-3" onClick={()=>loadDiffs(report?.tender_id||assessment.tender_id).catch(e=>alert(e.message))}><RefreshCw size={14}/> Load detected changes</button><div className="mt-3 space-y-2">{diffs.map((d:any)=><div key={d.id} className="rounded-lg bg-amber-50 p-3 text-sm"><div className="font-bold">{d.change_type}</div><div className="mt-1 text-xs text-slate-600">Previous: {d.old_value||"Not found"}<br/>Updated: {d.new_value||"Not found"}</div><p className="mt-1 text-xs">{d.explanation}</p></div>)}{diffs.length===0&&<p className="text-xs text-slate-400">No changes loaded yet.</p>}</div></div>
    </div>}
  </>;
}
