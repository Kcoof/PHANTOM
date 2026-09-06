import { useState } from 'react'
import { Search as SearchIcon } from 'lucide-react'
import toast from 'react-hot-toast'
import { searchService } from '../../services/intruderService'
import { apiError } from '../../services/api'
import { useProxyStore } from '../../stores/proxyStore'
import type { SearchResult } from '../../types/intruder'
import { methodClass, statusClass } from '../../utils/formatters'

export function SearchView() {
  const [q, setQ] = useState('')
  const [regex, setRegex] = useState(false)
  const [side, setSide] = useState<'request' | 'response' | 'both'>('both')
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [busy, setBusy] = useState(false)

  const run = async () => {
    if (!q.trim()) return
    setBusy(true)
    try {
      setResults(await searchService.search(q, regex, side))
    } catch (err) {
      toast.error(apiError(err))
    } finally {
      setBusy(false)
    }
  }

  const openInProxy = async (id: number) => {
    await useProxyStore.getState().selectRequest(id)
    window.location.hash = '#/proxy'
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 14, gap: 10 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <SearchIcon size={15} color="var(--accent-primary)" />
        <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: 0.5 }}>Global search</span>
        <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>across every captured request & response (last 5,000)</span>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          className="input mono"
          placeholder={regex ? 'regex e.g. api[_-]?key\\s*[:=]' : 'text to find, e.g. api_key'}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void run()}
          style={{ flex: 1, fontSize: 12 }}
        />
        <select className="input" value={side} onChange={(e) => setSide(e.target.value as typeof side)} style={{ width: 120 }}>
          <option value="both">Both sides</option>
          <option value="request">Requests</option>
          <option value="response">Responses</option>
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, cursor: 'pointer' }}>
          <input type="checkbox" checked={regex} onChange={(e) => setRegex(e.target.checked)} />
          regex
        </label>
        <button className="btn primary" disabled={busy || !q.trim()} onClick={() => void run()}>
          {busy ? 'Searching…' : 'Search'}
        </button>
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {results && results.length === 0 && (
          <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 12 }}>No matches in captured history.</div>
        )}
        {results?.map((r) => (
          <div
            key={r.id}
            className="fade-in"
            onClick={() => void openInProxy(r.id)}
            style={{
              padding: '8px 10px',
              borderBottom: '1px solid var(--border-primary)',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              gap: 3,
            }}
          >
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 11 }}>
              <span className={methodClass(r.method)} style={{ fontWeight: 700 }}>{r.method}</span>
              <span className="mono" style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>
                {r.url}
              </span>
              <span className={statusClass(r.status_code)}>{r.status_code ?? '—'}</span>
              <span style={{ color: 'var(--accent-secondary)', fontSize: 10 }}>#{r.id} · {r.where}</span>
            </div>
            <div className="mono" style={{ fontSize: 11, color: 'var(--text-primary)', background: 'var(--bg-secondary)', borderRadius: 4, padding: '4px 8px', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
              {r.snippet}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
