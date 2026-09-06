import { api } from './api'
import type { RepeaterTab, SendResult } from '../types/repeater'

export const repeaterService = {
  async list(): Promise<RepeaterTab[]> {
    const { data } = await api.get<RepeaterTab[]>('/repeater/tabs')
    return data
  },
  async create(tab: { name?: string; method: string; url: string; request_headers: Record<string, string>; request_body?: string }): Promise<RepeaterTab> {
    const { data } = await api.post<RepeaterTab>('/repeater/tabs', tab)
    return data
  },
  async update(id: number, patch: Partial<RepeaterTab>): Promise<RepeaterTab> {
    const { data } = await api.put<RepeaterTab>(`/repeater/tabs/${id}`, patch)
    return data
  },
  async remove(id: number): Promise<void> {
    await api.delete(`/repeater/tabs/${id}`)
  },
  async send(id: number, rawRequest?: string): Promise<SendResult> {
    const { data } = await api.post<SendResult>(`/repeater/tabs/${id}/send`, {
      raw_request: rawRequest ?? null,
    })
    return data
  },
}

export function buildRaw(tab: RepeaterTab): string {
  try {
    const u = new URL(tab.url)
    const target = u.pathname + u.search
    const lines = [`${tab.method} ${target} HTTP/1.1`]
    const headers = { ...tab.request_headers }
    if (!Object.keys(headers).some((k) => k.toLowerCase() === 'host')) {
      lines.push(`Host: ${u.host}`)
    }
    Object.entries(headers).forEach(([k, v]) => lines.push(`${k}: ${v}`))
    let raw = lines.join('\n')
    if (tab.request_body) raw += `\n\n${tab.request_body}`
    return raw
  } catch {
    return `${tab.method} ${tab.url} HTTP/1.1`
  }
}
