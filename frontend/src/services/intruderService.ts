import { api } from './api'
import type { IntruderAttack, IntruderResult, MatchReplaceRule, SearchResult } from '../types/intruder'

export const intruderService = {
  async wordlists(): Promise<Record<string, number>> {
    const { data } = await api.get('/intruder/wordlists')
    return data
  },
  async wordlistItems(name: string): Promise<string[]> {
    const { data } = await api.get(`/intruder/wordlists/${name}`)
    return data
  },
  async start(body: { raw_request: string; payloads: string[]; grep_patterns?: string[]; name?: string }): Promise<{ attack_id: string }> {
    const { data } = await api.post('/intruder/attacks', body)
    return data
  },
  async attacks(): Promise<IntruderAttack[]> {
    const { data } = await api.get('/intruder/attacks')
    return data
  },
  async results(attackId: string): Promise<IntruderResult[]> {
    const { data } = await api.get(`/intruder/attacks/${attackId}/results`)
    return data
  },
  async resultDetail(resultId: number): Promise<IntruderResult> {
    const { data } = await api.get(`/intruder/results/${resultId}`)
    return data
  },
  async stop(attackId: string): Promise<void> {
    await api.post(`/intruder/attacks/${attackId}/stop`)
  },
  async remove(attackId: string): Promise<void> {
    await api.delete(`/intruder/attacks/${attackId}`)
  },
}

export const searchService = {
  async search(q: string, regex: boolean, side: 'request' | 'response' | 'both'): Promise<SearchResult[]> {
    const { data } = await api.get('/search', { params: { q, regex, side } })
    return data
  },
}

export const matchReplaceService = {
  async list(): Promise<MatchReplaceRule[]> {
    const { data } = await api.get('/match-replace')
    return data
  },
  async add(rule: Omit<MatchReplaceRule, 'id'>): Promise<void> {
    await api.post('/match-replace', rule)
  },
  async remove(id: number): Promise<void> {
    await api.delete(`/match-replace/${id}`)
  },
}
