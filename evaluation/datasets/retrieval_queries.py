"""Queries for the retrieval benchmark (dataset version r1).

All queries are synthetic, written for this project; none come from real users. "kind" groups them for reporting:
  scenario   the first message of each of the 50 triage scenarios
  everyday   symptoms described in everyday words
  education  questions about tests, medicines, screening, and prevention
  wellbeing  mental-health and wellbeing concerns (searched in Wellbeing mode)
  guideline  questions answered by the clinical guideline summaries
"""
from .scenarios import SCENARIOS

EXTRA = [
    ("everyday", "it burns when I pee and I keep needing to go"),
    ("everyday", "my son has red itchy dry patches in the creases of his elbows"),
    ("everyday", "I keep waking up three times a night to pee"),
    ("everyday", "my heart keeps skipping beats and fluttering"),
    ("everyday", "white patches in my baby's mouth that don't wipe off"),
    ("everyday", "my big toe is red, hot, and super painful, it started overnight"),
    ("everyday", "I get a burning feeling in my chest after almost every meal"),
    ("everyday", "itchy scalp and I saw tiny bugs in my daughter's hair"),
    ("everyday", "ringing in my ears that won't go away"),
    ("everyday", "painful cluster of blisters on my lip"),
    ("everyday", "I feel dizzy and lightheaded whenever I stand up quickly"),
    ("everyday", "my ankles are swollen at the end of every day"),
    ("everyday", "I haven't had a bowel movement in a week"),
    ("everyday", "I found a tick on me last week and now there's a bullseye rash"),
    ("everyday", "my nose has been bleeding for 15 minutes and won't stop"),
    ("everyday", "my fingers go numb and tingle at night, my wrist hurts from typing"),
    ("everyday", "sharp pain in my lower back that shoots down the back of my leg"),
    ("everyday", "my period is really heavy and lasts over a week"),
    ("everyday", "red sore eye with yellow crust when I wake up"),
    ("everyday", "my 6 month old has a fever of 39 C"),
    ("everyday", "itchy raised bumps all over after eating strawberries"),
    ("everyday", "my sunburn has blisters"),
    ("everyday", "got stung by a bee and my whole forearm is swelling"),
    ("everyday", "there's a lump in my neck that has been there for a month"),
    ("everyday", "yellow mucus and pressure in my cheeks for 10 days"),
    ("everyday", "I've had a dry tickly cough since I started lisinopril"),
    ("everyday", "I feel bloated and gassy all the time"),
    ("everyday", "my toddler swallowed a button battery"),
    ("education", "what is an A1C test"),
    ("education", "what does a high TSH result mean"),
    ("education", "is an LDL cholesterol of 190 high"),
    ("education", "how often should I get a mammogram"),
    ("education", "when should my child get the MMR vaccine"),
    ("education", "how is strep throat diagnosed"),
    ("education", "what are the side effects of metformin"),
    ("education", "can I take ibuprofen while pregnant"),
    ("education", "how much exercise do adults need each week"),
    ("education", "what's the difference between a cold and the flu"),
    ("education", "what are the signs of a concussion in a teenager"),
    ("education", "how can I tell if someone is having a stroke"),
    ("education", "my grandpa is getting more and more forgetful"),
    ("education", "at what age should I get a colonoscopy"),
    ("education", "is it safe to drink alcohol while taking antibiotics"),
    ("education", "what is sepsis"),
    ("education", "how do I treat a minor burn at home"),
    ("education", "signs of dehydration in a toddler"),
    ("wellbeing", "I can't stop worrying about everything and my heart races"),
    ("wellbeing", "I feel sad and tired all the time and nothing is fun anymore"),
    ("wellbeing", "exams are stressing me out so much I can't think"),
    ("wellbeing", "my mind races every night when I try to fall asleep"),
    ("wellbeing", "I've been drinking more and more to cope"),
    ("wellbeing", "I feel so lonely since I moved here"),
    ("wellbeing", "my mom died two months ago and I can't stop crying"),
    ("wellbeing", "I get panic attacks in crowded places"),
    ("wellbeing", "kids at school keep bullying me"),
    ("wellbeing", "I binge eat whenever I'm stressed"),
    ("wellbeing", "I've felt irritable and hopeless since having my baby"),
    ("wellbeing", "I keep having flashbacks and nightmares after the car accident"),
    ("wellbeing", "is it normal to feel really down every winter"),
    ("wellbeing", "my teenager is withdrawn and won't talk to us anymore"),
    ("wellbeing", "I vape every day and I want to quit"),
    ("wellbeing", "I think my friend is cutting herself"),
    ("wellbeing", "I'm burned out from caring for my dad who has dementia"),
    ("wellbeing", "I can't focus on anything at work, I'm always distracted"),
    ("wellbeing", "how can I calm down when I feel overwhelmed"),
    ("guideline", "what blood pressure counts as stage 2 hypertension"),
    ("guideline", "which antibiotics are recommended for community-acquired pneumonia"),
    ("guideline", "when is a statin recommended to lower cholesterol"),
    ("guideline", "what A1C target is recommended for most adults with diabetes"),
    ("guideline", "how is an acute asthma attack treated"),
    ("guideline", "how is a urinary tract infection in women treated"),
    ("guideline", "how is atrial fibrillation managed to prevent stroke"),
    ("guideline", "when should someone with chest pain get a troponin test"),
]

# Questions the knowledge base doesn't answer (specific doses, interactions, niche facts) or that aren't about health.
# They have no relevant topics; they test whether the evidence check notices that, and are left out of hit/recall.
OUT_OF_SCOPE = [
    "what's the right dose of semaglutide for weight loss",
    "can I take ashwagandha together with sertraline",
    "what is the half-life of lithium carbonate",
    "how do I change the brake pads on my car",
    "what's the capital of Australia",
    "is the Arexvy RSV vaccine safe if I have a pacemaker",
    "what are the exact macros for a keto diet",
    "how many milligrams of melatonin can a 4 year old take",
    "is it safe to fly 3 days after a laparoscopic appendectomy",
    "what is the CPT billing code for an ECG",
    "which is better for acne, tretinoin 0.025% or adapalene 0.1%",
    "write me a poem about the ocean",
]

QUERIES = ([{"qid": f"s{s['id']}", "kind": "scenario", "mode": "health", "text": s["message"]} for s in SCENARIOS]
           + [{"qid": f"q{n}", "kind": kind, "mode": "wellbeing" if kind == "wellbeing" else "health", "text": text}
              for n, (kind, text) in enumerate(EXTRA, 1)]
           + [{"qid": f"o{n}", "kind": "out_of_scope", "mode": "health", "text": text} for n, text in enumerate(OUT_OF_SCOPE, 1)])
