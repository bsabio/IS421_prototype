"""Ingest attendees from an organizer-export CSV or an official platform API.

Hard rules enforced here:
- NO scraping, NO login-wall bypassing, NO CAPTCHA solving.
- Only two data channels: organizer CSV export **or** official API with
  user-supplied credentials.
- Every request carries a clear User-Agent string.
- All access is logged.
"""

from __future__ import annotations

import csv
import logging
from io import StringIO
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from enricher.models import APIConfig, AttendeeRaw, SourceType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CSV ingestion
# ---------------------------------------------------------------------------

# Map common CSV header variations to AttendeeRaw field names
_CSV_FIELD_MAP: dict[str, str] = {
    "name": "full_name",
    "full name": "full_name",
    "fullname": "full_name",
    "first name": "first_name",
    "firstname": "first_name",
    "first": "first_name",
    "last name": "last_name",
    "lastname": "last_name",
    "last": "last_name",
    "company": "company",
    "organisation": "company",
    "organization": "company",
    "org": "company",
    "role": "role",
    "title": "role",
    "job title": "role",
    "jobtitle": "role",
    "email": "email",
    "e-mail": "email",
    "event": "event",
    "event name": "event",
    "attending": "event",
    "linkedin": "linkedin_url",
    "linkedin_url": "linkedin_url",
    "linkedin url": "linkedin_url",
    "twitter": "twitter_url",
    "twitter_url": "twitter_url",
    "twitter url": "twitter_url",
    "x": "twitter_url",
    "x_url": "twitter_url",
    "github": "github_url",
    "github_url": "github_url",
    "github url": "github_url",
    "website": "website_url",
    "website_url": "website_url",
    "url": "website_url",
    "personal site": "website_url",
}

_KNOWN_FIELDS = set(AttendeeRaw.model_fields.keys()) - {"extra"}


def ingest_csv(path: str | Path) -> list[AttendeeRaw]:
    """Read attendees from an organizer-provided CSV file.

    Unknown columns are placed in the ``extra`` dict so no data is silently
    dropped.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    logger.info("Ingesting attendees from CSV: %s", path)
    attendees: list[AttendeeRaw] = []

    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row_num, row in enumerate(reader, start=2):  # header is row 1
            mapped: dict[str, Any] = {}
            extra: dict[str, str] = {}
            for header, value in row.items():
                if header is None or value is None:
                    continue
                norm_header = header.strip().lower()
                target = _CSV_FIELD_MAP.get(norm_header)
                if target and target in _KNOWN_FIELDS:
                    mapped[target] = value.strip()
                else:
                    extra[header.strip()] = value.strip()
            mapped["extra"] = extra
            try:
                attendees.append(AttendeeRaw(**mapped))
            except Exception as exc:
                logger.warning("Row %d skipped – %s", row_num, exc)

    logger.info("Ingested %d attendees from CSV", len(attendees))
    return attendees


# ---------------------------------------------------------------------------
# API ingestion
# ---------------------------------------------------------------------------

def _build_session(cfg: APIConfig) -> requests.Session:
    """Build a requests session with retry/backoff and a clear User-Agent."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": cfg.user_agent,
        "Accept": "application/json",
    })
    if cfg.api_key:
        session.headers["Authorization"] = f"Bearer {cfg.api_key}"

    retries = Retry(
        total=cfg.max_retries,
        backoff_factor=cfg.backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def ingest_api(cfg: APIConfig, event_id: str | None = None) -> list[AttendeeRaw]:
    """Fetch attendees from an official, documented platform API endpoint.

    This function ONLY hits the endpoint the organizer has authorised and
    uses the credentials supplied by the user.  It never follows redirects
    to login pages or attempts to bypass access controls.
    """
    eid = event_id or cfg.event_id
    if not eid:
        raise ValueError("event_id is required for API ingestion")
    if not cfg.base_url:
        raise ValueError("api.base_url must be set in the configuration")
    if not cfg.api_key:
        raise ValueError("api.api_key must be set – we do not access unauthenticated endpoints")

    url = f"{cfg.base_url.rstrip('/')}/events/{eid}/attendees"
    logger.info("Fetching attendees from API: %s", url)

    session = _build_session(cfg)
    attendees: list[AttendeeRaw] = []
    page = 1

    while True:
        resp = session.get(url, params={"page": page}, timeout=cfg.timeout)
        logger.info("API %s page=%d  ➜  HTTP %d", url, page, resp.status_code)

        if resp.status_code == 401:
            raise PermissionError("API returned 401 – check your api_key")
        if resp.status_code == 403:
            raise PermissionError(
                "API returned 403 – you are not authorised to access this attendee list"
            )
        resp.raise_for_status()

        payload = resp.json()
        items = payload if isinstance(payload, list) else payload.get("data", payload.get("attendees", []))
        if not items:
            break

        for item in items:
            mapped: dict[str, Any] = {}
            extra: dict[str, Any] = {}
            for key, value in item.items():
                norm_key = key.strip().lower().replace("-", "_").replace(" ", "_")
                target = _CSV_FIELD_MAP.get(norm_key, norm_key)
                if target in _KNOWN_FIELDS:
                    mapped[target] = str(value).strip() if value else None
                else:
                    extra[key] = value
            mapped["extra"] = extra
            try:
                attendees.append(AttendeeRaw(**mapped))
            except Exception as exc:
                logger.warning("API record skipped – %s", exc)

        # Pagination: stop when no next page
        next_url = None
        if isinstance(payload, dict):
            next_url = payload.get("next") or payload.get("next_page")
        if next_url:
            url = next_url
            page += 1
        else:
            break

    logger.info("Ingested %d attendees from API", len(attendees))
    return attendees
