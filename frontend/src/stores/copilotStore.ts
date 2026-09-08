import { create } from 'zustand'
import toast from 'react-hot-toast'
import { aiService } from '../services/aiService'
import type { AiStatus, ChatMessage } from '../types/ai'

interface CopilotStore {
  status: AiStatus | null
  messages: ChatMessage[]
  streaming: boolean
  context: { type: 'request' | 'finding' | null; id: number | null; label: string }

  refreshStatus: () => Promise<void>
  loadHistory: () => Promise<void>
  clearHistory: () => Promise<void>
  setContext: (ctx: { type: 'request' | 'finding' | null; id: number | null; label: string }) => void
  send: (text: string) => Promise<void>
  analyzeRequest: (historyId: number, label: string) => Promise<void>
  analyzeFinding: (findingId: number, label: string) => Promise<void>
  suggestPayloads: (url: string, parameter: string, vulnType: string) => Promise<void>
  lastAssistantPayloads: () => string[]
  sendLastToIntruder: () => Promise<void>
}

export const useCopilotStore = create<CopilotStore>((set, get) => ({
  status: null,
  messages: [],
  streaming: false,
  context: { type: null, id: null, label: '' },

  refreshStatus: async () => {
    try {
      set({ status: await aiService.status() })
    } catch {
      set({ status: null })
    }
  },

  loadHistory: async () => {
    try {
      const rows = await aiService.conversations()
      set({ messages: rows.reverse().slice(-100) })
    } catch {
      /* transient */
    }
  },

  clearHistory: async () => {
    try {
      await aiService.clearConversations()
      set({ messages: [] })
      toast.success('Conversation cleared')
    } catch {
      toast.error('Failed to clear conversation')
    }
  },

  setContext: (ctx) => set({ context: ctx }),

  send: async (text) => {
    if (!text.trim() || get().streaming) return
    const { context } = get()
    set((s) => ({ messages: [...s.messages, { role: 'user', content: text }], streaming: true }))
    let acc = ''
    set((s) => ({ messages: [...s.messages, { role: 'assistant', content: '' }] }))
    await aiService.streamChat(
      {
        message: text,
        context_type: context.type ?? undefined,
        context_id: context.id ?? undefined,
      },
      {
        onDelta: (d) => {
          acc += d
          set((s) => {
            const messages = [...s.messages]
            messages[messages.length - 1] = { role: 'assistant', content: acc }
            return { messages }
          })
        },
        onError: (msg) => toast.error(msg),
        onDone: () => set({ streaming: false }),
      },
    )
    set({ streaming: false })
  },

  analyzeRequest: async (historyId, label) => {
    if (get().streaming) return
    set((s) => ({
      messages: [...s.messages, { role: 'user', content: `🔍 Analyze request: ${label}` }],
      streaming: true,
      context: { type: 'request', id: historyId, label },
    }))
    set((s) => ({ messages: [...s.messages, { role: 'assistant', content: '' }] }))
    let acc = ''
    await aiService.streamAnalyze(historyId, {
      onDelta: (d) => {
        acc += d
        set((s) => {
          const messages = [...s.messages]
          messages[messages.length - 1] = { role: 'assistant', content: acc }
          return { messages }
        })
      },
      onError: (msg) => toast.error(msg),
      onDone: () => set({ streaming: false }),
    })
    set({ streaming: false })
  },

  analyzeFinding: async (findingId, label) => {
    if (get().streaming) return
    set((s) => ({
      messages: [...s.messages, { role: 'user', content: `🛡️ Analyze finding: ${label}` }],
      streaming: true,
      context: { type: 'finding', id: findingId, label },
    }))
    set((s) => ({ messages: [...s.messages, { role: 'assistant', content: '' }] }))
    let acc = ''
    await aiService.streamChat(
      { message: 'Analyze this finding: is it exploitable, how would you verify it, and what is a good PoC? Include a concrete payload or curl if applicable.', context_type: 'finding', context_id: findingId },
      {
        onDelta: (d) => {
          acc += d
          set((s) => {
            const messages = [...s.messages]
            messages[messages.length - 1] = { role: 'assistant', content: acc }
            return { messages }
          })
        },
        onError: (msg) => toast.error(msg),
        onDone: () => set({ streaming: false }),
      },
    )
    set({ streaming: false })
  },

  lastAssistantPayloads: () => {
    const msgs = get().messages
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'assistant' && msgs[i].content.includes('```')) {
        const text = msgs[i].content
        const payloads: string[] = []
        const fence = /```[a-zA-Z]*\n([\s\S]*?)```/g
        let m: RegExpExecArray | null
        while ((m = fence.exec(text)) !== null) {
          m[1]
            .split('\n')
            .map((l) => l.replace(/\r$/, '').trim())
            .filter(Boolean)
            .forEach((l) => payloads.push(l))
        }
        return [...new Set(payloads)].slice(0, 50)
      }
    }
    return []
  },

  sendLastToIntruder: async () => {
    const payloads = get().lastAssistantPayloads()
    if (!payloads.length) {
      toast.error('No code-block payloads found in the last AI answer')
      return
    }
    const { useIntruderStore } = await import('./intruderStore')
    const intruder = useIntruderStore.getState()
    intruder.setPayloads(payloads.join('\n'))
    const ctx = get().context
    if (ctx.type === 'request' && ctx.id != null) {
      try {
        const { historyService } = await import('../services/proxyService')
        const d = await historyService.detail(ctx.id)
        const u = new URL(d.url)
        const lines = [`${d.method} ${u.pathname}${u.search} HTTP/1.1`, `Host: ${u.host}`]
        Object.entries(d.request_headers ?? {}).forEach(([k, v]) => lines.push(`${k}: ${v}`))
        let raw = lines.join('\n')
        if (d.request_body) raw += `\n\n${d.request_body}`
        intruder.setDraft(raw)
      } catch {
        /* draft stays as-is; user can paste a request */
      }
    }
    toast.success(`${payloads.length} payloads loaded into Intruder — mark §positions§ and Launch`)
    window.location.hash = '#/intruder'
  },

  suggestPayloads: async (url, parameter, vulnType) => {
    if (get().streaming) return
    set((s) => ({
      messages: [...s.messages, { role: 'user', content: `⚡ Generate ${vulnType} payloads for '${parameter}' on ${url}` }],
      streaming: true,
    }))
    set((s) => ({ messages: [...s.messages, { role: 'assistant', content: '' }] }))
    let acc = ''
    await aiService.streamPayloads({ url, parameter, vuln_type: vulnType }, {
      onDelta: (d) => {
        acc += d
        set((s) => {
          const messages = [...s.messages]
          messages[messages.length - 1] = { role: 'assistant', content: acc }
          return { messages }
        })
      },
      onError: (msg) => toast.error(msg),
      onDone: () => set({ streaming: false }),
    })
    set({ streaming: false })
  },
}))
