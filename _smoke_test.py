import json
import re
import sys
import urllib.request

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from api._medi import screen_red_flags

print("screener:", [f["label"] for f in screen_red_flags("I have crushing chest pain and can't breathe")])
print("negated:", screen_red_flags("headache, no chest pain, not short of breath"))


def post(path, body):
    req = urllib.request.Request("http://127.0.0.1:8785" + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def show(title, r):
    print(f"\n===== {title} =====")
    print("REPLY:", r["reply"])
    print("TRIAGE:", r["triage"]["level"], "-", r["triage"]["headline"])
    for c in r["conditions"]:
        print(f"  [{c['status']}] {c['name']}")
    print("UNKNOWNS:", r["important_unknowns"])
    print("NEXT STEPS:", r["next_steps"])
    blob = json.dumps(r)
    print("contains a percentage?", bool(re.search(r"\d+\s?%", blob)))


profile = {"age": "45", "conditions": "type 2 diabetes", "medications": "metformin", "allergies": "penicillin"}

msgs = [{"role": "user", "content": "I've had a sore throat and fever of 101F for 2 days, no cough, swollen glands in my neck."}]
show("Adult sore throat (self, with profile)", post("/consult", {"messages": msgs, "patient": "self", "profile": profile}))

r = post("/consult", {"messages": [{"role": "user", "content": "My 2 year old has a fever of 102F since this morning. How much ibuprofen should I give?"}],
                      "patient": "other", "profile": profile})
show("Child fever + dosing question (someone else)", r)
print("mentions the account holder's diabetes/penicillin?", bool(re.search(r"diabet|penicillin|metformin", json.dumps(r), re.I)))

r = post("/consult", {"messages": [{"role": "user", "content": "My dad's face is drooping and his speech is slurred"}], "patient": "other", "profile": {}})
print("\nEMERGENCY TEST:", r["triage"]["level"], [a["label"] for a in r["safety_alerts"]])
print("first sentence:", r["reply"].split(".")[0])
