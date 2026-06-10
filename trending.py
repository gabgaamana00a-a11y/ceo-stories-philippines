"""
trending.py — Pick story seeds for Kwentong Multo.

Strategy: rotate through 10 horror sub-categories from topics.json,
ensuring variety across the full year.  No external API needed — fully
self-contained so the pipeline runs forever without Reddit or scraping.
"""

import json
import os
import random
from datetime import date

_TOPICS_FILE     = os.path.join(os.path.dirname(__file__), "topics.json")
_USED_SEEDS_FILE = os.path.join(os.path.dirname(__file__), "used_topics.json")


# ── Category rotation order (10 categories = 10-day cycle) ───────────────────
_CATEGORY_ORDER = [
    "aswang_folklore",
    "multo_ghost",
    "ofw_horror",
    "paaralan_horror",
    "engkanto_spirits",
    "ospital_horror",
    "probinsya_horror",
    "urban_legend",
    "pamilya_horror",
    "panaginip_paranormal",
]


def _load_topics() -> dict:
    try:
        with open(_TOPICS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("tagalog_horror", {})
    except Exception as e:
        print(f"[trending] topics.json load error: {e}")
        return {}


def _load_used_seeds() -> set:
    try:
        with open(_USED_SEEDS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_used_seed(seed: str) -> None:
    used = _load_used_seeds()
    used.add(seed)
    with open(_USED_SEEDS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(used), f, ensure_ascii=False, indent=2)


def _get_todays_category() -> str:
    """Rotate through categories based on day-of-year so each gets equal coverage."""
    day_of_year = date.today().timetuple().tm_yday
    return _CATEGORY_ORDER[day_of_year % len(_CATEGORY_ORDER)]


def get_trending_drama_seed() -> str:
    """Return a horror story seed from today'"'"'s rotating category."""
    topics = _load_topics()
    used   = _load_used_seeds()

    category = _get_todays_category()
    seeds    = topics.get(category, [])

    # Try current category first, then fall back to any unused seed
    available = [s for s in seeds if s not in used]
    if not available:
        # Try other categories
        all_seeds = [s for cat in topics.values() for s in cat]
        available = [s for s in all_seeds if s not in used]

    if not available:
        # All seeds exhausted — reset and start over
        print("[trending] All seeds used — resetting used list")
        with open(_USED_SEEDS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        all_seeds = [s for cat in topics.values() for s in cat]
        available = list(all_seeds)

    seed = random.choice(available)
    _save_used_seed(seed)
    print(f"[trending] Category: {category} — Seed: {seed[:80]}...")
    return seed


# ── Title deduplication ──────────────────────────────────────────────────────
_USED_TITLES_FILE = os.path.join(os.path.dirname(__file__), "used_titles.json")


def _load_used_titles() -> set:
    try:
        with open(_USED_TITLES_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_used_title(title: str) -> None:
    """Record a generated title so it is never reused."""
    used = _load_used_titles()
    used.add(title)
    with open(_USED_TITLES_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(used), f, ensure_ascii=False, indent=2)


def is_title_used(title: str) -> bool:
    """Return True if *title* has already been used for a published video."""
    return title in _load_used_titles()


# ── Video log ─────────────────────────────────────────────────────────────────
_VIDEO_LOG_FILE = os.path.join(os.path.dirname(__file__), "video_log.json")


def append_video_log(entry: dict) -> None:
    """
    Append one record to video_log.json.
    Expected keys: date, seed, title, youtube_url, duration_seconds.
    """
    try:
        with open(_VIDEO_LOG_FILE, encoding="utf-8") as f:
            log = json.load(f)
    except Exception:
        log = []
    log.append(entry)
    with open(_VIDEO_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ── Legacy compatibility shim ─────────────────────────────────────────────────
def get_trending_topic(niche: str = "tagalog_horror", top_n: int = 1):
    """Legacy shim used by older batch/scheduler code."""
    seed = get_trending_drama_seed()
    return [seed] if top_n > 1 else seed
