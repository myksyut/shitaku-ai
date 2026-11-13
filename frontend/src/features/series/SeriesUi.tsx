import type { ReactNode } from 'react'

export function formatStart(value: string) {
  return new Date(value).toLocaleString('ja-JP', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex rounded-full bg-[var(--color-cream-300)] px-3 py-1 text-xs font-semibold text-[var(--color-warm-gray-600)]">
      {children}
    </span>
  )
}

export function ErrorNotice({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="rounded-xl bg-[var(--color-error-light)] p-3 text-sm text-[var(--color-error-dark)]">
      {children}
    </p>
  )
}
