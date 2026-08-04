import { QueryClient } from '@tanstack/react-query'
import { act, render } from '@testing-library/react'
import {
  createMemoryHistory,
  RouterProvider,
} from '@tanstack/react-router'

import { ErrorBoundary } from '../app/ErrorBoundary'
import { AppProviders } from '../app/providers'
import { createAppRouter } from '../app/router'

export async function renderApp(initialEntries: string[] = ['/']) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
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
