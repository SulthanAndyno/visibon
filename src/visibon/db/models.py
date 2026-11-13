"""Model database SQLite untuk pengguna, struk, dan item belanja."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    receipts: Mapped[list[ReceiptRecord]] = relationship(
        "ReceiptRecord", back_populates="user", cascade="all, delete-orphan"
    )


class ReceiptRecord(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    merchant: Mapped[str | None] = mapped_column(String, nullable=True)
    date: Mapped[str | None] = mapped_column(String, nullable=True)
    time: Mapped[str | None] = mapped_column(String, nullable=True)

    subtotal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount: Mapped[int] = mapped_column(Integer, default=0)
    tax: Mapped[int] = mapped_column(Integer, default=0)
    service: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int | None] = mapped_column(Integer, nullable=True)

    payment_method: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, default="Lainnya")
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped[User] = relationship("User", back_populates="receipts")
    items: Mapped[list[ItemRecord]] = relationship(
        "ItemRecord", back_populates="receipt", cascade="all, delete-orphan"
    )


class ItemRecord(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_id: Mapped[int] = mapped_column(Integer, ForeignKey("receipts.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    qty: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subtotal: Mapped[int] = mapped_column(Integer)

    receipt: Mapped[ReceiptRecord] = relationship("ReceiptRecord", back_populates="items")
