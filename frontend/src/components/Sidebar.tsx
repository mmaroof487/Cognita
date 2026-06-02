import { Activity, LayoutDashboard, Settings, TerminalSquare, AlertCircle, Lightbulb, Users } from 'lucide-react'
import { motion } from 'framer-motion'

export function Sidebar({ currentTab, setCurrentTab, orgId }: { currentTab: string, setCurrentTab: (tab: string) => void, orgId: string }) {
  const tabs = [
    { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { id: 'insights', icon: Lightbulb, label: 'Insights' },
    { id: 'developers', icon: Users, label: 'Developers' },
    { id: 'agent-runs', icon: TerminalSquare, label: 'Agent Runs' },
    { id: 'actions', icon: AlertCircle, label: 'Actions' },
    { id: 'settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="w-64 h-screen border-r border-[var(--color-border)] bg-[var(--color-background)] flex flex-col py-6">
      <div className="flex items-center gap-3 mb-10 px-6">
        <div className="bg-[var(--color-accent)]/20 p-2 rounded-lg border border-[var(--color-accent)]/30">
          <Activity className="w-6 h-6 text-[var(--color-accent)]" />
        </div>
        <h1 className="text-xl font-bold tracking-tight text-white">Cognita</h1>
      </div>

      <nav className="flex-1 w-full px-3 space-y-1 relative">
        {tabs.map((tab) => {
          const active = currentTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setCurrentTab(tab.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors relative z-10 ${
                active 
                  ? 'text-white' 
                  : 'text-[var(--color-muted)] hover:text-white hover:bg-white/5'
              }`}
            >
              {active && (
                <motion.div
                  layoutId="active-tab"
                  className="absolute inset-0 bg-[var(--color-accent)]/15 border border-[var(--color-accent)]/30 rounded-lg shadow-[0_0_15px_rgba(139,92,246,0.15)] z-[-1]"
                  initial={false}
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <tab.icon className={`w-5 h-5 ${active ? 'text-[var(--color-accent)]' : ''}`} />
              <span className="font-medium text-sm">{tab.label}</span>
            </button>
          )
        })}
      </nav>
      
      <div className="w-full px-4 mt-auto">
        <div className="p-4 rounded-xl bg-gradient-to-br from-[var(--color-accent)]/5 to-transparent border border-[var(--color-accent)]/10">
          <p className="text-xs text-[var(--color-accent)]/80 font-medium mb-1">Organization ID</p>
          <p className="text-xs text-[var(--color-muted)] font-mono truncate">{orgId || 'Not connected'}</p>
        </div>
      </div>
    </div>
  )
}
