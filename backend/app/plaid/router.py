from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from plaid.model.country_code import CountryCode
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Settings, get_session
from app.dependencies import get_current_user_id
from app.models import PlaidItem, WebhookEvent
from app.plaid.client import call, decrypt_token, get_plaid
from app.plaid.sync import link_item, sync_item

router = APIRouter(prefix="/api/plaid", tags=["plaid"])

CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
Session = Annotated[AsyncSession, Depends(get_session)]


class LinkTokenRequest(BaseModel):
    # Send this to reconnect a broken bank connection (Plaid Link update mode).
    item_id: UUID | None = None


class LinkTokenResponse(BaseModel):
    link_token: str


class ExchangeRequest(BaseModel):
    public_token: str
    # Plaid Link's onSuccess metadata includes the institution name.
    institution_name: str | None = None


class LinkedItem(BaseModel):
    item_id: UUID
    institution_name: str | None
    connection_status: str


class PlaidWebhook(BaseModel):
    webhook_type: str
    webhook_code: str
    item_id: str | None = None
    error: dict[str, Any] | None = None


@router.post("/link-token")
async def create_link_token(
    body: LinkTokenRequest, user_id: CurrentUserId, session: Session
) -> LinkTokenResponse:
    options: dict[str, Any] = {}
    if body.item_id:
        item = await session.get(PlaidItem, body.item_id)
        if item is None or item.user_id != user_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
        options["access_token"] = decrypt_token(item.access_token_encrypted)
    else:
        options["products"] = [Products("transactions")]
    if webhook_url := Settings().plaid_webhook_url:
        options["webhook"] = webhook_url

    request = LinkTokenCreateRequest(
        client_name="Agentic Finance Companion",
        language="en",
        country_codes=[CountryCode("US")],
        user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),
        **options,
    )
    response = await call(get_plaid().link_token_create, request)
    return LinkTokenResponse(link_token=response.link_token)


@router.post("/exchange")
async def exchange_public_token(
    body: ExchangeRequest, user_id: CurrentUserId, session: Session
) -> LinkedItem:
    item = await link_item(session, user_id, body.public_token, body.institution_name)
    return LinkedItem(
        item_id=item.item_id,
        institution_name=item.institution_name,
        connection_status=item.connection_status,
    )


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def receive_webhook(payload: PlaidWebhook, session: Session) -> None:
    item = await session.scalar(
        select(PlaidItem).where(PlaidItem.plaid_item_ref == payload.item_id)
    )
    if item is None:
        return
    event = WebhookEvent(
        item_id=item.item_id, webhook_type=payload.webhook_type, webhook_code=payload.webhook_code
    )
    session.add(event)
    await session.commit()

    code = payload.webhook_code
    if payload.webhook_type == "TRANSACTIONS" and code == "SYNC_UPDATES_AVAILABLE":
        await sync_item(session, item)
    elif payload.webhook_type == "ITEM" and code == "LOGIN_REPAIRED":
        item.connection_status = "healthy"
    elif payload.webhook_type == "ITEM" and (
        code in ("PENDING_EXPIRATION", "PENDING_DISCONNECT")
        or (code == "ERROR" and (payload.error or {}).get("error_code") == "ITEM_LOGIN_REQUIRED")
    ):
        item.connection_status = "login_required"

    event.processed_at = datetime.now(UTC)
    await session.commit()
