import type { ReactNode, MouseEvent } from 'react'

interface GlassCardProps {
  children: ReactNode
  className?: string
  title?: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
  onClick?: (e: MouseEvent<HTMLDivElement>) => void
  glow?: boolean
  pad?: boolean
}

export default function GlassCard({
  children,
  className = '',
  title,
  subtitle,
  action,
  onClick,
  glow = false,
  pad = true,
}: GlassCardProps) {
  const classes = [
    'glass-card',
    glow ? 'glass-card-glow' : '',
    pad ? 'glass-card-pad' : '',
    onClick ? 'glass-card-clickable' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={classes} onClick={onClick}>
      {(title || subtitle || action) && (
        <div className="glass-card-head">
          <div>
            {title && <h4 className="glass-card-title">{title}</h4>}
            {subtitle && <span className="glass-card-subtitle">{subtitle}</span>}
          </div>
          {action && <div className="glass-card-action">{action}</div>}
        </div>
      )}
      {children}
    </div>
  )
}
