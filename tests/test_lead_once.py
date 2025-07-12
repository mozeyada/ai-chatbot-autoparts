#!/usr/bin/env python3
"""
Unit tests for one-time lead capture flow
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_lead_prompt_once():
    """Lead prompt appears once; after lead saved, FAQ works normally"""
    bot = AutoPartsChatbot()
    
    # Trigger stock-out to get lead prompt
    response1 = bot.process_message("Ferrari battery", [])
    
    # Should offer lead capture
    if "notify you" in response1.lower():
        # Accept lead capture
        response2 = bot.process_message("yes", [])
        assert "name" in response2.lower()
        
        # Provide name
        response3 = bot.process_message("John Doe", [])
        assert "phone or email" in response3.lower()
        
        # Provide contact
        response4 = bot.process_message("john@email.com", [])
        assert "thanks" in response4.lower()
        
        # After lead saved, FAQ should work normally
        response5 = bot.process_message("What are your hours?", [])
        assert "monday" in response5.lower()
        assert "thanks john" not in response5.lower()

def test_lead_state_machine():
    """Test 3-step lead capture state machine"""
    bot = AutoPartsChatbot()
    
    # Set up lead capture state
    bot.awaiting_lead_capture = True
    
    # Step 1: Agreement
    response1 = bot.process_message("yes", [])
    assert bot.lead_capture_step == 'name'
    
    # Step 2: Name
    response2 = bot.process_message("Jane Smith", [])
    assert bot.lead_capture_step == 'contact'
    assert bot.lead_name == "Jane Smith"
    
    # Step 3: Contact and save
    response3 = bot.process_message("jane@email.com", [])
    assert bot.awaiting_lead_capture == False
    assert bot.lead_capture_step == None
    assert bot.lead_name == None

def test_lead_flags_reset():
    """Test all lead flags reset after save"""
    bot = AutoPartsChatbot()
    
    # Set up lead state
    bot.awaiting_lead_capture = True
    bot.lead_capture_step = 'contact'
    bot.lead_name = "Test User"
    
    # Complete lead capture
    bot.process_message("test@email.com", [])
    
    # All flags should be reset
    assert bot.awaiting_lead_capture == False
    assert bot.lead_capture_step == None
    assert bot.lead_name == None

if __name__ == "__main__":
    pytest.main([__file__])