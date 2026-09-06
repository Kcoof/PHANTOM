import { useEffect } from 'react'
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { MainLayout } from './components/layout/MainLayout'
import { ProxyView } from './components/proxy/ProxyView'
import { ModulePlaceholder } from './components/shared/ModulePlaceholder'
import { usePhantomWebSocket } from './hooks/useWebSocket'
import { useProxyStore } from './stores/proxyStore'

function AppShell() {
  usePhantomWebSocket()
  const refreshStatus = useProxyStore((s) => s.refreshStatus)

  useEffect(() => {
    void refreshStatus()
  }, [refreshStatus])

  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<ModulePlaceholder title="Dashboard" note="Analytics arrive in US5 — traffic charts, severity donut, detected technologies." />} />
        <Route path="/proxy" element={<ProxyView />} />
        <Route path="/repeater" element={<ModulePlaceholder title="Repeater" note="Request replay lands in US2 — Monaco editor, tabs, response views." />} />
        <Route path="/scanner" element={<ModulePlaceholder title="Scanner" note="Vulnerability scanning lands in US3 — 10 passive/active checks." />} />
        <Route path="/decoder" element={<ModulePlaceholder title="Decoder" note="Encode/decode/hash toolkit lands in US6." />} />
        <Route path="/copilot" element={<ModulePlaceholder title="AI Copilot" note="AI assistant lands in US4 — streamed analysis with a local model runtime." />} />
        <Route path="/settings" element={<ModulePlaceholder title="Settings" note="Settings & scope rules land in the polish phase." />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </MainLayout>
  )
}

export default function App() {
  return (
    <HashRouter>
      <AppShell />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: 'var(--bg-tertiary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-active)',
            fontSize: 12,
          },
        }}
      />
    </HashRouter>
  )
}
