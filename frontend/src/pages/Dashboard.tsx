import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, Skeleton, Badge, EmptyState } from '../components/UI'
import { Activity, GitMerge, ShieldAlert, Cpu, CheckCircle2, AlertTriangle, TrendingUp, TrendingDown, Bell } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const MOCK_TREND_DATA = [
  { name: 'Mon', health: 82 },
  { name: 'Tue', health: 85 },
  { name: 'Wed', health: 84 },
  { name: 'Thu', health: 89 },
  { name: 'Fri', health: 92 },
  { name: 'Sat', health: 91 },
  { name: 'Sun', health: 94 },
]

const COLORS = {
  healthy: 'var(--color-success)',
  warning: 'var(--color-warning)',
  critical: 'var(--color-critical)'
}

export function Dashboard({ token, orgId }: { token: string, orgId: string }) {
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null)

  const headers = { 'Authorization': `Bearer ${token}` }

  const { data: insights = [], isLoading: loadingInsights } = useQuery({
    queryKey: ['insights', orgId],
    queryFn: () => fetch(`/api/v1/orgs/${orgId}/insights`, { headers }).then(res => res.json()).then(d => d.items || [])
  })

  const { isLoading: loadingOrg } = useQuery({
    queryKey: ['org', orgId],
    queryFn: () => fetch(`/api/v1/orgs/${orgId}`, { headers }).then(res => res.json())
  })

  const { isLoading: loadingRuns } = useQuery({
    queryKey: ['runs', orgId],
    queryFn: () => fetch(`/api/v1/orgs/${orgId}/agent-runs?limit=1`, { headers }).then(res => res.json())
  })

  const { data: actions = [], isLoading: loadingActions } = useQuery({
    queryKey: ['actions', orgId],
    queryFn: () => fetch(`/api/v1/orgs/${orgId}/actions`, { headers }).then(res => res.json()).then(d => d.items || [])
  })

  const triggerRun = useMutation({
    mutationFn: () => fetch(`/api/v1/orgs/${orgId}/agent-runs`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ triggered_by: 'manual' })
    }).then(res => res.json()),
    onSuccess: (data) => {
      setNotification({ message: `Started agent run: ${data.run_id}`, type: 'success' });
      setTimeout(() => setNotification(null), 4000);
    },
    onError: () => {
      setNotification({ message: 'Failed to trigger run', type: 'error' });
      setTimeout(() => setNotification(null), 4000);
    }
  })

  const loading = loadingInsights || loadingOrg || loadingRuns || loadingActions
  // Stats formatting
  const pendingActions = actions.length

  // Calculate mock risk distribution based on insights for demonstration
  const highRiskCount = insights.filter((i: any) => i.severity === 'high').length
  const mediumRiskCount = insights.filter((i: any) => i.severity === 'medium').length
  const lowRiskCount = Math.max(10, insights.filter((i: any) => i.severity === 'low').length)
  
  const riskData = [
    { name: 'Healthy', value: lowRiskCount, color: COLORS.healthy },
    { name: 'Warning', value: mediumRiskCount, color: COLORS.warning },
    { name: 'Critical', value: highRiskCount, color: COLORS.critical },
  ]

  return (
    <div className="p-8 max-w-7xl mx-auto w-full animate-fade-in pb-20">
      <header className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Executive Dashboard</h1>
          <p className="text-[var(--color-muted)]">Real-time overview of your engineering organization.</p>
        </div>
        <button 
          onClick={() => triggerRun.mutate()}
          disabled={triggerRun.isPending}
          className="bg-[var(--color-accent)] hover:bg-purple-500 text-white px-5 py-2 rounded-lg font-medium transition-colors shadow-[0_0_15px_rgba(139,92,246,0.3)] flex items-center gap-2 disabled:opacity-50"
        >
          <Activity className="w-4 h-4" /> {triggerRun.isPending ? 'Starting...' : 'Trigger Run'}
        </button>
      </header>

      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-6 right-6 px-6 py-4 rounded-xl shadow-2xl border backdrop-blur-md z-50 animate-[slide-up_0.3s_ease-out] flex items-center gap-3 ${
          notification.type === 'success' 
            ? 'bg-[var(--color-success)]/10 border-[var(--color-success)]/30 text-[var(--color-success)]'
            : 'bg-[var(--color-critical)]/10 border-[var(--color-critical)]/30 text-[var(--color-critical)]'
        }`}>
          {notification.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
          <span className="font-medium text-sm">{notification.message}</span>
        </div>
      )}

      {/* ROW 1: Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="animate-[slide-up_0.2s_ease-out_forwards] opacity-0" glow>
          <div className="flex justify-between items-start mb-4">
            <p className="text-sm text-[var(--color-muted)] font-medium">Team Health</p>
            <div className="p-2 bg-[var(--color-success)]/10 text-[var(--color-success)] rounded-md">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-end gap-3">
            <p className="text-3xl font-bold text-white">92%</p>
            <span className="text-sm text-[var(--color-success)] flex items-center mb-1">
              <TrendingUp className="w-3 h-3 mr-1" /> +2.4%
            </span>
          </div>
        </Card>
        
        <Card className="animate-[slide-up_0.3s_ease-out_forwards] opacity-0" glow>
          <div className="flex justify-between items-start mb-4">
            <p className="text-sm text-[var(--color-muted)] font-medium">Developers Tracked</p>
            <div className="p-2 bg-[var(--color-accent)]/10 text-[var(--color-accent)] rounded-md">
              <GitMerge className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-end gap-3">
            <div className="text-3xl font-bold text-white">
              {loading ? <Skeleton className="h-9 w-12" /> : '24'}
            </div>
            <span className="text-sm text-[var(--color-muted)] flex items-center mb-1">
              Active today
            </span>
          </div>
        </Card>

        <Card className="animate-[slide-up_0.4s_ease-out_forwards] opacity-0" glow>
          <div className="flex justify-between items-start mb-4">
            <p className="text-sm text-[var(--color-muted)] font-medium">Critical Insights</p>
            <div className="p-2 bg-[var(--color-critical)]/10 text-[var(--color-critical)] rounded-md">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-end gap-3">
            <div className="text-3xl font-bold text-white">
              {loading ? <Skeleton className="h-9 w-8" /> : highRiskCount}
            </div>
            <span className="text-sm text-[var(--color-critical)] flex items-center mb-1">
              <TrendingDown className="w-3 h-3 mr-1" /> Needs attention
            </span>
          </div>
        </Card>

        <Card className="animate-[slide-up_0.5s_ease-out_forwards] opacity-0" glow>
          <div className="flex justify-between items-start mb-4">
            <p className="text-sm text-[var(--color-muted)] font-medium">Pending Actions</p>
            <div className="p-2 bg-[var(--color-warning)]/10 text-[var(--color-warning)] rounded-md">
              <Bell className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-end gap-3">
            <div className="text-3xl font-bold text-white">
              {loading ? <Skeleton className="h-9 w-8" /> : pendingActions}
            </div>
            <span className="text-sm text-[var(--color-warning)] flex items-center mb-1">
              Awaiting approval
            </span>
          </div>
        </Card>
      </div>

      {/* ROW 2 & 3: Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card className="lg:col-span-2 h-[400px] flex flex-col" glow>
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-white">Health Trend</h3>
            <p className="text-sm text-[var(--color-muted)]">7-day rolling average of organization health</p>
          </div>
          <div className="flex-1 min-h-0 w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_TREND_DATA} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorHealth" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-success)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--color-success)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--color-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--color-muted)" fontSize={12} tickLine={false} axisLine={false} domain={[60, 100]} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--color-text)' }}
                />
                <Area type="monotone" dataKey="health" stroke="var(--color-success)" strokeWidth={3} fillOpacity={1} fill="url(#colorHealth)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="h-[400px] flex flex-col" glow>
          <div className="mb-2">
            <h3 className="text-lg font-semibold text-white">Risk Distribution</h3>
            <p className="text-sm text-[var(--color-muted)]">Insights by severity level</p>
          </div>
          <div className="flex-1 min-h-0 w-full flex items-center justify-center relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskData}
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {riskData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--color-text)' }}
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Center Label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-3xl font-bold text-white">{insights.length || 0}</span>
              <span className="text-xs text-[var(--color-muted)]">Total</span>
            </div>
          </div>
        </Card>
      </div>

      {/* ROW 4: Insight Feed */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">Recent Insights Feed</h2>
          <button className="text-sm text-[var(--color-accent)] hover:text-purple-400 transition-colors">View All</button>
        </div>
        
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        ) : insights.length === 0 ? (
          <EmptyState 
            icon={ShieldAlert} 
            title="No insights found" 
            description="Your organization is currently healthy. Run an agent analysis to discover new insights." 
          />
        ) : (
          <div className="space-y-3">
            {insights.slice(0, 5).map((insight: any, i: number) => {
              const isHigh = insight.severity === 'high'
              const isMedium = insight.severity === 'medium'
              const severityColor = isHigh ? 'critical' : isMedium ? 'warning' : 'success'
              
              return (
                <Card 
                  key={insight.id} 
                  className="flex items-start gap-4 p-5 animate-[slide-up_0.4s_ease-out_forwards] opacity-0 hover:bg-[var(--color-card)]/80"
                  style={{ animationDelay: `${i * 100}ms` }}
                >
                  <div className={`mt-0.5 p-2 rounded-full border ${
                    isHigh ? 'bg-[var(--color-critical)]/10 text-[var(--color-critical)] border-[var(--color-critical)]/20' :
                    isMedium ? 'bg-[var(--color-warning)]/10 text-[var(--color-warning)] border-[var(--color-warning)]/20' :
                    'bg-[var(--color-success)]/10 text-[var(--color-success)] border-[var(--color-success)]/20'
                  }`}>
                    {isHigh ? <AlertTriangle className="w-5 h-5" /> : 
                     isMedium ? <AlertTriangle className="w-5 h-5" /> : 
                     <CheckCircle2 className="w-5 h-5" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start mb-1">
                      <h3 className="text-base font-semibold text-white truncate pr-4">{insight.title}</h3>
                      <Badge variant={severityColor as any} className="shrink-0 uppercase tracking-wider text-[10px]">
                        {insight.severity}
                      </Badge>
                    </div>
                    <p className="text-sm text-[var(--color-muted)] line-clamp-2 mb-3">{insight.body}</p>
                    <div className="flex items-center gap-3 text-xs font-mono text-[var(--color-muted)]">
                      <span className="flex items-center gap-1.5"><GitMerge className="w-3.5 h-3.5" /> backend-api</span>
                      <span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5" /> {insight.insight_type}</span>
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
