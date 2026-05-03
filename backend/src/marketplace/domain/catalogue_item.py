# Hexagonal Architecture: zero framework imports. Pure Python domain entity.

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from src.shared.domain.base_entity import BaseEntity
from src.shared.domain.exceptions import ValidationError


class ProductCategory(str, Enum):
    HR_COIL = "HR_COIL"
    CR_COIL = "CR_COIL"
    TMT_BAR = "TMT_BAR"
    WIRE_ROD = "WIRE_ROD"
    BILLET = "BILLET"
    SLAB = "SLAB"
    PLATE = "PLATE"
    PIPE = "PIPE"
    SHEET = "SHEET"
    ANGLE = "ANGLE"
    CHANNEL = "CHANNEL"
    BEAM = "BEAM"
    CUSTOM = "CUSTOM"


class PricingUnit(str, Enum):
    MT = "MT"
    KG = "KG"
    PIECE = "PIECE"
    BUNDLE = "BUNDLE"
    COIL = "COIL"


@dataclass
class BulkPricingTier:
    """A single tier in the bulk pricing schedule."""
    min_qty: Decimal
    max_qty: Decimal | None  # None means unlimited
    price_per_unit_inr: Decimal

    def __post_init__(self) -> None:
        if self.min_qty < Decimal("0"):
            raise ValidationError("min_qty must be >= 0.", field="min_qty")
        if self.max_qty is not None and self.max_qty <= self.min_qty:
            raise ValidationError("max_qty must be > min_qty.", field="max_qty")
        if self.price_per_unit_inr <= Decimal("0"):
            raise ValidationError("price_per_unit_inr must be > 0.", field="price_per_unit_inr")


@dataclass
class CatalogueItem(BaseEntity):
    """
    Seller product catalogue entry.

    Each seller lists products they can supply with pricing, MOQ,
    capacity limits, and lead times.
    """

    enterprise_id: uuid.UUID = field(default_factory=uuid.uuid4)
    product_name: str = ""
    hsn_code: str = ""
    product_category: ProductCategory = ProductCategory.CUSTOM
    grade: str | None = None
    specification_text: str | None = None
    unit: PricingUnit = PricingUnit.MT
    price_per_unit_inr: Decimal = Decimal("0")
    bulk_pricing_tiers: list[BulkPricingTier] = field(default_factory=list)
    moq: Decimal = Decimal("1")
    max_order_qty: Decimal = Decimal("1000")
    lead_time_days: int = 7
    in_stock_qty: Decimal = Decimal("0")
    is_active: bool = True
    certifications: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.price_per_unit_inr <= Decimal("0"):
            raise ValidationError("Price per unit must be > 0.", field="price_per_unit_inr")
        if self.moq <= Decimal("0"):
            raise ValidationError("MOQ must be > 0.", field="moq")
        if self.max_order_qty < self.moq:
            raise ValidationError("Max order qty must be >= MOQ.", field="max_order_qty")
        if not 1 <= self.lead_time_days <= 180:
            raise ValidationError("Lead time must be 1-180 days.", field="lead_time_days")
        self._validate_bulk_tiers()

    def _validate_bulk_tiers(self) -> None:
        """Ensure bulk pricing tiers are contiguous and non-overlapping."""
        if not self.bulk_pricing_tiers:
            return
        sorted_tiers = sorted(self.bulk_pricing_tiers, key=lambda t: t.min_qty)
        for i, tier in enumerate(sorted_tiers):
            if i > 0:
                prev = sorted_tiers[i - 1]
                if prev.max_qty is None:
                    raise ValidationError(
                        "Only the last tier can have unlimited max_qty.",
                        field="bulk_pricing_tiers",
                    )
                if tier.min_qty < prev.max_qty:
                    raise ValidationError(
                        f"Tier overlap: tier {i} min_qty ({tier.min_qty}) < previous max_qty ({prev.max_qty}).",
                        field="bulk_pricing_tiers",
                    )

    def get_price_for_quantity(self, qty: Decimal) -> Decimal:
        """Look up the applicable price for a given quantity."""
        if not self.bulk_pricing_tiers:
            return self.price_per_unit_inr

        sorted_tiers = sorted(self.bulk_pricing_tiers, key=lambda t: t.min_qty)
        for tier in reversed(sorted_tiers):
            if qty >= tier.min_qty:
                if tier.max_qty is None or qty <= tier.max_qty:
                    return tier.price_per_unit_inr
                # qty exceeds this tier's max, but it's the best match
                return tier.price_per_unit_inr
        return self.price_per_unit_inr

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        self.is_active = True
        self.touch()

    def update_stock(self, new_qty: Decimal) -> None:
        if new_qty < Decimal("0"):
            raise ValidationError("Stock quantity cannot be negative.", field="in_stock_qty")
        self.in_stock_qty = new_qty
        self.touch()

    def bulk_tiers_as_dicts(self) -> list[dict]:
        """Serialize bulk pricing tiers to JSON-safe dicts."""
        return [
            {
                "min_qty": float(t.min_qty),
                "max_qty": float(t.max_qty) if t.max_qty is not None else None,
                "price_per_unit_inr": float(t.price_per_unit_inr),
            }
            for t in self.bulk_pricing_tiers
        ]
