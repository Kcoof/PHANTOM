import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, Crosshair, Globe, ListTree, Search as SearchIcon } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '../../services/api'
import { apiError } from '../../services/api'
import { settingsService, type ScopeRule } from '../../services/settingsService'
import { useProxyStore } from '../../stores/proxyStore'
import { hostInScope } from '../../utils/scope'
import { formatMs, methodClass, statusClass } from '../../utils/formatters'

interface TreeRow {
  host: string
  has_https: number
  count: number
  methods: string
  last_id: number
  last_status: number | null
  path: string
}

interface EntryRow {
  id: number
  timestamp: string
  method: string
  url: string
  status_code: number | null
  response_time_ms: number | null
  size_bytes: number | null
  is_in_scope: number | boolean
}

interface TreeNodeT {
  name: string
  fullPath: string
  count: number
  children: Map<string, TreeNodeT>
  row?: TreeRow
}

async function loadTree(search: string): Promise<TreeRow[]> {
  const { data } = await api.get<TreeRow[]>('/target/tree', { params: search ? { search } : {} })
  return data
}

async function loadEntries(host: string, path: string): Promise<EntryRow[]> {
  const { data } = await api.get<EntryRow[]>('/target/entries', { params: { host, path } })
  return data
}

export function TargetView() {
  const [rows, setRows] = useState<TreeRow[]>([])
  const [filter, setFilter] = useState('')
  const [onlyInScope, setOnlyInScope] = useState(false)
  const [scopeRules, setScopeRules] = useState<ScopeRule[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [selected, setSelected] = useState<{ host: string; path: string; count: number } | null>(null)
  const [entries, setEntries] = useState<EntryRow[]>([])
  const [loadingEntries, setLoadingEntries] = useState(false)

  useEffect(() => {
    void loadTree('')
      .then(setRows)
      .catch((err) => toast.error(apiError(err)))
    void settingsService.scope().then(setScopeRules).catch(() => undefined)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => {
      void loadTree(filter)
        .then(setRows)
        .catch(() => undefined)
    }, 350)
    return () => clearTimeout(t)
  }, [filter])

  const hosts = useMemo(() => {
    const hostMap = new Map<string, TreeNodeT>()
    for (const r of rows) {
      if (onlyInScope && scopeRules.length && !hostInScope(scopeRules, r.host)) continue
      let hostNode = hostMap.get(r.host)
      if (!hostNode) {
        hostNode = { name: r.host, fullPath: '', count: 0, children: new Map() }
        hostMap.set(r.host, hostNode)
      }
      hostNode.count += r.count
      const segments = (r.path || '/').split('/').filter(Boolean)
      let node = hostNode
      let acc = ''
      for (const seg of segments) {
        acc += `/${seg}`
        let child = node.children.get(seg)
        if (!child) {
          child = { name: seg, fullPath: acc, count: 0, children: new Map() }
          node.children.set(seg, child)
        }
        child.count += r.count
        node = child
      }
      node.row = r
    }
    return [...hostMap.values()].sort((a, b) => b.count - a.count)
  }, [rows, onlyInScope, scopeRules])

  const toggle = (path: string) => {
    setExpanded((s) => {
      const next = new Set(s)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const openEntries = async (host: string, path: string, count: number) => {
    setSelected({ host, path, count })
    setLoadingEntries(true)
    try {
      setEntries(await loadEntries(host, path || '/'))
    } catch (err) {
      toast.error(apiError(err))
    } finally {
      setLoadingEntries(false)
    }
  }

  const openInProxy = async (id: number) => {
    await useProxyStore.getState().selectRequest(id)
    window.location.hash = '#/proxy'
  }

  const includeRules = scopeRules.filter((r) => r.rule_type === 'include')

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-primary)' }}>
        <ListTree size={14} color="var(--accent-primary)" />
        <span style={{ fontWeight: 700, letterSpacing: 0.5 }}>Target</span>
        <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>site map — everything you've discovered, per host</span>
        <div style={{ flex: 1 }} />
        <div style={{ position: 'relative' }}>
          <SearchIcon size={12} style={{ position: 'absolute', left: 7, top: 7, color: 'var(--text-muted)' }} />
          <input
            className="input"
            placeholder="Filter hosts / paths…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ width: 210, paddingLeft: 24 }}
          />
        </div>
        <button
          className={`btn ghost sm ${onlyInScope ? 'primary' : ''}`}
          title={includeRules.length ? `Only in-scope hosts (${includeRules.length} rules)` : 'No scope rules — add one in Settings'}
          onClick={() => setOnlyInScope((v) => !v)}
        >
          <Crosshair size={12} /> In scope{onlyInScope ? ' · on' : ''}
        </button>
      </div>

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <div style={{ width: 460, flex: '0 0 auto', overflow: 'auto', borderRight: '1px solid var(--border-primary)', padding: '6px 4px' }}>
          {hosts.map((host) => (
            <HostNode
              key={host.name}
              node={host}
              host={host.name}
              expanded={expanded}
              onToggle={toggle}
              selected={selected}
              onSelect={openEntries}
              depth={0}
            />
          ))}
          {hosts.length === 0 && (
            <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 12, textAlign: 'center' }}>
              Nothing captured yet{filter ? ' for this filter' : ''} — browse through the proxy.
            </div>
          )}
        </div>

        <div style={{ flex: 1, minWidth: 0, overflow: 'auto' }}>
          {selected ? (
            <div>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-primary)', display: 'flex', alignItems: 'center', gap: 10 }}>
                <Globe size={13} color="var(--accent-secondary)" />
                <span className="mono" style={{ fontSize: 12 }}>
                  {selected.host}
                  <span style={{ color: 'var(--text-secondary)' }}>{selected.path || '/'}</span>
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{selected.count} request(s) captured</span>
              </div>
              {loadingEntries ? (
                <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 12 }}>Loading…</div>
              ) : (
                entries.map((e) => (
                  <div
                    key={e.id}
                    className="fade-in"
                    onClick={() => void openInProxy(e.id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: '7px 14px',
                      borderBottom: '1px solid var(--border-primary)', cursor: 'pointer',
                    }}
                  >
                    <span className={methodClass(e.method)} style={{ fontWeight: 700, fontSize: 11, width: 46 }}>{e.method}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', width: 60 }}>#{e.id}</span>
                    <span className={statusClass(e.status_code)} style={{ fontWeight: 600, fontSize: 11, width: 34 }}>{e.status_code ?? '—'}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{formatMs(e.response_time_ms)}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{e.timestamp?.slice(5, 19)}</span>
                    <span style={{ flex: 1 }} />
                    <span style={{ fontSize: 10.5, color: 'var(--accent-primary)' }}>open in Proxy →</span>
                  </div>
                ))
              )}
              {!loadingEntries && entries.length === 0 && (
                <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 12 }}>No entries.</div>
              )}
            </div>
          ) : (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 12 }}>
              <ListTree size={26} style={{ opacity: 0.5 }} />
              Select a page in the tree to see its captured requests.
              <span style={{ fontSize: 11 }}>Click an entry to open it full-size in the Proxy view.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function HostNode(props: {
  node: TreeNodeT
  host: string
  expanded: Set<string>
  onToggle: (p: string) => void
  selected: { host: string; path: string } | null
  onSelect: (host: string, path: string, count: number) => void
  depth: number
}) {
  const { node, host, expanded, onToggle, selected, onSelect, depth } = props
  const key = `${host}${node.fullPath}`
  const isOpen = expanded.has(key)
  const children = [...node.children.values()].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
  const hasChildren = children.length > 0
  const isSelected = selected?.host === host && (selected.path || '/') === node.row?.path
  const methods = node.row?.methods?.split(',').slice(0, 3) ?? []
  const hasRow = Boolean(node.row)

  return (
    <div>
      <div
        onClick={() => {
          if (hasChildren) onToggle(key)
          if (hasRow) void onSelect(host, node.row!.path, node.row!.count)
        }}
        style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '3px 6px', marginLeft: depth * 14,
          borderRadius: 6, cursor: hasRow || hasChildren ? 'pointer' : 'default',
          background: isSelected ? 'var(--bg-active)' : 'transparent',
          transition: 'background var(--transition-fast)',
        }}
        onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = 'var(--bg-hover)' }}
        onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}
        title={`${host}${node.fullPath} — ${node.count} request(s)`}
      >
        {hasChildren ? (
          isOpen ? <ChevronDown size={12} color="var(--text-secondary)" /> : <ChevronRight size={12} color="var(--text-secondary)" />
        ) : (
          <span style={{ width: 12, display: 'inline-block' }} />
        )}
        {depth === 0 ? <Globe size={12} color="var(--accent-secondary)" /> : null}
        <span className={depth === 0 ? 'mono' : ''} style={{ fontSize: depth === 0 ? 12 : 11.5, fontWeight: depth === 0 ? 600 : 400, color: depth === 0 ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
          {node.name}
        </span>
        {depth === 0 && node.row?.has_https ? <span style={{ fontSize: 9 }}>🔒</span> : null}
        {hasRow && methods.length > 1 && depth > 0 && (
          <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{methods.join(' ')}</span>
        )}
        <div style={{ flex: 1 }} />
        {hasRow && node.row?.last_status != null && (
          <span className={statusClass(node.row.last_status)} style={{ fontSize: 10, fontWeight: 600 }}>{node.row.last_status}</span>
        )}
        <span style={{ fontSize: 10, color: 'var(--text-muted)', minWidth: 26, textAlign: 'right' }}>{node.count}</span>
      </div>
      {isOpen &&
        children.map((c) => (
          <HostNode key={c.name} node={c} host={host} expanded={expanded} onToggle={onToggle} selected={selected} onSelect={onSelect} depth={depth + 1} />
        ))}
    </div>
  )
}
