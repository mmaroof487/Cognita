import { useState, useEffect } from 'react'
import { Sidebar } from './components/Sidebar'
import { Dashboard } from './pages/Dashboard'
import { Actions } from './pages/Actions'
import { TerminalSquare, Save } from 'lucide-react'

function App() {
  const [currentTab, setCurrentTab] = useState('dashboard')
  const [token, setToken] = useState(localStorage.getItem('cognita_token') || '')
  const [orgId, setOrgId] = useState(localStorage.getItem('cognita_org_id') || '')

  const handleSaveConfig = () => {
    localStorage.setItem('cognita_token', token)
    localStorage.setItem('cognita_org_id', orgId)
    window.location.reload()
  }

  if (!localStorage.getItem('cognita_token') || !localStorage.getItem('cognita_org_id')) {
    return (
      <div className="min-h-screen bg-[var(--color-background)] flex items-center justify-center p-4">
        <div className="glass-panel p-8 rounded-2xl max-w-md w-full glow-border">
          <h1 className="text-2xl font-bold text-white mb-2">Welcome to Cognita</h1>
          <p className="text-slate-400 mb-6 text-sm">Please provide your API configuration to connect the frontend to the backend.</p>
          
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">JWT Access Token</label>
              <input 
                type="text" 
                value={token}
                onChange={e => setToken(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                placeholder="eyJhbGciOi..."
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Organization ID</label>
              <input 
                type="text" 
                value={orgId}
                onChange={e => setOrgId(e.target.value)}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                placeholder="uuid-here..."
              />
            </div>
            <button 
              onClick={handleSaveConfig}
              className="w-full bg-indigo-500 hover:bg-indigo-600 text-white font-medium py-2 rounded-lg flex items-center justify-center gap-2 mt-4"
            >
              <Save className="w-4 h-4" /> Save Configuration
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen w-full bg-[var(--color-background)] overflow-hidden">
      <Sidebar currentTab={currentTab} setCurrentTab={setCurrentTab} />
      
      <main className="flex-1 overflow-y-auto relative">
        {currentTab === 'dashboard' && <Dashboard token={token} orgId={orgId} />}
        {currentTab === 'actions' && <Actions token={token} orgId={orgId} />}
        {currentTab === 'stream' && (
          <div className="p-8 h-full flex flex-col items-center justify-center text-center animate-[fade-in_0.3s_ease-out]">
            <div className="w-20 h-20 bg-indigo-500/10 rounded-2xl border border-indigo-500/20 flex items-center justify-center mb-6">
              <TerminalSquare className="w-10 h-10 text-indigo-400 animate-[pulse-slow_3s_infinite]" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Agent Stream</h2>
            <p className="text-slate-400 max-w-md">Connect to the SSE endpoint to watch the LangGraph agents think in real-time.</p>
          </div>
        )}
        {currentTab === 'settings' && (
          <div className="p-8 h-full flex flex-col items-center justify-center text-center animate-[fade-in_0.3s_ease-out]">
            <h2 className="text-2xl font-bold text-white mb-2">Settings</h2>
            <p className="text-slate-400 mb-4">Update your configuration.</p>
            <button 
              onClick={() => {
                localStorage.removeItem('cognita_token')
                localStorage.removeItem('cognita_org_id')
                window.location.reload()
              }}
              className="bg-red-500/20 text-red-400 px-4 py-2 rounded-lg"
            >
              Log Out / Reset
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
