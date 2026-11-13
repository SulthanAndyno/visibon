"""Operasi database (CRUD) untuk struk dan pengguna."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from visibon.db.models import ItemRecord, ReceiptRecord, User
from visibon.schemas import Receipt


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    elif username and user.username != username:
        user.username = username
        await session.commit()

    return user


async def save_receipt(
    session: AsyncSession,
    user_id: int,
    receipt: Receipt,
    is_valid: bool = True,
    image_path: str | None = None,
) -> ReceiptRecord:
    record = ReceiptRecord(
        user_id=user_id,
        merchant=receipt.merchant,
        date=receipt.date or datetime.now().strftime("%Y-%m-%d"),
        time=receipt.time or datetime.now().strftime("%H:%M"),
        subtotal=receipt.subtotal,
        discount=receipt.discount,
        tax=receipt.tax,
        service=receipt.service,
        total=receipt.total,
        payment_method=receipt.payment_method,
        category=receipt.category or "Lainnya",
        is_valid=is_valid,
        image_path=image_path,
    )
    session.add(record)
    await session.flush()  # dapatkan record.id

    for item in receipt.items:
        session.add(
            ItemRecord(
                receipt_id=record.id,
                name=item.name,
                qty=item.qty,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
        )

    await session.commit()
    await session.refresh(record, ["items"])
    return record


async def get_recent_receipts(
    session: AsyncSession, user_id: int, limit: int = 5
) -> list[ReceiptRecord]:
    stmt = (
        select(ReceiptRecord)
        .where(ReceiptRecord.user_id == user_id)
        .order_by(desc(ReceiptRecord.id))
        .limit(limit)
        .options(selectinload(ReceiptRecord.items))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_monthly_summary(session: AsyncSession, user_id: int, year: int, month: int) -> dict:
    prefix = f"{year:04d}-{month:02d}"
    stmt = (
        select(
            ReceiptRecord.category,
            func.count(ReceiptRecord.id).label("count"),
            func.sum(ReceiptRecord.total).label("total_spent"),
        )
        .where(ReceiptRecord.user_id == user_id)
        .where(ReceiptRecord.date.startswith(prefix))
        .group_by(ReceiptRecord.category)
    )
    result = await session.execute(stmt)
    rows = result.all()

    by_category = {}
    total_spent = 0
    total_count = 0
    for cat, count, amount in rows:
        amount = amount or 0
        by_category[cat] = {"count": count, "total": amount}
        total_spent += amount
        total_count += count

    return {
        "year": year,
        "month": month,
        "total_spent": total_spent,
        "total_receipts": total_count,
        "by_category": by_category,
    }
