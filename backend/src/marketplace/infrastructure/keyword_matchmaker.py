# SQL-based matching using commodity overlap, geography, and order value ranges.
# Implements IMatchmakingEngine as a keyword-based fallback when pgvector is unavailable.

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.infrastructure.models import EnterpriseModel
from src.marketplace.infrastructure.models import CapabilityProfileModel
from src.shared.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from src.marketplace.domain.rfq import RFQ

log = get_logger(__name__)

# Weights for scoring
COMMODITY_WEIGHT = 0.5
GEOGRAPHY_WEIGHT = 0.3
VALUE_WEIGHT = 0.2


class KeywordMatchmaker:
    """SQL-based matching using commodity overlap, geography, and order value ranges."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_matches(
        self,
        rfq: "RFQ",
        rfq_embedding: list[float],
        top_n: int = 10,
    ) -> list[tuple[uuid.UUID, float]]:
        """Find seller matches using keyword-based scoring against CapabilityProfiles."""
        parsed = rfq.parsed_fields or {}
        rfq_product = (parsed.get("product") or "").lower()
        rfq_geography = (parsed.get("geography") or "").lower()
        rfq_budget_min = parsed.get("budget_min")
        rfq_budget_max = parsed.get("budget_max")

        if not rfq_product:
            log.info("keyword_match_skipped_no_product", rfq_id=str(rfq.id))
            return []

        # Query capability profiles joined with enterprises to filter by trade role
        stmt = select(
            CapabilityProfileModel.enterprise_id,
            CapabilityProfileModel.commodities,
            CapabilityProfileModel.geographies_served,
            CapabilityProfileModel.min_order_value,
            CapabilityProfileModel.max_order_value,
        ).join(
            EnterpriseModel,
            EnterpriseModel.id == CapabilityProfileModel.enterprise_id,
        ).where(
            and_(
                CapabilityProfileModel.enterprise_id != rfq.buyer_enterprise_id,
                or_(
                    EnterpriseModel.trade_role == "SELLER",
                    EnterpriseModel.trade_role == "BOTH",
                ),
            )
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        scored: list[tuple[uuid.UUID, float]] = []

        for row in rows:
            score = 0.0

            # 1. Commodity overlap (weight: 0.5)
            commodities = row.commodities or []
            commodity_lower = [c.lower() for c in commodities]
            product_words = rfq_product.split()

            commodity_match = any(
                word in " ".join(commodity_lower)
                for word in product_words
                if len(word) > 2
            ) or any(
                rfq_product in c for c in commodity_lower
            )
            if commodity_match:
                score += COMMODITY_WEIGHT

            # 2. Geography match (weight: 0.3)
            geographies = row.geographies_served or []
            geo_lower = [g.lower() for g in geographies]
            if rfq_geography and geo_lower:
                geo_match = any(
                    rfq_geography in g or g in rfq_geography
                    for g in geo_lower
                )
                if geo_match:
                    score += GEOGRAPHY_WEIGHT

            # 3. Order value range overlap (weight: 0.2)
            if rfq_budget_min is not None or rfq_budget_max is not None:
                ent_min = float(row.min_order_value) if row.min_order_value else 0
                ent_max = float(row.max_order_value) if row.max_order_value else float("inf")
                b_min = float(rfq_budget_min) if rfq_budget_min else 0
                b_max = float(rfq_budget_max) if rfq_budget_max else float("inf")

                # Check overlap
                if b_min <= ent_max and b_max >= ent_min:
                    score += VALUE_WEIGHT

            if score > 0:
                scored.append((row.enterprise_id, round(min(score, 1.0), 3)))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        matches = scored[:top_n]

        log.info(
            "keyword_match_complete",
            rfq_id=str(rfq.id),
            match_count=len(matches),
            top_score=matches[0][1] if matches else 0.0,
        )

        return matches
