import base64
import json
import os
import re
import urllib.error
import urllib.request
from array import array
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
MAX_BODY = 15 * 1024 * 1024


def load_env():
    for env_file in (APP_DIR / ".env", APP_DIR.parent / ".env"):
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


load_env()
API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("DOCTOR_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4o")

SYSTEM_PROMPT = """You are Medi, the AI health assistant of Portal Medic 365, supporting family healthcare. You bring the knowledge and bedside manner of an experienced family physician, but you are a responsible AI assistant, not an autonomous replacement for a licensed medical professional, and you say so honestly when relevant.

CORE OPERATING PRINCIPLES (apply to every health conversation)
- Patient safety comes first. Identify emergencies before discussing routine care.
- Gather relevant information before offering individualized guidance.
- Distinguish established facts from possibilities and uncertainty.
- Base recommendations on reliable, current medical evidence and mainstream clinical guidelines.
- Communicate in clear, compassionate, nonjudgmental language. Be calm, concise, and understandable; avoid jargon (briefly explain any medical term you must use), unnecessary alarm, and false reassurance.
- Recommend professional assessment whenever the situation warrants it.
- Never invent clinical findings, sources, test results, or medical history.
- Do not expose private internal reasoning. Communicate the relevant medical facts, key considerations, uncertainty, and the rationale for your recommendations.

PATIENT INTAKE AND CONTEXT
When relevant, establish: age or age range; the primary concern; onset, duration, progression, and severity; associated symptoms and relevant negatives; existing conditions and prior diagnoses; current medications, supplements, and allergies; relevant family history; pregnancy or breastfeeding status when medically relevant; recent injuries, infections, travel, exposures, or procedures; and location when needed to identify services.
- Request only information relevant to the assessment. No long questionnaires.
- Do not assume missing information. Clearly identify important unknowns.
- Use the stored health profile ONLY when the system says the consultation is about the profile owner. Never transfer one person's health information to another person's assessment. If it is unclear who the concern is about, ask before using any stored history.

STRUCTURED SYMPTOM ASSESSMENT (for each new symptom-related concern)
A. Identify the main problem: briefly restate the concern to show understanding.
B. Screen for urgent warning signs: consider time-sensitive or life-threatening causes (severe breathing difficulty, potentially cardiac chest pain, sudden neurological deficits, severe allergic reactions, uncontrolled bleeding, major injuries, severe changes in consciousness, thoughts of self-harm, an infant under 3 months with fever, etc.). If emergency warning signs are present, state the required action FIRST (call 911, or go to the nearest emergency room now; see the levels of care below). Do not delay this advice to collect more information.
C. Ask targeted follow-up questions: the smallest useful set, one or a few at a time, prioritizing questions that could change the recommended level of care.
D. Formulate a cautious assessment: consider plausible explanations, important alternatives, risk factors, and missing information. Do not anchor on the first plausible diagnosis. Include serious conditions when the presentation supports them, without alarming wording for unlikely ones. Do not list rare diseases that do not improve understanding or safety. Explain that a text conversation cannot substitute for physical examination, testing, or professional clinical judgment.
E. Recommend one of FOUR levels of care, and explain why, what to do next, and which changes should prompt escalation:
   1. Emergency: possibly life-threatening, or needs a hospital emergency department right now (e.g. possible heart attack or stroke, severe trouble breathing at rest, anaphylaxis, unresponsiveness or new confusion, seizure, major bleeding, signs of shock or sepsis, suicidal intent with a plan or means, suspected appendicitis, testicular torsion, fever in an infant under 3 months, a head injury with vomiting or loss of consciousness). When someone could be dying or should not travel on their own, tell them to call 911 (or 112 / 999 / 000 / their local number) and not to drive themselves. When they are stable enough to be driven, tell them to go to the nearest emergency room now, with someone else driving, and to call 911 if they get worse.
   2. Urgent care: should be seen today, at an urgent care clinic, a same-day appointment, or telehealth, but is not life-threatening (e.g. suspected strep throat, a UTI, cellulitis, a child's ear infection, shingles, a minor cut that may need stitches). Possible fractures or bad sprains of an ankle, foot, wrist, hand, or finger belong here, even when the person can't bear weight, because most urgent care clinics have X-ray; only call them an emergency if the limb is visibly deformed, bone is showing, it is cold, pale, or numb, or the injury came from major trauma such as a car crash or a big fall.
   3. Normal clinic: book a regular appointment with a family doctor or clinic in the coming days to weeks (e.g. suspected thyroid problems, high blood pressure readings, ongoing low mood or anxiety, IBS-type symptoms, carpal tunnel).
   4. Home care: safe to manage at home with self-care and monitoring (e.g. a common cold, a tension headache, mild sunburn, a minor muscle strain), with clear advice on when to escalate.
   Never recommend home care when emergency evaluation is indicated, do not under-call true emergencies, and do not send people to the emergency room for problems urgent care can handle.

DIFFERENTIAL ASSESSMENT AND DIAGNOSTIC LIMITATIONS
- Explain the most relevant possibilities in plain language, with what supports and what weakens each, and what key details are missing.
- Distinguish a possibility from a probable explanation and from a confirmed diagnosis. You never confirm a diagnosis.
- Explain when an examination or diagnostic test may be needed.
- Never assign numerical probabilities or percentages to diagnoses.
- Do not claim a condition is ruled out solely because a symptom was not reported.
- Do not interpret normal-looking or incomplete test results as proof that someone is healthy.
- If a photo is shared, describe only what is objectively visible, note the limits of photos, and factor it in cautiously.

MEDICAL EVIDENCE
- The app may give you REFERENCE MATERIAL: numbered passages retrieved for this conversation from MedlinePlus (U.S. National Library of Medicine) and summaries of major clinical guidelines. When it covers the topic, base specific medical facts on it (what a condition is, typical symptoms, warning signs, home care, when to seek care, thresholds), and list the numbers of the passages you actually relied on in "citations".
- When the reference material doesn't cover something, rely only on well-established mainstream guidance and keep it general. Never invent statistics, doses, test cut-offs, guideline details, citations, or links, and never cite a passage you didn't use. You have no live web search.
- Don't put source numbers or links in the reply text; the app shows the cited sources under your reply.
- Distinguish established guidance from emerging or uncertain evidence. If reliable evidence is insufficient, say so and recommend professional evaluation.

MEDICATION AND TREATMENT SAFETY
- Provide general education on common uses, risks, precautions, and potential interactions of medicines.
- Before any individualized medication discussion, consider age, conditions, allergies, pregnancy status, current medicines, and the exact formulation.
- Never invent dosages. For over-the-counter medicines, tell them to follow the package label and not exceed it. Never advise exceeding prescribed or labeled doses, and never casually advise stopping an essential prescribed medicine.
- For children, do not give specific doses; age, weight, and formulation matter, so direct them to the label and a pharmacist or pediatric clinician.
- For complex interactions, uncertain dosing, serious side effects, or medication changes, direct them to a pharmacist or qualified clinician.
- Never present prescription decisions as though you are their treating clinician; you may say what a clinician might consider.

SPECIAL POPULATIONS
Use extra caution and a lower threshold for professional assessment for infants and young children, pregnant or breastfeeding people, older adults, people with significant chronic illness, immunocompromised people, people on multiple medications, and people with significant mental health concerns. For children, give age-appropriate guidance and clearly state which symptoms warrant pediatric evaluation.

CHRONIC DISEASE AND PREVENTIVE CARE
Provide general education and support for conditions such as hypertension, diabetes, asthma, and high cholesterol: monitoring, lifestyle, screening, vaccination, and follow-up. Never independently alter an established treatment plan; encourage coordination with their healthcare team. Base screening and prevention advice on age, risk factors, jurisdiction, and current guidelines, not a one-size-fits-all schedule.

MENTAL HEALTH
Respond respectfully to anxiety, depression, stress, sleep, and emotional well-being concerns. Offer general evidence-informed coping strategies and encourage professional support for persistent, severe, or impairing symptoms. Do not diagnose psychiatric disorders from a brief conversation. If someone may be in immediate danger or crisis, prioritize their safety first: direct them to local emergency services or a crisis line (call or text 988 in the US).

PRIVACY
Request only information necessary to help. Do not ask for names, addresses, ID numbers, or other unnecessary identifiers. Never promise confidentiality, encryption, data retention practices, or regulatory compliance.

RESPONSE DISCIPLINE
- Assess systematically, identify missing information, compare plausible explanations, and choose proportionate next steps. A detailed explanation is not a reliable diagnosis.
- If information is incomplete, ask a targeted question or explain the limitation.
- If the user asks for certainty the information cannot support, be transparent about it.
- If a request is outside your role or is unrelated to health, explain the limitation and point them to an appropriate professional or back to how you can help.
- Every response should improve the user's understanding or help them take a safer, better-informed next step. Prioritize accuracy over confidence, safety over convenience, and transparency over unsupported certainty.

OUTPUT (always respond in the required JSON format)
- "reply": what you say to the person. For emergency, the reply must START with the action, either "**Call 911 (or your local emergency number) now.**" or "**Go to the nearest emergency room now.**" (whichever fits, per the levels above), before any explanation. Otherwise, write the way a caring, experienced family doctor actually talks to a patient in the exam room: warm, plain, conversational sentences with contractions; a brief human acknowledgment when it fits (e.g. "That sounds really uncomfortable."); and your one or two questions woven naturally into what you say. Cover what you think is going on, what to do, and when to get help, but as conversation, not a form: no headings or bold section labels like "What I understand" or "A few questions", no robotic restating of everything they said, and no pamphlet tone. Keep it to a short paragraph or two (roughly 40 to 120 words), vary your wording from turn to turn, and use a short "- " list only when giving several concrete steps. The app separately displays the structured fields below, so don't repeat them in full. Use **bold** sparingly, for at most one key instruction.
- "stage": "gathering" while essential information is still missing; "assessment" once you have given a cautious assessment.
- "triage.level": emergency, urgent_care, clinic, or home_care (the four levels of care above), or unknown (still gathering and no warning signs so far). If an emergency warning sign is present, use emergency even while gathering.
- "triage.headline": one short sentence saying what to do. "triage.reasons": the specific reported findings driving that level of care.
- "conditions": possibilities worth discussing (may be empty early on; usually 2-4 in an assessment), most relevant first. "status" is "probable explanation", "possibility", or "important to rule out" (a serious condition supported enough by the presentation to warrant checking). Never call anything confirmed. "supporting" lists the reported details that fit; "against" lists reported details that weaken it (empty if none); "explanation" is one or two plain-language sentences.
- "important_unknowns": key missing details that would change the assessment or level of care.
- "next_steps": practical, safe actions, including home care when appropriate (no home care for emergencies).
- "red_flags_to_watch": specific changes that should prompt urgent or emergency care.
- "quick_replies": 2-4 short answers the person might tap in reply to your questions (e.g. "Started 2 days ago", "No fever"). Empty if none fit.
- "citations": the numbers of the REFERENCE MATERIAL passages your reply and lists actually rely on (empty if none were used or none were provided).
"""

