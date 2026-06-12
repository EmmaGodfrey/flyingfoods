"""Supplier CRUD and search operations for procurement workflows."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Supplier, User
from app.schemas.procurement import SupplierCreate, SupplierListResponse, SupplierRead, SupplierUpdate
from app.services.search_indexing import delete_supplier_document, index_supplier_document


class SupplierNotFoundError(Exception):
    pass


def _to_supplier_read(supplier: Supplier) -> SupplierRead:
    return SupplierRead(
        supplier_id=supplier.id,
        branch_id=supplier.branch_id,
        name=supplier.name,
        contact_name=supplier.contact_name,
        phone=supplier.phone,
        email=supplier.email,
        is_active=supplier.is_active,
        created_at=supplier.created_at,
    )


async def create_supplier(
    session: AsyncSession,
    *,
    branch_id: int,
    actor: User,
    payload: SupplierCreate,
) -> SupplierRead:
    supplier = Supplier(branch_id=branch_id, **payload.model_dump())
    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)

    index_supplier_document(
        supplier_id=supplier.id,
        branch_id=supplier.branch_id,
        name=supplier.name,
        contact_name=supplier.contact_name,
        phone=supplier.phone,
        email=supplier.email,
        is_active=supplier.is_active,
    )
    return _to_supplier_read(supplier)


async def list_suppliers(
    session: AsyncSession,
    *,
    branch_id: int,
    limit: int,
    offset: int,
    search: str | None,
    is_active: bool | None,
) -> SupplierListResponse:
    filters = [Supplier.branch_id == branch_id]
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Supplier.name.ilike(term),
                Supplier.contact_name.ilike(term),
                Supplier.phone.ilike(term),
                Supplier.email.ilike(term),
            )
        )
    if is_active is not None:
        filters.append(Supplier.is_active == is_active)

    total_stmt = select(func.count()).select_from(Supplier).where(*filters)
    total = int((await session.execute(total_stmt)).scalar_one())

    items_stmt = (
        select(Supplier)
        .where(*filters)
        .order_by(Supplier.created_at.desc(), Supplier.id.desc())
        .limit(limit)
        .offset(offset)
    )
    suppliers = (await session.execute(items_stmt)).scalars().all()

    return SupplierListResponse(items=[_to_supplier_read(supplier) for supplier in suppliers], total=total, limit=limit, offset=offset)


async def get_supplier_or_none(session: AsyncSession, *, branch_id: int, supplier_id: int) -> Supplier | None:
    stmt = select(Supplier).where(Supplier.id == supplier_id, Supplier.branch_id == branch_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_supplier(
    session: AsyncSession,
    *,
    branch_id: int,
    supplier: Supplier,
    payload: SupplierUpdate,
) -> SupplierRead:
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(supplier, key, value)
    await session.commit()
    await session.refresh(supplier)

    index_supplier_document(
        supplier_id=supplier.id,
        branch_id=supplier.branch_id,
        name=supplier.name,
        contact_name=supplier.contact_name,
        phone=supplier.phone,
        email=supplier.email,
        is_active=supplier.is_active,
    )
    return _to_supplier_read(supplier)


async def delete_supplier(
    session: AsyncSession,
    *,
    branch_id: int,
    supplier: Supplier,
) -> None:
    supplier_id = supplier.id
    await session.delete(supplier)
    await session.commit()
    delete_supplier_document(supplier_id=supplier_id, branch_id=branch_id)
