import {
  createRootRoute,
  createRoute,
  createRouter,
  type RouterHistory,
} from '@tanstack/react-router'

import { HomePage } from '../pages/HomePage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RouteErrorPage } from '../pages/RouteErrorPage'
import { StylePreviewPage } from '../pages/StylePreviewPage'
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

const stylePreviewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/style-preview',
  component: StylePreviewPage,
})

const routeTree = rootRoute.addChildren([indexRoute, stylePreviewRoute])

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
