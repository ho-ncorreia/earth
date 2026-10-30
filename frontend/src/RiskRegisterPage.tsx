import { useEffect, useRef, useState, type FormEvent } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { ArrowRight, Info, ShieldCheck, X } from 'lucide-react'
import { api, type Page, type User } from './api'
import { en } from './i18n/en'
import { fr } from './i18n/fr'
import { RiskScoringFields } from './RiskScoringFields'

type Language = 'en' | 'fr'
type Copy = typeof en | typeof fr
type Study = { id: number; identifier: string; title: string; jira_jpd_url: string; confluence_url: string }
export type TaxonomyType = { id: string; family_id: string; label_en: string; label_fr: string }
export type TaxonomyFamily = { id: string; name_en: string; name_fr: string; types: TaxonomyType[] }
export type HelpDefinition = { id: string; risk_code: string; risk_number: number; subfamily_id: string; title_en: string; title_fr: string; description_en: string; description_fr: string; causes: string[]; causes_fr: string[]; impacts: string[]; impacts_fr: string[]; data_quality_notes: string[] }
type ReferenceValue = { id: string; category: 'object_type' | 'source_type' | 'scope_type'; code: string; label_en: string; label_fr: string; is_active: boolean }
type Mitigation = { mitigation_id: string; title: string; status: string; validated_at: string | null; residual_score: number | null }
type Risk = { id: number; identifier: string; title: string; description: string; probability: number; impact: number; inherent_score: number; residual_score: number | null; criticality: string; status: string; study_id: number | null; family_id: string | null; family_label: string | null; family_label_en: string | null; subfamily_id: string | null; subfamily_label: string | null; subfamily_label_en: string | null; risk_definition_id: string | null; mitigations: Mitigation[] }
type HelpDraft = { title_en: string; title_fr: string; description_en: string; description_fr: string; causes: string; causes_fr: string; impacts: string; impacts_fr: string; data_quality_notes: string }
type RiskDraft = { title: string; description: string; probability: string; impact: string; study_id: string; family_id: string; subfamily_id: string; object_type: string; object_ref: string; source_type: string; source_ref: string; scope_type: string; scope_ref: string }
const transitions: Record<string, string[]> = { Identified: ['Identified', 'Assessed'], Assessed: ['Assessed', 'Treatment Defined'], 'Treatment Defined': ['Treatment Defined', 'Mitigation in Progress', 'Monitoring'], 'Mitigation in Progress': ['Mitigation in Progress', 'Monitoring', 'Treatment Defined'], Monitoring: ['Monitoring', 'Accepted', 'Mitigation in Progress', 'Closed'], Accepted: ['Accepted', 'Monitoring', 'Closed'], Closed: ['Closed'] }
const blankDraft = (): RiskDraft => ({ title: '', description: '', probability: '2', impact: '2', study_id: '', family_id: '', subfamily_id: '', object_type: '', object_ref: '', source_type: '', source_ref: '', scope_type: '', scope_ref: '' })
const splitLines = (value: string) => value.split('\n').map((line) => line.trim()).filter(Boolean)

function validationState(mitigations: Mitigation[], staleDays: number, t: Copy) {
  if (!mitigations.length || mitigations.some((item) => item.status !== 'Approved' || !item.validated_at)) return { label: t.mitigationNotValidated, tone: 'not-validated' }
  const isStale = mitigations.some((item) => (Date.now() - new Date(item.validated_at as string).getTime()) / 86400000 >= staleDays)
  return isStale ? { label: t.mitigationValidationStale, tone: 'stale' } : { label: t.mitigationValidated, tone: 'valid' }
}

