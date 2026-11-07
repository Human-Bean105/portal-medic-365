# Safety screener evaluation (before)

Deterministic rules only (no AI model). English texts from the project's labeled datasets.

| | Count | Result |
|---|---|---|
| Should alert | 29 | caught 17 (59%) |
| Should not alert | 116 | false alarms 4 (3%) |

Missed by the rules (the AI model still assesses these):

- scenario 1 Concussion with red flags: I'm 17. I got hit in the head playing football about 2 hours ago and blacked out for maybe a minute. I've thro
- scenario 3 Stroke: My 70 year old mother suddenly can't lift her right arm and her speech is slurred. It started about 20 minutes
- scenario 5 Appendicitis: I'm 19. My stomach pain started around my belly button yesterday and has moved to the lower right side. I have
- scenario 8 Diabetic ketoacidosis: My 14 year old has type 1 diabetes. Since yesterday he's been vomiting, extremely thirsty, peeing a lot, his b
- scenario 9 Fever in a newborn: My baby is 6 weeks old and has a rectal temperature of 100.8F. She's feeding a bit less than usual.
- scenario 10 Ectopic pregnancy: I'm 28 and my period is 6 weeks late, and a home pregnancy test was positive. Now I have sharp pain low on my 
- scenario 13 Testicular torsion: My 15 year old son woke up 2 hours ago with sudden severe pain in one testicle. It's swollen and he's vomiting
- scenario 14 Upper GI bleed: I take ibuprofen every day for my back. Today I vomited something that looked like coffee grounds, my stools a
- scenario 15 Heat stroke: My coworker was working outside in 100F heat all afternoon. Now he's confused, his skin is hot and dry, he sto
- scenario 16 Sepsis: My 75 year old father was being treated for a urinary infection. Today he has a 102F fever, he's shaking, brea
- scenario 17 Carbon monoxide poisoning: Everyone in my family has had headaches, nausea, and dizziness for a few days. It's worse when we're at home w
- scenario 28 Preeclampsia: I'm 34 weeks pregnant. I have a bad headache, my face and hands are suddenly swollen, I'm seeing spots, and my

Unnecessary alerts:

- scenario 24 Pneumonia: I'm 65. I've had a cough with green phlegm for 5 days, a fever of 101.5F, I get short of b -> Chest pain or pressure, Trouble breathing
- query q40 (education): how can I tell if someone is having a stroke -> Possible stroke signs
- query q72 (guideline): how is atrial fibrillation managed to prevent stroke -> Possible stroke signs
- query q73 (guideline): when should someone with chest pain get a troponin test -> Chest pain or pressure
