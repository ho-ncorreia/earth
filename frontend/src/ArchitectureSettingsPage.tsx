import { useEffect, useState, type FormEvent } from 'react'
import { Database, Plus, Save } from 'lucide-react'
import { api } from './api'
import { en } from './i18n/en'
import { fr } from './i18n/fr'

type Copy = typeof en | typeof fr
type Domain = { id: number; name: string; is_active: boolean }
type Family = { id: string; name_en: string; name_fr: string }
type Subfamily = { id: string; family_id: string; label_en: string; label_fr: string }
type ReferenceValue = { id: string; category: 'object_type' | 'source_type' | 'scope_type'; code: string; label_en: string; label_fr: string; is_active: boolean }
type ReferenceData = { families: Family[]; subfamilies: Subfamily[]; values: ReferenceValue[] }
type DatabaseColumn = { name: string; type: string; nullable: boolean; primary_key: boolean; foreign_key: boolean }
type DatabaseForeignKey = { columns: string[]; references_table: string | null; references_columns: string[]; from_cardinality: string; to_cardinality: string }
type DatabaseTable = { name: string; row_count: number; columns: DatabaseColumn[]; foreign_keys: DatabaseForeignKey[] }
type DatabaseSchema = { database: string; tables: DatabaseTable[] }
type DatabaseRows = { table: string; columns: string[]; items: Record<string, unknown>[]; total: number; limit: number; offset: number }
type ArdoqSettings = { api_host: string; org_label: string; token_configured: boolean; root_workspace_id: string; component_type_ids: Record<string, string>; object_types: { code: string; label_en: string; label_fr: string; is_active: boolean }[] }
type Tab = 'domain' | 'family' | 'subfamily' | 'object_type' | 'source_type' | 'scope_type' | 'ardoq' | 'database'

