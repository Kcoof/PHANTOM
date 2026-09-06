import { useState } from 'react'
import { Copy } from 'lucide-react'
import toast from 'react-hot-toast'
import type { SendResult } from '../../types/repeater'
import { copyToClipboard, statusClass } from '../../utils/formatters'

type Tab = 'raw' | 'headers' | 'body' | 'hex'

export function ResponseViewer({ result }: { result: SendResult | null }) {
  const [tab, setTab] = useState<Tab>('raw')

  if (!result)
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        Send a request to see the response
      </div>
    )

  const raw = `HTTP ${result.status}\n${Object.entries(result.headers)
    .map(([k, v]) => `${k}: ${v}`)
    .join('\n')}\n\n${result.body}`

  const hex = Array.from(new TextEncoder().encode(result.body.slice(0, 4096)))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join(' ')

  const content =
    tab === 'raw' ? raw
    : tab === 'headers' ? Object.entries(result.headers).map(([k, v]) => `${k}: ${v}`).join('\n')
    : tab === 'body' ? result.body
    : hex

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
      <div style={{ display: 'flex', gap: 2, borderBottom: '1px solid var(--border-primary)' }}>
        {(['raw', 'headers', 'body', 'hex'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
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
      </div>
      <pre className="mono" style={{ flex: 1, overflow: 'auto', padding: 10, fontSize: 11.5, lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
        {content}
      </pre>
    </div>
  )
}
