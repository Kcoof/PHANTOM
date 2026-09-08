import { useEffect } from 'react'
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { loader } from '@monaco-editor/react'
import { MainLayout } from './components/layout/MainLayout'
import { ProxyView } from './components/proxy/ProxyView'
import { RepeaterView } from './components/repeater/RepeaterView'
import { IntruderView } from './components/intruder/IntruderView'
import { SearchView } from './components/search/SearchView'
import { ScannerView } from './components/scanner/ScannerView'
import { PluginsView } from './components/plugins/PluginsView'
import { CopilotView } from './components/copilot/CopilotView'
import { DashboardView } from './components/dashboard/DashboardView'
import { DecoderView } from './components/decoder/DecoderView'
import { SettingsView } from './components/settings/SettingsView'
import { usePhantomWebSocket } from './hooks/useWebSocket'
import { useProxyStore } from './stores/proxyStore'

function AppShell() {
  usePhantomWebSocket()
  const refreshStatus = useProxyStore((s) => s.refreshStatus)

  useEffect(() => {
    void refreshStatus()
    // Preload Monaco in the background so opening the Repeater is instant
    void loader.init()
  }, [refreshStatus])

  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<DashboardView />} />
        <Route path="/proxy" element={<ProxyView />} />
        <Route path="/repeater" element={<RepeaterView />} />
        <Route path="/intruder" element={<IntruderView />} />
        <Route path="/search" element={<SearchView />} />
        <Route path="/scanner" element={<ScannerView />} />
        <Route path="/plugins" element={<PluginsView />} />
        <Route path="/decoder" element={<DecoderView />} />
        <Route path="/copilot" element={<CopilotView />} />
        <Route path="/settings" element={<SettingsView />} />
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
