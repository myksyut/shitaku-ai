import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './api-client'

const mockGetSession = vi.fn()
const mockSignOut = vi.fn()

vi.mock('./supabase', () => ({
  supabase: {
    auth: {
      getSession: () => mockGetSession(),
      signOut: () => mockSignOut(),
    },
  },
}))

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

    await expect(apiClient('/test')).rejects.toThrow('Unauthorized')
    expect(mockSignOut).toHaveBeenCalled()
  })
})
