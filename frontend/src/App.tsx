import { NavLink, Route, Routes, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Activity, ArrowRight, Bot, Check, ClipboardCheck, GitBranch, Globe2, Info, KeyRound, LayoutDashboard, LogOut, Menu, MessageCircle, PanelLeftClose, PanelLeftOpen, Pencil, Plus, Save, Send, Settings2, ShieldCheck, Users, X } from 'lucide-react'
import { api, refreshCsrf, type AuditEvent, type Page, type User } from './api'
import { en } from './i18n/en'
import { fr } from './i18n/fr'
import { RiskRegisterConfiguredPage } from './RiskRegisterConfiguredPage'
import { MitigationsPage } from './MitigationsPage'
import { RiskDetailPage } from './RiskDetailPage'
import { ArchitectureSettingsPage } from './ArchitectureSettingsPage'
import { RiskMonitoringDashboard } from './RiskMonitoringDashboard'

type Language = 'en' | 'fr'
type Copy = typeof en | typeof fr
type DashboardData = { database: string; studies: number; open_risks: number; critical_risks: number }
type StudyRecord = { id: number; identifier: string; title: string; description: string; architecture_domain: string; architecture_domain_id: number | null; jira_jpd_url: string; confluence_url: string; status: string; target_review_date: string | null; created_at: string; row_version: number }
type ArchitectureDomainRecord = { id: number; name: string; is_active: boolean }
type RiskMitigationRecord = { mitigation_id: string; risk_id: number; risk_identifier: string; risk_title: string; title: string; description: string; residual_probability: number | null; residual_impact: number | null; residual_score: number | null; treatment_strategy: string; control_effectiveness: string; status: 'Draft' | 'Submitted' | 'Approved' | 'Rejected'; submitted_at: string | null; validated_at: string | null; validated_by_id: number | null; validation_comment: string; updated_at: string | null; attachments: { id: string; file_name: string; content_type: string; file_size: number; created_at: string }[]; reviews: { id: string; reviewer_id: number; reviewer_name: string; decision: 'Approved' | 'Rejected'; comment: string; created_at: string }[] }
type RiskRecord = { id: number; identifier: string; title: string; description: string; probability: number; impact: number; inherent_score: number; residual_score: number | null; criticality: string; status: string; study_id: number | null; created_at: string; row_version: number; family_id: string | null; family_label: string | null; family_label_en: string | null; subfamily_id: string | null; subfamily_label: string | null; subfamily_label_en: string | null; risk_definition_id: string | null; treatment_strategy: string; residual_probability: number | null; residual_impact: number | null; existing_controls: string; control_effectiveness: string; objects: { object_type: string; object_ref: string }[]; sources: { source_type: string; source_ref: string }[]; scopes: { scope_type: string; scope_ref: string }[]; mitigations: RiskMitigationRecord[] }
type RiskTaxonomyType = { id: string; family_id: string; label_en: string; label_fr: string }
type RiskTaxonomyFamily = { id: string; name_en: string; name_fr: string; types: RiskTaxonomyType[] }
type RiskHelpDefinition = { id: string; risk_code: string; risk_number: number; subfamily_id: string; title_en: string; title_fr: string; description_en: string; description_fr: string; causes: string[]; causes_fr: string[]; impacts: string[]; impacts_fr: string[]; data_quality_notes: string[] }
type RiskFormState = { title: string; description: string; probability: string; impact: string; residual_probability: string; residual_impact: string; family_id: string; subfamily_id: string; study_id: string; object_type: string; object_ref: string; source_type: string; source_ref: string; scope_type: string; scope_ref: string; mitigations: string; existing_controls: string; treatment_strategy: string; control_effectiveness: string }
type RiskHelpForm = { title_en: string; title_fr: string; description_en: string; description_fr: string; causes: string; causes_fr: string; impacts: string; impacts_fr: string; data_quality_notes: string }
type RiskMitigationDraft = { description: string; status: string }
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
  const currentPage = location.pathname.startsWith('/users') ? t.people : location.pathname.startsWith('/audit') ? t.audit : location.pathname.startsWith('/settings') ? t.architectureSettings : location.pathname.startsWith('/risk-dashboard') ? t.riskMonitoring : location.pathname.startsWith('/studies') ? t.studies : location.pathname.startsWith('/mitigations') ? t.mitigationsTitle : location.pathname.startsWith('/risks') ? t.risks : location.pathname.startsWith('/decisions') ? t.decisions : location.pathname.startsWith('/assistant') ? t.assistant : t.dashboard
  return <div className={`app-shell ${sidebarCollapsed ? 'shell-collapsed' : ''}`}>
    {sidebarOpen && <button aria-label="Close navigation" className="mobile-scrim" onClick={() => setSidebarOpen(false)} />}
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <div className="brand-lockup"><div className="brand-mark">EA</div><div><strong>{t.appName}</strong><span>{t.eyebrow}</span></div><button aria-label="Close navigation" className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)}><X size={19} /></button></div>
      <div className="nav-section-label">{t.workspace}</div>
      <nav className="primary-nav" aria-label={t.workspace}><NavItem to="/" icon={<LayoutDashboard size={18} />} label={t.dashboard} end /><NavItem to="/risk-dashboard" icon={<Activity size={18} />} label={t.riskMonitoring} /><NavItem to="/studies" icon={<Activity size={18} />} label={t.studies} /><NavItem to="/decisions" icon={<GitBranch size={18} />} label={t.decisions} /><NavItem to="/risks" icon={<ShieldCheck size={18} />} label={t.risks} /><NavItem to="/mitigations" icon={<ClipboardCheck size={18} />} label={t.mitigationsTitle} /><NavItem to="/assistant" icon={<MessageCircle size={18} />} label={t.assistant} /></nav>
      {(isAdmin || user.role.permissions.includes('admin.configure')) && <><div className="nav-section-label admin-label">{t.administration}</div><nav className="primary-nav" aria-label={t.administration}>
        {isAdmin && <><NavItem to="/users" icon={<Users size={18} />} label={t.people} /><NavItem to="/audit" icon={<Activity size={18} />} label={t.audit} /></>}
        {user.role.permissions.includes('admin.configure') && <NavItem to="/settings" icon={<Settings2 size={18} />} label={t.architectureSettings} />}
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
        <Route path="/risk-dashboard" element={<RiskMonitoringDashboard t={t} language={language} />} />
        <Route path="/studies" element={<StudiesPage t={t} user={user} />} />
        <Route path="/risks" element={<RiskRegisterConfiguredPage t={t} user={user} language={language} />} />
        <Route path="/risks/:riskId" element={<RiskDetailPage t={t} language={language} user={user} />} />
        <Route path="/mitigations" element={<MitigationsPage t={t} user={user} language={language} />} />
        <Route path="/decisions" element={<DecisionsPage t={t} user={user} />} />
        <Route path="/decisions/:decisionId" element={<DecisionDetailPage t={t} user={user} />} />
        <Route path="/assistant" element={<AssistantPage t={t} user={user} />} />
        <Route path="/users" element={isAdmin ? <UsersPage t={t} onNotice={setNotice} /> : <Denied t={t} />} />
        <Route path="/audit" element={isAdmin ? <AuditPage t={t} /> : <Denied t={t} />} />
        <Route path="/settings" element={user.role.permissions.includes('admin.configure') ? <ArchitectureSettingsPage t={t} language={language} /> : <Denied t={t} />} />
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
  return keys[name] ? String(t[keys[name]]) : name
}

