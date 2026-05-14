"""
trending.py — Fetch trending drama story seeds for Drama Desk.

Sources (no API key required):
  • Reddit public JSON API  (r/AITA, r/relationship_advice, r/entitledparents, etc.)
  • Curated fallback seed list for guaranteed daily output

Strategy: pull hot posts from drama subreddits, filter for high engagement,
and use the title as a story seed for the AI script writer.  We never
reproduce post body text verbatim — the AI generates a fully original
dramatised story inspired by the seed.
"""

import json
import os
import random
import re
import requests
from config import DRAMA_SUBREDDITS

_HEADERS = {
    "User-Agent": "DramaDeskBot/2.0 (YouTube education content)",
    "Accept": "application/json",
}

# Curated high-engagement drama seeds — US audience
FALLBACK_SEEDS = [
    "My fiance's mother exposed a shocking secret at our engagement party in front of everyone",
    "I found out my husband has been secretly sending money to his ex-wife for two years",
    "My sister uninvited me from her wedding because I refused to lose weight for the photos",
    "My coworker went through my personal messages and used them to get me fired",
    "My parents paid my sibling's rent for years but never once offered to help me",
    "My mother-in-law rearranged our entire home while I was at work without asking",
    "My best friend of fifteen years admitted she has been in love with my husband since before we met",
    "My dad left his entire estate to a secret second family none of us knew existed",
    "My boyfriend's ex keeps showing up at family events and his family defends her over me",
    "My brother announced to everyone I got fired before I had a chance to tell anyone",
    "My wife's family staged an intervention about my career at Thanksgiving dinner",
    "I found texts proving my best friend has been secretly talking to my ex for months",
    "My mother-in-law gave away the baby name we chose without asking us",
    "My boss promoted someone I spent six months training over me so I quit on the spot",
    "My sister publicly announced my pregnancy before I was ready at a family gathering",
    "My husband let his drunk friends into our house at two AM without asking me",
    "My wedding photographer is holding our photos hostage and demanding twice the price",
    "My roommate told my entire friend group I was struggling financially",
    "My neighbor was caught on camera going through my mail every day for three months",
    "A woman demanded I give up my first class seat for her child and caused a scene when I refused",
    "My landlord entered my apartment without permission and reported something legal to my employer",
    "My HOA fined me for a garden decoration that has been there for eight years",
    "My boss took credit for my year-long project in front of the entire company",
    "My coworker was spreading rumors about me and I only found out because my manager warned me",
    "I discovered my husband has been living a double life for the last three years",
    "My girlfriend admitted she cheated but only because she thought I already knew",
    "I found out my fiance proposed with his ex's ring and she recognized it at the engagement party",
    "My in-laws showed up for a two-day visit and have been here for six weeks with no signs of leaving",
    "I accidentally replied-all to a company email complaining about my manager and now HR is involved",
    "My team found out I earn fifty thousand dollars more than everyone else and things got ugly fast",
]

_HOOK_WORDS = [
    "aita", "aitah", "told", "refused", "left", "exposed", "found out",
    "secret", "fired", "cheated", "lied", "confronted", "broke up",
    "uninvited", "cut off", "called out", "demanded", "stormed out",
    "betrayed", "humiliated", "embarrassed",
]


_USED_SEEDS_FILE = os.path.join(os.path.dirname(__file__), "used_topics.json")


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
        json.dump(sorted(used), f, indent=2)


def _pick_unused_fallback() -> str:
    """Pick a fallback seed not yet used. Resets the list when all are exhausted."""
    used = _load_used_seeds()
    available = [s for s in FALLBACK_SEEDS if s not in used]
    if not available:
        # All seeds used — reset and start over
        print("[trending] All fallback seeds used — resetting used list")
        available = list(FALLBACK_SEEDS)
        with open(_USED_SEEDS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    seed = random.choice(available)
    _save_used_seed(seed)
    return seed


def get_trending_drama_seed() -> str:
    """Return a trending drama story seed from Reddit, or a curated fallback."""
    shuffled = random.sample(DRAMA_SUBREDDITS, min(4, len(DRAMA_SUBREDDITS)))
    for subreddit in shuffled:
        seed = _fetch_from_reddit(subreddit)
        if seed:
            _save_used_seed(seed)
            return seed
    print("[trending] Reddit unavailable — using curated fallback seed")
    return _pick_unused_fallback()


def _fetch_from_reddit(subreddit: str) -> str | None:
    """Return the title of a high-engagement drama post, or None on failure."""
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=30"
        resp = requests.get(url, headers=_HEADERS, timeout=12)
        if resp.status_code != 200:
            return None

        posts = resp.json().get("data", {}).get("children", [])
        candidates = []

        for post in posts:
            d = post.get("data", {})
            if d.get("stickied") or d.get("over_18") or d.get("is_video"):
                continue
            title = d.get("title", "").strip()
            score = d.get("score", 0)
            comments = d.get("num_comments", 0)

            if score < 300 or comments < 80 or len(title) < 30:
                continue

            hook_score = sum(1 for w in _HOOK_WORDS if w in title.lower())
            engagement = score + comments * 3 + hook_score * 500
            candidates.append((title, engagement))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        chosen_title = random.choice(candidates[:5])[0]
        # Strip "AITA for" / "AITAH for" prefix for cleaner seeds
        clean = re.sub(
            r"^(AITA|AITAH|AITa|aita)\s+(for\s+)?", "",
            chosen_title, flags=re.IGNORECASE
        ).strip()
        print(f"[trending] r/{subreddit}: {clean[:90]}...")
        return clean

    except Exception as e:
        print(f"[trending] r/{subreddit} fetch error: {e}")
        return None


# ── Legacy compatibility ───────────────────────────────────────────────────────
def get_trending_topic(niche: str = "aita_drama", top_n: int = 1):
    """Legacy shim — returns a drama seed regardless of niche argument."""
    seed = get_trending_drama_seed()
    if top_n == 1:
        return seed
    return [seed]


def get_trending_suggestions(niche: str = "aita_drama", count: int = 8) -> list:
    seeds = [get_trending_drama_seed() for _ in range(count)]
    return [{"title": s, "score": 0} for s in seeds]
