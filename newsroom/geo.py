"""Geospatial helpers for the funding heatmap.

This module keeps a static Tri-State coordinate lookup to avoid runtime
geocoding/API calls.
"""

from __future__ import annotations

from typing import Dict, List

from .models import FundingItem

# Static lookup for common Tri-State startup hubs.
TRI_STATE_COORDS: Dict[str, tuple[float, float]] = {
    "new york, ny": (40.7128, -74.0060),
    "manhattan, ny": (40.7831, -73.9712),
    "brooklyn, ny": (40.6782, -73.9442),
    "queens, ny": (40.7282, -73.7949),
    "bronx, ny": (40.8448, -73.8648),
    "staten island, ny": (40.5795, -74.1502),
    "jersey city, nj": (40.7178, -74.0431),
    "hoboken, nj": (40.7430, -74.0324),
    "newark, nj": (40.7357, -74.1724),
    "new brunswick, nj": (40.4862, -74.4518),
    "princeton, nj": (40.3573, -74.6672),
    "trenton, nj": (40.2171, -74.7429),
    "camden, nj": (39.9259, -75.1196),
    "vineland, nj": (39.4864, -75.0257),
    "new haven, ct": (41.3083, -72.9279),
    "stamford, ct": (41.0534, -73.5387),
    "bridgeport, ct": (41.1865, -73.1952),
    "white plains, ny": (41.0330, -73.7629),
    "yonkers, ny": (40.9312, -73.8988),
    "long island city, ny": (40.7447, -73.9485),
    "boston, ma": (42.3601, -71.0589),
}


def _normalize_location(location: str) -> str:
    return (location or "").strip().lower()


def _coords_for_location(location: str) -> tuple[float, float] | None:
    """Resolve coordinates from static lookup with simple fallbacks."""
    normalized = _normalize_location(location)
    if not normalized:
        return None

    if normalized in TRI_STATE_COORDS:
        return TRI_STATE_COORDS[normalized]

    # Fallback: match by city part before comma (e.g. "New York" -> "new york, ny")
    city = normalized.split(",")[0].strip()
    for key, coords in TRI_STATE_COORDS.items():
        if key.startswith(city + ",") or key == city:
            return coords

    return None


def build_funding_heatmap_data(funding_items: List[FundingItem]) -> List[Dict[str, object]]:
    """Build serializable point data for Leaflet heat/bubble rendering."""
    points: List[Dict[str, object]] = []

    for item in funding_items:
        coords = _coords_for_location(item.location or "")
        if coords is None:
            continue

        amount_value = float(item.amount_numeric or 0)
        if amount_value < 0:
            amount_value = 0.0

        points.append(
            {
                "startup_name": item.startup_name,
                "location": item.location or "Unknown",
                "lat": coords[0],
                "lng": coords[1],
                "amount_numeric": amount_value,
                "amount": item.amount,
                "categories": item.categories or [],
                "who": item.who_what_why_when_where_how.who,
                "why": item.who_what_why_when_where_how.why,
            }
        )

    return points
