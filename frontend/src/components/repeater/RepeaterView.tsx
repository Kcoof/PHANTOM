import { useEffect } from 'react'
import { Play, Plus, X } from 'lucide-react'
import { useRepeaterStore } from '../../stores/repeaterStore'
import { RequestEditor } from './RequestEditor'
import { ResponseViewer } from './ResponseViewer'
import { SplitPane } from '../shared/SplitPane'

export function RepeaterView() {
  const { tabs, activeTabId, load, newTab, closeTab, setActive, send, sending, rawEdits, setRaw, rawOf, lastResult, loaded } =
    useRepeaterStore()

  useEffect(() => {
    if (!loaded) void load()
  }, [loaded, load])

  // Ctrl+Enter sends the active tab (FR-018)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault()
        if (activeTabId != null) void send(activeTabId)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [activeTabId, send])

  const active = tabs.find((t) => t.id === activeTabId) ?? null

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* tab strip */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          padding: '4px 6px',
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border-primary)',
          overflowX: 'auto',
        }}
      >
        {tabs.map((t) => (
          <div
            key={t.id}
            onClick={() => setActive(t.id)}
            className="fade-in"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
              cursor: 'pointer',
              fontSize: 11.5,
              background: t.id === activeTabId ? 'var(--bg-active)' : 'var(--bg-tertiary)',
              color: t.id === activeTabId ? 'var(--text-primary)' : 'var(--text-secondary)',
              border: '1px solid',
              borderColor: t.id === activeTabId ? 'var(--border-active)' : 'var(--border-primary)',
              maxWidth: 240,
              whiteSpace: 'nowrap',
            }}
          >
            <span className={`method-${t.method}`} style={{ fontWeight: 600 }}>{t.method}</span>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.name}</span>
            {t.last_response_status != null && (
              <span className={`status-${Math.floor(t.last_response_status / 100)}xx`}>{t.last_response_status}</span>
            )}
            <X
              size={11}
              style={{ flexShrink: 0 }}
              onClick={(e) => {
                e.stopPropagation()
                void closeTab(t.id)
              }}
            />
          </div>
        ))}
        <button className="btn ghost sm" title="New tab" onClick={() => void newTab()}>
          <Plus size={13} />
        </button>
      </div>

      {active ? (
        <div style={{ flex: 1, minHeight: 0 }}>
          <SplitPane
            initial={55}
            min={25}
            max={75}
            left={
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-primary)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 10px', borderBottom: '1px solid var(--border-primary)' }}>
                  <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)' }}>REQUEST</span>
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-muted)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {active.url}
                  </span>
                  <button className="btn sm primary" disabled={sending} onClick={() => void send(active.id)} title="Ctrl+Enter">
                    <Play size={11} />
                    {sending ? 'Sending…' : 'Send'}
                  </button>
                </div>
                <div style={{ flex: 1, minHeight: 0 }}>
                  <RequestEditor
                    value={rawEdits[active.id] ?? rawOf(active)}
                    onChange={(v) => setRaw(active.id, v)}
                  />
                </div>
              </div>
            }
            right={
              <div style={{ height: '100%', borderLeft: '1px solid var(--border-primary)' }}>
                <ResponseViewer result={lastResult[active.id] ?? null} />
              </div>
            }
          />
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, color: 'var(--text-muted)' }}>
          <div>No repeater tabs.</div>
          <div style={{ fontSize: 11 }}>Right-click a request in Proxy → “Send to Repeater”, or create a tab:</div>
          <button className="btn primary" onClick={() => void newTab()}>
            <Plus size={13} /> New tab
          </button>
        </div>
      )}
    </div>
  )
}
