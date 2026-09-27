"""
content_gen.py — High-CTR content bank generator for CEO Stories Philippines.

Generates complete video content packages (title, script, description, CTA)
using OpenRouter (google/gemini-2.5-flash-lite) and saves them to content.csv.

The CSV is the SINGLE SOURCE OF TRUTH — main.py consumes rows from it instead
of generating content on the fly during the workflow.

CSV columns:
    id, seed, category, title, script, description, cta, used, created_at

Usage:
    python content_gen.py                 # generate 30 packages (default)
    python content_gen.py --count 50      # generate 50 packages
    python content_gen.py --minutes 10    # target script length
    python content_gen.py --stats         # show CSV stats only
"""

import os
import sys
import re
import csv
import json
import time
import random
import argparse
from datetime import datetime

import requests
from dotenv import load_dotenv

# Windows console is cp1252 by default and crashes on emoji/arrows in titles.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

load_dotenv()

CSV_FILE = os.path.join(os.path.dirname(__file__), "content.csv")
MODEL = "google/gemini-2.5-flash-lite"

CSV_HEADERS = [
    "id", "seed", "category", "title",
    "script", "description", "cta", "used", "created_at",
]


# ── System prompt — HIGH CTR hook-first formula ───────────────────────────────

_SYSTEM_PROMPT = """Ikaw ay isang EKSPERTO sa viral YouTube scripting para sa "CEO Stories Philippines" — isang Filipino channel na nagkukuwento ng mga kwento ng tagumpay: mula sa kahirapan tungo sa pagiging CEO.

TARGET: Filipino adults 18-45 (Pilipinas + OFW). Scroll-happy. MAHINA ang attention span. Kailangan mong huwag silang paalisin sa unang 3 SEGUNDO.

═══ ANG PINAKAMAHALAGANG BAGAY: ANG HOOK ═══

Ang UNANG LINYA ng [NARRATOR] ay DAPAT ang pinaka-nakakagulat, pinaka-dramatiko, o pinaka-misteryosong linya ng BUONG KWENTO. Ito ang "scroll-stopper."

MGA HALIMBAWA NG MABUBUTING HOOK (pattern — hindi kopyahin):
- "Isang gabi, natulog siya sa bangketa na walang makain. Limang taon pagkatapos, pagmamay-ari na niya ang buong kalye."
- "Sinabihan siya ng kanyang boss: 'Wala kang mararating sa buhay.' Ngayon, ang boss niya ang nag-aapply sa kanya."
- "May lihim siyang itinatago — isang bagay na magbabago sa lahat. At ngayon, sasabihin ko na sa inyo."
- "P1,000 lang ang nasa bulsa niya nang umalis siya ng Pilipinas. Hindi niya alam na babalik siya bilang bilyonaryo."

PAGKATAPOS NG HOOK: "Hayaan ninyong ikuwento ko kung paano nagsimula ang lahat."

═══ OPEN LOOPS (panatilihin silang nanonood) ═══
Tuwing 60-90 segundo, maglagay ng "open loop" — isang bagay na ipapaalam ngunit hindi pa isasabi ang detalye:
- "Ngunit may isang bagay na hindi ko pa nasasabi sa inyo..."
- "At ang nangyari pagkatapos ay HINDI ko inaasahan."
- "Pero bago iyon, kailangan ninyong malaman ang isang bagay."
- "Ito ang bahagi na hindi ko pa naikuwento kahit kanino."

═══ SPEAKER TAGS (gamitin LAMANG ang mga ito) ═══
  [NARRATOR]     — Tagapagsalaysay. Mainit, dramatikong boses.
  [OP_MALE]      — Lalaking bida na nagkukwento (first-person)
  [OP]           — Babaeng bida na nagkukwento (first-person)
  [CHARACTER_M]  — Lalaking karakter (gamitin ang totoong pangalan sa teksto)
  [CHARACTER_F]  — Babaeng karakter (gamitin ang totoong pangalan)
  [CHARACTER_M2] — Pangalawang lalaki (kung kailangan)
  [CHARACTER_F2] — Pangalawang babae (kung kailangan)

BAWAL: [SIYA] [SILA] [KAIBIGAN] [INA] [AMA] [ATE] [KUYA] [LOLA] atbp.

═══ ESTRUKTURA (sundin EKSAKTO) ═══
1. [NARRATOR] — HOOK (1-2 pangungusap, pinaka-dramatiko) + "Hayaan ninyong ikuwento..."
2. [OP_MALE]/[OP] — Setup: sino siya, saan, gaano kahirap, anong pangarap
3. [NARRATOR] — Bridge + mid-story CTA: "I-like at mag-comment ng 💪 kung naiintindihan mo ang pakiramdam."
4. Dialogue exchange (5+ linya, emosyonal, totoong pangalan)
5. [NARRATOR] — Stakes raiser + retention hook: "Manatili kayo — dahil ang susunod ay HINDI kapani-paniwala."
6. [OP] — Ang pagbagsak / pagsubok / pagtatraydor
7. Dialogue — ang pagbangon at determinasyon
8. [OP] — Ang tagumpay (breakthrough moment)
9. [NARRATOR] — Aftermath + aral
10. [NARRATOR] — Final CTA (mag-subscribe, i-share, mag-comment)

═══ MGA PATAKARAN ═══
- Haba: {min_words}-{max_words} salita
- Natural na Tagalog — casual, contractions, emosyonal
- Totoong Filipino detalye: pangalan ng lugar, edad, trabaho, pamilya
- I-OUTPUT LAMANG ANG SCRIPT — walang pamagat, walang markdown, walang asterisk, walang stage directions
- Magsimula AGAD sa [NARRATOR]
- Huwag gumamit ng emoji SA LOOB ng script (para sa TTS)
"""


