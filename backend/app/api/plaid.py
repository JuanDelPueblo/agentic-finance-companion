from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.deps import CurrentPrincipal
from app.integrations.plaid import (
    PlaidProvider,
    PlaidWebhook,
    WebhookVerificationError,
    get_plaid,
)
from app.schemas.common import ErrorResponse
from app.schemas.finance import LinkedAccount, LinkedItem, LinkTokenResponse, PublicTokenExchange

router = APIRouter(prefix="/plaid", tags=["plaid"])
Plaid = Annotated[PlaidProvider, Depends(get_plaid)]
PLAID_ERRORS: dict[int | str, dict[str, object]] = {
    409: {"model": ErrorResponse, "description": "The connection needs to be re-linked"},
    502: {"model": ErrorResponse, "description": "Plaid returned an error"},
}


@router.post("/link-token", responses=PLAID_ERRORS)
async def create_link_token(principal: CurrentPrincipal, plaid: Plaid) -> LinkTokenResponse:
    """Start Plaid Link. With the mock provider, skip Link and exchange `public-mock-<any>`."""
    token = await plaid.create_link_token(principal.subject)
    return LinkTokenResponse(link_token=token.link_token, expiration=token.expiration)


@router.post("/exchange", responses=PLAID_ERRORS)
async def exchange_public_token(
    body: PublicTokenExchange, principal: CurrentPrincipal, plaid: Plaid
) -> LinkedItem:
    item = await plaid.exchange_public_token(body.public_token)
    accounts = await plaid.get_accounts(item.access_token)
    # TODO(persistence): store the Item with `app.security.encrypt_token(item.access_token)`
    # and its accounts for `principal`, then run the first transaction sync.
    return LinkedItem(
        item_id=item.item_id,
        accounts=[LinkedAccount(name=a.name, type=a.type, subtype=a.subtype) for a in accounts],
    )


@router.post(
    "/webhook",
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: {"model": ErrorResponse}},
)
async def receive_webhook(
    request: Request,
    plaid: Plaid,
    plaid_verification: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    """Called by Plaid, not the frontend. Verified by signature instead of user auth."""
    try:
        webhook: PlaidWebhook = await plaid.verify_webhook(await request.body(), plaid_verification)
    except WebhookVerificationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    # TODO(persistence): store the event (webhook_events) before processing it, then mark
    # the Item for re-link (`webhook.requires_relink`) or sync (`webhook.transactions_updated`).
    _ = webhook
    return {"received": True}
