"""Broker integration API routes."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.modules.broker.schemas import (
    BrokerAuthUrlResponse,
    BrokerCallbackRequest,
    BrokerCallbackResponse,
    BrokerCredentialCreate,
    BrokerCredentialResponse,
    BrokerCredentialStatus,
    BrokerDisconnectResponse,
    BrokerListResponse,
    BrokerType,
)
from app.modules.broker.service import BrokerService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=BrokerListResponse)
async def list_brokers(db: DbSession, current_user: CurrentUser) -> BrokerListResponse:
    """List all broker integrations and their status."""
    service = BrokerService(db)
    credentials = await service.get_all_credentials(current_user.id)

    # Build status for each supported broker
    broker_statuses = []
    configured_brokers = {c.broker_type: c for c in credentials}

    for broker_type in BrokerType:
        cred = configured_brokers.get(broker_type.value)
        if cred:
            broker_statuses.append(
                BrokerCredentialStatus(
                    broker_type=cred.broker_type,
                    is_configured=True,
                    is_connected=cred.is_connected,
                    is_active=cred.is_active,
                    client_id=cred.masked_client_id,
                    last_used_at=cred.last_used_at,
                    token_expires_at=cred.token_expires_at,
                )
            )
        else:
            broker_statuses.append(
                BrokerCredentialStatus(
                    broker_type=broker_type.value,
                    is_configured=False,
                    is_connected=False,
                    is_active=False,
                )
            )

    return BrokerListResponse(brokers=broker_statuses)


@router.get("/{broker_type}", response_model=BrokerCredentialStatus)
async def get_broker_status(
    broker_type: BrokerType, db: DbSession, current_user: CurrentUser
) -> BrokerCredentialStatus:
    """Get status of a specific broker integration."""
    service = BrokerService(db)
    cred = await service.get_credential(current_user.id, broker_type.value)

    if not cred:
        return BrokerCredentialStatus(
            broker_type=broker_type.value,
            is_configured=False,
            is_connected=False,
            is_active=False,
        )

    return BrokerCredentialStatus(
        broker_type=cred.broker_type,
        is_configured=True,
        is_connected=cred.is_connected,
        is_active=cred.is_active,
        client_id=cred.masked_client_id,
        last_used_at=cred.last_used_at,
        token_expires_at=cred.token_expires_at,
    )


@router.post("", response_model=BrokerCredentialResponse)
async def save_broker_credentials(
    data: BrokerCredentialCreate, db: DbSession, current_user: CurrentUser
) -> BrokerCredentialResponse:
    """Save broker API credentials (encrypted at rest)."""
    service = BrokerService(db)
    credential = await service.create_or_update_credential(current_user.id, data)

    return BrokerCredentialResponse(
        id=credential.id,
        broker_type=credential.broker_type,
        client_id=credential.masked_client_id,
        redirect_uri=credential.redirect_uri,
        is_connected=credential.is_connected,
        is_active=credential.is_active,
        token_expires_at=credential.token_expires_at,
        created_at=credential.created_at,
        updated_at=credential.updated_at,
        last_used_at=credential.last_used_at,
    )


@router.delete("/{broker_type}", response_model=BrokerDisconnectResponse)
async def delete_broker(
    broker_type: BrokerType, db: DbSession, current_user: CurrentUser
) -> BrokerDisconnectResponse:
    """Delete broker credentials permanently."""
    service = BrokerService(db)
    deleted = await service.delete_credential(current_user.id, broker_type.value)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {broker_type.value} credentials found",
        )

    return BrokerDisconnectResponse(
        success=True,
        message=f"{broker_type.value} credentials deleted",
        broker_type=broker_type.value,
    )


@router.post("/{broker_type}/disconnect", response_model=BrokerDisconnectResponse)
async def disconnect_broker(
    broker_type: BrokerType, db: DbSession, current_user: CurrentUser
) -> BrokerDisconnectResponse:
    """Disconnect broker (clear access token but keep credentials)."""
    service = BrokerService(db)
    disconnected = await service.disconnect_broker(current_user.id, broker_type.value)

    if not disconnected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {broker_type.value} credentials found",
        )

    return BrokerDisconnectResponse(
        success=True,
        message=f"{broker_type.value} disconnected",
        broker_type=broker_type.value,
    )


# ============================================================================
# Fyers-specific OAuth endpoints
# ============================================================================


@router.get("/fyers/auth-url", response_model=BrokerAuthUrlResponse)
async def get_fyers_auth_url(db: DbSession, current_user: CurrentUser) -> BrokerAuthUrlResponse:
    """Generate Fyers OAuth authorization URL.

    User must first save their Fyers credentials via POST /brokers.
    Then call this endpoint to get the auth URL to redirect to Fyers login.
    """
    from shared.providers.broker.fyers_auth import FyersAuthHandler, FyersCredentials

    service = BrokerService(db)
    cred = await service.get_credential(current_user.id, BrokerType.FYERS.value)

    if not cred:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fyers credentials not configured. Save credentials first.",
        )

    try:
        # Create auth handler with user's credentials
        fyers_creds = FyersCredentials(
            client_id=cred.client_id,
            secret_key=cred.secret_key,  # Decrypted via property
            redirect_uri=cred.redirect_uri,
        )
        auth_handler = FyersAuthHandler(fyers_creds)
        auth_url = auth_handler.generate_auth_url()

        return BrokerAuthUrlResponse(
            auth_url=auth_url,
            broker_type=BrokerType.FYERS.value,
            message="Redirect user to auth_url to complete Fyers OAuth flow",
        )
    except Exception as e:
        logger.error(f"Failed to generate Fyers auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auth URL: {str(e)}",
        )


@router.post("/fyers/callback", response_model=BrokerCallbackResponse)
async def fyers_oauth_callback(
    data: BrokerCallbackRequest, db: DbSession, current_user: CurrentUser
) -> BrokerCallbackResponse:
    """Handle Fyers OAuth callback and exchange auth code for access token.

    After user completes Fyers login, they are redirected with an auth_code.
    Send that code here to exchange it for an access token.
    """
    from shared.providers.broker.fyers_auth import FyersAuthHandler, FyersCredentials

    service = BrokerService(db)
    cred = await service.get_credential(current_user.id, BrokerType.FYERS.value)

    if not cred:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fyers credentials not configured",
        )

    try:
        # Create auth handler with user's credentials
        fyers_creds = FyersCredentials(
            client_id=cred.client_id,
            secret_key=cred.secret_key,  # Decrypted via property
            redirect_uri=cred.redirect_uri,
        )
        auth_handler = FyersAuthHandler(fyers_creds)

        # Exchange auth code for access token
        access_token = auth_handler.exchange_auth_code(data.auth_code)

        # Save encrypted access token
        await service.update_access_token(
            user_id=current_user.id,
            broker_type=BrokerType.FYERS.value,
            access_token=access_token,
            expires_at=None,  # Fyers tokens don't have explicit expiry
        )

        return BrokerCallbackResponse(
            success=True,
            message="Successfully connected to Fyers",
            broker_type=BrokerType.FYERS.value,
            is_connected=True,
        )
    except ValueError as e:
        logger.error(f"Fyers token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Fyers OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}",
        )
