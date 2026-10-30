import { useEffect, useState, type FormEvent } from 'react'
import { NavLink, useParams } from 'react-router-dom'
import { ArrowLeft, Edit2, ExternalLink, Save, X } from 'lucide-react'
import { api, type Page, type User } from './api'
import { en } from './i18n/en'
import { fr } from './i18n/fr'
import { RiskScoringFields } from './RiskScoringFields'

type Language = 'en' | 'fr'
type Copy = typeof en | typeof fr
type RiskDetail = {
  id: number; identifier: string; title: string; description: string; probability: number; impact: number; inherent_score: number; residual_score: number | null; criticality: string; status: string; study_id: number | null; family_id: string | null; family_label: string | null; family_label_en: string | null; subfamily_id: string | null; subfamily_label: string | null; subfamily_label_en: string | null; risk_definition_id: string | null
  objects: { object_type: string; object_ref: string }[]; sources: { source_type: string; source_ref: string }[]; scopes: { scope_type: string; scope_ref: string }[]
  mitigations: { mitigation_id: string; title: string; description: string; status: string; validated_at: string | null; residual_score: number | null }[]
}
type StudyLink = { id: number; identifier: string; title: string; jira_jpd_url: string; confluence_url: string }
type Taxonomy = { id: string; name_en: string; name_fr: string; types: { id: string; family_id: string; label_en: string; label_fr: string }[] }
type RiskEditDraft = { title: string; description: string; probability: string; impact: string; family_id: string; subfamily_id: string; study_id: string; status: string }
const riskStatuses = ['Open', 'In Progress', 'Closed', 'Archived', 'Reopened']

