"""Held-out phrasings for the safety screener (dataset version screener-heldout-v1).

Written and committed before the November 2026 screener rule changes, so the new rules were not tuned to these texts.
They were written by the developer's team, so they are not independent of the project. All synthetic.
"""

SHOULD_ALERT = [
    "my husband's speech is suddenly garbled and his arm is weak",
    "half of my face went numb and I can't smile properly",
    "my grandmother is suddenly confused and doesn't know where she is",
    "my 3 week old feels hot, temperature 38.2",
    "my son fell off his bike, hit his head and has thrown up three times",
    "she hit her head on the ice and was knocked out for a few seconds",
    "I'm throwing up blood",
    "there's blood in my vomit and I feel faint",
    "my baby's lips look blue",
    "I can't catch my breath even sitting down",
    "my tongue is swelling after taking a new antibiotic",
    "my friend took a whole bottle of sleeping pills",
    "my dad collapsed and isn't responding",
    "my daughter is having a seizure right now",
    "sudden terrible pain in my testicle",
    "the bleeding from the cut won't stop after 20 minutes of pressure",
    "I want to end my life",
    "I'm going to kill myself tonight",
    "pressure in my chest and my jaw hurts",
    "worst headache I've ever had, it came on suddenly",
    "my kid drank some bleach",
    "he's breathing really fast, cold and clammy and very pale",
    "I'm 30 weeks pregnant and bleeding heavily",
    "my toddler swallowed some magnets",
]

SHOULD_NOT_ALERT = [
    "what are the warning signs of a heart attack?",
    "what is a seizure?",
    "how do I know if a cut needs stitches?",
    "my baby is 6 months old and has a mild fever",
    "I bumped my head on a cupboard, small bump, no other symptoms",
    "I get a little short of breath when I run",
    "can anxiety cause chest tightness?",
    "my throat is sore and scratchy",
    "I feel tired all the time",
    "my lips are chapped",
    "I have a mild headache from screen time",
    "how is a stroke treated?",
    "is it normal to feel dizzy when standing up fast?",
    "my son has a fever of 38.5 and is 4 years old",
    "I threw up once after eating bad sushi",
    "what's the best way to stop a nosebleed?",
    "I cut my finger cooking, it stopped bleeding",
    "my period is heavier than usual",
    "I'm stressed about my exams",
    "what happens during a colonoscopy?",
]