function translatedRoleDescription(name: string, t: Copy): string {
  const keys: Record<string, keyof Copy> = {
    Administrator: 'administratorRoleDescription',
    'Enterprise Architect': 'enterpriseArchitectRoleDescription',
    'Solution Architect': 'solutionArchitectRoleDescription',
    'Technical Architect': 'technicalArchitectRoleDescription',
    'Reviewer / ARB Member': 'reviewerRoleDescription',
    'Read-only User': 'readOnlyRoleDescription',
  }
  return keys[name] ? String(t[keys[name]]) : ''
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
  Closed: ['Closed', 'Archived'], Archived: ['Archived', 'In Progress'],
}
const riskTransitions: Record<string, string[]> = {
  Open: ['Open', 'In Progress', 'Closed', 'Archived'],
  'In Progress': ['In Progress', 'Open', 'Closed', 'Archived'],
  Closed: ['Closed', 'Reopened', 'Archived'],
  Archived: ['Archived', 'Reopened'],
  Reopened: ['Reopened', 'In Progress', 'Closed', 'Archived'],
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
  const [domains, setDomains] = useState<ArchitectureDomainRecord[]>([])
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('search') ?? '')
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', architecture_domain_id: '', business_context: '', business_objectives: '', scope: '', out_of_scope: '', jira_jpd_url: '', confluence_url: '' })
  const canWrite = user.role.permissions.includes('studies.write')
  const canApprove = user.role.permissions.includes('studies.approve')
  async function load() {
    try { const [page, domainList] = await Promise.all([api<Page<StudyRecord>>('/studies?limit=100'), api<ArchitectureDomainRecord[]>('/studies/domains')]); setStudies(page.items); setDomains(domainList); setError('') }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try { await api('/studies', { method: 'POST', body: JSON.stringify({ ...form, architecture_domain_id: form.architecture_domain_id ? Number(form.architecture_domain_id) : null }) }); setShowForm(false); setForm({ title: '', description: '', architecture_domain_id: '', business_context: '', business_objectives: '', scope: '', out_of_scope: '', jira_jpd_url: '', confluence_url: '' }); await load() }
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
      <div className="table-scroll"><table><thead><tr><th>{t.study}</th><th>{t.domain}</th><th>{t.studyStatus}</th><th>{t.date}</th><th>{t.studyConnections}</th></tr></thead><tbody>{visible.map((study) => <tr key={study.id}><td><div className="record-cell"><b>{study.title}</b><small>{study.identifier}</small></div></td><td>{study.architecture_domain || '—'}</td><td className="study-status-cell">{canWrite ? <select className="status-select" aria-label={`${t.studyStatus}: ${study.title}`} value={study.status} onChange={(event) => void changeStatus(study, event.target.value)}>{(studyTransitions[study.status] ?? [study.status]).filter((status) => status !== 'Approved' || canApprove).map((status) => <option key={status}>{status}</option>)}</select> : <span className="status-label">{study.status}</span>}{canApprove && study.status === 'Under Review' && <button type="button" className="button-primary compact-button study-approve-button" onClick={() => void changeStatus(study, 'Approved')}><Check size={14} />{t.approveStudy}</button>}</td><td>{study.target_review_date ? new Date(study.target_review_date).toLocaleDateString() : '—'}</td><td><span className="study-jump-links">{study.jira_jpd_url && <a href={study.jira_jpd_url} target="_blank" rel="noreferrer">Jira JPD</a>}{study.confluence_url && <a href={study.confluence_url} target="_blank" rel="noreferrer">Confluence</a>}{!study.jira_jpd_url && !study.confluence_url && '—'}</span></td></tr>)}{visible.length === 0 && <tr><td colSpan={5} className="empty-cell">{t.noStudies}</td></tr>}</tbody></table></div>
    </section>{showForm && <div className="modal-backdrop"><form className="modal-panel" onSubmit={create}><div className="modal-title"><div><span className="page-eyebrow">{t.workspaceFoundation}</span><h2>{t.createStudy}</h2></div><button type="button" className="icon-button" aria-label={t.cancel} onClick={() => setShowForm(false)}><X size={19} /></button></div><label>{t.title}<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label>{t.description}<input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label><label>{t.domain}<select required value={form.architecture_domain_id} onChange={(event) => setForm({ ...form, architecture_domain_id: event.target.value })}><option value="">{t.selectArchitectureDomain}</option>{domains.map((domain) => <option key={domain.id} value={domain.id}>{domain.name}</option>)}</select></label><label>{t.businessContext}<textarea value={form.business_context} onChange={(event) => setForm({ ...form, business_context: event.target.value })} /></label><fieldset className="study-link-fields"><legend>{t.studyConnections}</legend><label>{t.jiraJpdUrl}<input type="url" maxLength={1000} value={form.jira_jpd_url} onChange={(event) => setForm({ ...form, jira_jpd_url: event.target.value })} /></label><label>{t.confluenceUrl}<input type="url" maxLength={1000} value={form.confluence_url} onChange={(event) => setForm({ ...form, confluence_url: event.target.value })} /></label></fieldset><div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setShowForm(false)}>{t.cancel}</button><button className="button-primary" disabled={busy || domains.length === 0}>{busy ? t.loading : t.createStudy}<ArrowRight size={16} /></button></div></form></div>}
  </>
}

