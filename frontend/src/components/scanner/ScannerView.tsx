import { useEffect, useState } from 'react'
import { Ban, BrainCircuit, CheckCircle2, Crosshair, FileDown, FileText, Pause, Play, Radar, Square, Wrench } from 'lucide-react'
import toast from 'react-hot-toast'
import { useScannerStore } from '../../stores/scannerStore'
import { SeverityBadge } from '../shared/Badge'
import { apiError } from '../../services/api'
import { historyService } from '../../services/proxyService'
import { scannerService } from '../../services/scannerService'
import { settingsService, type ScopeRule } from '../../services/settingsService'
import { hostInScope as hostInScopeFn } from '../../utils/scope'
import type { Finding } from '../../types/scanner'

const SEVERITIES = ['critical', 'high', 'medium', 'low', 'info']
const SCOPE_LS_KEY = 'phantom.scanner.onlyInScope'

export function ScannerView() {
  const store = useScannerStore()
  const [scanType, setScanType] = useState<'passive' | 'active' | 'full'>('passive')
  const [selected, setSelected] = useState<string[]>([])
  const [severityFilter, setSeverityFilter] = useState('')
  const [targetHost, setTargetHost] = useState('')
  const [targets, setTargets] = useState<Array<{ host: string; count: number }>>([])
  const [scopeRules, setScopeRules] = useState<ScopeRule[]>([])
  const [onlyInScope, setOnlyInScope] = useState(() => {
    try {
      return localStorage.getItem(SCOPE_LS_KEY) === '1'
    } catch {
      return false
    }
  })

  const toggleScopeFilter = () => {
    setOnlyInScope((v) => {
      try {
        localStorage.setItem(SCOPE_LS_KEY, v ? '0' : '1')
      } catch {
        /* non-fatal */
      }
      return !v
    })
  }

  const loadTargets = async () => {
    try {
      const [t, rules] = await Promise.all([scannerService.targets(), settingsService.scope()])
      setTargets(t)
      setScopeRules(rules)
    } catch {
      /* transient — dropdown just stays empty */
    }
  }

  useEffect(() => {
    void store.load()
    void loadTargets()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const includeRules = scopeRules.filter(
    (r) => r.rule_type === 'include' && (r.is_active === 1 || r.is_active === true),
  )
  const hostInScope = (host: string) => hostInScopeFn(scopeRules, host)
  const inScopeTargetCount = targets.filter((t) => hostInScope(t.host)).length
  const IN_SCOPE = '__in_scope__'

  const findingHostInScope = (f: Finding) => {
    try {
      return hostInScope(new URL(f.url).hostname)
    } catch {
      return true // unparsable URL — don't hide it
    }
  }

  const addHostToScope = async (host: string) => {
    try {
      await settingsService.addScope({ rule_type: 'include', host_pattern: host, protocol: 'any', path_pattern: '.*' })
      toast.success(`${host} added to active-scan scope`)
      void loadTargets()
    } catch (err) {
      toast.error(apiError(err))
    }
  }

  const [exportOpen, setExportOpen] = useState(false)
  const exportReport = async (format: 'markdown' | 'html') => {
    setExportOpen(false)
    try {
      const params = new URLSearchParams({ format })
      if (severityFilter) params.set('severity', severityFilter)
      const r = await fetch(`/api/scanner/report?${params}`)
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `phantom-report.${format === 'markdown' ? 'md' : 'html'}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`Report exported (${format})`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err))
    }
  }

  const visibleFindings = store.findings.filter((f) => {
    if (severityFilter && f.severity !== severityFilter) return false
    if (onlyInScope && !findingHostInScope(f)) return false
    return true
  })

  const runningScans = store.scans.filter((s) => s.status === 'running' || s.status === 'paused')

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* scan config bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '8px 12px',
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border-primary)',
          flexWrap: 'wrap',
        }}
      >
        <Radar size={14} color="var(--accent-primary)" />
        <select className="input" value={scanType} onChange={(e) => setScanType(e.target.value as 'passive' | 'active' | 'full')} style={{ width: 110 }}>
          <option value="passive">Passive</option>
          <option value="active">Active</option>
          <option value="full">Full</option>
        </select>
        <select
          className="input"
          title="Scan target — hosts seen in your proxy history"
          value={targetHost}
          onChange={(e) => setTargetHost(e.target.value)}
          style={{ width: 260 }}
        >
          <option value="">All captured hosts ({targets.reduce((a, t) => a + t.count, 0)} requests)</option>
          <option value={IN_SCOPE}>
            In-scope hosts — {includeRules.length === 0 ? 'no rules, = all' : `${inScopeTargetCount} host${inScopeTargetCount === 1 ? '' : 's'} (${targets.filter((t) => hostInScope(t.host)).reduce((a, t) => a + t.count, 0)} requests)`}
          </option>
          {targets.map((t) => (
            <option key={t.host} value={t.host}>
              {t.host} ({t.count})
            </option>
          ))}
        </select>
        <select
          className="input"
          value={selected.length ? selected[0] : ''}
          onChange={(e) => setSelected(e.target.value ? [e.target.value] : [])}
          style={{ width: 190 }}
        >
          <option value="">All checks</option>
          {store.checks.map((c) => (
            <option key={c.check_type} value={c.check_type}>
              {c.name} ({c.mode})
            </option>
          ))}
        </select>
        <button
          className="btn primary sm"
          disabled={store.starting}
          onClick={() => void store.startScan(scanType, selected, targetHost === IN_SCOPE ? undefined : targetHost || undefined, targetHost === IN_SCOPE)}
        >
          {store.starting ? 'Starting…' : 'Start scan'}
        </button>
        {scanType !== 'passive' && !targetHost && (
          <span style={{ fontSize: 10.5, color: 'var(--severity-medium)' }}>
            Pick a target host for active scanning
          </span>
        )}
        {scanType !== 'passive' && targetHost === IN_SCOPE && includeRules.length === 0 && (
          <span style={{ fontSize: 10.5, color: 'var(--severity-medium)' }}>
            No scope rules yet — add one in Settings → Scope
          </span>
        )}
        {scanType !== 'passive' && targetHost === IN_SCOPE && includeRules.length > 0 && (
          <span style={{ fontSize: 10.5, color: 'var(--severity-low)' }}>✓ in-scope hosts · authorized targets only</span>
        )}
        {scanType !== 'passive' && targetHost && targetHost !== IN_SCOPE && !hostInScope(targetHost) && (
          <button className="btn sm" style={{ color: 'var(--severity-medium)' }} onClick={() => void addHostToScope(targetHost)}>
            Add {targetHost} to scope
          </button>
        )}
        {scanType !== 'passive' && targetHost && targetHost !== IN_SCOPE && hostInScope(targetHost) && (
          <span style={{ fontSize: 10.5, color: 'var(--severity-low)' }}>✓ {targetHost} in scope · authorized targets only</span>
        )}
        <div style={{ flex: 1 }} />
        <button
          className={`btn ghost sm ${onlyInScope ? 'primary' : ''}`}
          onClick={toggleScopeFilter}
          title={
            includeRules.length > 0
              ? `Toggle: show only findings on in-scope hosts (${includeRules.length} include rule${includeRules.length === 1 ? '' : 's'} active)`
              : 'No include scope rules defined — add one in Settings → Scope for this to filter anything'
          }
        >
          <Crosshair size={12} />
          Scope: {includeRules.length === 0 ? 'none' : `${includeRules.length} rule${includeRules.length === 1 ? '' : 's'}`}
          {onlyInScope ? ' · filtering' : ''}
        </button>
        <select className="input" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} style={{ width: 130 }}>
          <option value="">All severities</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          {visibleFindings.length === store.findings.length
            ? `${store.findings.length} findings`
            : `${visibleFindings.length} of ${store.findings.length} findings`}
        </span>
        <button
          className="btn sm"
          disabled={!!store.triageProgress}
          title="Let the AI review the findings list and flag likely false positives"
          onClick={() => void store.runTriage()}
        >
          <BrainCircuit size={12} />
          {store.triageProgress
            ? `Triaging ${store.triageProgress.done}/${store.triageProgress.total}…`
            : 'AI Triage'}
        </button>
        <span style={{ position: 'relative' }}>
          <button
            className="btn sm"
            onClick={() => setExportOpen((o) => !o)}
            title={`Export report${severityFilter ? ` (${severityFilter} only)` : ' (all severities)'}`}
          >
            <FileDown size={12} /> Export
          </button>
          {exportOpen && (
            <div
              className="fade-in"
              style={{
                position: 'absolute',
                top: '110%',
                right: 0,
                zIndex: 300,
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-active)',
                borderRadius: 'var(--radius-md)',
                padding: 4,
                minWidth: 170,
                boxShadow: '0 10px 30px rgba(0,0,0,0.55)',
              }}
            >
              <button className="btn ghost sm" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={() => void exportReport('markdown')}>
                <FileText size={12} /> Markdown (.md)
              </button>
              <button className="btn ghost sm" style={{ width: '100%', justifyContent: 'flex-start' }} onClick={() => void exportReport('html')}>
                <FileDown size={12} /> HTML (printable)
              </button>
            </div>
          )}
        </span>
      </div>

      {/* running scans */}
      {runningScans.length > 0 && (
        <div style={{ display: 'flex', gap: 10, padding: '6px 12px', borderBottom: '1px solid var(--border-primary)', background: 'var(--bg-tertiary)' }}>
          {runningScans.map((s) => {
            const p = store.progress[s.id]
            const pct = p && p.total ? Math.round((p.done / p.total) * 100) : 0
            return (
              <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, flex: 1 }}>
                <span className="pulse-dot" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--accent-primary)' }} />
                <span className="mono">{s.id}</span>
                <div style={{ flex: 1, height: 4, background: 'var(--bg-primary)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent-primary)', transition: 'width 300ms ease' }} />
                </div>
                <span style={{ color: 'var(--text-secondary)' }}>{pct}%</span>
                {s.status === 'running' ? (
                  <button className="btn ghost sm" title="Pause" onClick={() => void store.control(s.id, 'pause')}><Pause size={11} /></button>
                ) : (
                  <button className="btn ghost sm" title="Resume" onClick={() => void store.control(s.id, 'resume')}><Play size={11} /></button>
                )}
                <button className="btn ghost sm danger" title="Stop" onClick={() => void store.control(s.id, 'stop')}><Square size={11} /></button>
              </div>
            )
          })}
        </div>
      )}

      <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        {/* findings list */}
        <div style={{ width: 420, flex: '0 0 auto', overflow: 'auto', borderRight: '1px solid var(--border-primary)' }}>
          {store.findings.length === 0 && !store.selectedFinding && (
            <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 12, textAlign: 'center' }}>
              No findings yet — run a passive scan over your captured history.
            </div>
          )}
          {visibleFindings.map((f) => (
            <div
              key={f.id}
              className="fade-in"
              onClick={() => store.selectFinding(f)}
              style={{
                padding: '8px 12px',
                borderBottom: '1px solid var(--border-primary)',
                cursor: 'pointer',
                background: store.selectedFinding?.id === f.id ? 'var(--bg-active)' : 'transparent',
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <SeverityBadge severity={f.severity} />
                <span style={{ fontSize: 12, fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {f.title}
                </span>
                {f.ai_verdict && <AiVerdictBadge verdict={f.ai_verdict.verdict} />}
                {(f.status ?? 'open') !== 'open' && (
                  <span style={{ fontSize: 9.5, color: f.status === 'false_positive' ? 'var(--text-muted)' : 'var(--severity-low)' }}>
                    {(f.status ?? '').replace('_', ' ')}
                  </span>
                )}
              </div>
              <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {f.url}
              </div>
            </div>
          ))}
        </div>

        {/* finding detail */}
        <div style={{ flex: 1, minWidth: 0, overflow: 'auto' }}>
          {store.selectedFinding ? <FindingDetail finding={store.selectedFinding} /> : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              Select a finding to inspect
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function FindingDetail({ finding }: { finding: Finding }) {
  const store = useScannerStore()
  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <SeverityBadge severity={finding.severity} />
        <span style={{ fontSize: 9.5, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
          confidence: {finding.confidence} · {finding.finding_type}{finding.cwe_id ? ` · ${finding.cwe_id}` : ''}
        </span>
        <div style={{ flex: 1 }} />
        <button className="btn sm" onClick={() => void store.setFindingStatus(finding.id, 'confirmed')} title="Mark confirmed">
          <CheckCircle2 size={11} /> Confirm
        </button>
        <button className="btn sm" onClick={() => void store.setFindingStatus(finding.id, 'false_positive')} title="Mark false positive">
          <Ban size={11} /> False positive
        </button>
        <button className="btn sm" onClick={() => void store.setFindingStatus(finding.id, 'fixed')} title="Mark fixed">
          <Wrench size={11} /> Fixed
        </button>
      </div>

      <section>
        <SectionTitle>Description</SectionTitle>
        <p style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--text-primary)' }}>{finding.description}</p>
      </section>

      {finding.url && (
        <section>
          <SectionTitle>Affected URL{finding.parameter ? ` · parameter: ${finding.parameter}` : ''}</SectionTitle>
          <div className="mono panel" style={{ padding: 8, fontSize: 11, wordBreak: 'break-all' }}>{finding.url}</div>
        </section>
      )}

      {finding.payload && (
        <section>
          <SectionTitle>Payload</SectionTitle>
          <pre className="mono panel" style={{ padding: 8, fontSize: 11, whiteSpace: 'pre-wrap' }}>{finding.payload}</pre>
        </section>
      )}

      {finding.evidence && (
        <section>
          <SectionTitle>Evidence</SectionTitle>
          <pre className="mono panel" style={{ padding: 8, fontSize: 11, whiteSpace: 'pre-wrap', color: 'var(--severity-high)' }}>{finding.evidence}</pre>
        </section>
      )}

      {finding.remediation && (
        <section>
          <SectionTitle>Remediation</SectionTitle>
          <p style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--severity-low)' }}>{finding.remediation}</p>
        </section>
      )}

      {finding.ai_verdict && (
        <section>
          <SectionTitle>AI assessment</SectionTitle>
          <div className="panel" style={{ padding: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <AiVerdictBadge verdict={finding.ai_verdict.verdict} />
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                priority {finding.ai_verdict.priority}/5
                {finding.ai_verdict.model ? ` · ${finding.ai_verdict.model}` : ''}
              </span>
            </div>
            <p style={{ fontSize: 12, lineHeight: 1.5 }}>{finding.ai_verdict.reason}</p>
            <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>advisory — your own status always wins</span>
          </div>
        </section>
      )}

      {finding.history_id != null && (
        <section>
          <SectionTitle>Actions</SectionTitle>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn sm"
              onClick={async () => {
                try {
                  const { repeater_tab_id } = await historyService.sendToRepeater(finding.history_id!)
                  toast.success(`Sent to Repeater tab #${repeater_tab_id}`)
                } catch (err) {
                  toast.error(apiError(err))
                }
              }}
            >
              Reproduce in Repeater
            </button>
          </div>
        </section>
      )}

      <section>
        <SectionTitle>AI & Plugins</SectionTitle>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            className="btn sm primary"
            onClick={async () => {
              const { useCopilotStore } = await import('../../stores/copilotStore')
              void useCopilotStore.getState().analyzeFinding(finding.id, finding.title)
              window.location.hash = '#/copilot'
            }}
          >
            <BrainCircuit size={11} /> Analyze with AI Copilot
          </button>
          {finding.history_id != null && (
            <button
              className="btn sm"
              onClick={async () => {
                const { usePluginStore } = await import('../../stores/pluginStore')
                void usePluginStore.getState().start('hpere', { kind: 'request', history_id: finding.history_id })
                window.location.hash = '#/plugins'
              }}
            >
              ⛏ Run Hpere
            </button>
          )}
          <button className="btn sm" title="Locate this request's site in the Target tree" onClick={() => { window.location.hash = '#/target' }}>
            🌳 View in Target
          </button>
        </div>
      </section>
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.2, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
      {children}
    </div>
  )
}

const VERDICT_STYLE: Record<string, { label: string; color: string }> = {
  'likely-real': { label: 'AI ✓ REAL', color: 'var(--severity-low)' },
  'likely-fp': { label: 'AI ✗ FP', color: 'var(--severity-critical)' },
  'needs-manual': { label: 'AI ? CHECK', color: 'var(--severity-medium)' },
}

function AiVerdictBadge({ verdict }: { verdict: string }) {
  const s = VERDICT_STYLE[verdict] ?? VERDICT_STYLE['needs-manual']
  return (
    <span
      className="badge"
      style={{ background: `${s.color}18`, color: s.color, border: `1px solid ${s.color}55`, fontSize: 9 }}
    >
      {s.label}
    </span>
  )
}
