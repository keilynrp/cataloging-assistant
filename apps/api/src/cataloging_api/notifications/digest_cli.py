import asyncio
import json

from cataloging_api.db.session import SessionFactory
from cataloging_api.notifications.digest import build_digest_summary


async def main() -> None:
    async with SessionFactory() as session:
        event = await build_digest_summary(session)
        await session.commit()
    if event is None:
        print(json.dumps({"emitted": False}))
    else:
        print(
            json.dumps(
                {"emitted": True, "event_id": str(event.event_id), "summary": event.summary},
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
