#!/usr/bin/env python3
"""
Unit tests for unknown intent polite redirect
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_off_scope_redirect():
    """'How is world peace?' triggers polite off-scope reply with steer-back"""
    bot = AutoPartsChatbot()
    
    # Set low confidence to trigger LLM redirect
    bot.clf_conf = 0.3
    
    response = bot.process_message("How is world peace?", [])
    
    # Should be polite and steer back to auto parts
    assert len(response) > 20  # Not just "didn't catch that"
    assert "didn't catch that" not in response.lower()

def test_help_menu_after_two_unknowns():
    """Help menu shows once after two unknown inputs"""
    bot = AutoPartsChatbot()
    
    # First unknown
    response1 = bot.process_message("gibberish1", [])
    assert "didn't catch that" in response1.lower()
    
    # Second unknown - should show help
    response2 = bot.process_message("gibberish2", [])
    assert "examples" in response2.lower()
    assert "Honda battery" in response2
    
    # Third unknown - should not show help again
    response3 = bot.process_message("gibberish3", [])
    assert "examples" not in response3.lower()

def test_oops_count_reset():
    """Oops count resets on recognized intent"""
    bot = AutoPartsChatbot()
    
    # Unknown input
    bot.process_message("gibberish", [])
    assert bot.oops_count == 1
    
    # Recognized intent should reset
    bot.process_message("Honda battery", [])
    assert bot.oops_count == 0

if __name__ == "__main__":
    pytest.main([__file__])