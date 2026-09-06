import { create } from 'zustand'
import toast from 'react-hot-toast'
import { apiError } from '../services/api'
import { intruderService } from '../services/intruderService'
import type { IntruderAttack, IntruderResult } from '../types/intruder'

interface IntruderStore {
  draft: string // raw request template (with §positions§)
  payloads: string
  grep: string
  attacks: IntruderAttack[]
  activeAttackId: string | null
  results: Record<string, IntruderResult[]>
  progress: Record<string, { done: number; total: number; status?: string }>
  starting: boolean

  setDraft: (raw: string) => void
  setPayloads: (p: string) => void
  setGrep: (g: string) => void
  load: () => Promise<void>
  selectAttack: (id: string | null) => Promise<void>
  launch: () => Promise<void>
  stop: (id: string) => Promise<void>
  handleWsEvent: (event: string, data: unknown) => void
}

export const useIntruderStore = create<IntruderStore>((set, get) => ({
  draft: '',
  payloads: '',
  grep: '',
  attacks: [],
  activeAttackId: null,
  results: {},
  progress: {},
  starting: false,

  setDraft: (raw) => set({ draft: raw }),
  setPayloads: (p) => set({ payloads: p }),
  setGrep: (g) => set({ grep: g }),

  load: async () => {
    try {
      const attacks = await intruderService.attacks()
      set({ attacks })
      const active = get().activeAttackId ?? attacks[0]?.id ?? null
      if (active) {
        set({ activeAttackId: active })
        set((s) => ({ results: { ...s.results, [active]: [] } }))
        const results = await intruderService.results(active)
        set((s) => ({ results: { ...s.results, [active]: results } }))
      }
    } catch (err) {
      toast.error(`Intruder load failed: ${apiError(err)}`)
    }
  },

  selectAttack: async (id) => {
    set({ activeAttackId: id })
    if (id && !get().results[id]) {
      try {
        const results = await intruderService.results(id)
        set((s) => ({ results: { ...s.results, [id]: results } }))
      } catch (err) {
        toast.error(apiError(err))
      }
    }
  },

  launch: async () => {
    const { draft, payloads, grep } = get()
    const lines = payloads.split('\n').map((p) => p.replace(/\r$/, ''))
    const payloadList = lines.filter((p) => p !== '' || lines.length === 1)
    if (!draft.includes('§')) {
      toast.error('Mark at least one §position§ in the request first')
      return
    }
    set({ starting: true })
    try {
      const { attack_id } = await intruderService.start({
        raw_request: draft,
        payloads: payloadList,
        grep_patterns: grep.split(',').map((s) => s.trim()).filter(Boolean),
      })
      set((s) => ({
        activeAttackId: attack_id,
        results: { ...s.results, [attack_id]: [] },
        progress: { ...s.progress, [attack_id]: { done: 0, total: payloadList.length } },
      }))
      toast.success(`Attack ${attack_id} launched`)
      void get().load()
    } catch (err) {
      toast.error(apiError(err))
    } finally {
      set({ starting: false })
    }
  },

  stop: async (id) => {
    try {
      await intruderService.stop(id)
      toast.success('Stopping…')
    } catch (err) {
      toast.error(apiError(err))
    }
  },

  handleWsEvent: (event, data) => {
    if (event === 'intruder_result') {
      const r = data as IntruderResult
      set((s) => ({
        results: { ...s.results, [r.attack_id]: [...(s.results[r.attack_id] ?? []), r] },
      }))
    } else if (event === 'intruder_progress') {
      const p = data as { attack_id: string; done: number; total: number; status?: string }
      set((s) => ({ progress: { ...s.progress, [p.attack_id]: p } }))
    }
  },
}))
