"""Deterministic input safety checks. They run before any model call, so obvious emergencies are never missed."""
import re

from .. import language

RED_FLAGS = [
    (r"\b(suicid\w*|kill(ing|ed)? (my|him|her)self|end(ing)? (my life|it all)|take my (own )?life|self[- ]?harm\w*|want to die"
     r"|hurt(ing)? myself|cut(ting)? myself|better off dead|better off without me|no reason to live"
     r"|(no longer|don'?t|do not) want to (live|be alive|exist|be here)|wish I (was|were|wasn'?t) (dead|alive|here)"
     r"|(wish|hope|want)\b[^.!?]{0,40}\b(not|never) (to )?wake up"
     r"|(lethal|fatal|deadly) (dose|amount)|how (much|many)\b[^.!?]{0,40}\bto (die|kill (my|him|her)self)|overdose on purpose)\b",
     "Thoughts of suicide or self-harm",
     "You deserve support right now. Call or text 9-8-8 (Suicide Crisis Helpline, Canada and US), or call 911 if you might act on these thoughts."),
    (r"\b(want|going|plan(ning)?) to (kill|hurt|harm|attack) (him|her|them|someone|somebody|people|my \w+)\b",
     "Thoughts of harming someone else",
     "If anyone could be in danger right now, call 911. You can also call or text 9-8-8 to talk it through with someone."),
    (r"\b(hits|beats|abuses|chokes|hurts|touches) me\b|\bbeing (abused|hit|beaten)\b|\b(scared|afraid) (to go|of going) home\b",
     "Possible abuse or an unsafe home",
     "If you're in danger right now, call 911. You deserve to be safe, and a crisis line like 9-8-8 can help you make a plan."),
    (r"\bchest\b[^.,;!?]{0,20}\b(pain\w*|hurt\w*|pressure|tight\w*|heavy|aches?|aching)\b"
     r"|\b(pain|pressure|tightness)\b[^.,;!?]{0,15}\b(in|on) my chest\b|\bcrushing\b.*\bchest\b|\bheart attack\b",
     "Chest pain or pressure",
     "Chest pain can be a heart attack. Call emergency services (911 / 112 / 999) now."),
    (r"\b(can'?t|cannot|unable to|hard to|trouble|difficulty|struggling to) breath\w*|\bshort(ness)? of breath\b|\bgasping\b"
     r"|\bcan'?t catch (my|his|her|their) breath\b|\b(lips?|face)\b[^.,;!?]{0,20}\b(blue|bluish)\b",
     "Trouble breathing",
     "Severe breathing difficulty needs emergency care. Call emergency services now."),
    (r"\b(face|mouth|smile) (is )?(droop\w*|drooping)\b|\bslurred speech\b|\bslurring\b|\bspeech (is |was )?(suddenly )?(slurred|garbled)\b"
     r"|\bgarbled speech\b|\b(sudden )?(numb|weak)\w* (on )?one side\b|\bhalf (of )?(my|his|her|their) (face|body)\b[^.,;!?]{0,20}\b(numb|weak|droop\w*|paralyz\w*)"
     r"|\bsudden(ly)?\b[^.,;!?]{0,20}\b(can'?t|cannot|unable to) (lift|raise|move) (my|his|her|their) (arm|leg)\b|\bstroke\b",
     "Possible stroke signs",
     "Think F.A.S.T.: face drooping, arm weakness, speech difficulty, time to call emergency services. Call now."),
    (r"\b(suddenly|very|newly) confused\b|\bconfused and (doesn'?t|does not|can'?t) (know|recogni[sz]e)\b"
     r"|\bdoesn'?t know where (he|she|they) (is|are)\b",
     "Sudden confusion",
     "Sudden confusion can be a stroke, very low blood sugar, or a serious infection. Call emergency services now."),
    (r"^(?=.*\b(([0-9]|1[0-2])[- ]?(days?|weeks?|wks?)[- ]old|[0-2][- ]?(months?|mos?)[- ]old|newborn)\b)"
     r"(?=.*\b(fever\w*|temperature|temp|feels hot|38(\.\d)?|39(\.\d)?|100\.[4-9]|10[1-4](\.\d)?)\b)",
     "Fever in a young infant",
     "A fever in a baby under 3 months old needs emergency care now. Go to the nearest emergency room or call 911."),
    (r"^(?=.*\b((hit|bumped|banged|struck|smacked) (my|his|her|their|the) head|head (injury|trauma)|fell on (my|his|her|their) head|concussion)\b)"
     r"(?=.*\b(vomit\w*|threw up|thrown up|throwing up|passed out|blacked out|knocked out|unconscious|seizure|confus\w*|won'?t wake)\b)",
     "Head injury with warning signs",
     "A head injury with vomiting, confusion, or passing out needs emergency care now. Call 911 or go to the ER."),
    (r"\b(throat|tongue|lips?)\b[^.,;!?]{0,25}\b(swell\w*|swollen|closing|clos(e|ing) up)\b|\banaphyla\w*\b",
     "Possible severe allergic reaction",
     "Use an epinephrine auto-injector if you have one and call emergency services now."),
    (r"\b(passed out|fainted|unconscious|unresponsive|seizure|convuls\w*|collapsed|blacked out|knocked out"
     r"|(isn'?t|is not|not) responding|won'?t wake up|can'?t wake (him|her|them))\b",
     "Loss of consciousness or seizure",
     "If someone has collapsed, isn't responding, or is having a seizure, call emergency services (911) now. "
     "A faint that has passed still needs to be checked soon."),
    (r"\b(coughing|vomiting|throwing up) (up )?blood\b|\bblood in (my|his|her|their|the) (vomit|stool|poop)\b|\bcoffee grounds\b"
     r"|\bbleeding\b[^.,;!?]{0,25}\b(won'?t|will not|doesn'?t|does not|that won'?t) stop\b|\bblack,? tarry stool\b",
     "Serious bleeding",
     "Significant bleeding needs emergency care. Call emergency services or go to the ER now."),
    (r"^(?=.*\bpregnan\w*)(?=.*\bbleed\w*)",
     "Bleeding in pregnancy",
     "Bleeding during pregnancy needs to be checked right away. Go to the emergency room or call 911 if it's heavy or with pain."),
    (r"\b(testicle|testicular|scrot\w*)\b[^.!?]{0,30}\b(sudden\w*|severe|terrible|worst|excruciating)\b"
     r"|\b(sudden\w*|severe|terrible|worst|excruciating)\b[^.!?]{0,30}\b(testicle|testicular|scrot\w*)\b",
     "Sudden severe testicle pain",
     "Sudden, severe testicle pain can be testicular torsion, which needs emergency surgery. Go to the ER now."),
    (r"\bcold,? (and )?clammy\b",
     "Possible shock",
     "Cold, clammy skin with feeling faint or breathing fast can be shock. Call emergency services now."),
    (r"\bworst headache\b|\bthunderclap\b|\bstiff neck\b.*\bfever\b|\bfever\b.*\bstiff neck\b",
     "Possible serious headache / meningitis signs",
     "A sudden worst-ever headache or fever with stiff neck needs emergency evaluation now."),
    (r"\boverdos\w*\b|\b(took|taken|swallowed|ate)\b[^.!?]{0,25}\b(\d{2,}|a lot of|too many|lots of|a (whole|full) (bottle|pack|box) of)\b"
     r"[^.!?]{0,25}\b(pills|tablets|capsules)\b"
     r"|\b(swallowed|drank|drunk|ate|ingested)\b[^.!?]{0,25}\b(batter(y|ies)|bleach|detergent|cleaner|antifreeze|magnets?|poison)\b"
     r"|\bcarbon monoxide\b",
     "Possible overdose or poisoning",
     "Call 911 or your local poison control centre now, even if they seem fine. Don't wait for symptoms."),
]


