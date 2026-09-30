"""The README's example requests, for profile.py."""

def q(text):
    return {"type": "noul", "instructions": text}


ORDER = {"item": "wireless mouse", "delivered": "5 days ago", "customer_message": "The box arrived empty. This is the second time!"}
REQS = {
    "short": {"model": "jev-latest", "state": "Help! My payouts have been failing for 3 days.", "questions": {"q": q("Does this convey urgency?")}},
    "long": {"model": "jev-latest", "state": ("Order 55120. Customer reports the parcel arrived with the seal broken and one of three items missing. " * 8).strip(),
             "questions": {"q": q("Should the customer receive a refund for the missing item?")}},
    "1q": {"model": "jev-latest", "state": ORDER, "questions": {"refund": q("Our policy refunds items reported missing within 30 days of delivery. Should this customer get a refund?")}},
    "3q": {"model": "jev-latest", "state": ORDER, "questions": {
        "refund": q("Our policy refunds items reported missing within 30 days of delivery. Should this customer get a refund?"),
        "upset": q("Is the customer upset?"), "wrong_item": q("Does the customer say they received the wrong item?")}},
}
