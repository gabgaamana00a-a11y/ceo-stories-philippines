"""
story_engine.py — Free procedural CEO revenge story generator.

NO API calls. NO OpenRouter. NO costs.
Generates 20-60 minute Tagalog CEO revenge/rags-to-riches stories
using pre-written templates, character pools, and scene composition.

Output format: [SPEAKER] tagged script (compatible with tts_engine.py)
"""

import random
import textwrap

# ── Character name pools ──────────────────────────────────────────────────────

MALE_NAMES = [
    ("Juan", "dela Cruz"), ("Carlos", "Santos"), ("Miguel", "Reyes"),
    ("Jose", "Gonzales"), ("Antonio", "Villanueva"), ("Ramon", "Dimagiba"),
    ("Eduardo", "Marcos"), ("Fernando", "Lopez"), ("Manuel", "Aquino"),
    ("Pedro", "Mendoza"), ("Rico", "Fernandez"), ("Dante", "Navarro"),
    ("Luis", "Ramirez"), ("Rafael", "Castillo"), ("Mario", "Torres"),
]

FEMALE_NAMES = [
    ("Maria", "Santos"), ("Ana", "dela Cruz"), ("Rosa", "Mendoza"),
    ("Clara", "Villanueva"), ("Luz", "Fernandez"), ("Elena", "Ramirez"),
    ("Celia", "Gonzales"), ("Nena", "Lopez"), ("Teresa", "Aquino"),
    ("Lorna", "Castillo"), ("Fe", "Navarro"), ("Gloria", "Reyes"),
    ("Rita", "Dimagiba"), ("Lilia", "Torres"), ("Sonia", "Marcos"),
]

FAMILY_NAMES = ["Ina", "Nanay", "Tatay", "Ama", "Lola", "Lolo", "Tiya", "Tiyo"]

# ── Location pools ────────────────────────────────────────────────────────────

LOCATIONS_POOR = [
    "Tondo, Maynila", "isang estero sa Manila", "isang baryo sa Batangas",
    "isang maliit na isla sa Visayas", "isang probinsya sa Quezon",
    "isang fishing village sa Samar", "isang bundok sa Benguet",
    "isang squatter area sa Pasay", "isang liblib na baryo sa Leyte",
    "isang palayan sa Nueva Ecija", "isang maliit na bayan sa Bicol",
    "isang compound sa Navotas",
]

LOCATIONS_BUSINESS = [
    "sa isang corporate office sa Makati", "sa BGC, Taguig",
    "sa isang business district sa Ortigas", "sa isang mall sa Quezon City",
    "sa isang manufacturing plant sa Laguna", "isang restaurant sa Maynila",
    "sa financial district ng Singapore", "isang tech hub sa California",
]

# ── Betrayal scenarios ────────────────────────────────────────────────────────

