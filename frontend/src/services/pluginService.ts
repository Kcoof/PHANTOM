import { api } from './api'
import { intruderService } from './intruderService'

export interface PluginInfo {
  id: string
  name: string
  description: string
  accepts: string[]
  parameters: Array<{ key: string; type: string; options?: string[]; default?: string | number }>
}

export interface PluginRun {
  id: string
  plugin_id: string
  target: string
  status: 'running' | 'completed' | 'failed' | 'stopped'
  done: number
  total: number
  error: string | null
  created_at: string
}

export interface PluginResultRow {
  id: number
  run_id: string
  kind: string // 'param' | 'info' | 'summary' | ...
  data: Record<string, unknown>
}

export const pluginService = {
  async list(): Promise<PluginInfo[]> {
    const { data } = await api.get('/plugins')
    return data
  },
  async run(pluginId: string, context: Record<string, unknown>, options: Record<string, unknown> = {}): Promise<{ run_id: string }> {
    const { data } = await api.post(`/plugins/${pluginId}/run`, { context, options })
    return data
  },
  async runs(): Promise<PluginRun[]> {
    const { data } = await api.get('/plugins/runs')
    return data
  },
  async results(runId: string): Promise<PluginResultRow[]> {
    const { data } = await api.get(`/plugins/runs/${runId}/results`)
    return data
  },
  async stop(runId: string): Promise<void> {
    await api.post(`/plugins/runs/${runId}/stop`)
  },
  intruder: intruderService,
}
