from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, PlaidItem, Transaction
from app.plaid.client import PlaidError, call, decrypt_token, encrypt_token, get_plaid


async def link_item(
    session: AsyncSession, user_id: UUID, public_token: str, institution_name: str | None
) -> PlaidItem:
    """Exchange a public token from Plaid Link, save the item, and import its data."""
    exchange = await call(
        get_plaid().item_public_token_exchange,
        ItemPublicTokenExchangeRequest(public_token=public_token),
    )
    item = PlaidItem(
        user_id=user_id,
        plaid_item_ref=exchange.item_id,
        access_token_encrypted=encrypt_token(exchange.access_token),
        institution_name=institution_name,
        connection_status="healthy",
    )
    session.add(item)
    # Save the item before syncing so a failed sync doesn't lose the access token.
    await session.commit()
    await sync_item(session, item)
    return item


async def sync_item(session: AsyncSession, item: PlaidItem) -> None:
    """Import the item's accounts and the transaction changes since the last sync.

    If any Plaid call fails, nothing is saved and the next sync starts from the same cursor.
    """
    access_token = decrypt_token(item.access_token_encrypted)
    try:
        await _sync_accounts(session, item, access_token)
        await _sync_transactions(session, item, access_token)
    except PlaidError as error:
        await session.rollback()
        if error.code == "ITEM_LOGIN_REQUIRED":
            item.connection_status = "login_required"
            await session.commit()
        raise
    item.last_synced_at = datetime.now(UTC)
    await session.commit()


async def _sync_accounts(session: AsyncSession, item: PlaidItem, access_token: str) -> None:
    response = await call(get_plaid().accounts_get, AccountsGetRequest(access_token=access_token))
    rows = await session.scalars(select(Account).where(Account.item_id == item.item_id))
    existing = {row.plaid_account_ref: row for row in rows}

    for account in response.to_dict()["accounts"]:
        row = existing.get(account["account_id"])
        if row is None:
            row = Account(item_id=item.item_id, plaid_account_ref=account["account_id"])
            session.add(row)
        balances = account["balances"]
        row.name = account["name"][:120]
        row.account_type = str(account["type"])
        row.account_subtype = str(account["subtype"]) if account.get("subtype") else None
        row.current_balance = _decimal(balances.get("current"))
        row.available_balance = _decimal(balances.get("available"))
        row.currency_code = balances.get("iso_currency_code")
    await session.flush()


async def _sync_transactions(session: AsyncSession, item: PlaidItem, access_token: str) -> None:
    accounts = await session.scalars(select(Account).where(Account.item_id == item.item_id))
    account_ids = {account.plaid_account_ref: account.account_id for account in accounts}
    rows = await session.scalars(
        select(Transaction).join(Account).where(Account.item_id == item.item_id)
    )
    existing = {row.plaid_transaction_ref: row for row in rows}

    has_more = True
    while has_more:
        request = TransactionsSyncRequest(access_token=access_token)
        if item.sync_cursor:
            request.cursor = item.sync_cursor
        page = (await call(get_plaid().transactions_sync, request)).to_dict()

        for transaction in page["added"] + page["modified"]:
            row = existing.get(transaction["transaction_id"])
            if row is None:
                row = Transaction(plaid_transaction_ref=transaction["transaction_id"])
                session.add(row)
                existing[row.plaid_transaction_ref] = row
            merchant = transaction.get("merchant_name") or transaction.get("name")
            row.account_id = account_ids[transaction["account_id"]]
            # Plaid amounts are positive when money leaves the account.
            row.amount = Decimal(str(transaction["amount"]))
            row.posted_date = transaction["date"]
            row.merchant_name = merchant[:160] if merchant else None
            row.category = (transaction.get("personal_finance_category") or {}).get("primary")
            row.sync_state = "pending" if transaction["pending"] else "posted"
            row.updated_at = datetime.now(UTC)

        for transaction in page["removed"]:
            row = existing.pop(transaction["transaction_id"], None)
            if row is not None:
                await session.delete(row)

        item.sync_cursor = page["next_cursor"]
        has_more = page["has_more"]


def _decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))
