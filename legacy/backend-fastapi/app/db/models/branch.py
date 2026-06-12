"""Branch model for tenant partitioning across all ERP modules."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    users = relationship("User", back_populates="branch")
    categories = relationship("Category", back_populates="branch")
    units = relationship("Unit", back_populates="branch")
    suppliers = relationship("Supplier", back_populates="branch")
    products = relationship("Product", back_populates="branch")
    stock_movements = relationship("StockMovement", back_populates="branch")
    boms = relationship("BillOfMaterial", back_populates="branch")
    audit_logs = relationship("AuditLog", back_populates="branch")
    sales = relationship("Sale", back_populates="branch")
    sale_line_items = relationship("SaleLineItem", back_populates="branch")
