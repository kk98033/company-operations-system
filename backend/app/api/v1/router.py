"""Top-level API v1 router."""

from collections.abc import Sequence

from fastapi import APIRouter

from app.api.v1.health import build_health_router
from app.core.readiness import ReadinessCheck
from app.modules.audit.api import build_audit_router
from app.modules.auth.api import build_auth_router
from app.modules.billing import build_billing_router
from app.modules.customers.api import build_customer_router
from app.modules.customers.work_item_api import build_work_item_router
from app.modules.master_data import build_master_data_router
from app.modules.organizations.api import build_organization_router
from app.modules.pricing import build_pricing_router
from app.modules.production import build_production_router
from app.modules.quotations import build_quotation_router
from app.modules.shipments import build_shipment_router
from app.modules.work_orders import build_work_order_router


def build_v1_router(readiness_checks: Sequence[ReadinessCheck]) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(build_health_router(readiness_checks))
    router.include_router(build_auth_router())
    router.include_router(build_audit_router())
    router.include_router(build_organization_router())
    router.include_router(build_customer_router())
    router.include_router(build_work_item_router())
    router.include_router(build_master_data_router())
    router.include_router(build_quotation_router())
    router.include_router(build_work_order_router())
    router.include_router(build_production_router())
    router.include_router(build_shipment_router())
    router.include_router(build_pricing_router())
    router.include_router(build_billing_router())
    return router
