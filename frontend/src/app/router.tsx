import {
  createRootRoute,
  createRoute,
  createRouter,
  type RouterHistory,
} from '@tanstack/react-router'

import { HomePage } from '../pages/HomePage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RouteErrorPage } from '../pages/RouteErrorPage'
import { AppLayout } from './AppLayout'

const rootRoute = createRootRoute({
  component: AppLayout,
  errorComponent: RouteErrorPage,
  notFoundComponent: NotFoundPage,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: HomePage,
})

const routeTree = rootRoute.addChildren([indexRoute])

export function createAppRouter(history?: RouterHistory) {
  return createRouter({
    routeTree,
    defaultPreload: 'intent',
    ...(history ? { history } : {}),
  })
}

export const appRouter = createAppRouter()

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof appRouter
  }
}