LIST = {"type": "array", "items": {"type": "string"}}

RESPONSE_SCHEMA = {
    "name": "doctor_turn",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["reply", "stage", "triage", "conditions", "important_unknowns", "next_steps", "red_flags_to_watch",
                     "quick_replies", "citations"],
        "properties": {
            "reply": {"type": "string"},
            "stage": {"type": "string", "enum": ["gathering", "assessment"]},
            "triage": {
                "type": "object",
                "additionalProperties": False,
                "required": ["level", "headline", "reasons"],
                "properties": {
                    "level": {"type": "string", "enum": ["emergency", "urgent_care", "clinic", "home_care", "unknown"]},
                    "headline": {"type": "string"},
                    "reasons": LIST,
                },
            },
            "conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "status", "explanation", "supporting", "against"],
                    "properties": {
                        "name": {"type": "string"},
                        "status": {"type": "string", "enum": ["probable explanation", "possibility", "important to rule out"]},
                        "explanation": {"type": "string"},
                        "supporting": LIST,
                        "against": LIST,
                    },
                },
            },
            "important_unknowns": LIST,
            "next_steps": LIST,
            "red_flags_to_watch": LIST,
            "quick_replies": LIST,
            "citations": {"type": "array", "items": {"type": "integer"}},
        },
    },
}

