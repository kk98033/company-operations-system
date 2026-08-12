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
import { AuditLogPage } from '../pages/audit/AuditLogPage'
import { CasePrototypePage } from '../pages/cases/CasePrototypePage'
import { CustomerCreatePage } from '../pages/customers/CustomerCreatePage'
import { CustomerEditPage } from '../pages/customers/CustomerEditPage'
import { CustomerListPage } from '../pages/customers/CustomerListPage'
import { CompanyProfilePage } from '../pages/settings/CompanyProfilePage'
import { CompanyDefaultsPage } from '../pages/settings/CompanyDefaultsPage'
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

const auditLogsRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/audit-logs',
  component: AuditLogPage,
})

const companyProfileRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/settings/company',
  component: CompanyProfilePage,
})

const companyDefaultsRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/settings/defaults',
  component: CompanyDefaultsPage,
})

const workflowRoutes = workflowModules.map((module) => createRoute({
  getParentRoute: () => authenticatedRoute,
  path: module.path,
  component: module.id === 'work-orders'
    ? WorkOrderListPrototypePage
    : module.id === 'customers'
      ? CustomerListPage
    : module.id === 'cases'
      ? () => <CasePrototypePage module={module} />
    : () => <ModulePrototypePage module={module} />,
}))

const workOrderNewRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/work-orders/new',
  component: WorkOrderPrototypePage,
})

const customerNewRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/customers/new',
  component: CustomerCreatePage,
})

const customerEditRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/customers/$customerId',
  component: CustomerEditPage,
})

const routeTree = rootRoute.addChildren([
  loginRoute,
  authenticatedRoute.addChildren([
    indexRoute,
    ...workflowRoutes,
    customerNewRoute,
    customerEditRoute,
    workOrderNewRoute,
    auditLogsRoute,
    companyProfileRoute,
    companyDefaultsRoute,
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
