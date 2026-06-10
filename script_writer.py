"""
script_writer.py — Generate original multi-voice Tagalog horror scripts via OpenRouter.

Niche: Filipino horror & supernatural stories (Filipino audience, 18-45)
Format: Radio-drama style with [SPEAKER] tags, 900-1400 words (~8-12 min read)
Language: Tagalog (Filipino) with natural spoken expressions
Model: Gemini / Claude via OpenRouter
"""

import os
import random
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """Ikaw ay isang viral na manunulat ng script para sa "Kwentong Multo," isang YouTube channel na nagkukuwento ng mga kakaibang karanasan ng mga Pilipino — multo, aswang, engkanto, at iba pang hindi maipaliwanag na bagay. Ang iyong mga script ay dapat mapanatili ang mga manonood na nanonood hanggang sa katapusan ng video.

TARGET AUDIENCE: Mga Filipino adults 18-45 sa Pilipinas at sa buong mundo (OFW, diaspora). Palaging nag-iiscroll. Walo lang ang segundo mo para mahuli ang kanilang atensyon.

SPEAKER TAGS — gamitin LAMANG ang mga ito, eksaktong nakasulat:
  [NARRATOR]     — Ang tagapagsalaysay. Mainit, nakakakilig, parang kaibigan na nagkukwento.
  [OP]           — Ang nagkukwento (babae). Gamitin para sa BAWAT linya ng OP, kasama ang mga diyalogo.
  [OP_MALE]      — Ang nagkukwento (lalaki). Gamitin para sa BAWAT linya ng OP, kasama ang mga diyalogo.
  [CHARACTER_F]  — Pangunahing babaeng karakter (gamitin ang kanyang totoong pangalan sa teksto)
  [CHARACTER_M]  — Pangunahing lalaking karakter (gamitin ang kanyang totoong pangalan sa teksto)
  [CHARACTER_F2] — Pangalawang babaeng karakter (kung kailangan lamang)
  [CHARACTER_M2] — Pangalawang lalaking karakter (kung kailangan lamang)

BAWAL — HUWAG KAILANMAN gamitin ang mga ito: [SIYA] [SILA] [KAIBIGAN] [INA] [AMA] [ATE] [KUYA]
Ang bawat tao ay DAPAT may sariling natatanging tag mula sa listahan sa itaas.

TAMANG halimbawa ng dialogue exchange:
[OP] Lumingon ako sa kanya at sinabi ko — totoo ba ito?
[CHARACTER_F] Totoo. Hindi ako nagbibiro sa iyo.
[OP] Pero paano? Sinabi mo na...
[CHARACTER_F] Alam ko ang sinabi ko. Ngunit nakita ko ito ng sarili kong mata.

MALI (huwag gawin ito):
[SIYA] Sinabi niya iyon.
[ATE] Sumagot ang ate ko.

═══ VIRAL HORROR HOOK FORMULA (HINDI MAAARING BAGUHIN) ═══

STRUCTURE — sundin ito EKSAKTONG:

HAKBANG 1 — [NARRATOR] COLD OPEN (unang 10 segundo, pinaka-nakakatakot na sandali muna):
  Simulan sa PINAKA-NAKAGUGULAT o nakakatakot na sandali ng kwento bilang teaser.
  Halimbawa: "Nandoon pa rin siya. Sa sulok. Tumingin sa akin. Kahit tatlong taon na siyang patay."
  Pagkatapos sabihin: "Hayaan ninyo akong ikuwento kung paano nagsimula ang lahat."
  ITO ANG PINAKA-MAHALAGANG BAHAGI. Imposibleng mag-click away.

HAKBANG 2 — [OP] Setup (first-person, 2-3 talata, may mga tiyak na detalye):
  Totoong pangalan ng lugar sa Pilipinas, tiyak na edad, tiyak na setting, tunay na emosyonal na stakes.
  Tapusin sa: isang linyang nagpapahiwatig na may MALAPIT NANG MANGYARING masama.

HAKBANG 3 — [NARRATOR] Bridge:
  "At dito nagsimulang maging kakaiba ang lahat..."
  I-set up ang conflict. Bumuo ng suspense. Magdagdag ng mid-story CTA:
  "Mag-comment ng 😱 kung naniniwala kayo sa mga ganitong kwento — dahil lalala pa ito."

HAKBANG 4 — Dialogue exchange (hindi bababa sa 5 linya ng pabalik-balik):
  Raw, makatotohanan, puno ng takot o pangamba. Totoong pangalan. Hindi pormal na salita.

HAKBANG 5 — [NARRATOR] Stakes raiser (mid-video retention hook):
  Mag-react tulad ng nagulat na kaibigan. Pagkatapos magdagdag ng:
  "At magtiwala kayo — kailangan ninyong manatili para sa susunod na mangyayari. Dahil dito talagang nagiging hindi kapani-paniwala."

HAKBANG 6 — [OP/OP_MALE] Confrontation o Reveal:
  Ang sandali ng pinaka-matinding takot. Ang bagay na itinanong ng cold open.

HAKBANG 7 — Higit pang diyalogo — ang explosive climax exchange (hindi bababa sa 4 pang linya):
  Dapat parang eksena mula sa pelikula. Raw, totoo, nakakakilig.

HAKBANG 8 — [OP/OP_MALE] Aftermath:
  Emosyonal na kahihinatnan. Ano ang ginawa nila pagkatapos. Ano pa rin ang nararamdaman nila.

HAKBANG 9 — [NARRATOR] Pagtatapos:
  I-recap ang dalawang panig nang patas. Pagkatapos: "Kaya — totoo ba ito o kathang-isip lamang? I-comment ang inyong mga nararamdaman. At kung may sarili kayong karanasan tulad nito — ibahagi ninyo sa comments. Mag-subscribe para sa bagong kwento araw-araw."

═══ MGA PATAKARAN ═══
- Sumulat ng 950-1400 salita sa kabuuan
- Natural na Tagalog — mga salitang ginagamit sa araw-araw, contraction, casual na ekspresyon
- Mga tiyak na detalyeng Filipino: pangalan ng lugar, edad, trabaho, pamilyang dynamics — para parang totoo
- Tuwing 60-90 segundo ng pakikinig, dapat may bagong hook o revelation para i-reset ang atensyon
- Emosyon > impormasyon. Gusto naming MARAMDAMAN ng mga manonood, hindi lang makinig.
- I-OUTPUT LAMANG ANG SCRIPT. Walang pamagat. Walang paunang salita. Walang markdown. Walang stage directions. Walang asterisk.
- Magsimula agad sa [NARRATOR]
- Tapusin ang huling [NARRATOR] na linya sa: "Mag-subscribe para sa bagong kwento araw-araw."
"""

