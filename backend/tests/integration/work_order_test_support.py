"""Synthetic setup helpers for case and work-order integration tests."""

from uuid import uuid4

from pydantic import SecretStr
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as OrmSession

from app.modules.authorization.models import (
    OrganizationMemberRole,
    Permission,
    Role,
    RolePermission,
)
from tests.integration.auth_test_support import create_auth_identity, make_auth_client


def grant(engine: Engine, identity, *codes: str) -> None:
    role = Role(
        id=uuid4(),
        organization_id=identity.organization_id,
        code=f"work_order_{uuid4().hex}",
        name="Synthetic Work Order Role",
    )
    with OrmSession(engine) as session, session.begin():
        permissions = []
        for code in codes:
            permission = session.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(id=uuid4(), code=code, name=f"Synthetic {code}")
                session.add(permission)
            permissions.append(permission)
        session.add(role)
        session.flush()
        session.add_all(
            [RolePermission(role_id=role.id, permission_id=item.id) for item in permissions]
            + [
                OrganizationMemberRole(
                    organization_id=identity.organization_id,
                    organization_member_id=identity.membership_id,
                    role_id=role.id,
                )
            ]
        )


def setup_company(engine: Engine, suffix: str):
    identity = create_auth_identity(engine, password=SecretStr(f"Synthetic-{suffix}-{uuid4()}"))
    grant(
        engine,
        identity,
        "customers.read",
        "customers.manage",
        "quotations.read",
        "quotations.manage",
        "quotations.confirm",
        "cases.read",
        "cases.manage",
        "work_orders.read",
        "work_orders.manage",
        "work_orders.confirm",
        "production.read",
        "production.manage",
        "production.complete",
        "inventory.read",
        "inventory.adjust",
        "shipment.read",
        "shipment.create",
        "shipment.confirm",
        "shipment.cancel",
        "shipment.complete_and_confirm",
        "pricing.read",
        "pricing.create",
        "pricing.confirm",
        "pricing.cancel",
        "price_default.update",
        "statement.read",
        "statement.issue",
        "statement.cancel",
        "receipt.read",
        "receipt.record",
        "receipt.reverse",
    )
    client = make_auth_client(engine)
    login = client.post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(identity.organization_id),
            "login_name": identity.login_name,
            "password": identity.password.get_secret_value(),
        },
    )
    assert login.status_code == 200
    csrf = client.cookies.get("company_system_csrf")
    customer = client.post(
        "/api/v1/customers",
        json={"code": f"WO-{suffix}", "name": f"虛構工單客戶 {suffix}"},
        headers={"X-CSRF-Token": csrf},
    ).json()
    return identity, client, csrf, customer


def work_order_payload(customer_id: str, order_date: str = "2026-08-13") -> dict:
    process_names = [
        ("artwork", "美工"),
        ("output", "輸出"),
        ("plate", "製版"),
        ("proof", "打樣"),
        ("printing", "印刷"),
        ("coating", "上光"),
        ("mounting", "裱紙"),
        ("die", "模具"),
        ("die_cutting", "軋型"),
        ("finishing", "加工"),
        ("gluing", "糊邊"),
        ("transport", "運送"),
        ("other", "其他"),
    ]
    return {
        "case_id": None,
        "order_date": order_date,
        "delivery_date": "2026-08-20",
        "customer_id": customer_id,
        "customer_order_number": "PO-SYNTHETIC-001",
        "product_name": "虛構彩盒",
        "order_quantity": "1000",
        "specification": "100 x 120 x 30 mm",
        "unit_price": "20.50",
        "plate_fee": "7000",
        "die_fee": "3500",
        "papers": [
            {"type": "face", "vendor": "虛構紙商", "paper": "白卡", "mill": "虛構紙廠"},
            {"type": "back", "paper": "牛卡"},
            {"type": "flute", "paper": "E 浪"},
        ],
        "print_specification": {
            "length": "100",
            "width": "120",
            "k_count": 1,
            "imposition_count": 2,
            "print_quantity": "1050",
            "variance": "50",
            "front": {"color_count": 4, "c": True, "m": True, "y": True, "k": True},
            "back": {"color_count": 0},
            "total_color_count": 4,
        },
        "processes": [
            {"code": code, "name": name, "content": f"{name}虛構說明"}
            for code, name in process_names
        ],
        "notes": "工單整體虛構備註",
    }
