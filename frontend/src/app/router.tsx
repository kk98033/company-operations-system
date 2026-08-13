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
import { CaseDetailPage, CasePrototypePage } from '../pages/cases/CasePrototypePage'
import { CustomerCreatePage } from '../pages/customers/CustomerCreatePage'
import { CustomerEditPage } from '../pages/customers/CustomerEditPage'
import { CustomerListPage } from '../pages/customers/CustomerListPage'
import { MasterDataPage } from '../pages/master-data/MasterDataPage'
import { InventoryPage } from '../pages/inventory/InventoryPage'
import { ProductionDetailPage } from '../pages/production/ProductionDetailPage'
import { ProductionListPage } from '../pages/production/ProductionListPage'
import { PricingDetailPage } from '../pages/pricing/PricingDetailPage'
import { PricingListPage } from '../pages/pricing/PricingListPage'
import { ReceiptListPage } from '../pages/billing/ReceiptListPage'
import { StatementDetailPage } from '../pages/billing/StatementDetailPage'
import { StatementListPage } from '../pages/billing/StatementListPage'
import { StatementPrintPage } from '../pages/billing/StatementPrintPage'
import { QuotationEditPage, QuotationNewPage } from '../pages/quotations/QuotationEditorPage'
import { QuotationListPage } from '../pages/quotations/QuotationListPage'
import { QuotationPrintPage } from '../pages/quotations/QuotationPrintPage'
import { ShipmentDetailPage } from '../pages/shipments/ShipmentDetailPage'
import { ShipmentEditorPage } from '../pages/shipments/ShipmentEditorPage'
import { ShipmentListPage } from '../pages/shipments/ShipmentListPage'
import { ShipmentPrintPage } from '../pages/shipments/ShipmentPrintPage'
import { CompanyProfilePage } from '../pages/settings/CompanyProfilePage'
import { CompanyDefaultsPage } from '../pages/settings/CompanyDefaultsPage'
import { ModulePrototypePage } from '../pages/ModulePrototypePage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RouteErrorPage } from '../pages/RouteErrorPage'
import { StylePreviewPage } from '../pages/StylePreviewPage'
import { UiPatternsPage } from '../pages/UiPatternsPage'
import { WorkOrderListPrototypePage } from '../pages/work-orders/WorkOrderListPrototypePage'
import { WorkOrderEditPage, WorkOrderNewPage } from '../pages/work-orders/WorkOrderPrototypePage'
import { WorkOrderPrintPage } from '../pages/work-orders/WorkOrderPrintPage'
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

const masterDataRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/master-data',
  component: MasterDataPage,
})

const workflowRoutes = workflowModules.map((module) => createRoute({
  getParentRoute: () => authenticatedRoute,
  path: module.path,
  component: module.id === 'work-orders'
    ? WorkOrderListPrototypePage
    : module.id === 'customers'
      ? CustomerListPage
    : module.id === 'quotations'
      ? QuotationListPage
    : module.id === 'cases'
      ? CasePrototypePage
    : module.id === 'production'
      ? ProductionListPage
    : module.id === 'inventory'
      ? InventoryPage
    : module.id === 'shipments'
      ? ShipmentListPage
    : module.id === 'pricing'
      ? PricingListPage
    : module.id === 'statements'
      ? StatementListPage
    : module.id === 'receipts'
      ? ReceiptListPage
    : () => <ModulePrototypePage module={module} />,
}))

const workOrderNewRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/work-orders/new',
  component: WorkOrderNewPage,
})

const workOrderEditRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/work-orders/$workOrderId',
  component: WorkOrderEditPage,
})

const workOrderPrintRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/work-orders/$workOrderId/print',
  component: WorkOrderPrintPage,
})

const caseDetailRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/cases/$caseId',
  component: CaseDetailPage,
})

const productionDetailRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/production/work-orders/$workOrderId',
  component: ProductionDetailPage,
})

const shipmentNewRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/shipments/new',
  component: ShipmentEditorPage,
})

const shipmentDetailRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/shipments/$shipmentId',
  component: ShipmentDetailPage,
})

const shipmentPrintRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/shipments/$shipmentId/print',
  component: ShipmentPrintPage,
})

const pricingDetailRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/pricing/$pricingId',
  component: PricingDetailPage,
})

const statementDetailRoute = createRoute({ getParentRoute: () => authenticatedRoute, path: '/statements/$statementId', component: StatementDetailPage })
const statementPrintRoute = createRoute({ getParentRoute: () => authenticatedRoute, path: '/statements/$statementId/print', component: StatementPrintPage })

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

const quotationNewRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/quotations/new',
  component: QuotationNewPage,
})

const quotationEditRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/quotations/$quotationId',
  component: QuotationEditPage,
})

const quotationPrintRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/quotations/$quotationId/print',
  component: QuotationPrintPage,
})

const routeTree = rootRoute.addChildren([
  loginRoute,
  authenticatedRoute.addChildren([
    indexRoute,
    ...workflowRoutes,
    customerNewRoute,
    customerEditRoute,
    quotationNewRoute,
    quotationEditRoute,
    quotationPrintRoute,
    workOrderNewRoute,
    workOrderEditRoute,
    workOrderPrintRoute,
    caseDetailRoute,
    productionDetailRoute,
    shipmentNewRoute,
    shipmentDetailRoute,
    shipmentPrintRoute,
    pricingDetailRoute,
    statementDetailRoute,
    statementPrintRoute,
    auditLogsRoute,
    companyProfileRoute,
    companyDefaultsRoute,
    masterDataRoute,
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
