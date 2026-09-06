import { useState } from 'react'
import { ArrowDownToLine, Pencil, XCircle } from 'lucide-react'
import { useProxyStore } from '../../stores/proxyStore'
import { Badge } from '../shared/Badge'

export function InterceptPanel() {
  const queue = useProxyStore((s) => s.interceptQueue)
  const enabled = useProxyStore((s) => s.interceptEnabled)
  const forward = useProxyStore((s) => s.forwardFlow)
  const drop = useProxyStore((s) => s.dropFlow)
  const [editing, setEditing] = useState<string | null>(null)
  const [editText, setEditText] = useState('')

  if (!enabled) return null

  const startEdit = (flowId: string, method: string, url: string, headers: Record<string, string>, body: string | null) => {
    const raw = `${method} ${url.replace(/^https?:\/\/[^/]+/, '')}\n${Object.entries(headers)
      .filter(([k]) => k.toLowerCase() !== 'proxy-connection')
      .map(([k, v]) => `${k}: ${v}`)
      .join('\n')}${body ? `\n\n${body}` : ''}`
    setEditing(flowId)
    setEditText(raw)
  }

  return (
    <div
      className="fade-in"
      style={{
        maxHeight: 260,
        borderBottom: '1px solid var(--border-active)',
        background: 'var(--bg-tertiary)',
        overflow: 'auto',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 10px',
          position: 'sticky',
          top: 0,
          background: 'var(--bg-tertiary)',
          borderBottom: '1px solid var(--border-primary)',
        }}
      >
        <Badge color="var(--severity-high)">INTERCEPT</Badge>
        <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          {queue.length} request{queue.length === 1 ? '' : 's'} held
        </span>
      </div>
      {queue.map((f) => (
        <div
          key={f.flow_id}
          style={{
            padding: '8px 10px',
            borderBottom: '1px solid var(--border-primary)',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className={`method-${f.method}`} style={{ fontWeight: 700, fontSize: 11 }}>
              {f.method}
            </span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {f.url}
            </span>
            <button className="btn sm" title="Edit then forward" onClick={() => startEdit(f.flow_id, f.method, f.url, f.headers, f.body)}>
              <Pencil size={11} />
            </button>
            <button className="btn sm primary" title="Forward" onClick={() => void forward(f.flow_id)}>
              <ArrowDownToLine size={11} />
            </button>
            <button className="btn sm danger" title="Drop" onClick={() => void drop(f.flow_id)}>
              <XCircle size={11} />
            </button>
          </div>
          {editing === f.flow_id && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <textarea
                className="input mono"
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                rows={8}
                style={{ width: '100%', resize: 'vertical', fontSize: 11 }}
              />
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  className="btn sm primary"
                  onClick={() => {
                    void forward(f.flow_id, editText)
                    setEditing(null)
                  }}
                >
                  Forward edited
                </button>
                <button className="btn sm ghost" onClick={() => setEditing(null)}>
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
      {queue.length === 0 && (
        <div style={{ padding: 14, color: 'var(--text-muted)', fontSize: 11 }}>
          Intercept is ON — matching requests will be held here.
        </div>
      )}
    </div>
  )
}
