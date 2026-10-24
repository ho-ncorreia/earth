import { NavLink, Route, Routes, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Activity, ArrowRight, Bot, GitBranch, Globe2, LayoutDashboard, LogOut, Menu, MessageCircle, PanelLeftClose, PanelLeftOpen, Plus, Send, ShieldCheck, Users, X } from 'lucide-react'
import { api, refreshCsrf, type AuditEvent, type Page, type User } from './api'
import { en } from './i18n/en'
import { fr } from './i18n/fr'

type Language = 'en' | 'fr'
type Copy = typeof en | typeof fr
type DashboardData = { database: string; studies: number; open_risks: number; critical_risks: number }
type StudyRecord = { id: number; identifier: string; title: string; description: string; architecture_domain: string; status: string; target_review_date: string | null; created_at: string; row_version: number }
type RiskRecord = { id: number; identifier: string; title: string; description: string; probability: number; impact: number; inherent_score: number; residual_score: number | null; criticality: string; status: string; study_id: number | null; created_at: string; row_version: number }
type DecisionRecord = { id: number; number: string; title: string; context: string; problem_statement: string; options: { id: number; title: string; advantages: string; disadvantages: string }[]; selected_option: string; decision_rationale: string; status: string; decision_authority: string; decision_date: string | null; rejection_rationale: string; version: number; row_version: number; related_study_ids: number[]; related_risk_ids: number[] }
type DecisionVersion = { version: number; snapshot: Record<string, unknown>; created_at: string }
type ChatSource = { id: number; source_type: string; object_id: number; title: string; excerpt: string }
type ChatMessage = { id: number; role: string; content: string; sources: ChatSource[]; model: string; created_at: string }
type Conversation = { id: number; title: string; updated_at: string }

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [language, setLanguage] = useState<Language>('en')
  const [ready, setReady] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [notice, setNotice] = useState('')
  const t: Copy = language === 'en' ? en : fr
  const location = useLocation()

  useEffect(() => {
    refreshCsrf().then(() => api<User>('/auth/me')).then(setUser).catch(() => setUser(null)).finally(() => setReady(true))
  }, [])
  useEffect(() => setSidebarOpen(false), [location.pathname])
  useEffect(() => { document.documentElement.lang = language }, [language])

  async function signIn(email: string, password: string) {
    setUser(await api<User>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }))
  }
  async function signOut() {
    try { await api('/auth/logout', { method: 'POST' }) } finally { setUser(null) }
  }

  if (!ready) return <div className="boot-screen">{t.loading}</div>
  if (!user) return <Login t={t} language={language} onLanguageChange={setLanguage} onSignIn={signIn} />

  const isAdmin = user.role.name === 'Administrator'
  const currentPage = location.pathname.startsWith('/users') ? t.people : location.pathname.startsWith('/audit') ? t.audit : location.pathname.startsWith('/studies') ? t.studies : location.pathname.startsWith('/risks') ? t.risks : location.pathname.startsWith('/decisions') ? t.decisions : location.pathname.startsWith('/assistant') ? t.assistant : t.dashboard
  return <div className={`app-shell ${sidebarCollapsed ? 'shell-collapsed' : ''}`}>
    {sidebarOpen && <button aria-label="Close navigation" className="mobile-scrim" onClick={() => setSidebarOpen(false)} />}
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <div className="brand-lockup"><div className="brand-mark">EA</div><div><strong>{t.appName}</strong><span>{t.eyebrow}</span></div><button aria-label="Close navigation" className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)}><X size={19} /></button></div>
      <div className="nav-section-label">{t.workspace}</div>
      <nav className="primary-nav" aria-label={t.workspace}><NavItem to="/" icon={<LayoutDashboard size={18} />} label={t.dashboard} end /><NavItem to="/studies" icon={<Activity size={18} />} label={t.studies} /><NavItem to="/decisions" icon={<GitBranch size={18} />} label={t.decisions} /><NavItem to="/risks" icon={<ShieldCheck size={18} />} label={t.risks} /><NavItem to="/assistant" icon={<MessageCircle size={18} />} label={t.assistant} /></nav>
      {isAdmin && <><div className="nav-section-label admin-label">{t.administration}</div><nav className="primary-nav" aria-label={t.administration}>
        <NavItem to="/users" icon={<Users size={18} />} label={t.people} /><NavItem to="/audit" icon={<Activity size={18} />} label={t.audit} />
      </nav></>}
      <div className="sidebar-spacer" /><div className="sidebar-footnote" title={t.foundationOnline}><span className="status-dot" /><span>{t.foundationOnline}</span></div>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <button aria-label={sidebarCollapsed ? t.expandNavigation : t.collapseNavigation} title={sidebarCollapsed ? t.expandNavigation : t.collapseNavigation} className="icon-button collapse-toggle" onClick={() => setSidebarCollapsed(!sidebarCollapsed)}>{sidebarCollapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}</button>
        <button aria-label="Open navigation" className="icon-button menu-toggle" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button>
        <div className="breadcrumbs"><span>EA Workbench</span><span className="crumb-divider">/</span><strong>{currentPage}</strong></div>
        <div className="topbar-actions">
          <label className="language-control"><Globe2 size={16} /><span className="sr-only">{t.language}</span><select value={language} onChange={(event) => setLanguage(event.target.value as Language)} aria-label={t.language}><option value="en">EN</option><option value="fr">FR</option></select></label>
          <div className="profile-chip"><span className="avatar">{user.display_name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</span><span className="profile-name">{user.display_name}</span><button className="icon-button signout" onClick={signOut} aria-label={t.signOut} title={t.signOut}><LogOut size={17} /></button></div>
        </div>
      </header>
      {notice && <div role="status" className="toast"><ShieldCheck size={17} />{notice}<button className="icon-button" aria-label="Dismiss" onClick={() => setNotice('')}><X size={16} /></button></div>}
      <div className="page-content"><Routes>
        <Route path="/" element={<Dashboard t={t} isAdmin={isAdmin} />} />
        <Route path="/studies" element={<StudiesPage t={t} user={user} />} />
        <Route path="/risks" element={<RisksPage t={t} user={user} />} />
        <Route path="/decisions" element={<DecisionsPage t={t} user={user} />} />
        <Route path="/decisions/:decisionId" element={<DecisionDetailPage t={t} user={user} />} />
        <Route path="/assistant" element={<AssistantPage t={t} user={user} />} />
        <Route path="/users" element={isAdmin ? <UsersPage t={t} onNotice={setNotice} /> : <Denied t={t} />} />
        <Route path="/audit" element={isAdmin ? <AuditPage t={t} /> : <Denied t={t} />} />
        <Route path="*" element={<Dashboard t={t} isAdmin={isAdmin} />} />
      </Routes></div>
    </main>
  </div>
}

