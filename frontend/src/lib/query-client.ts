import { isServer, QueryClient } from '@tanstack/react-query'
import { ApiError } from './api-client'

export function createAppQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status >= 400 && error.status <= 499) return false
          return failureCount < (isServer ? 0 : 3)
        },
      },
    },
  })
}
