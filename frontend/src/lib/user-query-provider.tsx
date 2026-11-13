import { QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode, useState } from 'react'
import { createAppQueryClient } from './query-client'

function UserQueryClientProvider({ children }: { children: ReactNode }) {
  const [client] = useState(createAppQueryClient)
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

export function UserQueryProvider({ userId, children }: { userId: string; children: ReactNode }) {
  return <UserQueryClientProvider key={userId}>{children}</UserQueryClientProvider>
}