export function RiskRegisterPage({ t, user, language }: { t: Copy; user: User; language: Language }) {
  const navigate = useNavigate()
  const [risks, setRisks] = useState<Risk[]>([])
  const [studies, setStudies] = useState<Study[]>([])
  const [families, setFamilies] = useState<TaxonomyFamily[]>([])
  const [referenceValues, setReferenceValues] = useState<ReferenceValue[]>([])
  const [definitions, setDefinitions] = useState<HelpDefinition[]>([])
  const [staleDays, setStaleDays] = useState(365)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<'register' | 'help'>('register')
  const [helpDefinition, setHelpDefinition] = useState<HelpDefinition | null>(null)
  const [helpCode, setHelpCode] = useState('')
  const [helpDraft, setHelpDraft] = useState<HelpDraft | null>(null)
  const [draft, setDraft] = useState<RiskDraft>(blankDraft())
  const canWrite = user.role.permissions.includes('risks.write')
  const canConfigure = user.role.permissions.includes('admin.configure')
  const load = async () => {
    try {
      const [riskPage, studyPage, taxonomy, help, settings, references] = await Promise.all([
        api<Page<Risk>>('/risks?limit=100'), api<Page<Study>>('/studies?limit=100'), api<TaxonomyFamily[]>('/risks/catalog'),
        api<HelpDefinition[]>('/risks/catalog/help'), api<{ mitigation_validation_stale_days: number }>('/risks/settings/mitigations'),
        api<{ values: ReferenceValue[] }>('/risks/settings/references'),
      ])
      const activeReferences = references.values.filter((item) => item.is_active)
      const defaultFor = (category: ReferenceValue['category']) => activeReferences.find((item) => item.category === category)?.code ?? ''
      setRisks(riskPage.items); setStudies(studyPage.items); setFamilies(taxonomy); setDefinitions(help); setReferenceValues(activeReferences); setStaleDays(settings.mitigation_validation_stale_days); setError('')
      setDraft((current) => ({ ...current, object_type: current.object_type || defaultFor('object_type'), source_type: current.source_type || defaultFor('source_type'), scope_type: current.scope_type || defaultFor('scope_type') }))
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) {
    event.preventDefault()
    if (Boolean(draft.family_id) !== Boolean(draft.subfamily_id)) { setError(t.taxonomyPairRequired); return }
    setBusy(true); setError('')
    const family = families.find((item) => item.id === draft.family_id)
    const subfamily = family?.types.find((item) => item.id === draft.subfamily_id)
    const definition = definitions.find((item) => item.subfamily_id === draft.subfamily_id)
    const objectType = referenceValues.find((item) => item.category === 'object_type' && item.code === draft.object_type)
    const sourceType = referenceValues.find((item) => item.category === 'source_type' && item.code === draft.source_type)
    const scopeType = referenceValues.find((item) => item.category === 'scope_type' && item.code === draft.scope_type)
    try {
      await api('/risks', { method: 'POST', body: JSON.stringify({
        title: draft.title, description: draft.description, probability: Number(draft.probability), impact: Number(draft.impact),
        study_id: draft.study_id ? Number(draft.study_id) : null, family: family?.name_en ?? '', category: subfamily?.label_en ?? '',
        family_id: draft.family_id || null, subfamily_id: draft.subfamily_id || null, risk_definition_id: definition?.id ?? null,
        objects: draft.object_ref.trim() && objectType ? [{ object_type: objectType.label_en, object_ref: draft.object_ref.trim() }] : [],
        sources: draft.source_ref.trim() && sourceType ? [{ source_type: sourceType.label_en, source_ref: draft.source_ref.trim() }] : [],
        scopes: draft.scope_ref.trim() && scopeType ? [{ scope_type: scopeType.label_en, scope_ref: draft.scope_ref.trim() }] : [],
      }) })
      setShowForm(false); setDraft(blankDraft()); await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  async function changeStatus(risk: Risk, status: string) {
    try { await api(`/risks/${risk.id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : t.invalidAction) }
  }
  function openHelp(code: string) {
    const definition = definitions.find((item) => item.risk_code === code)
    if (definition) setHelpDefinition(definition)
  }
  function definitionFor(risk: Risk) {
    return definitions.find((item) => item.id === risk.risk_definition_id) ?? definitions.find((item) => item.subfamily_id === risk.subfamily_id)
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
    setBusy(true)
    try {
      const saved = await api<HelpDefinition>(`/risks/catalog/help/${helpCode}`, { method: 'PATCH', body: JSON.stringify({ ...helpDraft, causes: splitLines(helpDraft.causes), causes_fr: splitLines(helpDraft.causes_fr), impacts: splitLines(helpDraft.impacts), impacts_fr: splitLines(helpDraft.impacts_fr), data_quality_notes: splitLines(helpDraft.data_quality_notes) }) })
      setDefinitions((current) => current.map((item) => item.id === saved.id ? saved : item))
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  const filtered = risks.map((risk) => ({ ...risk, family_label: language === 'fr' ? risk.family_label : risk.family_label_en, subfamily_label: language === 'fr' ? risk.subfamily_label : risk.subfamily_label_en })).filter((risk) => `${risk.identifier} ${risk.title} ${risk.description} ${risk.family_label ?? ''} ${risk.subfamily_label ?? ''}`.toLowerCase().includes(query.toLowerCase()))
  const chosenFamily = families.find((family) => family.id === draft.family_id)
  useEffect(() => {
    if (tab !== 'register') return
    const table = document.querySelector('.risk-tabs + .data-section table')
    const rows = table?.querySelectorAll<HTMLTableRowElement>('tbody tr')
    if (!rows) return
    const cleanups: (() => void)[] = []
    filtered.forEach((risk, index) => {
      const row = rows[index]
      if (!row) return
      row.tabIndex = 0
      row.setAttribute('aria-label', `${risk.identifier} · ${risk.title} · ${t.openRiskDetail}`)
      row.classList.add('risk-row-clickable')
      const activate = () => navigate(`/risks/${risk.id}`)
      const onClick = (event: Event) => {
        if ((event.target as HTMLElement).closest('a, button, input, select, textarea')) return
        activate()
      }
      const onKeyDown = (event: KeyboardEvent) => {
        if (event.target !== row || (event.key !== 'Enter' && event.key !== ' ')) return
        event.preventDefault()
        activate()
      }
      row.addEventListener('click', onClick)
      row.addEventListener('keydown', onKeyDown)
      cleanups.push(() => { row.removeEventListener('click', onClick); row.removeEventListener('keydown', onKeyDown); row.removeAttribute('tabindex'); row.removeAttribute('aria-label'); row.classList.remove('risk-row-clickable') })
    })
    return () => cleanups.forEach((cleanup) => cleanup())
  }, [filtered, navigate, tab, t.openRiskDetail])
  return <>
    <header className="page-heading"><div><span className="page-eyebrow">{t.governanceTraceability}</span><h1>{t.risksTitle}</h1><p>{t.risksSub}</p></div>{canWrite && tab === 'register' && <button className="button-primary compact-button" onClick={() => { setDraft(blankDraft()); setShowForm(true) }}><ShieldCheck size={16} />{t.createRisk}</button>}</header>
    {error && <div className="chat-error" role="alert">{error}</div>}
    <div className="risk-tabs" role="tablist" aria-label={t.risksTitle}><button type="button" role="tab" aria-selected={tab === 'register'} className={tab === 'register' ? 'risk-tab active' : 'risk-tab'} onClick={() => setTab('register')}><ShieldCheck size={16} />{t.riskRegisterTab}</button>{canConfigure && <button type="button" role="tab" aria-selected={tab === 'help'} className={tab === 'help' ? 'risk-tab active' : 'risk-tab'} onClick={() => setTab('help')}>{t.helpSettings}</button>}</div>
    {tab === 'register' ? <section className="data-section"><div className="table-toolbar"><div className="table-count">{filtered.length} <span>{t.risks.toLowerCase()}</span></div><label className="table-search"><span className="sr-only">{t.search}</span><input placeholder={t.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label></div><div className="table-scroll"><table><thead><tr><th>{t.risksTitle}</th><th>{t.riskTaxonomy}</th><th>{t.inherentScore}</th><th>{t.residualScore}</th><th>{t.riskStatus}</th><th>{t.mitigationValidation}</th><th>{t.actions}</th></tr></thead><tbody>{filtered.map((risk) => { const study = studies.find((item) => item.id === risk.study_id); const treatment = risk.mitigations[0]; const validation = validationState(risk.mitigations, staleDays, t); const help = definitionFor(risk); return <tr key={risk.id}><td><div className="record-cell"><span className="risk-record-title"><b>{risk.title}</b>{help && <button type="button" className="help-icon-button" aria-label={`${t.openRiskHelp}: ${risk.title}`} title={t.openRiskHelp} onClick={() => openHelp(help.risk_code)}><Info size={15} /></button>}</span><small>{risk.identifier}</small><span className="risk-summary-text">{risk.description}</span>{study && <small className="study-under-description">{t.study}: {study.identifier} · {study.title}</small>}</div></td><td><span className="taxonomy-cell"><b>{risk.family_label || t.toQualify}</b><small>{risk.subfamily_id ? `${risk.subfamily_id} · ${risk.subfamily_label}` : t.toQualify}</small></span></td><td><span className="score-cell">{risk.inherent_score}<small>{risk.probability} × {risk.impact}</small></span></td><td>{treatment?.residual_score ?? '—'}</td><td>{canWrite ? <select className="status-select" aria-label={`${t.riskStatus}: ${risk.title}`} value={risk.status} onChange={(event) => void changeStatus(risk, event.target.value)}>{(transitions[risk.status] ?? [risk.status]).map((status) => <option key={status}>{status}</option>)}</select> : <span className="status-label">{risk.status}</span>}</td><td><span className={`validation-badge validation-${validation.tone}`}>{validation.label}</span></td><td><NavLink className="button-secondary compact-button" to={`/mitigations?risk_id=${risk.id}`}>{t.openMitigation}</NavLink></td></tr> })}{filtered.length === 0 && <tr><td colSpan={7} className="empty-cell">{t.noRisks}</td></tr>}</tbody></table></div></section> : <section className="data-section help-settings"><div className="help-settings-heading"><div><h2>{t.helpSettings}</h2><p>{t.helpSettingsSub}</p></div><label>{t.riskDefinition}<select value={helpCode} onChange={(event) => chooseHelp(event.target.value)}><option value="">{t.selectRiskDefinition}</option>{definitions.map((item) => <option key={item.id} value={item.risk_code}>{item.risk_code} · {item.title_en}</option>)}</select></label></div>{helpDraft && <form className="help-settings-form" onSubmit={saveHelp}><div className="field-pair"><label>{t.titleEnglish}<input required value={helpDraft.title_en} onChange={(event) => setHelpDraft({ ...helpDraft, title_en: event.target.value })} /></label><label>{t.titleFrench}<input required value={helpDraft.title_fr} onChange={(event) => setHelpDraft({ ...helpDraft, title_fr: event.target.value })} /></label></div><div className="field-pair"><label>{t.descriptionEnglish}<textarea required value={helpDraft.description_en} onChange={(event) => setHelpDraft({ ...helpDraft, description_en: event.target.value })} /></label><label>{t.descriptionFrench}<textarea value={helpDraft.description_fr} onChange={(event) => setHelpDraft({ ...helpDraft, description_fr: event.target.value })} /></label></div><div className="field-pair"><label>{t.causesEnglish}<textarea value={helpDraft.causes} onChange={(event) => setHelpDraft({ ...helpDraft, causes: event.target.value })} /></label><label>{t.causesFrench}<textarea value={helpDraft.causes_fr} onChange={(event) => setHelpDraft({ ...helpDraft, causes_fr: event.target.value })} /></label></div><div className="field-pair"><label>{t.impactsEnglish}<textarea value={helpDraft.impacts} onChange={(event) => setHelpDraft({ ...helpDraft, impacts: event.target.value })} /></label><label>{t.impactsFrench}<textarea value={helpDraft.impacts_fr} onChange={(event) => setHelpDraft({ ...helpDraft, impacts_fr: event.target.value })} /></label></div><label>{t.dataQualityNotes}<textarea value={helpDraft.data_quality_notes} onChange={(event) => setHelpDraft({ ...helpDraft, data_quality_notes: event.target.value })} /></label><div className="modal-actions"><button className="button-primary" disabled={busy}>{t.saveHelpSettings}<ArrowRight size={16} /></button></div></form>}</section>}
    {showForm && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowForm(false) }}><form className="modal-panel risk-form-panel" onSubmit={create}><div className="modal-title"><div><span className="page-eyebrow">{t.governanceTraceability}</span><h2>{t.createRisk}</h2></div><button type="button" className="icon-button" aria-label={t.close} onClick={() => setShowForm(false)}><X size={19} /></button></div><label>{t.title}<input required value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label><label>{t.description}<textarea required value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label><label>{t.study}<select value={draft.study_id} onChange={(event) => setDraft({ ...draft, study_id: event.target.value })}><option value="">—</option>{studies.map((study) => <option key={study.id} value={study.id}>{study.identifier} · {study.title}</option>)}</select></label><div className="field-pair"><label>{t.family}<select value={draft.family_id} onChange={(event) => setDraft({ ...draft, family_id: event.target.value, subfamily_id: '' })}><option value="">{t.toQualify}</option>{families.map((family) => <option key={family.id} value={family.id}>{family.id} · {language === 'fr' ? family.name_fr : family.name_en}</option>)}</select></label><label>{t.subfamily}<span className="select-with-help"><select value={draft.subfamily_id} disabled={!draft.family_id} onChange={(event) => setDraft({ ...draft, subfamily_id: event.target.value })}><option value="">{draft.family_id ? t.selectSubfamily : t.selectFamilyFirst}</option>{chosenFamily?.types.map((item) => <option key={item.id} value={item.id}>{item.id} · {language === 'fr' ? item.label_fr : item.label_en}</option>)}</select>{draft.subfamily_id && <button type="button" className="help-icon-button" aria-label={t.openRiskHelp} title={t.openRiskHelp} onClick={() => openHelp(definitions.find((item) => item.subfamily_id === draft.subfamily_id)?.risk_code ?? '')}><Info size={16} /></button>}</span></label></div><RiskScoringFields probability={draft.probability} impact={draft.impact} onProbabilityChange={(value) => setDraft({ ...draft, probability: value })} onImpactChange={(value) => setDraft({ ...draft, impact: value })} language={language} copy={{ probabilityLabel: t.probability, impactLabel: t.impact, matrixResult: t.matrixResult, ratingDefinitions: t.ratingDefinitions, riskMatrix: t.riskMatrix, probabilityShort: t.probabilityShort, impactShort: t.impactShort, critical: t.critical, high: t.high, medium: t.medium, low: t.low }} /><div className="field-pair"><label>{t.objectType}<select value={draft.object_type} onChange={(event) => setDraft({ ...draft, object_type: event.target.value })}>{['Application', 'Technology / Component', 'Platform / Infra', 'Data / Integration', 'Service IT / Business', 'Provider / Third Party', 'Archi Domain / Capa', 'Enterprise / IT landscape'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.objectReference}<input className="ardoq-code-input" placeholder={t.ardoqCode} value={draft.object_ref} onChange={(event) => setDraft({ ...draft, object_ref: event.target.value })} /></label></div><div className="field-pair"><label>{t.sourceType}<select value={draft.source_type} onChange={(event) => setDraft({ ...draft, source_type: event.target.value })}>{['ADR / Exception', 'ARB', 'Project', 'App / Techno lifecycle review', 'Audit / Compliance review', 'Incident / Problem mgt'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.sourceReference}<input value={draft.source_ref} onChange={(event) => setDraft({ ...draft, source_ref: event.target.value })} /></label></div><div className="field-pair"><label>{t.scopeType}<select value={draft.scope_type} onChange={(event) => setDraft({ ...draft, scope_type: event.target.value })}>{['Team', 'Domain', 'Capability', 'Company / Entity'].map((value) => <option key={value}>{value}</option>)}</select></label><label>{t.scopeReference}<input value={draft.scope_ref} onChange={(event) => setDraft({ ...draft, scope_ref: event.target.value })} /></label></div><div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setShowForm(false)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.createRisk}<ArrowRight size={16} /></button></div></form></div>}
    {helpDefinition && <HelpDialog definition={helpDefinition} families={families} language={language} t={t} onClose={() => setHelpDefinition(null)} />}
  </>
}

export function HelpDialog({ definition, families, language, t, onClose }: { definition: HelpDefinition; families: TaxonomyFamily[]; language: Language; t: Copy; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const type = families.flatMap((family) => family.types).find((item) => item.id === definition.subfamily_id)
  const family = families.find((item) => item.id === type?.family_id)
  const description = language === 'fr' && definition.description_fr ? definition.description_fr : definition.description_en
  const causes = language === 'fr' && definition.causes_fr.length ? definition.causes_fr : definition.causes
  const impacts = language === 'fr' && definition.impacts_fr.length ? definition.impacts_fr : definition.impacts
  useEffect(() => {
    const prior = document.activeElement as HTMLElement | null
    closeRef.current?.focus()
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); return }
      if (event.key !== 'Tab') return
      const dialog = closeRef.current?.closest('[role="dialog"]')
      const focusable = dialog?.querySelectorAll<HTMLElement>('button:not([disabled]), [tabindex]:not([tabindex="-1"])')
      if (!focusable?.length) { event.preventDefault(); return }
      if (event.shiftKey && document.activeElement === focusable[0]) { event.preventDefault(); focusable[focusable.length - 1].focus() }
      else if (!event.shiftKey && document.activeElement === focusable[focusable.length - 1]) { event.preventDefault(); focusable[0].focus() }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => { document.removeEventListener('keydown', onKeyDown); prior?.focus() }
  }, [definition.id])
  return <div className="modal-backdrop help-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="modal-panel risk-help-dialog" role="dialog" aria-modal="true" aria-labelledby="risk-help-heading"><div className="modal-title"><div><span className="page-eyebrow">{definition.risk_code} · {t.riskNumber} {definition.risk_number}</span><h2 id="risk-help-heading">{language === 'fr' ? definition.title_fr : definition.title_en}</h2></div><button ref={closeRef} type="button" className="icon-button" aria-label={t.close} onClick={onClose}><X size={19} /></button></div><div className="risk-help-scroll" tabIndex={0} aria-label={t.riskHelpContent}><dl className="risk-help-meta"><div><dt>{t.family}</dt><dd>{language === 'fr' ? family?.name_fr : family?.name_en}</dd></div><div><dt>{t.subfamily}</dt><dd>{type?.id} · {language === 'fr' ? type?.label_fr : type?.label_en}</dd></div></dl><section><h3>{t.description}</h3><p>{description}</p></section><div className="field-pair help-lists"><section><h3>{t.causes}</h3><ul>{causes.map((cause, index) => <li key={`${index}-${cause}`}>{cause}</li>)}</ul></section><section><h3>{t.impacts}</h3><ul>{impacts.map((impact, index) => <li key={`${index}-${impact}`}>{impact}</li>)}</ul></section></div>{definition.data_quality_notes.length > 0 && <section className="data-quality-note"><h3>{t.dataQualityNotes}</h3><ul>{definition.data_quality_notes.map((note, index) => <li key={`${index}-${note}`}>{note}</li>)}</ul></section>}</div></section></div>
}
