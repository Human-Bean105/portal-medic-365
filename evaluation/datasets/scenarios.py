"""50 test vignettes for Medi.

Each scenario is a classic, textbook presentation. "accept" lists the levels of care
(emergency, urgent_care, clinic, home_care) a family physician would consider appropriate; the first entry is the ideal answer. "expected" is the textbook condition and "aliases"
are other names that count as the same answer. Ground truth is based on standard clinical teaching and has not
been reviewed by a licensed clinician.
"""

S = []


def add(sid, group, title, message, accept, expected, aliases=(), patient="self"):
    S.append({"id": sid, "group": group, "title": title, "message": message, "patient": patient,
              "accept": list(accept), "expected": expected, "aliases": list(aliases)})


# ---------------- Emergencies ----------------
add(1, "Emergency", "Concussion with red flags",
    "I'm 17. I got hit in the head playing football about 2 hours ago and blacked out for maybe a minute. "
    "I've thrown up twice since then and my headache keeps getting worse.",
    ["emergency"], "Concussion / traumatic brain injury", ["concussion", "traumatic brain injury", "intracranial bleed", "brain bleed", "head injury"])
add(2, "Emergency", "Heart attack",
    "I'm a 58 year old man. For the last 30 minutes I've had a crushing pressure in my chest that spreads to my "
    "left arm and jaw. I'm sweaty and feel sick to my stomach.",
    ["emergency"], "Heart attack (acute coronary syndrome)", ["myocardial infarction", "acute coronary syndrome", "heart attack", "angina"])
add(3, "Emergency", "Stroke",
    "My 70 year old mother suddenly can't lift her right arm and her speech is slurred. It started about 20 minutes ago.",
    ["emergency"], "Stroke", ["stroke", "transient ischemic attack", "TIA", "cerebrovascular accident"], patient="other")
add(4, "Emergency", "Anaphylaxis",
    "I just ate shrimp at a restaurant and now my lips are swelling, my throat feels tight, I have hives all over, "
    "and I'm wheezing.",
    ["emergency"], "Anaphylaxis", ["anaphylaxis", "severe allergic reaction"])
add(5, "Emergency", "Appendicitis",
    "I'm 19. My stomach pain started around my belly button yesterday and has moved to the lower right side. "
    "I have a fever of 100.8F, I threw up, and it hurts more when I walk or cough.",
    ["emergency", "urgent_care"], "Appendicitis", ["appendicitis"])
add(6, "Emergency", "Bacterial meningitis",
    "I'm a 20 year old college student. I have a 103F fever, a terrible headache, a stiff neck, light hurts my eyes, "
    "and there's a purple rash on my legs that doesn't fade when I press a glass on it.",
    ["emergency"], "Meningitis (possibly meningococcal)", ["meningitis", "meningococcal", "meningococcemia", "sepsis"])
add(7, "Emergency", "Pulmonary embolism",
    "I'm 35 and on birth control pills. I got off a 12 hour flight yesterday. Today I have sudden sharp chest pain "
    "that's worse when I breathe in, I'm short of breath, and my left calf is swollen and sore.",
    ["emergency"], "Pulmonary embolism / blood clot", ["pulmonary embolism", "blood clot", "deep vein thrombosis", "DVT"])
add(8, "Emergency", "Diabetic ketoacidosis",
    "My 14 year old has type 1 diabetes. Since yesterday he's been vomiting, extremely thirsty, peeing a lot, his "
    "breath smells fruity, he's breathing fast, and his glucose meter just says HI.",
    ["emergency"], "Diabetic ketoacidosis (DKA)", ["diabetic ketoacidosis", "DKA", "ketoacidosis"], patient="other")
add(9, "Emergency", "Fever in a newborn",
    "My baby is 6 weeks old and has a rectal temperature of 100.8F. She's feeding a bit less than usual.",
    ["emergency", "urgent_care"], "Fever in a young infant (possible serious infection)",
    ["serious bacterial infection", "sepsis", "infection", "neonatal fever", "urinary tract infection", "meningitis"], patient="other")
add(10, "Emergency", "Ectopic pregnancy",
    "I'm 28 and my period is 6 weeks late, and a home pregnancy test was positive. Now I have sharp pain low on my "
    "left side, some spotting, I feel dizzy, and my shoulder hurts.",
    ["emergency"], "Ectopic pregnancy", ["ectopic pregnancy"])