function NavItem({ to, icon, label, end }: { to: string; icon: ReactNode; label: string; end?: boolean }) {
  return <NavLink to={to} end={end} title={label} aria-label={label} className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>{icon}<span>{label}</span></NavLink>
}

function translatedRole(name: string, t: Copy): string {
  const keys: Record<string, keyof Copy> = {
    Administrator: 'administrator',
    'Enterprise Architect': 'enterpriseArchitect',
    'Solution Architect': 'solutionArchitect',
    'Technical Architect': 'technicalArchitect',
    'Reviewer / ARB Member': 'reviewer',
    'Read-only User': 'readOnlyUser',
  }
  return keys[name] ? t[keys[name]] : name
}

function Login({ t, language, onLanguageChange, onSignIn }: { t: Copy; language: Language; onLanguageChange: (language: Language) => void; onSignIn: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true)
    try { await onSignIn(email, password) } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) } finally { setBusy(false) }
  }
  return <main className="login-screen"><div className="login-art"><div className="login-art-grid" /><div className="login-copy"><div className="brand-mark brand-mark-light">EA</div><p className="login-kicker">{t.eyebrow}</p><h1>{t.welcome}</h1><p>{t.welcomeSub}</p></div><div className="login-coordinate">{t.governanceTraceability}</div></div><form className="login-form" onSubmit={submit}><div className="login-locale"><Globe2 size={16} /><span className="sr-only">{t.language}</span><select value={language} onChange={(event) => onLanguageChange(event.target.value as Language)} aria-label={t.language}><option value="en">EN</option><option value="fr">FR</option></select></div><div className="form-overline">{t.loginAccess}</div><h2>{t.signIn}</h2><label>{t.email}<input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>{t.password}<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>{error && <div role="alert" className="form-error">{error}</div>}<button className="button-primary" disabled={busy}>{busy ? t.loading : t.continue}<ArrowRight size={17} /></button><div className="login-foot">{t.localSession}</div></form></main>
}

function PageHeading({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="page-eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>
}

function Dashboard({ t, isAdmin }: { t: Copy; isAdmin: boolean }) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    const activity = isAdmin ? api<Page<AuditEvent>>('/audit-events?limit=5') : Promise.resolve({ items: [], total: 0, limit: 5, offset: 0 })
    Promise.all([api<DashboardData>('/dashboard'), activity]).then(([dashboard, audit]) => { setData(dashboard); setEvents(audit.items) }).catch((reason) => setError(reason instanceof Error ? reason.message : t.error))
  }, [isAdmin, t.error])
  return <>
    <PageHeading eyebrow={t.workspaceFoundation} title={t.welcome} subtitle={t.welcomeSub} action={<span className="live-pill"><span className="status-dot" />{t.lastUpdated}</span>} />
    {error ? <ErrorBanner message={error} /> : !data ? <div className="loading-line">{t.loading}</div> : <>
      <div className="metric-grid"><Metric t={t} label={t.studyCount} value={data.studies} icon={<LayoutDashboard size={18} />} tone="blue" /><Metric t={t} label={t.openRisks} value={data.open_risks} icon={<ShieldCheck size={18} />} tone="red" /><Metric t={t} label={t.criticalRisks} value={data.critical_risks} icon={<Activity size={18} />} tone="slate" />
        <div className="metric-card health-card"><div className="metric-top"><span>{t.service}</span><span className="health-icon"><span className="status-dot" /></span></div><strong className="health-value">{t.ready}</strong><div className="health-detail">{t.database} <b>{data.database}</b></div></div>
      </div>
      {isAdmin && <section className="activity-section"><div className="section-heading"><div><h2>{t.recentActivity}</h2><p>{t.activitySub}</p></div><NavLink to="/audit" className="text-link">{t.viewAudit}<ArrowRight size={15} /></NavLink></div><AuditTable events={events} t={t} /></section>}
    </>}
  </>
}

