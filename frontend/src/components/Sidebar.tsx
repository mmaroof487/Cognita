import { Activity, LayoutDashboard, Settings, TerminalSquare, AlertCircle } from 'lucide-react'

export function Sidebar({ currentTab, setCurrentTab }: { currentTab: string, setCurrentTab: (tab: string) => void }) {
  const tabs = [
    { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { id: 'actions', icon: AlertCircle, label: 'Pending Actions' },
    { id: 'stream', icon: TerminalSquare, label: 'Agent Stream' },
    { id: 'settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="w-64 h-screen border-r border-[var(--color-border)] bg-[var(--color-background)]/50 backdrop-blur-xl flex flex-col items-center py-8">
      <div className="flex items-center gap-3 mb-12">
        <div className="bg-indigo-500/20 p-2 rounded-lg border border-indigo-500/30">
          <Activity className="w-6 h-6 text-indigo-400" />
        </div>
        <h1 className="text-xl font-bold tracking-tight text-white">Cognita</h1>
      </div>

      <nav className="flex-1 w-full px-4 space-y-2">
        {tabs.map((tab) => {
          const active = currentTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setCurrentTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                active 
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.15)]' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              <span className="font-medium text-sm">{tab.label}</span>
            </button>
          )
        })}
      </nav>
      
      <div className="w-full px-4 mt-auto">
        <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/20">
          <p className="text-xs text-indigo-300 font-medium mb-1">Tenant ID</p>
          <p className="text-xs text-slate-400 font-mono truncate">0e6e8c74-c79e-...</p>
        </div>
      </div>
    </div>
  )
}
