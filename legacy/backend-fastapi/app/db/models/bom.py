"""Bill of materials model linking finished goods to ingredient products."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BillOfMaterial(Base):
    __tablename__ = "bill_of_materials"
    __table_args__ = (
        CheckConstraint("product_id <> ingredient_id", name="ck_bom_product_not_self"),
        UniqueConstraint("branch_id", "product_id", "ingredient_id", name="uq_bom_branch_product_ingredient"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    branch = relationship("Branch", back_populates="boms")
    finished_product = relationship("Product", back_populates="bom_outputs", foreign_keys=[product_id])
    ingredient_product = relationship("Product", back_populates="bom_inputs", foreign_keys=[ingredient_id])
