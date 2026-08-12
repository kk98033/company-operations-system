"""Master-data router composition."""

from fastapi import APIRouter

from app.modules.master_data.catalog_api import build_catalog_router
from app.modules.master_data.vendor_api import build_vendor_router


def build_master_data_router() -> APIRouter:
    router = APIRouter()
    router.include_router(build_vendor_router())
    router.include_router(build_catalog_router())
    return router