NEGATION = re.compile(r"\b(no|not|never|without|denies|don'?t have|doesn'?t have|haven'?t had|no sign of|didn'?t|did not)\b"
                      r"[^.,;!?]{0,25}$")

# Breathlessness only during activity ("short of breath on the stairs") is not an emergency on its own;
# the model still judges it in context.
EXERTIONAL = re.compile(r"^[^.,;!?]{0,25}\b(on|when|with|after|while|during|going up|climbing|walking)\b[^.,;!?]{0,25}"
                        r"\b(stairs|steps|exercis\w*|exert\w*|walk\w*|run\w*|climb\w*|activity|hills?|working out|sports?)\b")
SKIP_IF_FOLLOWED_BY = {"Trouble breathing": EXERTIONAL}

MENTAL_HEALTH = {"Thoughts of suicide or self-harm", "Thoughts of harming someone else", "Possible abuse or an unsafe home"}
QUESTION = re.compile(r"^\s*(what|how|why|when|which|who|is|are|can|could|does|do|should|would|will)\b")
ASKING_HOW_TO_TELL = re.compile(r"\bhow (can|do|would|should|could) (i|we|you) (tell|know|recogni[sz]e|spot)\b")
PERSONAL = re.compile(r"\b(i|i'm|im|i've|ive|i'd|me|my|mine|we|our|us|he|she|his|her|him|they|them|their|son|daughter|baby|"
                      r"child|kid|toddler|mom|mum|mother|dad|father|husband|wife|partner|friend|grandma|grandpa|grandmother|"
                      r"grandfather|brother|sister|boyfriend|girlfriend|coworker)\b")


def is_general_question(text):
    """A question about health in general ("how is a stroke treated?"), not about someone it's happening to."""
    return bool(QUESTION.search(text)) and not PERSONAL.search(ASKING_HOW_TO_TELL.sub("", text))


def screen_red_flags(text):
    """Physical red flags are skipped for general questions; mental-health flags never are."""
    text = text.lower()
    general = is_general_question(text)
    flags = []
    for pattern, label, advice in RED_FLAGS:
        if general and label not in MENTAL_HEALTH:
            continue
        skip_after = SKIP_IF_FOLLOWED_BY.get(label)
        for m in re.finditer(pattern, text, re.I):
            if NEGATION.search(text[:m.start()]):
                continue
            if skip_after and m.group(0).startswith(("short", "can")) and skip_after.search(text[m.end():]):
                continue
            flags.append({"label": label, "advice": advice})
            break
    return flags


def screen_message(text, lang="en", usage=None):
    """Keyword safety check that also works for other languages, by checking an English translation too.
    Labels stay in English (the app uses them as keys); the advice is shown in the app language."""
    flags = screen_red_flags(text)
    if not flags and text.strip() and language.needs_english(text, lang):
        try:
            flags = screen_red_flags(language.to_english(text, usage=usage))
        except Exception as e:
            print("Translation for safety check failed:", type(e).__name__)
    return [{**f, "advice": language.ui_text(f["advice"], lang)} for f in flags]
