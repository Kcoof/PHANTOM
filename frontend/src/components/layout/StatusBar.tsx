import { useProxyStore } from '../../stores/proxyStore'

export function StatusBar() {
  const status = useProxyStore((s) => s.status)
  const total = useProxyStore((s) => s.total)
  const ws = useProxyStore((s) => s.wsConnected)
  const running = status?.running ?? false

  const cell: React.CSSProperties = {
    padding: '0 12px',
    borderRight: '1px solid var(--border-primary)',
    color: 'var(--text-secondary)',
    fontSize: 11,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    height: '100%',
  }

  return (
    <footer
      style={{
        height: 24,
        flex: '0 0 auto',
        display: 'flex',
        alignItems: 'stretch',
        background: 'var(--bg-secondary)',
        borderTop: '1px solid var(--border-primary)',
      }}
    >
      <div style={cell}>
        <span
          className={running ? 'pulse-dot' : ''}
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: running ? 'var(--severity-low)' : 'var(--text-muted)',
          }}
        />
        Proxy: {running ? `${status?.host}:${status?.port}` : 'off'}
      </div>
      <div style={cell}>Requests: {status?.requests_captured ?? 0}</div>
      <div style={cell}>History: {total.toLocaleString()}</div>
      <div style={cell}>Intercept: {status?.intercept_enabled ? 'ON' : 'off'}</div>
      <div style={{ ...cell, borderRight: 'none', marginLeft: 'auto' }}>
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: ws ? 'var(--severity-low)' : 'var(--severity-critical)',
          }}
        />
        Live: {ws ? 'connected' : 'reconnecting…'}
      </div>
    </footer>
  )
}