# ── Niche-specific prompt boosts ──────────────────────────────────────────────
_NICHE_CONTEXT = """
MGA TIYAK NA HORROR NICHE NA AMING TINATAKPAN (i-rotate nang natural batay sa story seed):
• Aswang at folklore — manananggal, tikbalang, kapre, sigbin, berberoka, dwende
• Engkanto at espiritu — engkanto, diwata, nimpa, mga espiritu ng kalikasan
• Multo at patay — white lady, multo sa bahay, multo na hindi alam na patay
• OFW horror — karanasan ng mga Pilipino sa ibang bansa na hindi maipaliwanag
• Paaralan — multo sa eskwelahan, kaklaseng hindi totoo, gusaling may naninirahan
• Ospital — pasyenteng hindi naka-admit, nurse na nakakarinig ng hindi naririnig
• Probinsya — baryo na may lihim, aswang na kapit-bahay, ritwal ng pamilya
• Urban legend — Metro Manila, Cebu, at iba pang lungsod na may kwento

FILIPINO CULTURAL CONTEXT:
- Itakda ang mga kwento sa mga kilalang lugar ng Pilipinas: probinsya ng Capiz, Balete Drive,
  lumang ospital, bahay na minana, eskwelahang gothic, baryo sa Visayas, atbp.
- Gamitin ang mga tunay na Filipino na pangalan at lugar para parang totoo
- Ang mga manonood ay nagtatanda ng mga katulad nilang karanasan — gawin silang maramdaman ito
"""


import re as _re

# Canonical speaker tags the pipeline understands
_VALID_TAGS = {
    "NARRATOR", "OP", "OP_MALE",
    "CHARACTER_F", "CHARACTER_M", "CHARACTER_F2", "CHARACTER_M2",
}