export function LegacyRisksPage({ t, user, language }: { t: Copy; user: User; language: Language }) {
  const [risks, setRisks] = useState<RiskRecord[]>([])
  const [studies, setStudies] = useState<StudyRecord[]>([])
  const [catalog, setCatalog] = useState<RiskTaxonomyFamily[]>([])
  const [definitions, setDefinitions] = useState<RiskHelpDefinition[]>([])
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [managingRisk, setManagingRisk] = useState<RiskRecord | null>(null)
  const [workflowRisk, setWorkflowRisk] = useState<RiskRecord | null>(null)
  const [selectedHelp, setSelectedHelp] = useState<RiskHelpDefinition | null>(null)
  const [selectedHelpCode, setSelectedHelpCode] = useState('')
  const [helpForm, setHelpForm] = useState<RiskHelpForm | null>(null)
  const [tab, setTab] = useState<'register' | 'help'>('register')
  const [busy, setBusy] = useState(false)
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('search') ?? '')
  const canWrite = user.role.permissions.includes('risks.write')
  const canConfigureHelp = user.role.permissions.includes('admin.configure')
  const [form, setForm] = useState<RiskFormState>(emptyRiskForm())
  async function load() {
    try {
      const [riskPage, studyPage, taxonomy, help] = await Promise.all([api<Page<RiskRecord>>('/risks?limit=100'), api<Page<StudyRecord>>('/studies?limit=100'), api<RiskTaxonomyFamily[]>('/risks/catalog'), api<RiskHelpDefinition[]>('/risks/catalog/help')])
      setRisks(riskPage.items); setStudies(studyPage.items); setCatalog(taxonomy); setDefinitions(help); setError('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    if (Boolean(form.family_id) !== Boolean(form.subfamily_id)) { setError(t.taxonomyPairRequired); setBusy(false); return }
    const selectedType = catalog.flatMap((family) => family.types).find((type) => type.id === form.subfamily_id)
    const definition = definitions.find((item) => item.subfamily_id === form.subfamily_id)
    const family = catalog.find((item) => item.id === form.family_id)
    const payload = {
      title: form.title, description: form.description, probability: Number(form.probability), impact: Number(form.impact),
      study_id: form.study_id ? Number(form.study_id) : null, family: family?.name_en ?? '', category: selectedType?.label_en ?? '',
      family_id: form.family_id || null, subfamily_id: form.subfamily_id || null, risk_definition_id: definition?.id ?? null,
      objects: form.object_ref.trim() ? [{ object_type: form.object_type, object_ref: form.object_ref.trim() }] : [],
      sources: form.source_ref.trim() ? [{ source_type: form.source_type, source_ref: form.source_ref.trim() }] : [],
      scopes: form.scope_ref.trim() ? [{ scope_type: form.scope_type, scope_ref: form.scope_ref.trim() }] : [],
    }
    try { await api('/risks', { method: 'POST', body: JSON.stringify(payload) }); setShowForm(false); setForm(emptyRiskForm()); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  async function saveTreatment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
  }
  async function saveWorkflowTreatment(_payload: Record<string, unknown>) {
    setWorkflowRisk(null)
  }
  async function changeStatus(risk: RiskRecord, status: string) {
    try { await api(`/risks/${risk.id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.invalidAction) }
  }
  function openHelp(definition: RiskHelpDefinition | undefined) {
    if (definition) setSelectedHelp(definition)
  }
  function definitionFor(risk: RiskRecord) {
    return definitions.find((item) => item.id === risk.risk_definition_id) ?? definitions.find((item) => item.subfamily_id === risk.subfamily_id)
  }
  function selectHelpDefinition(code: string) {
    setSelectedHelpCode(code)
    const item = definitions.find((definition) => definition.risk_code === code)
    setHelpForm(item ? helpDefinitionToForm(item) : null)
  }
  async function saveHelpDefinition(event: FormEvent) {
    event.preventDefault()
    const definition = definitions.find((item) => item.risk_code === selectedHelpCode)
    if (!definition || !helpForm) return
    setBusy(true)
    try {
      const saved = await api<RiskHelpDefinition>(`/risks/catalog/help/${definition.risk_code}`, { method: 'PATCH', body: JSON.stringify({
        title_en: helpForm.title_en, title_fr: helpForm.title_fr, description_en: helpForm.description_en, description_fr: helpForm.description_fr,
        causes: splitLines(helpForm.causes), causes_fr: splitLines(helpForm.causes_fr), impacts: splitLines(helpForm.impacts),
        impacts_fr: splitLines(helpForm.impacts_fr), data_quality_notes: splitLines(helpForm.data_quality_notes),
      }) })
      setDefinitions((current) => current.map((item) => item.id === saved.id ? saved : item))
      setHelpForm(helpDefinitionToForm(saved))
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  const criticalityLabels: Record<string, string> = { Critical: t.critical, High: t.high, Medium: t.medium, Low: t.low }
  const visibleRisks = risks.map((risk) => ({ ...risk, family_label: language === 'fr' ? risk.family_label : risk.family_label_en, subfamily_label: language === 'fr' ? risk.subfamily_label : risk.subfamily_label_en })).filter((risk) => `${risk.identifier} ${risk.title} ${risk.description} ${risk.family_label ?? ''} ${risk.subfamily_label ?? ''}`.toLowerCase().includes(query.toLowerCase()))
  const selectedFamily = catalog.find((family) => family.id === form.family_id)
  const subfamilyOptions = selectedFamily?.types ?? []
  return <><PageHeading eyebrow={t.governanceTraceability} title={t.risksTitle} subtitle={t.risksSub} action={canWrite && tab === 'register' ? <button className="button-primary compact-button" onClick={() => { setForm(emptyRiskForm()); setShowForm(true) }}><ShieldCheck size={16} />{t.createRisk}</button> : undefined} />
    {error && <ErrorBanner message={error} />}
    {workflowRisk && <RiskMitigationWorkflow risk={workflowRisk} t={t} busy={busy} onClose={() => setWorkflowRisk(null)} onSave={saveWorkflowTreatment} />}
    <div className="risk-tabs" role="tablist" aria-label={t.risksTitle}>
      <button type="button" role="tab" aria-selected={tab === 'register'} className={tab === 'register' ? 'risk-tab active' : 'risk-tab'} onClick={() => setTab('register')}><ShieldCheck size={16} />{t.riskRegisterTab}</button>
      {canConfigureHelp && <button type="button" role="tab" aria-selected={tab === 'help'} className={tab === 'help' ? 'risk-tab active' : 'risk-tab'} onClick={() => setTab('help')}><Settings2 size={16} />{t.helpSettings}</button>}
      {canWrite && <label className="treatment-launcher">{t.manageTreatment}<select value="" onChange={(event) => { const risk = risks.find((item) => item.id === Number(event.target.value)); if (risk) setWorkflowRisk(risk) }}><option value="">{t.selectRiskForTreatment}</option>{risks.map((risk) => <option key={risk.id} value={risk.id}>{risk.identifier} · {risk.title}</option>)}</select></label>}
    </div>
    {tab === 'register' ? <section className="data-section"><div className="table-toolbar"><div className="table-count">{visibleRisks.length} <span>{t.risks.toLowerCase()}</span></div><label className="table-search"><span className="sr-only">{t.search}</span><input placeholder={t.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label></div><div className="table-scroll"><table><thead><tr><th>{t.risksTitle}</th><th>{t.riskTaxonomy}</th><th>{t.inherentScore}</th><th>{t.residualScore}</th><th>{t.criticality}</th><th>{t.riskStatus}</th><th>{t.actions}</th></tr></thead><tbody>{visibleRisks.map((risk) => <tr key={risk.id}><td><div className="record-cell"><span className="risk-record-title"><b>{risk.title}</b>{definitionFor(risk) && <button type="button" className="help-icon-button" aria-label={`${t.openRiskHelp}: ${risk.title}`} title={t.openRiskHelp} onClick={(event) => { event.preventDefault(); event.stopPropagation(); openHelp(definitionFor(risk)) }}><Info size={15} /></button>}</span><small>{risk.identifier}</small></div></td><td><span className="taxonomy-cell"><b>{risk.family_label || t.toQualify}</b><small>{risk.subfamily_id ? `${risk.subfamily_id} · ${risk.subfamily_label}` : t.toQualify}</small></span></td><td><span className="score-cell">{risk.inherent_score}<small>{risk.probability} × {risk.impact}</small></span></td><td>{risk.residual_score ?? '—'}</td><td><span className={`criticality-tag criticality-${risk.criticality.toLowerCase()}`}>{criticalityLabels[risk.criticality] ?? risk.criticality}</span></td><td>{canWrite ? <select className="status-select" aria-label={`${t.riskStatus}: ${risk.title}`} value={risk.status} onChange={(event) => void changeStatus(risk, event.target.value)}>{(riskTransitions[risk.status] ?? [risk.status]).map((status) => <option key={status}>{status}</option>)}</select> : <span className="status-label">{risk.status}</span>}</td><td>{canWrite && <button type="button" className="button-secondary compact-button" onClick={() => setManagingRisk(risk)}>{t.manageTreatment}</button>}</td></tr>)}{visibleRisks.length === 0 && <tr><td colSpan={7} className="empty-cell">{t.noRisks}</td></tr>}</tbody></table></div></section> : <section className="data-section help-settings"><div className="help-settings-heading"><div><h2>{t.helpSettings}</h2><p>{t.helpSettingsSub}</p></div><label>{t.riskDefinition}<select value={selectedHelpCode} onChange={(event) => selectHelpDefinition(event.target.value)}><option value="">{t.selectRiskDefinition}</option>{definitions.map((item) => <option key={item.id} value={item.risk_code}>{item.risk_code} · {item.title_en}</option>)}</select></label></div>{helpForm && <form className="help-settings-form" onSubmit={saveHelpDefinition}><div className="field-pair"><label>{t.titleEnglish}<input required value={helpForm.title_en} onChange={(event) => setHelpForm({ ...helpForm, title_en: event.target.value })} /></label><label>{t.titleFrench}<input required value={helpForm.title_fr} onChange={(event) => setHelpForm({ ...helpForm, title_fr: event.target.value })} /></label></div><div className="field-pair"><label>{t.descriptionEnglish}<textarea required value={helpForm.description_en} onChange={(event) => setHelpForm({ ...helpForm, description_en: event.target.value })} /></label><label>{t.descriptionFrench}<textarea value={helpForm.description_fr} onChange={(event) => setHelpForm({ ...helpForm, description_fr: event.target.value })} /></label></div><div className="field-pair"><label>{t.causesEnglish}<textarea value={helpForm.causes} onChange={(event) => setHelpForm({ ...helpForm, causes: event.target.value })} /></label><label>{t.causesFrench}<textarea value={helpForm.causes_fr} onChange={(event) => setHelpForm({ ...helpForm, causes_fr: event.target.value })} /></label></div><div className="field-pair"><label>{t.impactsEnglish}<textarea value={helpForm.impacts} onChange={(event) => setHelpForm({ ...helpForm, impacts: event.target.value })} /></label><label>{t.impactsFrench}<textarea value={helpForm.impacts_fr} onChange={(event) => setHelpForm({ ...helpForm, impacts_fr: event.target.value })} /></label></div><label>{t.dataQualityNotes}<textarea value={helpForm.data_quality_notes} onChange={(event) => setHelpForm({ ...helpForm, data_quality_notes: event.target.value })} /></label><div className="modal-actions"><button className="button-primary" disabled={busy}>{busy ? t.loading : t.saveHelpSettings}<Save size={16} /></button></div></form>}</section>}
    {showForm && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowForm(false) }}><form className="modal-panel risk-form-panel" onSubmit={create}><div className="modal-title"><div><span className="page-eyebrow">{t.governanceTraceability}</span><h2>{t.createRisk}</h2></div><button type="button" className="icon-button" aria-label={t.close} onClick={() => setShowForm(false)}><X size={19} /></button></div><label>{t.title}<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label>{t.description}<textarea required value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label><div className="field-pair"><label>{t.family}<select value={form.family_id} onChange={(event) => setForm({ ...form, family_id: event.target.value, subfamily_id: '' })}><option value="">{t.toQualify}</option>{catalog.map((family) => <option key={family.id} value={family.id}>{family.id} · {language === 'fr' ? family.name_fr : family.name_en}</option>)}</select></label><label>{t.subfamily}<span className="select-with-help"><select value={form.subfamily_id} disabled={!form.family_id} onChange={(event) => setForm({ ...form, subfamily_id: event.target.value })}><option value="">{form.family_id ? t.selectSubfamily : t.selectFamilyFirst}</option>{subfamilyOptions.map((item) => <option key={item.id} value={item.id}>{item.id} · {language === 'fr' ? item.label_fr : item.label_en}</option>)}</select>{form.subfamily_id && <button type="button" className="help-icon-button" aria-label={t.openRiskHelp} title={t.openRiskHelp} onClick={() => openHelp(definitions.find((item) => item.subfamily_id === form.subfamily_id))}><Info size={16} /></button>}</span></label></div><div className="field-pair"><label>{t.probability}<select value={form.probability} onChange={(event) => setForm({ ...form, probability: event.target.value })}>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.impact}<select value={form.impact} onChange={(event) => setForm({ ...form, impact: event.target.value })}>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label></div><div className="field-pair"><label>{t.residualProbability}<select value={form.residual_probability} onChange={(event) => setForm({ ...form, residual_probability: event.target.value, residual_impact: event.target.value ? form.residual_impact : '' })}><option value="">—</option>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.residualImpact}<select value={form.residual_impact} onChange={(event) => setForm({ ...form, residual_impact: event.target.value, residual_probability: event.target.value ? form.residual_probability : '' })}><option value="">—</option>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label></div><label>{t.study}<select value={form.study_id} onChange={(event) => setForm({ ...form, study_id: event.target.value })}><option value="">—</option>{studies.map((study) => <option key={study.id} value={study.id}>{study.identifier} · {study.title}</option>)}</select></label><div className="field-pair"><label>{t.objectType}<select value={form.object_type} onChange={(event) => setForm({ ...form, object_type: event.target.value })}>{['Application', 'Technology / Component', 'Platform / Infra', 'Data / Integration', 'Service IT / Business', 'Provider / Third Party', 'Archi Domain / Capa', 'Enterprise / IT landscape'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.objectReference}<input value={form.object_ref} onChange={(event) => setForm({ ...form, object_ref: event.target.value })} /></label></div><div className="field-pair"><label>{t.sourceType}<select value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value })}>{['ADR / Exception', 'ARB', 'Project', 'App / Techno lifecycle review', 'Audit / Compliance review', 'Incident / Problem mgt'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.sourceReference}<input value={form.source_ref} onChange={(event) => setForm({ ...form, source_ref: event.target.value })} /></label></div><div className="field-pair"><label>{t.scopeType}<select value={form.scope_type} onChange={(event) => setForm({ ...form, scope_type: event.target.value })}>{['Team', 'Domain', 'Capability', 'Company / Entity'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.scopeReference}<input value={form.scope_ref} onChange={(event) => setForm({ ...form, scope_ref: event.target.value })} /></label></div><label>{t.mitigations}<textarea value={form.mitigations} onChange={(event) => setForm({ ...form, mitigations: event.target.value })} /></label><div className="field-pair"><label>{t.treatmentStrategy}<select value={form.treatment_strategy} onChange={(event) => setForm({ ...form, treatment_strategy: event.target.value })}>{['Avoid', 'Reduce', 'Transfer', 'Accept'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.controlEffectiveness}<select value={form.control_effectiveness} onChange={(event) => setForm({ ...form, control_effectiveness: event.target.value })}>{['Unknown', 'Low', 'Moderate', 'High'].map((value) => <option key={value}>{value}</option>)}</select></label></div><label>{t.existingControls}<textarea value={form.existing_controls} onChange={(event) => setForm({ ...form, existing_controls: event.target.value })} /></label><div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setShowForm(false)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.createRisk}<ArrowRight size={16} /></button></div></form></div>}
    {managingRisk && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setManagingRisk(null) }}><form className="modal-panel risk-form-panel" onSubmit={saveTreatment}><div className="modal-title"><div><span className="page-eyebrow">{managingRisk.identifier}</span><h2>{t.manageTreatment}</h2></div><button type="button" className="icon-button" aria-label={t.close} onClick={() => setManagingRisk(null)}><X size={19} /></button></div><p className="treatment-risk-title">{managingRisk.title}</p><div className="field-pair"><label>{t.residualProbability}<select name="residual_probability" defaultValue={managingRisk.residual_probability ?? ''}><option value="">—</option>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.residualImpact}<select name="residual_impact" defaultValue={managingRisk.residual_impact ?? ''}><option value="">—</option>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label></div><label>{t.treatmentStrategy}<select name="treatment_strategy" defaultValue={managingRisk.treatment_strategy}>{['Avoid', 'Reduce', 'Transfer', 'Accept'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.controlEffectiveness}<select name="control_effectiveness" defaultValue={managingRisk.control_effectiveness}>{['Unknown', 'Low', 'Moderate', 'High'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.mitigations}<textarea name="mitigations" defaultValue={managingRisk.mitigations.map((item) => item.description).join('\n')} /></label><label>{t.existingControls}<textarea name="existing_controls" defaultValue={managingRisk.existing_controls} /></label><div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setManagingRisk(null)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.save}<Save size={16} /></button></div></form></div>}
    {selectedHelp && <RiskHelpDialog definition={selectedHelp} catalog={catalog} language={language} t={t} onClose={() => setSelectedHelp(null)} />}
  </>
}

function emptyRiskForm(): RiskFormState {
  return { title: '', description: '', probability: '2', impact: '2', residual_probability: '', residual_impact: '', family_id: '', subfamily_id: '', study_id: '', object_type: 'Application', object_ref: '', source_type: 'Project', source_ref: '', scope_type: 'Domain', scope_ref: '', mitigations: '', existing_controls: '', treatment_strategy: 'Reduce', control_effectiveness: 'Unknown' }
}

function splitLines(value: string) { return value.split('\n').map((item) => item.trim()).filter(Boolean) }

function RiskMitigationWorkflow({ risk, t, busy, onClose, onSave }: { risk: RiskRecord; t: Copy; busy: boolean; onClose: () => void; onSave: (payload: Record<string, unknown>) => Promise<void> }) {
  const [drafts, setDrafts] = useState<RiskMitigationDraft[]>(risk.mitigations.map((item) => ({ description: item.description, status: item.status })))
  const [residualProbability, setResidualProbability] = useState(risk.residual_probability?.toString() ?? '')
  const [residualImpact, setResidualImpact] = useState(risk.residual_impact?.toString() ?? '')
  const [treatmentStrategy, setTreatmentStrategy] = useState(risk.treatment_strategy)
  const [controlEffectiveness, setControlEffectiveness] = useState(risk.control_effectiveness)
  const [existingControls, setExistingControls] = useState(risk.existing_controls)
  const [validationError, setValidationError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (Boolean(residualProbability) !== Boolean(residualImpact)) { setValidationError(t.residualPairRequired); return }
    setValidationError('')
    await onSave({
      residual_probability: residualProbability ? Number(residualProbability) : null,
      residual_impact: residualImpact ? Number(residualImpact) : null,
      treatment_strategy: treatmentStrategy, control_effectiveness: controlEffectiveness,
      existing_controls: existingControls,
      mitigations: drafts.filter((item) => item.description.trim()).map((item) => ({ description: item.description.trim(), status: item.status })),
    })
  }
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><form className="modal-panel risk-form-panel" onSubmit={submit}><div className="modal-title"><div><span className="page-eyebrow">{risk.identifier}</span><h2>{t.manageTreatment}</h2></div><button type="button" className="icon-button" aria-label={t.close} onClick={onClose}><X size={19} /></button></div><p className="treatment-risk-title">{risk.title}</p><div className="field-pair"><label>{t.residualProbability}<select value={residualProbability} onChange={(event) => setResidualProbability(event.target.value)}><option value="">—</option>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.residualImpact}<select value={residualImpact} onChange={(event) => setResidualImpact(event.target.value)}><option value="">—</option>{[1, 2, 3, 4].map((value) => <option key={value}>{value}</option>)}</select></label></div><div className="field-pair"><label>{t.treatmentStrategy}<select value={treatmentStrategy} onChange={(event) => setTreatmentStrategy(event.target.value)}>{['Avoid', 'Reduce', 'Transfer', 'Accept'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.controlEffectiveness}<select value={controlEffectiveness} onChange={(event) => setControlEffectiveness(event.target.value)}>{['Unknown', 'Low', 'Moderate', 'High'].map((value) => <option key={value}>{value}</option>)}</select></label></div><section className="mitigation-editor"><div className="mitigation-editor-heading"><h3>{t.mitigationMeasures}</h3><button type="button" className="button-secondary compact-button" onClick={() => setDrafts((current) => [...current, { description: '', status: 'Planned' }])}><Plus size={14} />{t.addMitigation}</button></div>{drafts.map((mitigation, index) => <div className="mitigation-editor-row" key={`${index}-${mitigation.description}`}><label>{t.mitigationDescription}<input value={mitigation.description} onChange={(event) => setDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, description: event.target.value } : item))} /></label><label>{t.mitigationStatus}<select value={mitigation.status} onChange={(event) => setDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, status: event.target.value } : item))}><option value="Planned">{t.mitigationPlanned}</option><option value="In Progress">{t.mitigationInProgress}</option><option value="Implemented">{t.mitigationImplemented}</option><option value="Verified">{t.mitigationVerified}</option></select></label><button type="button" className="help-icon-button" aria-label={t.removeMitigation} title={t.removeMitigation} onClick={() => setDrafts((current) => current.filter((_, itemIndex) => itemIndex !== index))}><X size={15} /></button></div>)}</section><label>{t.existingControls}<textarea value={existingControls} onChange={(event) => setExistingControls(event.target.value)} /></label>{validationError && <p className="chat-error" role="alert">{validationError}</p>}<div className="modal-actions"><button type="button" className="button-secondary" onClick={onClose}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.save}<Save size={16} /></button></div></form></div>
}

function helpDefinitionToForm(definition: RiskHelpDefinition): RiskHelpForm {
  return { title_en: definition.title_en, title_fr: definition.title_fr, description_en: definition.description_en, description_fr: definition.description_fr, causes: definition.causes.join('\n'), causes_fr: definition.causes_fr.join('\n'), impacts: definition.impacts.join('\n'), impacts_fr: definition.impacts_fr.join('\n'), data_quality_notes: definition.data_quality_notes.join('\n') }
}

function RiskHelpDialog({ definition, catalog, language, t, onClose }: { definition: RiskHelpDefinition; catalog: RiskTaxonomyFamily[]; language: Language; t: Copy; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const type = catalog.flatMap((family) => family.types).find((item) => item.id === definition.subfamily_id)
  const family = catalog.find((item) => item.id === type?.family_id)
  const description = language === 'fr' && definition.description_fr ? definition.description_fr : definition.description_en
  const causes = language === 'fr' && definition.causes_fr.length ? definition.causes_fr : definition.causes
  const impacts = language === 'fr' && definition.impacts_fr.length ? definition.impacts_fr : definition.impacts
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null
    closeRef.current?.focus()
    const scrollRegion = closeRef.current?.closest('[role="dialog"]')?.querySelector('.risk-help-scroll')
    scrollRegion?.setAttribute('tabindex', '0')
    scrollRegion?.setAttribute('aria-label', t.riskHelpContent)
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); return }
      if (event.key !== 'Tab') return
      const dialog = closeRef.current?.closest('[role="dialog"]')
      const focusable = dialog?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])')
      if (!focusable?.length) { event.preventDefault(); return }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => { document.removeEventListener('keydown', handleKeyDown); previousFocus?.focus() }
  }, [definition.id, t.riskHelpContent])
  return <div className="modal-backdrop help-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="modal-panel risk-help-dialog" role="dialog" aria-modal="true" aria-labelledby="risk-help-title" tabIndex={-1}><div className="modal-title"><div><span className="page-eyebrow">{definition.risk_code} · {t.riskNumber} {definition.risk_number}</span><h2 id="risk-help-title">{language === 'fr' ? definition.title_fr : definition.title_en}</h2></div><button ref={closeRef} type="button" className="icon-button" aria-label={t.close} onClick={onClose}><X size={19} /></button></div><div className="risk-help-scroll"><dl className="risk-help-meta"><div><dt>{t.family}</dt><dd>{language === 'fr' ? family?.name_fr : family?.name_en}</dd></div><div><dt>{t.subfamily}</dt><dd>{type?.id} · {language === 'fr' ? type?.label_fr : type?.label_en}</dd></div></dl><section><h3>{t.description}</h3><p>{description}</p></section><div className="field-pair help-lists"><section><h3>{t.causes}</h3><ul>{causes.map((cause, index) => <li key={`${index}-${cause}`}>{cause}</li>)}</ul></section><section><h3>{t.impacts}</h3><ul>{impacts.map((impact, index) => <li key={`${index}-${impact}`}>{impact}</li>)}</ul></section></div>{definition.data_quality_notes.length > 0 && <section className="data-quality-note"><h3>{t.dataQualityNotes}</h3><ul>{definition.data_quality_notes.map((note, index) => <li key={`${index}-${note}`}>{note}</li>)}</ul></section>}</div></section></div>
}

function UsersPage({ t, onNotice }: { t: Copy; onNotice: (value: string) => void }) {
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<User['role'][]>([])
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [editForm, setEditForm] = useState({ display_name: '', role_id: '', is_active: true, temporary_password: '' })
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
  function startEdit(item: User) {
    setEditingUser(item)
    setEditForm({ display_name: item.display_name, role_id: String(item.role.id), is_active: item.is_active, temporary_password: '' })
    setError('')
  }
  async function saveUser(event: FormEvent) {
    event.preventDefault()
    if (!editingUser) return
    setBusy(true); setError('')
    try {
      await api(`/users/${editingUser.id}`, { method: 'PATCH', body: JSON.stringify({ display_name: editForm.display_name, role_id: Number(editForm.role_id), is_active: editForm.is_active }) })
      if (editForm.temporary_password) await api(`/users/${editingUser.id}/password`, { method: 'POST', body: JSON.stringify({ temporary_password: editForm.temporary_password }) })
      setEditingUser(null)
      onNotice(editForm.temporary_password ? t.userUpdatedAndPasswordReset : t.userUpdated)
      await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  const filtered = users.filter((item) => `${item.display_name} ${item.email} ${item.role.name}`.toLowerCase().includes(query.toLowerCase()))
  return <>
    <PageHeading eyebrow={t.accessControl} title={t.usersTitle} subtitle={t.usersSub} action={<button className="button-primary compact-button" onClick={() => setShowForm(true)}><Users size={16} />{t.createUser}</button>} />
    {error && <ErrorBanner message={error} />}
    <section className="data-section"><div className="table-toolbar"><div className="table-count">{users.length} <span>{t.accounts}</span></div><label className="table-search"><span className="sr-only">{t.search}</span><input placeholder={t.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label></div>
      <div className="table-scroll"><table><thead><tr><th>{t.user}</th><th>{t.role}</th><th>{t.status}</th><th>{t.date}</th><th>{t.actions}</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.id}><td><div className="person-cell"><span className="avatar avatar-small">{item.display_name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</span><span><b>{item.display_name}</b><small>{item.email}</small></span></div></td><td><span className="role-cell"><b className="role-label">{translatedRole(item.role.name, t)}</b><small>{translatedRoleDescription(item.role.name, t)}</small></span></td><td><span className="status-label"><span className={`status-dot ${item.is_active ? '' : 'status-dot-inactive'}`} />{item.is_active ? t.active : t.inactive}</span></td><td>{new Date(item.created_at).toLocaleDateString()}</td><td><button className="button-secondary compact-button" onClick={() => startEdit(item)}><Pencil size={14} />{t.editUser}</button></td></tr>)}{filtered.length === 0 && <tr><td colSpan={5} className="empty-cell">{t.emptyUsers}</td></tr>}</tbody></table></div>
    </section>
    {showForm && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowForm(false) }}><form className="modal-panel" onSubmit={create}><div className="modal-title"><div><span className="page-eyebrow">ACCESS CONTROL</span><h2>{t.createUser}</h2></div><button type="button" className="icon-button" aria-label={t.cancel} onClick={() => setShowForm(false)}><X size={19} /></button></div>
      <label>{t.displayName}<input required value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} /></label><label>{t.email}<input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
      <label>{t.role}<select required value={form.role_id} onChange={(event) => setForm({ ...form, role_id: event.target.value })}><option value="">{t.selectRole}</option>{roles.map((role) => <option key={role.id} value={role.id}>{translatedRole(role.name, t)}</option>)}</select></label>
      <label>{t.temporaryPassword}<input type="password" minLength={12} required value={form.temporary_password} onChange={(event) => setForm({ ...form, temporary_password: event.target.value })} /></label>{error && <div role="alert" className="form-error">{error}</div>}
      <div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setShowForm(false)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.createUser}<ArrowRight size={16} /></button></div>
    </form></div>}
    {editingUser && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setEditingUser(null) }}><form className="modal-panel" onSubmit={saveUser}><div className="modal-title"><div><span className="page-eyebrow">{editingUser.email}</span><h2>{t.editUser}</h2></div><button type="button" className="icon-button" aria-label={t.cancel} onClick={() => setEditingUser(null)}><X size={19} /></button></div><label>{t.displayName}<input required value={editForm.display_name} onChange={(event) => setEditForm({ ...editForm, display_name: event.target.value })} /></label><label>{t.role}<select required value={editForm.role_id} onChange={(event) => setEditForm({ ...editForm, role_id: event.target.value })}>{roles.map((role) => <option key={role.id} value={role.id}>{translatedRole(role.name, t)}</option>)}</select></label><label className="user-active-toggle"><input type="checkbox" checked={editForm.is_active} onChange={(event) => setEditForm({ ...editForm, is_active: event.target.checked })} />{t.active}</label><label>{t.resetPasswordOptional}<span className="password-reset-field"><KeyRound size={15} /><input type="password" minLength={12} autoComplete="new-password" value={editForm.temporary_password} onChange={(event) => setEditForm({ ...editForm, temporary_password: event.target.value })} /></span></label>{error && <div role="alert" className="form-error">{error}</div>}<div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setEditingUser(null)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.save}<Save size={16} /></button></div></form></div>}
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