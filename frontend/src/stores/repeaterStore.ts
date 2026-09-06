import { create } from 'zustand'
import toast from 'react-hot-toast'
import { apiError } from '../services/api'
import { buildRaw, repeaterService } from '../services/repeaterService'
import type { RepeaterTab, SendResult } from '../types/repeater'

interface RepeaterStore {
  tabs: RepeaterTab[]
  activeTabId: number | null
  rawEdits: Record<number, string>
  sending: boolean
  lastResult: Record<number, SendResult>
  loaded: boolean

  load: () => Promise<void>
  setActive: (id: number) => void
  setRaw: (id: number, raw: string) => void
  rawOf: (tab: RepeaterTab) => string
  newTab: () => Promise<void>
  closeTab: (id: number) => Promise<void>
  send: (id: number) => Promise<void>
}

export const useRepeaterStore = create<RepeaterStore>((set, get) => ({
  tabs: [],
  activeTabId: null,
  rawEdits: {},
  sending: false,
  lastResult: {},
  loaded: false,

  load: async () => {
    try {
      const tabs = await repeaterService.list()
      set({
        tabs,
        loaded: true,
        activeTabId: get().activeTabId ?? tabs[tabs.length - 1]?.id ?? null,
      })
    } catch (err) {
      toast.error(`Failed to load repeater tabs: ${apiError(err)}`)
    }
  },

  setActive: (id) => set({ activeTabId: id }),

  setRaw: (id, raw) => set((s) => ({ rawEdits: { ...s.rawEdits, [id]: raw } })),

  rawOf: (tab) => get().rawEdits[tab.id] ?? buildRaw(tab),

  newTab: async () => {
    try {
      const tab = await repeaterService.create({
        name: `Tab ${get().tabs.length + 1}`,
        method: 'GET',
        url: 'http://example.com/',
        request_headers: { 'User-Agent': 'PHANTOM-Repeater' },
      })
      set((s) => ({ tabs: [...s.tabs, tab], activeTabId: tab.id }))
    } catch (err) {
      toast.error(`Failed to create tab: ${apiError(err)}`)
    }
  },

  closeTab: async (id) => {
    try {
      await repeaterService.remove(id)
      set((s) => {
        const tabs = s.tabs.filter((t) => t.id !== id)
        return {
          tabs,
          activeTabId: s.activeTabId === id ? tabs[tabs.length - 1]?.id ?? null : s.activeTabId,
        }
      })
    } catch (err) {
      toast.error(`Failed to close tab: ${apiError(err)}`)
    }
  },

  send: async (id) => {
    const tab = get().tabs.find((t) => t.id === id)
    if (!tab) return
    set({ sending: true })
    try {
      const raw = get().rawEdits[id] ?? buildRaw(tab)
      const result = await repeaterService.send(id, raw)
      set((s) => ({ lastResult: { ...s.lastResult, [id]: result } }))
      void get().load()
      toast.success(`Response ${result.status} in ${result.time_ms} ms`)
    } catch (err) {
      toast.error(`Send failed: ${apiError(err)}`)
    } finally {
      set({ sending: false })
    }
  },
}))
