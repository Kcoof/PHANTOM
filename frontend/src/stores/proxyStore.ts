import { create } from 'zustand'
import toast from 'react-hot-toast'
import { apiError } from '../services/api'
import { historyService, proxyService } from '../services/proxyService'
import { settingsService, type ScopeRule } from '../services/settingsService'
import { hostInScope } from '../utils/scope'
import type { ProxyRequestDetail } from '../types/common'
import type { InterceptedFlow, NewRequestEvent, ProxyStatus } from '../types/proxy'
import type { ProxyRequest } from '../types/proxy'

export interface HistoryFilters {
  method: string
  host: string
  status: string
  search: string
}

/** Burp-style visibility filters (hide noise / focus on what matters). */
export interface VisibilityFilters {
  hideJs: boolean
  hideCss: boolean
  hideImages: boolean
  hideFonts: boolean
  hideMedia: boolean
  customHiddenExts: string // comma-separated
  onlyInScope: boolean
  onlyParameterized: boolean
}

const DEFAULT_VISIBILITY: VisibilityFilters = {
  hideJs: true,
  hideCss: true,
  hideImages: true,
  hideFonts: true,
  hideMedia: true,
  customHiddenExts: '',
  onlyInScope: false,
  onlyParameterized: false,
}

const PRESET_EXTS: Record<keyof Pick<VisibilityFilters, 'hideJs' | 'hideCss' | 'hideImages' | 'hideFonts' | 'hideMedia'>, string[]> = {
  hideJs: ['js', 'mjs', 'jsx', 'map', 'ts', 'coffee'],
  hideCss: ['css', 'scss', 'less'],
  hideImages: ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp', 'avif'],
  hideFonts: ['woff', 'woff2', 'ttf', 'otf', 'eot'],
  hideMedia: ['mp4', 'webm', 'mp3', 'wav', 'ogg', 'm4a', 'mov'],
}

const VISIBILITY_LS_KEY = 'phantom.proxy.visibility'

function loadStoredVisibility(): VisibilityFilters {
  try {
    const raw = localStorage.getItem(VISIBILITY_LS_KEY)
    if (raw) return { ...DEFAULT_VISIBILITY, ...JSON.parse(raw) }
  } catch {
    /* fall back to defaults */
  }
  return DEFAULT_VISIBILITY
}

function hiddenExtensions(v: VisibilityFilters): Set<string> {
  const exts = new Set<string>()
  for (const key of Object.keys(PRESET_EXTS) as (keyof typeof PRESET_EXTS)[]) {
    if (v[key]) PRESET_EXTS[key].forEach((e) => exts.add(e))
  }
  v.customHiddenExts
    .split(',')
    .map((s) => s.trim().toLowerCase().replace(/^\./, ''))
    .filter(Boolean)
    .forEach((e) => exts.add(e))
  return exts
}

interface ProxyStore {
  requests: ProxyRequest[]
  total: number
  selectedId: number | null
  selectedDetail: ProxyRequestDetail | null
  detailLoading: boolean
  filters: HistoryFilters
  visibility: VisibilityFilters
  hiddenCount: number
  scopeRules: ScopeRule[]
  status: ProxyStatus | null
  interceptEnabled: boolean
  interceptFilter: string
  interceptQueue: InterceptedFlow[]
  wsConnected: boolean
  liveTail: boolean

  setWsConnected: (v: boolean) => void
  setFilters: (f: Partial<HistoryFilters>) => void
  setVisibility: (v: Partial<VisibilityFilters>) => void
  resetVisibility: () => void
  refreshScopeRules: () => Promise<void>
  visibleRequests: () => ProxyRequest[]
  refreshRequests: () => Promise<void>
  selectRequest: (id: number | null) => Promise<void>
  refreshStatus: () => Promise<void>
  startProxy: () => Promise<void>
  stopProxy: () => Promise<void>
  toggleIntercept: () => Promise<void>
  setInterceptFilter: (f: string) => void
  refreshInterceptQueue: () => Promise<void>
  forwardFlow: (flowId: string, modified?: string) => Promise<void>
  dropFlow: (flowId: string) => Promise<void>
  clearHistory: () => Promise<void>
  handleWsEvent: (event: string, data: unknown) => void
  setLiveTail: (v: boolean) => void
  analyzeRequest: (id: number, label: string) => Promise<void>
}

