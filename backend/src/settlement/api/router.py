# context.md §10: All endpoints versioned under /v1/.
# context.md §10: All responses use ApiResponse[T] envelope.
# context.md §14: Auth via Phase One get_current_user + require_role.

from __future__ import annotations

import uuid

import algosdk.mnemonic as algo_mnemonic  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from src.shared.api.responses import ApiResponse, success_response
from src.shared.infrastructure.logging import get_logger
from src.identity.api.dependencies import (
    get_current_user,
    rate_limit,
    require_role,
)
from src.identity.domain.user import User
from src.settlement.api.dependencies import get_settlement_service, SettlementServiceDep
from src.settlement.api.schemas import (
    DeployEscrowRequest,
    DeployEscrowResponse,
    EscrowResponse,
    FreezeEscrowRequest,
    FundEscrowRequest,
    RefundEscrowRequest,
    ReleaseEscrowRequest,
    SettlementResponse,
)
from src.settlement.application.commands import (
    ApproveEscrowCommand,
    DeployEscrowCommand,
    FreezeEscrowCommand,
    FundEscrowCommand,
    RefundEscrowCommand,
    RejectEscrowCommand,
    ReleaseEscrowCommand,
    UnfreezeEscrowCommand,
)
from src.settlement.application.queries import (
    GetEscrowByIdQuery,
    GetEscrowQuery,
    GetSettlementsQuery,
)

log = get_logger(__name__)

router = APIRouter(prefix="/v1/escrow", tags=["escrow"])


# ── GET /v1/escrow — list escrows ─────────────────────────────────────────────


