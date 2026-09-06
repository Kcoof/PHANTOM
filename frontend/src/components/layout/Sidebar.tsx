import { NavLink } from 'react-router-dom'
import {
  Activity,
  BrainCircuit,
  Lock,
  Radar,
  Repeat2,
  Settings,
  Shield,
} from 'lucide-react'
import { useProxyStore } from '../../stores/proxyStore'

const ITEMS = [
  { to: '/', label: 'Dashboard', icon: Activity },
  { to: '/proxy', label: 'Proxy', icon: Shield },
  { to: '/repeater', label: 'Repeater', icon: Repeat2 },
  { to: '/scanner', label: 'Scanner', icon: Radar },
  { to: '/decoder', label: 'Decoder', icon: Lock },
  { to: '/copilot', label: 'AI Copilot', icon: BrainCircuit },
]

export function Sidebar() {
  const wsConnected = useProxyStore((s) => s.wsConnected)
  const proxyRunning = useProxyStore((s) => s.status?.running ?? false)

  return (
    <nav
      style={{
        width: 56,
        flex: '0 0 auto',
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border-primary)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '10px 0',
        gap: 4,
      }}
    >
      {ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          title={label}
          style={({ isActive }) => ({
            width: 40,
            height: 40,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 'var(--radius-md)',
            color: isActive ? '#fff' : 'var(--text-secondary)',
            background: isActive ? 'var(--accent-primary)' : 'transparent',
            boxShadow: isActive ? '0 0 12px var(--accent-glow)' : 'none',
            transition: 'all var(--transition-fast)',
          })}
          onMouseEnter={(e) => {
            if (!e.currentTarget.classList.contains('active'))
              e.currentTarget.style.background = 'var(--bg-hover)'
          }}
          onMouseLeave={(e) => {
            if (!e.currentTarget.classList.contains('active'))
              e.currentTarget.style.background = 'transparent'
          }}
        >
          <Icon size={18} />
        </NavLink>
      ))}
      <div style={{ flex: 1 }} />
      <NavLink
        to="/settings"
        title="Settings"
        style={({ isActive }) => ({
          width: 40,
          height: 40,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 'var(--radius-md)',
          color: isActive ? '#fff' : 'var(--text-secondary)',
          background: isActive ? 'var(--accent-primary)' : 'transparent',
        })}
      >
        <Settings size={18} />
      </NavLink>
      <div
        title={wsConnected ? 'Live events connected' : 'Live events disconnected'}
        className={wsConnected ? 'pulse-dot' : ''}
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          margin: '8px 0 2px',
          background: wsConnected
            ? proxyRunning
              ? 'var(--severity-low)'
              : 'var(--severity-info)'
            : 'var(--severity-critical)',
        }}
      />
    </nav>
  )
}