_TITLE_PROMPT = """Gumawa ng ISANG high-CTR YouTube title para sa Tagalog CEO success story:

KWENTO: {seed}

ANG MGA SIKRETO NG HIGH-CTR FILIPINO TITLE:
- Magsimula sa isang SHOCKING statement, numero, o damdamin (₱500, 5 taon, ₱1M, "Tinanggal", "Nilait")
- Gumamit ng EMOTIONAL trigger: paghihirap, pagtatraydor, pag-asa, paghihiganti
- Gumamit ng "MULA SA ___ HANGGANG ___" o "___ → ___" na transition
- Maglagay ng curiosity gap — huwag isiwalat ang lahat
- Palaging may TUKOY na numero o halaga (₱1,000, 5 taon, 100 branches)

MGA HALIMBAWA (pattern — hindi kopyahin):
- "₱500 Lang ang Puhunan — Ngayon May 50 Branches Na! 😱 | CEO Stories PH"
- "Tinanggal sa Trabaho — Ngayon Mas Mayaman Pa sa Dating Boss! 💰 | CEO Stories"
- "Natulog sa Bangketa — Ngayon CEO na ng Sariling Kumpanya! 🏆 | Tagalog Success"

MGA PATAKARAN (HIGPIT NA SUNDIN):
- 55-85 characters TOTAL (kasama ang suffix)
- Tagalog (Filipino) — natural at casual
- ISANG emoji lamang (💼 💰 🔥 🏆 💪 📈 😱 💎 👑)
- Ang pera ay gamitan ng ₱ sign (₱1,000 — HINDI P1,000)
- BAWAL ang nakakulong na numero tulad ng "(25)" o "(10)"
- BAWAL ang doble o sobrang space
- TAMANG spelling at capitalization — i-UPPERCASE ang acronym (RTW, CEO, OFW, DH, IT) — HINDI "Rtw"
- IWASAN ang maling salita tulad ng "Ngayong" (gamitin: "Ngayon")
- BAWAL sabihing "hindi totoo" o "peke" ang kwento — TOTOONG kwento ito
- Tapusin sa "| CEO Stories PH" o "| Tagalog Success" o "| CEO Stories"
- I-OUTPUT LAMANG ANG TITLE — walang quotes, walang iba"""


_TITLE_RETRY_HINT = (
    "\n\nMAHIGPIT NA PAALALA: Hindi pasado ang naunang sagot. Siguraduhing: "
    "(1) may tiyak na numero o ₱ halaga, (2) may transition na \"Mula ... Hanggang\" o \"→\", "
    "(3) WALANG nakakulong na numero o doble space, (4) 55-85 characters kasama ang suffix."
)


