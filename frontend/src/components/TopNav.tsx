import { Bell, Search, User, Activity } from 'lucide-react'

export function TopNav() {
  // Mock health score, would ideally come from an API endpoint for overall org health
  const healthScore = 92;

  return (
    <header className="h-16 border-b border-[var(--color-border)] bg-[var(--color-background)]/80 backdrop-blur-md sticky top-0 z-40 flex items-center justify-between px-8">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-muted)]" />
          <input 
            type="text" 
            placeholder="Search insights, actions, or developers..." 
            className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-full pl-10 pr-4 py-1.5 text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors placeholder:text-[var(--color-muted)]"
          />
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--color-success)]/10 border border-[var(--color-success)]/20 animate-pulse-slow">
          <Activity className="w-4 h-4 text-[var(--color-success)]" />
          <span className="text-xs font-semibold text-[var(--color-success)]">Team Health: {healthScore}%</span>
        </div>

        <div className="flex items-center gap-3">
          <button className="p-2 text-[var(--color-muted)] hover:text-white transition-colors relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[var(--color-critical)] rounded-full border border-[var(--color-background)]"></span>
          </button>
          
          <div className="w-px h-6 bg-[var(--color-border)]"></div>
          
          <button className="w-8 h-8 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center text-[var(--color-muted)] hover:text-white hover:border-[var(--color-accent)]/50 transition-colors">
            <User className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  )
}