export function ArchitectureSettingsPage({ t, language }: { t: Copy; language: 'en' | 'fr' }) {
  const [domains, setDomains] = useState<Domain[]>([])
  const [families, setFamilies] = useState<Family[]>([])
  const [subfamilies, setSubfamilies] = useState<Subfamily[]>([])
  const [values, setValues] = useState<ReferenceValue[]>([])
  const [databaseSchema, setDatabaseSchema] = useState<DatabaseSchema | null>(null)
  const [ardoqSettings, setArdoqSettings] = useState<ArdoqSettings | null>(null)
  const [ardoqWorkspaceId, setArdoqWorkspaceId] = useState('')
  const [ardoqTypeIds, setArdoqTypeIds] = useState<Record<string, string>>({})
  const [selectedTable, setSelectedTable] = useState('')
  const [tableRows, setTableRows] = useState<DatabaseRows | null>(null)
  const [tableOffset, setTableOffset] = useState(0)
  const [tableBusy, setTableBusy] = useState(false)
  const [domainNames, setDomainNames] = useState<Record<number, string>>({})
  const [familyNames, setFamilyNames] = useState<Record<string, { en: string; fr: string }>>({})
  const [subfamilyNames, setSubfamilyNames] = useState<Record<string, { en: string; fr: string }>>({})
  const [valueNames, setValueNames] = useState<Record<string, { en: string; fr: string }>>({})
  const [newName, setNewName] = useState('')
  const [newLabelEn, setNewLabelEn] = useState('')
  const [newLabelFr, setNewLabelFr] = useState('')
  const [tab, setTab] = useState<Tab>('domain')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  async function load() {
    try {
      const [domainList, referenceData, schema, ardoq] = await Promise.all([api<Domain[]>('/studies/domains?include_inactive=true'), api<ReferenceData>('/risks/settings/references'), api<DatabaseSchema>('/admin/database/schema'), api<ArdoqSettings>('/risks/settings/ardoq')])
      setDomains(domainList); setFamilies(referenceData.families); setSubfamilies(referenceData.subfamilies); setValues(referenceData.values)
      setDatabaseSchema(schema); setSelectedTable((current) => current || schema.tables[0]?.name || '')
      setArdoqSettings(ardoq); setArdoqWorkspaceId(ardoq.root_workspace_id); setArdoqTypeIds(ardoq.component_type_ids)
      setDomainNames(Object.fromEntries(domainList.map((item) => [item.id, item.name])))
      setFamilyNames(Object.fromEntries(referenceData.families.map((item) => [item.id, { en: item.name_en, fr: item.name_fr }])))
      setSubfamilyNames(Object.fromEntries(referenceData.subfamilies.map((item) => [item.id, { en: item.label_en, fr: item.label_fr }])))
      setValueNames(Object.fromEntries(referenceData.values.map((item) => [item.id, { en: item.label_en, fr: item.label_fr }])))
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.error) }
  }
  useEffect(() => { void load() }, [])
  useEffect(() => {
    if (tab !== 'database' || !selectedTable) return
    let active = true
    setTableBusy(true)
    api<DatabaseRows>(`/admin/database/tables/${encodeURIComponent(selectedTable)}/rows?limit=50&offset=${tableOffset}`)
      .then((result) => { if (active) setTableRows(result) })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : t.error) })
      .finally(() => { if (active) setTableBusy(false) })
    return () => { active = false }
  }, [tab, selectedTable, tableOffset])
  function announceError(reason: unknown) { setError(reason instanceof Error ? reason.message : t.error); setNotice('') }
  async function saveRequest(operation: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('')
    try { await operation(); setNotice(t.settingsSaved); await load() }
    catch (reason) { announceError(reason) }
    finally { setBusy(false) }
  }
  async function createDomain(event: FormEvent) {
    event.preventDefault()
    if (!newName.trim()) return
    await saveRequest(async () => { await api('/studies/domains', { method: 'POST', body: JSON.stringify({ name: newName.trim() }) }); setNewName('') })
  }
  async function saveDomain(domain: Domain, changes: Partial<Pick<Domain, 'name' | 'is_active'>>) {
    await saveRequest(async () => { await api(`/studies/domains/${domain.id}`, { method: 'PATCH', body: JSON.stringify(changes) }) })
  }
  async function saveFamily(family: Family) {
    const labels = familyNames[family.id]
    await saveRequest(async () => { await api(`/risks/settings/families/${family.id}`, { method: 'PATCH', body: JSON.stringify({ name_en: labels.en, name_fr: labels.fr }) }) })
  }
  async function saveSubfamily(item: Subfamily) {
    const labels = subfamilyNames[item.id]
    await saveRequest(async () => { await api(`/risks/settings/subfamilies/${encodeURIComponent(item.id)}`, { method: 'PATCH', body: JSON.stringify({ label_en: labels.en, label_fr: labels.fr }) }) })
  }
  async function createValue(event: FormEvent) {
    event.preventDefault()
    if (!newLabelEn.trim() || !newLabelFr.trim()) return
    await saveRequest(async () => { await api('/risks/settings/references', { method: 'POST', body: JSON.stringify({ category: tab, label_en: newLabelEn.trim(), label_fr: newLabelFr.trim() }) }); setNewLabelEn(''); setNewLabelFr('') })
  }
  async function updateValue(item: ReferenceValue, changes: Partial<Pick<ReferenceValue, 'label_en' | 'label_fr' | 'is_active'>>) {
    await saveRequest(async () => { await api(`/risks/settings/references/${item.id}`, { method: 'PATCH', body: JSON.stringify(changes) }) })
  }
  async function saveArdoq(event: FormEvent) {
    event.preventDefault()
    await saveRequest(async () => { await api('/risks/settings/ardoq', { method: 'PUT', body: JSON.stringify({ root_workspace_id: ardoqWorkspaceId, component_type_ids: ardoqTypeIds }) }) })
  }
  const referenceTabs: { id: Tab; label: string }[] = [
    { id: 'domain', label: t.architectureDomains }, { id: 'family', label: t.families }, { id: 'subfamily', label: t.subfamilies },
    { id: 'object_type', label: t.objectTypes }, { id: 'source_type', label: t.sourceTypes }, { id: 'scope_type', label: t.scopeTypes },
    { id: 'ardoq', label: t.ardoqIntegration },
    { id: 'database', label: t.databaseModel },
  ]
  const tabValues = values.filter((item) => item.category === tab)
  return <>
    <header className="page-heading"><div><span className="page-eyebrow">{t.administration}</span><h1>{t.architectureSettings}</h1><p>{t.architectureSettingsSub}</p></div></header>
    {error && <div className="chat-error" role="alert">{error}</div>}{notice && <div className="toast" role="status">{notice}</div>}
    <div className="risk-tabs settings-tabs" role="tablist" aria-label={t.architectureSettings}>{referenceTabs.map((item) => <button key={item.id} type="button" role="tab" aria-selected={tab === item.id} className={tab === item.id ? 'risk-tab active' : 'risk-tab'} onClick={() => setTab(item.id)}>{item.id === 'database' && <Database size={15} />}{item.label}</button>)}</div>
    {tab === 'domain' && <section className="data-section architecture-domain-settings"><div className="section-heading"><div><h2>{t.architectureDomains}</h2><p>{t.architectureDomainsSub}</p></div></div><form className="domain-create-form" onSubmit={createDomain}><label>{t.domainName}<input required maxLength={120} value={newName} onChange={(event) => setNewName(event.target.value)} /></label><button className="button-primary" disabled={busy}><Plus size={15} />{t.addDomain}</button></form><div className="domain-setting-list">{domains.map((domain) => <div className="domain-setting-row" key={domain.id}><span className="domain-setting-id">D{String(domain.id).padStart(3, '0')}</span><label><span className="sr-only">{t.domainName}</span><input value={domainNames[domain.id] ?? domain.name} disabled={!domain.is_active} onChange={(event) => setDomainNames((current) => ({ ...current, [domain.id]: event.target.value }))} /></label>{domain.is_active && <button className="button-secondary compact-button" disabled={busy || domainNames[domain.id] === domain.name} onClick={() => void saveDomain(domain, { name: domainNames[domain.id] })}><Save size={14} />{t.save}</button>}<button type="button" className={domain.is_active ? 'button-secondary compact-button' : 'button-primary compact-button'} disabled={busy} onClick={() => void saveDomain(domain, { is_active: !domain.is_active })}>{domain.is_active ? t.deactivateDomain : t.activateDomain}</button></div>)}</div></section>}
    {tab === 'family' && <section className="data-section architecture-domain-settings"><p className="settings-note">{t.taxonomyIdsRemainStable}</p><div className="domain-setting-list">{families.map((family) => <div className="taxonomy-setting-row" key={family.id}><b>{family.id}</b><label>{t.labelEnglish}<input value={familyNames[family.id]?.en ?? family.name_en} onChange={(event) => setFamilyNames((current) => ({ ...current, [family.id]: { ...current[family.id], en: event.target.value } }))} /></label><label>{t.labelFrench}<input value={familyNames[family.id]?.fr ?? family.name_fr} onChange={(event) => setFamilyNames((current) => ({ ...current, [family.id]: { ...current[family.id], fr: event.target.value } }))} /></label><button className="button-secondary compact-button" disabled={busy || (familyNames[family.id]?.en === family.name_en && familyNames[family.id]?.fr === family.name_fr)} onClick={() => void saveFamily(family)}><Save size={14} />{t.save}</button></div>)}</div></section>}
    {tab === 'subfamily' && <section className="data-section architecture-domain-settings"><p className="settings-note">{t.taxonomyIdsRemainStable}</p><div className="domain-setting-list">{subfamilies.map((item) => <div className="taxonomy-setting-row" key={item.id}><b>{item.id}</b><span>{families.find((family) => family.id === item.family_id)?.name_fr ?? item.family_id}</span><label>{t.labelEnglish}<input value={subfamilyNames[item.id]?.en ?? item.label_en} onChange={(event) => setSubfamilyNames((current) => ({ ...current, [item.id]: { ...current[item.id], en: event.target.value } }))} /></label><label>{t.labelFrench}<input value={subfamilyNames[item.id]?.fr ?? item.label_fr} onChange={(event) => setSubfamilyNames((current) => ({ ...current, [item.id]: { ...current[item.id], fr: event.target.value } }))} /></label><button className="button-secondary compact-button" disabled={busy || (subfamilyNames[item.id]?.en === item.label_en && subfamilyNames[item.id]?.fr === item.label_fr)} onClick={() => void saveSubfamily(item)}><Save size={14} />{t.save}</button></div>)}</div></section>}
    {(tab === 'object_type' || tab === 'source_type' || tab === 'scope_type') && <section className="data-section architecture-domain-settings"><form className="reference-create-form" onSubmit={createValue}><label>{t.labelEnglish}<input required maxLength={160} value={newLabelEn} onChange={(event) => setNewLabelEn(event.target.value)} /></label><label>{t.labelFrench}<input required maxLength={160} value={newLabelFr} onChange={(event) => setNewLabelFr(event.target.value)} /></label><button className="button-primary" disabled={busy}><Plus size={15} />{t.addReferenceValue}</button></form><div className="domain-setting-list">{tabValues.map((item) => <div className="taxonomy-setting-row" key={item.id}><b>{item.code}</b><label>{t.labelEnglish}<input value={valueNames[item.id]?.en ?? item.label_en} disabled={!item.is_active} onChange={(event) => setValueNames((current) => ({ ...current, [item.id]: { ...current[item.id], en: event.target.value } }))} /></label><label>{t.labelFrench}<input value={valueNames[item.id]?.fr ?? item.label_fr} disabled={!item.is_active} onChange={(event) => setValueNames((current) => ({ ...current, [item.id]: { ...current[item.id], fr: event.target.value } }))} /></label>{item.is_active && <button className="button-secondary compact-button" disabled={busy || (valueNames[item.id]?.en === item.label_en && valueNames[item.id]?.fr === item.label_fr)} onClick={() => void updateValue(item, { label_en: valueNames[item.id].en, label_fr: valueNames[item.id].fr })}><Save size={14} />{t.save}</button>}<button type="button" className={item.is_active ? 'button-secondary compact-button' : 'button-primary compact-button'} disabled={busy} onClick={() => void updateValue(item, { is_active: !item.is_active })}>{item.is_active ? t.deactivateDomain : t.activateDomain}</button></div>)}</div></section>}
    {tab === 'ardoq' && ardoqSettings && <section className="data-section architecture-domain-settings"><div className="section-heading"><div><h2>{t.ardoqIntegration}</h2><p>{t.ardoqSettingsSub}</p></div><span className={`validation-badge ${ardoqSettings.token_configured ? 'validation-valid' : 'validation-not-validated'}`}>{ardoqSettings.token_configured ? t.ardoqTokenReady : t.ardoqTokenMissing}</span></div><form className="ardoq-settings-form" onSubmit={saveArdoq}><div className="field-pair"><label>{t.ardoqApiHost}<input readOnly value={ardoqSettings.api_host} /></label><label>{t.ardoqOrgLabel}<input readOnly value={ardoqSettings.org_label || '—'} /></label></div><label>{t.ardoqRootWorkspace}<input required value={ardoqWorkspaceId} onChange={(event) => setArdoqWorkspaceId(event.target.value)} /></label><div className="domain-setting-list">{ardoqSettings.object_types.filter((item) => item.is_active).map((item) => <div className="ardoq-type-row" key={item.code}><b>{language === 'fr' ? item.label_fr : item.label_en}</b><code>{item.code}</code><label>{t.ardoqComponentTypeId}<input value={ardoqTypeIds[item.code] ?? ''} onChange={(event) => setArdoqTypeIds((current) => ({ ...current, [item.code]: event.target.value }))} /></label></div>)}</div><div className="modal-actions"><button className="button-primary" disabled={busy}>{t.save}<Save size={15} /></button></div></form></section>}
    {tab === 'database' && databaseSchema && <DatabaseTableBrowser schema={databaseSchema} selectedTable={selectedTable} onSelect={(name) => { setSelectedTable(name); setTableOffset(0) }} rows={tableRows} offset={tableOffset} onOffset={setTableOffset} busy={tableBusy} t={t} />}
  </>
}

