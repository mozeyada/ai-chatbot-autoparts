#!/usr/bin/env python3
"""
Unit tests for double fallback escalation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_double_fallback_escalation():
    """Send gibberish twice → bot should invite human help"""
    bot = AutoPartsChatbot()
    
    # First gibberish
    response1 = bot.process_message("xyzabc123", [])
    assert "didn't catch that" in response1.lower()
    
    # Second gibberish - should escalate
    response2 = bot.process_message("qwerty999", [])
    
    # Should escalate to human help
    assert "human" in response2.lower()
    assert "email or phone" in response2.lower()
    assert bot.awaiting_lead_capture == True

def test_fallback_reset_on_valid_input():
    """Test that fallback counter resets on valid input"""
    bot = AutoPartsChatbot()
    
    # First gibberish
    bot.process_message("gibberish1", [])
    assert bot.consecutive_fallbacks == 1
    
    # Valid input should reset counter
    bot.process_message("Honda battery", [])
    assert bot.consecutive_fallbacks == 0
    
    # Another gibberish should not escalate immediately
    response = bot.process_message("gibberish2", [])
    assert "human" not in response.lower()

def test_escalation_leads_to_capture():
    """Test that escalation properly triggers lead capture"""
    bot = AutoPartsChatbot()
    
    # Trigger double fallback
    bot.process_message("gibberish1", [])
    bot.process_message("gibberish2", [])
    
    # Should be in lead capture mode
    assert bot.awaiting_lead_capture == True
    
    # Next response should handle as lead capture
    response = bot.process_message("yes", [])
    assert "name" in response.lower()

def test_consecutive_fallback_counter():
    """Test consecutive fallback counter behavior"""
    bot = AutoPartsChatbot()
    
    # Should start at 0
    assert bot.consecutive_fallbacks == 0
    
    # First unknown
    bot.process_message("unknown1", [])
    assert bot.consecutive_fallbacks == 1
    
    # Second unknown should reset and escalate
    bot.process_message("unknown2", [])
    assert bot.consecutive_fallbacks == 0  # Reset after escalation

if __name__ == "__main__":
    pytest.main([__file__])