BETRAYALS = [
    {
        "title": "stolen_idea",
        "setup": "ninakaw ng kanyang kasamahan sa trabaho ang kanyang original na idea at inangkin bilang sarili nito",
        "perpetrator": "ang kanyang pinagkakatiwalaang kasamahan at kaibigan",
        "detail": "Ipinakita niya ang kanyang plano sa kanyang kasamahan isang gabi pagkatapos ng trabaho. Makalipas ang isang linggo, sa harap ng kanilang mga boss, iniharap ng kasamahan ang idea bilang sarili niya at nakatanggap ng promotion at bonus.",
        "aftermath_emotion": "parang binuhusan siya ng malamig na tubig. Hindi siya makapaniwala. Ang taong pinagkatiwalaan niya ang siyang sumaksak sa kanya.",
    },
    {
        "title": "fired_unfairly",
        "setup": "tinanggal sa trabaho nang walang katarungan ng kanyang mapagmataas na boss",
        "perpetrator": "ang kanyang brutal at mapagmataas na boss",
        "detail": "Sa loob ng limang taon, siya ang pinakamasipag na empleyado. Hinding-hindi siya nahuli, walang absent, at laging lampas sa quota. Ngunit isang araw, tinawag siya ng boss sa opisina at sinabing wala na siyang trabaho — pinalitan siya ng pamangkin ng boss.",
        "aftermath_emotion": "Nawalan siya ng lakas ng loob. Paano niya sasabihin sa kanyang pamilya na wala na siyang trabaho?",
    },
    {
        "title": "cheated_partner",
        "setup": "niloko ng kanyang business partner at iniwan na walang wala",
        "perpetrator": "ang kanyang pinagkakatiwalaang business partner",
        "detail": "Sama-sama silang nagtayo ng negosyo mula sa wala. Limang taon nilang pinaghirapan ang kompanya. Ngunit isang araw, nawala ang partner dala ang lahat ng pera ng kompanya. Iniwan siyang may malaking utang sa bangko at sa mga suppliers.",
        "aftermath_emotion": "Para siyang sinuntok sa sikmura. Hindi lang siya nawalan ng negosyo — nawalan din siya ng tiwala sa sangkatauhan.",
    },
    {
        "title": "humiliated_public",
        "setup": "pinahiya sa harap ng maraming tao ng isang taong mayayabang",
        "perpetrator": "isang mayabang na kakilala na laging minamaliit siya",
        "detail": "Sa isang corporate event, sa harap ng daan-daang tao, pinahiya siya ng isang kakilala. Pinagtawanan ang kanyang pinanggalingan, ang kanyang damit, ang kanyang trabaho. Lahat ay nakatitig sa kanya. Ramdam niya ang init sa kanyang mukha.",
        "aftermath_emotion": "Sobrang hiya ang kanyang naramdaman. Gusto niyang lumubog sa lupa. Pero sa ilalim ng hiya na iyon, may apoy na nag-aapoy — isang determinasyon na patunayan na mali ang taong iyon.",
    },
    {
        "title": "family_disowned",
        "setup": "itinakwil ng kanyang mayamang pamilya dahil pinili niya ang kanyang pangarap",
        "perpetrator": "ang kanyang sariling mayamang pamilya",
        "detail": "Galing siya sa isang mayamang pamilya na may sariling negosyo. Ngunit hindi niya gusto ang landas na inihanda para sa kanya — magmana at magpatakbo ng negosyo ng pamilya. Gusto niyang magtayo ng sariling kompanya. Pinalayas siya ng kanyang ama at sinabing huwag nang bumalik.",
        "aftermath_emotion": "Masmadama pa ang sakit ng pagtatakwil kaysa sa kahirapan. Ang sariling pamilya mo — ang dapat na sumusuporta sa iyo — ay tatalikod sa iyo.",
    },
    {
        "title": "ex_left_for_rich",
        "setup": "iniwan ng kasintahan para sa mas mayamang tao",
        "perpetrator": "ang kanyang dating kasintahan na pumili ng pera kaysa pag-ibig",
        "detail": "Siyam na taon sila ng kanyang kasintahan. Magkasama silang nagplano ng kanilang kinabukasan. Ngunit isang araw, nakilala ng kanyang kasintahan ang isang mayamang negosyante. Iniwan siya nito na may mensahe: 'Pasensya na, pero gusto ko ng magandang buhay. Hindi sapat ang pagmamahal para mabuhay.'",
        "aftermath_emotion": "Nasira ang kanyang puso. Siyam na taon — nawala lahat sa isang iglap. Pero sa sakit na iyon, natuto siyang huwag umasa sa iba. Ang tunay na seguridad ay nagmumula sa sarili.",
    },
    {
        "title": "scammed_by_friend",
        "setup": "na-scam ng pinakamatalik na kaibigan at nawalan ng lahat ng ipon",
        "perpetrator": "ang kanyang pinakamatalik na kaibigan mula pagkabata",
        "detail": "Pinagkatiwalaan niya ang kanyang matalik na kaibigan. Sama-sama silang lumaki sa hirap. Nang magkaroon siya ng pera, inalok siya ng kaibigan ng isang 'magandang investment' — isang negosyo raw na tiyak na kikita. Lahat ng kanyang pinaghirapang pera — sampung taon ng pag-iipon — ay nawala. Scam pala ito.",
        "aftermath_emotion": "Hindi pera ang nawala sa kanya — nawala ang kanyang paniniwala na may totoo pang pagkakaibigan. Kung ang matalik mong kaibigan ay kaya kang lokohin, sino pa ang mapagkakatiwalaan mo?",
    },
]

# ── Industry paths to success ─────────────────────────────────────────────────

