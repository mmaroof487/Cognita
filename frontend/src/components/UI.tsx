import React from 'react'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function Card({ className, children, glow, ...props }: React.HTMLAttributes<HTMLDivElement> & { glow?: boolean }) {
  return (
    <div 
      className={cn(
        "glass-card rounded-xl p-6", 
        glow && "hover:border-[var(--color-accent)]/30 hover:shadow-[0_4px_20px_-2px_rgba(139,92,246,0.15)]",
        className
      )} 
      {...props}
    >
      {children}
    </div>
  )
}

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("skeleton rounded-md", className)} {...props} />
  )
}

export function Badge({ 
  children, 
  variant = 'default',
  className 
}: { 
  children: React.ReactNode, 
  variant?: 'default' | 'success' | 'warning' | 'critical' | 'accent',
  className?: string
}) {
  const variants = {
    default: "bg-[var(--color-surface)] text-[var(--color-muted)] border-[var(--color-border)]",
    success: "bg-[var(--color-success)]/10 text-[var(--color-success)] border-[var(--color-success)]/20",
    warning: "bg-[var(--color-warning)]/10 text-[var(--color-warning)] border-[var(--color-warning)]/20",
    critical: "bg-[var(--color-critical)]/10 text-[var(--color-critical)] border-[var(--color-critical)]/20",
    accent: "bg-[var(--color-accent)]/10 text-[var(--color-accent)] border-[var(--color-accent)]/20",
  }
  
  return (
    <span className={cn("px-2.5 py-0.5 rounded-full text-xs font-medium border", variants[variant], className)}>
      {children}
    </span>
  )
}

export function EmptyState({ 
  icon: Icon, 
  title, 
  description 
}: { 
  icon: React.ElementType, 
  title: string, 
  description: string 
}) {
  return (
    <div className="flex flex-col items-center justify-center p-12 border border-dashed border-[var(--color-border)] rounded-xl bg-[var(--color-surface)]/50 text-center animate-fade-in">
      <div className="w-16 h-16 bg-[var(--color-surface)] rounded-2xl flex items-center justify-center mb-6 border border-[var(--color-border)] shadow-sm">
        <Icon className="w-8 h-8 text-[var(--color-muted)]" />
      </div>
      <h3 className="text-lg font-semibold text-[var(--color-text)] mb-2">{title}</h3>
      <p className="text-[var(--color-muted)] max-w-sm">{description}</p>
    </div>
  )
}
