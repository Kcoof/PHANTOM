import { useState } from 'react'
import { Copy } from 'lucide-react'
import toast from 'react-hot-toast'
import { useProxyStore } from '../../stores/proxyStore'
import { SplitPane } from '../shared/SplitPane'
import { LoadingSpinner } from '../shared/LoadingSpinner'
import { copyToClipboard, methodClass, statusClass } from '../../utils/formatters'

type Tab = 'raw' | 'headers' | 'body'

function TabBar({ tabs, active, onChange }: { tabs: Tab[]; active: Tab; onChange: (t: Tab) => void }) {
  return (
    <div style={{ display: 'flex', gap: 2, borderBottom: '1px solid var(--border-primary)' }}>
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          style={{
            padding: '5px 12px',
            background: 'transparent',
            border: 'none',
            borderBottom: active === t ? '2px solid var(--accent-primary)' : '2px solid transparent',
            color: active === t ? 'var(--text-primary)' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: 11,
            fontWeight: 500,
            textTransform: 'capitalize',
          }}
        >
          {t}
        </button>
      ))}
    </div>
  )
}

function rawHttp(prefix: string, headers: Record<string, string>, body: string | null): string {
  const h = Object.entries(headers || {})
    .map(([k, v]) => `${k}: ${v}`)
    .join('\n')
  return `${prefix}\n${h}\n${body ? `\n${body}` : ''}`
}

export function RequestDetail() {
  const detail = useProxyStore((s) => s.selectedDetail)
  const loading = useProxyStore((s) => s.detailLoading)
  const [reqTab, setReqTab] = useState<Tab>('raw')
  const [respTab, setRespTab] = useState<Tab>('raw')

  if (loading) return <LoadingSpinner label="Loading request…" />
  if (!detail)
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
        }}
      >
        Select a request to inspect
      </div>
    )

  const reqRaw = rawHttp(
    `${detail.method} ${detail.path}${detail.query_string ? `?${detail.query_string}` : ''}`,
    detail.request_headers,
    detail.request_body,
  )
  const respRaw = detail.status_code
    ? rawHttp(`HTTP ${detail.status_code}`, detail.response_headers ?? {}, detail.response_body)
    : '(no response)'

  const pane = (title: string, tabs: Tab[], active: Tab, setActive: (t: Tab) => void, raw: string, headers: Record<string, string> | null, body: string | null) => (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 8px',
          height: 28,
          borderBottom: '1px solid var(--border-primary)',
          gap: 8,
        }}
      >
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)' }}>
          {title}
        </span>
        <button
          className="btn ghost sm"
          title="Copy raw"
          onClick={() => {
            copyToClipboard(raw)
            toast.success(`${title} copied`)
          }}
        >
          <Copy size={11} />
        </button>
      </div>
      <TabBar tabs={tabs} active={active} onChange={setActive} />
      <pre
        className="mono"
        style={{
          flex: 1,
          overflow: 'auto',
          padding: 10,
          fontSize: 11.5,
          lineHeight: 1.55,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
          color: 'var(--text-primary)',
        }}
      >
        {active === 'raw'
          ? raw
          : active === 'headers'
            ? headers
              ? Object.entries(headers)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join('\n')
              : '(none)'
            : body || '(no body)'}
      </pre>
    </div>
  )

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          display: 'flex',
          gap: 10,
          alignItems: 'center',
          padding: '6px 10px',
          borderBottom: '1px solid var(--border-primary)',
          fontSize: 11.5,
        }}
      >
        <span className={methodClass(detail.method)} style={{ fontWeight: 700 }}>
          {detail.method}
        </span>
        <span className="mono" style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {detail.url}
        </span>
        <span className={statusClass(detail.status_code)} style={{ fontWeight: 700, marginLeft: 'auto' }}>
          {detail.status_code ?? '—'}
        </span>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <SplitPane
          left={pane('REQUEST', ['raw', 'headers', 'body'], reqTab, setReqTab, reqRaw, detail.request_headers, detail.request_body)}
          right={pane('RESPONSE', ['raw', 'headers', 'body'], respTab, setRespTab, respRaw, detail.response_headers ?? {}, detail.response_body)}
          initial={50}
          min={20}
          max={80}
        />
      </div>
    </div>
  )
}
