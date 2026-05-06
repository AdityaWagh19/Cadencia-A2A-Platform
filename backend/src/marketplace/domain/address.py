# Hexagonal Architecture: zero framework imports. Pure Python domain entity.

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from src.shared.domain.base_entity import BaseEntity
from src.shared.domain.exceptions import ValidationError


class AddressType(str, Enum):
    FACILITY = "FACILITY"
    DELIVERY = "DELIVERY"
    REGISTERED_OFFICE = "REGISTERED_OFFICE"
    WAREHOUSE = "WAREHOUSE"


INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]


@dataclass
class Address(BaseEntity):
    """Reusable address entity for enterprise facilities and delivery sites."""

    enterprise_id: uuid.UUID = field(default_factory=uuid.uuid4)
    address_type: AddressType = AddressType.FACILITY
    address_line1: str = ""
    address_line2: str | None = None
    city: str = ""
    state: str = ""
    pincode: str = ""
    latitude: float | None = None
    longitude: float | None = None
    is_primary: bool = True

    def __post_init__(self) -> None:
        if self.address_line1 and len(self.address_line1) < 5:
            raise ValidationError("Address line 1 must be at least 5 characters.", field="address_line1")
        if self.pincode and (len(self.pincode) != 6 or not self.pincode.isdigit()):
            raise ValidationError("Pincode must be exactly 6 digits.", field="pincode")

    def update(
        self,
        address_line1: str | None = None,
        address_line2: str | None = None,
        city: str | None = None,
        state: str | None = None,
        pincode: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> None:
        if address_line1 is not None:
            self.address_line1 = address_line1
        if address_line2 is not None:
            self.address_line2 = address_line2
        if city is not None:
            self.city = city
        if state is not None:
            self.state = state
        if pincode is not None:
            if len(pincode) != 6 or not pincode.isdigit():
                raise ValidationError("Pincode must be exactly 6 digits.", field="pincode")
            self.pincode = pincode
        if latitude is not None:
            self.latitude = latitude
        if longitude is not None:
            self.longitude = longitude
        self.touch()
