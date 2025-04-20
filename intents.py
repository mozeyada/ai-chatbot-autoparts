"""
intents.py  – simple keyword heuristics to label user messages
--------------------------------------------------------------
Returns one of:
    • "product_query"
    • "faq"
    • "lead"
    • "chitchat"
"""

import re

# basic keyword buckets
PRODUCT_WORDS   = {"brake", "filter", "pad", "oil", "engine", "alternator",
                   "belt", "battery", "plug", "part", "parts", "stock"}
FAQ_WORDS       = {"return", "refund", "ship", "shipping", "deliver",
                   "delivery", "hours", "open", "warranty", "policy"}
LEAD_WORDS      = {"contact", "phone", "call", "email", "speak", "human", "representative"}

# follow‑up phrases (e.g., "what else", "more options")
FOLLOWUP_WORDS  = {"else", "another", "more", "options", "anything"}

# one small regex to catch year model queries (e.g., 2018)
YEAR_RX = re.compile(r"\b(19|20)\d{2}\b")

def get_intent(msg: str) -> str:
    lower = msg.lower()

    # follow‑up like "what else?"
    if any(word in lower for word in FOLLOWUP_WORDS):
        return "product_query"

    # product query keywords or contains a 4‑digit year
    if any(word in lower for word in PRODUCT_WORDS) or YEAR_RX.search(lower):
        return "product_query"

    if any(word in lower for word in FAQ_WORDS):
        return "faq"

    if any(word in lower for word in LEAD_WORDS):
        return "lead"

    return "chitchat"
