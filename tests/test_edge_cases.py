#!/usr/bin/env python3
"""
Unit tests for edge cases: toxic language and repeated queries
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_toxic_language():
    """Test polite de-escalation for toxic language"""
    bot = AutoPartsChatbot()
    
    toxic_messages = [
        "Hello mother fucker",
        "Are you stupid?",
        "This is fucking stupid",
        "You're an idiot"
    ]
    
    for message in toxic_messages:
        response = bot.process_message(message, [])
        
        # Should de-escalate politely
        assert "respectful" in response.lower()
        assert "help" in response.lower()
        # Should not echo the toxic language
        assert "fuck" not in response.lower()
        assert "stupid" not in response.lower()

def test_repeated_part_without_make():
    """Test loop guard for repeated part requests without vehicle make"""
    bot = AutoPartsChatbot()
    
    # First request for tires
    response1 = bot.process_message("I need tires", [])
    assert "which make" in response1.lower()
    
    # Second request for same part
    response2 = bot.process_message("My car needs tires", [])
    
    # Should trigger lead capture after repetition
    assert "call you" in response2.lower() or "help" in response2.lower()
    assert bot.awaiting_lead_capture == True

def test_repeated_part_different_category():
    """Test that different parts don't trigger loop guard"""
    bot = AutoPartsChatbot()
    
    # Request tires
    bot.process_message("I need tires", [])
    
    # Request different part - should not trigger loop guard
    response = bot.process_message("I need battery", [])
    
    # Should ask for make normally
    assert "which make" in response.lower()
    assert bot.awaiting_lead_capture == False

def test_toxic_detection_function():
    """Test toxic language detection function directly"""
    bot = AutoPartsChatbot()
    
    # Should detect toxic language
    assert bot.is_toxic("you're fucking stupid") == True
    assert bot.is_toxic("damn idiot") == True
    assert bot.is_toxic("what a moron") == True
    
    # Should not flag normal language
    assert bot.is_toxic("I need help") == False
    assert bot.is_toxic("Honda battery") == False
    assert bot.is_toxic("thank you") == False

def test_loop_guard_reset():
    """Test that loop guard resets properly"""
    bot = AutoPartsChatbot()
    
    # Trigger loop guard
    bot.process_message("I need tires", [])
    bot.process_message("My car needs tires", [])
    
    # Should be in lead capture mode
    assert bot.awaiting_lead_capture == True
    
    # Reset session
    bot.reset_session()
    
    # Should be back to normal
    assert bot.awaiting_lead_capture == False
    assert bot.pending_part_category == None
    assert bot.pending_part_count == 0

def test_part_with_vehicle_no_loop():
    """Test that providing vehicle with part doesn't trigger loop guard"""
    bot = AutoPartsChatbot()
    
    # Provide both vehicle and part
    response = bot.process_message("Honda tires", [])
    
    # Should search normally, not trigger loop guard
    assert "honda" in response.lower()
    assert "tire" in response.lower()
    assert bot.pending_part_count == 0

if __name__ == "__main__":
    pytest.main([__file__])