def _clean_title(raw: str) -> str:
    """Normalize a raw LLM title into one clean single line."""
    if not raw:
        return ""
    t = raw.replace("```", " ").strip()
    t = t.split("\n")[0].strip()
    t = t.strip('"').strip("'").strip()
    t = re.sub(r"\s+", " ", t)                 # collapse whitespace
    t = re.sub(r"\bP(\d[\d,]*)", r"₱\1", t)    # P1,000 -> ₱1,000
    t = re.sub(r"\s*\|", " |", t)               # tidy pipe spacing
    return t.strip()


def _title_is_high_ctr(title: str) -> bool:
    """Heuristic gate that rejects weak or malformed titles."""
    t = (title or "").strip()
    if not (40 <= len(t) <= 95):
        return False
    if "(" in t or ")" in t:                     # stray "(25)" / "(10)"
        return False
    if "  " in t:                                 # double space
        return False
    if "|" not in t:                              # missing brand suffix
        return False
    low = t.lower()
    if any(bad in low for bad in ("di totoo", "hindi totoo", "peke")):
        return False
    has_number = any(c.isdigit() for c in t) or "₱" in t
    has_hook = ("→" in t) or ("mula" in low) or ("hanggang" in low)
    return has_number or has_hook


_DESC_PROMPT = """Gumawa ng YouTube description para sa video na ito.

TITLE: {title}
KWENTO: {seed}

MGA PATAKARAN:
- Magsimula sa isang compelling hook (1-2 pangungusap, may emoji)
- Maglagay ng "👇 MAG-COMMENT:" section na may 3 options
- Maglagay ng "⏱️ MGA KABANATA" na may 6 timestamps
- Maglagay ng subscribe/like/share CTA
- Tapusin sa 15-20 hashtags (Tagalog at English success tags)
- Tagalog ang pangunahing wika
- I-OUTPUT LAMANG ANG DESCRIPTION"""


_CTA_PROMPT = """Gumawa ng SHORT, HIGH-ENGAGEMENT CTA (call-to-action) para sa YouTube video na ito.

TITLE: {title}

Ang CTA ay dapat:
- 2-3 pangungusap lamang
- Magtanong sa manonood (para mag-comment sila)
- Mag-udyok na mag-subscribe at i-like
- Tagalog (Filipino), casual at emosyonal
- I-OUTPUT LAMANG ANG CTA — walang quotes"""


# ── OpenRouter helper ─────────────────────────────────────────────────────────

def _get_keys() -> list[str]:
    """Get all OpenRouter keys from env."""
    from config import get_openrouter_keys
    return get_openrouter_keys()


def _call_openrouter(prompt: str, system: str = None, max_tokens: int = 3000,
                     temperature: float = 0.9) -> str | None:
    """Call OpenRouter with key rotation. Returns content or None."""
    keys = _get_keys()
    if not keys:
        print("[content_gen] No OPENROUTER_API_KEY found")
        return None

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for key_idx, key in enumerate(keys):
        for attempt in range(3):
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://youtube.com/@CEOStoriesPH",
                        "X-Title": "CEO Stories Philippines",
                    },
                    json={
                        "model": MODEL,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=120,
                )
                if resp.status_code in (401, 402, 403):
                    print(f"[content_gen] key{key_idx+1} auth/credit error — next key")
                    break
                if resp.status_code == 429:
                    if attempt < 2:
                        print(f"[content_gen] key{key_idx+1} rate limited — waiting 15s")
                        time.sleep(15)
                        continue
                    break
                if resp.status_code != 200:
                    print(f"[content_gen] key{key_idx+1} error {resp.status_code}: {resp.text[:120]}")
                    break
                return resp.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"[content_gen] key{key_idx+1} exception: {e}")
                time.sleep(3)
                continue
    return None


# ── Random seed helper (avoids importing trending for isolation) ──────────────

def _random_seed() -> tuple[str, str]:
    """Return a random (category, seed) from topics.json."""
    topics_file = os.path.join(os.path.dirname(__file__), "topics.json")
    try:
        with open(topics_file, encoding="utf-8") as f:
            data = json.load(f).get("ceo_success_stories", {})
        if not data:
            raise ValueError("empty topics")
        category = random.choice(list(data.keys()))
        seed = random.choice(data[category])
        return category, seed
    except Exception as e:
        print(f"[content_gen] topics load error: {e}")
        return "rags_to_riches", "Mula sa pagtitinda ng kape hanggang sa pagmamay-ari ng coffee franchise empire"


