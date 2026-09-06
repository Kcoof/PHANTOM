import { create } from 'zustand'
import toast from 'react-hot-toast'
import { apiError } from '../services/api'
import { historyService, proxyService } from '../services/proxyService'
import type { ProxyRequestDetail } from '../types/common'
import type { InterceptedFlow, NewRequestEvent, ProxyStatus } from '../types/proxy'
import type { ProxyRequest } from '../types/proxy'

export interface HistoryFilters {
  method: string
  host: string
  status: string
  search: string
}

interface ProxyStore {
  requests: ProxyRequest[]
  total: number
  selectedId: number | null
  selectedDetail: ProxyRequestDetail | null
  detailLoading: boolean
  filters: HistoryFilters
  status: ProxyStatus | null
  interceptEnabled: boolean
  interceptFilter: string
  interceptQueue: InterceptedFlow[]
  wsConnected: boolean
  liveTail: boolean

  setWsConnected: (v: boolean) => void
  setFilters: (f: Partial<HistoryFilters>) => void
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
}

const MAX_ROWS = 2000

export const useProxyStore = create<ProxyStore>((set, get) => ({
  requests: [],
  total: 0,
  selectedId: null,
  selectedDetail: null,
  detailLoading: false,
  filters: { method: '', host: '', status: '', search: '' },
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
          url: e.url,
          status_code: e.status_code,
          response_time_ms: e.response_time_ms,
          size_bytes: e.size_bytes,
          is_intercepted: 0,
          is_in_scope: 1,
          tags: [],
          _new: true,
        } as ProxyRequest
        set((s) => ({
          requests: [row, ...s.requests].slice(0, MAX_ROWS),
          total: s.total + 1,
        }))
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
}))
