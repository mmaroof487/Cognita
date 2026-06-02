import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Sidebar } from './components/Sidebar'
import { TopNav } from './components/TopNav'
import { Dashboard } from './pages/Dashboard'
import { Actions } from './pages/Actions'
import { AgentRuns } from './pages/AgentRuns'
import { Developers } from './pages/Developers'
import { Insights } from './pages/Insights'
import { Save } from 'lucide-react'

// Create a client
const queryClient = new QueryClient()

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
          <p className="text-[var(--color-muted)] mb-6 text-sm">Please provide your API configuration to connect the frontend to the backend.</p>
          
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">JWT Access Token</label>
              <input 
                type="text" 
                value={token}
                onChange={e => setToken(e.target.value)}
                className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[var(--color-accent)] transition-colors"
                placeholder="eyJhbGciOi..."
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Organization ID</label>
              <input 
                type="text" 
                value={orgId}
                onChange={e => setOrgId(e.target.value)}
                className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[var(--color-accent)] transition-colors"
                placeholder="uuid-here..."
              />
            </div>
            <button 
              onClick={handleSaveConfig}
              className="w-full bg-[var(--color-accent)] hover:bg-purple-500 text-white font-medium py-2 rounded-lg flex items-center justify-center gap-2 mt-4 transition-colors"
            >
              <Save className="w-4 h-4" /> Save Configuration
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex h-screen w-full bg-[var(--color-background)] overflow-hidden">
        {/* Animated Background Orbs */}
        <div className="blur-orb bg-[var(--color-accent)] w-96 h-96 top-0 left-0 -translate-x-1/2 -translate-y-1/2"></div>
        <div className="blur-orb bg-[var(--color-accent)] w-[30rem] h-[30rem] bottom-0 right-0 translate-x-1/3 translate-y-1/3 opacity-20"></div>

        <Sidebar currentTab={currentTab} setCurrentTab={setCurrentTab} orgId={orgId} />
        
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative z-10">
          <TopNav />
          <main className="flex-1 overflow-y-auto relative">
            {currentTab === 'dashboard' && <Dashboard token={token} orgId={orgId} />}
            {currentTab === 'insights' && <Insights token={token} orgId={orgId} />}
            {currentTab === 'developers' && <Developers token={token} orgId={orgId} />}
            {currentTab === 'agent-runs' && <AgentRuns token={token} orgId={orgId} />}
            {currentTab === 'actions' && <Actions token={token} orgId={orgId} />}
            
            {currentTab === 'settings' && (
              <div className="p-8 h-full flex flex-col items-center justify-center text-center animate-fade-in">
                <h2 className="text-2xl font-bold text-white mb-2">Settings</h2>
                <p className="text-[var(--color-muted)] mb-4">Update your configuration.</p>
                <button 
                  onClick={() => {
                    localStorage.removeItem('cognita_token')
                    localStorage.removeItem('cognita_org_id')
                    window.location.reload()
                  }}
                  className="bg-[var(--color-critical)]/10 text-[var(--color-critical)] px-4 py-2 rounded-lg border border-[var(--color-critical)]/20 hover:bg-[var(--color-critical)]/20 transition-colors"
                >
                  Log Out / Reset
                </button>
              </div>
            )}
          </main>
        </div>
      </div>
    </QueryClientProvider>
  )
}

export default App