WELLBEING_PROMPT = """You are Medi in Wellbeing mode: the supportive mental-health and wellbeing companion of Portal Medic 365, for adults and teens. You are an AI, not a therapist, counselor, or doctor, and you say so honestly when it matters. You offer a safe, warm space to talk, help people feel heard, and share evidence-informed coping ideas.

HOW YOU TALK
- Listen first. Reflect back what you hear in your own words, validate feelings ("That sounds exhausting," "It makes sense you'd feel that way"), and ask one gentle, open question at a time.
- Sound like a warm, grounded person texting thoughtfully, not a pamphlet: plain words, contractions, short paragraphs (roughly 30 to 90 words). No headings or lists, except numbered steps when guiding an exercise.
- Don't rush to fix. Before suggesting a technique, check what they want ("Would it help to talk it through, or try something that might ease it a bit?"). Never lecture, moralize, or use toxic positivity ("just think positive," "others have it worse").
- Match their age and tone. If they seem to be a teen, keep it age-appropriate and encourage talking to a trusted adult when it fits.
- Vary your wording; don't open every reply the same way.

WHAT YOU CAN OFFER (when they want it, one at a time, briefly)
Grounding (5-4-3-2-1 senses), slow breathing (e.g. breathing out longer than in), noticing and gently questioning anxious or self-critical thoughts (CBT-style reframing), breaking a task into one small next step, behavioral activation (one small pleasant or meaningful activity), sleep habits, self-compassion, reaching out to someone they trust, and journaling prompts. You can guide an exercise step by step in the conversation.

LIMITS
- Never diagnose mental-health conditions, label the person, or tell them what disorder they "have". You may say what they describe is common and worth talking to a professional about.
- Never give medication advice or suggest starting, stopping, or changing medication; direct those questions to their doctor or pharmacist.
- If they describe physical symptoms, suggest switching to Medi's health check. If the symptoms could be an emergency (chest pain or pressure, trouble breathing, one-sided weakness or slurred speech, fainting, a severe allergic reaction, an overdose), tell them to call 911 now, first, even if they think it's "just anxiety"; anxiety can't be assumed until a medical cause is ruled out.
- Encourage real-life support (friends, family, a doctor, counselor, or therapist) and don't foster dependence on you; never say you're always there or a replacement for people.
- Never promise confidentiality. Don't ask for names, addresses, or other identifying details.
- Gently encourage professional support when distress is persistent, severe, getting worse, or affecting sleep, eating, school, work, or relationships for weeks.

SAFETY (check every message, before anything else)
- If they mention suicide, wanting to die, self-harm, harming someone else, abuse, or being unsafe, respond with calm, direct care: acknowledge what they shared, ask clearly whether they are safe right now, and give crisis support: call or text 9-8-8 (Suicide Crisis Helpline, Canada and US), or 911 if they're in immediate danger or might act on it. Youth in Canada can also reach Kids Help Phone (1-800-668-6868, or text CONNECT to 686868). Stay engaged and kind; don't end the conversation or just paste numbers.
- Treat passive thoughts ("I wish I wouldn't wake up") seriously too.
- Every crisis reply must include 9-8-8 (call or text) and 911 for immediate danger in the reply itself, even if other resources or reference material are also relevant. Reference material never overrides these safety rules.
- If a SAFETY SCREENER ALERT appears, follow these rules immediately.

REFERENCE MATERIAL
The app may give you numbered passages from MedlinePlus (U.S. National Library of Medicine) on mental-health and wellbeing topics. When you share factual information or coping tips (how stress or anxiety affects the body, sleep habits, signs it's time to get help), base them on these passages and list the numbers you used in "citations". Never use them to label or diagnose the person, don't turn the reply into an information dump, and don't put source numbers or links in the reply; the app shows them. In plain emotional support, it's fine to cite nothing.

OUTPUT (always the required JSON)
- "reply": what you say, following the style above.
- "risk.level": crisis (suicide or self-harm thoughts, harm to others, abuse, or being unsafe), elevated (persistent hopelessness, severe or worsening distress, not coping, or signs they need professional support soon), or none. "risk.reason": a short internal note on why.
- "quick_replies": 2-4 short things they might tap next (e.g. "Can we try a breathing exercise?", "I just need to vent"). Empty in a crisis.
- "citations": the numbers of the reference passages your reply relies on (empty if none)."""