add(11, "Emergency", "Suicidal crisis",
    "I've been thinking about ending my life. I've been saving up pills and I don't really see the point anymore.",
    ["emergency"], "Suicidal crisis (mental health emergency)", ["suicid", "depression", "mental health crisis", "crisis"])
add(12, "Emergency", "Severe asthma attack",
    "I have asthma. I've used my rescue inhaler 4 times in the last hour and it isn't helping. I can only say a few "
    "words at a time and my lips look a bit blue.",
    ["emergency"], "Severe asthma attack", ["asthma exacerbation", "asthma attack", "status asthmaticus", "severe asthma"])
add(13, "Emergency", "Testicular torsion",
    "My 15 year old son woke up 2 hours ago with sudden severe pain in one testicle. It's swollen and he's vomiting.",
    ["emergency"], "Testicular torsion", ["testicular torsion", "torsion"], patient="other")
add(14, "Emergency", "Upper GI bleed",
    "I take ibuprofen every day for my back. Today I vomited something that looked like coffee grounds, my stools "
    "are black and tarry, and I get dizzy when I stand up.",
    ["emergency"], "Upper GI bleeding (e.g. bleeding stomach ulcer)", ["gastrointestinal bleed", "GI bleed", "peptic ulcer", "ulcer", "bleeding"])
add(15, "Emergency", "Heat stroke",
    "My coworker was working outside in 100F heat all afternoon. Now he's confused, his skin is hot and dry, he "
    "stopped sweating, and his temperature is 104F.",
    ["emergency"], "Heat stroke", ["heat stroke", "heatstroke", "hyperthermia"], patient="other")
add(16, "Emergency", "Sepsis",
    "My 75 year old father was being treated for a urinary infection. Today he has a 102F fever, he's shaking, "
    "breathing fast, his heart is racing, and he's very confused.",
    ["emergency"], "Sepsis", ["sepsis", "urosepsis", "septic"], patient="other")
add(17, "Emergency", "Carbon monoxide poisoning",
    "Everyone in my family has had headaches, nausea, and dizziness for a few days. It's worse when we're at home "
    "with the gas heater on and gets better when we leave the house.",
    ["emergency"], "Carbon monoxide poisoning", ["carbon monoxide", "CO poisoning"])

# ---------------- Urgent / same-day ----------------
add(18, "Urgent", "Strep throat",
    "I'm 16. I have a 102F fever, a really sore throat, white patches on my tonsils, and swollen tender glands in my "
    "neck. I don't have a cough.",
    ["urgent_care", "clinic"], "Strep throat", ["strep", "streptococcal pharyngitis", "tonsillitis", "pharyngitis"])
add(19, "Urgent", "Bladder infection (UTI)",
    "I'm a 30 year old woman. For 2 days it burns when I pee, I need to go all the time, and I feel urgency. "
    "No fever, no back pain, and I'm not pregnant.",
    ["urgent_care", "clinic"], "Urinary tract infection (cystitis)", ["urinary tract infection", "UTI", "cystitis", "bladder infection"])
add(20, "Urgent", "Kidney infection",
    "I'm 25. I've had burning when I pee for a few days and now I have a 102F fever, pain in my right side and back, "
    "and I threw up this morning.",
    ["urgent_care", "emergency"], "Kidney infection (pyelonephritis)", ["pyelonephritis", "kidney infection"])
add(21, "Urgent", "Kidney stone",
    "I'm a 40 year old man. I suddenly got severe cramping pain in my left side that goes down to my groin. It comes "
    "in waves, I can't sit still, and my pee looks pink.",
    ["urgent_care", "emergency"], "Kidney stone", ["kidney stone", "renal colic", "nephrolithiasis", "ureteral stone"])
add(22, "Urgent", "Cellulitis",
    "I scraped my shin 3 days ago. Now there's a red, warm, swollen patch around it that's getting bigger, and I have "
    "a low fever of 100.4F.",
    ["urgent_care"], "Cellulitis (skin infection)", ["cellulitis", "skin infection"])
add(23, "Urgent", "Possible ankle fracture",
    "I rolled my ankle playing basketball an hour ago. It's very swollen, I can't put any weight on it, and the bony "
    "bump on the outside of my ankle is really tender to touch.",
    ["urgent_care"], "Ankle fracture (or severe sprain)", ["fracture", "broken", "sprain"])