const MAX_ROWS = 2000

export const useProxyStore = create<ProxyStore>((set, get) => ({
  requests: [],
  total: 0,
  selectedId: null,
  selectedDetail: null,
  detailLoading: false,
  filters: { method: '', host: '', status: '', search: '' },
  visibility: loadStoredVisibility(),
  hiddenCount: 0,
  scopeRules: [],
  status: null,
  interceptEnabled: false,
  interceptFilter: '',
  interceptQueue: [],
  wsConnected: false,
  liveTail: true,

  setWsConnected: (v) => set({ wsConnected: v }),

  setFilters: (f) => {
    set((s) => ({ filters: { ...s.filters, ...f } }))
    void get().refreshRequests()
  },

  setVisibility: (patch) => {
    set((s) => {
      const visibility = { ...s.visibility, ...patch }
      try {
        localStorage.setItem(VISIBILITY_LS_KEY, JSON.stringify(visibility))
      } catch {
        /* non-fatal */
      }
      return { visibility }
    })
    get().visibleRequests() // recompute hiddenCount
  },

  resetVisibility: () => {
    try {
      localStorage.setItem(VISIBILITY_LS_KEY, JSON.stringify(DEFAULT_VISIBILITY))
    } catch {
      /* non-fatal */
    }
    set({ visibility: { ...DEFAULT_VISIBILITY } })
    get().visibleRequests()
  },

  refreshScopeRules: async () => {
    try {
      set({ scopeRules: await settingsService.scope() })
    } catch {
      /* keep last known rules */
    }
  },

  visibleRequests: () => {
    const { requests, visibility, scopeRules } = get()
    const exts = hiddenExtensions(visibility)
    const visible = requests.filter((r) => {
      if (exts.size > 0) {
        const file = (r.path || '').split('?')[0].split('/').pop() ?? ''
        const dot = file.lastIndexOf('.')
        const ext = dot >= 0 ? file.slice(dot + 1).toLowerCase() : ''
        if (ext && exts.has(ext)) return false
        if (!ext && visibility.hideImages && /^(favicon|apple-touch-icon|.*-\d+x\d+)$/.test(file)) return false
      }
      if (visibility.onlyInScope && scopeRules.length >= 0) {
        // live evaluation against current rules (rows captured before rule
        // changes still get judged by what's in scope NOW, like Burp)
        if (!hostInScope(scopeRules, r.host)) return false
      }
      if (visibility.onlyParameterized) {
        const hasQuery = Boolean(r.query_string) || /\?[^/]*=/.test(r.url)
        if (!hasQuery) return false
      }
      return true
    })
    if (visible.length !== requests.length - get().hiddenCount) {
      set({ hiddenCount: requests.length - visible.length })
    }
    return visible
  },

  refreshRequests: async () => {
    const { filters } = get()
    try {
      const page = await historyService.list({
        limit: 500,
        method: filters.method || undefined,
        host: filters.host || undefined,
        status: filters.status ? Number(filters.status) : undefined,
        search: filters.search || undefined,
      })
      set({ requests: page.items, total: page.total })
    } catch (err) {
      toast.error(`Failed to load history: ${apiError(err)}`)
    }
  },

  selectRequest: async (id) => {
    if (id == null) {
      set({ selectedId: null, selectedDetail: null })
      return
    }
    set({ selectedId: id, detailLoading: true, selectedDetail: null })
    try {
      const detail = await historyService.detail(id)
      set({ selectedDetail: detail })
    } catch (err) {
      toast.error(`Failed to load request: ${apiError(err)}`)
    } finally {
      set({ detailLoading: false })
    }
  },

  refreshStatus: async () => {
    try {
      const status = await proxyService.status()
      set({ status, interceptEnabled: status.intercept_enabled })
    } catch {
      set({ status: null })
    }
    void get().refreshScopeRules()
  },

  startProxy: async () => {
    try {
      await proxyService.start()
      await get().refreshStatus()
      toast.success('Proxy started')
    } catch (err) {
      toast.error(`Proxy failed to start: ${apiError(err)}`)
    }
  },

  stopProxy: async () => {
    try {
      await proxyService.stop()
      await get().refreshStatus()
      toast.success('Proxy stopped')
    } catch (err) {
      toast.error(`Proxy stop failed: ${apiError(err)}`)
    }
  },

  toggleIntercept: async () => {
    const next = !get().interceptEnabled
    try {
      await proxyService.toggleIntercept(next, get().interceptFilter)
      set({ interceptEnabled: next })
      toast.success(next ? 'Intercept ON — matching requests will be held' : 'Intercept OFF')
      if (!next) set({ interceptQueue: [] })
    } catch (err) {
      toast.error(`Intercept toggle failed: ${apiError(err)}`)
    }
  },

  setInterceptFilter: (f) => set({ interceptFilter: f }),

  refreshInterceptQueue: async () => {
    try {
      set({ interceptQueue: await proxyService.interceptQueue() })
    } catch {
      /* transient — ws events will refresh */
    }
  },

  forwardFlow: async (flowId, modified) => {
    try {
      await proxyService.forwardFlow(flowId, modified)
      set((s) => ({ interceptQueue: s.interceptQueue.filter((f) => f.flow_id !== flowId) }))
      toast.success('Request forwarded')
    } catch (err) {
      toast.error(`Forward failed: ${apiError(err)}`)
    }
  },

  dropFlow: async (flowId) => {
    try {
      await proxyService.dropFlow(flowId)
      set((s) => ({ interceptQueue: s.interceptQueue.filter((f) => f.flow_id !== flowId) }))
      toast.success('Request dropped')
    } catch (err) {
      toast.error(`Drop failed: ${apiError(err)}`)
    }
  },

  clearHistory: async () => {
    try {
      const { deleted } = await historyService.clear()
      toast.success(`Cleared ${deleted} entries`)
      set({ requests: [], total: 0, selectedId: null, selectedDetail: null })
    } catch (err) {
      toast.error(`Clear failed: ${apiError(err)}`)
    }
  },

  handleWsEvent: (event, data) => {
    const state = get()
    switch (event) {
      case 'new_request': {
        if (!state.liveTail) return
        const e = data as NewRequestEvent
        const row: ProxyRequest = {
          id: e.id,
          method: e.method,
          scheme: '',
          host: e.host,
          port: 0,
          path: e.path,
          query_string: e.query_string ?? null,
          url: e.url,
          status_code: e.status_code,
          response_time_ms: e.response_time_ms,
          size_bytes: e.size_bytes,
          is_intercepted: 0,
          is_in_scope: e.is_in_scope ?? 1,
          tags: [],
          _new: true,
        } as ProxyRequest
        set((s) => ({
          requests: [row, ...s.requests].slice(0, MAX_ROWS),
          total: s.total + 1,
        }))
        get().visibleRequests() // keep hidden-count fresh for live rows
        break
      }
      case 'intercept_request':
        void state.refreshInterceptQueue()
        break
      case 'intercept_resolved':
        set((s) => ({
          interceptQueue: s.interceptQueue.filter((f) => f.flow_id !== (data as { flow_id: string }).flow_id),
        }))
        break
      case 'proxy_status':
        void state.refreshStatus()
        break
      default:
        break
    }
  },

  setLiveTail: (v) => set({ liveTail: v }),

  analyzeRequest: async (id, label) => {
    const { useCopilotStore } = await import('./copilotStore')
    const { analyzeRequest } = useCopilotStore.getState()
    await analyzeRequest(id, label)
    window.location.hash = '#/copilot'
  },
}))
