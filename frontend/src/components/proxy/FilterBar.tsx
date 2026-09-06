import { Eraser, Search } from 'lucide-react'
import { useProxyStore } from '../../stores/proxyStore'

const METHODS = ['', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH']
const STATUSES = ['', '200', '301', '302', '400', '401', '403', '404', '500']

export function FilterBar() {
  const filters = useProxyStore((s) => s.filters)
  const setFilters = useProxyStore((s) => s.setFilters)

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '8px 10px' }}>
      <div style={{ position: 'relative', flex: 1 }}>
        <Search
          size={13}
          style={{ position: 'absolute', left: 8, top: 7, color: 'var(--text-muted)' }}
        />
        <input
          className="input"
          placeholder="Search URL, host, path…"
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value })}
          style={{ width: '100%', paddingLeft: 26 }}
        />
      </div>
      <select
        className="input"
        value={filters.method}
        onChange={(e) => setFilters({ method: e.target.value })}
        style={{ width: 100 }}
      >
        {METHODS.map((m) => (
          <option key={m} value={m}>{m || 'Any method'}</option>
        ))}
      </select>
      <select
        className="input"
        value={filters.status}
        onChange={(e) => setFilters({ status: e.target.value })}
        style={{ width: 100 }}
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
        style={{ width: 180 }}
      />
      <button
        className="btn ghost sm"
        title="Clear filters"
        onClick={() => setFilters({ search: '', method: '', status: '', host: '' })}
      >
        <Eraser size={13} />
      </button>
    </div>
  )
}