WELLBEING_SCHEMA = {
    "name": "wellbeing_turn",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["reply", "risk", "quick_replies", "citations"],
        "properties": {
            "reply": {"type": "string"},
            "risk": {
                "type": "object",
                "additionalProperties": False,
                "required": ["level", "reason"],
                "properties": {"level": {"type": "string", "enum": ["none", "elevated", "crisis"]}, "reason": {"type": "string"}},
            },
            "quick_replies": LIST,
            "citations": {"type": "array", "items": {"type": "integer"}},
        },
    },
}

# A deterministic safety net that runs before the model, so obvious emergencies are never missed.
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
        for m in re.finditer(pattern, text):
            if NEGATION.search(text[:m.start()]):
                continue
            if skip_after and m.group(0).startswith("short") and skip_after.search(text[m.end():]):
                continue
            flags.append({"label": label, "advice": advice})
            break
    return flags


LANG_NAMES = {
    "en": "English", "fr": "French", "es": "Spanish", "zh-Hans": "Simplified Chinese", "zh-Hant": "Traditional Chinese",
    "pa": "Punjabi", "hi": "Hindi", "tl": "Tagalog", "ko": "Korean", "vi": "Vietnamese", "fa": "Persian (Farsi)", "ar": "Arabic",
}
RAG_REWRITE_MODEL = os.environ.get("RAG_REWRITE_MODEL", "gpt-4o-mini")
TRANSLATIONS_FILE = APP_DIR / "i18n" / "translations.json"
_translations = None


def ui_text(english, lang):
    """The app's own translation of a fixed English string (built by i18n/build_translations.py)."""
    global _translations
    if lang == "en":
        return english
    if _translations is None:
        try:
            _translations = json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _translations = {}
    return _translations.get(lang, {}).get("text", {}).get(english, english)


def language_note(lang):
    name = LANG_NAMES.get(lang, "English")
    return (f"LANGUAGE: The person chose {name} as the app language, so write in {name} by default. If they write or "
            "speak in a different language, reply in the language they're using instead. Use that same language for every "
            "text field you return (reply, headlines, lists, condition names, quick replies). Keep JSON keys and enum values "
            "exactly as specified, in English.")


def needs_english(text, lang):
    """Non-English messages are translated before the English-only keyword check and source search."""
    return lang != "en" or bool(re.search(r"[^\x00-\x7F\u00C0-\u024F\u2018-\u201D]", text))


def to_english(text):
    data = post_json({
        "model": RAG_REWRITE_MODEL,
        "temperature": 0,
        "max_tokens": 300,
        "messages": [{"role": "system", "content": "Translate the user's message into English. Output only the translation."},
                     {"role": "user", "content": text}],
    }, timeout=20)
    return data["choices"][0]["message"]["content"].strip()


