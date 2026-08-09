import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  type RouterHistory,
} from '@tanstack/react-router'

import { AuthenticatedBoundary } from '../auth/AuthenticatedBoundary'
import { HomePage } from '../pages/HomePage'
import { LoginPage } from '../pages/LoginPage'
import { CasePrototypePage } from '../pages/cases/CasePrototypePage'
import { ModulePrototypePage } from '../pages/ModulePrototypePage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RouteErrorPage } from '../pages/RouteErrorPage'
import { StylePreviewPage } from '../pages/StylePreviewPage'
import { UiPatternsPage } from '../pages/UiPatternsPage'
import { WorkOrderListPrototypePage } from '../pages/work-orders/WorkOrderListPrototypePage'
import { WorkOrderPrototypePage } from '../pages/work-orders/WorkOrderPrototypePage'
import { workflowModules } from './workflowModules'

const rootRoute = createRootRoute({
  component: Outlet,
  errorComponent: RouteErrorPage,
  notFoundComponent: NotFoundPage,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
})

const authenticatedRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'authenticated',
  component: AuthenticatedBoundary,
})

const indexRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/',
  component: HomePage,
})

const stylePreviewRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/style-preview',
  component: StylePreviewPage,
})

const uiPatternsRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/ui-patterns',
  component: UiPatternsPage,
})

const workflowRoutes = workflowModules.map((module) => createRoute({
  getParentRoute: () => authenticatedRoute,
  path: module.path,
  component: module.id === 'work-orders'
    ? WorkOrderListPrototypePage
    : module.id === 'cases'
      ? () => <CasePrototypePage module={module} />
    : () => <ModulePrototypePage module={module} />,
}))

const workOrderNewRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/work-orders/new',
  component: WorkOrderPrototypePage,
})

const routeTree = rootRoute.addChildren([
  loginRoute,
  authenticatedRoute.addChildren([
    indexRoute,
    ...workflowRoutes,
    workOrderNewRoute,
    uiPatternsRoute,
    stylePreviewRoute,
  ]),
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
