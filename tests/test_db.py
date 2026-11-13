import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from visibon.db.models import Base
from visibon.db.repository import (
    get_monthly_summary,
    get_or_create_user,
    get_recent_receipts,
    save_receipt,
)
from visibon.schemas import Receipt


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_user(async_session):
    u1 = await get_or_create_user(async_session, 12345, "shuu", "Shuu")
    assert u1.id is not None
    assert u1.telegram_id == 12345

    # Should fetch existing user
    u2 = await get_or_create_user(async_session, 12345)
    assert u2.id == u1.id


@pytest.mark.asyncio
async def test_save_and_retrieve_receipt(async_session):
    user = await get_or_create_user(async_session, 999, "tester")
    receipt = Receipt.model_validate(
        {
            "merchant": "Alfamart Margonda",
            "date": "2026-11-14",
            "time": "02:00",
            "items": [
                {"name": "Ultra Milk", "qty": 2, "unit_price": 7000, "subtotal": 14000},
                {"name": "Chiki", "qty": 1, "unit_price": 6000, "subtotal": 6000},
            ],
            "total": 20000,
            "category": "Makanan & Minuman",
        }
    )

    record = await save_receipt(async_session, user.id, receipt, is_valid=True)
    assert record.id is not None
    assert record.merchant == "Alfamart Margonda"
    assert len(record.items) == 2

    # Recent receipts
    recent = await get_recent_receipts(async_session, user.id, limit=5)
    assert len(recent) == 1
    assert recent[0].total == 20000

    # Monthly summary
    summary = await get_monthly_summary(async_session, user.id, 2026, 11)
    assert summary["total_spent"] == 20000
    assert summary["total_receipts"] == 1
    assert "Makanan & Minuman" in summary["by_category"]
