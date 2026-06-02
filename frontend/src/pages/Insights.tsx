import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Skeleton, Badge, EmptyState } from '../components/UI'
import { Search, Filter, ShieldAlert, GitMerge, ChevronRight, Clock } from 'lucide-react'

export function Insights({ token, orgId }: { token: string, orgId: string }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')

  const { data: insights = [], isLoading } = useQuery({
    queryKey: ['insights', orgId],
    queryFn: () => fetch(`/api/v1/orgs/${orgId}/insights`, { 
      headers: { 'Authorization': `Bearer ${token}` } 
    }).then(res => res.json()).then(d => d.items || [])
  })

  const filteredInsights = insights.filter((i: any) => {
    const matchesSearch = i.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          i.body.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesSeverity = severityFilter === 'all' || i.severity === severityFilter
    return matchesSearch && matchesSeverity
  })

  return (
    <div className="p-8 max-w-6xl mx-auto w-full animate-fade-in pb-20">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Insights Explorer</h1>
        <p className="text-[var(--color-muted)]">Search and filter AI-generated code analysis and findings.</p>
      </header>

      {/* Toolbar */}
      <div className="flex flex-col md:flex-row gap-4 mb-8 bg-[var(--color-surface)] p-4 rounded-xl border border-[var(--color-border)] shadow-lg">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-muted)]" />
          <input 
            type="text" 
            placeholder="Search insights by title or content..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
          />
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg px-3 py-1">
            <Filter className="w-4 h-4 text-[var(--color-muted)]" />
            <select 
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-transparent text-sm text-white focus:outline-none py-1 appearance-none cursor-pointer pr-4"
            >
              <option value="all">All Severities</option>
              <option value="high">High Severity</option>
              <option value="medium">Medium Severity</option>
              <option value="low">Low Severity</option>
            </select>
          </div>
        </div>
      </div>

      {/* Insight List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-20 w-full" />)}
        </div>
      ) : filteredInsights.length === 0 ? (
        <EmptyState 
          icon={ShieldAlert}
          title="No insights found"
          description="Try adjusting your filters or search term."
        />
      ) : (
        <div className="space-y-3">
          {filteredInsights.map((insight: any, i: number) => {
            const isHigh = insight.severity === 'high'
            const isMedium = insight.severity === 'medium'
            const severityColor = isHigh ? 'critical' : isMedium ? 'warning' : 'success'
            
            return (
              <div 
                key={insight.id}
                className="group bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 flex items-center gap-4 hover:border-[var(--color-accent)]/50 hover:shadow-[0_0_15px_rgba(139,92,246,0.1)] transition-all cursor-pointer animate-[slide-up_0.3s_ease-out_forwards] opacity-0"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                {/* ID & Status */}
                <div className="w-24 shrink-0 flex flex-col gap-1.5">
                  <span className="text-xs font-mono text-[var(--color-muted)]">INS-{insight.id.substring(0, 4).toUpperCase()}</span>
                  <Badge variant={severityColor as any} className="w-fit text-[10px] uppercase">{insight.severity}</Badge>
                </div>
                
                {/* Main Content */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-semibold text-white truncate group-hover:text-[var(--color-accent)] transition-colors">{insight.title}</h3>
                  <p className="text-sm text-[var(--color-muted)] truncate mt-1">{insight.body}</p>
                </div>
                
                {/* Meta */}
                <div className="hidden md:flex items-center gap-6 shrink-0">
                  <div className="flex flex-col gap-1 items-end">
                    <span className="text-xs text-[var(--color-muted)] flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" /> 
                      {insight.created_at ? new Date(insight.created_at).toLocaleString() : 'Just now'}
                    </span>
                    <span className="text-xs text-[var(--color-muted)] flex items-center gap-1.5">
                      <GitMerge className="w-3.5 h-3.5" /> 
                      {insight.repository_name || 'backend-api'}
                    </span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-[var(--color-border)] group-hover:text-[var(--color-accent)] transition-colors" />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