function Metric({ label, value, icon, tone, t }: { label: string; value: number; icon: ReactNode; tone: string; t: Copy }) {
  return <div className="metric-card"><div className="metric-top"><span>{label}</span><span className={`metric-icon ${tone}`}>{icon}</span></div><strong className="metric-value">{value.toLocaleString()}</strong><div className="metric-foot">{t.liveDatabase}</div></div>
}

const studyTransitions: Record<string, string[]> = {
  Draft: ['Draft', 'In Progress'], 'In Progress': ['In Progress', 'Draft', 'Ready for Review'],
  'Ready for Review': ['Ready for Review', 'In Progress', 'Under Review'],
  'Under Review': ['Under Review', 'In Progress', 'Approved'], Approved: ['Approved', 'Closed', 'Archived'],
  Closed: ['Closed', 'Archived'], Archived: ['Archived'],
}
const riskTransitions: Record<string, string[]> = {
  Identified: ['Identified', 'Assessed'], Assessed: ['Assessed', 'Treatment Defined'],
  'Treatment Defined': ['Treatment Defined', 'Mitigation in Progress', 'Monitoring'],
  'Mitigation in Progress': ['Mitigation in Progress', 'Monitoring', 'Treatment Defined'],
  Monitoring: ['Monitoring', 'Accepted', 'Mitigation in Progress', 'Closed'],
  Accepted: ['Accepted', 'Monitoring', 'Closed'], Closed: ['Closed'],
}

function DecisionsPage({ t, user }: { t: Copy; user: User }) {
  const [decisions, setDecisions] = useState<DecisionRecord[]>([])
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ title: '', context: '', problem_statement: '', decision_drivers: '', options: [{ title: '', advantages: '', disadvantages: '' }, { title: '', advantages: '', disadvantages: '' }] })
  const canWrite = user.role.permissions.includes('decisions.write')
  async function load() {
    try { setDecisions((await api<Page<DecisionRecord>>('/decisions?limit=100')).items); setError('') }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      await api('/decisions', { method: 'POST', body: JSON.stringify({ ...form, options: form.options.filter((option) => option.title.trim()), related_study_ids: [], related_risk_ids: [] }) })
      setShowForm(false); setForm({ title: '', context: '', problem_statement: '', decision_drivers: '', options: [{ title: '', advantages: '', disadvantages: '' }, { title: '', advantages: '', disadvantages: '' }] }); await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) } finally { setBusy(false) }
  }
  const visible = decisions.filter((decision) => `${decision.number} ${decision.title} ${decision.context}`.toLowerCase().includes(query.toLowerCase()))
  return <><PageHeading eyebrow={t.governanceTraceability} title={t.decisionsTitle} subtitle={t.decisionsSub} action={canWrite ? <button className="button-primary compact-button" onClick={() => setShowForm(true)}><GitBranch size={16} />{t.createDecision}</button> : undefined} />
    {error && <ErrorBanner message={error} />}<section className="data-section"><div className="table-toolbar"><div className="table-count">{decisions.length} <span>{t.decisions.toLowerCase()}</span></div><label className="table-search"><span className="sr-only">{t.search}</span><input placeholder={t.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label></div>
      <div className="table-scroll"><table><thead><tr><th>ADR</th><th>{t.title}</th><th>{t.status}</th><th>{t.versionHistory}</th></tr></thead><tbody>{visible.map((decision) => <tr key={decision.id}><td><NavLink className="record-link" to={`/decisions/${decision.id}`}>{decision.number}</NavLink></td><td>{decision.title}</td><td><span className={`decision-status decision-${decision.status.toLowerCase().replaceAll(' ', '-')}`}>{decision.status}</span></td><td>v{decision.version}</td></tr>)}{visible.length === 0 && <tr><td colSpan={4} className="empty-cell">{t.noDecisions}</td></tr>}</tbody></table></div>
    </section>
    {showForm && <div className="modal-backdrop"><form className="modal-panel decision-form" onSubmit={create}><div className="modal-title"><div><span className="page-eyebrow">{t.governanceTraceability}</span><h2>{t.createDecision}</h2></div><button type="button" className="icon-button" aria-label={t.cancel} onClick={() => setShowForm(false)}><X size={19} /></button></div>
      <label>{t.title}<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label>{t.decisionContext}<textarea value={form.context} onChange={(event) => setForm({ ...form, context: event.target.value })} /></label><label>{t.problemStatement}<textarea value={form.problem_statement} onChange={(event) => setForm({ ...form, problem_statement: event.target.value })} /></label><label>{t.decisionDrivers}<textarea value={form.decision_drivers} onChange={(event) => setForm({ ...form, decision_drivers: event.target.value })} /></label>
      <div className="option-editor"><h3>{t.consideredOptions}</h3>{form.options.map((option, index) => <fieldset key={index}><legend>{t.consideredOptions} {index + 1}</legend><label>{t.title}<input required value={option.title} onChange={(event) => setForm({ ...form, options: form.options.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.target.value } : item) })} /></label><label>{t.advantages}<textarea value={option.advantages} onChange={(event) => setForm({ ...form, options: form.options.map((item, itemIndex) => itemIndex === index ? { ...item, advantages: event.target.value } : item) })} /></label><label>{t.disadvantages}<textarea value={option.disadvantages} onChange={(event) => setForm({ ...form, options: form.options.map((item, itemIndex) => itemIndex === index ? { ...item, disadvantages: event.target.value } : item) })} /></label></fieldset>)}</div>
      <div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setShowForm(false)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.createDecision}<ArrowRight size={16} /></button></div>
    </form></div>}
  </>
}

