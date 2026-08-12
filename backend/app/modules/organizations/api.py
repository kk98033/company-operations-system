"""Permission-guarded API for the current company's profile."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as OrmSession

from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_authenticated_csrf
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.dependencies import require_capability
from app.modules.organizations.models import Organization
from app.modules.organizations.profile import (
    OrganizationProfileConflictError,
    get_organization_profile,
    update_organization_profile,
)
from app.modules.organizations.schemas import (
    OrganizationLogoMetadata,
    OrganizationProfileResponse,
    OrganizationProfileUpdate,
)
from app.modules.organizations.scope import OrganizationScope

_require_settings_manage = require_capability("settings.manage")


def _scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def _response(organization: Organization) -> OrganizationProfileResponse:
    logo = None
    if organization.logo_object_key is not None:
        logo = OrganizationLogoMetadata(
            original_filename=organization.logo_original_filename,
            content_type=organization.logo_content_type,
            sha256=organization.logo_sha256,
        )
    return OrganizationProfileResponse(
        id=organization.id,
        name=organization.name,
        tax_identifier=organization.tax_identifier,
        representative_name=organization.representative_name,
        phone=organization.phone,
        fax=organization.fax,
        email=organization.email,
        address=organization.address,
        logo=logo,
        updated_at=organization.updated_at,
    )


def build_organization_router() -> APIRouter:
    router = APIRouter(prefix="/organizations/current", tags=["organizations"])

    @router.get(
        "/profile",
        response_model=OrganizationProfileResponse,
        operation_id="organization_profile_get",
        summary="讀取目前公司的基本資料",
    )
    def get_profile(
        context: Annotated[AuthenticatedSession, Depends(_require_settings_manage)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> OrganizationProfileResponse:
        return _response(
            get_organization_profile(database_session, scope=_scope(context))
        )

    @router.put(
        "/profile",
        response_model=OrganizationProfileResponse,
        operation_id="organization_profile_update",
        summary="更新目前公司的基本資料",
    )
    def update_profile(
        payload: OrganizationProfileUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_require_settings_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> OrganizationProfileResponse:
        try:
            organization = update_organization_profile(
                database_session,
                scope=_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except OrganizationProfileConflictError:
            raise ApplicationError(
                status_code=409,
                code="ORGANIZATION_PROFILE_CONFLICT",
                message="公司資料已被其他人更新，請重新載入後再修改",
            ) from None
        return _response(organization)

    return router
