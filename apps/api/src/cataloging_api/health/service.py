import asyncio
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_OK = "DATABASE_OK"
DATABASE_UNREACHABLE = "DATABASE_UNREACHABLE"


@dataclass(frozen=True)
class ComponentCheck:
    name: str
    status: str
    detail_code: str


async def check_database(session: AsyncSession, timeout_seconds: float) -> ComponentCheck:
    """Read-only readiness probe for PostgreSQL, bounded by `timeout_seconds`.

    Connection failures and timeouts both collapse to DATABASE_UNREACHABLE so the
    response never carries raw driver exception text, hosts, or credentials.
    """
    try:
        await asyncio.wait_for(session.execute(text("select 1")), timeout=timeout_seconds)
    except (TimeoutError, SQLAlchemyError):
        return ComponentCheck(name="database", status="NOT_READY", detail_code=DATABASE_UNREACHABLE)
    return ComponentCheck(name="database", status="READY", detail_code=DATABASE_OK)
