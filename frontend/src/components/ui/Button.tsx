import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { ButtonHTMLAttributes } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-blue-500 text-white hover:bg-blue-600',
  secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
  danger: 'bg-red-500 text-white hover:bg-red-600',
}

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-2 py-1 text-sm',
  md: 'px-4 py-2',
  lg: 'px-6 py-3 text-lg',
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={twMerge(
        clsx(
          'rounded font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
          variantStyles[variant],
          sizeStyles[size],
          className,
        ),
      )}
      {...props}
    >
      {children}
    </button>
  )
}
