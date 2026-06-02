import { useState, useEffect } from 'react'
import { Card } from '../components/Card'
import { CheckCircle2, XCircle, Hash, Ticket } from 'lucide-react'

export function Actions({ token, orgId }: { token: string, orgId: string }) {
  const [actions, setActions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/v1/orgs/${orgId}/actions`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    .then(res => res.json())
    .then(data => {
      setActions(data.items || [])
      setLoading(false)
    })
    .catch(err => {
      console.error(err)
      setLoading(false)
    })
  }, [orgId, token])

  const handleApprove = async (id: string) => {
    try {
      await fetch(`/api/v1/actions/${id}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      })
      setActions(actions.filter(a => a.id !== id))
    } catch (err) {
      console.error(err)
    }
  }

  const handleReject = async (id: string) => {
    try {
      await fetch(`/api/v1/actions/${id}/reject`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason: "User rejected" })
      })
      setActions(actions.filter(a => a.id !== id))
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="p-8 max-w-6xl mx-auto w-full animate-[fade-in_0.3s_ease-out]">
      <header className="mb-10">
        <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Pending Actions</h1>
        <p className="text-slate-400">Review and approve AI-generated notifications and tickets.</p>
      </header>

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map(i => (
            <Card key={i} className="h-32 animate-pulse bg-slate-800/50 border-slate-700/50" />
          ))}
        </div>
      ) : actions.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 border border-dashed border-slate-700/50 rounded-xl bg-slate-800/20">
          <CheckCircle2 className="w-12 h-12 text-emerald-500/50 mb-4" />
          <p className="text-slate-400 font-medium">All caught up! No pending actions.</p>
        </div>
      ) : (
        <div className="grid gap-6">
          {actions.map((action, i) => (
            <Card 
              key={action.id} 
              className="flex flex-col md:flex-row gap-6 items-start md:items-center hover:border-indigo-500/30 transition-all duration-300 transform hover:-translate-y-1"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className={`px-3 py-1 text-xs font-medium rounded-full flex items-center gap-1.5
                    ${action.action_type === 'send_slack' ? 'bg-[#E01E5A]/10 text-[#E01E5A] border border-[#E01E5A]/20' : 'bg-[#0052CC]/10 text-[#0052CC] border border-[#0052CC]/20'}`}
                  >
                    {action.action_type === 'send_slack' ? <Hash className="w-3.5 h-3.5" /> : <Ticket className="w-3.5 h-3.5" />}
                    {action.action_type.toUpperCase()}
                  </span>
                  <span className="text-slate-400 font-mono text-sm">{action.payload?.channel || 'Jira Epic'}</span>
                </div>
                <p className="text-slate-200 text-lg">{action.payload?.message || action.payload?.detail}</p>
              </div>
              
              <div className="flex items-center gap-3 w-full md:w-auto mt-4 md:mt-0">
                <button 
                  onClick={() => handleReject(action.id)}
                  className="flex-1 md:flex-none px-4 py-2 rounded-lg font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-colors flex items-center justify-center gap-2"
                >
                  <XCircle className="w-4 h-4" /> Reject
                </button>
                <button 
                  onClick={() => handleApprove(action.id)}
                  className="flex-1 md:flex-none px-4 py-2 rounded-lg font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 transition-colors flex items-center justify-center gap-2"
                >
                  <CheckCircle2 className="w-4 h-4" /> Approve
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
