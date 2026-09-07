import { useEffect, useState } from 'react'
import { Globe2, Plus, Replace, Shield, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiError } from '../../services/api'
import { settingsService, type ScopeRule } from '../../services/settingsService'
import { matchReplaceService } from '../../services/intruderService'
import type { MatchReplaceRule } from '../../types/intruder'
import { Badge } from '../shared/Badge'
import { LoadingSpinner } from '../shared/LoadingSpinner'

const SETTING_LABELS: Record<string, string> = {
  proxy_port: 'Proxy port',
  proxy_host: 'Proxy bind host',
  intercept_enabled: 'Intercept on at startup',
  intercept_filter: 'Intercept filter',
  scanner_threads: 'Scanner threads',
  scanner_timeout: 'Scanner timeout (s)',
  scanner_delay_ms: 'Scanner delay between probes (ms)',
  scanner_concurrency: 'Scanner max concurrency',
  ai_provider: 'AI provider (ollama | openai)',
  ai_model: 'AI model',
  ai_base_url: 'AI base URL (…/v1 for openai)',
  ai_api_key: 'AI API key (openai-compatible)',
  theme: 'Theme',
  font_size: 'Font size',
}

export function SettingsView() {
  const [settings, setSettings] = useState<Record<string, Record<string, string>> | null>(null)
  const [scope, setScope] = useState<ScopeRule[]>([])
  const [newPattern, setNewPattern] = useState('')
  const [newType, setNewType] = useState<'include' | 'exclude'>('include')
  const [mrRules, setMrRules] = useState<MatchReplaceRule[]>([])
  const [mrForm, setMrForm] = useState({
    location: 'request' as 'request' | 'response',
    match_type: 'literal' as 'literal' | 'regex',
    match_value: '',
    replace_value: '',
    comment: '',
  })

  const load = async () => {
    try {
      const [s, sc, mr] = await Promise.all([
        settingsService.all(),
        settingsService.scope(),
        matchReplaceService.list(),
      ])
      setSettings(s)
      setScope(sc)
      setMrRules(mr)
    } catch (err) {
      toast.error(`Failed to load settings: ${apiError(err)}`)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const save = async (key: string, value: string) => {
    try {
      await settingsService.update({ [key]: value })
      toast.success(`Saved ${key}`)
      void load()
    } catch (err) {
      toast.error(apiError(err))
    }
  }

  const addRule = async () => {
    if (!newPattern.trim()) return
    try {
      await settingsService.addScope({ rule_type: newType, host_pattern: newPattern.trim(), protocol: 'any', path_pattern: '.*' })
      toast.success('Scope rule added')
      setNewPattern('')
      void load()
    } catch (err) {
      toast.error(apiError(err))
    }
  }

  if (!settings) return <LoadingSpinner label="Loading settings…" />

  const categoryIcons: Record<string, React.ReactNode> = {
    proxy: <Globe2 size={14} color="var(--accent-secondary)" />,
    scanner: <Shield size={14} color="var(--severity-high)" />,
    ai: <Shield size={14} color="var(--accent-primary)" />,
    ui: <Shield size={14} color="var(--severity-info)" />,
  }

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 18, display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 860 }}>
      <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: 0.5 }}>Settings</div>

      {Object.entries(settings).map(([category, values]) => (
        <div key={category} className="panel" style={{ padding: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, textTransform: 'capitalize' }}>
            {categoryIcons[category]} <span style={{ fontWeight: 700, fontSize: 12.5 }}>{category}</span>
          </div>
          {Object.entries(values).map(([key, value]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)', width: 200 }}>{SETTING_LABELS[key] ?? key}</span>
              <input
                className="input mono"
                defaultValue={value}
                style={{ flex: 1, fontSize: 11.5 }}
                onBlur={(e) => e.target.value !== value && void save(key, e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
              />
            </div>
          ))}
        </div>
      ))}

      {/* scope rules */}
      <div className="panel" style={{ padding: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <Shield size={14} color="var(--severity-high)" />
          <span style={{ fontWeight: 700, fontSize: 12.5 }}>Scope rules</span>
        </div>
        <p style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 10 }}>
          Active scanning only runs against hosts matching an active <b>include</b> rule (authorized targets only).
          Exclude rules take precedence. A domain matches itself <b>and all its subdomains</b> —
          <span className="mono"> example.com</span> covers <span className="mono">api.example.com</span> too,
          and <span className="mono">*.example.com</span> also matches the apex.
        </p>
        <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
          <select className="input" value={newType} onChange={(e) => setNewType(e.target.value as 'include' | 'exclude')} style={{ width: 110 }}>
            <option value="include">include</option>
            <option value="exclude">exclude</option>
          </select>
          <input
            className="input mono"
            placeholder="*.your-lab.example"
            value={newPattern}
            onChange={(e) => setNewPattern(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void addRule()}
            style={{ flex: 1 }}
          />
          <button className="btn primary sm" onClick={() => void addRule()}>
            <Plus size={12} /> Add
          </button>
        </div>
        {scope.map((r) => (
          <div key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: '1px solid var(--border-primary)' }}>
            <Badge color={r.rule_type === 'include' ? 'var(--severity-low)' : 'var(--severity-critical)'}>
              {r.rule_type.toUpperCase()}
            </Badge>
            <span className="mono" style={{ fontSize: 12, flex: 1 }}>{r.host_pattern}</span>
            <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>{r.protocol ?? 'any'}</span>
            <button
              className="btn ghost sm danger"
              onClick={async () => {
                try {
                  await settingsService.deleteScope(r.id)
                  toast.success('Rule deleted')
                  void load()
                } catch (err) {
                  toast.error(apiError(err))
                }
              }}
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
        {scope.length === 0 && (
          <div style={{ color: 'var(--text-muted)', fontSize: 11.5 }}>No scope rules — active scanning is blocked until you add one.</div>
        )}
      </div>

      {/* match & replace */}
      <div className="panel" style={{ padding: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <Replace size={14} color="var(--accent-secondary)" />
          <span style={{ fontWeight: 700, fontSize: 12.5 }}>Match &amp; Replace</span>
        </div>
        <p style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 10 }}>
          Live rewriting of proxied traffic, applied in order before it's sent/stored. Use it to inject headers,
          strip cache busters, or normalize values. Header names, header values, and bodies are all rewritten.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '90px 80px 1fr 1fr auto', gap: 6, marginBottom: 8 }}>
          <select className="input" value={mrForm.location} onChange={(e) => setMrForm({ ...mrForm, location: e.target.value as 'request' | 'response' })}>
            <option value="request">request</option>
            <option value="response">response</option>
          </select>
          <select className="input" value={mrForm.match_type} onChange={(e) => setMrForm({ ...mrForm, match_type: e.target.value as 'literal' | 'regex' })}>
            <option value="literal">literal</option>
            <option value="regex">regex</option>
          </select>
          <input className="input mono" placeholder="match (e.g. X-Old-Header or ^/v1/)" value={mrForm.match_value} onChange={(e) => setMrForm({ ...mrForm, match_value: e.target.value })} style={{ fontSize: 11 }} />
          <input className="input mono" placeholder="replace with…" value={mrForm.replace_value} onChange={(e) => setMrForm({ ...mrForm, replace_value: e.target.value })} style={{ fontSize: 11 }} />
          <button
            className="btn primary sm"
            onClick={async () => {
              if (!mrForm.match_value.trim()) return
              try {
                await matchReplaceService.add({ ...mrForm, enabled: true, comment: mrForm.comment || null })
                toast.success('Rule added — applies to new traffic')
                setMrForm({ ...mrForm, match_value: '', replace_value: '' })
                void load()
              } catch (err) {
                toast.error(apiError(err))
              }
            }}
          >
            <Plus size={12} /> Add
          </button>
        </div>
        {mrRules.map((r) => (
          <div key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', borderBottom: '1px solid var(--border-primary)', fontSize: 11.5 }}>
            <Badge color={r.location === 'request' ? 'var(--accent-primary)' : 'var(--accent-secondary)'}>{r.location}</Badge>
            <span style={{ color: 'var(--text-muted)', width: 46 }}>{r.match_type}</span>
            <span className="mono" style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {r.match_value} <span style={{ color: 'var(--text-muted)' }}>→</span> {r.replace_value || '(remove)'}
            </span>
            <button
              className="btn ghost sm danger"
              onClick={async () => {
                try {
                  await matchReplaceService.remove(r.id)
                  void load()
                } catch (err) {
                  toast.error(apiError(err))
                }
              }}
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
        {mrRules.length === 0 && (
          <div style={{ color: 'var(--text-muted)', fontSize: 11.5 }}>No rules — proxied traffic passes through unchanged.</div>
        )}
      </div>
    </div>
  )
}
