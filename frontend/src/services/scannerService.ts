import { api } from './api'
import type { Finding, Scan, ScanCheckInfo } from '../types/scanner'

export interface ScanTarget {
  host: string
  count: number
  last_seen: string | null
}

export const scannerService = {
  async checks(): Promise<ScanCheckInfo[]> {
    const { data } = await api.get<ScanCheckInfo[]>('/scanner/checks')
    return data
  },
  async targets(): Promise<ScanTarget[]> {
    const { data } = await api.get<ScanTarget[]>('/scanner/targets')
    return data
  },
  async startScan(body: {
    target_url?: string
    scan_type: 'active' | 'passive' | 'full'
    checks?: string[]
  }): Promise<{ scan_id: string }> {
    const { data } = await api.post('/scanner/scan', body)
    return data
  },
  async scanHistoryIds(ids: number[], scan_type: 'active' | 'passive' = 'passive'): Promise<{ scan_id: string }> {
    const { data } = await api.post('/scanner/scan', { history_ids: ids, scan_type })
    return data
  },
  async scans(): Promise<Scan[]> {
    const { data } = await api.get<Scan[]>('/scanner/scans')
    return data
  },
  async findings(params?: { severity?: string; scan_id?: string }): Promise<Finding[]> {
    const { data } = await api.get<Finding[]>('/scanner/findings', { params })
    return data
  },
  async setFindingStatus(id: number, status: string): Promise<Finding> {
    const { data } = await api.put<Finding>(`/scanner/findings/${id}/status`, { status })
    return data
  },
  async control(scanId: string, action: 'pause' | 'resume' | 'stop'): Promise<void> {
    await api.post(`/scanner/scans/${scanId}/${action}`)
  },
}
