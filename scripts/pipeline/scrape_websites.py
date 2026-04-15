#!/usr/bin/env python3
"""
scrape_websites.py - Check restaurant websites & Instagram for child-friendly keywords.

Input:  scripts/pipeline/details.json
Output: scripts/pipeline/kid_friendly_web.json
Resume: scripts/pipeline/scrape_progress_web.json
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DETAILS_PATH = BASE_DIR / "details.json"
OUTPUT_PATH = BASE_DIR / "kid_friendly_web.json"
PROGRESS_PATH = BASE_DIR / "scrape_progress_web.json"

# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------
CHILD_KEYWORDS = [
    "お子様", "キッズ", "子連れ", "子ども連れ", "こども連れ",
    "ベビーカー", "ベビーチェア", "キッズチェア", "ハイチェア",
    "キッズメニュー", "お子様メニュー", "お子様ランチ", "お子さまメニュー",
    "離乳食", "ミルク用のお湯", "授乳室", "授乳",
    "子供用", "子ども用", "こども用",
    "おむつ替え", "おむつ交換",
    "家族連れ歓迎", "お子様歓迎", "お子様連れ歓迎",
    "ファミリー", "親子",
]

NEGATIVE_KEYWORDS = [
    "お子様お断り",
    "お子様のご入店",
    "お子様はご遠慮",
    "未就学児不可",
    "小学生未満",
]

TAG_RULES = [
    (["ベビーカー", "バリアフリー"], "ベビーカーOK"),
    (["座敷", "小上がり", "掘りごたつ", "畳"], "座敷あり"),
    (["キッズチェア", "子供用椅子", "ベビーチェア", "ハイチェア", "こども椅子"], "キッズチェアあり"),
    (["個室", "半個室", "貸切"], "個室あり"),
    (["キッズメニュー", "お子様メニュー", "お子様ランチ", "子供メニュー", "お子さまメニュー"], "子供メニューあり"),
    (["子連れ", "お子様歓迎", "家族連れ", "ファミリー", "お子様連れ歓迎"], "子連れOK"),
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 10
REQUEST_DELAY = 1.0
SAVE_INTERVAL = 50

# ---------------------------------------------------------------------------
# HTML tag stripper
# ---------------------------------------------------------------------------
class _TagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        self.parts.append(data)

    def get_text(self) -> str:
        return " ".join(self.parts)

    def error(self, message):
        pass


def strip_html(html: str) -> str:
    stripper = _TagStripper()
    try:
        stripper.feed(html)
    except Exception:
        pass
    return stripper.get_text()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _make_ssl_context() -> ssl.SSLContext:
    """Create an SSL context that ignores certificate errors (fallback)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_url(url: str) -> str | None:
    """Fetch a URL and return the decoded body, or None on error."""
    if not url or not url.startswith("http"):
        return None

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    # Try with default SSL first, then with no-verify fallback
    for ssl_ctx in [None, _make_ssl_context()]:
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ssl_ctx) as resp:
                raw = resp.read()
            # Try multiple encodings
            for enc in ("utf-8", "shift_jis", "latin-1"):
                try:
                    return raw.decode(enc)
                except (UnicodeDecodeError, LookupError):
                    continue
            return raw.decode("latin-1", errors="replace")
        except ssl.SSLError:
            continue  # retry with no-verify context
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Instagram helpers
# ---------------------------------------------------------------------------
_INSTAGRAM_PATTERN = re.compile(
    r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?'
)


def is_instagram_url(url: str) -> bool:
    if not url:
        return False
    return "instagram.com/" in url


def find_instagram_urls(html: str) -> list[str]:
    return _INSTAGRAM_PATTERN.findall(html)


