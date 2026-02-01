/**
 * Card component with clay-morphism styling
 */
import type { HTMLAttributes, ReactNode } from 'react'

type CardVariant = 'default' | 'clay' | 'interactive'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant
  children: ReactNode
}

const variantClasses: Record<CardVariant, string> = {
  default: 'card',
  clay: 'card-clay',
  interactive: 'card card-interactive',
}

export function Card({ variant = 'default', children, className = '', ...props }: CardProps) {
  return (
    <div className={`${variantClasses[variant]} ${className}`.trim()} {...props}>
      {children}
    </div>
  )
}

interface CardHeaderProps {
  title: string
  subtitle?: string
  action?: ReactNode
}

export function CardHeader({ title, subtitle, action }: CardHeaderProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        marginBottom: 'var(--space-4)',
      }}
    >
      <div>
        <h3
          style={{
            fontSize: 'var(--font-size-lg)',
            fontWeight: 700,
            color: 'var(--color-warm-gray-800)',
            margin: 0,
          }}
        >
          {title}
        </h3>
        {subtitle && (
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warm-gray-500)',
              marginTop: 'var(--space-1)',
              margin: 0,
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {action}
    </div>
  )
}

interface CardContentProps {
  children: ReactNode
}

export function CardContent({ children }: CardContentProps) {
  return <div>{children}</div>
}

interface CardFooterProps {
  children: ReactNode
}

export function CardFooter({ children }: CardFooterProps) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'flex-end',
        gap: 'var(--space-3)',
        marginTop: 'var(--space-4)',
        paddingTop: 'var(--space-4)',
        borderTop: '1px solid var(--color-cream-300)',
      }}
    >
      {children}
    </div>
  )
}
