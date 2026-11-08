"""Link a Plaid Sandbox bank to the local test user and import its accounts and transactions.

Run from backend/ after `uv run alembic upgrade head`:

    uv run python scripts/plaid_sandbox_link.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from sqlalchemy import func, select

from app.db import get_engine, get_session
from app.dependencies import get_current_user_id
from app.models import Account, Transaction
from app.plaid.client import call, get_plaid
from app.plaid.sync import link_item, sync_item

INSTITUTION_ID = "ins_109508"  # First Platypus Bank, a Plaid Sandbox institution
INSTITUTION_NAME = "First Platypus Bank"


async def main() -> None:
    public_token = await call(
        get_plaid().sandbox_public_token_create,
        SandboxPublicTokenCreateRequest(
            institution_id=INSTITUTION_ID, initial_products=[Products("transactions")]
        ),
    )
    async for session in get_session():
        user_id = await get_current_user_id(session)
        item = await link_item(session, user_id, public_token.public_token, INSTITUTION_NAME)
        # A new Sandbox item can take a few seconds to have transactions ready.
        for _ in range(10):
            count = await session.scalar(
                select(func.count())
                .select_from(Transaction)
                .join(Account)
                .where(Account.item_id == item.item_id)
            )
            if count:
                break
            await asyncio.sleep(3)
            await sync_item(session, item)
        print(f"Linked {INSTITUTION_NAME} as item {item.item_id} with {count} transactions.")
    await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
