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
from app.modules.organizations.models import Organization, OrganizationSettings
from app.modules.organizations.profile import (
    OrganizationProfileConflictError,
    get_organization_profile,
    update_organization_profile,
)
from app.modules.organizations.schemas import (
    DocumentNumberPolicyResponse,
    OrganizationLogoMetadata,
    OrganizationProfileResponse,
    OrganizationProfileUpdate,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdate,
    PrintPolicyResponse,
    StatementTaxDefaults,
)
from app.modules.organizations.scope import OrganizationScope
from app.modules.organizations.settings import (
    OrganizationSettingsConflictError,
    get_organization_settings,
    update_organization_settings,
)
from app.modules.organizations.settings_contract import (
    DOCUMENT_NUMBER_POLICIES,
    PRINT_POLICIES,
)

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


def _settings_response(
    settings: OrganizationSettings,
) -> OrganizationSettingsResponse:
    return OrganizationSettingsResponse(
        organization_id=settings.organization_id,
        statement_tax=StatementTaxDefaults(
            enabled=settings.statement_tax_default_enabled,
            tax_rate_percent=settings.statement_tax_rate_percent,
            rounding_scope=settings.statement_rounding_scope,
            rounding_decimal_places=settings.statement_rounding_decimal_places,
            calculation_status="active_company_uat_pending",
        ),
        document_number_policy_version=settings.document_number_policy_version,
        document_numbering=[
            DocumentNumberPolicyResponse(
                document_type=policy.document_type,
                label=policy.label,
                format=policy.format,
                reset_period=policy.reset_period,
            )
            for policy in DOCUMENT_NUMBER_POLICIES
        ],
        quotation_print_layout_version=settings.quotation_print_layout_version,
        work_order_print_layout_version=settings.work_order_print_layout_version,
        printing=[
            PrintPolicyResponse(
                document_type=policy.document_type,
                label=policy.label,
                paper_size=policy.paper_size,
                orientation=policy.orientation,
                status=policy.status,
                note=policy.note,
            )
            for policy in PRINT_POLICIES
        ],
        updated_at=settings.updated_at,
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

    @router.get(
        "/settings",
        response_model=OrganizationSettingsResponse,
        operation_id="organization_settings_get",
        summary="讀取目前公司的帳務與文件預設設定",
    )
    def get_settings(
        context: Annotated[AuthenticatedSession, Depends(_require_settings_manage)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> OrganizationSettingsResponse:
        return _settings_response(
            get_organization_settings(database_session, scope=_scope(context))
        )

    @router.put(
        "/settings",
        response_model=OrganizationSettingsResponse,
        operation_id="organization_settings_update",
        summary="更新目前公司的對帳單預設設定",
    )
    def update_settings(
        payload: OrganizationSettingsUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_require_settings_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> OrganizationSettingsResponse:
        try:
            settings = update_organization_settings(
                database_session,
                scope=_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except OrganizationSettingsConflictError:
            raise ApplicationError(
                status_code=409,
                code="ORGANIZATION_SETTINGS_CONFLICT",
                message="公司預設設定已被其他人更新，請重新載入後再修改",
            ) from None
        return _settings_response(settings)

    return router