@router.get(
    "",
    response_model=ApiResponse[list[EscrowResponse]],
    summary="List escrow contracts for current user's enterprise",
    dependencies=[Depends(rate_limit)],
)
async def list_escrows(
    escrow_status: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[list[EscrowResponse]]:
    escrows = await svc.list_escrows(
        enterprise_id=current_user.enterprise_id,
        status=escrow_status,
        limit=limit,
        offset=offset,
    )
    return success_response([EscrowResponse.from_domain(e) for e in escrows])


# ── GET /v1/escrow/pending — list escrows awaiting admin approval ─────────────


class PendingEscrowResponse(BaseModel):
    escrow_id: str
    session_id: str
    amount_microalgo: int
    amount_algo: float
    agreed_price_inr: float | None = None
    buyer_enterprise_id: str | None = None
    seller_enterprise_id: str | None = None
    buyer_name: str | None = None
    seller_name: str | None = None
    status: str
    created_at: str


@router.get(
    "/pending",
    response_model=ApiResponse[list[PendingEscrowResponse]],
    summary="List escrows pending admin approval",
    dependencies=[Depends(require_role("ADMIN")), Depends(rate_limit)],
)
async def list_pending_escrows(
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[list[PendingEscrowResponse]]:
    """Admin-only: list all escrows in PENDING_APPROVAL state."""
    escrows = await svc.list_pending_approvals()

    items = []
    for e in escrows:
        item = PendingEscrowResponse(
            escrow_id=str(e.id),
            session_id=str(e.session_id),
            amount_microalgo=e.amount.value.value,
            amount_algo=e.amount.value.value / 1_000_000,
            status=e.status.value,
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        items.append(item)

    return success_response(items)


# ── GET /v1/escrow/{session_id} ───────────────────────────────────────────────


@router.get(
    "/{session_id}",
    response_model=ApiResponse[EscrowResponse],
    summary="Get escrow state by negotiation session ID",
    dependencies=[Depends(rate_limit)],
)
async def get_escrow(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[EscrowResponse]:
    escrow = await svc.get_escrow(
        GetEscrowQuery(
            session_id=session_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )
    return success_response(EscrowResponse.from_domain(escrow))


# ── POST /v1/escrow/{session_id}/deploy ───────────────────────────────────────


@router.post(
    "/{session_id}/deploy",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[DeployEscrowResponse],
    summary="Deploy Algorand escrow contract (ADMIN only — Phase 2 testing convenience)",
    dependencies=[Depends(require_role("ADMIN")), Depends(rate_limit)],
)
async def deploy_escrow(
    session_id: uuid.UUID,
    request_body: DeployEscrowRequest,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[DeployEscrowResponse]:
    """
    Phase Two convenience endpoint: deploy escrow directly via API.
    In Phase Four+, this is triggered automatically by the SessionAgreed domain event.
    """
    result = await svc.deploy_escrow(
        DeployEscrowCommand(
            session_id=session_id,
            buyer_enterprise_id=request_body.buyer_enterprise_id,
            seller_enterprise_id=request_body.seller_enterprise_id,
            buyer_algo_address=request_body.buyer_algo_address,
            seller_algo_address=request_body.seller_algo_address,
            agreed_price_microalgo=request_body.agreed_price_microalgo,
        )
    )
    return success_response(
        DeployEscrowResponse(
            escrow_id=result["escrow_id"],
            algo_app_id=result["algo_app_id"],
            algo_app_address=result["algo_app_address"],
            status=result["status"],
            tx_id=result["tx_id"],
        )
    )


# ── POST /v1/escrow/{escrow_id}/approve — admin approves and deploys on-chain ─


class ApproveEscrowRequest(BaseModel):
    pass  # No body needed, admin identity from JWT


@router.post(
    "/{escrow_id}/approve",
    response_model=ApiResponse[dict],
    summary="Admin approves a pending escrow — transitions to APPROVED, buyer deploys via Pera Wallet",
    dependencies=[Depends(require_role("ADMIN")), Depends(rate_limit)],
)
async def approve_escrow(
    escrow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[dict]:
    result = await svc.approve_escrow(
        ApproveEscrowCommand(
            escrow_id=escrow_id,
            admin_user_id=current_user.id,
        )
    )
    # result = {"escrow_id": ..., "status": "APPROVED", "message": ...}
    return success_response({
        "escrow_id": str(result["escrow_id"]),
        "status": result["status"],
        "message": result.get("message", ""),
    })




# ── POST /v1/escrow/{escrow_id}/reject — admin rejects escrow ─────────────────


class RejectEscrowRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500, description="Reason for rejection")


class RejectEscrowResponse(BaseModel):
    escrow_id: str
    status: str
    reason: str


@router.post(
    "/{escrow_id}/reject",
    response_model=ApiResponse[RejectEscrowResponse],
    summary="Admin rejects a pending escrow",
    dependencies=[Depends(require_role("ADMIN")), Depends(rate_limit)],
)
async def reject_escrow(
    escrow_id: uuid.UUID,
    request_body: RejectEscrowRequest,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[RejectEscrowResponse]:
    result = await svc.reject_escrow(
        RejectEscrowCommand(
            escrow_id=escrow_id,
            admin_user_id=current_user.id,
            reason=request_body.reason,
        )
    )
    return success_response(
        RejectEscrowResponse(
            escrow_id=str(result["escrow_id"]),
            status=result["status"],
            reason=result["reason"],
        )
    )


# ── POST /v1/escrow/{session_id}/platform-deploy ─────────────────────────────
#    Uses the platform wallet (ALGORAND_ESCROW_CREATOR_MNEMONIC) so the buyer
#    does NOT need to re-connect Pera Wallet just for deployment.


class PlatformDeployResponse(BaseModel):
    escrow_id: str
    app_id: int
    app_address: str
    tx_id: str
    status: str = "DEPLOYED"


@router.post(
    "/{session_id}/platform-deploy",
    response_model=ApiResponse[PlatformDeployResponse],
    summary="Deploy escrow smart contract using the platform wallet",
    dependencies=[Depends(rate_limit)],
)
async def platform_deploy_escrow(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[PlatformDeployResponse]:
    """
    Deploy the escrow smart contract server-side using the platform wallet mnemonic.

    This avoids requiring the buyer to re-connect their Pera Wallet just for
    contract deployment. The buyer's Pera Wallet is only needed for funding
    (actual ALGO transfer) and release.

    Flow:
      1. Validates escrow is in APPROVED state
      2. Looks up buyer/seller Algorand addresses from enterprise profiles
      3. Deploys via AlgorandGateway.deploy_escrow() using platform wallet
      4. Persists APPROVED → DEPLOYED transition
    """
    from fastapi import HTTPException
    from src.settlement.application.queries import GetEscrowQuery
    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    from src.identity.infrastructure.models import EnterpriseModel
    from sqlalchemy import select

    # 1. Get escrow by session_id
    escrow = await svc.get_escrow(
        GetEscrowQuery(
            session_id=session_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )

    if escrow.status.value not in ("APPROVED", "PENDING_APPROVAL"):
        raise HTTPException(
            status_code=409,
            detail=f"Escrow cannot be deployed in state: {escrow.status.value}",
        )

    # 2. Look up buyer/seller Algorand addresses from enterprise profiles
    buyer_address = ""
    seller_address = ""

    if hasattr(escrow, 'buyer_address') and escrow.buyer_address:
        buyer_address = escrow.buyer_address
    if hasattr(escrow, 'seller_address') and escrow.seller_address:
        seller_address = escrow.seller_address

    # If addresses not on escrow, look up from enterprise profiles
    if not buyer_address or not seller_address:
        try:
            from src.settlement.infrastructure.models import EscrowContractModel
            from sqlalchemy import select as sql_select

            # Get enterprise IDs from escrow model
            stmt = sql_select(EscrowContractModel).where(
                EscrowContractModel.session_id == session_id
            )
            result = await svc._uow._session.execute(stmt)
            escrow_model = result.scalar_one_or_none()

            if escrow_model:
                buyer_eid = escrow_model.buyer_enterprise_id
                seller_eid = escrow_model.seller_enterprise_id

                if buyer_eid and not buyer_address:
                    ent_stmt = sql_select(EnterpriseModel).where(EnterpriseModel.id == buyer_eid)
                    ent_result = await svc._uow._session.execute(ent_stmt)
                    buyer_ent = ent_result.scalar_one_or_none()
                    if buyer_ent and buyer_ent.algorand_wallet:
                        buyer_address = buyer_ent.algorand_wallet

                if seller_eid and not seller_address:
                    ent_stmt = sql_select(EnterpriseModel).where(EnterpriseModel.id == seller_eid)
                    ent_result = await svc._uow._session.execute(ent_stmt)
                    seller_ent = ent_result.scalar_one_or_none()
                    if seller_ent and seller_ent.algorand_wallet:
                        seller_address = seller_ent.algorand_wallet
        except Exception as lookup_exc:
            log.warning("platform_deploy_enterprise_lookup_failed", error=str(lookup_exc))

    # 3. Deploy using platform wallet
    gateway = AlgorandGateway()

    amount_microalgo = escrow.amount.value.value if hasattr(escrow.amount, 'value') else 100_000

    # Use platform creator address as fallback for buyer/seller if not found
    if not buyer_address:
        buyer_address = gateway._creator_address or ""
    if not seller_address:
        seller_address = gateway._creator_address or ""

    if not gateway._creator_sk:
        raise HTTPException(
            status_code=503,
            detail="Platform wallet (ALGORAND_ESCROW_CREATOR_MNEMONIC) not configured. Cannot deploy.",
        )

    blockchain_result = await gateway.deploy_escrow(
        buyer_address=buyer_address,
        seller_address=seller_address,
        amount_microalgo=amount_microalgo,
        session_id=str(session_id),
    )

    # 4. Record deployment (APPROVED → DEPLOYED)
    updated_escrow = await svc.record_pera_deploy(
        session_id=session_id,
        app_id=blockchain_result["app_id"],
        app_address=blockchain_result["app_address"],
        tx_id=blockchain_result["tx_id"],
    )

    log.info(
        "escrow_deployed_via_platform_wallet",
        session_id=str(session_id),
        app_id=blockchain_result["app_id"],
        tx_id=blockchain_result["tx_id"],
    )

    return success_response(PlatformDeployResponse(
        escrow_id=str(updated_escrow.id) if hasattr(updated_escrow, 'id') else str(session_id),
        app_id=blockchain_result["app_id"],
        app_address=blockchain_result["app_address"],
        tx_id=blockchain_result["tx_id"],
    ))


# ── POST /v1/escrow/{escrow_id}/platform-fund ────────────────────────────────
#    Uses the platform wallet so the buyer doesn't need Pera Wallet for funding.


class PlatformFundResponse(BaseModel):
    escrow_id: str
    tx_id: str
    confirmed_round: int
    status: str = "FUNDED"


@router.post(
    "/{escrow_id}/platform-fund",
    response_model=ApiResponse[PlatformFundResponse],
    summary="Fund escrow using the platform wallet (no Pera Wallet needed)",
    dependencies=[Depends(rate_limit)],
)
async def platform_fund_escrow(
    escrow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[PlatformFundResponse]:
    """
    Fund the escrow smart contract server-side using the platform wallet.
    The buyer's already-linked wallet is used for identification only.
    """
    from fastapi import HTTPException
    from src.settlement.application.queries import GetEscrowByIdQuery
    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    from algosdk.logic import get_application_address

    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )

    if escrow.status.value != "DEPLOYED":
        raise HTTPException(
            status_code=409,
            detail=f"Escrow cannot be funded in state: {escrow.status.value}",
        )

    app_id = escrow.algo_app_id.value if hasattr(escrow.algo_app_id, 'value') else escrow.algo_app_id
    if not app_id:
        raise HTTPException(status_code=400, detail="Escrow has no app_id")

    app_address = get_application_address(app_id)

    gateway = AlgorandGateway()
    if not gateway._creator_sk:
        raise HTTPException(
            status_code=503,
            detail="Platform wallet not configured. Cannot fund.",
        )

    blockchain_result = await gateway.fund_escrow(
        app_id=app_id,
        app_address=app_address,
        amount_microalgo=escrow.amount.value.value,
        funder_sk=gateway._creator_sk,
    )

    updated_escrow = await svc.record_pera_fund(escrow_id, blockchain_result["tx_id"])

    log.info(
        "escrow_funded_via_platform_wallet",
        escrow_id=str(escrow_id),
        tx_id=blockchain_result["tx_id"],
    )

    return success_response(PlatformFundResponse(
        escrow_id=str(escrow_id),
        tx_id=blockchain_result["tx_id"],
        confirmed_round=blockchain_result["confirmed_round"],
        status=updated_escrow.status.value,
    ))


# ── POST /v1/escrow/{escrow_id}/platform-release ────────────────────────────
#    Uses the platform wallet so the buyer doesn't need Pera Wallet for release.


class PlatformReleaseResponse(BaseModel):
    escrow_id: str
    tx_id: str
    confirmed_round: int
    status: str = "RELEASED"


@router.post(
    "/{escrow_id}/platform-release",
    response_model=ApiResponse[PlatformReleaseResponse],
    summary="Release escrow using the platform wallet (no Pera Wallet needed)",
    dependencies=[Depends(rate_limit)],
)
async def platform_release_escrow(
    escrow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[PlatformReleaseResponse]:
    """
    Release escrow funds to seller server-side using the platform wallet.
    Computes Merkle root from audit trail and anchors on-chain.
    """
    from fastapi import HTTPException
    from src.settlement.application.queries import GetEscrowByIdQuery
    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway

    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )

    if escrow.status.value != "FUNDED":
        raise HTTPException(
            status_code=409,
            detail=f"Escrow must be FUNDED to release, current: {escrow.status.value}",
        )

    app_id = escrow.algo_app_id.value if hasattr(escrow.algo_app_id, 'value') else escrow.algo_app_id
    if not app_id:
        raise HTTPException(status_code=400, detail="Escrow has no app_id")

    gateway = AlgorandGateway()
    if not gateway._creator_sk:
        raise HTTPException(
            status_code=503,
            detail="Platform wallet not configured. Cannot release.",
        )

    # Compute merkle root
    merkle_root = await svc.compute_merkle_root(escrow_id)

    blockchain_result = await gateway.release_escrow(
        app_id=app_id,
        merkle_root=merkle_root,
    )

    updated_escrow = await svc.record_pera_release(escrow_id, blockchain_result["tx_id"])

    log.info(
        "escrow_released_via_platform_wallet",
        escrow_id=str(escrow_id),
        tx_id=blockchain_result["tx_id"],
    )

    return success_response(PlatformReleaseResponse(
        escrow_id=str(escrow_id),
        tx_id=blockchain_result["tx_id"],
        confirmed_round=blockchain_result["confirmed_round"],
        status=updated_escrow.status.value,
    ))


# ── POST /v1/escrow/{escrow_id}/fund ─────────────────────────────────────────


@router.post(
    "/{escrow_id}/fund",
    response_model=ApiResponse[EscrowResponse],
    summary="[ADMIN ONLY] Fund escrow using platform mnemonic — internal ops endpoint",
    dependencies=[Depends(require_role("ADMIN")), Depends(rate_limit)],
)
async def fund_escrow(
    escrow_id: uuid.UUID,
    request_body: FundEscrowRequest,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[EscrowResponse]:
    """
    Platform-internal endpoint for admin/ops use only (e.g. testnet seeding).

    Accepts a raw Algorand mnemonic and signs server-side — this is intentionally
    restricted to ADMIN role. Non-admin users MUST use the Pera Wallet flow:
      GET  /{escrow_id}/build-fund-txn       → build unsigned tx group
      POST /{escrow_id}/submit-signed-fund   → submit Pera-signed tx

    SECURITY: mnemonic → private key conversion happens here in the API layer.
    The raw mnemonic is NEVER passed further into the application/domain.
    Non-ADMIN callers receive HTTP 403 before this handler is invoked.
    """
    # Convert mnemonic → sk here — never log either value
    funder_sk = algo_mnemonic.to_private_key(request_body.funder_algo_mnemonic)

    await svc.fund_escrow(
        FundEscrowCommand(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
            funder_algo_sk=funder_sk,
        )
    )
    # Reload escrow for response
    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )
    return success_response(EscrowResponse.from_domain(escrow))


# ── POST /v1/escrow/{escrow_id}/release ──────────────────────────────────────


@router.post(
    "/{escrow_id}/release",
    response_model=ApiResponse[EscrowResponse],
    summary="Release funds to seller with Merkle root anchoring",
    dependencies=[Depends(require_role("ADMIN", "MEMBER")), Depends(rate_limit)],
)
async def release_escrow(
    escrow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[EscrowResponse]:
    await svc.release_escrow(
        ReleaseEscrowCommand(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )
    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )
    return success_response(EscrowResponse.from_domain(escrow))


# ── POST /v1/escrow/{escrow_id}/refund ───────────────────────────────────────


@router.post(
    "/{escrow_id}/refund",
    response_model=ApiResponse[EscrowResponse],
    summary="Refund buyer",
    dependencies=[Depends(require_role("ADMIN", "MEMBER")), Depends(rate_limit)],
)
async def refund_escrow(
    escrow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[EscrowResponse]:
    await svc.refund_escrow(
        RefundEscrowCommand(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
            reason="Demo refund requested",
        )
    )
    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )
    return success_response(EscrowResponse.from_domain(escrow))


# ── POST /v1/escrow/{escrow_id}/freeze ───────────────────────────────────────


@router.post(
    "/{escrow_id}/freeze",
    response_model=ApiResponse[EscrowResponse],
    summary="Freeze escrow to halt state transitions",
    dependencies=[Depends(require_role("ADMIN", "MEMBER")), Depends(rate_limit)],
)
async def freeze_escrow(
    escrow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[EscrowResponse]:
    await svc.freeze_escrow(
        FreezeEscrowCommand(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
            frozen_by_role="ADMIN",
        )
    )
    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )
    return success_response(EscrowResponse.from_domain(escrow))


# ── GET /v1/escrow/{escrow_id}/settlements ────────────────────────────────────


@router.get(
    "/{escrow_id}/settlements",
    response_model=ApiResponse[list[SettlementResponse]],
    summary="List settlement records for an escrow",
    dependencies=[Depends(rate_limit)],
)
async def get_settlements(
    escrow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[list[SettlementResponse]]:
    settlements = await svc.get_settlements(
        GetSettlementsQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )
    return success_response([SettlementResponse.from_domain(s) for s in settlements])


# ── Pera Wallet Endpoints (RW-02) ────────────────────────────────────────────


from pydantic import BaseModel, Field


class BuildFundTxnResponse(BaseModel):
    """Components for building fund transaction on the frontend."""

    app_id: int = Field(default=0, description="Escrow app ID")
    app_address: str = Field(default="", description="Escrow app address")
    amount_microalgo: int = Field(default=0, description="Amount to fund in microALGO")
    funder_address: str = Field(default="", description="Funder's Algorand address")
    method_selector_b64: str = Field(default="", description="Base64-encoded ABI method selector")
    description: str = Field(default="")


class SubmitSignedFundRequest(BaseModel):
    """Pre-signed transaction group from Pera Wallet."""

    signed_transactions: list[str] = Field(
        description="Base64-encoded signed transactions from Pera Wallet"
    )


class SubmitSignedFundResponse(BaseModel):
    """Result of submitting signed transactions to Algorand."""

    txid: str = Field(description="Algorand transaction ID")
    confirmed_round: int = Field(description="Block round when confirmed")
    escrow_id: str = Field(default="", description="Escrow UUID")
    status: str = Field(default="", description="Updated escrow status after this operation")


@router.get(
    "/{escrow_id}/build-fund-txn",
    response_model=ApiResponse[BuildFundTxnResponse],
    summary="Build unsigned atomic group for Pera Wallet escrow funding",
    dependencies=[Depends(rate_limit)],
)
async def build_fund_transaction(
    escrow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[BuildFundTxnResponse]:
    """
    Build unsigned escrow funding transactions for Pera Wallet signing.

    Returns a base64-encoded atomic group [PaymentTxn, AppCallTxn(fund)]
    that the frontend passes to PeraWallet.signTransactions().

    context.md §12: backend NEVER handles user private keys.
    """
    from fastapi import HTTPException
    from src.settlement.application.queries import GetEscrowByIdQuery

    # Get escrow details
    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )

    if escrow.algo_app_id is None:
        raise HTTPException(
            status_code=400,
            detail="Escrow not deployed — no Algorand app ID",
        )

    if escrow.status.value != "DEPLOYED":
        raise HTTPException(
            status_code=409,
            detail=f"Escrow cannot be funded in state: {escrow.status.value}",
        )

    # Build unsigned transactions
    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    gateway = AlgorandGateway()

    # Calculate app address from app_id (need raw int value)
    from algosdk.logic import get_application_address
    app_id_int = escrow.algo_app_id.value if hasattr(escrow.algo_app_id, 'value') else escrow.algo_app_id
    app_address = get_application_address(app_id_int)

    result = await gateway.build_fund_transaction(
        app_id=app_id_int,
        app_address=app_address,
        amount_microalgo=escrow.amount.value.value,
        funder_address=escrow.buyer_address,
    )

    return success_response(BuildFundTxnResponse(**result))


@router.post(
    "/{escrow_id}/submit-signed-fund",
    response_model=ApiResponse[SubmitSignedFundResponse],
    summary="Submit Pera Wallet pre-signed transaction group",
    dependencies=[Depends(rate_limit)],
)
async def submit_signed_fund(
    escrow_id: uuid.UUID,
    request_body: SubmitSignedFundRequest,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[SubmitSignedFundResponse]:
    """
    Submit pre-signed transactions from Pera Wallet.

    1. Validates escrow is in DEPLOYED state
    2. Runs mandatory dry-run simulation (SRS-SC-001)
    3. Broadcasts to Algorand network
    4. Updates escrow status to FUNDED

    context.md §7.3: dry-run BEFORE every broadcast.
    context.md §12: backend NEVER sees private keys.
    """
    from fastapi import HTTPException
    from src.settlement.application.queries import GetEscrowByIdQuery

    # Validate escrow state
    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )

    if escrow.status.value != "DEPLOYED":
        raise HTTPException(
            status_code=409,
            detail=f"Escrow cannot be funded in state: {escrow.status.value}",
        )

    # Submit signed transactions
    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    gateway = AlgorandGateway()

    result = await gateway.submit_signed_fund(
        signed_txn_bytes_list=request_body.signed_transactions,
    )

    # Persist DEPLOYED → FUNDED status change in the database.
    # Without this, the on-chain fund succeeds but the DB stays DEPLOYED,
    # blocking all downstream operations that check escrow.status == FUNDED.
    updated_escrow = await svc.record_pera_fund(escrow_id, result["tx_id"])

    log.info(
        "escrow_funded_via_pera_wallet",
        escrow_id=str(escrow_id),
        tx_id=result["tx_id"],
        confirmed_round=result["confirmed_round"],
    )

    return success_response(SubmitSignedFundResponse(
        txid=result["tx_id"],
        confirmed_round=result["confirmed_round"],
        escrow_id=str(escrow_id),
        status=updated_escrow.status.value,
    ))


# ── Pera Wallet: Build/Submit Deploy ─────────────────────────────────────────


class BuildDeployTxnResponse(BaseModel):
    """Components for building deploy transaction on the frontend."""
    approval_program_b64: str = Field(description="Base64-encoded approval TEAL bytecode")
    clear_program_b64: str = Field(description="Base64-encoded clear TEAL bytecode")
    app_args_b64: list[str] = Field(description="Base64-encoded ABI app args")
    global_schema: dict = Field(description="Global state schema {num_uints, num_byte_slices}")
    local_schema: dict = Field(description="Local state schema {num_uints, num_byte_slices}")
    description: str = Field(default="")


class SubmitSignedDeployRequest(BaseModel):
    signed_transactions: list[str]


class SubmitSignedDeployResponse(BaseModel):
    escrow_id: str
    app_id: int
    app_address: str
    tx_id: str
    confirmed_round: int
    status: str = "DEPLOYED"


@router.get(
    "/{session_id}/build-deploy-txn",
    response_model=ApiResponse[BuildDeployTxnResponse],
    summary="Build unsigned deploy transaction for Pera Wallet",
    dependencies=[Depends(rate_limit)],
)
async def build_deploy_transaction(
    session_id: uuid.UUID,
    deployer_address: str = Query(description="Deployer's Algorand address (Pera wallet)"),
    buyer_address: str = Query(description="Buyer's Algorand address"),
    seller_address: str = Query(description="Seller's Algorand address"),
    amount_microalgo: int = Query(description="Escrow amount in microALGO"),
) -> ApiResponse[BuildDeployTxnResponse]:
    """Build unsigned escrow deploy transaction for Pera Wallet signing.
    
    No JWT required — the Algorand wallet signature is the authentication.
    """
    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    gateway = AlgorandGateway()

    result = await gateway.build_deploy_transaction(
        deployer_address=deployer_address,
        buyer_address=buyer_address,
        seller_address=seller_address,
        amount_microalgo=amount_microalgo,
        session_id=str(session_id),
    )

    return success_response(BuildDeployTxnResponse(**result))


@router.post(
    "/{session_id}/submit-signed-deploy",
    response_model=ApiResponse[SubmitSignedDeployResponse],
    summary="Submit Pera-signed deploy transaction",
    dependencies=[Depends(rate_limit)],
)
async def submit_signed_deploy(
    session_id: uuid.UUID,
    request_body: SubmitSignedDeployRequest,
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[SubmitSignedDeployResponse]:
    """
    Submit pre-signed deploy transaction and persist the Escrow entity.
    No JWT required — the Algorand wallet signature is the authentication.
    """
    from fastapi import HTTPException
    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    from src.settlement.application.commands import DeployEscrowCommand

    gateway = AlgorandGateway()

    result = await gateway.submit_signed_deploy(
        signed_txn_bytes_list=request_body.signed_transactions,
    )

    # Persist escrow entity via service
    try:
        escrow = await svc.record_pera_deploy(
            session_id=session_id,
            app_id=result["app_id"],
            app_address=result["app_address"],
            tx_id=result["tx_id"],
        )
    except Exception as exc:
        log.error("persist_deploy_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Deploy succeeded on-chain but failed to persist: {exc}")

    return success_response(SubmitSignedDeployResponse(
        escrow_id=str(escrow.id) if hasattr(escrow, 'id') else str(session_id),
        app_id=result["app_id"],
        app_address=result["app_address"],
        tx_id=result["tx_id"],
        confirmed_round=result["confirmed_round"],
    ))


# ── Pera Wallet: Build/Submit Release ────────────────────────────────────────


class BuildReleaseTxnResponse(BaseModel):
    """Components for building release transaction on the frontend."""
    app_id: int = Field(default=0)
    app_args_b64: list[str] = Field(default_factory=list)
    extra_fee: int = Field(default=2000, description="Extra fee for inner txns")
    description: str = Field(default="")
    merkle_root: str = Field(default="")


@router.get(
    "/{escrow_id}/build-release-txn",
    response_model=ApiResponse[BuildReleaseTxnResponse],
    summary="Build unsigned release transaction for Pera Wallet",
    dependencies=[Depends(rate_limit)],
)
async def build_release_transaction(
    escrow_id: uuid.UUID,
    sender_address: str = Query(description="Creator's Algorand address (must match deployer)"),
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[BuildReleaseTxnResponse]:
    """Build unsigned release transaction. Computes merkle root from audit trail."""
    from fastapi import HTTPException
    from src.settlement.application.queries import GetEscrowByIdQuery

    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )

    if escrow.status.value != "FUNDED":
        raise HTTPException(status_code=409, detail=f"Escrow must be FUNDED to release, current: {escrow.status.value}")

    app_id = escrow.algo_app_id.value if hasattr(escrow.algo_app_id, 'value') else escrow.algo_app_id
    if not app_id:
        raise HTTPException(status_code=400, detail="Escrow has no app_id")

    # Compute merkle root (reuse service logic)
    merkle_root = await svc.compute_merkle_root(escrow_id)

    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    gateway = AlgorandGateway()

    result = await gateway.build_release_transaction(
        app_id=app_id,
        sender_address=sender_address,
        merkle_root=merkle_root,
    )

    return success_response(BuildReleaseTxnResponse(
        **result,
        merkle_root=merkle_root,
    ))


@router.post(
    "/{escrow_id}/submit-signed-release",
    response_model=ApiResponse[SubmitSignedFundResponse],
    summary="Submit Pera-signed release transaction",
    dependencies=[Depends(rate_limit)],
)
async def submit_signed_release(
    escrow_id: uuid.UUID,
    request_body: SubmitSignedFundRequest,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[SubmitSignedFundResponse]:
    """Submit pre-signed release transaction, update escrow to RELEASED."""
    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    gateway = AlgorandGateway()

    result = await gateway.submit_signed_transaction(
        signed_txn_bytes_list=request_body.signed_transactions,
    )

    # Update escrow status to RELEASED
    updated_escrow = await svc.record_pera_release(escrow_id, result["tx_id"])

    return success_response(SubmitSignedFundResponse(
        txid=result["tx_id"],
        confirmed_round=result["confirmed_round"],
        escrow_id=str(escrow_id),
        status=updated_escrow.status.value,
    ))


# ── Pera Wallet: Build/Submit Refund ─────────────────────────────────────────


@router.get(
    "/{escrow_id}/build-refund-txn",
    response_model=ApiResponse[BuildFundTxnResponse],
    summary="Build unsigned refund transaction for Pera Wallet",
    dependencies=[Depends(rate_limit)],
)
async def build_refund_transaction(
    escrow_id: uuid.UUID,
    sender_address: str = Query(description="Creator's Algorand address"),
    reason: str = Query(default="Buyer requested refund", description="Refund reason"),
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[BuildFundTxnResponse]:
    """Build unsigned refund transaction."""
    from fastapi import HTTPException
    from src.settlement.application.queries import GetEscrowByIdQuery

    escrow = await svc.get_escrow_by_id(
        GetEscrowByIdQuery(
            escrow_id=escrow_id,
            requesting_enterprise_id=current_user.enterprise_id,
        )
    )

    if escrow.status.value != "FUNDED":
        raise HTTPException(status_code=409, detail=f"Escrow must be FUNDED to refund, current: {escrow.status.value}")

    app_id = escrow.algo_app_id.value if hasattr(escrow.algo_app_id, 'value') else escrow.algo_app_id

    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    gateway = AlgorandGateway()

    result = await gateway.build_refund_transaction(
        app_id=app_id,
        sender_address=sender_address,
        reason=reason,
    )

    return success_response(BuildReleaseTxnResponse(**result))


@router.post(
    "/{escrow_id}/submit-signed-refund",
    response_model=ApiResponse[SubmitSignedFundResponse],
    summary="Submit Pera-signed refund transaction",
    dependencies=[Depends(rate_limit)],
)
async def submit_signed_refund(
    escrow_id: uuid.UUID,
    request_body: SubmitSignedFundRequest,
    current_user: User = Depends(get_current_user),
    svc: SettlementServiceDep = Depends(get_settlement_service),
) -> ApiResponse[SubmitSignedFundResponse]:
    """Submit pre-signed refund transaction, update escrow to REFUNDED."""
    from src.settlement.infrastructure.algorand_gateway import AlgorandGateway
    gateway = AlgorandGateway()

    result = await gateway.submit_signed_transaction(
        signed_txn_bytes_list=request_body.signed_transactions,
    )

    # Update escrow status to REFUNDED
    updated_escrow = await svc.record_pera_refund(escrow_id, result["tx_id"])

    return success_response(SubmitSignedFundResponse(
        txid=result["tx_id"],
        confirmed_round=result["confirmed_round"],
        escrow_id=str(escrow_id),
        status=updated_escrow.status.value,
    ))

