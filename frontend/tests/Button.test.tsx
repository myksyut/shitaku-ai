import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '@/components/ui/Button'

describe('Button', () => {
  it('renders with default props', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button')).toHaveTextContent('Click me')
  })

  it('renders with primary variant', () => {
    render(<Button variant="primary">Primary</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-blue-500')
  })

  it('renders with secondary variant', () => {
    render(<Button variant="secondary">Secondary</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-gray-200')
  })

  it('renders with danger variant', () => {
    render(<Button variant="danger">Danger</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-red-500')
  })

  it('renders with different sizes', () => {
    const { rerender } = render(<Button size="sm">Small</Button>)
    expect(screen.getByRole('button')).toHaveClass('px-2')

    rerender(<Button size="lg">Large</Button>)
    expect(screen.getByRole('button')).toHaveClass('px-6')
  })
})
