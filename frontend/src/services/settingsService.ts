import { api } from './api'

export interface ScopeRule {
  id: number
  rule_type: 'include' | 'exclude'
  protocol: string | null
  host_pattern: string
  port: string | null
  path_pattern: string
  is_active: number | boolean
}

export const settingsService = {
  async all(): Promise<Record<string, Record<string, string>>> {
    const { data } = await api.get('/settings')
    return data.categories
  },
  async update(values: Record<string, string>): Promise<void> {
    await api.put('/settings', { values })
  },
  async scope(): Promise<ScopeRule[]> {
    const { data } = await api.get('/settings/scope')
    return data
  },
  async addScope(rule: Partial<ScopeRule>): Promise<void> {
    await api.post('/settings/scope', rule)
  },
  async deleteScope(id: number): Promise<void> {
    await api.delete(`/settings/scope/${id}`)
  },
}
