import { useEffect } from 'react'
import { Pause, Play, Trash2 } from 'lucide-react'
import { useProxyStore } from '../../stores/proxyStore'
import { FilterBar } from './FilterBar'
import { RequestTable } from './RequestTable'
import { RequestDetail } from './RequestDetail'
import { InterceptPanel } from './InterceptPanel'
import { SplitPane } from '../shared/SplitPane'

export function ProxyView() {
  const refresh = useProxyStore((s) => s.refreshRequests)
  const refreshStatus = useProxyStore((s) => s.refreshStatus)
  const toggleIntercept = useProxyStore((s) => s.toggleIntercept)
  const interceptEnabled = useProxyStore((s) => s.interceptEnabled)
  const clearHistory = useProxyStore((s) => s.clearHistory)

  useEffect(() => {
    void refresh()
    void refreshStatus()
    // Ctrl+Shift+I toggles intercept (Constitution IV / FR-018)
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'i') {
        e.preventDefault()
        void toggleIntercept()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [refresh, refreshStatus, toggleIntercept])

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          borderBottom: '1px solid var(--border-primary)',
          background: 'var(--bg-secondary)',
        }}
      >
        <button
          className={`btn sm ${interceptEnabled ? 'primary' : ''}`}
          style={{ margin: '6px 0 6px 10px' }}
          onClick={() => void toggleIntercept()}
          title="Ctrl+Shift+I"
        >
          {interceptEnabled ? <Pause size={12} /> : <Play size={12} />}
          Intercept: {interceptEnabled ? 'ON' : 'OFF'}
        </button>
        <div style={{ flex: 1 }} />
        <button className="btn ghost sm" style={{ margin: '6px 0' }} onClick={() => void clearHistory()} title="Clear all history">
          <Trash2 size={12} />
          Clear
        </button>
      </div>
      <InterceptPanel />
      <div style={{ borderBottom: '1px solid var(--border-primary)' }}>
        <FilterBar />
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <SplitPane
          initial={55}
          min={25}
          max={75}
          left={
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-primary)' }}>
              <RequestTable />
            </div>
          }
          right={
            <div style={{ height: '100%', borderLeft: '1px solid var(--border-primary)' }}>
              <RequestDetail />
            </div>
          }
        />
      </div>
    </div>
  )
}
