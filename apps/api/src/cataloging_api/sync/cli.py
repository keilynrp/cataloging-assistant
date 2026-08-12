import argparse
import asyncio

import structlog

from cataloging_api.config import get_settings
from cataloging_api.db.session import SessionFactory
from cataloging_api.sync.service import SyncService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize the configured pilot collection")
    parser.add_argument("--resume-page", type=int, default=0)
    args = parser.parse_args()
    structlog.configure(processors=[structlog.processors.JSONRenderer()])
    run_id = await SyncService(get_settings(), SessionFactory).run(resume_page=args.resume_page)
    print(run_id)


if __name__ == "__main__":
    asyncio.run(main())
