import { api } from './api'

export interface AutoDetectResult {
  codec: string
  output: string
  confidence: number
}

export const decoderService = {
  async encode(input: string, codec: string): Promise<string> {
    const { data } = await api.post('/decoder/encode', { input, codec })
    return data.output
  },
  async decode(input: string, codec: string): Promise<string> {
    const { data } = await api.post('/decoder/decode', { input, codec })
    return data.output
  },
  async autoDetect(input: string): Promise<AutoDetectResult[]> {
    const { data } = await api.post('/decoder/auto-detect', { input })
    return data.results
  },
  async hash(input: string, algorithm: string): Promise<string> {
    const { data } = await api.post('/decoder/hash', { input, algorithm })
    return data.digest
  },
}