# ── CSV helpers ───────────────────────────────────────────────────────────────

def _load_rows() -> list[dict]:
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write_rows(rows: list[dict]) -> None:
    with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        w.writeheader()
        w.writerows(rows)


def _next_id(rows: list[dict]) -> int:
    if not rows:
        return 1
    try:
        return max(int(r["id"]) for r in rows) + 1
    except Exception:
        return len(rows) + 1


# ── Package generation ────────────────────────────────────────────────────────

def generate_package(seed: str = None, category: str = None,
                     minutes: int = 10) -> dict | None:
    """Generate ONE complete content package (title, script, description, cta)."""
    if not seed:
        category, seed = _random_seed()
    if not category:
        category = "rags_to_riches"

    min_words = minutes * 130
    max_words = int(minutes * 160)

    label = seed[:60]

    # ── 1. Script (hook-first) ───────────────────────────────────────────────
    print(f"[content_gen]   Generating script for: {label}...")
    sys_prompt = _SYSTEM_PROMPT.replace("{min_words}", str(min_words)).replace("{max_words}", str(max_words))
    script = _call_openrouter(
        f'Sumulat ng buong script para sa kwentong ito:\n\n"{seed}"\n\n'
        f'Gawin itong HINDI MAPIGILAN ang panonood — simulan sa pinaka-malakas na hook.',
        system=sys_prompt, max_tokens=4000, temperature=0.9,
    )
    if not script or len(script.split()) < 200:
        print(f"[content_gen]   Script generation failed or too short")
        return None
    # Strip markdown artifacts
    script = script.replace("```", "").strip()
    if "[NARRATOR]" not in script and "[OP" not in script:
        print(f"[content_gen]   Script missing speaker tags")
        return None

    # ── 2. Title (validated high-CTR, retry if weak) ──────────────────────────
    print(f"[content_gen]   Generating title...")
    title = None
    for attempt in range(3):
        prompt = _TITLE_PROMPT.format(seed=seed)
        if attempt:
            prompt += _TITLE_RETRY_HINT
        cand = _clean_title(_call_openrouter(prompt, max_tokens=120, temperature=1.0) or "")
        if cand and _title_is_high_ctr(cand):
            title = cand
            break
        title = title or cand          # keep best effort as fallback
        time.sleep(1)
    if not title:
        return None

    # ── 3. Description ───────────────────────────────────────────────────────
    print(f"[content_gen]   Generating description...")
    description = _call_openrouter(
        _DESC_PROMPT.format(title=title, seed=seed),
        max_tokens=900, temperature=0.8,
    )
    if not description:
        description = _fallback_description(title, seed)
    description = description.replace("```", "").strip()

    # ── 4. CTA ───────────────────────────────────────────────────────────────
    print(f"[content_gen]   Generating CTA...")
    cta = _call_openrouter(
        _CTA_PROMPT.format(title=title),
        max_tokens=200, temperature=0.9,
    )
    if not cta:
        cta = "Kung na-inspire ka sa kwentong ito, mag-comment ng 💪 at mag-subscribe para sa bagong kwento ng tagumpay araw-araw!"
    cta = cta.replace("```", "").strip().strip('"').strip("'")

    return {
        "seed": seed,
        "category": category,
        "title": title,
        "script": script,
        "description": description,
        "cta": cta,
    }


