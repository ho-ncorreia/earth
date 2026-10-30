import { useEffect, useState, type FormEvent } from 'react'
import { NavLink, useSearchParams } from 'react-router-dom'
import { Check, ClipboardCheck, ExternalLink, FileUp, Save, Send, X } from 'lucide-react'
import { api, type User } from './api'
import { en } from './i18n/en'
import { fr } from './i18n/fr'
import { RatingDefinitions } from './RiskScoringFields'

type Language = 'en' | 'fr'
type Copy = typeof en | typeof fr
type Attachment = { id: string; file_name: string; content_type: string; file_size: number; created_at: string }
type Review = { id: string; reviewer_id: number; reviewer_name: string; decision: 'Approved' | 'Rejected'; comment: string; created_at: string }
type Mitigation = { mitigation_id: string; risk_id: number; risk_identifier: string; risk_title: string; title: string; description: string; residual_probability: number | null; residual_impact: number | null; residual_score: number | null; treatment_strategy: string; control_effectiveness: string; status: 'Draft' | 'Submitted' | 'Approved' | 'Rejected'; submitted_at: string | null; validated_at: string | null; validated_by_id: number | null; validation_comment: string; updated_at: string | null; attachments: Attachment[]; reviews: Review[] }
type Draft = { title: string; description: string; residual_probability: string; residual_impact: string; treatment_strategy: string; control_effectiveness: string }
const emptyDraft: Draft = { title: '', description: '', residual_probability: '', residual_impact: '', treatment_strategy: 'Reduce', control_effectiveness: 'Unknown' }
const probabilityLabels = { en: ['Unlikely', 'Possible', 'Probable', 'Quasi certain'], fr: ['Peu probable', 'Possible', 'Probable', 'Quasi certain'] }
const impactLabels = { en: ['Minor', 'Significant', 'Major', 'Review'], fr: ['Mineur', 'Significatif', 'Majeur', 'À revoir'] }
const acceptedFiles = '.pdf,.png,.jpg,.jpeg,.txt,.docx'

function validationState(mitigation: Mitigation, staleDays: number, t: Copy) {
  if (mitigation.status !== 'Approved' || !mitigation.validated_at) return { label: t.mitigationNotValidated, tone: 'not-validated' }
  const ageDays = (Date.now() - new Date(mitigation.validated_at).getTime()) / 86400000
  return ageDays >= staleDays ? { label: t.mitigationValidationStale, tone: 'stale' } : { label: t.mitigationValidated, tone: 'valid' }
}

