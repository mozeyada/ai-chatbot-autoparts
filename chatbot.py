"""
chatbot.py  – Mistral‑7B‑Instruct (4‑bit) assistant
===================================================
• Loads product CSV + FAQ
• Uses mistralai/Mistral‑7B‑Instruct‑v0.2 with bitsandbytes 4‑bit quant
• Same slot‑memory and categorical filtering as before
• llm_reply() guarantees non‑empty outputs
"""

import json, re, os
from pathlib import Path
import pandas as pd
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          BitsAndBytesConfig, pipeline)

# --------------------------------------------------  Config & data
CFG = json.load(open("config.json"))
STORE_NAME      = CFG["STORE_NAME"]
WELCOME_MESSAGE = CFG["WELCOME_MESSAGE"]
CSV_PATH        = CFG["PRODUCT_DB_PATH"]
FAQ_PATH        = CFG["FAQ_PATH"]

df_parts = pd.read_csv(CSV_PATH)

import faq_handler
faq_data = faq_handler.load_faq(FAQ_PATH)

# --------------------------------------------------  Load Mistral‑7B
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"

print("⌛ Loading Mistral‑7B‑Instruct (4‑bit) … first run may take a few minutes.")

bnb_cfg = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype="float16",
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model     = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    device_map="auto",                # CPU or GPU if present
    quantization_config=bnb_cfg,
)

generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    do_sample=False,
    temperature=0.2,
    repetition_penalty=1.3,
    max_new_tokens=140,
)

STAGE_RX = re.compile(r"\[[^\]]{0,100}\]")    # strip “[pause]”, etc.

def llm_reply(system_prompt: str, user_msg: str, max_new: int = 60) -> str:
    prompt = f"{system_prompt}\nUser: {user_msg}\nAssistant:"
    raw = generator(
        prompt,
        max_new_tokens=max_new,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id,
    )[0]["generated_text"]

    txt = raw.split("Assistant:", 1)[-1]
    for tag in ("\nUser:", "\nAssistant:"):
        if tag in txt:
            txt = txt.split(tag, 1)[0]
    txt = STAGE_RX.sub("", txt).strip()
    if not txt:
        txt = "Could you clarify your question?"
    return txt

# --------------------------------------------------  Entity parsing
MAKES = ["honda","toyota","ford","nissan","mazda","hyundai","kia"]
MODEL_MAP = {
    "accord": "Accord", "civic": "Civic",
    "camry": "Camry", "corolla": "Corolla",
    "focus": "Focus", "elantra": "Elantra", "rio": "Rio",
}
CAT_RX = re.compile(
    r"(brake pads?|brakes?|filter|oil|engine oil|plug|alternator|belt|battery)",
    re.I,
)

def parse_entities(msg: str):
    lower = msg.lower()
    make  = next((m for m in MAKES if m in lower), None)
    model = next((v for k,v in MODEL_MAP.items() if k in lower), None)

    cat_match = CAT_RX.search(lower)
    category = None
    if cat_match:
        raw = cat_match.group(1).lower()
        if raw in ("oil","engine oil"):
            category = "Engine Oil"
        elif raw.startswith("brake"):
            category = "Brakes"
        else:
            category = raw.capitalize()
    return make, model, category

# --------------------------------------------------  Product answer
def list_categories_for_make(make):
    return ", ".join(sorted(
        df_parts.loc[df_parts["VehicleMake"].str.lower()==make.lower(),"Category"].unique()
    ))

def list_makes_for_category(cat):
    return ", ".join(sorted(
        df_parts.loc[df_parts["Category"].str.lower()==cat.lower(),"VehicleMake"].unique()
    ))

def answer_product_query(user_msg: str, ctx: dict) -> str|None:
    make, model, cat = parse_entities(user_msg)
    make  = make  or ctx.get("make")
    model = model or ctx.get("model")

    matches = df_parts.copy()
    if make:
        matches = matches[matches["VehicleMake"].str.lower()==make.lower()]
    if model:
        matches = matches[matches["VehicleModel"].str.lower()==model.lower()]
    if cat:
        matches = matches[matches["Category"].str.lower()==cat.lower()]

    # exclude SKUs already shown this session
    shown = set(ctx.get("shown_skus", []))
    if shown.any() if isinstance(shown, pd.Series) else shown:
        matches = matches[~matches["SKU"].isin(shown)]

    if not matches.empty:
        rows = matches.head(3).to_dict(orient="records")
        facts = " • ".join(
            f"{r['PartName']} (SKU {r['SKU']}, ${r['Price']}, {r['Availability']})"
            for r in rows
        )
        # remember context & shown SKUs
        ctx["make"], ctx["model"] = make, model
        ctx.setdefault("shown_skus", []).extend(r["SKU"] for r in rows)
        return f"I found these parts:\n{facts}\nNeed more options? Let me know."

    if make and not cat:
        cats = list_categories_for_make(make)
        if cats:
            return f"For {make.title()} we carry: {cats}. Which category interests you?"

    if cat and not make:
        makes = list_makes_for_category(cat)
        if makes:
            return f"We have {cat.lower()} for: {makes}. Which make & model?"

    return None   # triggers lead capture

def answer_faq(user_msg: str):
    qa = faq_handler.get_best_answer(faq_data, user_msg)
    if qa:
        sys = f"You are a helpful assistant for {STORE_NAME}. Use the policy below."
        return llm_reply(sys, user_msg + "\n\nPolicy:\n" + qa, max_new=80)

# --------------------------------------------------  Console test
def console_chat():
    ctx, awaiting = {}, False
    print(WELCOME_MESSAGE, "\n(type quit to exit)\n")
    from intents import get_intent
    while True:
        user = input("You: ").strip()
        if user.lower() in {"quit","exit"}: break
        if awaiting:
            print("Bot: Thanks! A specialist will email you shortly.\n")
            awaiting=False; continue
        intent = get_intent(user)
        if intent=="product_query":
            reply = answer_product_query(user, ctx) or (
                "I'm not seeing that part; can I get your email for a specialist?")
            if reply.startswith("I'm not seeing"):
                awaiting=True
        elif intent=="faq":
            reply = answer_faq(user) or (
                "I'm not sure—can I take your email so a parts expert can confirm?")
        else:
            reply = llm_reply(f"You are a friendly assistant for {STORE_NAME}.", user)
        print("Bot:", reply, "\n")

if __name__=="__main__":
    console_chat()
