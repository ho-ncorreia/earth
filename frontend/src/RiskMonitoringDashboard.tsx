import { useEffect, useState } from 'react'
import { Activity, Check, Clock3, ShieldAlert } from 'lucide-react'
import { api } from './api'
import { en } from './i18n/en'
import { fr } from './i18n/fr'

type Language = 'en' | 'fr'
type Copy = typeof en | typeof fr
type DashboardMetrics = {
  open_risks: number
  critical_risks: number
  average_open_risk_score: number
  mitigations_not_validated: number
  mitigations_stale: number
  mitigations_in_review: number
  risk_status_counts: Record<string, number>
  study_status_counts: Record<string, number>
  open_risk_family_counts: { family_id: string | null; family: string; count: number }[]
}

function BarList({ title, data, emptyLabel }: { title: string; data: { label: string; value: number }[]; emptyLabel: string }) {
  const maximum = Math.max(1, ...data.map((item) => item.value))
  return <section className="monitor-chart"><h2>{title}</h2>{data.length === 0 ? <p className="empty-cell">{emptyLabel}</p> : <ul>{data.map((item) => <li key={item.label}><span className="monitor-chart-label">{item.label}</span><span className="monitor-bar-track" role="img" aria-label={`${item.label}: ${item.value}`}><span className="monitor-bar" style={{ width: `${Math.max(3, (item.value / maximum) * 100)}%` }} /></span><b>{item.value}</b></li>)}</ul>}</section>
}
export function RiskMonitoringDashboard({ t, language }: { t: Copy; language: Language }) {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api<DashboardMetrics>('/dashboard').then(setMetrics).catch((reason) => setError(reason instanceof Error ? reason.message : t.error)) }, [])
  const riskStatuses = ['Open', 'In Progress', 'Reopened', 'Closed', 'Archived']
  const studyStatuses = ['Draft', 'In Progress', 'Ready for Review', 'Under Review', 'Approved', 'Closed', 'Archived']
  return <>
    <header className="page-heading"><div><span className="page-eyebrow">{t.governanceTraceability}</span><h1>{t.riskMonitoring}</h1><p>{t.riskMonitoringSub}</p></div></header>
    {error && <div className="chat-error" role="alert">{error}</div>}{!metrics ? <div className="loading-line">{t.loading}</div> : <>
      <div className="monitor-metrics"><div className="monitor-metric"><span><ShieldAlert size={17} />{t.openRisks}</span><strong>{metrics.open_risks}</strong></div><div className="monitor-metric"><span><Activity size={17} />{t.averageOpenRisk}</span><strong>{metrics.average_open_risk_score.toLocaleString(language === 'fr' ? 'fr-FR' : 'en-US')}</strong><small>{t.probabilityShort} × {t.impactShort}</small></div><div className="monitor-metric monitor-red"><span><Clock3 size={17} />{t.mitigationsNotValidated}</span><strong>{metrics.mitigations_not_validated}</strong></div><div className="monitor-metric monitor-amber"><span><Clock3 size={17} />{t.mitigationsStale}</span><strong>{metrics.mitigations_stale}</strong></div><div className="monitor-metric monitor-green"><span><Check size={17} />{t.mitigationsInReview}</span><strong>{metrics.mitigations_in_review}</strong></div></div>
      <div className="monitor-charts"><BarList title={t.risksByStatus} data={riskStatuses.filter((status) => metrics.risk_status_counts[status]).map((status) => ({ label: t.riskStateLabels[status as keyof typeof t.riskStateLabels] ?? status, value: metrics.risk_status_counts[status] }))} emptyLabel={t.noChartData} /><BarList title={t.openRisksByFamily} data={metrics.open_risk_family_counts.map((item) => ({ label: item.family_id ? `${item.family_id} · ${item.family}` : t.toQualify, value: item.count }))} emptyLabel={t.noChartData} /><BarList title={t.studiesByStatus} data={studyStatuses.filter((status) => metrics.study_status_counts[status]).map((status) => ({ label: t.studyStateLabels[status as keyof typeof t.studyStateLabels] ?? status, value: metrics.study_status_counts[status] }))} emptyLabel={t.noChartData} /></div>
    </>}
  </>
}