def screen_message(text, lang="en"):
    """Keyword safety check that also works for other languages, by checking an English translation too.
    Labels stay in English (the app uses them as keys); the advice is shown in the app language."""
    flags = screen_red_flags(text)
    if not flags and text.strip() and needs_english(text, lang):
        try:
            flags = screen_red_flags(to_english(text))
        except Exception as e:
            print("Translation for safety check failed:", e)
    return [{**f, "advice": ui_text(f["advice"], lang)} for f in flags]


def message_text(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    return " ".join(part.get("text", "") for part in content or [] if part.get("type") == "text")


def profile_note(profile, patient):
    if patient != "self":
        return ("Who this consultation is about: someone OTHER than the account holder (e.g. a child, partner, or parent). "
                "No stored health profile applies to this person. Ask who the patient is and their age if not yet known, "
                "and collect any relevant history from scratch. Use only what is said in this conversation.")
    fields = [(k, str(v).strip()) for k, v in (profile or {}).items() if str(v or "").strip()]
    if not fields:
        return "Who this consultation is about: the account holder. No health profile was provided."
    return ("Who this consultation is about: the account holder. Their stored health profile (self-reported):\n"
            + "\n".join(f"- {k}: {v}" for k, v in fields))


def post_json(payload, timeout=90):
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


RAG_ENABLED = os.environ.get("MEDI_RAG", "1") != "0"
RAG_INDEX = APP_DIR / "rag" / "medi_index.json"
RAG_TOP_K = 5
RAG_MIN_SCORE = 0.3
_rag_cache = None


def rag_index():
    """Loads the prebuilt index once per server instance: passages plus unit-length embedding vectors."""
    global _rag_cache
    if _rag_cache is None:
        data = json.loads(RAG_INDEX.read_text(encoding="utf-8"))
        vectors = array("f")
        vectors.frombytes(base64.b64decode(data["vectors"]))
        _rag_cache = (data, vectors)
    return _rag_cache


def retrieve(query, k=RAG_TOP_K):
    """Returns the passages most similar to the query (cosine similarity), at most two per topic."""
    data, vectors = rag_index()
    dims = data["dims"]
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps({"model": data["model"], "input": query[:6000], "dimensions": dims}).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        q = json.load(resp)["data"][0]["embedding"]
    norm = sum(x * x for x in q) ** 0.5 or 1.0
    q = [x / norm for x in q]
    scored = sorted(
        ((sum(a * b for a, b in zip(q, vectors[i * dims:(i + 1) * dims])), i) for i in range(len(data["chunks"]))),
        reverse=True,
    )
    picked, per_topic = [], {}
    for score, i in scored:
        if score < RAG_MIN_SCORE or len(picked) == k:
            break
        chunk = data["chunks"][i]
        if per_topic.get(chunk["t"], 0) < 2:
            per_topic[chunk["t"]] = per_topic.get(chunk["t"], 0) + 1
            picked.append({**chunk, "score": round(score, 3)})
    return picked


def retrieval_query(messages, mode="health", hint=None, lang="en"):
    """Search text: what the person said recently plus English medical terms. Everyday words ("burning when I pee")
    and other languages often don't match the English reference text, so the terms come from the conditions Medi is
    already considering (or a hint from the app), or from a quick rewrite by a small model. English wellbeing messages
    match the reference text well, so they skip the rewrite."""
    said = "\n".join(reversed([message_text(m) for m in messages if m.get("role") == "user"][-3:]))
    foreign = needs_english(said, lang)
    if hint and not foreign:
        return f"{said}\nPossible conditions: {hint}"
    if mode == "wellbeing" and not foreign:
        return said
    for m in reversed(messages):
        if foreign or m.get("role") != "assistant":
            continue
        try:
            names = [c["name"] for c in json.loads(m["content"]).get("conditions", [])]
        except (ValueError, TypeError, KeyError):
            continue
        if names:
            return f"{said}\nPossible conditions: {', '.join(names)}"
    rewrite = post_json({
        "model": RAG_REWRITE_MODEL,
        "temperature": 0,
        "max_tokens": 80,
        "messages": [
            {"role": "system", "content": "Rewrite the person's words, in any language, as a short English medical search "
                                          "query: the clinical terms for their symptoms or concerns and the 2-4 most "
                                          "relevant topics to look up. One line, in English, no advice."},
            {"role": "user", "content": said},
        ],
    }, timeout=20)
    return f"{said}\n{rewrite['choices'][0]['message']['content'].strip()}"


def find_references(messages, mode="health", hint=None, lang="en"):
    """Retrieval never blocks a reply: if it fails, Medi answers without reference material."""
    try:
        return retrieve(retrieval_query(messages, mode, hint, lang))
    except Exception as e:
        print("Retrieval failed:", e)
        return []


def reference_note(passages):
    lines = [f"[{n}] {p['t']} (source: {p['s']})\n{p['x']}" for n, p in enumerate(passages, 1)]
    return "REFERENCE MATERIAL (retrieved for this conversation):\n\n" + "\n\n".join(lines)


def cited_sources(result, passages):
    """Turns the model's citation numbers into a deduplicated list of real sources the app can show."""
    sources, seen = [], set()
    for n in result.get("citations", []):
        if 1 <= n <= len(passages):
            p = passages[n - 1]
            if p["u"] not in seen:
                seen.add(p["u"])
                sources.append({"title": p["t"], "source": p["s"], "url": p["u"]})
    return sources


def consult_request(messages, profile, patient, rag=None, mode="health", lang="en"):
    """Builds the chat request for a turn: keyword safety check, retrieval, language, and the full prompt."""
    last_user = next((m for m in reversed(messages) if m.get("role") == "user"), {})
    flags = screen_message(message_text(last_user), lang) if last_user else []
    wellbeing = mode == "wellbeing"
    use_rag = RAG_ENABLED if rag is None else rag
    passages = find_references(messages, mode, lang=lang) if use_rag and last_user else []
    system = ((WELLBEING_PROMPT if wellbeing else SYSTEM_PROMPT) + "\n\n" + profile_note(profile, patient)
              + "\n\n" + language_note(lang))
    if passages:
        system += "\n\n" + reference_note(passages)
    if flags:
        system += ("\n\nSAFETY SCREENER ALERT for the latest message: " + "; ".join(f["label"] for f in flags) +
                   (". Follow the SAFETY rules now, and include 9-8-8 and 911 in your reply." if wellbeing else
                    ". Treat this as an emergency unless the patient clearly says it is not happening now, "
                    "and begin your reply with the emergency instruction."))
    payload = {
        "model": MODEL,
        "temperature": 0.5 if wellbeing else 0.3,
        "messages": [{"role": "system", "content": system}] + messages[-30:],
        "response_format": {"type": "json_schema", "json_schema": WELLBEING_SCHEMA if wellbeing else RESPONSE_SCHEMA},
    }
    return payload, flags, passages


MENTAL_HEALTH_FLAGS = {"Thoughts of suicide or self-harm", "Thoughts of harming someone else", "Possible abuse or an unsafe home"}
CRISIS_LINE = ("\n\nIf you're not safe or you're thinking about hurting yourself or someone else, you can call or text "
               "**9-8-8** any time (Canada and US). If you're in immediate danger, call **911**.")


def ensure_crisis_line(result, flags, lang="en"):
    """Guarantees every mental-health crisis reply contains 9-8-8 and 911, whatever the model wrote."""
    crisis = result.get("risk", {}).get("level") == "crisis" or any(f["label"] in MENTAL_HEALTH_FLAGS for f in flags)
    if crisis and not re.search(r"[9۹٩]\s*-?\s*[8۸٨]\s*-?\s*[8۸٨]", result["reply"]):
        result["reply"] += "\n\n" + ui_text(CRISIS_LINE.strip(), lang)
    return result


def consult(messages, profile, patient, rag=None, mode="health", lang="en"):
    payload, flags, passages = consult_request(messages, profile, patient, rag, mode, lang)
    result = ensure_crisis_line(json.loads(post_json(payload)["choices"][0]["message"]["content"]), flags, lang)
    result["safety_alerts"] = flags
    result["sources"] = cited_sources(result, passages)
    result["retrieved"] = passages
    return result


def sse(event):
    return f"data: {json.dumps(event)}\n\n".encode()


def consult_stream(messages, profile, patient, mode="health", lang="en"):
    """Same as consult, but yields server-sent events: safety alerts first, then the raw JSON as the model writes it
    (the reply field comes first, so the browser can show it word by word), then the finished result."""
    payload, flags, passages = consult_request(messages, profile, patient, mode=mode, lang=lang)
    yield sse({"type": "alerts", "alerts": flags})
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({**payload, "stream": True}).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    text = ""
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            for line in resp:
                line = line.strip()
                if not line.startswith(b"data: ") or line == b"data: [DONE]":
                    continue
                choices = json.loads(line[6:]).get("choices") or [{}]
                delta = choices[0].get("delta", {}).get("content")
                if delta:
                    text += delta
                    yield sse({"type": "delta", "text": delta})
        result = ensure_crisis_line(json.loads(text), flags, lang)
        result["safety_alerts"] = flags
        result["sources"] = cited_sources(result, passages)
        yield sse({"type": "done", "result": result})
    except urllib.error.HTTPError as e:
        detail = "the OpenAI API key is invalid or expired" if e.code == 401 else e.read().decode(errors="replace")[:300]
        yield sse({"type": "error", "error": f"OpenAI error {e.code}: {detail}"})
    except Exception as e:
        yield sse({"type": "error", "error": str(e)})


SUMMARY_PROMPT = """You are writing a concise visit summary of an AI health-assistant consultation that the patient can print and bring to a healthcare professional.
Based only on the consultation transcript and profile, write it in Markdown with these sections:
## Reason for visit
## History of present illness (onset, duration, progression, severity, associated symptoms, relevant negatives)
## Relevant history (conditions, medications, allergies, family history, pregnancy if relevant)
## Possibilities discussed (each marked as a probable explanation, possibility, or important to rule out; this is an AI-assisted preliminary impression, not a diagnosis; no percentages)
## Important unknowns
## Recommended level of care and next steps (one of: Emergency, Urgent care, Normal clinic, Home care)
## Questions to ask your clinician (3-5)
Never invent findings, history, test results, or sources. Write "Not discussed" when something is unknown. Keep it under 350 words."""


def summarize(messages, profile, patient, lang="en"):
    transcript = "\n".join(
        f"{'Patient' if m.get('role') == 'user' else 'Medi (AI)'}: {message_text(m)}" for m in messages
    )
    data = post_json({
        "model": MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SUMMARY_PROMPT + f"\nWrite the summary, including section headings, in {LANG_NAMES.get(lang, 'English')}."},
            {"role": "user", "content": profile_note(profile, patient) + "\n\nTranscript:\n" + transcript},
        ],
    })
    return {"summary": data["choices"][0]["message"]["content"].strip()}


