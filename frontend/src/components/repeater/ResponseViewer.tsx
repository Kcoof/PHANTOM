import { useEffect, useMemo, useRef, useState } from 'react'
import { CaseSensitive, ChevronDown, ChevronUp, Copy, Search, X } from 'lucide-react'
import toast from 'react-hot-toast'
import type { SendResult } from '../../types/repeater'
import { copyToClipboard, statusClass } from '../../utils/formatters'

type Tab = 'raw' | 'headers' | 'body' | 'hex'

const MAX_HIGHLIGHT_MATCHES = 5000

export function ResponseViewer({ result }: { result: SendResult | null }) {
  const [tab, setTab] = useState<Tab>('raw')
  const [query, setQuery] = useState('')
  const [caseSensitive, setCaseSensitive] = useState(false)
  const [activeMatch, setActiveMatch] = useState(0)
  const searchRef = useRef<HTMLInputElement | null>(null)
  const bodyRef = useRef<HTMLPreElement | null>(null)

  useEffect(() => {
    setQuery('')
    setActiveMatch(0)
  }, [result])

  const content = useMemo(() => {
    if (!result) return ''
    const raw = `HTTP ${result.status}\n${Object.entries(result.headers)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\n')}\n\n${result.body}`
    if (tab === 'raw') return raw
    if (tab === 'headers') return Object.entries(result.headers).map(([k, v]) => `${k}: ${v}`).join('\n')
    if (tab === 'body') return result.body
    return Array.from(new TextEncoder().encode(result.body.slice(0, 4096)))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join(' ')
  }, [result, tab])

  const { segments, matchCount } = useMemo(
    () => highlight(content, query, activeMatch, caseSensitive),
    [content, query, activeMatch, caseSensitive],
  )

  const step = (dir: 1 | -1) => {
    if (matchCount === 0) return
    setActiveMatch((i) => (i + dir + matchCount) % matchCount)
  }

  // auto-scroll the active match into view
  useEffect(() => {
    if (!query || matchCount === 0) return
    bodyRef.current
      ?.querySelector(`[data-match="${activeMatch}"]`)
      ?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [activeMatch, query, matchCount])

  // Ctrl+F focuses the response search while the Repeater is mounted
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
        e.preventDefault()
        searchRef.current?.focus()
        searchRef.current?.select()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  if (!result)
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        Send a request to see the response
      </div>
    )

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 8px', height: 28, borderBottom: '1px solid var(--border-primary)' }}>
        <span className={statusClass(result.status)} style={{ fontWeight: 700 }}>
          {result.status}
        </span>
        <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>{result.time_ms} ms · {result.size} B</span>
        <div style={{ flex: 1 }} />
        <button className="btn ghost sm" onClick={() => { copyToClipboard(content); toast.success('Copied') }}>
          <Copy size={11} />
        </button>
      </div>
      <div style={{ display: 'flex', gap: 2, borderBottom: '1px solid var(--border-primary)', alignItems: 'center' }}>
        {(['raw', 'headers', 'body', 'hex'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setActiveMatch(0) }}
            style={{
              padding: '4px 12px',
              background: 'transparent',
              border: 'none',
              borderBottom: tab === t ? '2px solid var(--accent-secondary)' : '2px solid transparent',
              color: tab === t ? 'var(--text-primary)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: 11,
            }}
          >
            {t}
          </button>
        ))}
        {/* response search */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, padding: '2px 6px' }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={11} style={{ position: 'absolute', left: 6, color: 'var(--text-muted)', pointerEvents: 'none' }} />
            <input
              ref={searchRef}
              className="input"
              placeholder="Find in response (Ctrl+F)"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setActiveMatch(0) }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') { e.preventDefault(); step(e.shiftKey ? -1 : 1) }
                if (e.key === 'Escape') { setQuery(''); e.currentTarget.blur() }
              }}
              style={{ width: 190, paddingLeft: 22, paddingRight: query ? 56 : 8, fontSize: 10.5, paddingBlock: 3 }}
            />
            {query && (
              <span style={{ position: 'absolute', right: 30, fontSize: 10, color: 'var(--text-secondary)', pointerEvents: 'none' }}>
                {matchCount ? `${activeMatch + 1}/${matchCount}` : '0'}
              </span>
            )}
            {query && (
              <button
                className="btn ghost sm"
                style={{ position: 'absolute', right: 2, padding: 1 }}
                onClick={() => setQuery('')}
                title="Clear (Esc)"
              >
                <X size={10} />
              </button>
            )}
          </div>
          <button
            className={`btn ghost sm ${caseSensitive ? 'primary' : ''}`}
            style={{ padding: 2 }}
            title="Match case"
            onClick={() => { setCaseSensitive((v) => !v); setActiveMatch(0) }}
          >
            <CaseSensitive size={12} />
          </button>
          <button className="btn ghost sm" style={{ padding: 2 }} title="Previous match (Shift+Enter)" onClick={() => step(-1)} disabled={!matchCount}>
            <ChevronUp size={12} />
          </button>
          <button className="btn ghost sm" style={{ padding: 2 }} title="Next match (Enter)" onClick={() => step(1)} disabled={!matchCount}>
            <ChevronDown size={12} />
          </button>
        </div>
      </div>
      <pre
        ref={bodyRef}
        className="mono"
        style={{ flex: 1, overflow: 'auto', padding: 10, fontSize: 11.5, lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}
      >
        {segments}
      </pre>
    </div>
  )
}

/** Split `text` into strings + styled <mark> spans for `query` (capped for perf). */
function highlight(
  text: string,
  query: string,
  activeMatch: number,
  caseSensitive: boolean,
): { segments: React.ReactNode[]; matchCount: number } {
  if (!query || !text) return { segments: [text], matchCount: 0 }
  const hay = caseSensitive ? text : text.toLowerCase()
  const needle = caseSensitive ? query : query.toLowerCase()
  const segments: React.ReactNode[] = []
  let pos = 0
  let idx = hay.indexOf(needle)
  let matchIdx = 0
  while (idx !== -1 && matchIdx < MAX_HIGHLIGHT_MATCHES) {
    if (idx > pos) segments.push(text.slice(pos, idx))
    segments.push(
      <mark
        key={`m${matchIdx}`}
        data-match={matchIdx}
        style={{
          background: matchIdx === activeMatch ? 'var(--accent-primary)' : 'rgba(108, 92, 231, 0.30)',
          color: matchIdx === activeMatch ? '#fff' : 'inherit',
          borderRadius: 2,
          padding: '0 1px',
          fontWeight: matchIdx === activeMatch ? 600 : 400,
        }}
      >
        {text.slice(idx, idx + needle.length)}
      </mark>,
    )
    pos = idx + needle.length
    matchIdx += 1
    idx = hay.indexOf(needle, pos)
  }
  if (pos < text.length) segments.push(text.slice(pos))
  let count = matchIdx
  if (matchIdx >= MAX_HIGHLIGHT_MATCHES) {
    let scan = hay.indexOf(needle, pos)
    while (scan !== -1) { count += 1; scan = hay.indexOf(needle, scan + needle.length) }
  }
  return { segments, matchCount: count }
}
