import { useEffect, useRef, useState } from 'react'
import { Info, X } from 'lucide-react'

type Language = 'en' | 'fr'
export type RiskScoringCopy = {
  probabilityLabel: string
  impactLabel: string
  matrixResult: string
  ratingDefinitions: string
  riskMatrix: string
  probabilityShort: string
  impactShort: string
  critical: string
  high: string
  medium: string
  low: string
  close?: string
  probabilityHelp?: string
  impactHelp?: string
  criticalityHelp?: string
}

const guides = {
  en: {
    probabilityLabels: ['Unlikely', 'Possible', 'Probable', 'Quasi certain'],
    impactLabels: ['Minor', 'Significant', 'Major', 'Review'],
    probabilityDefinitions: [
      'The risk could occur but few risk factors are present. Existing mechanisms make it unlikely that it will materialize.',
      'Some risk factors are present and the scenario is credible, but its materialization remains uncertain.',
      'Several risk factors are present, weaknesses are identified or similar situations have already occurred.',
      'Several risk factors are present, weaknesses are identified or similar situations have already occurred.',
    ],
    impactDefinitions: [
      'Localized impact, easily reversible, with no significant effect on business, services or costs.',
      'Limited degradation of a service, moderate cost or remediation effort, manageable business impact.',
      'Significant impact on an important service or process, high costs, significant disruption or significant safety/regulatory exposure.',
      'Major impact on a critical business or service, prolonged interruption, significant data loss, major regulatory/security exposure, or a strategic consequence that is difficult to reverse.',
    ],
    criticalityDefinitions: ['Requires immediate management attention and treatment.', 'Requires planned treatment and regular monitoring.', 'Requires proportionate treatment and monitoring.', 'Acceptable only with routine monitoring.'],
  },
  fr: {
    probabilityLabels: ['Peu probable', 'Possible', 'Probable', 'Quasi certain'],
    impactLabels: ['Mineur', 'Significatif', 'Majeur', 'À revoir'],
    probabilityDefinitions: [
      'Le risque peut survenir, mais peu de facteurs de risque sont présents. Les mécanismes existants rendent sa matérialisation peu probable.',
      'Certains facteurs de risque sont présents et le scénario est crédible, mais sa matérialisation reste incertaine.',
      'Plusieurs facteurs de risque sont présents, des faiblesses sont identifiées ou des situations similaires se sont déjà produites.',
      'Plusieurs facteurs de risque sont présents, des faiblesses sont identifiées ou des situations similaires se sont déjà produites.',
    ],
    impactDefinitions: [
      'Impact localisé, facilement réversible, sans effet significatif sur l’activité, les services ou les coûts.',
      'Dégradation limitée d’un service, coût ou effort de remédiation modéré, impact métier maîtrisable.',
      'Impact important sur un service ou processus essentiel, coûts élevés, perturbation ou exposition sécurité/réglementaire significative.',
      'Impact majeur sur une activité ou un service critique, interruption prolongée, perte importante de données, exposition réglementaire/sécurité majeure ou conséquence stratégique difficilement réversible.',
    ],
    criticalityDefinitions: ['Traitement prioritaire et attention immédiate de la direction.', 'Traitement planifié et suivi régulier.', 'Traitement proportionné et suivi adapté.', 'Acceptable avec une surveillance courante.'],
  },
} as const

function matrixLevel(score: number, copy: RiskScoringCopy) {
  if (score >= 12) return { label: copy.critical, tone: 'critical' }
  if (score >= 8) return { label: copy.high, tone: 'high' }
  if (score >= 4) return { label: copy.medium, tone: 'medium' }
  return { label: copy.low, tone: 'low' }
}

