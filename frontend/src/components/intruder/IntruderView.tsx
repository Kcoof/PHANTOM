import { useEffect, useRef, useState } from 'react'
import type { editor } from 'monaco-editor'
import { Crosshair, Play, Square, Wand2 } from 'lucide-react'
import toast from 'react-hot-toast'
import Editor from '@monaco-editor/react'
import { useIntruderStore } from '../../stores/intruderStore'
import { intruderService } from '../../services/intruderService'
import { apiError } from '../../services/api'
import { formatMs, statusClass } from '../../utils/formatters'
import type { IntruderResult } from '../../types/intruder'

export function IntruderView() {
  const store = useIntruderStore()
  const [wordlists, setWordlists] = useState<Record<string, number>>({})
  const [showOnlyDeviations, setShowOnlyDeviations] = useState(false)
  const [detail, setDetail] = useState<IntruderResult | null>(null)
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)

  useEffect(() => {
    void store.load()
    void intruderService.wordlists().then(setWordlists).catch(() => undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const wrapSelection = () => {
    const ed = editorRef.current
    if (!ed) return
    const sel = ed.getSelection()
    if (!sel || sel.isEmpty()) {
      toast('Select text in the request first, then press Add §', { icon: '✋' })
      return
    }
    ed.executeEdits('phantom', [
      { range: sel, text: `§${ed.getModel()?.getValueInRange(sel) ?? ''}§`, forceMoveMarkers: true },
    ])
  }

  const loadWordlist = async (name: string) => {
    if (!name) return
    try {
      const items = await intruderService.wordlistItems(name)
      store.setPayloads(items.join('\n'))
      toast.success(`Loaded ${items.length} payloads from ${name}`)
    } catch (err) {
      toast.error(apiError(err))
    }
  }

  const active = store.attacks.find((a) => a.id === store.activeAttackId) ?? null
  const running = active?.status === 'running'
  const progress = store.progress[active?.id ?? '']
  const allResults = store.results[active?.id ?? ''] ?? []
  const baseline = allResults.find((r) => r.is_baseline)
  const results = showOnlyDeviations
    ? allResults.filter((r) => r.is_baseline || r.status !== baseline?.status || r.length !== baseline?.length)
    : allResults

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '8px 12px',
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border-primary)',
        }}
      >
        <Crosshair size={14} color="var(--accent-primary)" />
        <span style={{ fontWeight: 700, letterSpacing: 0.5 }}>Intruder</span>
        <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>
          mark §positions§ → payloads → Launch · throttled · authorized targets only
        </span>
        <div style={{ flex: 1 }} />
        {active && (
          <select className="input" value={active.id} onChange={(e) => void store.selectAttack(e.target.value)} style={{ width: 200 }}>
            {store.attacks.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} · {a.status} ({a.done}/{a.total})
              </option>
            ))}
          </select>
        )}
      </div>

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* config column */}
        <div style={{ width: 460, flex: '0 0 auto', borderRight: '1px solid var(--border-primary)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderBottom: '1px solid var(--border-primary)' }}>
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)' }}>REQUEST TEMPLATE</span>
            <button className="btn ghost sm" onClick={wrapSelection} title="Wrap the selected text as a payload position">
              <Wand2 size={11} /> Add §
            </button>
          </div>
          <div style={{ height: 260, flexShrink: 0, borderBottom: '1px solid var(--border-primary)' }}>
            <Editor
              height="100%"
              defaultLanguage="ini"
              value={store.draft}
              onChange={(v) => store.setDraft(v ?? '')}
              onMount={(ed) => (editorRef.current = ed)}
              theme="vs-dark"
              options={{
                fontFamily: 'JetBrains Mono, Consolas, monospace',
                fontSize: 12,
                minimap: { enabled: false },
                lineNumbers: 'off',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                padding: { top: 8 },
                renderLineHighlight: 'none',
                automaticLayout: true,
              }}
            />
          </div>
          <div style={{ padding: 8, display: 'flex', flexDirection: 'column', gap: 6, overflow: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)' }}>PAYLOADS</span>
              <select className="input" style={{ width: 170, fontSize: 10.5 }} defaultValue="" onChange={(e) => void loadWordlist(e.target.value)}>
                <option value="">Load wordlist…</option>
                {Object.entries(wordlists).map(([name, n]) => (
                  <option key={name} value={name}>{name} ({n})</option>
                ))}
              </select>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {store.payloads.split('\n').filter(Boolean).length} loaded
              </span>
            </div>
            <textarea
              className="input mono"
              placeholder={'one payload per line\nadmin\ntest\nroot'}
              value={store.payloads}
              onChange={(e) => store.setPayloads(e.target.value)}
              rows={5}
              style={{ fontSize: 11, resize: 'vertical' }}
            />
            <input
              className="input mono"
              placeholder="grep patterns (regex, comma-separated) — optional"
              value={store.grep}
              onChange={(e) => store.setGrep(e.target.value)}
              style={{ fontSize: 11 }}
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn primary" disabled={store.starting} onClick={() => void store.launch()}>
                <Play size={12} /> {store.starting ? 'Launching…' : 'Launch attack'}
              </button>
              {running && (
                <button className="btn danger" onClick={() => void store.stop(active.id)}>
                  <Square size={12} /> Stop
                </button>
              )}
            </div>
          </div>
        </div>

        {/* results column */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 10px', borderBottom: '1px solid var(--border-primary)' }}>
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)' }}>RESULTS</span>
            {active && (
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                {progress?.done ?? active.done}/{progress?.total ?? active.total}
                {baseline ? ` · baseline ${baseline.status}/${baseline.length}B` : ''}
                {progress?.status && progress.status !== 'running' ? ` · ${progress.status}` : ''}
              </span>
            )}
            <div style={{ flex: 1 }} />
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, cursor: 'pointer' }}>
              <input type="checkbox" checked={showOnlyDeviations} onChange={(e) => setShowOnlyDeviations(e.target.checked)} />
              only deviations
            </label>
          </div>
          {running && (
            <div style={{ height: 3, background: 'var(--bg-tertiary)' }}>
              <div
                style={{
                  height: '100%',
                  width: `${Math.round(((progress?.done ?? active?.done ?? 0) / Math.max(progress?.total ?? active?.total ?? 1, 1)) * 100)}%`,
                  background: 'var(--accent-primary)',
                  transition: 'width 250ms ease',
                }}
              />
            </div>
          )}
          <div style={{ flex: 1, overflow: 'auto' }}>
            <table className="mono" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5 }}>
              <thead style={{ position: 'sticky', top: 0 }}>
                <tr style={{ background: 'var(--bg-tertiary)' }}>
                  {['#', 'Payload', 'Status', 'Length', 'Time', 'Grep', 'Δ'].map((h) => (
                    <th key={h} style={{ textAlign: 'left', padding: '5px 8px', color: 'var(--text-secondary)', fontSize: 10, fontWeight: 600, borderBottom: '1px solid var(--border-primary)' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((r) => {
                  const deviates =
                    !r.is_baseline &&
                    baseline != null &&
                    (r.status !== baseline.status || r.length !== baseline.length)
                  return (
                    <tr
                      key={r.id ?? `${r.attack_id}-${r.idx}`}
                      onClick={() => void intruderService.resultDetail(r.id).then(setDetail).catch(() => undefined)}
                      style={{
                        cursor: 'pointer',
                        background: r.is_baseline
                          ? 'var(--bg-active)'
                          : deviates
                            ? 'rgba(255,56,56,0.10)'
                            : 'transparent',
                        borderBottom: '1px solid var(--border-primary)',
                      }}
                    >
                      <td style={{ padding: '3px 8px', color: 'var(--text-muted)' }}>{r.is_baseline ? '◦' : r.idx}</td>
                      <td style={{ padding: '3px 8px', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.payload}</td>
                      <td style={{ padding: '3px 8px' }}>
                        <span className={statusClass(r.status)} style={{ fontWeight: 600 }}>{r.status || 'ERR'}</span>
                      </td>
                      <td style={{ padding: '3px 8px', color: deviates ? 'var(--severity-critical)' : 'var(--text-secondary)' }}>{r.length}</td>
                      <td style={{ padding: '3px 8px', color: 'var(--text-secondary)' }}>{formatMs(r.time_ms)}</td>
                      <td style={{ padding: '3px 8px', color: 'var(--severity-low)' }}>{r.matched?.length ? `✓ ${r.matched.length}` : ''}</td>
                      <td style={{ padding: '3px 8px', color: 'var(--severity-critical)' }}>{deviates ? 'Δ' : ''}</td>
                    </tr>
                  )
                })}
                {results.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                      {store.draft
                        ? 'No results yet — mark positions and Launch.'
                        : 'Send a request here from Proxy/Repeater (right-click → Send to Intruder), or paste one and mark §positions§.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {detail && (
            <div style={{ height: 180, borderTop: '1px solid var(--border-primary)', display: 'flex', flexDirection: 'column', background: 'var(--bg-secondary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 10px', borderBottom: '1px solid var(--border-primary)' }}>
                <span className={statusClass(detail.status)} style={{ fontWeight: 700 }}>{detail.status}</span>
                <span className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  payload: {detail.payload} → {detail.url}
                </span>
                <button className="btn ghost sm" onClick={() => setDetail(null)}>✕</button>
              </div>
              <pre className="mono" style={{ flex: 1, overflow: 'auto', padding: 8, fontSize: 11, whiteSpace: 'pre-wrap', margin: 0 }}>
                {detail.response_body || '(empty)'}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
