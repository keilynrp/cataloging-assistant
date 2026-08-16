import asyncio
import contextlib

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cataloging_api.agent.routes import router as agent_router
from cataloging_api.api.routes import router
from cataloging_api.cataloging_contract_routes import router as cataloging_contract_router
from cataloging_api.config import get_settings
from cataloging_api.db.session import SessionFactory
from cataloging_api.notifications.broadcaster import broadcaster
from cataloging_api.notifications.routes import router as notifications_router
from cataloging_api.notifications.routes import ws_router as notifications_ws_router
from cataloging_api.notifications.worker import run_publisher_loop
from cataloging_api.provenance.routes import router as provenance_audit_router
from cataloging_api.vocabularies.dspace_routes import router as dspace_vocabulary_router
from cataloging_api.vocabularies.promotion_routes import router as vocabulary_promotion_router

settings = get_settings()
structlog.configure(
    processors=[structlog.contextvars.merge_contextvars, structlog.processors.JSONRenderer()]
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    publisher_task = asyncio.create_task(run_publisher_loop(SessionFactory, broadcaster))
    try:
        yield
    finally:
        publisher_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await publisher_task


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.catalog_web_origin],
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(cataloging_contract_router)
app.include_router(provenance_audit_router)
app.include_router(dspace_vocabulary_router)
app.include_router(vocabulary_promotion_router)
app.include_router(notifications_router)
app.include_router(notifications_ws_router)
app.include_router(agent_router)
