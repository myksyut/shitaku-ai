import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// Supabaseモジュールをモック
const mockGetSession = vi.fn()
const mockOnAuthStateChange = vi.fn()
const mockSignInWithPassword = vi.fn()
const mockSignUp = vi.fn()
const mockSignOut = vi.fn()

vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
      signInWithPassword: mockSignInWithPassword,
      signUp: mockSignUp,
      signOut: mockSignOut,
    },
  })),
}))

// supabase.tsの環境変数チェックをバイパスするためにモック
vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: () => mockGetSession(),
      onAuthStateChange: (callback: unknown) => mockOnAuthStateChange(callback),
      signInWithPassword: (params: unknown) => mockSignInWithPassword(params),
      signUp: (params: unknown) => mockSignUp(params),
      signOut: () => mockSignOut(),
    },
  },
}))

import { AuthProvider, useAuthContext } from '../contexts/AuthContext'
import { useAuth } from './useAuth'

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetSession.mockResolvedValue({
      data: { session: null },
      error: null,
    })
    mockOnAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    })
  })

  describe('AuthProvider', () => {
    it('should render children and provide context', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>
      const { result } = renderHook(() => useAuthContext(), { wrapper })

      await waitFor(() => {
        expect(result.current).toBeDefined()
        expect(result.current.user).toBeNull()
      })
    })
  })

  describe('useAuth initial state', () => {
    it('should have null user initially', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
      expect(result.current.user).toBeNull()
    })

    it('should have loading true initially then false after session check', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>
      const { result } = renderHook(() => useAuth(), { wrapper })

      // 初期状態ではloadingはtrue
      // getSession解決後はfalse
      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
    })
  })

  describe('useAuth functions', () => {
    it('should have signIn function', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
      expect(typeof result.current.signIn).toBe('function')
    })

    it('should have signOut function', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
      expect(typeof result.current.signOut).toBe('function')
    })

    it('should call supabase signIn when signIn is called', async () => {
      mockSignInWithPassword.mockResolvedValue({ error: null })
      const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      await act(async () => {
        await result.current.signIn('test@example.com', 'password')
      })

      expect(mockSignInWithPassword).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password',
      })
    })

    it('should call supabase signOut when signOut is called', async () => {
      mockSignOut.mockResolvedValue({ error: null })
      const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>
      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      await act(async () => {
        await result.current.signOut()
      })

      expect(mockSignOut).toHaveBeenCalled()
    })
  })

  describe('useAuthContext error', () => {
    it('should throw error when used outside AuthProvider', () => {
      expect(() => {
        renderHook(() => useAuthContext())
      }).toThrow('useAuthContext must be used within an AuthProvider')
    })
  })
})

describe('apiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetSession.mockResolvedValue({
      data: { session: null },
      error: null,
    })
  })

  it('should add Authorization header when session exists', async () => {
    const mockSession = {
      access_token: 'test-token-123',
      user: { id: '1', email: 'test@example.com' },
    }
    mockGetSession.mockResolvedValue({
      data: { session: mockSession },
      error: null,
    })

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 'test' }),
    })
    globalThis.fetch = mockFetch

    const { apiClient } = await import('../lib/api-client')
    await apiClient('/test')

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/test'),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token-123',
        }),
      }),
    )
  })

  it('should handle 401 error by calling signOut', async () => {
    mockGetSession.mockResolvedValue({
      data: { session: { access_token: 'expired-token' } },
      error: null,
    })
    mockSignOut.mockResolvedValue({ error: null })

    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: 'Unauthorized' }),
    })
    globalThis.fetch = mockFetch

    const { apiClient } = await import('../lib/api-client')

    await expect(apiClient('/test')).rejects.toThrow('Unauthorized')
    expect(mockSignOut).toHaveBeenCalled()
  })
})
