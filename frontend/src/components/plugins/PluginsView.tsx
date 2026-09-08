import { useEffect, useState } from 'react'
import { ArrowRight, Blocks, Play, Square } from 'lucide-react'
import toast from 'react-hot-toast'
import { usePluginStore } from '../../stores/pluginStore'
import { historyService } from '../../services/proxyService'
import { statusClass } from '../../utils/formatters'

export function PluginsView() {
  const store = usePluginStore()
  const [pluginId, setPluginId] = useState('param-miner')
  const [target, setTarget] = useState('')
  const [targets, setTargets] = useState<Array<{ id: number; method: string; url: string; host: string; path: string }>>([])
  const [optionValues, setOptionValues] = useState<Record<string, string | number>>({})

  useEffect(() => {
    void store.load()
    void historyService.list({ limit: 100 }).then((p) => setTargets(p.items)).catch(() => undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const plugin = store.plugins.find((p) => p.id === pluginId)
  const activeRun = store.runs.find((r) => r.id === store.activeRunId) ?? null
  const running = activeRun?.status === 'running'
  const progress = store.progress[activeRun?.id ?? '']
  const rows = store.results[activeRun?.id ?? ''] ?? []
  const params = rows.filter((r) => r.kind === 'param')
  const infos = rows.filter((r) => r.kind === 'info' || r.kind === 'summary')

  const launch = () => {
    if (!target) {
      toast('Pick a captured request to run on', { icon: '🎯' })
      return
    }
    void store.start(pluginId, { kind: 'request', history_id: Number(target) }, optionValues)
  }

  const toRepeater = async (row: { data: Record<string, unknown> }) => {
    const id = Number(activeRun?.target)
    if (!activeRun || !Number.isFinite(id) || id <= 0) {
      toast('Run started from a raw request — open it from Proxy history instead', { icon: 'ℹ️' })
      return
    }
    try {
      const { repeater_tab_id } = await historyService.sendToRepeater(id)
      toast.success(`Repeater tab #${repeater_tab_id} — add ?${row.data.name}= to probe`)
    } catch {
      toast.error('Could not open in Repeater')
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-primary)' }}>
        <Blocks size={14} color="var(--accent-primary)" />
        <span style={{ fontWeight: 700, letterSpacing: 0.5 }}>Plugins</span>
        <select className="input" value={pluginId} onChange={(e) => { setPluginId(e.target.value); setOptionValues({}) }} style={{ width: 190 }}>
          {store.plugins.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <select className="input" value={target} onChange={(e) => setTarget(e.target.value)} style={{ width: 320 }}>
          <option value="">target: pick a captured request…</option>
          {targets.map((t) => (
            <option key={t.id} value={t.id}>#{t.id} {t.method} {t.host}{t.path.slice(0, 36)}</option>
          ))}
        </select>
        {plugin?.parameters.map((p) => (
          p.type === 'select' ? (
            <select key={p.key} className="input" value={String(optionValues[p.key] ?? p.default ?? '')} onChange={(e) => setOptionValues((v) => ({ ...v, [p.key]: e.target.value }))} style={{ width: 140 }}>
              {(p.options ?? []).map((o) => <option key={o} value={o}>{p.key}: {o}</option>)}
            </select>
          ) : (
            <input key={p.key} className="input" type="number" placeholder={`${p.key}: ${p.default}`} value={String(optionValues[p.key] ?? '')} onChange={(e) => setOptionValues((v) => ({ ...v, [p.key]: Number(e.target.value) }))} style={{ width: 120 }} />
          )
        ))}
        <button className="btn primary sm" onClick={launch} disabled={!plugin}>
          <Play size={11} /> Run
        </button>
        {running && (
          <button className="btn danger sm" onClick={() => void store.stop(activeRun!.id)}>
            <Square size={11} /> Stop
          </button>
        )}
        <div style={{ flex: 1 }} />
        <select className="input" value={store.activeRunId ?? ''} onChange={(e) => void store.selectRun(e.target.value)} style={{ width: 210 }}>
          {store.runs.map((r) => (
            <option key={r.id} value={r.id}>{r.plugin_id} · {r.status} · {r.target.slice(0, 24)}</option>
          ))}
        </select>
      </div>

      {plugin && (
        <div style={{ padding: '6px 12px', borderBottom: '1px solid var(--border-primary)', fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          {plugin.description}
        </div>
      )}

      {running && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 12px', background: 'var(--bg-tertiary)' }}>
          <span className="pulse-dot" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--accent-primary)' }} />
          <div style={{ flex: 1, height: 5, background: 'var(--bg-primary)', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${Math.round(((progress?.done ?? activeRun?.done ?? 0) / Math.max(progress?.total ?? activeRun?.total ?? 1, 1)) * 100)}%`, background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))', transition: 'width 250ms ease' }} />
          </div>
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-secondary)' }}>
            {progress?.done ?? activeRun?.done ?? 0}/{progress?.total ?? activeRun?.total ?? '?'} probes
          </span>
        </div>
      )}

      <div style={{ flex: 1, overflow: 'auto' }}>
        {infos.length > 0 && (
          <div style={{ padding: '8px 12px', color: 'var(--text-secondary)', fontSize: 11.5, borderBottom: '1px solid var(--border-primary)' }}>
            {infos.map((r, i) => (
              <div key={i}>
                {r.kind === 'summary'
                  ? `✅ ${String(r.data.found ?? '')} hidden parameter(s) found: ${Array.isArray(r.data.names) ? (r.data.names as string[]).join(', ') : ''}`
                  : String(r.data.message ?? '')}
              </div>
            ))}
          </div>
        )}
        {params.length > 0 ? (
          <table className="mono" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5 }}>
            <thead style={{ position: 'sticky', top: 0 }}>
              <tr style={{ background: 'var(--bg-tertiary)' }}>
                {['✓', 'PARAMETER', 'DETECTED VIA', 'EVIDENCE', 'RESPONSE', 'Δ', ''].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '6px 10px', color: 'var(--text-secondary)', fontSize: 10, fontWeight: 600, borderBottom: '1px solid var(--border-primary)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {params.map((r) => {
                const d = r.data as { name: string; detected_via: string; evidence: string; status: number; delta: number }
                return (
                  <tr key={r.id} className="fade-in" style={{ borderBottom: '1px solid var(--border-primary)' }}>
                    <td style={{ padding: '5px 10px', color: 'var(--severity-low)' }}>✓</td>
                    <td style={{ padding: '5px 10px', color: 'var(--severity-low)', fontWeight: 600 }}>{d.name}</td>
                    <td style={{ padding: '5px 10px', color: d.detected_via === 'reflection' ? 'var(--severity-info)' : 'var(--severity-medium)' }}>{d.detected_via}</td>
                    <td style={{ padding: '5px 10px', color: 'var(--text-secondary)', maxWidth: 380, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.evidence}</td>
                    <td style={{ padding: '5px 10px' }}><span className={statusClass(d.status)}>{d.status}</span></td>
                    <td style={{ padding: '5px 10px', color: d.delta ? 'var(--severity-medium)' : 'var(--text-muted)' }}>{d.delta > 0 ? `+${d.delta}` : d.delta || 0} B</td>
                    <td style={{ padding: '3px 8px' }}>
                      <button className="btn ghost sm" title="Open the source request in Repeater to probe" onClick={() => void toRepeater(r)}>
                        <ArrowRight size={11} /> Repeater
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: 28, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.7 }}>
            No parameter discoveries yet.<br />
            <span style={{ fontSize: 11 }}>Right-click a request in Proxy → Plugins ▸ Parameter Miner, or pick a target above and press Run.</span>
          </div>
        )}
        {activeRun?.status === 'failed' && activeRun.error && (
          <div style={{ margin: 12, padding: 10, background: 'rgba(255,56,56,0.08)', border: '1px solid rgba(255,56,56,0.3)', borderRadius: 8, color: 'var(--severity-critical)', fontSize: 11.5 }}>
            {activeRun.error}
          </div>
        )}
      </div>
    </div>
  )
}
