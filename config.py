"""Central config for Drama Desk — AITA/Reddit drama YouTube channel."""

CHANNEL_NAME = "Drama Desk"
CHANNEL_NICHE = "aita_drama"

# ── YouTube upload ────────────────────────────────────────────────────────────
UPLOAD_PRIVACY  = "public"   # public | unlisted | private
UPLOAD_CATEGORY = "22"       # 22 = People & Blogs
UPLOAD_TAGS = [
    "reddit stories", "aita", "am i the asshole", "reddit drama",
    "relationship drama", "family drama", "reddit", "storytime",
    "drama channel", "reddit relationship advice", "entitled people",
    "aita reddit", "relationship advice", "cheating story", "true story",
]

# ── Video format — 16:9 landscape for YouTube long-form ──────────────────────
VIDEO_WIDTH  = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS    = 30

# Target script length for a 5-10 minute video
SCRIPT_MIN_WORDS = 700
SCRIPT_MAX_WORDS = 1200

# ── TTS voices (Microsoft Edge TTS neural voices) ────────────────────────────
# Multi-voice cast gives a "radio drama" feel
VOICES = {
    "NARRATOR":     "en-US-AriaNeural",    # Warm authoritative host
    "OP":           "en-US-JennyNeural",   # Female original poster
    "OP_MALE":      "en-US-GuyNeural",     # Male original poster
    "CHARACTER_F":  "en-US-NancyNeural",   # Primary female character
    "CHARACTER_M":  "en-US-TonyNeural",    # Primary male character
    "CHARACTER_F2": "en-US-SaraNeural",    # Secondary female character
    "CHARACTER_M2": "en-US-DavisNeural",   # Secondary male character
}

# Human-readable display names shown as on-screen speaker labels
SPEAKER_LABELS = {
    "NARRATOR":     "NARRATOR",
    "OP":           "OP",
    "OP_MALE":      "OP",
    "CHARACTER_F":  "HER",
    "CHARACTER_M":  "HIM",
    "CHARACTER_F2": "HER FRIEND",
    "CHARACTER_M2": "HIS FRIEND",
}

# ── Pexels B-roll scene mapping ───────────────────────────────────────────────
# Maps detected scene keywords in script → Pexels search queries
SCENE_KEYWORDS = {
    "restaurant":   ["restaurant dining", "cafe people"],
    "kitchen":      ["kitchen cooking", "home kitchen"],
    "bedroom":      ["bedroom interior", "home room"],
    "office":       ["office workplace", "business meeting"],
    "wedding":      ["wedding ceremony", "bride"],
    "phone":        ["smartphone texting", "phone call"],
    "family":       ["family dinner", "family gathering"],
    "outdoor":      ["city street people", "park outdoor"],
    "argument":     ["couple conflict", "people arguing"],
    "couple":       ["couple relationship", "man woman"],
    "money":        ["money finance", "cash bills"],
    "default":      ["cinematic people", "dramatic indoor", "living room"],
}

# ── Reddit drama subreddits (for trending story seeds) ───────────────────────
DRAMA_SUBREDDITS = [
    "AmItheAsshole",
    "AITAH",
    "relationship_advice",
    "entitledparents",
    "tifu",
    "TrueOffMyChest",
    "offmychest",
    "weddingshaming",
    "JUSTNOMIL",
]

# ── Schedule ──────────────────────────────────────────────────────────────────
SCHEDULE_HOUR   = 14   # 2 PM UTC = 9 AM EST / 10 AM EDT
SCHEDULE_MINUTE = 0
