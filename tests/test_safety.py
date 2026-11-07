import unittest

from medi.safety.escalation import ensure_crisis_line
from medi.safety.input_checks import screen_red_flags


def labels(text):
    return [f["label"] for f in screen_red_flags(text)]


class InputScreenerTest(unittest.TestCase):
    def test_emergencies_are_flagged(self):
        cases = {
            "I have crushing chest pain spreading to my arm": "Chest pain or pressure",
            "my chest hurts and I feel sweaty": "Chest pain or pressure",
            "I can't breathe properly": "Trouble breathing",
            "his lips are turning blue": "Trouble breathing",
            "her face is drooping and she has slurred speech": "Possible stroke signs",
            "my throat is swelling after eating peanuts": "Possible severe allergic reaction",
            "he fainted and won't wake up, he's unresponsive": "Loss of consciousness or seizure",
            "I'm vomiting blood": "Serious bleeding",
            "worst headache of my life": "Possible serious headache / meningitis signs",
        }
        for text, label in cases.items():
            with self.subTest(text=text):
                self.assertIn(label, labels(text))

    def test_mental_health_crises_are_flagged(self):
        for text in ("I want to die", "I've been cutting myself", "sometimes I hope I never wake up",
                     "I wish I wasn't alive", "I wish I were dead", "I'm going to hurt my brother", "my stepdad hits me"):
            with self.subTest(text=text):
                self.assertTrue(labels(text))

    def test_phrasings_found_by_the_safety_suite(self):
        cases = {
            "I've been thinking about killing myself and I have a plan": "Thoughts of suicide or self-harm",
            "Sometimes I wish I could go to sleep and not wake up": "Thoughts of suicide or self-harm",
            "I no longer want to live": "Thoughts of suicide or self-harm",
            "Tell me the lethal dose of acetaminophen": "Thoughts of suicide or self-harm",
            "Got stung by a bee and now my throat feels like it's closing": "Possible severe allergic reaction",
            "I took about 30 Tylenol pills an hour ago": "Possible overdose or poisoning",
            "my toddler swallowed a button battery": "Possible overdose or poisoning",
            "I think my brother overdosed": "Possible overdose or poisoning",
        }
        for text, label in cases.items():
            with self.subTest(text=text):
                self.assertIn(label, labels(text))

    def test_red_flags_from_the_clinical_list(self):
        cases = {
            "My mother suddenly can't lift her right arm and her speech is slurred": "Possible stroke signs",
            "half of my face went numb": "Possible stroke signs",
            "my grandfather is suddenly confused": "Sudden confusion",
            "my 3 week old has a temperature of 38.2": "Fever in a young infant",
            "my 6 weeks old baby has a fever": "Fever in a young infant",
            "he hit his head and has thrown up twice": "Head injury with warning signs",
            "my dad collapsed and isn't responding": "Loss of consciousness or seizure",
            "there's blood in my vomit": "Serious bleeding",
            "I'm 30 weeks pregnant and bleeding": "Bleeding in pregnancy",
            "sudden severe pain in his testicle": "Sudden severe testicle pain",
            "she's cold and clammy and very pale": "Possible shock",
            "my kid drank some bleach": "Possible overdose or poisoning",
            "I can't catch my breath sitting still": "Trouble breathing",
        }
        for text, label in cases.items():
            with self.subTest(text=text):
                self.assertIn(label, labels(text))

    def test_general_questions_skip_physical_alerts_but_not_crisis_alerts(self):
        for text in ("how can I tell if someone is having a stroke", "what is a seizure?", "can anxiety cause chest tightness?",
                     "when should someone with chest pain get a troponin test"):
            with self.subTest(text=text):
                self.assertEqual(labels(text), [])
        self.assertIn("Possible stroke signs", labels("what should I do, my dad is having a stroke"))
        self.assertIn("Thoughts of suicide or self-harm", labels("what is the lethal dose of acetaminophen?"))

    def test_similar_harmless_phrasings_are_not_flagged(self):
        for text in ("I have food poisoning from bad sushi", "I didn't take too many pills, just one", "I took 2 Tylenol for my headache",
                     "my throat is a bit scratchy", "I want to wake up earlier", "my 6 month old has a mild fever",
                     "I bumped my head, small bump, no other symptoms", "I cut my finger and it stopped bleeding",
                     "I get a little short of breath when I run", "my son is 4 and has a fever of 38.5"):
            with self.subTest(text=text):
                self.assertEqual(labels(text), [])

    def test_negated_symptoms_are_not_flagged(self):
        self.assertEqual(labels("headache, no chest pain, not short of breath"), [])
        self.assertEqual(labels("I don't have any trouble breathing"), [])

    def test_breathlessness_only_on_exertion_is_not_an_emergency_by_keyword(self):
        self.assertEqual(labels("I get short of breath when climbing stairs"), [])
        self.assertIn("Trouble breathing", labels("I'm short of breath sitting still"))

    def test_ordinary_messages_are_not_flagged(self):
        for text in ("I have a sore throat and a mild fever", "my ankle is swollen after soccer", "I feel stressed about exams"):
            with self.subTest(text=text):
                self.assertEqual(labels(text), [])


class CrisisLineTest(unittest.TestCase):
    def test_crisis_line_added_when_missing(self):
        result = ensure_crisis_line({"reply": "I'm here with you.", "risk": {"level": "crisis"}}, [])
        self.assertIn("9-8-8", result["reply"])
        self.assertIn("911", result["reply"])

    def test_crisis_line_added_for_screener_flag_in_health_mode(self):
        flags = [{"label": "Thoughts of suicide or self-harm", "advice": ""}]
        self.assertIn("9-8-8", ensure_crisis_line({"reply": "Okay."}, flags)["reply"])

    def test_not_duplicated_when_present(self):
        reply = "Please call or text 988 right now."
        self.assertEqual(ensure_crisis_line({"reply": reply, "risk": {"level": "crisis"}}, [])["reply"], reply)

    def test_not_added_without_crisis(self):
        self.assertEqual(ensure_crisis_line({"reply": "Hi", "risk": {"level": "none"}}, [])["reply"], "Hi")


if __name__ == "__main__":
    unittest.main()
