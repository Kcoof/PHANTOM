import { api } from './api'

export interface DashboardStats {
  total_requests: number
  avg_response_time_ms: number
  total_findings: number
  findings_by_severity: Record<string, number>
  top_hosts: Array<{ host: string; count: number }>
}

export const dashboardService = {
  async stats(): Promise<DashboardStats> {
    const { data } = await api.get('/dashboard/stats')
    return data
  },
  async traffic(interval: 'minute' | 'hour' | 'day'): Promise<Array<{ bucket: string; count: number }>> {
    const { data } = await api.get('/dashboard/traffic', { params: { interval } })
    return data
  },
  async technologies(): Promise<Array<{ technology: string; hosts: string[]; source: string }>> {
    const { data } = await api.get('/dashboard/technologies')
    return data
  },
  async topFindings(): Promise<Array<{ finding_type: string; count: number; max_severity: string }>> {
    const { data } = await api.get('/dashboard/top-findings')
    return data
  },
}
