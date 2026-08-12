import asyncio
import json

from cataloging_api.config import get_settings
from cataloging_api.db.session import SessionFactory
from cataloging_api.diagnostics.service import DiagnosticsService


async def main() -> None:
    settings = get_settings()
    result = await DiagnosticsService(
        SessionFactory,
        required_fields=settings.required_fields,
    ).rebuild()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
