#!/usr/bin/env python3
"""
Unit tests for enhanced chitchat patterns
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chatbot import AutoPartsChatbot

def test_how_is_your_week():
    """Test 'How is your week?' returns friendly chitchat, not unknown"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("How is your week?", [])
    
    # Should return friendly chitchat response
    assert "things are going well" in response.lower()
    assert "thanks for asking" in response.lower()
    assert "auto parts" in response.lower()
    
    # Should NOT be unknown response
    assert "didn't catch that" not in response.lower()
    assert "having trouble" not in response.lower()

def test_hows_your_week():
    """Test 'How's your week?' with contraction"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("How's your week?", [])
    
    # Should return friendly chitchat response
    assert "things are going well" in response.lower()
    assert "thanks for asking" in response.lower()

def test_how_are_things():
    """Test 'How are things?' returns chitchat response"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("How are things?", [])
    
    # Should return friendly chitchat response
    assert "things are going well" in response.lower()
    assert "auto parts" in response.lower()

def test_hows_it_going():
    """Test 'How's it going?' returns chitchat response"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("How's it going?", [])
    
    # Should return friendly chitchat response
    assert "things are going well" in response.lower()
    assert "help you with" in response.lower()

def test_whats_up():
    """Test 'What's up?' returns chitchat response"""
    bot = AutoPartsChatbot()
    
    response = bot.process_message("What's up?", [])
    
    # Should return friendly chitchat response
    assert "things are going well" in response.lower()

def test_chitchat_patterns_not_unknown():
    """Test various chitchat patterns don't trigger unknown response"""
    bot = AutoPartsChatbot()
    
    chitchat_phrases = [
        "How is your week?",
        "How's your week?", 
        "How are things?",
        "How's it going?",
        "What's up?",
        "How are things going?"
    ]
    
    for phrase in chitchat_phrases:
        response = bot.process_message(phrase, [])
        
        # Should not be unknown response
        assert "didn't catch that" not in response.lower(), f"Failed for phrase: '{phrase}'"
        assert "having trouble" not in response.lower(), f"Failed for phrase: '{phrase}'"
        
        # Should be friendly response
        assert len(response) > 20, f"Response too short for phrase: '{phrase}'"

def test_chitchat_after_part_recommendation():
    """Test chitchat works after part recommendations"""
    bot = AutoPartsChatbot()
    
    # Get a part recommendation
    bot.process_message("Honda battery", [])
    
    # Then use chitchat
    response = bot.process_message("How's your week?", [])
    
    # Should still handle chitchat properly
    assert "things are going well" in response.lower()
    assert "didn't catch that" not in response.lower()

def test_mixed_case_chitchat():
    """Test chitchat works with different cases"""
    bot = AutoPartsChatbot()
    
    test_cases = [
        "HOW IS YOUR WEEK?",
        "how's your week?",
        "How Are Things?",
        "what's UP?"
    ]
    
    for phrase in test_cases:
        response = bot.process_message(phrase, [])
        assert "things are going well" in response.lower(), f"Failed for phrase: '{phrase}'"

if __name__ == "__main__":
    pytest.main([__file__])