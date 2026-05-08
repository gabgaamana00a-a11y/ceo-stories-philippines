"""
script_writer.py — Generate original multi-voice drama scripts via OpenRouter.

Niche: AITA / Reddit relationship drama (US audience, 18-45)
Format: Radio-drama style with [SPEAKER] tags, 700-1200 words (~5-9 min read)
Model: Claude 3.5 Sonnet via OpenRouter (best creative writing quality)
"""

import os
import random
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a professional drama script writer for "Drama Desk," a YouTube channel covering real-life American drama stories in the style of Reddit's r/AmItheAsshole and r/relationship_advice.

TARGET AUDIENCE: US adults 18-45 who love drama, storytelling, and relationship advice content.

SPEAKER TAGS — use ONLY these, exactly as written:
  [NARRATOR]     — The host. Warm, conversational, sets scenes, adds commentary.
  [OP]           — The original poster (use for female OP stories)
  [OP_MALE]      — Use instead of [OP] when the poster is male
  [CHARACTER_F]  — Primary female character (give her a real American name in dialogue)
  [CHARACTER_M]  — Primary male character (give him a real American name in dialogue)
  [CHARACTER_F2] — Secondary female character (only if needed)
  [CHARACTER_M2] — Secondary male character (only if needed)

SCRIPT STRUCTURE:
1. [NARRATOR] hook — grab attention in the first 15 seconds. Tease the drama.
2. [OP] or [OP_MALE] — sets up the situation in first-person (2-3 paragraphs)
3. Scene-setting [NARRATOR] bridge — "But here's where things get messy..."
4. Dialogue exchange — at least 4 back-and-forth lines between characters
5. [NARRATOR] — raise the stakes, add reaction/commentary
6. [OP/OP_MALE] — the confrontation or reveal moment
7. More dialogue — the climax exchange
8. [OP/OP_MALE] — aftermath and emotional reaction
9. [NARRATOR] closing — asks viewers for their verdict

RULES:
- Write 750-1100 words total in the script body
- Use natural spoken American English — contractions, casual phrasing
- Give characters specific American first names (e.g. Jake, Sarah, Mike, Ashley)
- Include specific realistic details (ages, locations, relationships) to feel authentic
- Build genuine tension — the audience should feel the emotion
- ONLY output the script. No title. No preamble. No markdown. No stage directions.
- Start immediately with [NARRATOR]
- End the last line with: "Drop a comment — who do YOU think is in the wrong here?"
"""

# ── Niche-specific prompt boosts ──────────────────────────────────────────────
_NICHE_CONTEXT = """
SPECIFIC DRAMA NICHES WE COVER (rotate naturally based on the story seed):
• AITA stories — "Am I wrong for..." dilemmas with clear moral conflict
• Relationship betrayal — cheating, lying, hidden secrets between partners
• Family drama — in-law conflicts, sibling rivalry, inheritance disputes, estrangement
• Entitled people — Karen moments, demanding relatives, boundary violations
• Workplace drama — toxic bosses, credit theft, HR incidents, office politics
• Friendship betrayal — best friends crossing lines, loyalty tested

US CULTURAL CONTEXT:
- Set stories in recognizable American settings: suburban homes, restaurants,
  offices, family holiday dinners, wedding venues, airports, etc.
- Reference realistic American salaries, family dynamics, and social situations
- The audience identifies with the OP — make them sympathetic but not perfect
"""


def generate_drama_script(story_seed: str) -> str:
    """Generate a full multi-voice drama script from a story seed."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("[script] No OPENROUTER_API_KEY — using fallback script")
        return _fallback_script(story_seed)

    user_prompt = f"""Write a full drama script for the following story premise:

"{story_seed}"

{_NICHE_CONTEXT}

Make it feel raw, real, and emotionally charged. Build to a dramatic confrontation or reveal.
The audience should feel torn — there should be genuine moral complexity.
End with the narrator asking viewers to comment their verdict."""

    models_to_try = [
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-haiku",
        "google/gemini-2.0-flash-001",
    ]

    for model in models_to_try:
        for attempt in range(2):
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://youtube.com/@DramaDeskChannel",
                        "X-Title": "Drama Desk",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {"role": "user",   "content": user_prompt},
                        ],
                        "max_tokens": 2200,
                        "temperature": 0.82,
                    },
                    timeout=90,
                )

                if resp.status_code == 429:
                    if attempt == 0:
                        print(f"[script] Rate limited on {model}, retrying in 20s...")
                        time.sleep(20)
                        continue
                    print(f"[script] Rate limited — trying next model")
                    break

                if resp.status_code != 200:
                    print(f"[script] {model} error {resp.status_code}: {resp.text[:120]}")
                    break

                script = resp.json()["choices"][0]["message"]["content"].strip()
                word_count = len(script.split())
                print(f"[script] Generated via {model}: {word_count} words")

                if word_count < 350:
                    print("[script] Too short — trying next model")
                    break

                # Sanity check: must have at least one speaker tag
                if "[NARRATOR]" not in script and "[OP]" not in script:
                    print("[script] Missing speaker tags — trying next model")
                    break

                return script

            except Exception as e:
                print(f"[script] {model} exception: {e}")
                break

    print("[script] All models failed — using fallback script")
    return _fallback_script(story_seed)


