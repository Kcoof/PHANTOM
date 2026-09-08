import { create } from 'zustand'
import toast from 'react-hot-toast'
import { apiError } from '../services/api'
import { pluginService, type PluginInfo, type PluginResultRow, type PluginRun } from '../services/pluginService'

interface PluginStore {
  plugins: PluginInfo[]
  runs: PluginRun[]
  activeRunId: string | null
  results: Record<string, PluginResultRow[]>
  progress: Record<string, { done: number; total: number }>

  load: () => Promise<void>
  selectRun: (id: string) => Promise<void>
  start: (pluginId: string, context: Record<string, unknown>, options?: Record<string, unknown>) => Promise<void>
  stop: (runId: string) => Promise<void>
  handleWsEvent: (event: string, data: unknown) => void
}

export const usePluginStore = create<PluginStore>((set, get) => ({
  plugins: [],
  runs: [],
  activeRunId: null,
  results: {},
  progress: {},

  load: async () => {
    try {
      const [plugins, runs] = await Promise.all([pluginService.list(), pluginService.runs()])
      set({ plugins, runs })
      const active = get().activeRunId ?? runs[0]?.id ?? null
      if (active) {
        set({ activeRunId: active })
        if (!get().results[active]) {
          const results = await pluginService.results(active)
          set((s) => ({ results: { ...s.results, [active]: results } }))
        }
      }
    } catch (err) {
      toast.error(`Plugins load failed: ${apiError(err)}`)
    }
  },

  selectRun: async (id) => {
    set({ activeRunId: id })
    if (id && !get().results[id]) {
      try {
        const results = await pluginService.results(id)
        set((s) => ({ results: { ...s.results, [id]: results } }))
      } catch (err) {
        toast.error(apiError(err))
      }
    }
  },

  start: async (pluginId, context, options = {}) => {
    try {
      const { run_id } = await pluginService.run(pluginId, context, options)
      set((s) => ({
        activeRunId: run_id,
        results: { ...s.results, [run_id]: [] },
        progress: { ...s.progress, [run_id]: { done: 0, total: 0 } },
      }))
      toast.success('Plugin run started')
      void get().load()
    } catch (err) {
      toast.error(apiError(err))
    }
  },

  stop: async (runId) => {
    try {
      await pluginService.stop(runId)
      toast.success('Stopping…')
    } catch (err) {
      toast.error(apiError(err))
    }
  },

  handleWsEvent: (event, data) => {
    if (event === 'plugin_progress') {
      const p = data as { run_id: string; done: number; total: number }
      set((s) => ({ progress: { ...s.progress, [p.run_id]: { done: p.done, total: p.total } } }))
    } else if (event === 'plugin_result') {
      const r = data as { run_id: string; id: number; kind: string; data: Record<string, unknown> }
      set((s) => ({
        results: { ...s.results, [r.run_id]: [...(s.results[r.run_id] ?? []), { id: r.id, run_id: r.run_id, kind: r.kind, data: r.data }] },
      }))
    } else if (event === 'plugin_done') {
      const d = data as { run_id: string; status: string }
      toast.success(`Plugin run ${d.status}`)
      void get().load()
    }
  },
}))
