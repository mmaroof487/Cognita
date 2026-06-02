import { useState, useEffect } from 'react'
import { Card } from '../components/Card'
import { Activity, GitMerge, ShieldAlert, Cpu } from 'lucide-react'

export function Dashboard({ token, orgId }: { token: string, orgId: string }) {
  const [loading, setLoading] = useState(true)
  const [insights, setInsights] = useState<any[]>([])
  const [repoCount, setRepoCount] = useState(0)
  const [agentRunCount, setAgentRunCount] = useState(0)
  const [repos, setRepos] = useState<any[]>([])
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'error'} | null>(null)
  useEffect(() => {
    const headers = { 'Authorization': `Bearer ${token}` }
    
    Promise.all([
      fetch(`/api/v1/orgs/${orgId}/insights`, { headers }).then(res => res.json()),
      fetch(`/api/v1/orgs/${orgId}`, { headers }).then(res => res.json()),
      fetch(`/api/v1/orgs/${orgId}/agent-runs`, { headers }).then(res => res.json()),
      fetch(`/api/v1/orgs/${orgId}/repos`, { headers }).then(res => res.json())
    ])
    .then(([insightsData, orgData, runsData, reposData]) => {
      setInsights(insightsData.items || [])
      setRepoCount(orgData.repo_count || 0)
      setAgentRunCount(runsData.total || 0)
      setRepos(reposData.items || [])
      setLoading(false)
    })
    .catch(err => {
      console.error(err)
      setLoading(false)
    })
  }, [orgId, token])

  return (
    <div className="p-8 max-w-6xl mx-auto w-full animate-[fade-in_0.3s_ease-out]">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Welcome back.</h1>
          <p className="text-slate-400">Here's what your agents have found today.</p>
        </div>
        <button 
          onClick={() => {
            fetch(`/api/v1/orgs/${orgId}/agent-runs`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({ triggered_by: 'manual' })
            })
            .then(res => res.json())
            .then(data => {
              setNotification({ message: `Started agent run: ${data.run_id}`, type: 'success' });
              setTimeout(() => setNotification(null), 4000);
            })
            .catch(err => {
              console.error(err);
              setNotification({ message: 'Failed to trigger run', type: 'error' });
              setTimeout(() => setNotification(null), 4000);
            })
          }}
          className="bg-indigo-500 hover:bg-indigo-600 text-white px-5 py-2.5 rounded-lg font-medium transition-all shadow-[0_0_15px_rgba(99,102,241,0.4)] flex items-center gap-2"
        >
          <Activity className="w-4 h-4" /> Trigger Run
        </button>
      </header>

      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-6 right-6 px-6 py-4 rounded-xl shadow-2xl border backdrop-blur-sm z-50 animate-[slide-in-right_0.3s_ease-out] flex items-center gap-3 ${
          notification.type === 'success' 
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
            : 'bg-red-500/10 border-red-500/30 text-red-400'
        }`}>
          {notification.type === 'success' ? <Activity className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
          <span className="font-medium text-sm">{notification.message}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <Card className="flex items-center gap-4 animate-[slide-up_0.4s_ease-out]" glow>
          <div className="p-3 bg-blue-500/20 text-blue-400 rounded-lg border border-blue-500/30">
            <GitMerge className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Active Repos</p>
            <p className="text-2xl font-bold text-white">{repoCount}</p>
          </div>
        </Card>
        
        <Card className="flex items-center gap-4 animate-[slide-up_0.5s_ease-out]" glow>
          <div className="p-3 bg-amber-500/20 text-amber-400 rounded-lg border border-amber-500/30">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Insights Found</p>
            <p className="text-2xl font-bold text-white">{insights.length}</p>
          </div>
        </Card>
        
        <Card className="flex items-center gap-4 animate-[slide-up_0.6s_ease-out]" glow>
          <div className="p-3 bg-purple-500/20 text-purple-400 rounded-lg border border-purple-500/30">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Agent Runs</p>
            <p className="text-2xl font-bold text-white">{agentRunCount}</p>
          </div>
        </Card>
      </div>

      <h2 className="text-xl font-bold text-white mb-6">Recent Insights</h2>
      
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <Card key={i} className="h-24 animate-pulse bg-slate-800/50 border-slate-700/50" />
          ))}
        </div>
      ) : insights.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 border border-dashed border-slate-700/50 rounded-xl bg-slate-800/20">
          <p className="text-slate-400 font-medium">No insights found.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {insights.map((insight, i) => (
            <Card 
              key={insight.id} 
              className="flex items-start gap-4 hover:border-indigo-500/30 transition-colors"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className={`p-2 rounded-md ${
                insight.severity === 'high' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                insight.severity === 'medium' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                'bg-blue-500/20 text-blue-400 border border-blue-500/30'
              }`}>
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-start mb-1">
                  <h3 className="text-lg font-semibold text-white">{insight.title}</h3>
                  <span className="text-xs font-mono text-slate-500">{insight.insight_type}</span>
                </div>
                <p className="text-sm text-slate-400">{insight.body}</p>
              </div>
            </Card>
          ))}
        </div>
      )}

      <h2 className="text-xl font-bold text-white mt-10 mb-6">Observed Repositories</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {repos.map(repo => (
          <Card key={repo.id} className="flex items-center justify-between p-4 bg-slate-800/30 border-slate-700/50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-md">
                <GitMerge className="w-4 h-4" />
              </div>
              <span className="text-white font-medium">{repo.name}</span>
            </div>
            <span className={`text-xs px-2 py-1 rounded-full ${repo.is_tracked ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-500/10 text-slate-400'}`}>
              {repo.is_tracked ? 'Tracked' : 'Untracked'}
            </span>
          </Card>
        ))}
      </div>
    </div>
  )
}
