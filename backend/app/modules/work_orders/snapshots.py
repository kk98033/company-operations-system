"""Company and customer snapshot lookup shared by case/work-order commands."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer
from app.modules.organizations.models import Organization
from app.modules.organizations.scope import OrganizationScope
from app.modules.work_orders.errors import WorkOrderNotFoundError


def load_snapshots(
    session: Session,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
) -> tuple[dict, dict]:
    organization = session.get(Organization, scope.organization_id)
    customer = session.scalar(
        scope.constrain(select(Customer), model=Customer).where(
            Customer.id == customer_id,
            Customer.status == "active",
        )
    )
    if organization is None or customer is None:
        raise WorkOrderNotFoundError
    return (
        {
            "name": organization.name,
            "tax_identifier": organization.tax_identifier,
            "phone": organization.phone,
            "fax": organization.fax,
            "email": organization.email,
            "address": organization.address,
        },
        {
            "code": customer.code,
            "name": customer.name,
            "contact_name": customer.contact_name,
            "phone": customer.phone,
            "fax": customer.fax,
            "address": customer.address,
        },
    )
