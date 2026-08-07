import {
  createRootRoute,
  createRoute,
  createRouter,
  type RouterHistory,
} from '@tanstack/react-router'

import { HomePage } from '../pages/HomePage'
import { ModulePrototypePage } from '../pages/ModulePrototypePage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RouteErrorPage } from '../pages/RouteErrorPage'
import { StylePreviewPage } from '../pages/StylePreviewPage'
import { UiPatternsPage } from '../pages/UiPatternsPage'
import { WorkOrderListPrototypePage } from '../pages/work-orders/WorkOrderListPrototypePage'
import { WorkOrderPrototypePage } from '../pages/work-orders/WorkOrderPrototypePage'
import { AppLayout } from './AppLayout'
import { workflowModules } from './workflowModules'

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

const uiPatternsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/ui-patterns',
  component: UiPatternsPage,
})

const workflowRoutes = workflowModules.map((module) => createRoute({
  getParentRoute: () => rootRoute,
  path: module.path,
  component: module.id === 'work-orders'
    ? WorkOrderListPrototypePage
    : () => <ModulePrototypePage module={module} />,
}))

const workOrderNewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/work-orders/new',
  component: WorkOrderPrototypePage,
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  ...workflowRoutes,
  workOrderNewRoute,
  uiPatternsRoute,
  stylePreviewRoute,
])

export function createAppRouter(history?: RouterHistory) {
  return createRouter({
    routeTree,
    defaultPreload: history ? false : 'intent',
    ...(history ? { history } : {}),
  })
}

export const appRouter = createAppRouter()

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof appRouter
  }
}