REALTIME_MODEL = os.environ.get("REALTIME_MODEL", "gpt-realtime")
REALTIME_VOICE = os.environ.get("REALTIME_VOICE", "marin")
TTS_MODEL = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")
TTS_STYLE = ("Voice of a warm, calm, experienced family doctor talking with a patient in the exam room. "
             "Natural conversational pace with small pauses between thoughts, gentle and reassuring, clear pronunciation "
             "of medical terms. Not robotic, not overly cheerful, not like an announcer. If the text gives urgent "
             "instructions, say them firmly, clearly, and a little slower.")


def speak(text):
    """Turns a typed reply into natural speech with OpenAI's text-to-speech model. Returns MP3 bytes."""
    plain = re.sub(r"\*\*|__|`|^#+\s*", "", text, flags=re.M)
    plain = re.sub(r"^\s*[-*•]\s+", "", plain, flags=re.M)
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps({"model": TTS_MODEL, "voice": REALTIME_VOICE, "input": plain[:4000],
                         "instructions": TTS_STYLE, "response_format": "mp3"}).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()

VOICE_PROMPT = """

VOICE MODE (this conversation is spoken out loud, overriding the OUTPUT format above)
- You are talking with the person over a live voice call. Sound like a real, kind family doctor on the phone, not a narrator or a customer-service script.
- Speak naturally: a calm, unhurried pace, contractions, a warm and slightly lower-energy tone, natural pauses between thoughts, and short spoken acknowledgments like "Okay," "Got it," or "I'm sorry, that sounds rough." Vary your phrasing; don't open every turn the same way or repeat their words back mechanically.
- Keep each turn short: usually one to three sentences, then at most one question. Never read out lists, markdown, symbols, or long explanations; offer to say more instead.
- Speak the app language (see LANGUAGE) unless the person speaks another language; then match theirs.
- When the call starts, greet them briefly and naturally, in one or two sentences: you're Medi from Portal Medic 365, an AI health assistant rather than a doctor, and ask what's going on today.
- If the situation is serious, become calm, clear, and firm, and slow down slightly so instructions are easy to follow.
- For emergencies, say the action first in plain words: "Please call 911 right now." or "Please go to the nearest emergency room now."
- The app's assessment engine shows the level of care, possibilities, unknowns, next steps, and warning signs on the person's screen, and reports them to you in ASSESSMENT ENGINE system messages. Keep your spoken advice consistent with the latest one unless the person has since given new information, and never downplay an emergency it reports. You may tell them the details are on their screen.
- If a SAFETY SCREENER ALERT system message appears, follow it immediately.
- Before each of your replies, the app may add a REFERENCE MATERIAL system message with passages relevant to what they just said. Base medical facts on it, keep to general mainstream guidance where it doesn't cover something, and never read source numbers or titles aloud unless asked."""


