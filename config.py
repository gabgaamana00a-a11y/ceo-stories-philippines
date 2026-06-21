"""Central config for CEO Stories — Filipino success & rags-to-riches YouTube channel."""

import os

def get_openrouter_keys() -> list[str]:
    """Return all configured OpenRouter API keys in order.

    Reads OPENROUTER_API_KEY (primary) plus OPENROUTER_API_KEY_2 …
    OPENROUTER_API_KEY_10.  Empty / missing slots are skipped.
    Returns at least an empty list if none are set.
    """
    keys = []
    primary = os.getenv("OPENROUTER_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    for i in range(2, 11):
        k = os.getenv(f"OPENROUTER_API_KEY_{i}", "").strip()
        if k:
            keys.append(k)
    return keys


CHANNEL_NAME = "CEO Stories Philippines"
CHANNEL_NICHE = "ceo_success_stories"

# ── YouTube upload ────────────────────────────────────────────────────────────
UPLOAD_PRIVACY  = "public"   # public | unlisted | private
UPLOAD_CATEGORY = "22"       # 22 = People & Blogs
UPLOAD_TAGS = [
    # High-volume success/inspiration searches
    "ceo story", "success story philippines", "rags to riches",
    "pinoy success story", "negosyo story", "entrepreneur philippines",
    "ofw success story", "buhay ceo", "yaman story",
    "inspirational story tagalog", "motivational story philippines",
    "sipag at tiyaga", "pinoy entrepreneur", "success mindset",
    # Founder/business terms
    "ceo philippines", "business story", "startup philippines",
    "yumaman sa negosyo", "karanasan ng ceo", "tagumpay sa buhay",
    "mahirap hanggang sa yumaman", "pinoy billionaire story",
    "small business success", "ofw na naging ceo",
    # Engagement terms
    "inspirasyon", "motivation", "tagumpay", "pinoy pride",
    "ceo stories", "filipino success", "youtube motivational",
]

# ── Video format — 16:9 landscape for YouTube long-form ──────────────────────
VIDEO_WIDTH  = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS    = 30

# Target script length for a 8-12 minute video
SCRIPT_MIN_WORDS = 900
SCRIPT_MAX_WORDS = 1400

# ── TTS voices (Microsoft Edge TTS — free, Filipino language support) ─────────
# Uses edge-tts package. Only 2 Filipino neural voices available.
VOICES = {
    "NARRATOR":     "fil-PH-AngeloNeural",      # deep male narrator — ominous horror voice
    "OP":           "fil-PH-BlessicaNeural",   # female first-person storyteller
    "OP_MALE":      "fil-PH-AngeloNeural",      # male first-person storyteller
    "CHARACTER_F":  "fil-PH-BlessicaNeural",    # female character
    "CHARACTER_M":  "fil-PH-AngeloNeural",      # male character
    "CHARACTER_F2": "fil-PH-BlessicaNeural",    # secondary female
    "CHARACTER_M2": "fil-PH-AngeloNeural",      # secondary male
    # Aliases
    "SIYA_B":       "fil-PH-BlessicaNeural",
    "SIYA_L":       "fil-PH-AngeloNeural",
    "KAIBIGAN":     "fil-PH-AngeloNeural",
    "INA":          "fil-PH-BlessicaNeural",
    "AMA":          "fil-PH-AngeloNeural",
}

# Human-readable display names shown as on-screen speaker labels
SPEAKER_LABELS = {
    "NARRATOR":     "TAGAPAGSALAYSAY",
    "OP":           "KWENTISTA",
    "OP_MALE":      "KWENTISTA",
    "CHARACTER_F":  "SIYA",
    "CHARACTER_M":  "SIYA",
    "CHARACTER_F2": "KAIBIGAN",
    "CHARACTER_M2": "KAIBIGAN",
    "SIYA_B":       "SIYA",
    "SIYA_L":       "SIYA",
    "KAIBIGAN":     "KAIBIGAN",
    "INA":          "INA",
    "AMA":          "AMA",
    "BOSS":         "BOSS",
    "MENTOR":       "MENTOR",
    "INVESTOR":     "INVESTOR",
}

# ── Pexels B-roll scene mapping (success/inspiration themed) ──────────────────
SCENE_KEYWORDS = {
    "negosyo":      ["office workspace modern", "business meeting"],
    "opisina":      ["corporate office interior", "modern office building"],
    "probinsya":    ["rural philippines village", "simple life farming"],
    "lungsod":      ["city skyline philippines", "makati city"],
    "bahay":        ["simple house interior", "dream home luxury"],
    "tindahan":     ["small store business", "market stall"],
    "pamilya":      ["filipino family happy", "family dinner"],
    "paaralan":     ["students studying", "classroom learning"],
    "abroad":       ["airport travel", "modern city abroad"],
    "factory":      ["factory worker", "manufacturing plant"],
    "construction": ["construction worker", "building site"],
    "office":       ["people working office", "corporate meeting"],
    "default":      ["successful businessman", "modern office", "city skyline"],
}

# ── CEO story categories for sustainable 365-day rotation ─────────────────────
CEO_CATEGORIES = [
    "rags_to_riches",       # Mahirap → yumaman sa sipag
    "ofw_success",          # OFW na naging CEO / negosyante
    "small_business",       # Mula sa maliit na tindahan → malaking negosyo
    "startup_story",        # Tech startup, innovation
    "overseas_dream",       # Pinoy na nagtagumpay sa abroad
    "family_business",      # Pampamilyang negosyo na lumago
    "failure_to_success",   # Bagsak → bumangon → nagtagumpay
    "pinoy_ceo",            # Kilalang Pinoy CEO / entrepreneur story
    "humble_beginning",     # Mula sa hirap ng buhay → tagumpay
    "business_lesson",      # Aral sa negosyo at buhay CEO
]

# ── Schedule (Philippine Standard Time UTC+8 = prime time 8-9 PM PST) ────────
SCHEDULE_HOUR   = 8    # 08:00 UTC = 4:00 PM PHT (Philippine Time, UTC+8)
SCHEDULE_MINUTE = 0