add(24, "Urgent", "Pneumonia",
    "I'm 65. I've had a cough with green phlegm for 5 days, a fever of 101.5F, I get short of breath walking around "
    "the house, and my chest hurts when I take a deep breath.",
    ["urgent_care", "emergency"], "Pneumonia", ["pneumonia", "chest infection", "lower respiratory tract infection"])
add(25, "Urgent", "Ear infection in a child",
    "My 3 year old has had a cold for a few days. Since last night he's been pulling at his right ear, he's fussy, "
    "and he has a 101F fever.",
    ["urgent_care", "clinic"], "Middle ear infection (otitis media)", ["otitis media", "ear infection"], patient="other")
add(26, "Urgent", "Shingles",
    "I'm 62. Two days ago I had burning and tingling on the left side of my chest, and now there's a painful "
    "blistering rash in a band on just that side.",
    ["urgent_care", "clinic"], "Shingles (herpes zoster)", ["shingles", "herpes zoster", "zoster"])
add(27, "Urgent", "Gout",
    "I'm a 50 year old man. I woke up with my big toe extremely painful, red, hot, and swollen. I can't even stand "
    "the bedsheet touching it. I had a lot of beer and steak last night.",
    ["urgent_care", "clinic"], "Gout", ["gout"])
add(28, "Urgent", "Preeclampsia",
    "I'm 34 weeks pregnant. I have a bad headache, my face and hands are suddenly swollen, I'm seeing spots, and my "
    "blood pressure at the pharmacy was 160/105.",
    ["emergency", "urgent_care"], "Preeclampsia", ["preeclampsia", "pre-eclampsia", "eclampsia", "HELLP"])
add(29, "Urgent", "Dehydration in a toddler",
    "My 2 year old has been vomiting and had diarrhea for 2 days. She's had fewer wet diapers today and her lips "
    "look dry, but she's still alert and playing a little.",
    ["urgent_care"], "Gastroenteritis with dehydration", ["dehydration", "gastroenteritis", "stomach bug"], patient="other")
add(30, "Urgent", "Eye injury from metal",
    "I was grinding metal without safety glasses and something flew into my eye. It hurts, it's watering a lot, "
    "and light bothers it.",
    ["urgent_care", "emergency"], "Corneal foreign body / corneal abrasion", ["foreign body", "corneal abrasion", "corneal injury", "scratched cornea"])
add(31, "Urgent", "Mononucleosis",
    "I'm 17. I've been exhausted for 2 weeks, with a sore throat, fever, swollen glands in my neck, and some "
    "discomfort under my left ribs.",
    ["urgent_care", "clinic"], "Infectious mononucleosis (mono)", ["mononucleosis", "mono", "Epstein-Barr", "glandular fever"])
add(32, "Urgent", "Minor head bump",
    "I'm 30. I bumped my head on a kitchen cabinet an hour ago. I didn't black out. I have a small bump and a mild "
    "headache but otherwise feel completely normal.",
    ["home_care", "clinic"], "Minor head injury (no red flags)", ["minor head injury", "head bump", "scalp", "contusion", "bump", "mild head injury", "concussion"])

# ---------------- Routine appointment ----------------
add(33, "Routine", "Underactive thyroid",
    "I'm a 45 year old woman. Over the past few months I've been tired all the time, gained weight, always feel cold, "
    "my skin is dry, I'm constipated, and my hair is thinning.",
    ["clinic"], "Hypothyroidism", ["hypothyroidism", "underactive thyroid", "Hashimoto"])
add(34, "Routine", "Type 2 diabetes",
    "I'm 48 and my dad has diabetes. For about 2 months I've been really thirsty, peeing a lot, my vision is blurry "
    "at times, and I've lost weight without trying.",
    ["clinic", "urgent_care"], "Type 2 diabetes", ["diabetes", "hyperglycemia", "high blood sugar"])
add(35, "Routine", "Iron-deficiency anemia",
    "I'm 32 and have very heavy periods. I've been tired, short of breath on the stairs, people say I look pale, "
    "and I keep craving ice.",
    ["clinic"], "Iron-deficiency anemia", ["anemia", "anaemia", "iron deficiency"])
add(36, "Routine", "Acid reflux (GERD)",
    "For a few months I get a burning feeling in my chest after meals, it's worse when I lie down, and I get a sour "
    "taste in my mouth. It never happens with exercise.",
    ["clinic", "home_care"], "Gastroesophageal reflux disease (GERD)", ["reflux", "GERD", "heartburn", "gastroesophageal"])
