import { cn } from "../lib/utils"

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: boolean
}

export function Card({ className, glow = false, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "glass-panel rounded-xl p-6 transition-all duration-300",
        glow && "glow-border",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}