function DecisionDetailPage({ t, user }: { t: Copy; user: User }) {
  const { decisionId = '' } = useParams()
  const [decision, setDecision] = useState<DecisionRecord | null>(null)
  const [versions, setVersions] = useState<DecisionVersion[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [authority, setAuthority] = useState('')
  const [decisionDate, setDecisionDate] = useState('')
  const [rejectionRationale, setRejectionRationale] = useState('')
  const [selectedOption, setSelectedOption] = useState('')
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({ title: '', context: '', problem_statement: '', decision_rationale: '' })
  const [fromVersion, setFromVersion] = useState('')
  const [toVersion, setToVersion] = useState('')
  const [diff, setDiff] = useState<Record<string, { from: unknown; to: unknown }> | null>(null)
  const canWrite = user.role.permissions.includes('decisions.write')
  const canReview = user.role.permissions.includes('decisions.review')
  async function load() {
    try {
      const record = await api<DecisionRecord>(`/decisions/${decisionId}`)
      const history = await api<DecisionVersion[]>(`/decisions/${decisionId}/versions`)
      setDecision(record); setVersions(history); setAuthority(record.decision_authority); setDecisionDate(record.decision_date ?? ''); setRejectionRationale(record.rejection_rationale); setSelectedOption(record.selected_option || record.options[0]?.title || '')
      setEditForm({ title: record.title, context: record.context, problem_statement: record.problem_statement, decision_rationale: record.decision_rationale }); setError('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [decisionId])
  async function update(changes: Record<string, unknown>) {
    if (!decision) return
    setBusy(true); setError('')
    try { await api(`/decisions/${decision.id}`, { method: 'PATCH', headers: { 'If-Match': `"${decision.row_version}"` }, body: JSON.stringify(changes) }); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  if (error && !decision) return <><ErrorBanner message={error} /><NavLink to="/decisions" className="text-link">{t.decisions}</NavLink></>
  if (!decision) return <div className="loading-line">{t.loading}</div>
  return <><PageHeading eyebrow={decision.number} title={decision.title} subtitle={`${decision.status} · v${decision.version}`} action={<NavLink to="/decisions" className="text-link">{t.decisions}</NavLink>} />
    {error && <ErrorBanner message={error} />}<div className="decision-layout"><section className="decision-document">
      {editing ? <div className="edit-fields"><label>{t.title}<input value={editForm.title} onChange={(event) => setEditForm({ ...editForm, title: event.target.value })} /></label><label>{t.decisionContext}<textarea value={editForm.context} onChange={(event) => setEditForm({ ...editForm, context: event.target.value })} /></label><label>{t.problemStatement}<textarea value={editForm.problem_statement} onChange={(event) => setEditForm({ ...editForm, problem_statement: event.target.value })} /></label><label>{t.rationale}<textarea value={editForm.decision_rationale} onChange={(event) => setEditForm({ ...editForm, decision_rationale: event.target.value })} /></label><div className="modal-actions"><button className="button-secondary" onClick={() => setEditing(false)}>{t.cancel}</button><button className="button-primary" disabled={busy} onClick={() => { void update(editForm); setEditing(false) }}>{t.save}<ArrowRight size={16} /></button></div></div> : <>
        <DecisionSection title={t.decisionContext} content={decision.context} /><DecisionSection title={t.problemStatement} content={decision.problem_statement} />
        <div className="decision-section"><h2>{t.consideredOptions}</h2>{decision.options.map((option) => <article className="option-row" key={option.id}><h3>{option.title}</h3><div className="option-columns"><div><b>{t.advantages}</b><p>{option.advantages || '—'}</p></div><div><b>{t.disadvantages}</b><p>{option.disadvantages || '—'}</p></div></div></article>)}</div>
        <DecisionSection title={t.rationale} content={decision.decision_rationale} /><DecisionSection title={t.selectedOption} content={decision.selected_option} />
      </>}
      {canWrite && <button className="button-secondary edit-decision" disabled={busy} onClick={() => setEditing(!editing)}>{editing ? t.cancel : t.editDecision}</button>}
      {(decision.status === 'Draft' && canWrite || decision.status === 'Proposed' && canWrite) && <button className="button-primary decision-action" disabled={busy} onClick={() => void update({ status: decision.status === 'Draft' ? 'Proposed' : 'Under Review' })}>{decision.status === 'Draft' ? t.submitForReview : t.requestReview}<ArrowRight size={16} /></button>}
      {decision.status === 'Under Review' && canReview && <div className="review-panel"><h2>{t.reviewDecision}</h2><label>{t.selectedOption}<select value={selectedOption} onChange={(event) => setSelectedOption(event.target.value)}>{decision.options.map((option) => <option key={option.id}>{option.title}</option>)}</select></label><label>{t.authority}<input value={authority} onChange={(event) => setAuthority(event.target.value)} /></label><label>{t.decisionDate}<input type="date" value={decisionDate} onChange={(event) => setDecisionDate(event.target.value)} /></label><button className="button-primary" disabled={busy} onClick={() => void update({ status: 'Accepted', selected_option: selectedOption, decision_authority: authority, decision_date: decisionDate })}>{t.acceptDecision}<ShieldCheck size={16} /></button><label>{t.rejectionRationale}<textarea value={rejectionRationale} onChange={(event) => setRejectionRationale(event.target.value)} /></label><button className="button-secondary reject-button" disabled={busy || !rejectionRationale.trim()} onClick={() => void update({ status: 'Rejected', rejection_rationale: rejectionRationale })}>{t.rejectDecision}</button></div>}
    </section><aside className="decision-aside"><section className="version-panel"><h2>{t.versionHistory}</h2>{versions.map((item) => <div className="version-row" key={item.version}><b>v{item.version}</b><span>{String(item.snapshot.title ?? '')}</span><time>{new Date(item.created_at).toLocaleDateString()}</time></div>)}{versions.length > 1 && <><h3>{t.compareVersions}</h3><div className="compare-fields"><select aria-label={`${t.compareVersions} from`} value={fromVersion} onChange={(event) => setFromVersion(event.target.value)}><option value="">v{versions[0].version}</option>{versions.map((item) => <option key={item.version} value={item.version}>{`v${item.version}`}</option>)}</select><select aria-label={`${t.compareVersions} to`} value={toVersion} onChange={(event) => setToVersion(event.target.value)}><option value="">v{versions.at(-1)?.version}</option>{versions.map((item) => <option key={item.version} value={item.version}>{`v${item.version}`}</option>)}</select><button className="button-secondary" onClick={() => { const start = fromVersion || String(versions[0].version); const end = toVersion || String(versions.at(-1)?.version); setFromVersion(start); setToVersion(end); void api<{ changes: Record<string, { from: unknown; to: unknown }> }>(`/decisions/${decision.id}/compare?from_version=${start}&to_version=${end}`).then((result) => setDiff(result.changes)).catch((reason) => setError(String(reason))) }}>{t.compare}</button></div>{diff && <div className="diff-list">{Object.entries(diff).map(([field, change]) => <div key={field}><b>{field}</b><span>{String(change.from ?? '—')} → {String(change.to ?? '—')}</span></div>)}{Object.keys(diff).length === 0 && <p>{t.noDifferences}</p>}</div>}</>}</section></aside></div>
  </>
}

function DecisionSection({ title, content }: { title: string; content: string }) {
  return <section className="decision-section"><h2>{title}</h2><p>{content || '—'}</p></section>
}

function AssistantPage({ t, user }: { t: Copy; user: User }) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const canUse = user.role.permissions.includes('assistant.use')
  async function loadConversations() {
    if (!canUse) return
    try { setConversations((await api<Page<Conversation>>('/ai/conversations')).items) }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void loadConversations() }, [canUse])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  async function openConversation(conversation: Conversation) {
    try {
      const detail = await api<{ id: number; messages: ChatMessage[] }>(`/ai/conversations/${conversation.id}`)
      setConversationId(conversation.id); setMessages(detail.messages); setError('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  async function send(event: FormEvent) {
    event.preventDefault()
    const text = question.trim()
    if (!text || busy || !canUse) return
    setBusy(true); setError(''); setQuestion('')
    try {
      const result = await api<{ conversation: Conversation; user_message: ChatMessage; assistant_message: ChatMessage }>('/ai/ask', { method: 'POST', body: JSON.stringify({ question: text, conversation_id: conversationId }) })
      setConversationId(result.conversation.id); setMessages((current) => [...current, result.user_message, result.assistant_message]); await loadConversations()
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.mistralUnavailable); setQuestion(text) }
    finally { setBusy(false) }
  }
  return <div className="assistant-workspace"><aside className="conversation-rail"><div className="conversation-heading"><h2>{t.conversations}</h2><button aria-label={t.newConversation} title={t.newConversation} className="icon-button" onClick={() => { setConversationId(null); setMessages([]); setError('') }}><Plus size={18} /></button></div><button className={`conversation-new ${conversationId === null ? 'conversation-selected' : ''}`} onClick={() => { setConversationId(null); setMessages([]); setError('') }}><Plus size={15} />{t.newConversation}</button>{conversations.map((conversation) => <button className={`conversation-item ${conversationId === conversation.id ? 'conversation-selected' : ''}`} key={conversation.id} onClick={() => void openConversation(conversation)}><MessageCircle size={15} /><span>{conversation.title}</span></button>)}</aside>
    <section className="chat-panel"><PageHeading eyebrow={t.governanceTraceability} title={t.assistantTitle} subtitle={t.assistantSub} />
      <div className="chat-messages">{messages.length === 0 && <div className="chat-empty"><span className="assistant-mark"><Bot size={25} /></span><h2>{t.assistantTitle}</h2><p>{t.noConversation}</p><div className="chat-hints"><button onClick={() => setQuestion(t.decisionsSub)}>{t.decisions}</button><button onClick={() => setQuestion(t.risksSub)}>{t.risks}</button><button onClick={() => setQuestion(t.studiesSub)}>{t.studies}</button></div></div>}{messages.map((message) => <article className={`chat-message message-${message.role}`} key={message.id}><div className="message-role">{message.role === 'assistant' ? t.assistant : t.user}</div><p>{message.content}</p>{message.sources?.length > 0 && <div className="source-list"><span>{t.sources}</span>{message.sources.map((source) => { const searchableTitle = source.title.replace(/^\[R\d+\]\s*/, '').split(' · ').slice(1).join(' · '); const target = source.source_type === 'decision' ? `/decisions/${source.object_id}` : `/${source.source_type === 'study' ? 'studies' : 'risks'}?search=${encodeURIComponent(searchableTitle)}`; return <NavLink key={source.id} to={target} title={source.excerpt}>{source.title}</NavLink> })}</div>}</article>)}{busy && <div className="chat-thinking"><span className="status-dot" />{t.loading}</div>}<div ref={bottomRef} /></div>
      {error && <div role="alert" className="chat-error">{error}</div>}<form className="chat-compose" onSubmit={send}><textarea aria-label={t.askQuestion} placeholder={t.askQuestion} value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} /><button className="button-primary" aria-label={t.send} title={t.send} disabled={busy || !question.trim()}><Send size={17} /></button><span className="chat-privacy">{t.assistantSub}</span></form>
    </section></div>
}

function StudiesPage({ t, user }: { t: Copy; user: User }) {
  const [studies, setStudies] = useState<StudyRecord[]>([])
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('search') ?? '')
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', architecture_domain: '', business_context: '', business_objectives: '', scope: '', out_of_scope: '' })
  const canWrite = user.role.permissions.includes('studies.write')
  async function load() {
    try { setStudies((await api<Page<StudyRecord>>('/studies?limit=100')).items); setError('') }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try { await api('/studies', { method: 'POST', body: JSON.stringify(form) }); setShowForm(false); setForm({ title: '', description: '', architecture_domain: '', business_context: '', business_objectives: '', scope: '', out_of_scope: '' }); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  async function changeStatus(study: StudyRecord, status: string) {
    try { await api(`/studies/${study.id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.invalidAction) }
  }
  const visible = studies.filter((item) => `${item.identifier} ${item.title} ${item.architecture_domain}`.toLowerCase().includes(query.toLowerCase()))
  return <><PageHeading eyebrow={t.workspaceFoundation} title={t.studiesTitle} subtitle={t.studiesSub} action={canWrite ? <button className="button-primary compact-button" onClick={() => setShowForm(true)}><Users size={16} />{t.createStudy}</button> : undefined} />
    {error && <ErrorBanner message={error} />}<section className="data-section"><div className="table-toolbar"><div className="table-count">{studies.length} <span>{t.studies.toLowerCase()}</span></div><label className="table-search"><span className="sr-only">{t.search}</span><input placeholder={t.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label></div>
      <div className="table-scroll"><table><thead><tr><th>{t.study}</th><th>{t.domain}</th><th>{t.studyStatus}</th><th>{t.date}</th></tr></thead><tbody>{visible.map((study) => <tr key={study.id}><td><div className="record-cell"><b>{study.title}</b><small>{study.identifier}</small></div></td><td>{study.architecture_domain || '—'}</td><td>{canWrite ? <select className="status-select" aria-label={`${t.studyStatus}: ${study.title}`} value={study.status} onChange={(event) => void changeStatus(study, event.target.value)}>{(studyTransitions[study.status] ?? [study.status]).map((status) => <option key={status}>{status}</option>)}</select> : <span className="status-label">{study.status}</span>}</td><td>{study.target_review_date ? new Date(study.target_review_date).toLocaleDateString() : '—'}</td></tr>)}{visible.length === 0 && <tr><td colSpan={4} className="empty-cell">{t.noStudies}</td></tr>}</tbody></table></div>
    </section>{showForm && <div className="modal-backdrop"><form className="modal-panel" onSubmit={create}><div className="modal-title"><div><span className="page-eyebrow">{t.workspaceFoundation}</span><h2>{t.createStudy}</h2></div><button type="button" className="icon-button" aria-label={t.cancel} onClick={() => setShowForm(false)}><X size={19} /></button></div><label>{t.title}<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label>{t.description}<input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label><label>{t.domain}<input value={form.architecture_domain} onChange={(event) => setForm({ ...form, architecture_domain: event.target.value })} /></label><label>{t.businessContext}<textarea value={form.business_context} onChange={(event) => setForm({ ...form, business_context: event.target.value })} /></label><div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setShowForm(false)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.createStudy}<ArrowRight size={16} /></button></div></form></div>}
  </>
}

function RisksPage({ t, user }: { t: Copy; user: User }) {
  const [risks, setRisks] = useState<RiskRecord[]>([])
  const [studies, setStudies] = useState<StudyRecord[]>([])
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('search') ?? '')
  const canWrite = user.role.permissions.includes('risks.write')
  const [form, setForm] = useState({ title: '', description: '', probability: '2', impact: '2', study_id: '' })
  async function load() {
    try {
      const [riskPage, studyPage] = await Promise.all([api<Page<RiskRecord>>('/risks?limit=100'), api<Page<StudyRecord>>('/studies?limit=100')])
      setRisks(riskPage.items); setStudies(studyPage.items); setError('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    const payload = { ...form, probability: Number(form.probability), impact: Number(form.impact), study_id: form.study_id ? Number(form.study_id) : null }
    try { await api('/risks', { method: 'POST', body: JSON.stringify(payload) }); setShowForm(false); setForm({ title: '', description: '', probability: '2', impact: '2', study_id: '' }); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  async function changeStatus(risk: RiskRecord, status: string) {
    try { await api(`/risks/${risk.id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.invalidAction) }
  }
  const criticalityLabels: Record<string, string> = { Critical: t.critical, High: t.high, Medium: t.medium, Low: t.low }
  const visibleRisks = risks.filter((risk) => `${risk.identifier} ${risk.title} ${risk.description}`.toLowerCase().includes(query.toLowerCase()))
  return <><PageHeading eyebrow={t.governanceTraceability} title={t.risksTitle} subtitle={t.risksSub} action={canWrite ? <button className="button-primary compact-button" onClick={() => setShowForm(true)}><ShieldCheck size={16} />{t.createRisk}</button> : undefined} />
    {error && <ErrorBanner message={error} />}<section className="data-section"><div className="table-toolbar"><div className="table-count">{visibleRisks.length} <span>{t.risks.toLowerCase()}</span></div><label className="table-search"><span className="sr-only">{t.search}</span><input placeholder={t.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label></div><div className="table-scroll"><table><thead><tr><th>{t.risksTitle}</th><th>{t.inherentScore}</th><th>{t.residualScore}</th><th>{t.criticality}</th><th>{t.riskStatus}</th></tr></thead><tbody>{visibleRisks.map((risk) => <tr key={risk.id}><td><div className="record-cell"><b>{risk.title}</b><small>{risk.identifier}</small></div></td><td><span className="score-cell">{risk.inherent_score}<small>{risk.probability} × {risk.impact}</small></span></td><td>{risk.residual_score ?? '—'}</td><td><span className={`criticality-tag criticality-${risk.criticality.toLowerCase()}`}>{criticalityLabels[risk.criticality] ?? risk.criticality}</span></td><td>{canWrite ? <select className="status-select" aria-label={`${t.riskStatus}: ${risk.title}`} value={risk.status} onChange={(event) => void changeStatus(risk, event.target.value)}>{(riskTransitions[risk.status] ?? [risk.status]).map((status) => <option key={status}>{status}</option>)}</select> : <span className="status-label">{risk.status}</span>}</td></tr>)}{visibleRisks.length === 0 && <tr><td colSpan={5} className="empty-cell">{t.noRisks}</td></tr>}</tbody></table></div></section>
    {showForm && <div className="modal-backdrop"><form className="modal-panel" onSubmit={create}><div className="modal-title"><div><span className="page-eyebrow">{t.governanceTraceability}</span><h2>{t.createRisk}</h2></div><button type="button" className="icon-button" aria-label={t.cancel} onClick={() => setShowForm(false)}><X size={19} /></button></div><label>{t.title}<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label>{t.description}<textarea required value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label><div className="field-pair"><label>{t.probability}<select value={form.probability} onChange={(event) => setForm({ ...form, probability: event.target.value })}>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.impact}<select value={form.impact} onChange={(event) => setForm({ ...form, impact: event.target.value })}>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label></div><label>{t.study}<select value={form.study_id} onChange={(event) => setForm({ ...form, study_id: event.target.value })}><option value="">—</option>{studies.map((study) => <option key={study.id} value={study.id}>{study.identifier} · {study.title}</option>)}</select></label><div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setShowForm(false)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.createRisk}<ArrowRight size={16} /></button></div></form></div>}
  </>
}

function UsersPage({ t, onNotice }: { t: Copy; onNotice: (value: string) => void }) {
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<User['role'][]>([])
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ email: '', display_name: '', role_id: '', temporary_password: '' })
  async function load() {
    try {
      const [page, availableRoles] = await Promise.all([api<Page<User>>('/users'), api<User['role'][]>('/users/roles')])
      setUsers(page.items); setRoles(availableRoles); setError('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      await api('/users', { method: 'POST', body: JSON.stringify({ ...form, role_id: Number(form.role_id) }) })
      setShowForm(false); setForm({ email: '', display_name: '', role_id: '', temporary_password: '' }); onNotice(t.userCreated); await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) } finally { setBusy(false) }
  }
  const filtered = users.filter((item) => `${item.display_name} ${item.email} ${item.role.name}`.toLowerCase().includes(query.toLowerCase()))
  return <>
    <PageHeading eyebrow={t.accessControl} title={t.usersTitle} subtitle={t.usersSub} action={<button className="button-primary compact-button" onClick={() => setShowForm(true)}><Users size={16} />{t.createUser}</button>} />
    {error && <ErrorBanner message={error} />}
    <section className="data-section"><div className="table-toolbar"><div className="table-count">{users.length} <span>{t.accounts}</span></div><label className="table-search"><span className="sr-only">{t.search}</span><input placeholder={t.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label></div>
      <div className="table-scroll"><table><thead><tr><th>{t.user}</th><th>{t.role}</th><th>{t.status}</th><th>{t.date}</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.id}><td><div className="person-cell"><span className="avatar avatar-small">{item.display_name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</span><span><b>{item.display_name}</b><small>{item.email}</small></span></div></td><td><span className="role-label">{item.role.name}</span></td><td><span className="status-label"><span className="status-dot" />{item.is_active ? t.active : t.inactive}</span></td><td>{new Date(item.created_at).toLocaleDateString()}</td></tr>)}{filtered.length === 0 && <tr><td colSpan={4} className="empty-cell">{t.emptyUsers}</td></tr>}</tbody></table></div>
    </section>
    {showForm && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowForm(false) }}><form className="modal-panel" onSubmit={create}><div className="modal-title"><div><span className="page-eyebrow">ACCESS CONTROL</span><h2>{t.createUser}</h2></div><button type="button" className="icon-button" aria-label={t.cancel} onClick={() => setShowForm(false)}><X size={19} /></button></div>
      <label>{t.displayName}<input required value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} /></label><label>{t.email}<input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
      <label>{t.role}<select required value={form.role_id} onChange={(event) => setForm({ ...form, role_id: event.target.value })}><option value="">{t.selectRole}</option>{roles.map((role) => <option key={role.id} value={role.id}>{translatedRole(role.name, t)}</option>)}</select></label>
      <label>{t.temporaryPassword}<input type="password" minLength={12} required value={form.temporary_password} onChange={(event) => setForm({ ...form, temporary_password: event.target.value })} /></label>{error && <div role="alert" className="form-error">{error}</div>}
      <div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setShowForm(false)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.createUser}<ArrowRight size={16} /></button></div>
    </form></div>}
  </>
}

