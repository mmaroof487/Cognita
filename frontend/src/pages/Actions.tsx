import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Skeleton, Badge, EmptyState } from '../components/UI'
import { CheckCircle2, XCircle, Hash, Ticket, AlertCircle } from 'lucide-react'

export function Actions({ token, orgId }: { token: string, orgId: string }) {
  const [activeTab, setActiveTab] = useState<'pending' | 'approved' | 'rejected'>('pending')
  const queryClient = useQueryClient()
  const headers = { 'Authorization': `Bearer ${token}` }

  const { data: actions = [], isLoading } = useQuery({
    queryKey: ['actions', orgId],
    queryFn: () => fetch(`/api/v1/orgs/${orgId}/actions`, { headers }).then(res => res.json()).then(d => d.items || [])
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => fetch(`/api/v1/actions/${id}/approve`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions', orgId] })
    }
  })

  const rejectMutation = useMutation({
    mutationFn: (id: string) => fetch(`/api/v1/actions/${id}/reject`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: "User rejected" })
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions', orgId] })
    }
  })

  // Filter actions based on tab (assuming status field exists, if not just show all in pending for demo)
  const filteredActions = actions.filter((a: any) => {
    const status = a.status || 'pending'
    return status === activeTab
  })

  return (
    <div className="p-8 max-w-5xl mx-auto w-full animate-fade-in pb-20">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Actions</h1>
        <p className="text-[var(--color-muted)]">Review and approve AI-generated notifications and tickets.</p>
      </header>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-8 bg-[var(--color-surface)] p-1.5 rounded-lg border border-[var(--color-border)] w-fit">
        {['pending', 'approved', 'rejected'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab as any)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              activeTab === tab 
                ? 'bg-[var(--color-card)] text-white shadow-sm border border-[var(--color-border)]' 
                : 'text-[var(--color-muted)] hover:text-white hover:bg-[var(--color-card)]/50 border border-transparent'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === 'pending' && (
              <span className="ml-2 px-1.5 py-0.5 rounded-full bg-[var(--color-accent)]/20 text-[var(--color-accent)] text-xs">
                {actions.filter((a: any) => (a.status || 'pending') === 'pending').length}
              </span>
            )}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map(i => <Skeleton key={i} className="h-40 w-full" />)}
        </div>
      ) : filteredActions.length === 0 ? (
        <EmptyState 
          icon={CheckCircle2}
          title={`No ${activeTab} actions`}
          description={activeTab === 'pending' ? 'All caught up! No actions require your approval right now.' : `You haven't ${activeTab} any actions yet.`}
        />
      ) : (
        <div className="grid gap-6">
          {filteredActions.map((action: any, i: number) => {
            const isSlack = action.action_type === 'send_slack'
            
            return (
              <Card 
                key={action.id} 
                className="flex flex-col md:flex-row gap-6 items-start hover:border-[var(--color-accent)]/40 transition-all duration-300 transform hover:-translate-y-1 relative overflow-hidden"
                style={{ animationDelay: `${i * 100}ms` }}
                glow
              >
                {/* Decorative side accent */}
                <div className={`absolute left-0 top-0 bottom-0 w-1 ${isSlack ? 'bg-[#E01E5A]' : 'bg-[#0052CC]'}`}></div>
                
                <div className="flex-1 pl-2">
                  <div className="flex items-center gap-3 mb-3">
                    <span className={`px-2.5 py-1 text-xs font-semibold rounded-md flex items-center gap-1.5
                      ${isSlack ? 'bg-[#E01E5A]/10 text-[#E01E5A] border border-[#E01E5A]/20' : 'bg-[#0052CC]/10 text-[#0052CC] border border-[#0052CC]/20'}`}
                    >
                      {isSlack ? <Hash className="w-3.5 h-3.5" /> : <Ticket className="w-3.5 h-3.5" />}
                      {action.action_type.replace('_', ' ').toUpperCase()}
                    </span>
                    <Badge variant={action.severity === 'high' ? 'critical' : action.severity === 'medium' ? 'warning' : 'success'}>
                      {action.severity || 'Medium'} Severity
                    </Badge>
                  </div>
                  
                  <h3 className="text-lg font-bold text-white mb-2">{action.payload?.title || 'Action Required'}</h3>
                  <p className="text-[var(--color-muted)] text-sm mb-4 bg-[var(--color-surface)] p-3 rounded-md border border-[var(--color-border)]">
                    {action.payload?.message || action.payload?.detail}
                  </p>
                  
                  <div className="flex items-center gap-2 text-xs text-[var(--color-muted)] font-mono">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Reason: Discovered critical insight in analysis phase</span>
                  </div>
                </div>
                
                {activeTab === 'pending' && (
                  <div className="flex md:flex-col items-center gap-3 w-full md:w-40 mt-4 md:mt-0 pt-4 md:pt-0 border-t md:border-t-0 md:border-l border-[var(--color-border)] md:pl-6">
                    <button 
                      onClick={() => approveMutation.mutate(action.id)}
                      disabled={approveMutation.isPending || rejectMutation.isPending}
                      className="flex-1 md:w-full px-4 py-2.5 rounded-lg font-medium text-[var(--color-success)] bg-[var(--color-success)]/10 hover:bg-[var(--color-success)]/20 border border-[var(--color-success)]/20 transition-all flex items-center justify-center gap-2 hover:shadow-[0_0_15px_rgba(34,197,94,0.2)] disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-4 h-4" /> Approve
                    </button>
                    <button 
                      onClick={() => rejectMutation.mutate(action.id)}
                      disabled={approveMutation.isPending || rejectMutation.isPending}
                      className="flex-1 md:w-full px-4 py-2.5 rounded-lg font-medium text-[var(--color-critical)] bg-[var(--color-critical)]/10 hover:bg-[var(--color-critical)]/20 border border-[var(--color-critical)]/20 transition-all flex items-center justify-center gap-2 hover:shadow-[0_0_15px_rgba(239,68,68,0.2)] disabled:opacity-50"
                    >
                      <XCircle className="w-4 h-4" /> Reject
                    </button>
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
