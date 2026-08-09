import { QueryClient } from '@tanstack/react-query'
import { act, render } from '@testing-library/react'
import {
  createMemoryHistory,
  RouterProvider,
} from '@tanstack/react-router'

import { ErrorBoundary } from '../app/ErrorBoundary'
import { AppProviders } from '../app/providers'
import { createAppRouter } from '../app/router'
import type { CurrentSessionResponse } from '../api/generated/company-system'
import { CURRENT_SESSION_QUERY_KEY } from '../auth/session'
import { syntheticCurrentSession } from './sessionFixture'

export async function renderApp(
  initialEntries: string[] = ['/'],
  options: { session?: CurrentSessionResponse | null } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  queryClient.setQueryDefaults(CURRENT_SESSION_QUERY_KEY, {
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  })
  if (options.session !== null) {
    queryClient.setQueryData(
      CURRENT_SESSION_QUERY_KEY,
      options.session ?? syntheticCurrentSession,
    )
  }
  const history = createMemoryHistory({ initialEntries })
  const router = createAppRouter(history)

  const view = render(
    <ErrorBoundary>
      <AppProviders queryClient={queryClient}>
        <RouterProvider router={router} />
      </AppProviders>
    </ErrorBoundary>,
  )

  await act(async () => {
    await router.load()
  })

  return { queryClient, router, ...view }
}
