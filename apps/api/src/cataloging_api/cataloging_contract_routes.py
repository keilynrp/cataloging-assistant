from fastapi import APIRouter

from cataloging_api.cataloging_contract import contract_payload

router = APIRouter(tags=["Cataloging contract"])


@router.get("/api/cataloging-contract")
async def get_cataloging_contract() -> dict[str, object]:
    return contract_payload()