def _fallback_description(title: str, seed: str) -> str:
    """Fallback description if LLM fails."""
    return (
        f"💼 {seed[:150]}\n\n"
        f"Mag-comment ng 💪 kung na-inspire ka, o 🔥 kung gusto mo ng ganitong kwento!\n\n"
        f"Maligayang pagdating sa CEO Stories Philippines — totoong kwento ng tagumpay ng mga Pilipino.\n\n"
        f"👇 MAG-COMMENT:\n💪 = Na-inspire ako\n🔥 = Gusto ko ng ganito araw-araw\n🙏 = May katulad akong kwento\n\n"
        f"⏱️ MGA KABANATA\n0:00 Ang Hook\n0:30 Ang Simula\n2:00 Ang Pagsubok\n3:30 Ang Pagbabago\n5:00 Ang Tagumpay\n6:30 Aral ng Kwento\n\n"
        f"🔔 Mag-subscribe at pindutin ang bel!\n👍 I-like kung nainspire ka\n📢 I-share sa mga kaibigan\n\n"
        f"#CEOStories #TagalogSuccess #PinoyCEO #RagsToRiches #OFWSuccess #PinoyEntrepreneur "
        f"#MulaSaWala #TagumpayNgPinoy #SuccessMindset #PinoyPride"
    )


# ── Batch generation ──────────────────────────────────────────────────────────

def generate_batch(count: int = 30, minutes: int = 10) -> int:
    """Generate `count` content packages and append to CSV. Returns count added."""
    rows = _load_rows()
    added = 0
    next_id = _next_id(rows)

    print(f"\n{'='*60}")
    print(f"  GENERATING {count} CONTENT PACKAGES (model: {MODEL})")
    print(f"  Existing rows: {len(rows)}")
    print(f"{'='*60}\n")

    for i in range(1, count + 1):
        print(f"\n[{i}/{count}] Generating package...")
        pkg = generate_package(minutes=minutes)
        if not pkg:
            print(f"[{i}/{count}] FAILED — skipping")
            continue
        rows.append({
            "id":         next_id,
            "seed":       pkg["seed"],
            "category":   pkg["category"],
            "title":      pkg["title"],
            "script":     pkg["script"],
            "description": pkg["description"],
            "cta":        pkg["cta"],
            "used":       "false",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        next_id += 1
        added += 1
        # Save after EACH package (resilient to crashes)
        _write_rows(rows)
        print(f"[{i}/{count}] SAVED: {pkg['title'][:60]}")
        # Small delay to avoid rate limits
        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"  DONE — added {added}/{count} packages")
    print(f"  Total rows in CSV: {len(rows)}")
    print(f"{'='*60}\n")
    return added


def csv_stats() -> dict:
    """Return stats about the CSV."""
    rows = _load_rows()
    used = sum(1 for r in rows if str(r.get("used", "")).lower() == "true")
    return {
        "total": len(rows),
        "used": used,
        "unused": len(rows) - used,
    }


def fix_titles() -> int:
    """Clean + re-generate any title that fails the high-CTR gate. Returns count fixed."""
    rows = _load_rows()
    if not rows:
        return 0
    fixed = 0
    for r in rows:
        cleaned = _clean_title(r.get("title", ""))
        if cleaned != r.get("title", ""):
            r["title"] = cleaned
        if _title_is_high_ctr(r["title"]):
            continue
        print(f"[fix] id={r['id']} WEAK: {r['title'][:70]}")
        new = None
        for attempt in range(3):
            prompt = _TITLE_PROMPT.format(seed=r.get("seed", ""))
            if attempt:
                prompt += _TITLE_RETRY_HINT
            cand = _clean_title(_call_openrouter(prompt, max_tokens=120, temperature=1.0) or "")
            if cand and _title_is_high_ctr(cand):
                new = cand
                break
        if new:
            r["title"] = new
            fixed += 1
            print(f"[fix] id={r['id']} NEW : {new}")
        else:
            print(f"[fix] id={r['id']} -- could not improve")
        time.sleep(1)
    _write_rows(rows)
    return fixed


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate high-CTR content bank (CSV)")
    parser.add_argument("--count",   type=int, default=30,   help="Number of packages to generate")
    parser.add_argument("--minutes", type=int, default=10,   help="Target script length in minutes")
    parser.add_argument("--stats",   action="store_true",    help="Show CSV stats only")
    parser.add_argument("--fix-titles", action="store_true", help="Re-generate weak (non-high-CTR) titles")
    args = parser.parse_args()

    if args.stats:
        s = csv_stats()
        print(f"Total:  {s['total']}")
        print(f"Used:   {s['used']}")
        print(f"Unused: {s['unused']}")
    elif args.fix_titles:
        n = fix_titles()
        print(f"Fixed {n} title(s)")
    else:
        generate_batch(count=args.count, minutes=args.minutes)