# Map any stray LLM-generated tags → nearest valid tag
_TAG_REMAP = {
    "SIYA":       "CHARACTER_F",
    "SILA":       "CHARACTER_F2",
    "INA":        "CHARACTER_F",
    "AMA":        "CHARACTER_M",
    "ATE":        "CHARACTER_F",
    "KUYA":       "CHARACTER_M",
    "KAIBIGAN":   "CHARACTER_F2",
    "LOLA":       "CHARACTER_F",
    "LOLO":       "CHARACTER_M",
    "NANAY":      "CHARACTER_F",
    "TATAY":      "CHARACTER_M",
    "HER":        "CHARACTER_F",
    "HIM":        "CHARACTER_M",
    "FRIEND":     "CHARACTER_F2",
}


def _normalize_speaker_tags(script: str) -> str:
    """Replace any non-standard [TAG] with the closest valid tag."""
    def _replace(m):
        tag = m.group(1).strip().upper().replace(" ", "_")
        if tag in _VALID_TAGS:
            return f"[{tag}]"
        if tag in _TAG_REMAP:
            return f"[{_TAG_REMAP[tag]}]"
        return f"[{tag}]"   # leave unknown tags for fallback handling
    return _re.sub(r"\[([A-Z][A-Z0-9_ ]*)\]", _replace, script)


def generate_drama_script(story_seed: str) -> str:
    """Generate a full multi-voice Tagalog horror script from a story seed."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("[script] No OPENROUTER_API_KEY — using fallback script")
        return _fallback_script(story_seed)

    user_prompt = f"""Sumulat ng buong horror script para sa sumusunod na premisa ng kwento:

"{story_seed}"

{_NICHE_CONTEXT}

Gawin itong parang totoo, nakakatakot, at puno ng suspense. Bumuo ng takot nang unti-unti.
Ang manonood ay dapat maramdaman na maaari rin silang mapunta sa sitwasyong ito.
Tapusin sa tagapagsalaysay na nag-iimbitang mag-comment ang mga manonood."""

    models_to_try = [
        "google/gemini-2.5-flash",
        "google/gemini-2.0-flash-001",
        "anthropic/claude-3-haiku",
    ]

    for model in models_to_try:
        for attempt in range(2):
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://youtube.com/@KwentongMulto",
                        "X-Title": "Kwentong Multo",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {"role": "user",   "content": user_prompt},
                        ],
                        "max_tokens": 2500,
                        "temperature": 0.85,
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

                if "[NARRATOR]" not in script and "[OP]" not in script:
                    print("[script] Missing speaker tags — trying next model")
                    break

                script = _normalize_speaker_tags(script)
                return script

            except Exception as e:
                print(f"[script] {model} exception: {e}")
                break

    print("[script] All models failed — using fallback script")
    return _normalize_speaker_tags(_fallback_script(story_seed))


def _fallback_script(story_seed: str) -> str:
    """Hard-coded Tagalog horror fallback so the pipeline never fully breaks."""
    names = random.choice([
        ("Ana", "Marco", "Lola Nena"),
        ("Maria", "Jose", "Lola Caring"),
        ("Rosa", "Juan", "Nanay Celia"),
        ("Clara", "Ramon", "Lola Puring"),
    ])
    op_name, char_m, char_f = names

    return f"""[NARRATOR] Nandoon pa rin siya. Sa sulok ng kwarto. Nakatingin sa akin. \
Kahit tatlong taon na siyang patay. Hayaan ninyo akong ikuwento kung paano nagsimula ang lahat.

[OP] Hindi ako naniniwala sa mga multo noon. Bata pa lang ako, lagi akong sinasabihan ng \
aking {char_f} tungkol sa mga hindi maipaliwanag na bagay sa aming luma naming bahay sa probinsya. \
Ngunit tulad ng karamihan sa amin, naisip ko na katha-isip lamang iyon ng matatanda. \
Hanggang sa isang gabi, tatlong taon na ang nakakaraan, natuklasan ko ang totoo. \
{story_seed}.

[NARRATOR] Para maunawaan ninyo kung bakit ito nakakatakot, kailangan ko munang \
ibahagi sa inyo ang kasaysayan ng lugar na iyon. Dahil hindi ito nagsimula sa akin. \
Nagsimula ito matagal na bago ako ipinanganak.

