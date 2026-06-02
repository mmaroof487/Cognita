import { useQuery } from '@tanstack/react-query'
import { Card, Skeleton, Badge, EmptyState } from '../components/UI'
import { Users, GitPullRequest, GitCommit, Activity, ShieldAlert } from 'lucide-react'

// Simple SVG Circular Progress Component
function CircularProgress({ value, color }: { value: number, color: string }) {
  const radius = 28
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (value / 100) * circumference

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg className="w-20 h-20 transform -rotate-90">
        <circle
          className="text-[var(--color-surface)]"
          strokeWidth="6"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="40"
          cy="40"
        />
        <circle
          className="transition-all duration-1000 ease-out"
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          stroke={color}
          fill="transparent"
          r={radius}
          cx="40"
          cy="40"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center text-white">
        <span className="text-xl font-bold">{value}</span>
      </div>
    </div>
  )
}

export function Developers({ token, orgId }: { token: string, orgId: string }) {
  const { data: developers = [], isLoading } = useQuery({
    queryKey: ['developers', orgId],
    queryFn: () => fetch(`/api/v1/orgs/${orgId}/developers`, { 
      headers: { 'Authorization': `Bearer ${token}` } 
    }).then(res => res.json()).then(d => d.items || [])
  })

  // Mock data if API returns empty for demo purposes (as it might not be fully populated)
  const displayDevs = developers.length > 0 ? developers : [
    { id: '1', username: 'alice.dev', health_score: 95, commit_count: 142, pr_count: 24, risk_level: 'low' },
    { id: '2', username: 'bob.engineer', health_score: 72, commit_count: 85, pr_count: 12, risk_level: 'medium' },
    { id: '3', username: 'charlie.code', health_score: 45, commit_count: 12, pr_count: 2, risk_level: 'high' },
    { id: '4', username: 'diana.lead', health_score: 88, commit_count: 210, pr_count: 45, risk_level: 'low' }
  ]

  return (
    <div className="p-8 max-w-6xl mx-auto w-full animate-fade-in pb-20">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Developers</h1>
          <p className="text-[var(--color-muted)]">Track individual performance and risk metrics.</p>
        </div>
        <div className="flex items-center gap-4 bg-[var(--color-surface)] px-4 py-2 rounded-lg border border-[var(--color-border)]">
          <div className="flex flex-col items-end">
            <span className="text-xs text-[var(--color-muted)]">Avg Health</span>
            <span className="text-lg font-bold text-[var(--color-success)]">84%</span>
          </div>
          <div className="w-px h-8 bg-[var(--color-border)]"></div>
          <div className="flex flex-col items-end">
            <span className="text-xs text-[var(--color-muted)]">At Risk</span>
            <span className="text-lg font-bold text-[var(--color-critical)]">1</span>
          </div>
        </div>
      </header>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-64 w-full" />)}
        </div>
      ) : displayDevs.length === 0 ? (
        <EmptyState 
          icon={Users}
          title="No developers found"
          description="Your organization doesn't have any developers tracked yet."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayDevs.map((dev: any, i: number) => {
            const isHighRisk = dev.risk_level === 'high'
            const isMediumRisk = dev.risk_level === 'medium'
            const healthColor = isHighRisk ? 'var(--color-critical)' : isMediumRisk ? 'var(--color-warning)' : 'var(--color-success)'
            
            return (
              <Card 
                key={dev.id || i} 
                className="flex flex-col animate-[slide-up_0.4s_ease-out_forwards] opacity-0"
                style={{ animationDelay: `${i * 100}ms` }}
                glow
              >
                <div className="flex justify-between items-start mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[var(--color-accent)] to-purple-700 flex items-center justify-center text-white font-bold shadow-lg">
                      {dev.username.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white">{dev.username}</h3>
                      <p className="text-xs text-[var(--color-muted)]">Developer</p>
                    </div>
                  </div>
                  <Badge variant={isHighRisk ? 'critical' : isMediumRisk ? 'warning' : 'success'}>
                    {dev.risk_level.toUpperCase()} RISK
                  </Badge>
                </div>

                <div className="flex justify-between items-center mb-6 bg-[var(--color-background)]/50 p-4 rounded-xl border border-[var(--color-border)]/50">
                  <div className="flex flex-col">
                    <span className="text-xs text-[var(--color-muted)] mb-1 flex items-center gap-1">
                      <Activity className="w-3 h-3" /> Health Score
                    </span>
                    {isHighRisk && <span className="text-[10px] text-[var(--color-critical)] mt-1 flex items-center gap-1"><ShieldAlert className="w-3 h-3" /> Needs Review</span>}
                  </div>
                  <CircularProgress value={dev.health_score} color={healthColor} />
                </div>

                <div className="grid grid-cols-2 gap-3 mt-auto">
                  <div className="flex flex-col items-center justify-center p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                    <GitCommit className="w-5 h-5 text-[var(--color-muted)] mb-1" />
                    <span className="text-xl font-bold text-white">{dev.commit_count}</span>
                    <span className="text-xs text-[var(--color-muted)]">Commits</span>
                  </div>
                  <div className="flex flex-col items-center justify-center p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                    <GitPullRequest className="w-5 h-5 text-[var(--color-muted)] mb-1" />
                    <span className="text-xl font-bold text-white">{dev.pr_count}</span>
                    <span className="text-xs text-[var(--color-muted)]">Pull Requests</span>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