def extract_og_description(html: str) -> str:
    """Extract og:description content from meta tags."""
    pattern = re.compile(
        r'<meta\s+[^>]*property=["\']og:description["\']\s+[^>]*content=["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    m = pattern.search(html)
    if m:
        return m.group(1)
    # Try reversed attribute order
    pattern2 = re.compile(
        r'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*property=["\']og:description["\']',
        re.IGNORECASE,
    )
    m2 = pattern2.search(html)
    if m2:
        return m2.group(1)
    return ""


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------
def search_keywords(text: str) -> tuple[list[str], list[str], bool]:
    """
    Search text for child-friendly / negative keywords.
    Returns: (matched_keywords, evidence_snippets, has_negative)
    """
    if not text:
        return [], [], False

    # Check negatives first
    for neg in NEGATIVE_KEYWORDS:
        if neg in text:
            return [], [], True

    matched = []
    evidence = []
    for kw in CHILD_KEYWORDS:
        idx = text.find(kw)
        if idx != -1:
            matched.append(kw)
            start = max(0, idx - 25)
            end = min(len(text), idx + len(kw) + 25)
            snippet = text[start:end].strip()
            # Clean up whitespace
            snippet = re.sub(r'\s+', ' ', snippet)
            evidence.append(snippet)

    return matched, evidence, False


# ---------------------------------------------------------------------------
# Tag extraction & scoring
# ---------------------------------------------------------------------------
def extract_tags(text: str) -> list[str]:
    """Determine which tags apply based on text content."""
    tags = []
    for keywords, tag_name in TAG_RULES:
        for kw in keywords:
            if kw in text:
                tags.append(tag_name)
                break
    return tags


def calculate_score(tags: list[str]) -> int:
    score = 3  # base score for passing keyword check
    if len(tags) >= 2:
        score += 1
    if len(tags) >= 4:
        score += 1
    return min(score, 5)


# ---------------------------------------------------------------------------
# Progress persistence
# ---------------------------------------------------------------------------
def load_progress() -> set[str]:
    if PROGRESS_PATH.exists():
        try:
            data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
            return set(data)
        except Exception:
            pass
    return set()


def save_progress(processed: set[str]):
    PROGRESS_PATH.write_text(
        json.dumps(sorted(processed), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_existing_results() -> list[dict]:
    if OUTPUT_PATH.exists():
        try:
            return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_results(results: list[dict]):
    OUTPUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------
def process_shop(shop: dict) -> dict | None:
    """
    Process a single shop. Returns a result dict if kid-friendly, else None.
    """
    place_id = shop.get("place_id", "")
    name = shop.get("name", "unknown")
    website_uri = shop.get("websiteUri", "") or ""
    instagram_url = shop.get("instagram_url", "") or ""

    all_matched_keywords: list[str] = []
    all_evidence: list[str] = []
    combined_text = ""
    source_parts: list[str] = []

    # ------------------------------------------------------------------
    # Step A: Official Website Check
    # ------------------------------------------------------------------
    website_html = ""
    if website_uri and not is_instagram_url(website_uri):
        website_html = fetch_url(website_uri) or ""
        time.sleep(REQUEST_DELAY)

        if website_html:
            plain_text = strip_html(website_html)
            matched, evidence, has_negative = search_keywords(plain_text)
            if has_negative:
                return None
            if matched:
                all_matched_keywords.extend(matched)
                all_evidence.extend(evidence)
                source_parts.append("website")
            combined_text += " " + plain_text

    # ------------------------------------------------------------------
    # Step B: Instagram Check
    # ------------------------------------------------------------------
    # Determine Instagram URL
    ig_url = ""
    if instagram_url:
        ig_url = instagram_url
    elif is_instagram_url(website_uri):
        ig_url = website_uri
    elif website_html:
        ig_links = find_instagram_urls(website_html)
        if ig_links:
            ig_url = ig_links[0]

    if ig_url:
        ig_html = fetch_url(ig_url)
        time.sleep(REQUEST_DELAY)

        if ig_html:
            og_desc = extract_og_description(ig_html)
            if og_desc:
                matched, evidence, has_negative = search_keywords(og_desc)
                if has_negative:
                    return None
                if matched:
                    all_matched_keywords.extend(matched)
                    all_evidence.extend(evidence)
                    source_parts.append("instagram")
                combined_text += " " + og_desc

    # No keywords found anywhere
    if not all_matched_keywords:
        return None

    # ------------------------------------------------------------------
    # Step C: Tag Extraction & Scoring
    # ------------------------------------------------------------------
    tags = extract_tags(combined_text)
    score = calculate_score(tags)

    # Determine source
    if len(source_parts) == 2:
        source = "both"
    elif source_parts:
        source = source_parts[0]
    else:
        source = "website"

    # Deduplicate
    seen_kw = set()
    unique_evidence = []
    for kw, ev in zip(all_matched_keywords, all_evidence):
        if kw not in seen_kw:
            seen_kw.add(kw)
            unique_evidence.append(ev)

    return {
        "place_id": place_id,
        "name": name,
        "address": shop.get("address", ""),
        "lat": shop.get("lat", 0),
        "lng": shop.get("lng", 0),
        "primaryType": shop.get("primaryType", ""),
        "websiteUri": website_uri,
        "instagram_url": ig_url or instagram_url,
        "photo_reference": shop.get("photo_reference", ""),
        "googleMapsUri": shop.get("googleMapsUri", ""),
        "tags": tags,
        "score": score,
        "evidence": unique_evidence,
        "source": source,
    }


def main():
    # Load input
    if not DETAILS_PATH.exists():
        print(f"ERROR: {DETAILS_PATH} not found")
        sys.exit(1)

    shops = json.loads(DETAILS_PATH.read_text(encoding="utf-8"))
    total = len(shops)
    print(f"Loaded {total} shops from details.json")

    # Load resume state
    processed = load_progress()
    results = load_existing_results()
    existing_ids = {r["place_id"] for r in results}

    if processed:
        print(f"Resuming: {len(processed)} already processed, {len(results)} kid-friendly found so far")

    # Stats
    stats = {
        "websites_checked": 0,
        "instagram_checked": 0,
        "skipped_no_url": 0,
        "errors": 0,
        "kid_friendly_found": 0,
        "tags_distribution": {},
    }

    count_since_save = 0

    for i, shop in enumerate(shops):
        place_id = shop.get("place_id", "")
        name = shop.get("name", "unknown")

        # Skip already processed
        if place_id in processed:
            continue

        website_uri = shop.get("websiteUri", "") or ""
        instagram_url = shop.get("instagram_url", "") or ""

        # Skip if no URL at all
        has_website = bool(website_uri) and not is_instagram_url(website_uri)
        has_instagram = bool(instagram_url) or is_instagram_url(website_uri)

        if not has_website and not has_instagram:
            processed.add(place_id)
            stats["skipped_no_url"] += 1
            print(f"  [{i+1}/{total}] {name} -> skipped (no URL)")
            continue

        if has_website:
            stats["websites_checked"] += 1
        if has_instagram:
            stats["instagram_checked"] += 1

        # Process
        try:
            result = process_shop(shop)
        except Exception as e:
            stats["errors"] += 1
            print(f"  [{i+1}/{total}] {name} -> ERROR: {e}")
            processed.add(place_id)
            continue

        processed.add(place_id)
        count_since_save += 1

        if result:
            stats["kid_friendly_found"] += 1
            if result["place_id"] not in existing_ids:
                results.append(result)
                existing_ids.add(result["place_id"])

            matched_kw = ", ".join(result["evidence"][:3])
            print(f"  [{i+1}/{total}] {name} -> FOUND (tags: {result['tags']}, keywords: {matched_kw})")

            # Update tag distribution
            for tag in result["tags"]:
                stats["tags_distribution"][tag] = stats["tags_distribution"].get(tag, 0) + 1
        else:
            print(f"  [{i+1}/{total}] {name} -> not found")

        # Periodic save
        if count_since_save >= SAVE_INTERVAL:
            save_results(results)
            save_progress(processed)
            count_since_save = 0
            print(f"  --- Progress saved ({len(results)} kid-friendly so far) ---")

    # Final save
    save_results(results)
    save_progress(processed)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total shops:          {total}")
    print(f"  Checked (total):      {len(processed)}")
    print(f"  Websites checked:     {stats['websites_checked']}")
    print(f"  Instagram checked:    {stats['instagram_checked']}")
    print(f"  Skipped (no URL):     {stats['skipped_no_url']}")
    print(f"  Errors:               {stats['errors']}")
    print(f"  Kid-friendly found:   {len(results)}")
    print()
    print("  Tag distribution:")
    for tag, count in sorted(stats["tags_distribution"].items(), key=lambda x: -x[1]):
        print(f"    {tag}: {count}")
    print("=" * 60)
    print(f"\nResults saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
