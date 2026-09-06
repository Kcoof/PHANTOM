import { api } from './api'
import type { Paged, ProxyRequestDetail } from '../types/common'
import type { InterceptedFlow, ProxyStatus } from '../types/proxy'

export const proxyService = {
  async status(): Promise<ProxyStatus> {
    const { data } = await api.get<ProxyStatus>('/proxy/status')
    return data
  },
  async start(host?: string, port?: number): Promise<{ status: string; host: string; port: number }> {
    const { data } = await api.post('/proxy/start', { host, port })
    return data
  },
  async stop(): Promise<{ status: string }> {
    const { data } = await api.post('/proxy/stop', {})
    return data
  },
  async toggleIntercept(enabled: boolean, filter?: string): Promise<{ intercept: boolean }> {
    const { data } = await api.post('/proxy/intercept/toggle', { enabled, filter })
    return data
  },
  async interceptQueue(): Promise<InterceptedFlow[]> {
    const { data } = await api.get<InterceptedFlow[]>('/proxy/intercept/queue')
    return data
  },
  async forwardFlow(flowId: string, modifiedRequest?: string): Promise<void> {
    await api.post(`/proxy/intercept/${flowId}/forward`, { modified_request: modifiedRequest })
  },
  async dropFlow(flowId: string): Promise<void> {
    await api.post(`/proxy/intercept/${flowId}/drop`, {})
  },
  caCertUrl: '/api/proxy/ca-cert',
}

export const historyService = {
  async list(params: {
    page?: number
    limit?: number
    method?: string
    host?: string
    status?: number
    search?: string
  }): Promise<Paged<ProxyRequestDetail>> {
    const { data } = await api.get<Paged<ProxyRequestDetail>>('/history', { params })
    return data
  },
  async detail(id: number): Promise<ProxyRequestDetail> {
    const { data } = await api.get<ProxyRequestDetail>(`/history/${id}`)
    return data
  },
  async clear(): Promise<{ deleted: number }> {
    const { data } = await api.delete('/history')
    return data
  },
  async remove(id: number): Promise<void> {
    await api.delete(`/history/${id}`)
  },
  async tag(id: number, tag: string): Promise<{ tags: string[] }> {
    const { data } = await api.post(`/history/${id}/tag`, { tag })
    return data
  },
  async note(id: number, note: string): Promise<void> {
    await api.post(`/history/${id}/note`, { note })
  },
  async highlight(id: number, color: string | null): Promise<void> {
    await api.post(`/history/${id}/highlight`, { color })
  },
  async sendToRepeater(id: number): Promise<{ repeater_tab_id: number }> {
    const { data } = await api.post(`/history/${id}/send-to-repeater`, {})
    return data
  },
}