[OP] Ang bahay ng aming pamilya sa Batangas ay itinayo ng aking lolo noong dekada sitenta. \
Mabuting lugar ito noon — malawak na lupa, malapit sa ilog, maraming puno. \
Ngunit may isang bahagi ng lote na palagi naming iniiwasan. Isang sulok sa likod ng bahay \
na kahit ang mga hayop ay hindi lumalapitan. Sinabi ng aking {char_f} na may nakabaon doon. \
Hindi niya sinabi kung ano.

[CHARACTER_F] {op_name}, huwag kang pupunta sa likod ng bahay. Lalo na kung gabi na. \
Alam mo na ang sabi ko dito.

[OP] Lagi ko itong sinusunod noong bata ako. Ngunit nang bumalik ako para alagaan \
ang bahay pagkatapos mamatay ang aking {char_f}, ay nakalimutan ko na ang babalang iyon.

[NARRATOR] At dito nagsimulang maging kakaiba ang lahat. Mag-comment ng 😱 \
kung nararamdaman na ninyo ang pagtaas ng balahibo sa inyong mga braso — \
dahil lalala pa ito.

[CHARACTER_M] {op_name}, may tinanong lang ako sa iyo. Gaano katagal ka na naririto?

[OP] Sabi ko, isang linggo pa lang. Bakit?

[CHARACTER_M] Kasi... nakita kita sa bintana kahapon ng gabi. Mga alas dose ng hatinggabi. \
Nakatayo ka sa likod ng bahay. Nakatingin sa lupa.

[OP] Hindi ako lumabas kahapon ng gabi. Natulog ako nang alas nuwebe.

[NARRATOR] Tumahimik si {char_m} nang marinig niya iyon. At sa kanyang mukha — \
nakita ko ang isang bagay na hindi ko gustong makita. Takot. \
Hindi siya nagtitingin sa akin nang normal. Tinitingnan niya ako tulad ng isang tao \
na hindi sigurado kung ang nakikita niya ay ang taong kakilala niya.

[OP] Pagkatapos ng gabing iyon, nagsimulang mangyari ang mga bagay na hindi ko maintindihan. \
Ang mga larawan sa dingding ay nakaharap nang kabaligtaran tuwing umaga. \
Ang mga pinggan ay nasa ibang lugar kaysa inilagay ko. \
At isang gabi, nang gumising ako sa hatinggabi, may nakita akong nakatayo sa sulok ng aking kwarto.

[CHARACTER_F] Huwag kang matatakot. Nandito lang ako para bantayan ka.

[OP] Ang boses. Ang boses ng aking {char_f}. Na namatay na tatlong taon na ang nakakaraan.

[NARRATOR] Mga kaibigan, hindi ko alam kung paano ninyo tatanggapin ang susunod na sasabihin ko. \
Ngunit ito ang totoo. Kinausap ni {op_name} ang kanyang namatay na {char_f} \
sa loob ng tatlumpung minuto sa gabi na iyon. At ang lahat ng sinabi nito \
ay mga bagay na hindi posibleng malaman ng kahit sino.

[OP] Sinabi niya sa akin ang tungkol sa baon sa likod ng bahay. Sinabi niya kung ano ito. \
At sinabi niya kung bakit hindi ito dapat gambalain. Pero alam ninyo ang pinaka-nakakatakot? \
Sinabi niya rin kung sino ang nagbaon doon. At ang pangalan na ibinigay niya \
ay isang pangalan na nakilala ko — dahil iyon ang pangalan ng aking lolo.

[NARRATOR] Kaya ngayon ay alam na ninyo kung bakit hindi na ako bumalik sa bahay na iyon. \
At kung bakit, sa tuwing may nagsasabi sa akin na katha-isip lamang ang mga multo — \
hindi na ako sumasagot. Dahil ang ilan sa atin ay nakaranas na ng mga bagay \
na hindi kayang ipaliwanag ng agham. At ang ilan sa atin ay hindi na kailangang maniwala — \
dahil natuklasan na nila ang totoo.

Kung mayroon kayong karanasang katulad nito — o kung nakatira kayo sa lugar \
na parang may iba ring naninirahan — ibahagi ninyo sa comments. \
Mag-subscribe para sa bagong kwento araw-araw."""