function DatabaseTableBrowser({ schema, selectedTable, onSelect, rows, offset, onOffset, busy, t }: { schema: DatabaseSchema; selectedTable: string; onSelect: (name: string) => void; rows: DatabaseRows | null; offset: number; onOffset: (offset: number) => void; busy: boolean; t: Copy }) {
  const table = schema.tables.find((item) => item.name === selectedTable)
  return <section className="data-section database-schema-panel"><header className="database-schema-toolbar"><div><h2>{t.databaseModel}</h2><p>{t.databaseModelSub} · {schema.database}</p></div></header><div className="database-model-layout"><nav className="database-table-list" aria-label={t.table}>{schema.tables.map((item) => <button key={item.name} type="button" className={item.name === selectedTable ? 'database-table-item selected' : 'database-table-item'} onClick={() => onSelect(item.name)}><b>{item.name}</b><span>{item.row_count}</span></button>)}</nav><article className="database-table-detail">{table && <><header className="database-table-heading"><div><span className="page-eyebrow">{t.table}</span><h3>{table.name}</h3></div><span className="database-row-count">{table.row_count} {t.rows}</span></header><div className="database-relation-list"><h4>{t.relationships}</h4>{table.foreign_keys.length ? table.foreign_keys.map((key, index) => <div className="database-relation" key={`${key.references_table}-${index}`}><span className="relation-table-name">{table.name}</span><span className="relation-cardinality">{key.from_cardinality}</span><span className="relation-line" aria-hidden="true" /><span className="relation-cardinality">{key.to_cardinality}</span><button type="button" className="relation-table-name relation-target" onClick={() => key.references_table && onSelect(key.references_table)}>{key.references_table} · {key.references_columns.join(', ')}</button></div>) : <p>{t.noRelationships}</p>}</div><div className="database-columns"><h4>{t.columns}</h4><div className="table-scroll"><table><thead><tr><th>{t.column}</th><th>{t.dataType}</th><th>{t.nullable}</th><th>{t.key}</th></tr></thead><tbody>{table.columns.map((column) => <tr key={column.name}><td><b>{column.name}</b></td><td>{column.type}</td><td>{column.nullable ? t.yes : t.no}</td><td>{column.primary_key ? t.primaryKey : column.foreign_key ? t.foreignKey : '—'}</td></tr>)}</tbody></table></div></div><div className="database-records"><h4>{t.records}</h4>{busy ? <p>{t.loading}</p> : rows && rows.items.length ? <div className="table-scroll"><table><thead><tr>{rows.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.items.map((row, rowIndex) => <tr key={String(row.id ?? rowIndex)}>{rows.columns.map((column) => <td key={column}>{row[column] === null ? '—' : typeof row[column] === 'object' ? JSON.stringify(row[column]) : String(row[column])}</td>)}</tr>)}</tbody></table></div> : <p>{t.noRecords}</p>}<div className="database-pagination"><span>{rows ? `${rows.offset + 1}–${Math.min(rows.offset + rows.items.length, rows.total)} / ${rows.total}` : '—'}</span><button className="button-secondary compact-button" disabled={busy || offset === 0} onClick={() => onOffset(Math.max(0, offset - 50))}>{t.previous}</button><button className="button-secondary compact-button" disabled={busy || !rows || offset + rows.limit >= rows.total} onClick={() => onOffset(offset + 50)}>{t.next}</button></div></div></>}</article></div></section>
}
