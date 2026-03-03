"""
AI Toolkit CLI for newsletter enrichment.

Generates:
- Rich paragraph prose from structured newsletter story data
- Story-specific image assets for full-page newsletter placeholders

Usage:
    python -m newsroom.ai_toolkit
    python -m newsroom.ai_toolkit --ranked data/ranked.json --output output/newsletter_ai_assets.json
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any

import requests

from .models import FundingItem, EventItem, AcceleratorItem
from .utils import load_config
from .web_template import build_home_articles_payload


def _word_count(text: str) -> int:
    return len([w for w in (text or '').split() if w.strip()])


def _fallback_longform_article(article: Dict[str, str], min_words: int, max_words: int) -> str:
    headline = article.get("headline", "This Story")
    dek = article.get("dek", "")
    summary = article.get("summary", "")
    section = article.get("sectionLabel", "News")
    source = article.get("sourceUrl", "")
    base_body = article.get("body", "")

    seed_points = [part.strip() for part in base_body.split("\n\n") if part.strip()]
    if not seed_points and summary:
        seed_points = [summary]

    paragraphs: List[str] = []
    paragraphs.append(
        f"{headline} sits at the center of this week’s {section.lower()} conversation, and the details point to a bigger shift that readers should pay attention to now. "
        f"{dek} The available reporting indicates this is not an isolated update, but part of an ongoing pattern that is shaping decisions across founders, operators, and investors."
    )

    for point in seed_points[:3]:
        paragraphs.append(
            f"At the core of the story is a concrete update: {point} That development matters because it changes what stakeholders can realistically plan for in the near term. "
            f"When similar milestones appear in a short window, they often influence hiring, product velocity, and partnership timing across the broader ecosystem."
        )

    paragraphs.append(
        "From an execution standpoint, this moment highlights a familiar newsroom theme: momentum is rarely created by a single announcement. "
        "It is usually the result of months of operational choices, customer validation, and resource allocation that finally become visible in one public update. "
        "For readers tracking outcomes rather than headlines, the key question is whether the organization can translate this moment into consistent follow-through over the next two quarters."
    )

    paragraphs.append(
        "The practical implications are straightforward. Teams in the same category will likely benchmark against this development, and market participants will adjust expectations in response. "
        "That can create secondary effects: faster competitive cycles, tighter performance standards, and stronger pressure to show measurable progress. "
        "In that environment, clarity around milestones and execution quality becomes more important than broad claims."
    )

    paragraphs.append(
        "For newsletter readers, the takeaway is to treat this as a directional signal rather than a final verdict. "
        "The immediate update is important, but the next stage is where real value is proven: product adoption, operational discipline, and sustained delivery. "
        "If those indicators trend in the right direction, this story can become a reference point for what disciplined growth looks like in the current cycle."
    )

    if source:
        paragraphs.append(
            f"Source note: this article is grounded in the linked source material ({source}) and the structured newsletter summary. "
            "It focuses on expanding readability and context while preserving the original facts, names, and figures available in the input."
        )

    text = "\n\n".join(paragraphs)
    while _word_count(text) < min_words:
        text += (
            "\n\nIn context, the most useful way to read this update is to watch what happens next: whether commitments are met, whether timelines hold, "
            "and whether outcomes remain consistent as attention shifts from announcement to execution."
        )

    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip() + "..."

    return text


class OpenAICompatibleClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com",
        timeout: int = 60,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    def _post(self, endpoint: str, payload: Dict[str, Any], retries: int = 2) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = self.session.post(url, json=payload, timeout=self.timeout)
                if resp.status_code >= 400:
                    raise RuntimeError(f"{resp.status_code} {resp.text[:300]}")
                return resp.json()
            except Exception as exc:
                last_err = exc
                if attempt < retries:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                raise RuntimeError(f"API request failed for {endpoint}: {last_err}") from last_err
        raise RuntimeError("Unreachable")

    def write_paragraphs(
        self,
        article: Dict[str, str],
        model: str,
        min_words: int = 500,
        max_words: int = 1000,
    ) -> str:
        system_prompt = (
            "You are a newsroom writing assistant. "
            "Convert structured newsletter notes into polished long-form newsletter prose. "
            "Do not invent facts. Keep names, dates, amounts, and claims grounded in the provided content."
        )

        user_prompt = (
            f"Rewrite this newsletter item as a full article between {min_words} and {max_words} words.\n"
            "Style: journalistic, readable, plain English, no bullet points.\n"
            "Output: 5-9 paragraphs with natural transitions and newsroom tone.\n"
            "Constraints: no hallucinations, no new companies, no new numbers, no fake quotes.\n"
            "You may elaborate implications and context only when clearly supported by the provided content.\n\n"
            f"Section: {article.get('sectionLabel', '')}\n"
            f"Headline: {article.get('headline', '')}\n"
            f"Dek: {article.get('dek', '')}\n"
            f"Source URL: {article.get('sourceUrl', '')}\n"
            f"Current Body:\n{article.get('body', '')}\n"
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        data = self._post("/v1/chat/completions", payload)
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise RuntimeError(f"Unexpected text response shape: {data}") from exc

    def generate_image(self, prompt: str, model: str, size: str = "1536x1024") -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
        }
        data = self._post("/v1/images/generations", payload)

        try:
            item = data["data"][0]
        except Exception as exc:
            raise RuntimeError(f"Unexpected image response shape: {data}") from exc

        b64 = item.get("b64_json")
        if b64:
            return f"data:image/png;base64,{b64}"

        url = item.get("url")
        if url:
            return url

        raise RuntimeError(f"No image payload found in response: {data}")


def _load_env_file(env_path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values

    for line in env_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, val = s.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        values[key] = val
    return values


def _build_home_articles_from_ranked(ranked_path: Path, config: Dict[str, Any]) -> List[Dict[str, str]]:
    with ranked_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    funding_items = [FundingItem.from_dict(item) for item in data.get("funding", [])]
    event_items = [EventItem.from_dict(item) for item in data.get("events", [])]
    accelerator_items = [AcceleratorItem.from_dict(item) for item in data.get("accelerators", [])]

    return build_home_articles_payload(
        funding_items=funding_items,
        event_items=event_items,
        accelerator_items=accelerator_items,
        config=config,
    )


def _image_prompt(article: Dict[str, str]) -> str:
    section = article.get("sectionLabel", "News")
    headline = article.get("headline", "")
    dek = article.get("dek", "")
    summary = article.get("summary", "")

    return (
        "Editorial illustration for a technology business newsletter. "
        f"Section: {section}. "
        f"Headline context: {headline}. "
        f"Supporting context: {dek} {summary}. "
        "Style: clean, modern, photorealistic or high-end digital editorial art, "
        "landscape composition, no logos, no text overlays, no watermark."
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate AI text+image assets for newsletter HTML placeholders")
    parser.add_argument("--ranked", default=None, help="Path to ranked.json (default from config)")
    parser.add_argument("--output", default=None, help="Output JSON path (default: output/newsletter_ai_assets.json)")
    parser.add_argument("--env-file", default=".env", help="Path to env file containing API keys")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY", help="Primary API key variable name")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible base URL (default: OPENAI_BASE_URL or api.openai.com)")
    parser.add_argument("--text-model", default="gpt-4.1-mini", help="Text model for paragraph expansion")
    parser.add_argument("--image-model", default="gpt-image-1", help="Image model")
    parser.add_argument("--image-size", default="1536x1024", help="Image size, e.g. 1024x1024 or 1536x1024")
    parser.add_argument("--max-articles", type=int, default=0, help="Optional cap on number of articles (0 = all)")
    parser.add_argument("--text-only", action="store_true", help="Generate only paragraph prose; skip image generation")
    parser.add_argument("--min-words", type=int, default=500, help="Minimum target word count for each article body")
    parser.add_argument("--max-words", type=int, default=1000, help="Maximum target word count for each article body")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    return parser


def main(argv: List[str] | None = None) -> None:
    args = _parser().parse_args(argv)

    if args.min_words < 100:
        raise ValueError("--min-words must be at least 100")
    if args.max_words <= args.min_words:
        raise ValueError("--max-words must be greater than --min-words")

    cfg = load_config()
    data_dir = Path(cfg["storage"]["data_dir"])
    output_dir = Path(cfg["output"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    ranked_path = Path(args.ranked) if args.ranked else data_dir / "ranked.json"
    output_path = Path(args.output) if args.output else output_dir / "newsletter_ai_assets.json"

    existing_assets: Dict[str, Dict[str, Any]] = {}
    if output_path.exists():
        try:
            existing_payload = json.loads(output_path.read_text(encoding="utf-8"))
            maybe_articles = existing_payload.get("articles", {})
            if isinstance(maybe_articles, dict):
                existing_assets = maybe_articles
        except (OSError, json.JSONDecodeError):
            existing_assets = {}

    if not ranked_path.exists():
        raise FileNotFoundError(f"Ranked input not found: {ranked_path}. Run `python -m newsroom.rank` first.")

    env_vals = _load_env_file(Path(args.env_file))
    for key, value in env_vals.items():
        os.environ[key] = value

    api_key = os.getenv(args.api_key_env) or os.getenv("API_KEY")
    if not api_key:
        raise ValueError(
            f"API key missing. Set `{args.api_key_env}` (or `API_KEY`) in {args.env_file} or environment."
        )

    base_url = args.base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com"
    client = OpenAICompatibleClient(api_key=api_key, base_url=base_url, timeout=args.timeout)

    articles = _build_home_articles_from_ranked(ranked_path, cfg)
    if args.max_articles > 0:
        articles = articles[: args.max_articles]

    assets: Dict[str, Dict[str, Any]] = {}

    print(f"Generating AI assets for {len(articles)} newsletter stories...")
    for idx, article in enumerate(articles, start=1):
        story_id = article["id"]
        print(f"[{idx}/{len(articles)}] {story_id} :: {article.get('headline', '')}")

        try:
            rewritten_body = client.write_paragraphs(
                article,
                model=args.text_model,
                min_words=args.min_words,
                max_words=args.max_words,
            )
            if _word_count(rewritten_body) < args.min_words:
                print("  ! text too short; fallback expansion used")
                rewritten_body = _fallback_longform_article(
                    article,
                    min_words=args.min_words,
                    max_words=args.max_words,
                )
        except Exception as exc:
            print(f"  ! text generation fallback used ({exc})")
            rewritten_body = _fallback_longform_article(
                article,
                min_words=args.min_words,
                max_words=args.max_words,
            )

        prompt = _image_prompt(article)
        image_url = ""

        if not args.text_only:
            try:
                image_url = client.generate_image(prompt=prompt, model=args.image_model, size=args.image_size)
            except Exception as exc:
                image_url = existing_assets.get(story_id, {}).get("image_url", "")
                print(f"  ! image generation fallback used ({exc})")

        assets[story_id] = {
            "headline": article.get("headline", ""),
            "section": article.get("sectionLabel", ""),
            "image_prompt": prompt,
            "image_url": image_url,
            "body": rewritten_body,
            "source_url": article.get("sourceUrl", ""),
        }

    payload = {
        "metadata": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ranked_input": str(ranked_path).replace("\\", "/"),
            "text_model": args.text_model,
            "image_model": args.image_model if not args.text_only else "",
            "base_url": base_url,
            "text_only": args.text_only,
            "min_words": args.min_words,
            "max_words": args.max_words,
        },
        "articles": assets,
    }

    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Saved AI assets to {output_path}")
    print("Next: run `python -m newsroom.render --format html` to apply assets to newsletter HTML.")


if __name__ == "__main__":
    main()