INDUSTRIES = [
    {
        "name": "tech_startup",
        "business": "tech startup",
        "role": "software development",
        "company": "tech company",
        "journey": "Natuto siyang mag-code gamit ang computer shop. Gabi-gabi, mag-isa siyang nag-aaral ng programming. Nag-freelance siya online, kumikita ng kaunti, hanggang sa nakaipon siya para magtayo ng sariling software company.",
        "success_detail": "Ang kanyang tech company ay lumago. Mula sa isang tao sa isang maliit na apartment, naging 200 empleyado sa isang building sa BGC. Ang kanyang software ay ginagamit na ng mga malalaking korporasyon.",
    },
    {
        "name": "food_business",
        "business": "restaurant chain",
        "role": "chef at restaurateur",
        "company": "restaurant group",
        "journey": "Nag-aral siyang magluto sa kanyang ina. Nagsimula siya sa pagtitinda ng pagkain sa bangketa. Paunti-unti, nakapag-ipon siya para magrenta ng maliit na kwarto at gawing karinderya. Ang kanyang luto ay naging tanyag sa buong lugar.",
        "success_detail": "Mula sa isang karinderya, nagkaroon siya ng sampung branches ng restaurant. Ang kanyang restaurant group ay kabilang na sa Top 100 sa bansa at nag-e-employ ng 500 katao.",
    },
    {
        "name": "real_estate",
        "business": "real estate development",
        "role": "real estate developer",
        "company": "real estate firm",
        "journey": "Nagsimula siya bilang helper sa construction. Pinagmasdan niya ang bawat proseso — paano magbenta, paano mag-negotiate, paano magpatayo ng gusali. Nag-ipon siya ng kaunti-kaunti at bumili ng unang lupa.",
        "success_detail": "Ang kanyang real estate company ay nag-develop na ng 20 subdivisions at 5 condominium projects. Mula sa helper, siya na ngayon ang isa sa pinakamalaking developer sa probinsya.",
    },
    {
        "name": "manufacturing",
        "business": "manufacturing",
        "role": "factory owner",
        "company": "manufacturing corporation",
        "journey": "Trabahador siya sa isang pabrika. Pinag-aralan niya ang buong operasyon — mula sa raw materials hanggang sa finished product. Nag-ipon siya at nagtayo ng sariling maliit na pabrika sa kanilang likod-bahay.",
        "success_detail": "Ang kanyang manufacturing company ay nag-e-export na ng mga produkto sa US, Europe, at Japan. Tatlong pabrika ang pagmamay-ari niya at halos 1,000 ang kanyang empleyado.",
    },
    {
        "name": "franchise_empire",
        "business": "franchise business",
        "role": "entrepreneur",
        "company": "franchise corporation",
        "journey": "Nagsimula siya sa maliit — isang food cart, isang water station, isang maliit na tindahan. Hindi siya nagsawa sa pag-aaral ng negosyo. Pinag-aralan niya ang sistema ng franchise at ginaya ito nang perpekto.",
        "success_detail": "Mula sa isang cart, mayroon na siyang 200 franchise outlets sa buong bansa. Ang kanyang franchise corporation ay isa sa pinakamabilis lumago sa Pilipinas.",
    },
    {
        "name": "logistics",
        "business": "logistics and transport",
        "role": "transport magnate",
        "company": "logistics company",
        "journey": "Driver siya ng tricycle sa kanilang baryo. Pagkatapos ay naging driver ng jeepney. Nang makaipon, bumili siya ng kanyang sariling jeepney. Pinaupahan niya ito at ginamit ang kita para bumili ng pangalawa, pangatlo.",
        "success_detail": "Ang kanyang logistics company ay may 200 trucks na naghahatid ng produkto sa buong Luzon. Mula sa tricycle driver, siya na ngayon ang kinikilalang transport magnate sa kanilang rehiyon.",
    },
]

# ── Dialogue snippets ─────────────────────────────────────────────────────────

DIALOGUE_BETRAYAL = [
    ("BETRAYER", "Alam mo, matagal ko nang gustong sabihin ito sa iyo. Hindi ako naniniwala na kaya mong gawin ang project na ito. Kaya kinuha ko na ang credit."),
    ("OP", "Bakit? Magkasama tayo mula pa noong una. Pinagkatiwalaan kita."),
    ("BETRAYER", "Wala sa mundo ng negosyo ang pagkakaibigan. Tandaan mo iyan."),
]

