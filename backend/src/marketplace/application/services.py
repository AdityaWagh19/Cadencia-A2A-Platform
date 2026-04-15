# context.md §3: Application service — orchestrates use cases.
# All infrastructure deps injected via constructor (DIP).

from __future__ import annotations

import asyncio
import json
import uuid
from typing import TYPE_CHECKING

from src.marketplace.application.commands import (
    ConfirmRFQCommand,
    UpdateCapabilityProfileCommand,
    UploadRFQCommand,
)
from src.marketplace.domain.capability_profile import CapabilityProfile
from src.marketplace.domain.events import (
    CapabilityProfileUpdated,
    RFQConfirmed,
    RFQMatched,
    RFQParsed,
    RFQUploaded,
)
from src.marketplace.domain.match import Match
from src.marketplace.domain.rfq import RFQ
from src.marketplace.domain.value_objects import SimilarityScore
from src.shared.domain.exceptions import AuthorizationError, NotFoundError
from src.shared.infrastructure.logging import get_logger
from src.shared.infrastructure.metrics import RFQ_UPLOADS_TOTAL

if TYPE_CHECKING:
    from src.marketplace.domain.ports import (
        ICapabilityProfileRepository,
        IDocumentParser,
        IMatchmakingEngine,
        IMatchRepository,
        IRFQRepository,
    )
    from src.shared.infrastructure.events.publisher import EventPublisher

log = get_logger(__name__)


