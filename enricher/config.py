"""Load enricher configuration from YAML file."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from enricher.models import EnricherConfig


_DEFAULT_CONFIG_NAME = "enricher_config.yaml"


def load_config(path: Optional[str] = None) -> EnricherConfig:
    """Load configuration from a YAML file, falling back to defaults."""
    if path is None:
        path = _DEFAULT_CONFIG_NAME
    p = Path(path)
    if p.exists():
        with open(p) as f:
            raw = yaml.safe_load(f) or {}
        return EnricherConfig(**raw)
    return EnricherConfig()
