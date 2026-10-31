"""Deterministic input safety checks. They run before any model call, so obvious emergencies are never missed."""
import re

from .. import language

RED_FLAGS = [
    (r"\b(suicid\w*|kill (my|him|her)self|end (my life|it all)|self[- ]?harm\w*|want to die|hurt(ing)? myself|cut(ting)? myself"
     r"|better off dead|better off without me|no reason to live|don'?t want to (live|be alive|be here anymore)|wish I (was|were|wasn'?t) (dead|alive|here)"
     r"|(want to|wish I could|hope I) (not|never) wake up)\b",
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
    (r"\b(can'?t|cannot|unable to|hard to|trouble|difficulty|struggling to) breath\w*|\bshort(ness)? of breath\b|\bgasping\b|\b(lips?|face)\b[^.,;!?]{0,20}\b(blue|bluish)\b",
     "Trouble breathing",
     "Severe breathing difficulty needs emergency care. Call emergency services now."),
    (r"\b(face|mouth|smile) (is )?(droop\w*|drooping)\b|\bslurred speech\b|\bslurring\b|\b(sudden )?(numb|weak)\w* (on )?one side\b|\bstroke\b",
     "Possible stroke signs",
     "Think F.A.S.T.: face drooping, arm weakness, speech difficulty, time to call emergency services. Call now."),
    (r"\b(throat|tongue|lips?) (is |are )?(swell\w*|closing)\b|\banaphyla\w*\b",
     "Possible severe allergic reaction",
     "Use an epinephrine auto-injector if you have one and call emergency services now."),
    (r"\b(passed out|fainted|unconscious|unresponsive|seizure|convuls\w*)\b",
     "Loss of consciousness or seizure",
     "Fainting or seizures need urgent evaluation. Call emergency services if it is happening now or recurring."),
    (r"\b(coughing|vomiting|throwing up) (up )?blood\b|\bbleeding (won'?t|will not|that won'?t) stop\b|\bblack,? tarry stool\b",
     "Serious bleeding",
     "Significant bleeding needs emergency care. Call emergency services or go to the ER now."),
    (r"\bworst headache\b|\bthunderclap\b|\bstiff neck\b.*\bfever\b|\bfever\b.*\bstiff neck\b",
     "Possible serious headache / meningitis signs",
     "A sudden worst-ever headache or fever with stiff neck needs emergency evaluation now."),
]


NEGATION = re.compile(r"\b(no|not|never|without|denies|don'?t have|doesn'?t have|haven'?t had|no sign of)\b[^.,;!?]{0,25}$")

# Breathlessness only during activity ("short of breath on the stairs") is not an emergency on its own;
# the model still judges it in context.
EXERTIONAL = re.compile(r"^[^.,;!?]{0,25}\b(on|when|with|after|while|during|going up|climbing|walking)\b[^.,;!?]{0,25}"
                        r"\b(stairs|steps|exercis\w*|exert\w*|walk\w*|run\w*|climb\w*|activity|hills?|working out|sports?)\b")
SKIP_IF_FOLLOWED_BY = {"Trouble breathing": EXERTIONAL}


def screen_red_flags(text):
    text = text.lower()
    flags = []
    for pattern, label, advice in RED_FLAGS:
        skip_after = SKIP_IF_FOLLOWED_BY.get(label)
        for m in re.finditer(pattern, text, re.I):
            if NEGATION.search(text[:m.start()]):
                continue
            if skip_after and m.group(0).startswith("short") and skip_after.search(text[m.end():]):
                continue
            flags.append({"label": label, "advice": advice})
            break
    return flags


def screen_message(text, lang="en"):
    """Keyword safety check that also works for other languages, by checking an English translation too.
    Labels stay in English (the app uses them as keys); the advice is shown in the app language."""
    flags = screen_red_flags(text)
    if not flags and text.strip() and language.needs_english(text, lang):
        try:
            flags = screen_red_flags(language.to_english(text))
        except Exception as e:
            print("Translation for safety check failed:", e)
    return [{**f, "advice": language.ui_text(f["advice"], lang)} for f in flags]
