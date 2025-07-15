"""
Gradio UI setup and interface components for the Auto Parts Chatbot.
Handles the web interface, formatting functions, and app launch configuration.
"""

import gradio as gr
import re
from chatbot import AutoPartsChatbot


def format_response_with_copyable_skus(response):
    """Make SKUs copyable by wrapping in backticks"""
    sku_pattern = r'SKU: ([A-Za-z0-9-]+)'
    return re.sub(sku_pattern, r'SKU: `\1`', response)


# Global chatbot instance to maintain state
_chatbot_instance = None

def get_chatbot_instance():
    """Get or create the global chatbot instance"""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = AutoPartsChatbot()
    return _chatbot_instance

def chat_interface(message, history):
    """Main chat interface function"""
    chatbot = get_chatbot_instance()
    response = chatbot.process_message(message, history)
    return format_response_with_copyable_skus(response)


def create_interface():
    """Create and configure the Gradio interface"""
    # Modern chat widget
    theme = gr.themes.Soft(primary_hue="orange")

    demo = gr.ChatInterface(
        fn=chat_interface,
        theme=theme,
        title="Auto Parts Assistant",
        description="Find live stock, prices & policies for automotive parts",
        examples=[
            "Honda battery",
            "Toyota tires", 
            "Opening hours?",
            "Return policy",
            "Can you recommend parts for my car?"
        ],
        textbox=gr.Textbox(
            placeholder="Type your message here... (e.g., 'Honda battery', 'What are your hours?')",
            container=False
        ),
        chatbot=gr.Chatbot(
            show_copy_button=True,
            bubble_full_width=False
        ),
        additional_inputs=[],
        css=".contain { max-width: 800px !important; }"
    )

    # Add footer via CSS injection
    with demo:
        gr.HTML("""
            <script>
            setTimeout(() => {
                const footer = document.createElement('div');
                footer.className = 'footer';
                footer.innerHTML = '☎️ 1800-AUTO-PARTS | ✉️ support@autoparts.com.au';
                footer.style.cssText = 'position: fixed; bottom: 0; left: 0; right: 0; background: var(--background-fill-primary); padding: 8px; text-align: center; border-top: 1px solid var(--border-color-primary); font-size: 14px; z-index: 1000;';
                document.body.appendChild(footer);
            }, 1000);
            </script>
        """, visible=False)

    return demo


def launch_app():
    """Launch the Gradio application"""
    demo = create_interface()
    demo.launch(share=True, show_error=True)


#!/usr/bin/env python3

if __name__ == "__main__":
    launch_app()