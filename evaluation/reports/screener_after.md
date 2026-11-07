# Safety screener evaluation (after)

Deterministic rules only (no AI model). English texts from the project's labeled datasets.

| | Count | Result |
|---|---|---|
| Should alert | 29 | caught 23 (79%) |
| Should not alert | 116 | false alarms 2 (2%) |

Missed by the rules (the AI model still assesses these):

- scenario 5 Appendicitis: I'm 19. My stomach pain started around my belly button yesterday and has moved to the lower right side. I have
- scenario 8 Diabetic ketoacidosis: My 14 year old has type 1 diabetes. Since yesterday he's been vomiting, extremely thirsty, peeing a lot, his b
- scenario 10 Ectopic pregnancy: I'm 28 and my period is 6 weeks late, and a home pregnancy test was positive. Now I have sharp pain low on my 
- scenario 15 Heat stroke: My coworker was working outside in 100F heat all afternoon. Now he's confused, his skin is hot and dry, he sto
- scenario 17 Carbon monoxide poisoning: Everyone in my family has had headaches, nausea, and dizziness for a few days. It's worse when we're at home w
- scenario 28 Preeclampsia: I'm 34 weeks pregnant. I have a bad headache, my face and hands are suddenly swollen, I'm seeing spots, and my

Unnecessary alerts:

- scenario 24 Pneumonia: I'm 65. I've had a cough with green phlegm for 5 days, a fever of 101.5F, I get short of b -> Chest pain or pressure, Trouble breathing
- query q15 (everyday): my nose has been bleeding for 15 minutes and won't stop -> Serious bleeding
