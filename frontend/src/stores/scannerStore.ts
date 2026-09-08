import { create } from 'zustand'
import toast from 'react-hot-toast'
import { apiError } from '../services/api'
import { scannerService } from '../services/scannerService'
import type { Finding, Scan, ScanCheckInfo, ScanProgressEvent } from '../types/scanner'
import type { NewRequestEvent } from '../types/proxy'

interface ScannerStore {
  checks: ScanCheckInfo[]
  scans: Scan[]
  findings: Finding[]
  selectedFinding: Finding | null
  progress: Record<string, ScanProgressEvent>
  starting: boolean
  triageProgress: { done: number; total: number; tagged: number } | null

  load: () => Promise<void>
  startScan: (type: 'active' | 'passive' | 'full', selected: string[], targetHost?: string, inScopeOnly?: boolean) => Promise<void>
  selectFinding: (f: Finding | null) => void
  setFindingStatus: (id: number, status: string) => Promise<void>
  control: (scanId: string, action: 'pause' | 'resume' | 'stop') => Promise<void>
  runTriage: () => Promise<void>
  handleWsEvent: (event: string, data: unknown) => void
}

export const useScannerStore = create<ScannerStore>((set, get) => ({
  checks: [],
  scans: [],
  findings: [],
  selectedFinding: null,
  progress: {},
  starting: false,
  triageProgress: null,

  load: async () => {
    try {
      const [checks, scans, findings] = await Promise.all([
        scannerService.checks(),
        scannerService.scans(),
        scannerService.findings(),
      ])
      set({ checks, scans, findings })
    } catch (err) {
      toast.error(`Scanner load failed: ${apiError(err)}`)
    }
  },

  startScan: async (type, selected, targetHost, inScopeOnly) => {
    set({ starting: true })
    try {
      const { scan_id } = await scannerService.startScan({
        scan_type: type,
        checks: selected.length ? selected : undefined,
        target_url: inScopeOnly ? undefined : targetHost || undefined,
        in_scope_only: inScopeOnly || undefined,
      })
      toast.success(`Scan ${scan_id} started`)
      set((s) => ({
        progress: { ...s.progress, [scan_id]: { scan_id, status: 'running', done: 0, total: 0 } },
      }))
      void get().load()
    } catch (err) {
      toast.error(`Scan failed to start: ${apiError(err)}`)
    } finally {
      set({ starting: false })
    }
  },

  selectFinding: (f) => set({ selectedFinding: f }),

  setFindingStatus: async (id, status) => {
    try {
      const updated = await scannerService.setFindingStatus(id, status)
      set((s) => ({
        findings: s.findings.map((f) => (f.id === id ? updated : f)),
        selectedFinding: s.selectedFinding?.id === id ? updated : s.selectedFinding,
      }))
      toast.success(`Finding marked ${status.replace('_', ' ')}`)
    } catch (err) {
      toast.error(`Status update failed: ${apiError(err)}`)
    }
  },

  control: async (scanId, action) => {
    try {
      await scannerService.control(scanId, action)
      void get().load()
    } catch (err) {
      toast.error(`${action} failed: ${apiError(err)}`)
    }
  },

  runTriage: async () => {
    try {
      const r = await scannerService.triage()
      toast.success(`AI triage started on ${r.count} findings (${r.batches} batches)`)
    } catch (err) {
      toast.error(`Triage failed: ${apiError(err)}`)
    }
  },

  handleWsEvent: (event, data) => {
    if (event === 'scan_finding') {
      const finding = data as Finding
      set((s) => ({ findings: [finding, ...s.findings] }))
    } else if (event === 'scan_progress') {
      const p = data as ScanProgressEvent
      set((s) => ({ progress: { ...s.progress, [p.scan_id]: p } }))
      if (p.status === 'completed' || p.status === 'failed' || p.status === 'stopped') {
        void get().load()
      }
    } else if (event === 'ai_triage_progress') {
      set({ triageProgress: data as { done: number; total: number; tagged: number } })
    } else if (event === 'ai_triage_done') {
      const d = data as { done: number; total: number; tagged: number }
      toast.success(`AI triage finished — ${d.tagged}/${d.total} findings tagged`)
      set({ triageProgress: null })
      void get().load()
    }
  },
}))

export type { NewRequestEvent }