add(37, "Routine", "High blood pressure",
    "I'm 52. My home blood pressure readings have been around 150/95 several times this month. I feel fine and have "
    "no headaches or chest pain.",
    ["clinic"], "Hypertension (high blood pressure)", ["hypertension", "high blood pressure"])
add(38, "Routine", "Depression",
    "For the past 2 months I've felt down almost every day, I've lost interest in things I used to enjoy, and I sleep "
    "badly. I'm not having any thoughts of hurting myself.",
    ["clinic", "urgent_care"], "Depression", ["depression", "depressive"])
add(39, "Routine", "Generalized anxiety",
    "For about 6 months I've been worrying constantly about everything, I feel restless and tense, my muscles ache, "
    "and I have trouble falling asleep. No thoughts of self-harm.",
    ["clinic"], "Generalized anxiety disorder", ["anxiety"])
add(40, "Routine", "Irritable bowel syndrome",
    "I'm a 26 year old woman. For months I've had crampy belly pain that gets better after I go to the bathroom, and I "
    "switch between constipation and diarrhea. No blood in my stool and no weight loss.",
    ["clinic"], "Irritable bowel syndrome (IBS)", ["irritable bowel", "IBS"])
add(41, "Routine", "Carpal tunnel syndrome",
    "I type all day at work. My thumb, index, and middle fingers on my right hand go numb and tingly, and it's worst "
    "at night. It's been going on for a couple of months.",
    ["clinic", "home_care"], "Carpal tunnel syndrome", ["carpal tunnel", "median nerve"])
add(42, "Routine", "Eczema in a child",
    "My 5 year old has itchy, dry, red patches in the creases of her elbows and behind her knees. She also has hay "
    "fever. It comes and goes.",
    ["clinic", "home_care"], "Eczema (atopic dermatitis)", ["eczema", "atopic dermatitis", "dermatitis"], patient="other")
add(43, "Routine", "Typical migraine",
    "I've had migraines for years. Today I saw zigzag lines for 20 minutes, then got a throbbing headache on one side "
    "with nausea and light sensitivity. It feels exactly like my usual ones.",
    ["home_care", "clinic"], "Migraine with aura", ["migraine"])
add(44, "Routine", "Plantar fasciitis",
    "I'm a runner. My heel hurts the most with my first steps in the morning and it eases up after I walk a bit. "
    "It's been about 3 weeks.",
    ["home_care", "clinic"], "Plantar fasciitis", ["plantar fasciitis", "plantar fasciopathy"])

# ---------------- Home care ----------------
add(45, "Home care", "Common cold",
    "For 2 days I've had a runny nose, sneezing, a mild sore throat, and a temperature of 99.5F. I'm eating and "
    "drinking fine.",
    ["home_care"], "Common cold (viral upper respiratory infection)", ["common cold", "cold", "upper respiratory", "viral"])
add(46, "Home care", "Tension headache",
    "At the end of a stressful workday where I skipped lunch, I got a dull, tight, band-like headache around my "
    "forehead. No other symptoms.",
    ["home_care"], "Tension-type headache", ["tension"])
add(47, "Home care", "Mild sunburn",
    "I spent the afternoon at the beach without sunscreen. My shoulders are red and sore but there are no blisters, "
    "and I feel fine otherwise.",
    ["home_care"], "Sunburn (first-degree)", ["sunburn"])
add(48, "Home care", "Lower back strain",
    "I hurt my lower back lifting heavy boxes yesterday. It's sore and stiff, but I have no numbness, no leg weakness, "
    "and no problems with my bladder or bowels. I can walk fine.",
    ["home_care", "clinic"], "Lower back muscle strain", ["strain", "sprain", "mechanical back pain", "lumbar", "muscle"])
add(49, "Home care", "Stomach bug",
    "I've had vomiting and diarrhea since last night, and a few coworkers had the same thing. I'm keeping water down, "
    "there's no blood, and I'm peeing normally.",
    ["home_care"], "Viral gastroenteritis", ["gastroenteritis", "stomach bug", "stomach flu", "norovirus", "food poisoning"])
add(50, "Home care", "Seasonal allergies",
    "Every spring I get itchy watery eyes, lots of sneezing, and a clear runny nose. No fever. It's happening again now.",
    ["home_care", "clinic"], "Seasonal allergic rhinitis (hay fever)", ["allergic rhinitis", "hay fever", "allergies", "seasonal allergy"])

SCENARIOS = S
assert len(SCENARIOS) == 50 and len({s["id"] for s in SCENARIOS}) == 50