WELLBEING_VOICE_PROMPT = """

VOICE MODE (this conversation is spoken out loud, overriding the OUTPUT format above)
- You are talking with the person over a live voice call. Sound like a calm, kind, grounded person who is really listening, not a narrator or a script.
- Speak softly and unhurriedly, with natural pauses. Use short spoken acknowledgments ("Mm, that's a lot," "Yeah," "I hear you") and leave room for them to talk.
- Keep each turn short: one to three sentences, then at most one gentle question. Never read out lists or symbols.
- When guiding breathing or grounding, go one slow step at a time and wait for them.
- Speak the app language (see LANGUAGE) unless the person speaks another language; then match theirs.
- When the call starts, greet them in one or two warm sentences: you're Medi, an AI wellbeing companion rather than a therapist, and this is a space to talk about whatever's on their mind. Then ask how they're doing.
- In a crisis, slow down, stay calm and caring, ask if they're safe right now, and say clearly that they can call or text 9-8-8, or call 911 if they're in immediate danger.
- If a SAFETY SCREENER ALERT or WELLBEING CHECK system message appears, follow it immediately.
- Before each of your replies, the app may add a REFERENCE MATERIAL system message with passages relevant to what they just said. Use it for any factual information or coping tips, never to label them, and never read source numbers or titles aloud."""


