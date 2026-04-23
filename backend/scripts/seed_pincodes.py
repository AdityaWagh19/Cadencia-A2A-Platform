"""
Seed script: Populate pincode_geocodes table with major Indian city pincodes.

This seeds ~50 major city pincodes for development/testing. For production,
import the full India Post dataset (~19,000 pincodes) via CSV.

Usage:
    python -m scripts.seed_pincodes
"""

import asyncio
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

MAJOR_PINCODES = [
    # pincode, city, state, lat, lng, region
    ("110001", "New Delhi", "Delhi", 28.6139, 77.2090, "NORTH"),
    ("110020", "New Delhi (South)", "Delhi", 28.5672, 77.2100, "NORTH"),
    ("400001", "Mumbai", "Maharashtra", 18.9388, 72.8354, "WEST"),
    ("400070", "Mumbai (Kurla)", "Maharashtra", 19.0726, 72.8794, "WEST"),
    ("560001", "Bengaluru", "Karnataka", 12.9716, 77.5946, "SOUTH"),
    ("600001", "Chennai", "Tamil Nadu", 13.0827, 80.2707, "SOUTH"),
    ("700001", "Kolkata", "West Bengal", 22.5726, 88.3639, "EAST"),
    ("500001", "Hyderabad", "Telangana", 17.3850, 78.4867, "SOUTH"),
    ("380001", "Ahmedabad", "Gujarat", 23.0225, 72.5714, "WEST"),
    ("411001", "Pune", "Maharashtra", 18.5204, 73.8567, "WEST"),
    ("302001", "Jaipur", "Rajasthan", 26.9124, 75.7873, "NORTH"),
    ("226001", "Lucknow", "Uttar Pradesh", 26.8467, 80.9462, "NORTH"),
    ("462001", "Bhopal", "Madhya Pradesh", 23.2599, 77.4126, "CENTRAL"),
    ("440001", "Nagpur", "Maharashtra", 21.1458, 79.0882, "CENTRAL"),
    ("360001", "Rajkot", "Gujarat", 22.3039, 70.8022, "WEST"),
    ("395001", "Surat", "Gujarat", 21.1702, 72.8311, "WEST"),
    ("201001", "Ghaziabad", "Uttar Pradesh", 28.6692, 77.4538, "NORTH"),
    ("122001", "Gurugram", "Haryana", 28.4595, 77.0266, "NORTH"),
    ("141001", "Ludhiana", "Punjab", 30.9010, 75.8573, "NORTH"),
    ("160001", "Chandigarh", "Chandigarh", 30.7333, 76.7794, "NORTH"),
    ("452001", "Indore", "Madhya Pradesh", 22.7196, 75.8577, "CENTRAL"),
    ("800001", "Patna", "Bihar", 25.6093, 85.1376, "EAST"),
    ("751001", "Bhubaneswar", "Odisha", 20.2961, 85.8245, "EAST"),
    ("781001", "Guwahati", "Assam", 26.1445, 91.7362, "NORTHEAST"),
    ("682001", "Kochi", "Kerala", 9.9312, 76.2673, "SOUTH"),
    ("641001", "Coimbatore", "Tamil Nadu", 11.0168, 76.9558, "SOUTH"),
    ("530001", "Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185, "SOUTH"),
    ("831001", "Jamshedpur", "Jharkhand", 22.8046, 86.2029, "EAST"),
    ("492001", "Raipur", "Chhattisgarh", 21.2514, 81.6296, "CENTRAL"),
    ("834001", "Ranchi", "Jharkhand", 23.3441, 85.3096, "EAST"),
    ("110060", "New Delhi (Saket)", "Delhi", 28.5244, 77.2066, "NORTH"),
    ("400059", "Mumbai (Andheri)", "Maharashtra", 19.1197, 72.8464, "WEST"),
    ("560100", "Bengaluru (Electronic City)", "Karnataka", 12.8399, 77.6770, "SOUTH"),
    ("600040", "Chennai (Anna Nagar)", "Tamil Nadu", 13.0850, 80.2101, "SOUTH"),
    ("500081", "Hyderabad (HITEC City)", "Telangana", 17.4435, 78.3772, "SOUTH"),
    ("431001", "Aurangabad", "Maharashtra", 19.8762, 75.3433, "WEST"),
    ("421001", "Thane", "Maharashtra", 19.2183, 72.9781, "WEST"),
    ("390001", "Vadodara", "Gujarat", 22.3072, 73.1812, "WEST"),
    ("520001", "Vijayawada", "Andhra Pradesh", 16.5062, 80.6480, "SOUTH"),
    ("625001", "Madurai", "Tamil Nadu", 9.9252, 78.1198, "SOUTH"),
    ("208001", "Kanpur", "Uttar Pradesh", 26.4499, 80.3319, "NORTH"),
    ("250001", "Meerut", "Uttar Pradesh", 28.9845, 77.7064, "NORTH"),
    ("244001", "Moradabad", "Uttar Pradesh", 28.8386, 78.7733, "NORTH"),
    ("273001", "Gorakhpur", "Uttar Pradesh", 26.7606, 83.3732, "NORTH"),
    ("342001", "Jodhpur", "Rajasthan", 26.2389, 73.0243, "NORTH"),
    ("313001", "Udaipur", "Rajasthan", 24.5854, 73.7125, "NORTH"),
    ("474001", "Gwalior", "Madhya Pradesh", 26.2183, 78.1828, "CENTRAL"),
    ("482001", "Jabalpur", "Madhya Pradesh", 23.1815, 79.9864, "CENTRAL"),
    ("769001", "Rourkela", "Odisha", 22.2604, 84.8536, "EAST"),
    ("570001", "Mysuru", "Karnataka", 12.2958, 76.6394, "SOUTH"),
]


async def seed_pincodes() -> None:
    from src.shared.infrastructure.db.session import get_session_factory
    from src.marketplace.infrastructure.models import PincodeGeocodeModel
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as session:
        # Check if already seeded
        result = await session.execute(select(PincodeGeocodeModel).limit(1))
        if result.scalar_one_or_none():
            print("Pincodes already seeded. Skipping.")
            return

        for pincode, city, state, lat, lng, region in MAJOR_PINCODES:
            session.add(PincodeGeocodeModel(
                pincode=pincode,
                city=city,
                state=state,
                latitude=lat,
                longitude=lng,
                region=region,
            ))

        await session.commit()
        print(f"Seeded {len(MAJOR_PINCODES)} pincodes.")


if __name__ == "__main__":
    asyncio.run(seed_pincodes())