export function RiskDetailPage({ t, language, user }: { t: Copy; language: Language; user: User }) {
  const { riskId } = useParams()
  const [risk, setRisk] = useState<RiskDetail | null>(null)
  const [study, setStudy] = useState<StudyLink | null>(null)
  const [studies, setStudies] = useState<StudyLink[]>([])
  const [taxonomy, setTaxonomy] = useState<Taxonomy[]>([])
  const [definitions, setDefinitions] = useState<{ id: string; subfamily_id: string }[]>([])
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<RiskEditDraft | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!riskId) return
    Promise.all([api<RiskDetail>(`/risks/${riskId}`), api<Page<StudyLink>>('/studies?limit=100'), api<Taxonomy[]>('/risks/catalog'), api<{ id: string; subfamily_id: string }[]>('/risks/catalog/help')]).then(([record, studyPage, availableTaxonomy, availableDefinitions]) => {
      setRisk(record)
      setStudies(studyPage.items)
      setTaxonomy(availableTaxonomy)
      setDefinitions(availableDefinitions)
      setDraft({ title: record.title, description: record.description, probability: String(record.probability), impact: String(record.impact), family_id: record.family_id ?? '', subfamily_id: record.subfamily_id ?? '', study_id: record.study_id ? String(record.study_id) : '', status: record.status })
      setStudy(null)
      if (record.study_id) {
        setStudy(studyPage.items.find((item) => item.id === record.study_id) ?? null)
      }
    }).catch((reason) => setError(reason instanceof Error ? reason.message : t.error))
  }, [riskId])
  const canWrite = user.role.permissions.includes('risks.write')
  const family = language === 'fr' ? risk?.family_label : risk?.family_label_en
  const subfamily = language === 'fr' ? risk?.subfamily_label : risk?.subfamily_label_en
  const selectedFamily = taxonomy.find((item) => item.id === draft?.family_id)
  async function saveRisk(event: FormEvent) {
    event.preventDefault()
    if (!risk || !draft) return
    if (Boolean(draft.family_id) !== Boolean(draft.subfamily_id)) { setError(t.taxonomyPairRequired); return }
    setBusy(true); setError('')
    const definition = definitions.find((item) => item.subfamily_id === draft.subfamily_id)
    try {
      const updated = await api<RiskDetail>(`/risks/${risk.id}`, { method: 'PATCH', body: JSON.stringify({
        title: draft.title.trim(), description: draft.description.trim(), probability: Number(draft.probability), impact: Number(draft.impact),
        family_id: draft.family_id || null, subfamily_id: draft.subfamily_id || null, risk_definition_id: definition?.id ?? null,
        study_id: draft.study_id ? Number(draft.study_id) : null, status: draft.status,
      }) })
      setRisk(updated)
      setStudy(studies.find((item) => item.id === updated.study_id) ?? null)
      setEditing(false)
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  return <>
    <NavLink className="back-link" to="/risks"><ArrowLeft size={15} />{t.backToRisks}</NavLink>
    {error && <div className="chat-error" role="alert">{error}</div>}
    {risk && <>
      <header className="page-heading risk-detail-heading"><div><span className="page-eyebrow">{risk.identifier}</span><h1>{risk.title}</h1></div><div className="risk-detail-actions">{canWrite && <button type="button" className="button-secondary compact-button" onClick={() => setEditing(true)}><Edit2 size={14} />{t.editRisk}</button>}<NavLink className="button-secondary compact-button" to={`/mitigations?risk_id=${risk.id}`}>{t.openMitigation}</NavLink></div></header>
      <section className="risk-detail-section"><h2>{t.description}</h2><p>{risk.description}</p>{study && <div className="risk-study-inline"><b>{t.study}:</b> {study.identifier} · {study.title}{study.jira_jpd_url && <a href={study.jira_jpd_url} target="_blank" rel="noreferrer">Jira JPD <ExternalLink size={13} /></a>}{study.confluence_url && <a href={study.confluence_url} target="_blank" rel="noreferrer">Confluence <ExternalLink size={13} /></a>}</div>}</section>
      <div className="risk-detail-grid"><section className="risk-detail-section"><h2>{t.riskTaxonomy}</h2><dl><div><dt>{t.family}</dt><dd>{risk.family_id ? `${risk.family_id} · ${family}` : t.toQualify}</dd></div><div><dt>{t.subfamily}</dt><dd>{risk.subfamily_id ? `${risk.subfamily_id} · ${subfamily}` : t.toQualify}</dd></div></dl></section><section className="risk-detail-section"><h2>{t.inherentAssessment}</h2><div className="risk-detail-score"><strong>{risk.inherent_score}</strong><span>{risk.probability} × {risk.impact}</span><b className={`criticality-tag criticality-${risk.criticality.toLowerCase()}`}>{risk.criticality}</b></div></section></div>
      <div className="risk-detail-grid"><section className="risk-detail-section"><h2>{t.objects}</h2>{risk.objects.length ? <ul>{risk.objects.map((item, index) => <li key={`${item.object_type}-${index}`}><b>{item.object_type}</b><span>{item.object_ref || '—'}</span></li>)}</ul> : <p>—</p>}</section><section className="risk-detail-section"><h2>{t.sources}</h2>{risk.sources.length ? <ul>{risk.sources.map((item, index) => <li key={`${item.source_type}-${index}`}><b>{item.source_type}</b><span>{item.source_ref || '—'}</span></li>)}</ul> : <p>—</p>}</section><section className="risk-detail-section"><h2>{t.scope}</h2>{risk.scopes.length ? <ul>{risk.scopes.map((item, index) => <li key={`${item.scope_type}-${index}`}><b>{item.scope_type}</b><span>{item.scope_ref || '—'}</span></li>)}</ul> : <p>—</p>}</section></div>
      <section className="risk-detail-section"><div className="risk-detail-section-heading"><h2>{t.mitigationsTitle}</h2><NavLink className="text-link" to={`/mitigations?risk_id=${risk.id}`}>{t.openMitigation}</NavLink></div>{risk.mitigations.length ? <ul className="risk-detail-mitigations">{risk.mitigations.map((item) => <li key={item.mitigation_id}><div><b>{item.title || t.mitigationTitleRequired}</b><small>{item.description || t.mitigationDescriptionRequired}</small></div><span className={`validation-badge ${item.status === 'Approved' ? 'validation-valid' : 'validation-not-validated'}`}>{item.status}</span><NavLink className="button-secondary compact-button" to={`/mitigations?risk_id=${risk.id}`}>{t.openMitigation}</NavLink></li>)}</ul> : <p>{t.noMitigations}</p>}</section>
    </>}
    {editing && draft && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setEditing(false) }}><form className="modal-panel risk-form-panel" onSubmit={saveRisk}><div className="modal-title"><div><span className="page-eyebrow">{risk?.identifier}</span><h2>{t.editRisk}</h2></div><button type="button" className="icon-button" aria-label={t.close} onClick={() => setEditing(false)}><X size={19} /></button></div><label>{t.title}<input required maxLength={240} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label><label>{t.description}<textarea required maxLength={4000} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label><label>{t.study}<select value={draft.study_id} onChange={(event) => setDraft({ ...draft, study_id: event.target.value })}><option value="">—</option>{studies.map((item) => <option key={item.id} value={item.id}>{item.identifier} · {item.title}</option>)}</select></label><div className="field-pair"><label>{t.family}<select value={draft.family_id} onChange={(event) => setDraft({ ...draft, family_id: event.target.value, subfamily_id: '' })}><option value="">{t.toQualify}</option>{taxonomy.map((item) => <option key={item.id} value={item.id}>{item.id} · {language === 'fr' ? item.name_fr : item.name_en}</option>)}</select></label><label>{t.subfamily}<select value={draft.subfamily_id} disabled={!draft.family_id} onChange={(event) => setDraft({ ...draft, subfamily_id: event.target.value })}><option value="">{draft.family_id ? t.selectSubfamily : t.selectFamilyFirst}</option>{selectedFamily?.types.map((item) => <option key={item.id} value={item.id}>{item.id} · {language === 'fr' ? item.label_fr : item.label_en}</option>)}</select></label></div><RiskScoringFields probability={draft.probability} impact={draft.impact} onProbabilityChange={(value) => setDraft({ ...draft, probability: value })} onImpactChange={(value) => setDraft({ ...draft, impact: value })} language={language} copy={{ probabilityLabel: t.probability, impactLabel: t.impact, matrixResult: t.matrixResult, ratingDefinitions: t.ratingDefinitions, riskMatrix: t.riskMatrix, probabilityShort: t.probabilityShort, impactShort: t.impactShort, critical: t.critical, high: t.high, medium: t.medium, low: t.low }} /><label>{t.riskStatus}<select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}>{riskStatuses.map((status) => <option key={status}>{status}</option>)}</select></label>{error && <div role="alert" className="form-error">{error}</div>}<div className="modal-actions"><button type="button" className="button-secondary" onClick={() => setEditing(false)}>{t.cancel}</button><button className="button-primary" disabled={busy}>{busy ? t.loading : t.save}<Save size={16} /></button></div></form></div>}
  </>
}