DIALOGUE_CONFRONTATION = [
    ("BETRAYER", "Ikaw? Ano ang ginagawa mo rito? Paano ka nakapasok sa building na ito?"),
    ("OP", "Ako na ngayon ang bagong may-ari ng building na ito. At ng kompanyang 'to."),
    ("BETRAYER", "Imposible. Saan mo nakuha ang pera?"),
    ("OP", "Hindi pera ang nagtulak sa akin. Ang itinuro mo sa akin — na walang pag-asa ang isang tulad ko. Naging inspirasyon mo ang pinakamagandang motivation ko."),
]

DIALOGUE_FAMILY = [
    ("FAMILY", "Anak, patawarin mo ako. Hindi ko dapat ginawa iyon sa iyo noon."),
    ("OP", "Matagal na iyon. Pareho tayong natuto sa pagkakamali natin."),
    ("FAMILY", "Ang ipinagmamalaki kita. Sana nasa langit ang iyong ama para makita ito."),
]

DIALOGUE_MENTOR = [
    ("MENTOR", "Nakakita ako ng potential sa iyo. Mayroon kang bagay na hindi ko nakikita sa iba."),
    ("OP", "Wala po akong karanasan. Wala po akong pera. Wala po akong alam sa negosyo."),
    ("MENTOR", "Ang karanasan ay natututunan. Ang pera ay kikitain. Pero ang determinasyon — iyon ay hindi mo mabibili. At iyon ang mayroon ka."),
]

DIALOGUE_FRIEND_SUPPORT = [
    ("KAIBIGAN", "Gising ka pa ba? Alas dos na ng madaling araw."),
    ("OP", "Hindi ako makatulog. Iniisip ko ang ating sitwasyon."),
    ("KAIBIGAN", "Huwag kang sumuko. Naniniwala ako sa iyo. Alam kong kaya mo ito."),
]


# ── Main story generator ──────────────────────────────────────────────────────

