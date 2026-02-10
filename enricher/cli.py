"""CLI entry-point for the Attendee Directory Enricher.

Usage:
    python -m enricher enrich --csv attendees.csv
    python -m enricher enrich --api --event-id XYZ
    python -m enricher export --format csv
    python -m enricher export --format json
"""

from __future__ import annotations

import argparse
import logging
import sys

from enricher.pipeline import run_api_pipeline, run_csv_pipeline
from enricher.config import load_config
from enricher.export import (
    compute_summary,
    export_csv,
    export_json,
    print_summary,
)
from enricher.models import AttendeeEnriched

# Re-export for ``python -m enricher``
import json
from pathlib import Path


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        level=level,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enricher",
        description="Attendee Directory Enricher – ethical, consent-based attendee data processing.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--config", default=None, help="Path to enricher_config.yaml"
    )
    sub = parser.add_subparsers(dest="command")

    # ---- enrich ----
    enrich_p = sub.add_parser("enrich", help="Ingest, normalise, validate, and enrich attendees")
    source = enrich_p.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", metavar="FILE", help="Path to organizer-export CSV")
    source.add_argument("--api", action="store_true", help="Use the official platform API")
    enrich_p.add_argument("--event-id", metavar="ID", help="Event ID (required with --api)")
    enrich_p.add_argument(
        "--format",
        dest="out_format",
        choices=["csv", "json", "both"],
        default="both",
        help="Output format (default: both)",
    )

    # ---- export ----
    export_p = sub.add_parser(
        "export",
        help="Re-export a previous enrichment run to a different format",
    )
    export_p.add_argument(
        "--format",
        dest="out_format",
        choices=["csv", "json"],
        required=True,
        help="Target format",
    )
    export_p.add_argument(
        "--input",
        default="output/attendees_enriched.json",
        help="Path to existing enriched JSON (default: output/attendees_enriched.json)",
    )

    return parser


def _formats(fmt: str) -> list[str]:
    if fmt == "both":
        return ["json", "csv"]
    return [fmt]


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    if args.command == "enrich":
        if args.csv:
            run_csv_pipeline(
                csv_path=args.csv,
                config_path=args.config,
                output_formats=_formats(args.out_format),
            )
        elif args.api:
            if not args.event_id:
                parser.error("--event-id is required when using --api")
            run_api_pipeline(
                event_id=args.event_id,
                config_path=args.config,
                output_formats=_formats(args.out_format),
            )

    elif args.command == "export":
        config = load_config(args.config)
        src = Path(args.input)
        if not src.exists():
            print(f"Error: {src} not found. Run 'enrich' first.", file=sys.stderr)
            sys.exit(1)
        data = json.loads(src.read_text())
        attendees = [AttendeeEnriched(**a) for a in data["attendees"]]
        summary_data = data.get("summary", {})
        from enricher.models import EnrichmentSummary
        summary = EnrichmentSummary(**summary_data)

        if args.out_format == "json":
            export_json(attendees, summary, config.output_dir)
        else:
            export_csv(attendees, summary, config.output_dir)
        print(print_summary(summary))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
