"""Read endpoints for the frontend.

STUB: these return synthetic data from app/fixtures.py. Replace each body with real
queries when persistence exists. Keep the response models unless you
change the contract on purpose.
"""

from fastapi import APIRouter

from app import fixtures
from app.api.deps import CurrentPrincipal
from app.schemas.finance import Account, Transaction

router = APIRouter(tags=["finance"])


@router.get("/accounts")
async def list_accounts(principal: CurrentPrincipal) -> list[Account]:
    return fixtures.accounts()


@router.get("/transactions")
async def list_transactions(principal: CurrentPrincipal) -> list[Transaction]:
    return fixtures.transactions()
