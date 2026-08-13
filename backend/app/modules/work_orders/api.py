"""Case and work-order router composition."""

from fastapi import APIRouter

from app.modules.work_orders.attachment_api import build_attachment_router
from app.modules.work_orders.case_api import build_case_router
from app.modules.work_orders.work_order_api import build_work_order_crud_router


def build_work_order_router() -> APIRouter:
    router = APIRouter()
    router.include_router(build_case_router())
    router.include_router(build_work_order_crud_router())
    router.include_router(build_attachment_router())
    return router
