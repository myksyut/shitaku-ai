import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { API, server } from '../test/series'
import { ApiError, apiClient } from './api-client'
import { supabase } from './supabase'

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(supabase.auth.getSession).mockResolvedValue({ data: { session: null }, error: null })
})

describe('apiClient', () => {
  it('sends the session token at the HTTP boundary', async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: {
        session: {
          access_token: 'test-token',
          refresh_token: '',
          expires_in: 3600,
          token_type: 'bearer',
          user: {
            id: 'user-1',
            email: 'user@example.com',
            aud: 'authenticated',
            app_metadata: {},
            user_metadata: {},
            created_at: '',
          },
        },
      },
      error: null,
    })
    server.use(
      http.get(`${API}/probe`, ({ request }) => {
        expect(request.headers.get('authorization')).toBe('Bearer test-token')
        return HttpResponse.json({ value: 'ok' })
      }),
    )
    await expect(apiClient('/api/v1/probe')).resolves.toEqual({ value: 'ok' })
  })

  it('signs out on 401 and retains the HTTP status', async () => {
    server.use(http.get(`${API}/probe`, () => HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })))
    await expect(apiClient('/api/v1/probe')).rejects.toEqual(new ApiError(401, 'Unauthorized'))
    expect(supabase.auth.signOut).toHaveBeenCalledOnce()
  })

  it('does not try to parse JSON after a successful deletion', async () => {
    server.use(http.delete(`${API}/probe`, () => new HttpResponse(null, { status: 204 })))
    await expect(apiClient('/api/v1/probe', { method: 'DELETE' })).resolves.toBeUndefined()
  })
})
