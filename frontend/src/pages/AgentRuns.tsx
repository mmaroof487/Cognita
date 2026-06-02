import { useQuery } from '@tanstack/react-query'
import { Card, Skeleton, Badge, EmptyState } from '../components/UI'
import { Search, GitBranch, Cpu, MessageSquare, Ticket, Clock, CheckCircle2 } from 'lucide-react'

export function AgentRuns({ token, orgId }: { token: string, orgId: string }) {
  const { data: runsData, isLoading } = useQuery({
    queryKey: ['runs', orgId],
    queryFn: () => fetch(`/api/v1/orgs/${orgId}/agent-runs`, { 
      headers: { 'Authorization': `Bearer ${token}` } 
    }).then(res => res.json())
  })

  const runs = runsData?.items || []

  // Get the most recent run for the pipeline visualization
  const activeRun = runs.length > 0 ? runs[0] : null
  
  // Pipeline stages
  const stages = [
    { id: 'collector', name: 'Collector', icon: Search, desc: 'Gathering context' },
    { id: 'analyst', name: 'Analyst', icon: Cpu, desc: 'Processing data' },
    { id: 'insight', name: 'Insight Gen', icon: MessageSquare, desc: 'Formulating findings' },
    { id: 'action', name: 'Action Gen', icon: Ticket, desc: 'Creating tickets/alerts' },
  ]

  return (
    <div className="p-8 max-w-5xl mx-auto w-full animate-fade-in pb-20">
      <header className="mb-10">
        <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Agent Runs</h1>
        <p className="text-[var(--color-muted)]">Real-time pipeline execution and historical runs.</p>
      </header>

      {/* Pipeline Visualization */}
      <h2 className="text-xl font-bold text-white mb-4">Latest Pipeline</h2>
      <Card className="mb-10 overflow-hidden relative" glow>
        {/* Connection line behind nodes */}
        <div className="absolute top-1/2 left-10 right-10 h-0.5 bg-[var(--color-border)] -translate-y-1/2 z-0"></div>
        
        <div className="relative z-10 grid grid-cols-4 gap-4">
          {stages.map((stage, i) => {
            // Mocking status based on the active run's status for demo purposes
            // In reality, this would come from the LangGraph state
            let status = 'pending'
            if (activeRun) {
              if (activeRun.status === 'completed') status = 'completed'
              else if (activeRun.status === 'failed') status = i === 2 ? 'failed' : 'completed' // Mock failure
              else if (activeRun.status === 'running') status = i === 1 ? 'running' : i < 1 ? 'completed' : 'pending' // Mock running state
            }
            
            const isRunning = status === 'running'
            const isCompleted = status === 'completed'
            const isFailed = status === 'failed'

            return (
              <div key={stage.id} className="flex flex-col items-center">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-4 border transition-all duration-500 relative
                  ${isCompleted ? 'bg-[var(--color-success)]/10 border-[var(--color-success)]/30 text-[var(--color-success)]' : 
                    isFailed ? 'bg-[var(--color-critical)]/10 border-[var(--color-critical)]/30 text-[var(--color-critical)]' : 
                    isRunning ? 'bg-[var(--color-accent)]/20 border-[var(--color-accent)] text-[var(--color-accent)] shadow-[0_0_20px_rgba(139,92,246,0.3)]' : 
                    'bg-[var(--color-surface)] border-[var(--color-border)] text-[var(--color-muted)]'
                  }`}
                >
                  {isRunning && (
                    <div className="absolute inset-0 rounded-2xl border-2 border-[var(--color-accent)] animate-ping opacity-20"></div>
                  )}
                  <stage.icon className={`w-7 h-7 ${isRunning ? 'animate-pulse' : ''}`} />
                  
                  {isCompleted && (
                    <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-[var(--color-background)] rounded-full flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 text-[var(--color-success)]" />
                    </div>
                  )}
                </div>
                <h3 className={`font-semibold text-sm mb-1 ${isRunning ? 'text-[var(--color-accent)]' : isCompleted ? 'text-white' : 'text-[var(--color-muted)]'}`}>
                  {stage.name}
                </h3>
                <p className="text-xs text-[var(--color-muted)] text-center">{stage.desc}</p>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Timeline View */}
      <h2 className="text-xl font-bold text-white mb-4">Run History</h2>
      
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-20 w-full" />)}
        </div>
      ) : runs.length === 0 ? (
        <EmptyState 
          icon={GitBranch}
          title="No agent runs found"
          description="Trigger a manual run from the dashboard to start analyzing your repositories."
        />
      ) : (
        <div className="relative border-l border-[var(--color-border)] ml-4 pl-8 space-y-6">
          {runs.map((run: any, i: number) => {
            const isSuccess = run.status === 'completed'
            const isFailed = run.status === 'failed'
            
            return (
              <div 
                key={run.id} 
                className="relative animate-[slide-up_0.4s_ease-out_forwards] opacity-0"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                {/* Timeline Dot */}
                <div className={`absolute -left-[41px] top-4 w-4 h-4 rounded-full border-2 border-[var(--color-background)] 
                  ${isSuccess ? 'bg-[var(--color-success)]' : 
                    isFailed ? 'bg-[var(--color-critical)]' : 
                    'bg-[var(--color-accent)] animate-pulse'
                  }`}
                />
                
                <Card className="hover:border-[var(--color-accent)]/30 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-3">
                      <h3 className="text-base font-semibold text-white uppercase tracking-wider text-sm">
                        Run {run.id.substring(0, 8)}
                      </h3>
                      <Badge variant={
                        isSuccess ? 'success' : 
                        isFailed ? 'critical' : 
                        'accent'
                      }>
                        {run.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-1.5 text-sm text-[var(--color-muted)]">
                      <Clock className="w-4 h-4" />
                      <span>{new Date(run.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4 mt-4">
                    <div className="bg-[var(--color-surface)] px-3 py-1.5 rounded border border-[var(--color-border)] text-sm text-[var(--color-muted)] flex items-center gap-2">
                      <span className="font-medium text-[var(--color-text)]">Trigger:</span> {run.triggered_by}
                    </div>
                    <div className="bg-[var(--color-surface)] px-3 py-1.5 rounded border border-[var(--color-border)] text-sm text-[var(--color-muted)] flex items-center gap-2">
                      <span className="font-medium text-[var(--color-text)]">Duration:</span> 45s
                    </div>
                  </div>
                </Card>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
