import { useEffect, useRef, useState, type FormEvent } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { ArrowRight, Info, Search, ShieldCheck, X } from 'lucide-react'
import { api, type Page, type User } from './api'
import { en } from './i18n/en'
import { fr } from './i18n/fr'
import { RiskScoringFields } from './RiskScoringFields'
import { HelpDialog, type HelpDefinition, type TaxonomyFamily } from './RiskRegisterPage'

type Language = 'en' | 'fr'
type Copy = typeof en | typeof fr
type Study = { id: number; identifier: string; title: string; jira_jpd_url: string; confluence_url: string }
type ReferenceValue = { id: string; category: 'object_type' | 'source_type' | 'scope_type'; code: string; label_en: string; label_fr: string; is_active: boolean }
type ArdoqComponent = { code: string; name: string; component_type: string; type_id: string }
type Mitigation = { mitigation_id: string; title: string; status: string; validated_at: string | null; residual_score: number | null }
type Risk = { id: number; identifier: string; title: string; description: string; probability: number; impact: number; inherent_score: number; residual_score: number | null; criticality: string; status: string; study_id: number | null; family_id: string | null; family_label: string | null; family_label_en: string | null; subfamily_id: string | null; subfamily_label: string | null; subfamily_label_en: string | null; risk_definition_id: string | null; mitigations: Mitigation[] }
type HelpDraft = { title_en: string; title_fr: string; description_en: string; description_fr: string; causes: string; causes_fr: string; impacts: string; impacts_fr: string; data_quality_notes: string }
type Draft = { title: string; description: string; probability: string; impact: string; study_id: string; family_id: string; subfamily_id: string; object_code: string; object_ref: string; source_code: string; source_ref: string; scope_code: string; scope_ref: string }
const transitions: Record<string, string[]> = { Open: ['Open', 'In Progress', 'Closed', 'Archived'], 'In Progress': ['In Progress', 'Open', 'Closed', 'Archived'], Closed: ['Closed', 'Reopened', 'Archived'], Archived: ['Archived', 'Reopened'], Reopened: ['Reopened', 'In Progress', 'Closed', 'Archived'] }
const blankDraft = (): Draft => ({ title: '', description: '', probability: '2', impact: '2', study_id: '', family_id: '', subfamily_id: '', object_code: '', object_ref: '', source_code: '', source_ref: '', scope_code: '', scope_ref: '' })
const splitLines = (value: string) => value.split('\n').map((line) => line.trim()).filter(Boolean)

function validationState(mitigations: Mitigation[], staleDays: number, t: Copy) {
  if (!mitigations.length || mitigations.some((item) => item.status !== 'Approved' || !item.validated_at)) return { label: t.mitigationNotValidated, tone: 'not-validated' }
  return mitigations.some((item) => (Date.now() - new Date(item.validated_at as string).getTime()) / 86400000 >= staleDays) ? { label: t.mitigationValidationStale, tone: 'stale' } : { label: t.mitigationValidated, tone: 'valid' }
}

