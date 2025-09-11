'use client'

import { client } from '@/lib/client/client.gen'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'
const queryClient = new QueryClient()

export const API_PROXY_PATH = '/api/proxy'

client.setConfig({ baseUrl: API_PROXY_PATH })

export const TanstackQueryProvider = ({
  children,
}: {
  children: ReactNode
}) => {
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
