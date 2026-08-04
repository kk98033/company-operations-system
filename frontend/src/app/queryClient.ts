import { QueryClient, type QueryClientConfig } from '@tanstack/react-query'

const queryClientConfig: QueryClientConfig = {
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
    mutations: {
      retry: false,
    },
  },
}

export function createAppQueryClient() {
  return new QueryClient(queryClientConfig)
}