export function RiskRegisterConfiguredPage({ t, user, language }: { t: Copy; user: User; language: Language }) {
  const navigate = useNavigate()
  const [risks, setRisks] = useState<Risk[]>([])
  const [studies, setStudies] = useState<Study[]>([])
  const [families, setFamilies] = useState<TaxonomyFamily[]>([])
  const [definitions, setDefinitions] = useState<HelpDefinition[]>([])
  const [references, setReferences] = useState<ReferenceValue[]>([])
  const [ardoqLabel, setArdoqLabel] = useState('')
  const [ardoqResults, setArdoqResults] = useState<ArdoqComponent[]>([])
  const [ardoqBusy, setArdoqBusy] = useState(false)
  const [ardoqError, setArdoqError] = useState('')
  const ardoqRequest = useRef(0)
  const [staleDays, setStaleDays] = useState(365)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<'register' | 'help'>('register')
  const [helpDefinition, setHelpDefinition] = useState<HelpDefinition | null>(null)
  const [helpCode, setHelpCode] = useState('')
  const [helpDraft, setHelpDraft] = useState<HelpDraft | null>(null)
  const [draft, setDraft] = useState<Draft>(blankDraft())
  const canWrite = user.role.permissions.includes('risks.write')
  const canConfigure = user.role.permissions.includes('admin.configure')
  async function load() {
    try {
      const [riskPage, studyPage, taxonomy, help, settings, referenceData] = await Promise.all([
        api<Page<Risk>>('/risks?limit=100'), api<Page<Study>>('/studies?limit=100'), api<TaxonomyFamily[]>('/risks/catalog'),
        api<HelpDefinition[]>('/risks/catalog/help'), api<{ mitigation_validation_stale_days: number }>('/risks/settings/mitigations'),
        api<{ values: ReferenceValue[] }>('/risks/settings/references'),
      ])
      const activeReferences = referenceData.values.filter((item) => item.is_active)
      setRisks(riskPage.items); setStudies(studyPage.items); setFamilies(taxonomy); setDefinitions(help); setReferences(activeReferences); setStaleDays(settings.mitigation_validation_stale_days); setError('')
      setDraft((current) => ({ ...current,
        object_code: current.object_code || activeReferences.find((item) => item.category === 'object_type')?.code || '',
        source_code: current.source_code || activeReferences.find((item) => item.category === 'source_type')?.code || '',
        scope_code: current.scope_code || activeReferences.find((item) => item.category === 'scope_type')?.code || '',
      }))
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [])
  useEffect(() => {
    if (!showForm) return
    setDraft((current) => ({ ...current,
      object_code: current.object_code || references.find((item) => item.category === 'object_type')?.code || '',
      source_code: current.source_code || references.find((item) => item.category === 'source_type')?.code || '',
      scope_code: current.scope_code || references.find((item) => item.category === 'scope_type')?.code || '',
    }))
  }, [showForm, references])
  useEffect(() => {
    ardoqRequest.current += 1
    setArdoqLabel(''); setArdoqResults([]); setArdoqError(''); setArdoqBusy(false)
    return () => { ardoqRequest.current += 1 }
  }, [draft.object_code, showForm])
  async function create(event: FormEvent) {
    event.preventDefault()
    if (Boolean(draft.family_id) !== Boolean(draft.subfamily_id)) { setError(t.taxonomyPairRequired); return }
    setBusy(true); setError('')
    const family = families.find((item) => item.id === draft.family_id)
    const subfamily = family?.types.find((item) => item.id === draft.subfamily_id)
    const definition = definitions.find((item) => item.subfamily_id === draft.subfamily_id)
    const selectedObject = references.find((item) => item.category === 'object_type' && item.code === draft.object_code)
    const selectedSource = references.find((item) => item.category === 'source_type' && item.code === draft.source_code)
    const selectedScope = references.find((item) => item.category === 'scope_type' && item.code === draft.scope_code)
    try {
      await api('/risks', { method: 'POST', body: JSON.stringify({
        title: draft.title, description: draft.description, probability: Number(draft.probability), impact: Number(draft.impact),
        study_id: draft.study_id ? Number(draft.study_id) : null, family: family?.name_en ?? '', category: subfamily?.label_en ?? '',
        family_id: draft.family_id || null, subfamily_id: draft.subfamily_id || null, risk_definition_id: definition?.id ?? null,
        objects: draft.object_ref.trim() && selectedObject ? [{ object_type: selectedObject.label_en, object_ref: draft.object_ref.trim() }] : [],
        sources: draft.source_ref.trim() && selectedSource ? [{ source_type: selectedSource.label_en, source_ref: draft.source_ref.trim() }] : [],
        scopes: draft.scope_ref.trim() && selectedScope ? [{ scope_type: selectedScope.label_en, scope_ref: draft.scope_ref.trim() }] : [],
      }) })
      setShowForm(false); setDraft(blankDraft()); await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  async function changeStatus(risk: Risk, status: string) {
    try { await api(`/risks/${risk.id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.invalidAction) }
  }
  async function searchArdoq() {
    if (ardoqLabel.trim().length < 2 || !draft.object_code) return
    const requestId = ++ardoqRequest.current
    setArdoqBusy(true); setArdoqError(''); setArdoqResults([])
    try {
      const results = await api<ArdoqComponent[]>(`/risks/ardoq/components?object_type_code=${encodeURIComponent(draft.object_code)}&label=${encodeURIComponent(ardoqLabel.trim())}`)
      if (requestId !== ardoqRequest.current) return
      setArdoqResults(results)
      if (!results.length) setArdoqError(t.ardoqNoResults)
    } catch (reason) { if (requestId === ardoqRequest.current) setArdoqError(reason instanceof Error ? reason.message : t.error) }
    finally { if (requestId === ardoqRequest.current) setArdoqBusy(false) }
  }
  function chooseHelp(code: string) {
    setHelpCode(code)
    const item = definitions.find((definition) => definition.risk_code === code)
    setHelpDraft(item ? { title_en: item.title_en, title_fr: item.title_fr, description_en: item.description_en, description_fr: item.description_fr, causes: item.causes.join('\n'), causes_fr: item.causes_fr.join('\n'), impacts: item.impacts.join('\n'), impacts_fr: item.impacts_fr.join('\n'), data_quality_notes: item.data_quality_notes.join('\n') } : null)
  }
  async function saveHelp(event: FormEvent) {
    event.preventDefault()
    const selected = definitions.find((definition) => definition.risk_code === helpCode)
    if (!selected || !helpDraft) return
    setBusy(true); setError('')
    try {
      const saved = await api<HelpDefinition>(`/risks/catalog/help/${helpCode}`, { method: 'PATCH', body: JSON.stringify({ ...helpDraft, causes: splitLines(helpDraft.causes), causes_fr: splitLines(helpDraft.causes_fr), impacts: splitLines(helpDraft.impacts), impacts_fr: splitLines(helpDraft.impacts_fr), data_quality_notes: splitLines(helpDraft.data_quality_notes) }) })
      setDefinitions((current) => current.map((item) => item.id === saved.id ? saved : item))
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  const filtered = risks.map((risk) => ({ ...risk, family_label: language === 'fr' ? risk.family_label : risk.family_label_en, subfamily_label: language === 'fr' ? risk.subfamily_label : risk.subfamily_label_en })).filter((risk) => `${risk.identifier} ${risk.title} ${risk.description} ${risk.family_label ?? ''} ${risk.subfamily_label ?? ''}`.toLowerCase().includes(query.toLowerCase()))
  const chosenFamily = families.find((family) => family.id === draft.family_id)
  const refOptions = (category: ReferenceValue['category']) => references.filter((item) => item.category === category)
  const selectRef = (category: ReferenceValue['category'], code: string) => { const item = references.find((value) => value.category === category && value.code === code); return language === 'fr' ? item?.label_fr : item?.label_en }
  return <>
    <header className="page-heading"><div><span className="page-eyebrow">{t.governanceTraceability}</span><h1>{t.risksTitle}</h1><p>{t.risksSub}</p></div>{canWrite && tab === 'register' && <button className="button-primary compact-button" onClick={() => { setDraft(blankDraft()); setShowForm(true) }}><ShieldCheck size={16} />{t.createRisk}</button>}</header>
    {error && <div className="chat-error" role="alert">{error}</div>}
    <div className="risk-tabs" role="tablist" aria-label={t.risksTitle}><button type="button" role="tab" aria-selected={tab === 'register'} className={tab === 'register' ? 'risk-tab active' : 'risk-tab'} onClick={() => setTab('register')}><ShieldCheck size={16} />{t.riskRegisterTab}</button>{canConfigure && <button type="button" role="tab" aria-selected={tab === 'help'} className={tab === 'help' ? 'risk-tab active' : 'risk-tab'} onClick={() => setTab('help')}>{t.helpSettings}</button>}</div>
    {tab === 'register' ? <section className="data-section"><div className="table-toolbar"><div className="table-count">{filtered.length} <span>{t.risks.toLowerCase()}</span></div><label className="table-search"><span className="sr-only">{t.search}</span><input placeholder={t.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label></div><div className="table-scroll"><table><thead><tr><th>{t.risksTitle}</th><th>{t.riskTaxonomy}</th><th>{t.inherentScore}</th><th>{t.residualScore}</th><th>{t.riskStatus}</th><th>{t.mitigationValidation}</th><th>{t.actions}</th></tr></thead><tbody>{filtered.map((risk) => { const study = studies.find((item) => item.id === risk.study_id); const treatment = risk.mitigations[0]; const validation = validationState(risk.mitigations, staleDays, t); const help = definitions.find((item) => item.id === risk.risk_definition_id) ?? definitions.find((item) => item.subfamily_id === risk.subfamily_id); return <tr key={risk.id} tabIndex={0} aria-label={`${risk.identifier} · ${risk.title} · ${t.openRiskDetail}`} className="risk-row-clickable" onClick={(event) => { if (!(event.target as HTMLElement).closest('a,button,input,select,textarea')) navigate(`/risks/${risk.id}`) }} onKeyDown={(event) => { if (event.target === event.currentTarget && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); navigate(`/risks/${risk.id}`) } }}><td><div className="record-cell"><span className="risk-record-title"><b>{risk.title}</b>{help && <button type="button" className="help-icon-button" aria-label={`${t.openRiskHelp}: ${risk.title}`} onClick={() => setHelpDefinition(help)}><Info size={15} /></button>}</span><small>{risk.identifier}</small><span className="risk-summary-text">{risk.description}</span>{study && <small className="study-under-description">{t.study}: {study.identifier} · {study.title}</small>}</div></td><td><span className="taxonomy-cell"><b>{risk.family_label || t.toQualify}</b><small>{risk.subfamily_id ? `${risk.subfamily_id} · ${risk.subfamily_label}` : t.toQualify}</small></span></td><td><span className="score-cell">{risk.inherent_score}<small>{risk.probability} × {risk.impact}</small></span></td><td>{treatment?.residual_score ?? '—'}</td><td>{canWrite ? <select className="status-select" aria-label={`${t.riskStatus}: ${risk.title}`} value={risk.status} onChange={(event) => void changeStatus(risk, event.target.value)}>{transitions[risk.status]?.map((status) => <option key={status}>{status}</option>)}</select> : <span className="status-label">{risk.status}</span>}</td><td><span className={`validation-badge validation-${validation.tone}`}>{validation.label}</span></td><td><NavLink className="button-secondary compact-button" to={`/mitigations?risk_id=${risk.id}`} onClick={(event) => event.stopPropagation()}>{t.openMitigation}</NavLink></td></tr> })}{filtered.length === 0 && <tr><td colSpan={7} className="empty-cell">{t.noRisks}</td></tr>}</tbody></table></div></section> : <section className="data-section help-settings"><div className="help-settings-heading"><div><h2>{t.helpSettings}</h2><p>{t.helpSettingsSub}</p></div><label>{t.riskDefinition}<select value={helpCode} onChange={(event) => chooseHelp(event.target.value)}><option value="">{t.selectRiskDefinition}</option>{definitions.map((item) => <option key={item.id} value={item.risk_code}>{item.risk_code} · {item.title_en}</option>)}</select></label></div>{helpDraft && <form className="help-settings-form" onSubmit={saveHelp}><label>{t.titleEnglish}<input required value={helpDraft.title_en} onChange={(event) => setHelpDraft({ ...helpDraft, title_en: event.target.value })} /></label><label>{t.titleFrench}<input required value={helpDraft.title_fr} onChange={(event) => setHelpDraft({ ...helpDraft, title_fr: event.target.value })} /></label><label>{t.descriptionEnglish}<textarea required value={helpDraft.description_en} onChange={(event) => setHelpDraft({ ...helpDraft, description_en: event.target.value })} /></label><label>{t.descriptionFrench}<textarea value={helpDraft.description_fr} onChange={(event) => setHelpDraft({ ...helpDraft, description_fr: event.target.value })} /></label><label>{t.causesEnglish}<textarea value={helpDraft.causes} onChange={(event) => setHelpDraft({ ...helpDraft, causes: event.target.value })} /></label><label>{t.causesFrench}<textarea value={helpDraft.causes_fr} onChange={(event) => setHelpDraft({ ...helpDraft, causes_fr: event.target.value })} /></label><label>{t.impactsEnglish}<textarea value={helpDraft.impacts} onChange={(event) => setHelpDraft({ ...helpDraft, impacts: event.target.value })} /></label><label>{t.impactsFrench}<textarea value={helpDraft.impacts_fr} onChange={(event) => setHelpDraft({ ...helpDraft, impacts_fr: event.target.value })} /></label><label>{t.dataQualityNotes}<textarea value={helpDraft.data_quality_notes} onChange={(event) => setHelpDraft({ ...helpDraft, data_quality_notes: event.target.value })} /></label><div className="modal-actions"><button className="button-primary" disabled={busy}>{t.saveHelpSettings}<ArrowRight size={16} /></button></div></form>}</section>}
    {showForm && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowForm(false) }}><form className="modal-panel risk-form-panel" onSubmit={create}>
      <div className="modal-title"><div><span className="page-eyebrow">{t.governanceTraceability}</span><h2>{t.createRisk}</h2></div><button type="button" className="icon-button" aria-label={t.close} onClick={() => setShowForm(false)}><X size={19} /></button></div>
      <label>{t.title}<input required value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
      <label>{t.description}<textarea required value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
      <label>{t.study}<select value={draft.study_id} onChange={(event) => setDraft({ ...draft, study_id: event.target.value })}><option value="">—</option>{studies.map((study) => <option key={study.id} value={study.id}>{study.identifier} · {study.title}</option>)}</select></label>
      <div className="field-pair"><label>{t.family}<select value={draft.family_id} onChange={(event) => setDraft({ ...draft, family_id: event.target.value, subfamily_id: '' })}><option value="">{t.toQualify}</option>{families.map((family) => <option key={family.id} value={family.id}>{family.id} · {language === 'fr' ? family.name_fr : family.name_en}</option>)}</select></label><label>{t.subfamily}<span className="select-with-help"><select value={draft.subfamily_id} disabled={!draft.family_id} onChange={(event) => setDraft({ ...draft, subfamily_id: event.target.value })}><option value="">{draft.family_id ? t.selectSubfamily : t.selectFamilyFirst}</option>{chosenFamily?.types.map((item) => <option key={item.id} value={item.id}>{item.id} · {language === 'fr' ? item.label_fr : item.label_en}</option>)}</select>{draft.subfamily_id && <button type="button" className="help-icon-button" aria-label={t.openRiskHelp} onClick={() => setHelpDefinition(definitions.find((item) => item.subfamily_id === draft.subfamily_id) ?? null)}><Info size={16} /></button>}</span></label></div>
      <RiskScoringFields probability={draft.probability} impact={draft.impact} onProbabilityChange={(value) => setDraft({ ...draft, probability: value })} onImpactChange={(value) => setDraft({ ...draft, impact: value })} language={language} copy={{ probabilityLabel: t.probability, impactLabel: t.impact, matrixResult: t.matrixResult, ratingDefinitions: t.ratingDefinitions, riskMatrix: t.riskMatrix, probabilityShort: t.probabilityShort, impactShort: t.impactShort, critical: t.critical, high: t.high, medium: t.medium, low: t.low }} />
      <div className="field-pair"><label>{t.objectType}<select value={draft.object_code} onChange={(event) => setDraft({ ...draft, object_code: event.target.value, object_ref: '' })}>{refOptions('object_type').map((item) => <option key={item.code} value={item.code}>{selectRef('object_type', item.code)}</option>)}</select></label><label>{t.objectReference}<input className="ardoq-code-input" placeholder={t.ardoqCode} value={draft.object_ref} onChange={(event) => setDraft({ ...draft, object_ref: event.target.value })} /></label></div>
      <div className="ardoq-lookup">
        <div className="ardoq-search-controls"><label>{t.ardoqSearchLabel}<input value={ardoqLabel} onChange={(event) => { ardoqRequest.current += 1; setArdoqBusy(false); setArdoqLabel(event.target.value); setArdoqResults([]); setArdoqError('') }} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); void searchArdoq() } }} /></label><button type="button" className="button-secondary" disabled={ardoqBusy || ardoqLabel.trim().length < 2 || !draft.object_code} onClick={() => void searchArdoq()}><Search size={16} />{ardoqBusy ? t.loading : t.searchArdoq}</button></div>
        {ardoqError && <p role="status">{ardoqError}</p>}
        {ardoqResults.length > 0 && <ul className="ardoq-results" aria-label={t.ardoqResults}>{ardoqResults.map((item) => <li key={item.code}><button type="button" className="button-secondary" onClick={() => { setDraft((current) => ({ ...current, object_ref: item.code })); setArdoqLabel(item.name); setArdoqResults([]) }}><span>{item.name}</span><code>{item.code}</code></button></li>)}</ul>}
      </div>
      <div className="field-pair"><label>{t.sourceType}<select value={draft.source_code} onChange={(event) => setDraft({ ...draft, source_code: event.target.value })}>{refOptions('source_type').map((item) => <option key={item.code} value={item.code}>{selectRef('source_type', item.code)}</option>)}</select></label><label>{t.sourceReference}<input value={draft.source_ref} onChange={(event) => setDraft({ ...draft, source_ref: event.target.value })} /></label></div>
      <div className="field-pair"><label>{t.scopeType}<select value={draft.scope_code} onChange={(event) => setDraft({ ...draft, scope_code: event.target.value })}>{refOptions('scope_type').map((item) => <option key={item.code} value={item.code}>{selectRef('scope_type', item.code)}</option>)}</select></label><label>{t.scopeReference}<input value={draft.scope_ref} onChange={(event) => setDraft({ ...draft, scope_ref: event.target.value })} /></label></div>
      <div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setShowForm(false)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.createRisk}<ArrowRight size={16} /></button></div>
    </form></div>}
    {helpDefinition && <HelpDialog definition={helpDefinition} families={families} language={language} t={t} onClose={() => setHelpDefinition(null)} />}
  </>
}