export function RatingDefinitions({ language, copy }: { language: Language; copy: RiskScoringCopy }) {
  const [topic, setTopic] = useState<'probability' | 'impact' | 'criticality' | null>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const guide = guides[language]
  useEffect(() => {
    if (!topic) return
    const previousFocus = document.activeElement as HTMLElement | null
    closeRef.current?.focus()
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); setTopic(null) }
      if (event.key === 'Tab') { event.preventDefault(); closeRef.current?.focus() }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => { document.removeEventListener('keydown', onKeyDown); previousFocus?.focus() }
  }, [topic])
  const criticalityLevels = [
    { label: copy.critical, score: '12+', tone: 'critical', description: guide.criticalityDefinitions[0] },
    { label: copy.high, score: '8–11', tone: 'high', description: guide.criticalityDefinitions[1] },
    { label: copy.medium, score: '4–7', tone: 'medium', description: guide.criticalityDefinitions[2] },
    { label: copy.low, score: '1–3', tone: 'low', description: guide.criticalityDefinitions[3] },
  ]
  const heading = topic === 'probability' ? copy.probabilityLabel : topic === 'impact' ? copy.impactLabel : copy.criticalityHelp
  const helpLabels = language === 'fr'
    ? { probability: 'Aide probabilité', impact: 'Aide impact', criticality: 'Niveaux de criticité', close: 'Fermer' }
    : { probability: 'Probability help', impact: 'Impact help', criticality: 'Criticality levels', close: 'Close' }
  return <>
    <div className="rating-help-controls"><button type="button" className="rating-help-button" onClick={() => setTopic('probability')}><Info size={14} />{copy.probabilityHelp ?? helpLabels.probability}</button><button type="button" className="rating-help-button" onClick={() => setTopic('impact')}><Info size={14} />{copy.impactHelp ?? helpLabels.impact}</button><button type="button" className="rating-help-button" onClick={() => setTopic('criticality')}><Info size={14} />{copy.criticalityHelp ?? helpLabels.criticality}</button></div>
    {topic && <div className="modal-backdrop rating-help-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setTopic(null) }}><section className="modal-panel rating-help-dialog" role="dialog" aria-modal="true" aria-labelledby="rating-help-heading"><div className="modal-title"><h2 id="rating-help-heading">{heading ?? helpLabels.criticality}</h2><button ref={closeRef} type="button" className="icon-button" aria-label={copy.close ?? helpLabels.close} onClick={() => setTopic(null)}><X size={18} /></button></div><div className="rating-help-content">{topic === 'probability' && <ol>{guide.probabilityDefinitions.map((definition, index) => <li key={index}><b>{index + 1} · {guide.probabilityLabels[index]}</b><span>{definition}</span></li>)}</ol>}{topic === 'impact' && <ol>{guide.impactDefinitions.map((definition, index) => <li key={index}><b>{index + 1} · {guide.impactLabels[index]}</b><span>{definition}</span></li>)}</ol>}{topic === 'criticality' && <ol>{criticalityLevels.map((item) => <li key={item.tone}><b className={`criticality-tag criticality-${item.tone}`}>{item.score} · {item.label}</b><span>{item.description}</span></li>)}</ol>}</div></section></div>}
  </>
}

export function RiskScoringFields({ probability, impact, onProbabilityChange, onImpactChange, language, copy }: {
  probability: string
  impact: string
  onProbabilityChange: (value: string) => void
  onImpactChange: (value: string) => void
  language: Language
  copy: RiskScoringCopy
}) {
  const guide = guides[language]
  const score = Number(probability) * Number(impact)
  const result = matrixLevel(score, copy)
  return <section className="risk-scoring-fields">
    <div className={`matrix-result criticality-${result.tone}`}><span>{copy.matrixResult}</span><strong>{score} · {result.label}</strong><small>{probability} × {impact}</small></div>
    <div className="field-pair">
      <label>{copy.probabilityLabel}<select value={probability} onChange={(event) => onProbabilityChange(event.target.value)}>{guide.probabilityLabels.map((label, index) => <option key={label} value={index + 1}>{index + 1} · {label}</option>)}</select></label>
      <label>{copy.impactLabel}<select value={impact} onChange={(event) => onImpactChange(event.target.value)}>{guide.impactLabels.map((label, index) => <option key={label} value={index + 1}>{index + 1} · {label}</option>)}</select></label>
    </div>
    <RatingDefinitions language={language} copy={copy} />
  </section>
}
