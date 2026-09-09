import { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  Clock,
  Globe,
  Layers,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { dashboardService, type DashboardStats } from '../../services/dashboardService'
import { SeverityBadge } from '../shared/Badge'
import { LoadingSpinner } from '../shared/LoadingSpinner'

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ff3838',
  high: '#ff6b35',
  medium: '#ffc107',
  low: '#00b894',
  info: '#74b9ff',
}

export function DashboardView() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [traffic, setTraffic] = useState<Array<{ bucket: string; count: number }>>([])
  const [tech, setTech] = useState<Array<{ technology: string; hosts: string[] }>>([])
  const [interval, setIntervalSel] = useState<'minute' | 'hour' | 'day'>('minute')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void (async () => {
      setLoading(true)
      try {
        const [s, t, tech] = await Promise.all([
          dashboardService.stats(),
          dashboardService.traffic('minute'),
          dashboardService.technologies(),
        ])
        setStats(s)
        setTraffic(t)
        setTech(tech)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  useEffect(() => {
    void dashboardService.traffic(interval).then(setTraffic)
  }, [interval])

  if (loading && !stats) return <LoadingSpinner label="Crunching your session data…" />

  const pieData = stats
    ? Object.entries(stats.findings_by_severity)
        .filter(([, v]) => v > 0)
        .map(([name, value]) => ({ name, value }))
    : []

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Activity size={16} color="var(--accent-primary)" />
        <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: 0.5 }}>Dashboard</span>
      </div>

      {/* stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
        <StatCard icon={<Globe size={15} />} label="Total requests" value={stats?.total_requests ?? 0} to="/proxy" />
        <StatCard icon={<AlertTriangle size={15} color="var(--severity-high)" />} label="Findings" value={stats?.total_findings ?? 0} to="/scanner" />
        <StatCard icon={<Clock size={15} color="var(--accent-secondary)" />} label="Avg response" value={`${stats?.avg_response_time_ms ?? 0} ms`} to="/target" />
        <StatCard icon={<Layers size={15} color="var(--severity-info)" />} label="Technologies" value={tech.length} to="/target" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
        {/* traffic chart */}
        <div className="panel" style={{ padding: 12, height: 240 }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)' }}>TRAFFIC</span>
            <div style={{ flex: 1 }} />
            {(['minute', 'hour', 'day'] as const).map((i) => (
              <button
                key={i}
                className={`btn sm ghost ${interval === i ? 'primary' : ''}`}
                onClick={() => setIntervalSel(i)}
              >
                {i}
              </button>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={traffic}>
              <defs>
                <linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6c5ce7" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="#6c5ce7" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <XAxis dataKey="bucket" tick={{ fill: '#8888a8', fontSize: 9 }} tickLine={false} axisLine={{ stroke: '#2a2a3e' }} />
              <YAxis tick={{ fill: '#8888a8', fontSize: 9 }} tickLine={false} axisLine={false} width={28} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#1a1a2e', border: '1px solid #4a4a6e', borderRadius: 8, fontSize: 11 }}
                labelStyle={{ color: '#e8e8f0' }}
              />
              <Area type="monotone" dataKey="count" stroke="#6c5ce7" strokeWidth={2} fill="url(#tg)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* severity donut */}
        <div className="panel" style={{ padding: 12, height: 240 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 8 }}>FINDINGS BY SEVERITY</div>
          {pieData.length ? (
            <ResponsiveContainer width="100%" height={190}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={70} paddingAngle={3} strokeWidth={0}>
                  {pieData.map((d) => (
                    <Cell key={d.name} fill={SEVERITY_COLORS[d.name] ?? '#555570'} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #4a4a6e', borderRadius: 8, fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 190, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 11 }}>
              No findings yet
            </div>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {/* top hosts */}
        <div className="panel" style={{ padding: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 8 }}>TOP HOSTS</div>
          {(stats?.top_hosts ?? []).map((h) => (
            <div key={h.host} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <Globe size={11} color="var(--text-muted)" />
              <span className="mono" style={{ fontSize: 11.5, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{h.host}</span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{h.count}</span>
            </div>
          ))}
          {!stats?.top_hosts.length && <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>No traffic yet</div>}
        </div>

        {/* technologies */}
        <div className="panel" style={{ padding: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 8 }}>DETECTED TECHNOLOGIES</div>
          {tech.map((t) => (
            <div key={t.technology} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <Layers size={11} color="var(--severity-info)" />
              <span className="mono" style={{ fontSize: 11.5, flex: 1 }}>{t.technology}</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{t.hosts.join(', ').slice(0, 40)}</span>
            </div>
          ))}
          {!tech.length && <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>None detected yet</div>}
        </div>
      </div>

      {/* severity legend */}
      {stats && stats.total_findings > 0 && (
        <div className="panel" style={{ padding: 12, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          {Object.entries(stats.findings_by_severity).map(([sev, count]) => (
            <div key={sev} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <SeverityBadge severity={sev} />
              <span style={{ fontSize: 12, fontWeight: 600 }}>{count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function StatCard({ icon, label, value, to }: { icon: React.ReactNode; label: string; value: string | number; to?: string }) {
  const inner = (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)', fontSize: 11 }}>{icon} {label}</div>
      <div style={{ fontSize: 24, fontWeight: 700 }}>{typeof value === 'number' ? value.toLocaleString() : value}</div>
    </>
  )
  if (to) {
    return (
      <a
        href={`#${to}`}
        className="panel fade-in"
        style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 6, textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
        onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--border-active)')}
        onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-primary)')}
      >
        {inner}
      </a>
    )
  }
  return (
    <div className="panel fade-in" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>{inner}</div>
  )
}