class MarketplaceService:
    """Orchestrates marketplace use cases."""

    def __init__(
        self,
        rfq_repo: IRFQRepository,
        match_repo: IMatchRepository,
        profile_repo: ICapabilityProfileRepository,
        document_parser: IDocumentParser,
        matchmaking_engine: IMatchmakingEngine,
        event_publisher: EventPublisher,
        top_n_matches: int = 10,
    ) -> None:
        self._rfq_repo = rfq_repo
        self._match_repo = match_repo
        self._profile_repo = profile_repo
        self._parser = document_parser
        self._matchmaker = matchmaking_engine
        self._publisher = event_publisher
        self._top_n = top_n_matches

    async def upload_rfq(self, cmd: UploadRFQCommand) -> RFQ:
        """Create RFQ in DRAFT, schedule background parse+match. Returns immediately."""
        rfq = RFQ(
            buyer_enterprise_id=cmd.buyer_enterprise_id,
            raw_document=cmd.raw_text,
        )
        await self._rfq_repo.save(rfq)

        await self._publisher.publish(
            RFQUploaded(
                aggregate_id=rfq.id,
                event_type="RFQUploaded",
                rfq_id=rfq.id,
                buyer_enterprise_id=rfq.buyer_enterprise_id,
                raw_document_length=len(cmd.raw_text),
            )
        )

        # Background parse & match — non-blocking (uses its own DB session)
        asyncio.create_task(self._parse_and_match_standalone(rfq.id))

        # Prometheus: RFQ upload success
        RFQ_UPLOADS_TOTAL.labels(status="success").inc()

        log.info("rfq_uploaded", rfq_id=str(rfq.id), status=rfq.status.value)
        return rfq

    async def _parse_and_match_standalone(self, rfq_id: uuid.UUID) -> None:
        """Background task with its own DB session — avoids asyncpg concurrency errors."""
        import os
        from src.marketplace.infrastructure.pgvector_matchmaker import PgvectorMatchmaker, StubMatchmakingEngine
        from src.marketplace.infrastructure.keyword_matchmaker import KeywordMatchmaker
        from src.marketplace.infrastructure.repositories import (
            PostgresCapabilityProfileRepository,
            PostgresMatchRepository,
            PostgresRFQRepository,
        )
        from src.shared.infrastructure.db.session import get_session_factory

        # Wait for the parent request's transaction to commit before we read.
        # Retry with backoff if the row isn't visible yet (transaction isolation).
        await asyncio.sleep(0.3)

        factory = get_session_factory()
        async with factory() as session:
            try:
                rfq_repo = PostgresRFQRepository(session)
                match_repo = PostgresMatchRepository(session)
                llm_provider = os.environ.get("LLM_PROVIDER", "stub")
                if llm_provider == "stub":
                    matchmaker = StubMatchmakingEngine(session=session)
                else:
                    matchmaker = PgvectorMatchmaker(session)

                rfq = await rfq_repo.get_by_id(rfq_id)
                if rfq is None:
                    # Retry: parent transaction may not have committed yet
                    for _attempt in range(3):
                        await asyncio.sleep(0.5)
                        rfq = await rfq_repo.get_by_id(rfq_id)
                        if rfq is not None:
                            break
                if rfq is None:
                    log.error("rfq_not_found_for_parse", rfq_id=str(rfq_id))
                    return

                # 1. Extract fields via LLM
                parsed = await self._parser.extract_rfq_fields(rfq.raw_document or "")
                if not parsed:
                    log.warning("rfq_extraction_empty", rfq_id=str(rfq_id))
                    return  # Stay DRAFT — no fields extracted

                # 2. Mark parsed
                event_data = rfq.mark_parsed(parsed)
                await rfq_repo.update(rfq)
                await session.commit()

                await self._publisher.publish(
                    RFQParsed(
                        aggregate_id=rfq.id,
                        event_type="RFQParsed",
                        **event_data,
                    )
                )

                # 3. Generate embedding
                embed_text = (rfq.raw_document or "") + " " + json.dumps(parsed)
                embedding = await self._parser.generate_embedding(embed_text)
                rfq.embedding = embedding

                # 4. Find matches (with keyword fallback)
                raw_matches = await matchmaker.find_matches(
                    rfq, embedding, self._top_n
                )

                # Fallback to keyword matching if pgvector returns no/low results
                if not raw_matches or (raw_matches and all(s < 0.3 for _, s in raw_matches)):
                    keyword_matchmaker = KeywordMatchmaker(session)
                    keyword_results = await keyword_matchmaker.find_matches(rfq, embedding, self._top_n)
                    if keyword_results:
                        raw_matches = keyword_results

                if not raw_matches:
                    log.info("rfq_no_matches", rfq_id=str(rfq_id))
                    await rfq_repo.update(rfq)
                    await session.commit()
                    return  # Stay PARSED

                # 5. Create Match entities
                matches = [
                    Match(
                        rfq_id=rfq.id,
                        seller_enterprise_id=ent_id,
                        similarity_score=SimilarityScore(value=score),
                        rank=rank + 1,
                    )
                    for rank, (ent_id, score) in enumerate(raw_matches)
                ]
                await match_repo.save_bulk(matches)

                # 6. Mark matched
                rfq_matched_data = rfq.mark_matched(len(matches))
                await rfq_repo.update(rfq)
                await session.commit()

                await self._publisher.publish(
                    RFQMatched(
                        aggregate_id=rfq.id,
                        event_type="RFQMatched",
                        top_score=raw_matches[0][1] if raw_matches else 0.0,
                        **rfq_matched_data,
                    )
                )

                log.info(
                    "rfq_parsed_and_matched",
                    rfq_id=str(rfq_id),
                    match_count=len(matches),
                )

            except Exception:
                log.exception("rfq_parse_match_failed", rfq_id=str(rfq_id))

    async def get_rfq(self, rfq_id: uuid.UUID) -> RFQ:
        rfq = await self._rfq_repo.get_by_id(rfq_id)
        if rfq is None:
            raise NotFoundError("RFQ", rfq_id)
        return rfq

    async def get_matches(self, rfq_id: uuid.UUID) -> list[Match]:
        return await self._match_repo.list_by_rfq(rfq_id)

    async def confirm_rfq(self, cmd: ConfirmRFQCommand) -> dict:
        """Confirm an RFQ match — resolves match from seller_enterprise_id,
        transitions RFQ to CONFIRMED, creates negotiation session SYNCHRONOUSLY,
        and returns the real session_id."""
        rfq = await self._rfq_repo.get_by_id(cmd.rfq_id)
        if rfq is None:
            raise NotFoundError("RFQ", cmd.rfq_id)

        if rfq.buyer_enterprise_id != cmd.buyer_enterprise_id:
            raise AuthorizationError("Only the buyer can confirm an RFQ.")

        # Resolve match from seller_enterprise_id
        match = await self._match_repo.get_match_by_seller(
            rfq_id=cmd.rfq_id,
            seller_enterprise_id=cmd.seller_enterprise_id,
        )
        if match is None:
            raise NotFoundError("Match", f"seller={cmd.seller_enterprise_id}")

        # Confirm RFQ + select match
        confirm_data = rfq.confirm(match.id)
        match.select()

        # Reject all other matches for this RFQ
        all_matches = await self._match_repo.list_by_rfq(rfq.id)
        for m in all_matches:
            if m.id != match.id and m.status.value == "PENDING":
                m.reject()
                await self._match_repo.update(m)

        await self._rfq_repo.update(rfq)
        await self._match_repo.update(match)

        # Create negotiation session SYNCHRONOUSLY to avoid session_id mismatch
        session_id = await self._create_negotiation_session_sync(
            match_id=match.id,
            rfq_id=rfq.id,
            buyer_enterprise_id=rfq.buyer_enterprise_id,
            seller_enterprise_id=match.seller_enterprise_id,
        )

        # Publish RFQConfirmed for audit/observability (non-blocking)
        await self._publisher.publish(
            RFQConfirmed(
                aggregate_id=rfq.id,
                event_type="RFQConfirmed",
                rfq_id=rfq.id,
                match_id=match.id,
                buyer_enterprise_id=rfq.buyer_enterprise_id,
                seller_enterprise_id=match.seller_enterprise_id,
            )
        )

        log.info(
            "rfq_confirmed",
            rfq_id=str(rfq.id),
            match_id=str(match.id),
            session_id=str(session_id),
        )
        return {
            "message": "Negotiation session created",
            "session_id": str(session_id),
        }

    async def _create_negotiation_session_sync(
        self,
        match_id: uuid.UUID,
        rfq_id: uuid.UUID,
        buyer_enterprise_id: uuid.UUID,
        seller_enterprise_id: uuid.UUID,
    ) -> uuid.UUID:
        """Create a negotiation session synchronously with its own DB session."""
        from src.shared.infrastructure.db.session import get_session_factory
        from src.shared.infrastructure.db.uow import SqlAlchemyUnitOfWork
        from src.shared.infrastructure.events.publisher import get_publisher
        from src.negotiation.application.services import NegotiationService
        from src.negotiation.application.commands import CreateSessionCommand
        from src.negotiation.infrastructure.llm_agent_driver import get_agent_driver
        from src.negotiation.infrastructure.neutral_engine import NeutralEngine
        from src.negotiation.infrastructure.personalization import PersonalizationBuilder
        from src.negotiation.infrastructure.repositories import (
            PostgresAgentProfileRepository,
            PostgresOfferRepository,
            PostgresPlaybookRepository,
            PostgresSessionRepository,
        )

        async with get_session_factory()() as db_session:
            engine = NeutralEngine(
                agent_driver=get_agent_driver(),
                personalization_builder=PersonalizationBuilder(),
                sse_publisher=None,
            )
            svc = NegotiationService(
                session_repo=PostgresSessionRepository(db_session),
                offer_repo=PostgresOfferRepository(db_session),
                profile_repo=PostgresAgentProfileRepository(db_session),
                playbook_repo=PostgresPlaybookRepository(db_session),
                neutral_engine=engine,
                sse_publisher=None,
                event_publisher=get_publisher(),
                uow=SqlAlchemyUnitOfWork(db_session),
            )
            session = await svc.create_session(
                CreateSessionCommand(
                    match_id=match_id,
                    rfq_id=rfq_id,
                    buyer_enterprise_id=buyer_enterprise_id,
                    seller_enterprise_id=seller_enterprise_id,
                )
            )
            return session.id

    async def list_rfqs(
        self,
        buyer_enterprise_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        statuses: list[str] | None = None,
    ) -> list[RFQ]:
        """List RFQs for the buyer's enterprise with optional status filter."""
        return await self._rfq_repo.list_by_buyer(
            buyer_enterprise_id=buyer_enterprise_id,
            limit=limit,
            offset=offset,
            statuses=statuses,
        )

    async def list_incoming_rfqs(
        self,
        seller_enterprise_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """List RFQs where this seller enterprise is in the match results."""
        matches = await self._match_repo.list_by_seller(
            seller_enterprise_id=seller_enterprise_id,
            limit=limit,
            offset=offset,
        )
        results = []
        for match in matches:
            rfq = await self._rfq_repo.get_by_id(match.rfq_id)
            if rfq:
                results.append({
                    "match_id": match.id,
                    "rfq_id": rfq.id,
                    "raw_text": rfq.raw_document or "",
                    "status": rfq.status.value,
                    "parsed_fields": rfq.parsed_fields,
                    "created_at": rfq.created_at,
                    "similarity_score": match.similarity_score.value if match.similarity_score else 0.0,
                    "rank": match.rank,
                    "match_status": match.status.value,
                    "buyer_enterprise_id": rfq.buyer_enterprise_id,
                })
        return results

    async def update_capability_profile(
        self, cmd: UpdateCapabilityProfileCommand
    ) -> CapabilityProfile:
        profile = await self._profile_repo.get_by_enterprise(cmd.enterprise_id)
        if profile is None:
            profile = CapabilityProfile(enterprise_id=cmd.enterprise_id)

        event_data = profile.update_profile(
            industry_vertical=cmd.industry_vertical,
            product_categories=cmd.product_categories,
            geography_scope=cmd.geography_scope,
            trade_volume_min=cmd.trade_volume_min,
            trade_volume_max=cmd.trade_volume_max,
            profile_text=cmd.profile_text,
        )

        if await self._profile_repo.get_by_enterprise(cmd.enterprise_id):
            await self._profile_repo.update(profile)
        else:
            await self._profile_repo.save(profile)

        await self._publisher.publish(
            CapabilityProfileUpdated(
                aggregate_id=profile.id,
                event_type="CapabilityProfileUpdated",
                **event_data,
            )
        )

        # Schedule background embedding recompute (uses its own DB session)
        asyncio.create_task(self._recompute_embedding_standalone(cmd.enterprise_id))
        return profile

    async def _recompute_embedding_standalone(self, enterprise_id: uuid.UUID) -> None:
        """Background: generate embedding for capability profile with its own DB session."""
        from src.marketplace.infrastructure.repositories import (
            PostgresCapabilityProfileRepository,
        )
        from src.shared.infrastructure.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            try:
                profile_repo = PostgresCapabilityProfileRepository(session)
                profile = await profile_repo.get_by_enterprise(enterprise_id)
                if profile is None:
                    return
                text_parts = [
                    profile.profile_text or "",
                    " ".join(profile.product_categories),
                    " ".join(profile.geography_scope),
                    profile.industry_vertical or "",
                ]
                text = " ".join(p for p in text_parts if p)
                if not text.strip():
                    return
                embedding = await self._parser.generate_embedding(text)
                profile.set_embedding(embedding)
                await profile_repo.update(profile)
                await session.commit()
                log.info("embedding_recomputed", enterprise_id=str(enterprise_id))
            except Exception:
                log.exception("embedding_recompute_failed", enterprise_id=str(enterprise_id))