def _fallback_script(story_seed: str) -> str:
    """Hard-coded fallback so the pipeline never fully breaks."""
    names = random.choice([
        ("Sarah", "Jake", "Linda"),
        ("Ashley", "Ryan", "Karen"),
        ("Megan", "Chris", "Diane"),
        ("Jessica", "Matt", "Brenda"),
    ])
    op_name, char_m, char_f = names

    return f"""[NARRATOR] Welcome back to Drama Desk — the channel where real life gets messy. \
Today's story is one that has us absolutely floored, and by the end of this video, \
I guarantee you will have a very strong opinion. If you are new here, subscribe right now \
because we drop a fresh drama story every single day.

[OP] Okay, so I really need an outside perspective on this because my entire family is divided, \
and honestly I am starting to question everything. I am a thirty-one-year-old woman living in \
suburban Ohio, and I have been with my partner {char_m} for four years. \
Here is the situation: {story_seed}.

[NARRATOR] Now before you jump to conclusions, let me give you the full context. \
Because this story has layers, and the more you hear, the more complicated it gets.

[OP] So it started about three weeks ago. Everything seemed completely normal on the surface. \
{char_m} and I had just gotten back from a weekend trip to visit his family. \
His mom {char_f} was perfectly pleasant the whole time — or so I thought.

[CHARACTER_F] Oh sweetheart, I just think you should know something. I've been meaning to say this \
for a while now and I think it's important.

[OP] And that is when she dropped it. Right there at the kitchen table, in front of {char_m} \
and his entire family. My jaw just hit the floor.

[CHARACTER_M] Mom — this is not the time for this. Can we please not do this right now?

[CHARACTER_F] No, she deserves to know. If you will not tell her then I will.

[OP] I looked at {char_m} and I could see it on his face immediately. He knew exactly what \
she was about to say. And in that moment I felt this sick feeling in my stomach, \
like everything I thought I knew was about to collapse.

[NARRATOR] And here is where it gets really messy, folks. Because what came out next was not \
just a surprise — it was a complete rewriting of everything {op_name} had been told.

[CHARACTER_F] He was engaged before you. For two years. And he broke it off in the worst possible way.

[OP] I could not even speak. I just sat there completely frozen while {char_m} started trying to explain.

[CHARACTER_M] It was years ago. It has nothing to do with us. I was going to tell you, I just — \
I did not know how, and then time passed and it felt like it was too late.

[OP] Too late? We have been together for four years. We have talked about marriage. \
And you did not think that was relevant information?

[CHARACTER_F] I am sorry for how this came out, I truly am. But someone had to say something.

[NARRATOR] So now {op_name} is left trying to figure out whether this is a dealbreaker \
or whether it is something she can move past. Her friends are split right down the middle. \
Half of them say {char_m} had every right to keep his past private. \
The other half say four years in, she deserved to know this from him — not from his mother.

[OP] I do not even know what I am most upset about. Is it the secret itself? \
Or is it the fact that his mother knew this whole time and was just sitting on it? \
And why now? Why at a family dinner with everyone watching?

[NARRATOR] Alright Drama Desk community — I want to hear from you right now. \
Was {char_m} wrong for never telling her? Was his mom completely out of line \
for bringing it up like that? And most importantly — what would YOU do in this situation? \
Drop a comment — who do YOU think is in the wrong here?"""
