"""
app.py – Gradio web interface for the auto‑parts chatbot
-------------------------------------------------------
• Uses helper functions from chatbot.py
• Remembers last make/model in session_state
• Captures user contact when needed
"""

import json
import gradio as gr

# --- import helper functions from chatbot.py ---------------------
from chatbot import (
    answer_product_query,
    answer_faq,
    llm_reply,
    parse_entities,        # entity parser
)

import intents             # simple rule‑based intent classifier

# ----------------------------------------------------------------
# Brand config
# ----------------------------------------------------------------
with open("config.json") as f:
    cfg = json.load(f)

STORE_NAME      = cfg["STORE_NAME"]
WELCOME_MESSAGE = cfg["WELCOME_MESSAGE"]

# ----------------------------------------------------------------
# Session memory for each chat
# ----------------------------------------------------------------
def new_session_state():
    return {"make": None, "model": None, "awaiting": False}

session_state = new_session_state()

# ----------------------------------------------------------------
# Chat response logic
# ----------------------------------------------------------------
def respond(user_msg, chat_history):
    global session_state
    st = session_state      # shortcut

    # ---------- If we’re waiting for contact info ----------
    if st["awaiting"]:
        # TODO: persist lead (CSV / email). For MVP we just thank them.
        bot_reply = "Thanks! A specialist will email you shortly."
        st["awaiting"] = False
        chat_history.append((user_msg, bot_reply))
        return chat_history, chat_history

    # ---------- Normal flow ----------
    intent = intents.get_intent(user_msg)

    if intent == "product_query":
        bot_reply = answer_product_query(user_msg, st)
        if bot_reply is None:
            bot_reply = (
                "I'm not seeing that part in my system. "
                "Could I get your name and email so a specialist can double‑check?"
            )
            st["awaiting"] = True
        else:
            # update memory with any new make/model mention
            make, model, _ = parse_entities(user_msg)
            if make:
                st["make"] = make
            if model:
                st["model"] = model

    elif intent == "faq":
        bot_reply = (
            answer_faq(user_msg)
            or "I'm not totally sure – may I take your email so a parts expert can confirm?"
        )

    elif intent == "lead":
        bot_reply = "Sure, please provide your name and email and we’ll get back to you."
        st["awaiting"] = True

    else:  # chitchat / fallback
        bot_reply = llm_reply(
            f"You are a friendly assistant for {STORE_NAME}.", user_msg
        )

    chat_history.append((user_msg, bot_reply))
    return chat_history, chat_history

# ----------------------------------------------------------------
# Gradio UI
# ----------------------------------------------------------------
with gr.Blocks(theme=gr.themes.Soft(primary_hue="orange")) as demo:
    gr.Markdown(f"### {STORE_NAME} AI Assistant\n{WELCOME_MESSAGE}")

    chatbox   = gr.Chatbot(height=420, show_copy_button=True)
    user_box  = gr.Textbox(
        placeholder="Ask about parts, pricing, shipping, opening hours…",
        scale=7,
    )
    clear_btn = gr.Button("Clear chat")

    user_box.submit(respond, [user_box, chatbox], [chatbox, chatbox])
    clear_btn.click(
        lambda: ([], new_session_state()), 
        None, 
        [chatbox, gr.State()],
        queue=False,
    )

if __name__ == "__main__":
    demo.launch(share=True)
