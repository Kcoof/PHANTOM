import { Power, Radio, Shield } from 'lucide-react'
import { useProxyStore } from '../../stores/proxyStore'

export function TopBar() {
  const status = useProxyStore((s) => s.status)
  const startProxy = useProxyStore((s) => s.startProxy)
  const stopProxy = useProxyStore((s) => s.stopProxy)
  const running = status?.running ?? false

  return (
    <header
      style={{
        height: 42,
        flex: '0 0 auto',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '0 14px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-primary)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Shield size={16} color="var(--accent-primary)" />
        <span style={{ fontWeight: 700, letterSpacing: 1.5, fontSize: 13 }}>PHANTOM</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>v1.0.0</span>
      </div>
      <div style={{ flex: 1 }} />
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 11,
          color: running ? 'var(--severity-low)' : 'var(--text-muted)',
        }}
      >
        <Radio size={13} className={running ? 'pulse-dot' : ''} />
        Proxy: {running ? `Running :${status?.port}` : 'Stopped'}
      </div>
      <button className={`btn sm ${running ? 'danger' : 'primary'}`} onClick={() => (running ? stopProxy() : startProxy())}>
        <Power size={12} />
        {running ? 'Stop' : 'Start'}
      </button>
    </header>
  )
}