function AuditPage({ t }: { t: Copy }) {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [error, setError] = useState('')
  useEffect(() => { api<Page<AuditEvent>>('/audit-events?limit=100').then((page) => setEvents(page.items)).catch((reason) => setError(reason instanceof Error ? reason.message : t.error)) }, [t.error])
  return <><PageHeading eyebrow="GOVERNANCE / TRACEABILITY" title={t.auditTitle} subtitle={t.auditSub} />{error ? <ErrorBanner message={error} /> : <section className="data-section"><div className="table-toolbar"><div className="table-count">{events.length} <span>{t.events.toLowerCase()}</span></div></div><AuditTable events={events} t={t} /></section>}</>
}

function AuditTable({ events, t }: { events: AuditEvent[]; t: Copy }) {
  return <div className="table-scroll"><table><thead><tr><th>{t.action}</th><th>{t.user}</th><th>{t.object}</th><th>{t.date}</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><td><span className="event-action">{event.action.replaceAll('.', ' ')}</span></td><td>{event.actor_email}</td><td>{event.object_type}{event.object_id ? ` #${event.object_id}` : ''}</td><td>{new Date(event.created_at).toLocaleString()}</td></tr>)}{events.length === 0 && <tr><td colSpan={4} className="empty-cell">{t.noEvents}</td></tr>}</tbody></table></div>
}

function ErrorBanner({ message }: { message: string }) { return <div role="alert" className="error-banner">{message}</div> }
function Denied({ t }: { t: Copy }) { return <div className="denied-panel"><ShieldCheck size={24} /><h2>{t.accessDenied}</h2></div> }