export function MitigationsPage({ t, user, language }: { t: Copy; user: User; language: Language }) {
  const [mitigations, setMitigations] = useState<Mitigation[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [draft, setDraft] = useState<Draft>(emptyDraft)
  const [staleDays, setStaleDays] = useState(365)
  const [staleDaysDraft, setStaleDaysDraft] = useState('365')
  const [reviewComment, setReviewComment] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [searchParams] = useSearchParams()
  const canWrite = user.role.permissions.includes('risks.write')
  const canApprove = user.role.permissions.includes('risks.approve')
  const canConfigure = user.role.permissions.includes('admin.configure')
  const selected = mitigations.find((item) => item.mitigation_id === selectedId) ?? null
  const selectedValidation = selected ? validationState(selected, staleDays, t) : null

  async function load() {
    try {
      const [items, config] = await Promise.all([api<Mitigation[]>('/risks/mitigations'), api<{ mitigation_validation_stale_days: number }>('/risks/settings/mitigations')])
      setMitigations(items)
      setStaleDays(config.mitigation_validation_stale_days)
      setStaleDaysDraft(String(config.mitigation_validation_stale_days))
      const riskQuery = Number(searchParams.get('risk_id'))
      const preferred = items.find((item) => item.risk_id === riskQuery) ?? items.find((item) => item.mitigation_id === selectedId) ?? items[0]
      if (preferred) select(preferred)
      else { setSelectedId(''); setDraft(emptyDraft) }
      setError('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  function select(mitigation: Mitigation) {
    setSelectedId(mitigation.mitigation_id)
    setDraft({ title: mitigation.title, description: mitigation.description, residual_probability: mitigation.residual_probability?.toString() ?? '', residual_impact: mitigation.residual_impact?.toString() ?? '', treatment_strategy: mitigation.treatment_strategy, control_effectiveness: mitigation.control_effectiveness })
    setReviewComment('')
  }
  useEffect(() => { void load() }, [])

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!selected) return
    if (!draft.title.trim()) { setError(`${t.validationFixFields} ${t.title}: ${t.mitigationTitleRequired}`); document.querySelector<HTMLInputElement>('.mitigation-form input')?.focus(); return }
    if (Boolean(draft.residual_probability) !== Boolean(draft.residual_impact)) { setError(`${t.validationFixFields} ${t.residualProbability}, ${t.residualImpact}: ${t.residualPairRequired}`); document.querySelector<HTMLElement>('.mitigation-form select')?.focus(); return }
    setBusy(true); setError(''); setNotice('')
    try {
      const updated = await api<Mitigation>(`/risks/mitigations/${selected.mitigation_id}`, { method: 'PATCH', body: JSON.stringify({
        title: draft.title, description: draft.description,
        residual_probability: draft.residual_probability ? Number(draft.residual_probability) : null,
        residual_impact: draft.residual_impact ? Number(draft.residual_impact) : null,
        treatment_strategy: draft.treatment_strategy, control_effectiveness: draft.control_effectiveness,
      }) })
      setMitigations((current) => current.map((item) => item.mitigation_id === updated.mitigation_id ? updated : item))
      setNotice(t.mitigationSaved)
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  async function submitForReview() {
    if (!selected) return
    const missing: string[] = []
    if (!draft.title.trim()) missing.push(`${t.title}: ${t.mitigationTitleRequired}`)
    if (!draft.description.trim()) missing.push(`${t.description}: ${t.mitigationDescriptionRequired}`)
    if (!draft.residual_probability || !draft.residual_impact) missing.push(`${t.residualProbability} / ${t.residualImpact}: ${t.residualScoresRequired}`)
    if (missing.length) {
      setError(`${t.validationFixFields} ${missing.join(' · ')}`)
      const form = document.querySelector('.mitigation-form')
      const controls = form?.querySelectorAll<HTMLElement>('input, textarea, select')
      const firstInvalid = [!draft.title.trim(), !draft.description.trim(), !draft.residual_probability, !draft.residual_impact].findIndex(Boolean)
      if (firstInvalid >= 0) controls?.[firstInvalid]?.focus()
      return
    }
    setBusy(true); setError('')
    try {
      await api(`/risks/mitigations/${selected.mitigation_id}`, { method: 'PATCH', body: JSON.stringify({
        title: draft.title.trim(), description: draft.description.trim(),
        residual_probability: Number(draft.residual_probability), residual_impact: Number(draft.residual_impact),
        treatment_strategy: draft.treatment_strategy, control_effectiveness: draft.control_effectiveness,
      }) })
      const updated = await api<Mitigation>(`/risks/mitigations/${selected.mitigation_id}/submit`, { method: 'POST', body: JSON.stringify({}) })
      setMitigations((current) => current.map((item) => item.mitigation_id === updated.mitigation_id ? updated : item)); select(updated)
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  async function review(decision: 'Approved' | 'Rejected') {
    if (!selected) return
    if (decision === 'Rejected' && !reviewComment.trim()) { setError(t.rejectionCommentRequired); return }
    setBusy(true); setError('')
    try {
      const updated = await api<Mitigation>(`/risks/mitigations/${selected.mitigation_id}/review`, { method: 'POST', body: JSON.stringify({ decision, comment: reviewComment }) })
      setMitigations((current) => current.map((item) => item.mitigation_id === updated.mitigation_id ? updated : item)); select(updated)
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  async function upload(event: FormEvent<HTMLInputElement>) {
    if (!selected) return
    const file = event.currentTarget.files?.[0]
    if (!file) return
    const body = new FormData(); body.append('file', file)
    setBusy(true); setError('')
    try {
      const updated = await api<Mitigation>(`/risks/mitigations/${selected.mitigation_id}/attachments`, { method: 'POST', body })
      setMitigations((current) => current.map((item) => item.mitigation_id === updated.mitigation_id ? updated : item)); select(updated)
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false); event.currentTarget.value = '' }
  }
  async function saveSettings(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      const result = await api<{ mitigation_validation_stale_days: number }>('/risks/settings/mitigations', { method: 'PUT', body: JSON.stringify({ mitigation_validation_stale_days: Number(staleDaysDraft) }) })
      setStaleDays(result.mitigation_validation_stale_days); setNotice(t.settingsSaved)
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
    finally { setBusy(false) }
  }
  const score = draft.residual_probability && draft.residual_impact ? Number(draft.residual_probability) * Number(draft.residual_impact) : null

  return <>
    <header className="page-heading"><div><span className="page-eyebrow">{t.governanceTraceability}</span><h1>{t.mitigationsTitle}</h1><p>{t.mitigationsSub}</p></div></header>
    <div className="mitigation-rating-reference"><RatingDefinitions language={language} copy={{ probabilityLabel: t.probability, impactLabel: t.impact, matrixResult: t.matrixResult, ratingDefinitions: t.ratingDefinitions, riskMatrix: t.riskMatrix, probabilityShort: t.probabilityShort, impactShort: t.impactShort, critical: t.critical, high: t.high, medium: t.medium, low: t.low, close: t.close, probabilityHelp: t.probabilityHelp, impactHelp: t.impactHelp, criticalityHelp: t.criticalityHelp }} /></div>
    {error && <div className="chat-error mitigation-page-error" role="alert">{error}</div>}{notice && <div className="toast" role="status">{notice}</div>}
    <section className="mitigation-workspace"><aside className="mitigation-rail"><div className="mitigation-rail-heading"><h2>{t.mitigationsTitle}</h2><span>{mitigations.length}</span></div>{mitigations.length === 0 && <p className="empty-cell">{t.noMitigations}</p>}{mitigations.map((item) => { const state = validationState(item, staleDays, t); return <button type="button" className={`mitigation-rail-item ${item.mitigation_id === selectedId ? 'selected' : ''}`} key={item.mitigation_id} onClick={() => select(item)}><span className="mitigation-rail-main"><b>{item.title || t.treatmentPlan}</b><small>{item.risk_identifier} · {item.risk_title}</small></span><span className={`validation-badge validation-${state.tone}`}>{state.label}</span></button> })}</aside>
      {selected ? <article className="mitigation-detail"><header className="mitigation-detail-heading"><div><span className="page-eyebrow">{selected.mitigation_id.slice(0, 8)}</span><h2>{selected.title}</h2><NavLink className="mitigation-risk-link" to={`/risks/${selected.risk_id}`}><ExternalLink size={14} />{selected.risk_identifier} · {selected.risk_title}</NavLink></div>{selectedValidation && <span className={`validation-badge validation-${selectedValidation.tone}`}>{selectedValidation.label}</span>}</header>
        <form className="mitigation-form" onSubmit={save}><label>{t.title}<input required maxLength={240} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label><label>{t.description}<textarea maxLength={2000} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label><div className="residual-score-result"><span>{t.residualScore}</span><strong>{score === null ? '—' : `${score} · ${score >= 12 ? t.critical : score >= 8 ? t.high : score >= 4 ? t.medium : t.low}`}</strong>{score !== null && <small>{draft.residual_probability} × {draft.residual_impact}</small>}</div><div className="field-pair"><label>{t.residualProbability}<select value={draft.residual_probability} onChange={(event) => setDraft({ ...draft, residual_probability: event.target.value })}><option value="">—</option>{probabilityLabels[language].map((label, index) => <option key={label} value={index + 1}>{index + 1} · {label}</option>)}</select></label><label>{t.residualImpact}<select value={draft.residual_impact} onChange={(event) => setDraft({ ...draft, residual_impact: event.target.value })}><option value="">—</option>{impactLabels[language].map((label, index) => <option key={label} value={index + 1}>{index + 1} · {label}</option>)}</select></label></div><div className="field-pair"><label>{t.treatmentStrategy}<select value={draft.treatment_strategy} onChange={(event) => setDraft({ ...draft, treatment_strategy: event.target.value })}>{['Avoid', 'Reduce', 'Transfer', 'Accept'].map((item) => <option key={item}>{item}</option>)}</select></label><label>{t.controlEffectiveness}<select value={draft.control_effectiveness} onChange={(event) => setDraft({ ...draft, control_effectiveness: event.target.value })}>{['Unknown', 'Low', 'Moderate', 'High'].map((item) => <option key={item}>{item}</option>)}</select></label></div><div className="mitigation-form-actions">{canWrite && <button className="button-primary" disabled={busy}><Save size={15} />{t.save}</button>}{canWrite && ['Draft', 'Rejected'].includes(selected.status) && <button type="button" className="button-secondary" disabled={busy} onClick={() => void submitForReview()}><Send size={15} />{t.submitMitigation}</button>}</div></form>
        <section className="mitigation-attachments"><div className="mitigation-section-heading"><h3>{t.attachments}</h3>{canWrite && <label className="button-secondary compact-button"><FileUp size={15} />{t.attachFile}<input type="file" accept={acceptedFiles} hidden onChange={(event) => void upload(event)} /></label>}</div>{selected.attachments.length === 0 ? <p>{t.noAttachments}</p> : <ul>{selected.attachments.map((file) => <li key={file.id}><a href={`/api/v1/risks/mitigations/${selected.mitigation_id}/attachments/${file.id}`}>{file.file_name}</a><small>{(file.file_size / 1024).toFixed(0)} KB</small></li>)}</ul>}</section>
        {selected.status === 'Submitted' && canApprove && <section className="mitigation-review"><h3>{t.validationDecision}</h3><label>{t.reviewComment}<textarea value={reviewComment} onChange={(event) => setReviewComment(event.target.value)} /></label><div className="mitigation-form-actions"><button type="button" className="button-secondary reject-button" disabled={busy} onClick={() => void review('Rejected')}><X size={15} />{t.rejectMitigation}</button><button type="button" className="button-primary" disabled={busy} onClick={() => void review('Approved')}><Check size={15} />{t.approveMitigation}</button></div></section>}
        {selected.reviews.length > 0 && <section className="mitigation-review-history"><h3>{t.validationHistory}</h3>{[...selected.reviews].reverse().map((entry) => <div key={entry.id}><b>{entry.decision === 'Approved' ? t.approved : t.rejected}</b><span>{entry.reviewer_name} · {new Date(entry.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US')}</span>{entry.comment && <p>{entry.comment}</p>}</div>)}</section>}
      </article> : <div className="mitigation-detail mitigation-empty"><ClipboardCheck size={26} /><h2>{t.selectMitigation}</h2></div>}
    </section>
    {canConfigure && <form className="mitigation-settings" onSubmit={saveSettings}><label>{t.staleValidationAfter}<span><input type="number" min="1" max="3650" value={staleDaysDraft} onChange={(event) => setStaleDaysDraft(event.target.value)} />{t.days}</span></label><button className="button-secondary" disabled={busy}>{t.save}</button></form>}
  </>
}