def generate_long_script(seed: str = None, target_minutes: int = 30) -> str:
    """Generate a complete [SPEAKER] tagged Tagalog CEO revenge story.

    Args:
        seed: Optional story seed to influence the story
        target_minutes: Target story length (15-60 minutes)

    Returns:
        Script string with [SPEAKER] tags
    """
    rng = random.Random(seed)

    # Pick character names
    male_name, male_surname = rng.choice(MALE_NAMES)
    female_name, female_surname = rng.choice(FEMALE_NAMES)
    betrayer_name = rng.choice([m for m in MALE_NAMES if m[0] != male_name] +
                                [(f, s) for f, s in FEMALE_NAMES if f != female_name])
    betrayer_first = betrayer_name[0]
    mentor_name = rng.choice([m for m in MALE_NAMES if m[0] not in (male_name, betrayer_name[0])])[0]

    # Pick location
    poor_location = rng.choice(LOCATIONS_POOR)
    biz_location = rng.choice(LOCATIONS_BUSINESS)

    # Pick betrayal
    betrayal = rng.choice(BETRAYALS)

    # Pick industry
    industry = rng.choice(INDUSTRIES)

    # Pick dialogue sets
    betrayal_dialogue = DIALOGUE_BETRAYAL
    confront_dialogue = DIALOGUE_CONFRONTATION

    # Calculate target word count (Tagalog TTS: ~140 words/min)
    target_words = target_minutes * 140
    # Ensure minimum
    target_words = max(target_words, 2000)

    # ── Build story parts ─────────────────────────────────────────────────────

    parts = []

    # ── PART 1: COLD OPEN ─────────────────────────────────────────────────────
    parts.append((
        "NARRATOR",
        f"Isang gabi, {poor_location}, nakatayo si {male_name} sa harap ng isang "
        f"malaking gusali {biz_location}. Nakatingin siya sa itaas — sa penthouse "
        f"kung saan nakaupo ang taong sumira sa kanyang buhay. Makalipas ang "
        f"sampung taon, babalik siya — hindi bilang isang mahirap na empleyado, "
        f"kundi bilang CEO ng kanyang sariling imperyo. 'Hayaan ninyong ikuwento ko "
        f"kung paano ako nagsimula sa wala — at kung paano ko nakuha ang lahat.'"
    ))

    # ── PART 2: SETUP — childhood and poverty ─────────────────────────────────
    parts.append((
        "OP_MALE",
        f"Ang pangalan ko ay {male_name} {male_surname}. Lumaki ako {poor_location} "
        f"sa isang pamilyang hindi alam kung saan kukuha ng susunod na pagkain. "
        f"Ang aking ama ay tricycle driver, ang aking ina ay labandera. "
        f"Apat kaming magkakapatid at kaming lahat ay nag-aaral sa pampublikong "
        f"paaralan. Hindi madali ang aming buhay. Madalas kaming walang makain "
        f"kundi kanin at toyo. Ngunit hindi ako nawalan ng pangarap. Pangarap kong "
        f"makaahon sa kahirapan at mabigyan ng magandang buhay ang aking pamilya."
    ))

    # ── PART 3: DREAM AND HARD WORK ───────────────────────────────────────────
    parts.append((
        "NARRATOR",
        f"Mula bata pa lang, alam na ni {male_name} na ang edukasyon ang tanging "
        f"daan para makaahon sa hirap. Araw-araw, naglalakad siya ng limang "
        f"kilometro papuntang eskwelahan — walang baon, walang sapatos, pero puno "
        f"ng pangarap. Sa gabi, nagtitinda siya ng kung anu-ano sa palengke para "
        f"makatulong sa kanyang pamilya."
    ))

    # ── PART 4: THE OPPORTUNITY ───────────────────────────────────────────────
    parts.append((
        "OP_MALE",
        f"Nang makapagtapos ako ng high school, nagtrabaho ako sa isang maliit na "
        f"kumpanya. Mababa ang sweldo, mahaba ang oras, pero okay lang sa akin. "
        f"Natututo ako. Bawat araw, pinag-aaralan ko ang negosyo — kung paano "
        f"ito tumatakbo, kung paano kumikita ang kompanya, kung saan nanggagaling "
        f"ang pera. Ine-extra ko ang lahat. Hindi ako nagrereklamo. Naniniwala "
        f"ako na ang sipag at tiyaga ay magbubunga balang araw."
    ))

    # ── PART 5: THE BIG IDEA ──────────────────────────────────────────────────
    parts.append((
        "OP_MALE",
        f"Isang araw, nagkaroon ako ng isang idea. Isang idea na alam kong "
        f"makapagpapabago sa aming kumpanya. Ilang gabi akong puyat, ginagawa "
        f"ang proposal. Iginuhit ko ang bawat detalye, kinompyut ang bawat numero. "
        f"Tatlong buwan ko itong ginawa. At isang gabi, ibinahagi ko ito sa aking "
        f"pinakamalapit na kasamahan — {betrayer_first}. Ang taong itinuturing "
        f"kong kapatid sa trabaho."
    ))

    # ── PART 6: THE BETRAYAL ──────────────────────────────────────────────────
    parts.append((
        "NARRATOR",
        f"Ngunit hindi alam ni {male_name} na ang taong kanyang pinagkatiwalaan "
        f"ay may ibang plano. {betrayal['detail']} {betrayal['aftermath_emotion']}"
    ))

    # Betrayal dialogue
    for speaker, line in betrayal_dialogue:
        spk = "OP_MALE" if speaker == "OP" else ("CHARACTER_M" if speaker == "BETRAYER" else speaker)
        parts.append((spk, line))

    # ── PART 7: AFTERMATH OF BETRAYAL ─────────────────────────────────────────
    parts.append((
        "OP_MALE",
        f"Parang bumagsak ang mundo ko. Nawalan ako ng trabaho, nawalan ako ng "
        f"karangalan, at higit sa lahat — nawalan ako ng tiwala sa ibang tao. "
        f"Umuwi ako sa aming bahay at nagtago. Hindi ako lumabas ng isang linggo. "
        f"Ang aking ina, si {female_name}, ang nagbigay sa akin ng lakas ng loob."
    ))

    parts.append((
        "CHARACTER_F",
        f"{male_name} anak, huwag kang susuko. Ang pagkatalo ay hindi katapusan. "
        f"Bumangon ka. Ipakita mo sa kanila kung sino ka."
    ))

    # ── PART 8: THE TURNING POINT ─────────────────────────────────────────────
    parts.append((
        "NARRATOR",
        f"At iyon ang naging turning point. Mula sa pagkabigo, nagsimulang "
        f"magsikap si {male_name}. Naghanap siya ng bagong oportunidad. "
        f"At isang araw, nakilala niya si {mentor_name} — isang taong makakapagpabago "
        f"ng kanyang buhay. Mag-comment kung na-inspire ka sa kwentong ito — "
        f"dahil ang pinakamagandang bahagi ay darating pa."
    ))

    # Mentor dialogue
    for speaker, line in DIALOGUE_MENTOR:
        spk = "OP_MALE" if speaker == "OP" else "CHARACTER_M"
        parts.append((spk, line.replace("MENTOR", mentor_name)))

    # ── PART 9: THE JOURNEY TO SUCCESS ────────────────────────────────────────
    parts.append((
        "NARRATOR",
        f"At dito nagsimula ang kamangha-manghang pagbabago. {industry['journey']}"
    ))

    parts.append((
        "OP_MALE",
        f"Hindi naging madali ang daan. Maraming gabi na gusto ko nang sumuko. "
        f"Maraming beses na wala akong pambayad sa upa. Maraming umaga na "
        f"gumising ako na walang laman ang refrigerator. Ngunit tuwing naaalala "
        f"ko ang pagtatraydor sa akin — ang sakit na ibinigay ng taong "
        f"pinagkatiwalaan ko — iyon ang nagtutulak sa akin na magpatuloy. "
        f"No pain, no gain. Sa bawat pagbagsak, mas matatag akong bumangon."
    ))

    # ── PART 10: THE CLIMB ────────────────────────────────────────────────────
    # Longer section — expand for 30+ min target
    climb_sections = [
        f"Ang {industry['business']} ay hindi agad naging successful. Unang taon, "
        f"lugi kami. Pangalawang taon, break-even lang. Ngunit sa ikatlong taon, "
        f"nagsimula nang kumita. Hindi ako naging gahaman. Bawat kita, "
        f"ina- reinvest ko sa negosyo. Bawat dagdag na piso, ibinabalik ko "
        f"sa pagpapalago ng kompanya.",

        f"Kinailangan kong magsakripisyo. Hindi ako nakadalo sa mga birthday "
        f"ng aking mga pamangkin. Hindi ako nakauwi sa probinsya nang tatlong "
        f"magkakasunod na Pasko. Ang aking ina ay umiiyak sa telepono, hinihiling "
        f"na umuwi ako. Ngunit alam ko na ang aking sakripisyo ay hindi "
        f"masasayang. Ang bawat oras na ginugugol ko sa trabaho ay isang "
        f"hakbang palapit sa aking pangarap.",

        f"Sa paglipas ng mga taon, nagsimulang makilala ang aking kumpanya. "
        f"{industry['success_detail']} Hindi lang ako ang umangat — lahat ng "
        f"kasama ko ay umangat din. Iyon ang tunay na tagumpay — hindi lang "
        f"ang iyong sariling pagyaman, kundi ang pag-angat mo sa iba.",

        f"Nagtayo ako ng scholarship program para sa mga batang katulad ko "
        f"noon — mahihirap ngunit puno ng pangarap. Nagbigay ako ng trabaho "
        f"sa mga taga-probinsya namin. Ang dating natutulog sa bangketa ay "
        f"ngayon ay nagpapatayo na ng mga bahay para sa iba.",
    ]

    for section in climb_sections:
        parts.append(("OP_MALE", section))

    # ── PART 11: THE REVENGE / CONFRONTATION ──────────────────────────────────
    parts.append((
        "NARRATOR",
        f"Ngunit hindi pa tapos ang kwento. Isang araw, nagkrus muli ang landas "
        f"ni {male_name} at {betrayer_first} — ang taong sumira sa kanyang buhay. "
        f"Muli silang nagkaharap — ngunit sa pagkakataong ito, iba na ang dinamiko."
    ))

    for speaker, line in confront_dialogue:
        spk = "OP_MALE" if speaker == "OP" else "CHARACTER_M"
        parts.append((spk, line))

    parts.append((
        "OP_MALE",
        f"Tiningnan ko siya sa mga mata. Hindi na ako ang mahirap na empleyado "
        f"na kanyang niloko. Ako na ngayon ang may-ari ng building na kanyang "
        f"pinagtatrabahuhan. Ang kanyang amo ay ako na ngayon. Hindi ako "
        f"nagalit. Sa halip, ngumiti ako at sinabi: "
        f"'Salamat. Dahil sa iyo, naging matagumpay ako. Kung hindi mo ako "
        f"tinraydor, hindi ko mararating ang kinaroroonan ko ngayon.'"
    ))

    # ── PART 12: RECONCILIATION / FAMILY ──────────────────────────────────────
    parts.append((
        "NARRATOR",
        f"Sa huli, natutunan ni {male_name} na ang tunay na tagumpay ay hindi "
        f"ang paghihiganti — kundi ang pagpapatawad at pag-angat sa iba."
    ))

    for speaker, line in DIALOGUE_FAMILY:
        spk = "OP_MALE" if speaker == "OP" else "CHARACTER_F"
        parts.append((spk, line.replace("FAMILY", female_name)))

    parts.append((
        "OP_MALE",
        f"Ngayon, tuwing Linggo, kumakain kaming magkakasama — buong pamilya. "
        f"Ang aking ina ay hindi na labandera. Ang aking mga kapatid ay "
        f"nakapagtapos na ng pag-aaral. Ang bahay namin ay hindi na kubo — "
        f"isa na itong malaking bahay na may hardin. Ngunit hindi ko "
        f"kinakalimutan kung saan ako nagsimula. Ang lumang bahay kubo namin "
        f"ay hindi ko ipinabagsak — pinanatili ko ito bilang paalala na "
        f"ang tagumpay ay hindi dumarating sa isang gabi."
    ))

    # ── PART 13: CONCLUSION ───────────────────────────────────────────────────
    parts.append((
        "NARRATOR",
        f"Kaya mga kaibigan — ano ang aral na natutunan natin sa kwentong ito? "
        f"Na ang pagkabigo ay hindi katapusan. Na ang pagtatraydor ay maaaring "
        f"maging inspirasyon. Na ang kahirapan ay hindi hadlang — ito ay "
        f"simula lamang. Ang tunay na tagumpay ay hindi nasusukat sa pera — "
        f"kundi sa kung gaano karaming tao ang iyong naiahon kasama mo."
        f"\n\n"
        f"Kung mayroon kayong sariling kwento ng tagumpay — o kung may kakilala "
        f"kayong nagtagumpay sa kabila ng lahat — ibahagi ninyo sa comments. "
        f"At kung nagustuhan ninyo ang kwentong ito, mag-subscribe at pindutin "
        f"ang bell para sa bagong kwento ng inspirasyon araw-araw."
    ))

    # ── Assemble script ───────────────────────────────────────────────────────
    total_words = sum(len(text.split()) for _, text in parts)

    # Pool of varied extra scenes for hitting target length
    FILLER_SCENES = [
        ("OP_MALE",
         "Marami akong natutunan tungkol sa negosyo at sa buhay. "
         "Ang pinakamahalagang aral — hindi lahat ng ngiti ay totoo. "
         "May mga taong lalapit dahil sa kung ano ang maaari mong ibigay, "
         "hindi dahil sa kung sino ka. Ngunit huwag mong hayaang baguhin "
         "ka ng mundong ito. Manatili kang totoo sa iyong sarili."),
        ("OP_MALE",
         "Ang tagumpay ay hindi dumarating sa isang gabi. Ito ay produkto "
         "ng libu-libong maliliit na desisyon. Ng bawat umaga na pinili "
         "mong gumising at lumaban kahit pagod na pagod ka na. Ng bawat "
         "gabi na pinili mong mag-aral sa halip na matulog. Ng bawat "
         "pagkakataon na pinili mong magpatuloy sa halip na sumuko."),
        ("OP_MALE",
         "Sa negosyo, ang pinakamahalaga ay hindi ang pera — kundi ang "
         "relasyon. Ang tiwala ng iyong mga customer. Ang loyalty ng "
         "iyong mga empleyado. Ang suporta ng iyong pamilya. Kapag "
         "nasira mo ang tiwala, nawala ang lahat. Pero kapag pinahalagahan "
         "mo ang bawat isa, walang limitasyon ang iyong maaabot."),
        ("OP_MALE",
         "Madalas akong tanungin ng mga tao — ano ang sikreto ng tagumpay? "
         "Ang sagot ko palagi ay: walang sikreto. Sipag, tiyaga, at tiwala "
         "sa Diyos. Hindi kailangan ng koneksyon. Hindi kailangan ng "
         "malaking puhunan. Kailangan mo lang ng matibay na loob at "
         "paninindigan na hindi ka susuko kahit anong mangyari."),
        ("OP_MALE",
         "Isang bagay ang natutunan ko sa mga pagsubok — ang tunay na "
         "yaman ay hindi nasusukat sa laman ng iyong bangko. Nasusukat "
         "ito sa laman ng iyong puso. Ilang tao ang iyong natulungan? "
         "Ilang pamilya ang iyong naiahon? Iyan ang tunay na kayamanan "
         "na walang magnanakaw na maaaring kunin sa iyo."),
        ("OP_MALE",
         "Noong nasa gitna ako ng pinakamabigat na pagsubok, may isang "
         "bagay na nagbigay sa akin ng lakas — ang alaala ng aking pamilya. "
         "Ang nakikita ko silang naghihirap ay sapat na dahilan para "
         "ipagpatuloy ko ang laban. Hindi ako nabigo para sa sarili ko — "
         "nabigo ako para sa kanila. At iyon ang pinakamasakit sa lahat."),
        ("OP_MALE",
         "Maraming beses na gusto ko nang tumigil. Maraming gabi na "
         "umiiyak ako sa dilim, nagdarasal na sana ay may magbago. "
         "Pero tuwing umaga, bumangon ako. Hindi dahil malakas ako — "
         "kundi dahil alam kong may umaasa sa akin. Ang aking pamilya. "
         "Ang aking mga pangarap. Ang aking pangako sa sarili."),
        ("OP_MALE",
         "Kung may isa akong payo na ibibigay sa mga nangangarap — huwag "
         "kayong matakot sa pagkabigo. Ang pagkabigo ay hindi kabiguan — "
         "ito ay aral. Bawat pagkakamali ay isang hakbang palapit sa "
         "tagumpay. Bawat pagkatalo ay nagtuturo sa iyo kung paano "
         "manalo. Ang tunay na pagkatalo ay ang pagsuko."),
        ("OP_MALE",
         "Ang negosyo ay parang halaman. Hindi ito lalago kung hindi mo "
         "aasikasuhin araw-araw. Kailangan ng tubig — iyon ang sipag. "
         "Kailangan ng araw — iyon ang tamang diskarte. Kailangan ng "
         "pataba — iyon ang mga taong nakapaligid sa iyo. At higit sa "
         "lahat, kailangan ng panahon. Walang instant na tagumpay."),
        ("OP_MALE",
         "Tatlong bagay ang lagi kong dala sa aking paglalakbay: una, "
         "ang pananampalataya sa Diyos — Siya ang aking gabay. Pangalawa, "
         "ang pagmamahal sa pamilya — sila ang aking inspirasyon. "
         "Pangatlo, ang determinasyon — ito ang aking sandata. Sa "
         "tatlong ito, walang hadlang na hindi malalampasan."),
    ]

    extra_scenes = []
    while total_words < target_words:
        idx = len(extra_scenes) % len(FILLER_SCENES)
        scene = FILLER_SCENES[idx]
        extra_scenes.append(scene)
        total_words += len(scene[1].split())

    for spk, text in extra_scenes:
        parts.insert(-1, (spk, text))

    # ── Build final script ────────────────────────────────────────────────────
    script_parts = []
    for speaker, text in parts:
        script_parts.append(f"[{speaker}] {text.strip()}")

    script = "\n\n".join(script_parts)
    final_words = len(script.split())
    print(f"[story_engine] Generated {final_words} words (~{final_words // 140} min script)")
    return script


if __name__ == "__main__":
    # Test
    script = generate_long_script(target_minutes=10)
    print("\n--- FIRST 500 CHARS ---")
    print(script[:500])
    print(f"\nTotal: {len(script.split())} words")
