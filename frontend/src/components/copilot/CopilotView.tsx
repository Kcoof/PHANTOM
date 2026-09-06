import { useEffect, useRef, useState } from 'react'
import { Bot, BrainCircuit, Send, User, Zap } from 'lucide-react'
import Markdown from 'react-markdown'
import { useCopilotStore } from '../../stores/copilotStore'
import { Badge } from '../shared/Badge'

export function CopilotView() {
  const store = useCopilotStore()
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    void store.refreshStatus()
    void store.loadHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [store.messages])

  const submit = () => {
    const text = input.trim()
    if (!text) return
    setInput('')
    void store.send(text)
  }

  const available = store.status?.available ?? false

  return (
    <div style={{ height: '100%', display: 'flex' }}>
      {/* chat column */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
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
          <BrainCircuit size={15} color="var(--accent-primary)" />
          <span style={{ fontWeight: 700, letterSpacing: 0.5 }}>PHANTOM AI Copilot</span>
          <Badge
            color={available ? 'var(--severity-low)' : 'var(--severity-medium)'}
            bg={available ? 'rgba(0,184,148,0.1)' : 'rgba(255,193,7,0.1)'}
          >
            {available ? `ONLINE · ${store.status?.model}` : 'OFFLINE'}
          </Badge>
          <div style={{ flex: 1 }} />
          <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>{store.status?.base_url}</span>
        </div>

        {!available && (
          <div style={{ padding: '8px 12px', background: 'rgba(255,193,7,0.07)', borderBottom: '1px solid var(--border-primary)', fontSize: 11.5, color: 'var(--severity-medium)', lineHeight: 1.5 }}>
            {store.status?.detail
              ? `AI runtime unavailable — ${store.status.detail}. Start it with: ollama serve && ollama pull ${store.status.model}. All other modules keep working.`
              : 'Checking AI runtime…'}
          </div>
        )}

        <div ref={scrollRef} style={{ flex: 1, overflow: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {store.messages.length === 0 && (
            <div style={{ color: 'var(--text-muted)', fontSize: 12, textAlign: 'center', marginTop: 40, lineHeight: 1.7 }}>
              <Bot size={28} style={{ marginBottom: 8, opacity: 0.5 }} />
              <div>Your AI security assistant.</div>
              <div style={{ fontSize: 11 }}>Send a request from Proxy → “AI Analyze”, or ask anything about the traffic you're testing.</div>
            </div>
          )}
          {store.messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} streaming={store.streaming && i === store.messages.length - 1} />
          ))}
        </div>

        <div style={{ padding: '10px 12px', borderTop: '1px solid var(--border-primary)', background: 'var(--bg-secondary)' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              className="input"
              style={{ flex: 1 }}
              placeholder={available ? 'Ask PHANTOM AI…' : 'AI runtime offline — ask after starting Ollama'}
              value={input}
              disabled={!available && store.messages.length === 0 ? false : !available}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submit()}
            />
            <button className="btn primary" onClick={submit} disabled={store.streaming}>
              <Send size={13} />
            </button>
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            {[
              { label: 'Analyze last request', run: () => void store.send('Analyze the most recent captured request in my proxy history for security issues.') },
              { label: 'Write report', run: () => void store.send('Write a brief executive summary of my current findings.') },
            ].map((q) => (
              <button key={q.label} className="btn ghost sm" disabled={!available || store.streaming} onClick={q.run}>
                {q.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* context column */}
      <div style={{ width: 280, flex: '0 0 auto', borderLeft: '1px solid var(--border-primary)', padding: 12, overflow: 'auto', background: 'var(--bg-secondary)' }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.2, color: 'var(--text-secondary)', marginBottom: 8 }}>CONTEXT</div>
        {store.context.type ? (
          <div className="panel" style={{ padding: 10, fontSize: 11.5, lineHeight: 1.5 }}>
            <Badge color="var(--accent-secondary)">{store.context.type}</Badge>
            <div className="mono" style={{ marginTop: 8, wordBreak: 'break-all' }}>{store.context.label}</div>
          </div>
        ) : (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
            No context attached. Right-click a proxy request → <b>AI Analyze</b> to attach one.
          </div>
        )}
        <div style={{ marginTop: 20, fontSize: 10, fontWeight: 700, letterSpacing: 1.2, color: 'var(--text-secondary)' }}>SUGGESTED</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
          {['Test SQL injection', 'Check for brute force', 'Verify rate limiting', 'Test password policy'].map((s) => (
            <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--text-secondary)' }}>
              <Zap size={11} color="var(--accent-secondary)" /> {s}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ role, content, streaming }: { role: string; content: string; streaming: boolean }) {
  const isUser = role === 'user'
  return (
    <div className="fade-in" style={{ display: 'flex', gap: 10, alignSelf: isUser ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
      {!isUser && <Bot size={16} color="var(--accent-primary)" style={{ marginTop: 4, flexShrink: 0 }} />}
      <div
        className="panel"
        style={{
          padding: '8px 12px',
          background: isUser ? 'var(--bg-active)' : 'var(--bg-tertiary)',
          fontSize: 12.5,
          lineHeight: 1.65,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
        }}
      >
        {isUser ? content : <Markdown components={{ p: 'span' }}>{content || (streaming ? '▍' : '')}</Markdown>}
      </div>
      {isUser && <User size={16} color="var(--text-secondary)" style={{ marginTop: 4, flexShrink: 0 }} />}
    </div>
  )
}
