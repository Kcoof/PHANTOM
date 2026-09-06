import { useEffect, useRef, useState } from 'react'
import { Eraser, Filter, RotateCcw } from 'lucide-react'
import { useProxyStore } from '../../stores/proxyStore'

const METHODS = ['', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH']
const STATUSES = ['', '200', '301', '302', '400', '401', '403', '404', '500']

const HIDE_TOGGLES: Array<{ key: 'hideJs' | 'hideCss' | 'hideImages' | 'hideFonts' | 'hideMedia'; label: string }> = [
  { key: 'hideJs', label: 'Hide JavaScript' },
  { key: 'hideCss', label: 'Hide CSS' },
  { key: 'hideImages', label: 'Hide images & favicons' },
  { key: 'hideFonts', label: 'Hide fonts' },
  { key: 'hideMedia', label: 'Hide media' },
]

export function FilterBar() {
  const filters = useProxyStore((s) => s.filters)
  const setFilters = useProxyStore((s) => s.setFilters)
  const visibility = useProxyStore((s) => s.visibility)
  const setVisibility = useProxyStore((s) => s.setVisibility)
  const resetVisibility = useProxyStore((s) => s.resetVisibility)
  const hiddenCount = useProxyStore((s) => s.hiddenCount)
  const total = useProxyStore((s) => s.requests.length)

  const [open, setOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (!panelRef.current?.contains(e.target as Node)) setOpen(false)
    }
    window.addEventListener('mousedown', close)
    return () => window.removeEventListener('mousedown', close)
  }, [open])

  const activeVisual =
    Object.values(HIDE_TOGGLES).filter(({ key }) => visibility[key]).length +
    (visibility.onlyInScope ? 1 : 0) +
    (visibility.onlyParameterized ? 1 : 0) +
    (visibility.customHiddenExts.trim() ? 1 : 0)

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '8px 10px', position: 'relative' }}>
      <div style={{ position: 'relative', flex: 1 }}>
        <input
          className="input"
          placeholder="Search URL, host, path…"
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value })}
          style={{ width: '100%' }}
        />
      </div>
      <select
        className="input"
        value={filters.method}
        onChange={(e) => setFilters({ method: e.target.value })}
        style={{ width: 95 }}
      >
        {METHODS.map((m) => (
          <option key={m} value={m}>{m || 'Any method'}</option>
        ))}
      </select>
      <select
        className="input"
        value={filters.status}
        onChange={(e) => setFilters({ status: e.target.value })}
        style={{ width: 95 }}
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>{s ? `${s} only` : 'Any status'}</option>
        ))}
      </select>
      <input
        className="input"
        placeholder="Host contains…"
        value={filters.host}
        onChange={(e) => setFilters({ host: e.target.value })}
        style={{ width: 160 }}
      />

      {/* Burp-style filter dropdown */}
      <div ref={panelRef} style={{ position: 'relative' }}>
        <button
          className={`btn sm ${activeVisual > 0 ? 'primary' : ''}`}
          onClick={() => setOpen((o) => !o)}
          title="Display filters"
        >
          <Filter size={12} />
          Filters{activeVisual > 0 ? ` (${activeVisual})` : ''}
        </button>
        {open && (
          <div
            className="fade-in"
            style={{
              position: 'absolute',
              top: '110%',
              right: 0,
              zIndex: 300,
              width: 300,
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-active)',
              borderRadius: 'var(--radius-md)',
              padding: 12,
              boxShadow: '0 10px 30px rgba(0,0,0,0.55)',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)' }}>
              FILTER BY REQUEST TYPE
            </div>
            {HIDE_TOGGLES.map(({ key, label }) => (
              <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
                <input type="checkbox" checked={visibility[key]} onChange={(e) => setVisibility({ [key]: e.target.checked })} />
                {label}
              </label>
            ))}
            <div style={{ height: 1, background: 'var(--border-primary)' }} />
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={visibility.onlyInScope}
                onChange={(e) => setVisibility({ onlyInScope: e.target.checked })}
              />
              Show only in-scope items
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={visibility.onlyParameterized}
                onChange={(e) => setVisibility({ onlyParameterized: e.target.checked })}
              />
              Show only parameterized requests
            </label>
            <div style={{ height: 1, background: 'var(--border-primary)' }} />
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)' }}>
              HIDE BY FILE EXTENSION
            </div>
            <input
              className="input mono"
              placeholder="e.g. json, svg, wasm"
              value={visibility.customHiddenExts}
              onChange={(e) => setVisibility({ customHiddenExts: e.target.value })}
              style={{ fontSize: 11 }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', flex: 1 }}>
                {hiddenCount > 0 ? `${hiddenCount} of ${total} hidden by filters` : 'nothing hidden'}
              </span>
              <button className="btn ghost sm" onClick={() => resetVisibility()} title="Reset filters">
                <RotateCcw size={11} /> Reset
              </button>
            </div>
          </div>
        )}
      </div>

      <button
        className="btn ghost sm"
        title="Clear search filters"
        onClick={() => setFilters({ search: '', method: '', status: '', host: '' })}
      >
        <Eraser size={13} />
      </button>
    </div>
  )
}