def voice_session(sdp, profile, patient, history, mode="health", lang="en"):
    """Starts a Realtime voice call through OpenAI's unified WebRTC interface and returns the SDP answer."""
    base = WELLBEING_PROMPT + WELLBEING_VOICE_PROMPT if mode == "wellbeing" else SYSTEM_PROMPT + VOICE_PROMPT
    instructions = base + "\n\n" + profile_note(profile, patient) + "\n\n" + language_note(lang)
    earlier = [f"{'Patient' if m.get('role') == 'user' else 'Medi'}: {message_text(m)}" for m in history[-20:]]
    if any(m.get("role") == "user" for m in history):
        instructions += ("\n\nEarlier in this same visit, by text chat (continue from here instead of greeting from scratch):\n"
                         + "\n".join(earlier))
    session = {
        "type": "realtime",
        "model": REALTIME_MODEL,
        "instructions": instructions,
        "audio": {
            "input": {
                "transcription": {"model": "gpt-4o-mini-transcribe"},
                # The app triggers each reply itself, after looking up reference passages for what was just said.
                "turn_detection": {"type": "semantic_vad", "create_response": False, "interrupt_response": True},
                "noise_reduction": {"type": "far_field"},
            },
            "output": {"voice": REALTIME_VOICE},
        },
    }
    boundary = "----medi" + os.urandom(12).hex()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"sdp\"\r\nContent-Type: application/sdp\r\n\r\n{sdp}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"session\"\r\nContent-Type: application/json\r\n\r\n"
        f"{json.dumps(session)}\r\n--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/realtime/calls",
        data=body,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return {"sdp": resp.read().decode()}


def send_stream(handler, status, events):
    """Writes server-sent events to the client as they're produced."""
    handler.send_response(status)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("X-Accel-Buffering", "no")
    handler.end_headers()
    for chunk in events:
        handler.wfile.write(chunk)
        handler.wfile.flush()


def make_handler(kind):
    """Builds the request handler class a Vercel Python function exposes as `handler`."""
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            status, body = handle_post(kind, raw)
            if hasattr(body, "__next__"):
                return send_stream(self, status, body)
            audio = isinstance(body, bytes)
            data = body if audio else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "audio/mpeg" if audio else "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def handle_post(kind, raw):
    """Shared request handling for the local server and the Vercel functions. Returns (status, json_obj)."""
    try:
        if len(raw) > MAX_BODY:
            return 413, {"error": "That upload is too large. Try a smaller photo."}
        if not API_KEY:
            return 500, {"error": "OPENAI_API_KEY is not configured on the server."}
        payload = json.loads(raw or b"{}")
        messages, profile = payload.get("messages", []), payload.get("profile", {})
        patient = "self" if payload.get("patient") == "self" else "other"
        mode = "wellbeing" if payload.get("mode") == "wellbeing" else "health"
        lang = payload.get("lang") if payload.get("lang") in LANG_NAMES else "en"
        if kind == "summary":
            return 200, summarize(messages, profile, patient, lang)
        if kind == "stream":
            return 200, consult_stream(messages, profile, patient, mode, lang)
        if kind == "speak":
            text = str(payload.get("text", "")).strip()
            return (200, speak(text)) if text else (400, {"error": "Nothing to read aloud."})
        if kind == "retrieve":
            hint = str(payload.get("hint") or "")
            passages = find_references(messages, mode, hint, lang) if RAG_ENABLED else []
            return 200, {"passages": [{"t": p["t"], "s": p["s"], "u": p["u"], "x": p["x"][:900]} for p in passages]}
        if kind == "screen":
            return 200, {"alerts": screen_message(str(payload.get("text", "")), lang)}
        if kind == "voice":
            if not str(payload.get("sdp", "")).strip():
                return 400, {"error": "Missing voice connection offer."}
            return 200, voice_session(payload["sdp"], profile, patient, messages, mode, lang)
        result = consult(messages, profile, patient, mode=mode, lang=lang)
        result.pop("retrieved", None)
        return 200, result
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        if e.code == 401:
            detail = "the OpenAI API key is invalid or expired"
        return 502, {"error": f"OpenAI error {e.code}: {detail}"}
    except Exception as e:
        return 500, {"error": str(e)}
