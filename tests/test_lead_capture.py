#!/usr/bin/env python3
"""
Unit tests for lead capture functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_lead_capture_state_management():
    """Test that lead capture 3-step flow works correctly"""
    bot = AutoPartsChatbot()
    
    # Trigger out of stock scenario
    response1 = bot.process_message("Honda battery", [])
    assert "sorry" in response1.lower() or "notify you" in response1.lower()
    
    if "notify you" in response1.lower():
        assert bot.awaiting_lead_capture == True
        
        # Step 1: User agrees to lead capture
        response2 = bot.process_message("yes", [])
        assert "name" in response2.lower()
        assert bot.lead_capture_step == 'name'
        
        # Step 2: User provides name
        response3 = bot.process_message("John Smith", [])
        assert "phone or email" in response3.lower()
        assert bot.lead_capture_step == 'contact'
        assert bot.lead_name == "John Smith"
        
        # Step 3: User provides contact
        response4 = bot.process_message("555-123-4567", [])
        assert "perfect" in response4.lower() or "thank" in response4.lower()
        assert bot.awaiting_lead_capture == False  # State should be cleared
        assert bot.lead_capture_step == None
        assert bot.lead_name == None

def test_unknown_intent_handling():
    """Test handling of gibberish and unknown inputs with improved loop guard"""
    bot = AutoPartsChatbot()
    
    # Test actual gibberish (not chitchat)
    response1 = bot.process_message("jjnjj", [])
    assert "didn't catch that" in response1.lower()
    
    # Second unknown should trigger help menu (threshold lowered to 2)
    response2 = bot.process_message("xyz123", [])
    assert "examples" in response2.lower() or "trouble understanding" in response2.lower()
    assert "Honda battery" in response2

def test_polite_chitchat_responses():
    """Test polite responses to simple chitchat"""
    bot = AutoPartsChatbot()
    
    # Test acknowledgements - these should be treated as chitchat now
    response1 = bot.process_message("ok", [])
    assert "sure" in response1.lower()
    assert "let me know" in response1.lower()
    
    response2 = bot.process_message("kk", [])
    assert "sure" in response2.lower()
    
    response3 = bot.process_message("thanks", [])
    assert "sure" in response3.lower() or "thanks" in response3.lower()

def test_faq_conversation_exit():
    """Test that FAQ responses don't immediately restart parts prompt"""
    bot = AutoPartsChatbot()
    
    # Ask FAQ question
    response1 = bot.process_message("What are your hours?", [])
    assert "8 am" in response1 or "Monday" in response1
    # Should not immediately ask for make/part
    assert "vehicle make" not in response1.lower()
    
    # Follow up with thanks should be handled politely
    response2 = bot.process_message("thanks", [])
    assert "sure" in response2.lower()

def test_honda_battery_search():
    """Test Honda battery search returns appropriate results"""
    bot = AutoPartsChatbot()
    
    # Test the actual search function
    parts = bot.search_parts("Honda", "Battery")
    # Should return empty since no Honda batteries in test data
    assert len(parts) == 0
    
    # Test fuzzy matching works
    normalized = bot.normalize_category("battries")
    assert normalized == "Battery"

if __name__ == "__main__":
    pytest.main([__file__])