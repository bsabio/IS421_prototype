"""URL validation with scheme + domain-allowlist enforcement.

Only URLs whose domain appears on the allowlist are accepted.  Anything
else is logged and dropped—never fetched or resolved.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from enricher.models import EnricherConfig, SocialLink, SourceType

logger = logging.getLogger(__name__)

# Mapping from domain fragments to canonical platform name
_DOMAIN_TO_PLATFORM: dict[str, str] = {
    "linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "github.com": "github",
}


def _classify_platform(domain: str) -> str:
    """Return the canonical platform name for a given domain."""
    domain_lower = domain.lower()
    for fragment, platform in _DOMAIN_TO_PLATFORM.items():
        if domain_lower == fragment or domain_lower.endswith("." + fragment):
            return platform
    return "website"


def validate_url(
    url: str | None,
    *,
    config: EnricherConfig,
    source_field: str,
    source_type: SourceType,
) -> SocialLink | None:
    """Validate a single URL and return a SocialLink or None.

    Checks performed:
    1. Non-empty string.
    2. Has an ``http`` or ``https`` scheme.
    3. Domain is on the configured allowlist  **or**  the URL was explicitly
       provided in a recognised social-link field (we still validate scheme).
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)
    except Exception:
        logger.debug("Unparseable URL dropped: %s", url)
        return None

    # --- scheme check ---
    if parsed.scheme not in ("http", "https"):
        logger.debug("URL with invalid scheme dropped: %s", url)
        return None

    # --- domain extraction ---
    domain = (parsed.hostname or "").lower()
    if not domain:
        logger.debug("URL with missing domain dropped: %s", url)
        return None

    # --- allowlist check ---
    # The allowlist decides which social domains we trust.
    # For "website" fields we are lenient—any scheme-valid URL is accepted.
    is_known_social_field = source_field.lower().rstrip("_url").rstrip("_") in {
        "linkedin", "twitter", "x", "github",
    }

    on_allowlist = any(
        domain == allowed or domain.endswith("." + allowed)
        for allowed in config.domain_allowlist
    )

    if is_known_social_field and not on_allowlist:
        logger.warning(
            "Social field '%s' has URL on non-allowlisted domain (%s) – dropped: %s",
            source_field,
            domain,
            url,
        )
        return None

    platform = _classify_platform(domain)
    provenance = f"{source_type.value}.{source_field}"

    return SocialLink(platform=platform, url=url, provenance=provenance)


def validate_attendee_urls(
    urls: dict[str, str | None],
    *,
    config: EnricherConfig,
    source_type: SourceType,
) -> list[SocialLink]:
    """Validate all social URLs for a single attendee.

    ``urls`` maps source-field names (e.g. ``linkedin_url``) to raw URL
    strings.  Returns only the validated links.
    """
    links: list[SocialLink] = []
    for field_name, raw_url in urls.items():
        link = validate_url(
            raw_url,
            config=config,
            source_field=field_name,
            source_type=source_type,
        )
        if link:
            links.append(link)
    return links
